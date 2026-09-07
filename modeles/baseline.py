"""
Chargement et interrogation des baselines législatifs retraite.

Usage :
    from baseline import Baselines
    b = Baselines.charger("baselines_retraites.yaml")
    b.age_legal(1965, baseline="B1_suspension", trimestre=1)   -> 753
    b.comparer(1966)                                           -> tableau B0/B1
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from . import chemins

BASELINES = ("B0_reforme_2023", "B1_suspension", "B2_post_2028")


def _parse_cle(cle) -> tuple[int, int, int]:
    """
    Traduit une clé de génération en (annee, trimestre_min, trimestre_max).

    1964      -> (1964, 1, 4)   toute la génération (YAML rend un int)
    '1965T1'  -> (1965, 1, 1)   premier trimestre seulement
    '1965T2+' -> (1965, 2, 4)   du deuxième trimestre à la fin de l'année
    '1961T4'  -> (1961, 4, 4)   nés à compter du 1er septembre
    """
    m = re.fullmatch(r"(\d{4})(?:T(\d)(\+)?)?", str(cle))
    if not m:
        raise ValueError(f"Clé de génération non reconnue : {cle!r}")
    annee, trim, ouvert = m.group(1), m.group(2), m.group(3)
    if trim is None:
        return int(annee), 1, 4
    t = int(trim)
    return int(annee), t, (4 if ouvert else t)


@dataclass(frozen=True)
class Parametres:
    """Paramètres applicables à une génération donnée sous un baseline donné."""

    generation: int
    trimestre: int
    baseline: str
    age_legal_mois: int
    duree_assurance_trimestres: int
    age_taux_plein_mois: int

    @property
    def age_legal_texte(self) -> str:
        a, m = divmod(self.age_legal_mois, 12)
        return f"{a} ans" if m == 0 else f"{a} ans {m} mois"

    def __str__(self) -> str:
        return (
            f"Génération {self.generation}T{self.trimestre} — {self.baseline}\n"
            f"  âge légal            : {self.age_legal_texte}\n"
            f"  durée requise        : {self.duree_assurance_trimestres} trimestres\n"
            f"  taux plein auto      : {self.age_taux_plein_mois // 12} ans"
        )


class Baselines:
    """Accès aux trois baselines législatifs."""

    def __init__(self, donnees: dict):
        self._d = donnees
        self.meta = donnees["meta"]
        self.invariants = donnees["invariants"]

    @classmethod
    def charger(cls, chemin: str | Path | None = None) -> "Baselines":
        with open(chemin or chemins.BASELINES, encoding="utf-8") as f:
            return cls(yaml.safe_load(f))

    # -- résolution d'une table --------------------------------------------

    def _resoudre(self, table: dict, generation: int, trimestre: int):
        """
        Cherche la valeur applicable, en privilégiant la clé la plus spécifique.
        Une clé restreinte à un trimestre l'emporte sur une clé annuelle.
        """
        sentinelles = ("defaut_au_dela", "defaut_en_deca")

        candidats = []
        for cle, valeur in table.items():
            if cle in sentinelles:
                continue
            annee, tmin, tmax = _parse_cle(cle)
            if annee == generation and tmin <= trimestre <= tmax:
                candidats.append((tmax - tmin, valeur))  # 0 = plus spécifique
        if candidats:
            return min(candidats)[1]

        annees = [
            _parse_cle(c)[0] for c in table if c not in sentinelles
        ]
        if generation > max(annees):
            return table["defaut_au_dela"]
        if generation < min(annees):
            if "defaut_en_deca" not in table:
                raise KeyError(
                    f"Génération {generation} antérieure au champ de la table "
                    f"(débute en {min(annees)}) et aucun `defaut_en_deca` défini."
                )
            return table["defaut_en_deca"]

        # Génération intercalaire, ou trimestre hors de la borne infra-annuelle
        # (ex. né en juin 1961, la table ne couvrant que 1961T4) : reporter la
        # dernière valeur connue, à défaut le plancher.
        candidates_ant = [a for a in annees if a < generation]
        if not candidates_ant:
            if "defaut_en_deca" not in table:
                raise KeyError(
                    f"Génération {generation}T{trimestre} non couverte et "
                    f"aucun `defaut_en_deca` défini."
                )
            return table["defaut_en_deca"]
        precedente = max(candidates_ant)
        return next(
            v
            for c, v in table.items()
            if c not in sentinelles and _parse_cle(c)[0] == precedente
        )

    def _bloc(self, baseline: str, mode: str | None = None) -> dict:
        """
        Renvoie le bloc de paramètres applicable.

        Pour B2, `mode` sélectionne la trajectoire de sortie de suspension.
        À défaut, le `mode_sortie` déclaré dans le fichier s'applique.
        """
        if baseline not in BASELINES:
            raise ValueError(f"Baseline inconnu : {baseline!r}. Attendu : {BASELINES}")
        bloc = self._d[baseline]

        if "modes" in bloc:
            choisi = mode or bloc["mode_sortie"]
            if choisi not in bloc["modes"]:
                raise ValueError(
                    f"Mode de sortie inconnu : {choisi!r}. "
                    f"Attendu : {tuple(bloc['modes'])}"
                )
            bloc = bloc["modes"][choisi]
        elif mode is not None:
            raise ValueError(f"Le baseline {baseline!r} n'admet pas de mode de sortie.")

        if "herite_de" in bloc:
            parent = dict(self._d[bloc["herite_de"]])
            parent.update({k: v for k, v in bloc.items() if k != "herite_de"})
            return parent
        return bloc

    def modes_disponibles(self, baseline: str = "B2_post_2028") -> tuple[str, ...]:
        return tuple(self._d[baseline].get("modes", {}))

    # -- API publique -------------------------------------------------------

    def parametres(
        self,
        generation: int,
        baseline: str = "B1_suspension",
        trimestre: int = 1,
        mode: str | None = None,
    ) -> Parametres:
        bloc = self._bloc(baseline, mode)
        return Parametres(
            generation=generation,
            trimestre=trimestre,
            baseline=baseline if mode is None else f"{baseline}/{mode}",
            age_legal_mois=self._resoudre(bloc["age_legal_mois"], generation, trimestre),
            duree_assurance_trimestres=self._resoudre(
                bloc["duree_assurance_trimestres"], generation, trimestre
            ),
            age_taux_plein_mois=self.invariants["age_taux_plein_automatique_mois"],
        )

    def age_legal(self, generation, baseline="B1_suspension", trimestre=1, mode=None) -> int:
        return self.parametres(generation, baseline, trimestre, mode).age_legal_mois

    def duree(self, generation, baseline="B1_suspension", trimestre=1, mode=None) -> int:
        return self.parametres(
            generation, baseline, trimestre, mode
        ).duree_assurance_trimestres

    def fourchette_post_2028(self, generation: int, trimestre: int = 1) -> dict:
        """
        Renvoie l'âge légal et la durée requise sous les trois modes de sortie.

        Tout chiffrage à horizon 2028 et au-delà doit être présenté sous cette
        forme de fourchette, jamais sous un mode unique : le choix du mode est
        une hypothèse politique, pas une lecture juridique.
        """
        resultat = {}
        for m in self.modes_disponibles():
            p = self.parametres(generation, "B2_post_2028", trimestre, mode=m)
            resultat[m] = {
                "age_legal_mois": p.age_legal_mois,
                "age_legal_texte": p.age_legal_texte,
                "duree_trimestres": p.duree_assurance_trimestres,
            }
        ages = [v["age_legal_mois"] for v in resultat.values()]
        resultat["amplitude_mois"] = max(ages) - min(ages)
        return resultat

    def comparer(self, generation: int, trimestre: int = 1) -> dict:
        """Écart B1 - B0 pour une génération : le gain net de la suspension."""
        p0 = self.parametres(generation, "B0_reforme_2023", trimestre)
        p1 = self.parametres(generation, "B1_suspension", trimestre)
        return {
            "generation": generation,
            "trimestre": trimestre,
            "age_B0_mois": p0.age_legal_mois,
            "age_B1_mois": p1.age_legal_mois,
            "gain_age_mois": p0.age_legal_mois - p1.age_legal_mois,
            "duree_B0": p0.duree_assurance_trimestres,
            "duree_B1": p1.duree_assurance_trimestres,
            "gain_duree_trimestres": p0.duree_assurance_trimestres
            - p1.duree_assurance_trimestres,
        }

    def baseline_applicable(self, date_effet_pension: str) -> str:
        """
        Sélectionne le baseline selon la date d'entrée en jouissance.
        Rappel : c'est bien la date d'effet de la pension qui commande,
        pas la date de dépôt du dossier.
        """
        b1 = self._d["B1_suspension"]
        if date_effet_pension < b1["date_effet"]:
            return "B0_reforme_2023"
        if date_effet_pension < b1["date_fin"]:
            return "B1_suspension"
        return "B2_post_2028"
