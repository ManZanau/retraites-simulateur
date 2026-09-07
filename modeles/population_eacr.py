"""
Construction de la population de retraités à partir des fichiers EACR réels.

CE QUI EST OBSERVÉ (exact, issu de l'EACR 2024) :
    - effectifs par âge et sexe, tous régimes, sans double compte
    - avantage principal moyen de droit direct (m1) par cellule

CE QUI NE L'EST PAS :
    - la DISPERSION des pensions à l'intérieur de chaque cellule.
      Aucune table de l'EACR ne publie de distribution par tranche de montant.
      Vérifié sur les neuf tables du millésime de mai 2026.

CONSÉQUENCE : cette classe produit une population dont les effectifs et les
moyennes sont exacts, et dont la dispersion est un PARAMÈTRE LIBRE. Toute
sortie dépendant des déciles doit être publiée sous forme de fourchette
balayant ce paramètre, jamais comme un chiffre unique.
"""

from __future__ import annotations

import pathlib
from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import chemins

FICHIER_PART1 = "62_EACR_diffusée_Part_1_-_version_du_26_mai_2026.xlsx"
MENTION_SOURCE = "Source : Drees, enquête annuelle auprès des caisses de retraite (EACR), enrichie avec le modèle Ancetre"


def _age_num(s) -> float:
    s = str(s).strip()
    if s.startswith("plus de"):
        return 96.0
    try:
        return float(s)
    except ValueError:
        return np.nan


@dataclass
class PopulationEACR:
    """Cellules âge x sexe avec effectif et pension moyenne observés."""

    cellules: pd.DataFrame          # colonnes : age, Sexe, effectifs, m1
    annee: int
    champ: str

    @classmethod
    def charger(
        cls,
        chemin_xlsx: str | None = None,
        annee: int = 2024,
        resid: str = "France",
    ) -> "PopulationEACR":
        chemin_xlsx = chemin_xlsx or chemins.EACR_PART1
        if not pathlib.Path(chemin_xlsx).exists():
            raise FileNotFoundError(
                f"Fichier EACR introuvable : {chemin_xlsx}\n"
                "Téléchargez les deux fichiers .xlsx depuis data.drees et placez-les "
                "dans le dossier donnees/ (voir donnees/LISEZMOI.md)."
            )
        C = pd.read_excel(chemin_xlsx, sheet_name="C-Droits_directs")
        d = C[
            (C.Année == annee)
            & (C.Champ == "ddir")
            & (C.CC == 0)                      # tous régimes ANCETRE, sans double compte
            & (C.Resid == resid)
            & (C.Naiss == "Ensemble")
            & (C.Sexe.isin(["Femmes", "Hommes"]))
        ].copy()
        d["age"] = d.Age.map(_age_num)
        d = d[d.age.notna() & d.effectifs.notna() & d.m1.notna()]
        return cls(
            cellules=d[["age", "Sexe", "effectifs", "m1"]].reset_index(drop=True),
            annee=annee,
            champ=f"droit direct, {resid}, tous régimes",
        )

    # -- grandeurs observées ------------------------------------------------

    @property
    def effectif_total(self) -> float:
        return float(self.cellules.effectifs.sum())

    @property
    def pension_moyenne(self) -> float:
        c = self.cellules
        return float((c.effectifs * c.m1).sum() / c.effectifs.sum())

    @property
    def ecart_type_inter_cellules(self) -> float:
        """
        Dispersion EFFECTIVEMENT observable. Ne mesure que l'écart entre les
        moyennes de cellules, pas la dispersion réelle des pensions.
        """
        c = self.cellules
        w, mu = c.effectifs.values, c.m1.values
        mbar = self.pension_moyenne
        return float(np.sqrt((w * (mu - mbar) ** 2).sum() / w.sum()))

    def part_variance_observee(self, ecart_type_total_suppose: float) -> float:
        return self.ecart_type_inter_cellules**2 / ecart_type_total_suppose**2

    # -- tirage d'individus -------------------------------------------------

    def tirer(
        self,
        n: int,
        sigma_intra: float,
        graine: int = 0,
        borne_basse: float = 80.0,
        borne_haute: float = 30_000.0,
    ) -> tuple[np.ndarray, np.ndarray, pd.DataFrame]:
        """
        Tire n individus. Chaque cellule reçoit une log-normale de moyenne
        égale à sa moyenne observée et de paramètre de forme `sigma_intra`,
        QUI EST UNE HYPOTHÈSE. Renvoie (pensions, poids, table des cellules).
        """
        if sigma_intra <= 0:
            raise ValueError("sigma_intra doit être strictement positif")
        rng = np.random.default_rng(graine)
        c = self.cellules
        proba = (c.effectifs / c.effectifs.sum()).values
        idx = rng.choice(len(c), size=n, p=proba)
        mu_cell = c.m1.values[idx]
        # Log-normale d'espérance mu_cell
        pensions = rng.lognormal(np.log(mu_cell) - sigma_intra**2 / 2, sigma_intra)
        pensions = np.clip(pensions, borne_basse, borne_haute)
        pensions *= self.pension_moyenne / np.average(pensions)   # recalage exact
        poids = np.full(n, self.effectif_total / n)
        return pensions, poids, c.iloc[idx].reset_index(drop=True)

    def rapport(self) -> str:
        return "\n".join([
            f"Population EACR {self.annee} — {self.champ}",
            f"  effectif total                : {self.effectif_total:>14,.0f}",
            f"  pension moyenne (m1)          : {self.pension_moyenne:>13,.1f} €",
            f"  cellules âge x sexe           : {len(self.cellules):>14,}",
            f"  écart-type inter-cellules     : {self.ecart_type_inter_cellules:>13,.1f} €",
            "",
            "  /!\\ La dispersion INTRA-cellule n'est pas observée. Elle est",
            "      fixée par le paramètre `sigma_intra` de la méthode tirer().",
            "",
            f"  {MENTION_SOURCE}",
        ])
