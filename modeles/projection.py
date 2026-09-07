"""
Projection des effectifs de retraités et de la masse des pensions.

MÉTHODE : projection par composantes de cohorte. Chaque génération est suivie
année par année ; on lui applique la mortalité, les liquidations nouvelles et
la revalorisation des pensions déjà liquidées.

INTÉGRATION : les âges de liquidation proviennent du module `baseline`, ce qui
garantit qu'une projection utilise bien le droit correspondant au scénario
législatif retenu (B0 / B1 / B2 et ses trois modes de sortie).

AVERTISSEMENT SUR LA HIÉRARCHIE DES EFFETS
    Sur vingt ans, la règle d'indexation pèse davantage que la démographie.
    Un écart d'un point par an entre indexation et croissance des salaires
    compose à environ 22 % sur la période. Aucun scénario démographique
    plausible ne produit un tel écart. Le simulateur doit donc traiter
    l'indexation comme un paramètre de premier rang, et non comme un
    réglage technique.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np


# =========================================================================
# Mortalité
# =========================================================================

@dataclass
class TableMortalite:
    """
    Quotients de mortalité annuels par âge et sexe.

    ÉTAT : forme paramétrique de Gompertz-Makeham, CALÉE sur les espérances de
    vie publiées par l'Insee pour 2025.

        femmes : e(60) = 27,9 ans et e(65) = 23,4 ans, reproduits exactement
        hommes : e(65) = 19,7 ans, reproduit exactement ; e(60) obtenu = 24,0
                 contre environ 23,5 attendus, la pente étant supposée commune
                 aux deux sexes faute d'une seconde cible masculine publiée

    DÉRIVE DE LONGÉVITÉ. Les quotients baissent chaque année d'un taux calé sur
    les cibles 2070 du COR : e(65) de 24,8 ans pour les hommes et 26,7 pour les
    femmes. Ignorer cette dérive sous-estimerait les dépenses futures.

    Une table INSEE réelle reste préférable et se branche par `depuis_tableau`,
    sans modifier le reste du moteur.
    """

    source: str = "Gompertz-Makeham calé sur Insee 2025 et cibles COR 2070"
    reelle: bool = False
    annee_reference: int = 2025
    # a = mortalité de fond, b et c = pente ; amelioration = baisse annuelle
    _params: dict = field(default_factory=lambda: {
        "homme": {"a": 0.0004, "b": 4.769e-06, "c": 0.11477, "amelioration": 0.01475},
        "femme": {"a": 0.0002, "b": 2.929e-06, "c": 0.11477, "amelioration": 0.00928},
    })
    _table: dict | None = None

    @classmethod
    def depuis_tableau(cls, quotients: dict, source: str) -> "TableMortalite":
        """quotients : {(sexe, age): qx}. Chemin d'entrée des tables INSEE."""
        return cls(source=source, reelle=True, _table=quotients)

    def qx(self, age: int, sexe: str, annee: int | None = None) -> float:
        """Quotient de mortalité, avec dérive de longévité si `annee` est fourni."""
        if self._table is not None:
            return self._table.get((sexe, age), 1.0)
        p = self._params[sexe]
        mu = p["a"] + p["b"] * math.exp(p["c"] * age)
        if annee is not None:
            mu *= (1.0 - p["amelioration"]) ** (annee - self.annee_reference)
        return min(1.0, 1.0 - math.exp(-mu))

    def esperance_de_vie(self, age_depart: int, sexe: str,
                         annee: int | None = None) -> float:
        """Contrôle de vraisemblance de la table."""
        survie, esperance = 1.0, 0.0
        for age in range(age_depart, 125):
            survie *= 1.0 - self.qx(age, sexe, annee)
            esperance += survie
        return esperance


# =========================================================================
# Hypothèses
# =========================================================================

@dataclass
class ComportementDepart:
    """
    Répartition des liquidations autour de l'âge légal.

    Tout le monde ne part pas à l'âge d'ouverture des droits : certains
    anticipent (carrières longues, invalidité), beaucoup décalent pour
    atteindre le taux plein. La distribution ci-dessous est une hypothèse
    de travail, à estimer sur l'EIC.
    """

    etalement: dict[int, float] = field(default_factory=lambda: {
        -2: 0.08,   # deux ans avant l'âge légal (carrières longues)
        -1: 0.07,
        0: 0.42,    # à l'âge légal
        1: 0.20,
        2: 0.13,
        3: 0.10,    # départs tardifs, dont attente du taux plein à 67 ans
    })
    source: str = "HYPOTHÈSE - à estimer sur l'EIC"

    def __post_init__(self):
        total = sum(self.etalement.values())
        if abs(total - 1.0) > 1e-9:
            raise ValueError(f"L'étalement doit sommer à 1, obtenu {total:.6f}")


@dataclass
class ReglesIndexation:
    """
    Règles de revalorisation, distinctes entre base et complémentaire.

    La divergence observée en 2026 — CNAV +0,9 %, AGIRC-ARRCO gelée — n'est
    pas un accident : les complémentaires sont pilotées par les partenaires
    sociaux, non par la loi. Modéliser les deux par un taux unique
    effacerait un mécanisme structurant de déformation de la distribution.
    """

    inflation: dict[int, float]
    croissance_salaires: dict[int, float]
    regle_base: str = "inflation"            # inflation | gel | salaires | fixe
    regle_complementaire: str = "inflation"
    taux_fixe_base: float = 0.0
    taux_fixe_complementaire: float = 0.0
    sous_indexation_base: float = 0.0        # points retranchés à l'inflation
    sous_indexation_complementaire: float = 0.0

    def taux(self, annee: int, regime: str) -> float:
        if regime == "base":
            regle, fixe, sous = (
                self.regle_base, self.taux_fixe_base, self.sous_indexation_base
            )
        else:
            regle, fixe, sous = (
                self.regle_complementaire,
                self.taux_fixe_complementaire,
                self.sous_indexation_complementaire,
            )
        if regle == "gel":
            return 0.0
        if regle == "fixe":
            return fixe
        if regle == "salaires":
            return self.croissance_salaires.get(annee, 0.0) - sous
        return self.inflation.get(annee, 0.0) - sous


# =========================================================================
# Population
# =========================================================================

@dataclass
class Cohorte:
    generation: int
    sexe: str
    effectif_non_liquide: float
    effectif_retraite: float
    pension_base: float           # mensuelle moyenne, en euros courants
    pension_complementaire: float

    @property
    def pension_totale(self) -> float:
        return self.pension_base + self.pension_complementaire


@dataclass
class ResultatAnnuel:
    annee: int
    effectif_retraites: float
    masse_pensions_annuelle: float
    pension_moyenne_mensuelle: float
    nouveaux_liquidants: float
    deces_retraites: float


# =========================================================================
# Moteur
# =========================================================================

class MoteurProjection:
    """Projection par composantes de cohorte."""

    def __init__(
        self,
        cohortes: list[Cohorte],
        baselines,                       # instance de baseline.Baselines
        mortalite: TableMortalite,
        indexation: ReglesIndexation,
        comportement: ComportementDepart | None = None,
        pension_entree_base: float = 900.0,
        pension_entree_complementaire: float = 500.0,
        croissance_pension_entree: float = 0.010,
    ):
        self.cohortes = [Cohorte(**c.__dict__) for c in cohortes]  # copie
        self.baselines = baselines
        self.mortalite = mortalite
        self.indexation = indexation
        self.comportement = comportement or ComportementDepart()
        self.pension_entree_base = pension_entree_base
        self.pension_entree_complementaire = pension_entree_complementaire
        self.croissance_pension_entree = croissance_pension_entree
        self.avertissements = []
        if not mortalite.reelle:
            self.avertissements.append(
                "Table de mortalité paramétrique, calée sur les espérances de vie "
                "Insee 2025 et les cibles COR 2070 — pas une table INSEE réelle."
            )

    # -- une année ---------------------------------------------------------

    def _pas_annuel(self, annee: int, baseline: str, mode: str | None) -> ResultatAnnuel:
        nouveaux, deces = 0.0, 0.0

        taux_base = self.indexation.taux(annee, "base")
        taux_compl = self.indexation.taux(annee, "complementaire")

        for c in self.cohortes:
            age = annee - c.generation
            if age < 0:
                continue
            q = self.mortalite.qx(age, c.sexe, annee)

            # 1. Mortalité, appliquée aux deux populations
            deces += c.effectif_retraite * q
            c.effectif_retraite *= 1.0 - q
            c.effectif_non_liquide *= 1.0 - q

            # 2. Liquidations nouvelles
            if c.effectif_non_liquide > 0:
                age_legal_mois = self.baselines.age_legal(
                    c.generation, baseline, mode=mode
                )
                age_legal = age_legal_mois // 12
                ecart = age - age_legal
                part = self.comportement.etalement.get(ecart, 0.0)
                # Rattrapage : au-delà de la fenêtre, on liquide le reliquat
                if ecart > max(self.comportement.etalement):
                    part = 1.0
                if part > 0:
                    flux = c.effectif_non_liquide * min(1.0, part)
                    if c.effectif_retraite + flux > 0:
                        # Pension moyenne pondérée entre stock et flux entrant
                        anciennete = annee - 2026
                        facteur = (1 + self.croissance_pension_entree) ** anciennete
                        pb = self.pension_entree_base * facteur
                        pc = self.pension_entree_complementaire * facteur
                        tot = c.effectif_retraite + flux
                        c.pension_base = (
                            c.pension_base * c.effectif_retraite + pb * flux
                        ) / tot
                        c.pension_complementaire = (
                            c.pension_complementaire * c.effectif_retraite + pc * flux
                        ) / tot
                    c.effectif_retraite += flux
                    c.effectif_non_liquide -= flux
                    nouveaux += flux

            # 3. Revalorisation du stock
            c.pension_base *= 1.0 + taux_base
            c.pension_complementaire *= 1.0 + taux_compl

        effectif = sum(c.effectif_retraite for c in self.cohortes)
        masse = sum(
            c.effectif_retraite * c.pension_totale * 12 for c in self.cohortes
        )
        return ResultatAnnuel(
            annee=annee,
            effectif_retraites=effectif,
            masse_pensions_annuelle=masse,
            pension_moyenne_mensuelle=(masse / effectif / 12) if effectif else 0.0,
            nouveaux_liquidants=nouveaux,
            deces_retraites=deces,
        )

    # -- projection complète ------------------------------------------------

    def projeter(
        self,
        annee_debut: int,
        annee_fin: int,
        baseline: str = "B1_suspension",
        mode: str | None = None,
    ) -> list[ResultatAnnuel]:
        if annee_fin < annee_debut:
            raise ValueError("Année de fin antérieure à l'année de début")
        return [
            self._pas_annuel(a, baseline, mode)
            for a in range(annee_debut, annee_fin + 1)
        ]

    @staticmethod
    def aux_horizons(
        resultats: list[ResultatAnnuel], base: int, horizons=(1, 2, 5, 10, 15, 20)
    ) -> list[dict]:
        """Extrait les horizons demandés, avec évolution rapportée à l'origine."""
        par_annee = {r.annee: r for r in resultats}
        origine = par_annee.get(base)
        if origine is None:
            raise ValueError(f"Année de base {base} absente de la projection")
        sorties = []
        for h in horizons:
            r = par_annee.get(base + h)
            if r is None:
                continue
            sorties.append({
                "horizon": h,
                "annee": r.annee,
                "effectif": r.effectif_retraites,
                "masse": r.masse_pensions_annuelle,
                "pension_moyenne": r.pension_moyenne_mensuelle,
                "evol_effectif": r.effectif_retraites / origine.effectif_retraites - 1,
                "evol_masse": r.masse_pensions_annuelle / origine.masse_pensions_annuelle - 1,
            })
        return sorties
