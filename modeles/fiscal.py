"""
Calcul des prélèvements sur les pensions : CSG/CRDS/CASA puis impôt sur le
revenu, et cascade de décomposition d'une réforme.

PRINCIPE DE PRUDENCE
    Les paramètres portent un niveau de confiance. Un paramètre marqué
    `conflit` non arbitré, ou `manquant`, fait LEVER une exception plutôt que
    produire un chiffre. Un simulateur budgétaire qui rend silencieusement un
    résultat faux est pire qu'un simulateur qui refuse de répondre.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from . import chemins


class ParametreIndisponible(RuntimeError):
    """Paramètre manquant ou non arbitré : le calcul doit s'interrompre."""


@dataclass
class ParametresASPA:
    """
    Paramètres d'ASPA rendus pilotables, pour tester une ASPA étendue comme
    alternative à un plancher de pension.

    assiette_menage  True  : ressources du ménage entier (droit en vigueur)
                     False : pension individuelle seulement. Ne correspond à
                             aucun droit existant, mais permet d'isoler l'effet
                             de la condition de ressources dans la comparaison
                             avec un plancher, qui lui est individuel.
    """

    montant_annuel_seul: float
    montant_annuel_couple: float
    age_minimum: int = 65
    taux_recours: float = 1.0
    sous_condition_ressources: bool = True
    assiette_menage: bool = True
    imposable: bool = False
    assujettie_csg: bool = False
    recuperable_succession: bool = True

    @classmethod
    def depuis_parametres(cls, bloc: dict) -> "ParametresASPA":
        return cls(
            montant_annuel_seul=bloc["montants_annuels"]["personne_seule"],
            montant_annuel_couple=bloc["montants_annuels"]["couple"],
            age_minimum=bloc["conditions"]["age_minimum"],
            taux_recours=bloc["taux_de_recours"]["valeur"],
        )

    def revalorise(self, facteur: float) -> "ParametresASPA":
        """Variante à montants multipliés, autres paramètres inchangés."""
        from dataclasses import replace
        return replace(
            self,
            montant_annuel_seul=self.montant_annuel_seul * facteur,
            montant_annuel_couple=self.montant_annuel_couple * facteur,
        )


@dataclass
class Prelevements:
    csg: float
    csg_deductible: float
    crds: float
    casa: float
    taux_csg_applique: str

    @property
    def total(self) -> float:
        return self.csg + self.crds + self.casa


@dataclass
class Cascade:
    """
    Décomposition d'une réforme, du brut à l'économie nette.

    Convention de signe : une valeur positive est un gain pour les finances
    publiques, une valeur négative un coût.
    """

    economie_brute: float
    perte_csg: float
    perte_crds_casa: float
    perte_ir: float
    effet_aspa: float = 0.0
    effet_autres_prestations: float | None = None

    @property
    def economie_nette(self) -> float:
        """
        Économie nette hors APL, CSS et exonérations locales, qui restent
        non renseignées. Ces termes vont tous dans le même sens : ils
        RÉDUISENT encore l'économie. Le résultat est donc une borne
        supérieure, resserrée par rapport à celle d'avant l'ASPA.
        """
        return (
            self.economie_brute
            - self.perte_csg
            - self.perte_crds_casa
            - self.perte_ir
            - self.effet_aspa
        )

    @property
    def taux_de_rendement(self) -> float:
        """Part de l'économie brute effectivement conservée."""
        if self.economie_brute == 0:
            return 0.0
        return self.economie_nette / self.economie_brute

    @property
    def economie_nette_hors_prestations(self) -> float:
        """Économie nette des seuls prélèvements, avant effet ASPA."""
        return (
            self.economie_brute - self.perte_csg - self.perte_crds_casa - self.perte_ir
        )

    def __str__(self) -> str:
        def ligne(lib, val):
            return f"  {lib:<44}{val / 1e9:>10,.2f} Md€"

        lignes = [
            "CASCADE DE DÉCOMPOSITION",
            ligne("Économie brute sur les pensions", self.economie_brute),
            ligne("− perte de CSG", -self.perte_csg),
            ligne("− perte de CRDS et CASA", -self.perte_crds_casa),
            ligne("− perte d'impôt sur le revenu", -self.perte_ir),
            ligne("− hausse de l'ASPA", -self.effet_aspa),
            "  " + "=" * 54,
            ligne("= ÉCONOMIE NETTE", self.economie_nette),
            f"  {'taux de rendement':<44}{self.taux_de_rendement:>13.1%}",
        ]
        if self.effet_autres_prestations is None:
            lignes += [
                "",
                "  Hors APL, CSS et exonérations locales : borne supérieure.",
            ]
        return "\n".join(lignes)


class Fiscalite:
    """Moteur de calcul fiscal, piloté par le fichier de paramètres."""

    def __init__(self, params: dict):
        self.p = params
        self._ir = params["impot_revenu"]
        self._ps = params["prelevements_sociaux"]
        self._aspa = params["aspa"]

    @classmethod
    def charger(cls, chemin: str | Path | None = None) -> "Fiscalite":
        with open(chemin or chemins.FISCAL, encoding="utf-8") as f:
            obj = cls(yaml.safe_load(f))
        obj.arbitrages = []
        return obj

    def arbitrer(self, chemin: str, valeur, motif: str) -> None:
        """
        Force la valeur d'un paramètre en conflit ou manquant, en consignant
        l'arbitrage. Tout résultat produit après un arbitrage doit le
        mentionner : c'est la différence entre une hypothèse assumée et une
        valeur inventée.

        chemin : clés séparées par des points, ex.
                 "prelevements_sociaux.seuils_rfr.deux_parts.plafond_taux_median"
        """
        cles = chemin.split(".")
        noeud = self.p
        for k in cles[:-1]:
            noeud = noeud[k]
        ancienne = noeud.get(cles[-1])
        noeud[cles[-1]] = valeur
        self.arbitrages.append(
            {"chemin": chemin, "ancienne": ancienne, "valeur": valeur, "motif": motif}
        )

    def rapport_arbitrages(self) -> str:
        if not self.arbitrages:
            return "Aucun arbitrage : tous les paramètres utilisés sont sourcés."
        lignes = [f"{len(self.arbitrages)} ARBITRAGE(S) — résultats conditionnels :"]
        for a in self.arbitrages:
            lignes.append(f"  - {a['chemin']}")
            lignes.append(f"      valeur retenue : {a['valeur']}  ({a['motif']})")
        return "\n".join(lignes)

    # -- prélèvements sociaux ----------------------------------------------

    def taux_csg(self, rfr: float, parts: float) -> str:
        """Détermine la tranche de CSG applicable, ou refuse de trancher."""
        seuils = self._ps["seuils_rfr"]
        if parts == 1.0:
            grille = seuils["une_part"]
        elif parts == 2.0:
            grille = seuils["deux_parts"]
        else:
            raise ParametreIndisponible(
                f"Grille de CSG non renseignée pour {parts} parts. Seules 1 et 2 "
                "parts sont couvertes ; le supplément par demi-part additionnelle "
                "n'a pas été collecté."
            )

        if rfr <= grille["plafond_exoneration"]:
            return "exonere"
        if rfr <= grille["plafond_taux_reduit"]:
            return "reduit"

        plafond_median = grille["plafond_taux_median"]
        if plafond_median is None:
            raise ParametreIndisponible(
                f"Plafond du taux médian non arbitré pour {parts:g} parts : les "
                "sources divergent (39 886 € contre 40 604 €). RFR de "
                f"{rfr:,.0f} € situé au-dessus du taux réduit, donc dépendant de "
                "ce seuil. Calcul interrompu — trancher la valeur avant de "
                "poursuivre."
            )
        return "median" if rfr <= plafond_median else "plein"

    def prelevements(
        self, pension_annuelle: float, rfr: float, parts: float
    ) -> Prelevements:
        tranche = self.taux_csg(rfr, parts)
        conf = self._ps["csg"]["taux"][tranche]
        csg = pension_annuelle * conf["taux"]
        deductible = pension_annuelle * conf["deductible"]

        if tranche == "exonere":
            # L'exonération de CSG emporte celle de CRDS et de CASA.
            return Prelevements(0.0, 0.0, 0.0, 0.0, tranche)

        crds = pension_annuelle * self._ps["crds"]["taux"]
        casa = (
            0.0
            if tranche in self._ps["casa"]["non_due_si_taux_csg"]
            else pension_annuelle * self._ps["casa"]["taux"]
        )
        return Prelevements(csg, deductible, crds, casa, tranche)

    # -- impôt sur le revenu ------------------------------------------------

    def abattement(self, pensions_foyer: float, nb_pensionnes: int) -> float:
        """
        10 % des pensions, avec un minimum PAR PENSIONNÉ et un plafond
        PAR FOYER FISCAL. Voir la note de conflit dans le fichier de
        paramètres : c'est le point le plus incertain de tout le module.
        """
        a = self._ir["abattement_pensions"]
        brut = pensions_foyer * a["taux"]
        plancher = a["minimum_par_pensionne"] * nb_pensionnes
        return min(max(brut, min(plancher, pensions_foyer)), a["maximum_par_foyer"])

    def _bareme(self, revenu_par_part: float) -> float:
        impot, bas = 0.0, 0.0
        for tr in self._ir["bareme"]["tranches"]:
            haut = tr["plafond"] if tr["plafond"] is not None else float("inf")
            if revenu_par_part <= bas:
                break
            impot += (min(revenu_par_part, haut) - bas) * tr["taux"]
            bas = haut
        return impot

    def impot(
        self,
        pensions_foyer: float,
        nb_pensionnes: int,
        parts: float,
        csg_deductible: float = 0.0,
        autres_revenus: float = 0.0,
    ) -> float:
        imposable = max(
            0.0,
            pensions_foyer
            - self.abattement(pensions_foyer, nb_pensionnes)
            - csg_deductible
            + autres_revenus,
        )

        parts_base = 2.0 if nb_pensionnes >= 2 else 1.0
        brut = self._bareme(imposable / parts) * parts

        # Plafonnement de l'avantage tiré des demi-parts supplémentaires
        demi_parts_sup = max(0.0, (parts - parts_base)) * 2
        if demi_parts_sup > 0:
            sans_avantage = self._bareme(imposable / parts_base) * parts_base
            plafond = self._ir["quotient_familial"]["plafond_par_demi_part"]
            brut = max(brut, sans_avantage - demi_parts_sup * plafond)

        # Décote
        d = self._ir["decote"]
        seuil = (
            d["seuil_application_couple"]
            if parts_base == 2.0
            else d["seuil_application_celibataire"]
        )
        if brut < seuil:
            montant = (
                d["montant_couple"] if parts_base == 2.0 else d["montant_celibataire"]
            )
            brut = max(0.0, brut - max(0.0, montant - d["taux"] * brut))

        return 0.0 if brut < self._ir["seuil_non_recouvrement"] else brut

    # -- ASPA ---------------------------------------------------------------

    def parametres_aspa_defaut(self) -> ParametresASPA:
        return ParametresASPA.depuis_parametres(self._aspa)

    def aspa_parametree(
        self,
        pension_individuelle: float,
        autres_ressources_menage: float,
        en_couple: bool,
        age: int,
        p: ParametresASPA,
    ) -> float:
        """
        ASPA sous paramètres arbitraires. Sert à tester une ASPA étendue
        comme alternative à un plancher de pension.
        """
        if age < p.age_minimum:
            return 0.0
        plafond = p.montant_annuel_couple if en_couple else p.montant_annuel_seul
        ressources = pension_individuelle + (
            autres_ressources_menage if p.assiette_menage else 0.0
        )
        if not p.sous_condition_ressources:
            # Prestation forfaitaire : versée sans examen des ressources.
            return plafond * p.taux_recours
        return max(0.0, plafond - ressources) * p.taux_recours

    def aspa(self, ressources_annuelles: float, en_couple: bool = False) -> float:
        """
        Allocation différentielle : comble l'écart entre les ressources et le
        montant garanti. Toute baisse de pension sous le plafond est donc
        compensée euro pour euro.

        Le taux de recours module le résultat. À 1 (défaut), on suppose que
        tout foyer éligible demande effectivement l'allocation — hypothèse
        naïve, qui maximise le contre-effet.
        """
        plafond = self._aspa["montants_annuels"][
            "couple" if en_couple else "personne_seule"
        ]
        brut = max(0.0, plafond - ressources_annuelles)
        return brut * self._aspa["taux_de_recours"]["valeur"]

    # -- cascade ------------------------------------------------------------

    def cascade(
        self,
        pensions_avant: float,
        pensions_apres: float,
        rfr: float,
        nb_pensionnes: int,
        parts: float,
    ) -> Cascade:
        """
        Cascade pour un foyer. Le RFR est celui d'avant réforme dans les deux
        cas : le décalage de deux ans du RFR fait que le taux de CSG ne réagit
        pas immédiatement à une baisse de pension.
        """
        av = self.prelevements(pensions_avant, rfr, parts)
        ap = self.prelevements(pensions_apres, rfr, parts)

        en_couple = nb_pensionnes >= 2
        aspa_av = self.aspa(pensions_avant, en_couple)
        aspa_ap = self.aspa(pensions_apres, en_couple)

        # L'ASPA n'est ni imposable ni assujettie : elle n'entre pas dans
        # l'assiette. Seules les pensions contributives comptent.
        ir_av = self.impot(pensions_avant, nb_pensionnes, parts, av.csg_deductible)
        ir_ap = self.impot(pensions_apres, nb_pensionnes, parts, ap.csg_deductible)

        return Cascade(
            economie_brute=pensions_avant - pensions_apres,
            perte_csg=av.csg - ap.csg,
            perte_crds_casa=(av.crds + av.casa) - (ap.crds + ap.casa),
            perte_ir=ir_av - ir_ap,
            effet_aspa=aspa_ap - aspa_av,
            effet_autres_prestations=None,   # APL, CSS, exonérations locales
        )
