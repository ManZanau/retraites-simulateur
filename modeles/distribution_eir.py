"""
Distribution empirique des pensions — DREES, EIR 2020, tableau 5.

CE QUE CE MODULE APPORTE
    Il remplace l'hypothèse de forme log-normale par la distribution
    réellement observée. L'EACR ne publie aucune ventilation par tranche de
    montant ; l'EIR, si. Le tableau 5 de l'EIR 2020 donne la répartition des
    retraités en 46 tranches de 100 euros.

VALIDATION CROISÉE
    Moyenne implicite du tableau 5 ..................... 1 624 €/mois
    EACR 2020, m1 + m2, tous régimes, tous lieux ....... 1 568 €/mois
    Écart de 3,6 %, compatible avec la majoration pour trois enfants,
    incluse dans le champ du tableau 5 et absente de m1 + m2.
    Les deux sources, construites indépendamment, concordent.

CE QUI RESTE INCERTAIN
    Une seule chose, et elle est bien plus étroite qu'auparavant : la tranche
    supérieure à 4 500 € est regroupée, sans moyenne publiée. Elle concerne
    1,82 % des retraités. C'est désormais le seul paramètre libre du modèle,
    contre la totalité de la dispersion auparavant.

CHAMP
    Bénéficiaires d'un avantage principal de droit direct dans au moins un
    régime de base, vivants au 31 décembre 2020, résidents et non-résidents.
    Pension totale : droit direct, réversion et majoration pour enfants.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

SOURCE = ("Drees, Échantillon interrégimes de retraités (EIR) 2020, tableau 5 — "
          "distribution des pensions mensuelles brutes totales")

# Parts en pourcentage, tranches de 100 € de 0 à 4 500 €, puis tranche ouverte.
PARTS_2020 = [
    2.43, 2.46, 2.35, 2.17, 2.00, 2.06, 2.28, 2.94, 4.36, 4.44,
    4.20, 4.40, 4.59, 4.82, 4.90, 4.75, 4.47, 4.23, 4.00, 3.76,
    3.63, 2.99, 2.60, 2.30, 1.99, 1.73, 1.53, 1.33, 1.17, 1.01,
    0.90, 0.76, 0.67, 0.57, 0.51, 0.46, 0.40, 0.38, 0.31, 0.29,
    0.26, 0.22, 0.20, 0.19, 0.18, 1.82,
]
BORNES_BASSES = list(range(0, 4600, 100))          # dernière = 4500, tranche ouverte

# Hypothèses sur la moyenne de la tranche supérieure à 4 500 €.
# Aucune n'est publiée : le modèle balaie l'intervalle.
TRANCHE_HAUTE = {
    "basse": 5000.0,
    "centrale": 5800.0,
    "haute": 7000.0,
}


@dataclass
class DistributionEIR:
    """Distribution empirique, éventuellement recalée sur un niveau plus récent."""

    parts: np.ndarray                 # sommant à 1
    centres: np.ndarray               # centre de chaque tranche, en €/mois
    moyenne_tranche_haute: float
    facteur_recalage: float = 1.0
    annee_forme: int = 2020
    annee_niveau: int = 2020
    effectif: float = 16_674_470

    @classmethod
    def construire(
        cls,
        moyenne_tranche_haute: float | str = "centrale",
        moyenne_cible: float | None = None,
        facteur: float | None = None,
        effectif: float | None = None,
        annee_niveau: int = 2020,
    ) -> "DistributionEIR":
        """
        `moyenne_cible` recale la distribution sur un niveau plus récent, en
        conservant sa FORME. C'est l'hypothèse standard : la déformation de la
        distribution entre deux millésimes proches est du second ordre devant
        son déplacement en niveau.
        """
        if isinstance(moyenne_tranche_haute, str):
            moyenne_tranche_haute = TRANCHE_HAUTE[moyenne_tranche_haute]
        if moyenne_tranche_haute <= 4500:
            raise ValueError("La tranche haute commence à 4 500 € : sa moyenne "
                             "doit être supérieure.")

        parts = np.array(PARTS_2020, dtype=float)
        parts /= parts.sum()
        centres = np.array([b + 50 for b in BORNES_BASSES[:-1]] + [moyenne_tranche_haute])

        if moyenne_cible is not None and facteur is not None:
            raise ValueError("Choisir soit `moyenne_cible`, soit `facteur`, pas les deux.")
        if facteur is None:
            facteur = 1.0
            if moyenne_cible is not None:
                # Recalage sur une moyenne cible : ABSORBE l'effet de
                # l'hypothèse sur la tranche haute. À réserver aux cas où la
                # moyenne est la contrainte, jamais à une analyse de
                # sensibilité sur cette tranche.
                facteur = moyenne_cible / float(np.average(centres, weights=parts))
        centres = centres * facteur

        return cls(parts=parts, centres=centres,
                   moyenne_tranche_haute=moyenne_tranche_haute,
                   facteur_recalage=facteur, annee_niveau=annee_niveau,
                   effectif=effectif if effectif is not None else 16_674_470)

    # -- statistiques -------------------------------------------------------

    @property
    def moyenne(self) -> float:
        return float(np.average(self.centres, weights=self.parts))

    @property
    def ecart_type(self) -> float:
        return float(np.sqrt(np.average((self.centres - self.moyenne) ** 2,
                                        weights=self.parts)))

    @property
    def bornes(self) -> np.ndarray:
        return np.array(BORNES_BASSES, dtype=float) * self.facteur_recalage

    def quantile(self, p: float) -> float:
        """Quantile par interpolation linéaire à l'intérieur des tranches."""
        if not 0 < p < 1:
            raise ValueError("p doit être strictement compris entre 0 et 1")
        cum = np.cumsum(self.parts)
        i = int(np.searchsorted(cum, p))
        c0 = cum[i - 1] if i > 0 else 0.0
        b = self.bornes
        if i >= len(self.parts) - 1:          # tranche ouverte : queue de Pareto
            return self._quantile_queue((p - c0) / self.parts[-1])
        return float(b[i] + (p - c0) / self.parts[i] * (b[i + 1] - b[i]))

    @property
    def alpha_pareto(self) -> float:
        """
        Indice de Pareto de la tranche ouverte, calé sur sa moyenne.
        Pour une loi de Pareto de seuil x_m et d'indice a, la moyenne vaut
        a·x_m/(a−1) ; on inverse cette relation.
        """
        xm = float(self.bornes[-1])
        m = float(self.centres[-1])
        if m <= xm:
            raise ValueError("Moyenne de la tranche ouverte inférieure à son seuil")
        return m / (m - xm)

    def _quantile_queue(self, u: float) -> float:
        """Quantile conditionnel dans la tranche ouverte, u dans [0, 1[."""
        xm, a = float(self.bornes[-1]), self.alpha_pareto
        u = min(u, 1 - 1e-9)
        return float(xm * (1.0 - u) ** (-1.0 / a))

    def deciles(self) -> list[float]:
        return [self.quantile(k / 10) for k in range(1, 10)]

    def grille(self, n_corps: int = 190, n_queue: int = 60,
               p_bascule: float = 0.98, p_max: float = 0.99995):
        """
        Grille de points de quantile à pas VARIABLE, avec une résolution fine
        dans la queue haute.

        Une grille équiprobable de 200 points s'arrête au 99,75e centile : elle
        ne contient donc personne au-delà, et un plafond de pension placé
        au-dessus de ce point paraît sans effet alors qu'il en a un. Le corps
        de la distribution est ici découpé en `n_corps` points équiprobables
        jusqu'à `p_bascule`, la queue en `n_queue` points logarithmiquement
        resserrés jusqu'à `p_max`.

        Renvoie (pensions, poids) ; les poids somment à 1.
        """
        p_corps = (np.arange(n_corps) + 0.5) / n_corps * p_bascule
        w_corps = np.full(n_corps, p_bascule / n_corps)

        # Découpage géométrique de la queue : pas de plus en plus fin
        bornes = 1 - np.geomspace(1 - p_bascule, 1 - p_max, n_queue + 1)
        p_queue = (bornes[:-1] + bornes[1:]) / 2
        w_queue = np.diff(bornes)

        p = np.concatenate([p_corps, p_queue])
        w = np.concatenate([w_corps, w_queue])
        w = w / w.sum()
        q = np.array([self.quantile(x) for x in p])
        # Recalage exact sur la moyenne de la distribution
        q = q * self.moyenne / float(np.average(q, weights=w))
        return q, w

    def rapport(self) -> str:
        d = self.deciles()
        return "\n".join([
            f"Distribution EIR — forme {self.annee_forme}, niveau {self.annee_niveau}",
            f"  moyenne                      : {self.moyenne:>10,.0f} €/mois",
            f"  écart-type                   : {self.ecart_type:>10,.0f} €/mois",
            f"  coefficient de variation     : {self.ecart_type / self.moyenne:>10.3f}",
            f"  effectif                     : {self.effectif:>10,.0f}",
            f"  facteur de recalage          : {self.facteur_recalage:>10.4f}",
            f"  moyenne tranche > 4 500 €    : {self.moyenne_tranche_haute:>10,.0f} € "
            f"(HYPOTHÈSE, 1,82 % des retraités)",
            "  déciles : " + "  ".join(f"D{i+1}={v:,.0f}" for i, v in enumerate(d)),
            "",
            f"  {SOURCE}",
        ])
