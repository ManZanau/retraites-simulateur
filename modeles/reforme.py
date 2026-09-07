"""
Application d'un scénario de réforme à une distribution de pensions.

LEVIER UNIQUE : la pension brute. Le net, les prélèvements et les prestations
sous conditions de ressources sont calculés en aval, dans le module fiscal.

DEUX MODES
    marginal  Seule la fraction de pension située dans une tranche subit le
              taux de cette tranche, comme un barème d'impôt. Préserve
              l'ordre des pensions : personne ne peut passer devant son
              voisin du fait de la réforme.

    moyen     La pension entière est multipliée par le taux de son décile.
              Crée des effets de seuil et des inversions de classement.
              Conservé uniquement pour DÉMONTRER ce défaut, pas pour chiffrer.

DÉCILES FIGÉS
    Les seuils de décile sont ceux de la distribution de référence, jamais
    recalculés après réforme. Sinon la réforme redéfinit ses propres tranches
    et le raisonnement devient circulaire.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

MODES = ("marginal", "moyen")


@dataclass
class Scenario:
    """
    Paramètres d'un scénario de réforme.

    variation_par_decile : taux par décile, 1 à 10. Positif = hausse.
                           Les déciles absents subissent 0.
    plafond              : {"seuil": euros/mois, "taux": part écrêtée de la
                           fraction au-dessus du seuil}. taux=1.0 = plafond dur.
    plancher             : {"seuil": euros/mois}. Toute pension inférieure y
                           est portée.
    """

    nom: str
    mode: str = "marginal"
    variation_par_decile: dict[int, float] = field(default_factory=dict)
    plafond: dict | None = None
    plancher: dict | None = None
    imputation: str = "proportionnelle"

    def __post_init__(self):
        if self.mode not in MODES:
            raise ValueError(f"Mode inconnu : {self.mode!r}. Attendu : {MODES}")
        for d in self.variation_par_decile:
            if not 1 <= d <= 10:
                raise ValueError(f"Décile hors bornes : {d}")
        for t in self.variation_par_decile.values():
            if t < -1.0:
                raise ValueError("Une baisse ne peut excéder -100 %")
        if self.plafond:
            if "seuil" not in self.plafond:
                raise ValueError("Plafond : `seuil` obligatoire")
            self.plafond.setdefault("taux", 1.0)
            if not 0.0 <= self.plafond["taux"] <= 1.0:
                raise ValueError("Plafond : taux d'écrêtement hors [0, 1]")
        if self.plancher and "seuil" not in self.plancher:
            raise ValueError("Plancher : `seuil` obligatoire")
        if self.plafond and self.plancher:
            if self.plancher["seuil"] > self.plafond["seuil"]:
                raise ValueError("Plancher supérieur au plafond : scénario incohérent")


@dataclass
class Resultat:
    """Sortie d'un scénario, avec de quoi juger de sa cohérence."""

    scenario: str
    pensions_avant: np.ndarray
    pensions_apres: np.ndarray
    poids: np.ndarray
    seuils_deciles: np.ndarray
    inversions: int
    taux_inversion: float
    par_decile: list[dict]
    delta_par_caisse: dict[str, float] | None = None

    @property
    def economie_brute_mensuelle(self) -> float:
        """Pondérée. Une somme non pondérée sur un échantillon n'a aucun sens."""
        return float(((self.pensions_avant - self.pensions_apres) * self.poids).sum())

    @property
    def economie_brute_annuelle(self) -> float:
        return self.economie_brute_mensuelle * 12

    def resume(self) -> str:
        lignes = [
            f"Scénario : {self.scenario}",
            f"  économie brute annuelle : {self.economie_brute_annuelle:,.0f} €",
            f"  effectifs concernés     : "
            f"{float(self.poids[self.pensions_avant != self.pensions_apres].sum()):,.0f}",
        ]
        if self.inversions:
            lignes.append(
                f"  /!\\ INVERSIONS DE CLASSEMENT : {self.taux_inversion:.2%} des "
                f"paires ({self.inversions:,}). Le scénario fait passer des "
                f"retraités devant d'autres qui percevaient davantage avant réforme."
            )
        return "\n".join(lignes)


class MoteurReforme:
    """Applique des scénarios à une distribution de pensions mensuelles brutes."""

    def __init__(
        self,
        pensions: np.ndarray,
        poids: np.ndarray | None = None,
        parts_caisses: np.ndarray | None = None,
        noms_caisses: list[str] | None = None,
    ):
        self.pensions = np.asarray(pensions, dtype=float)
        if np.any(self.pensions < 0):
            raise ValueError("Pensions négatives dans la population")
        self.poids = (
            np.ones_like(self.pensions)
            if poids is None
            else np.asarray(poids, dtype=float)
        )
        self.parts_caisses = parts_caisses
        self.noms_caisses = noms_caisses
        if parts_caisses is not None:
            parts = np.asarray(parts_caisses, dtype=float)
            if parts.shape[0] != len(self.pensions):
                raise ValueError("parts_caisses : première dimension incohérente")
            if not np.allclose(parts.sum(axis=1), 1.0):
                raise ValueError("parts_caisses : les parts doivent sommer à 1")
            self.parts_caisses = parts

        self.seuils = self._seuils_deciles()
        self.decile = self._affecter_deciles()

    # -- déciles de référence ----------------------------------------------

    def _seuils_deciles(self) -> np.ndarray:
        """Seuils D1..D9 de la distribution de référence, pondérés."""
        ordre = np.argsort(self.pensions)
        p_tri, w_tri = self.pensions[ordre], self.poids[ordre]
        cum = np.cumsum(w_tri) / w_tri.sum()
        return np.array([np.interp(q / 10, cum, p_tri) for q in range(1, 10)])

    def _affecter_deciles(self) -> np.ndarray:
        """Décile 1..10 de chaque individu, figé sur la référence."""
        return np.searchsorted(self.seuils, self.pensions, side="right") + 1

    # -- application --------------------------------------------------------

    def appliquer(self, sc: Scenario) -> Resultat:
        p = self.pensions.copy()

        if sc.variation_par_decile:
            p = (
                self._variation_marginale(p, sc)
                if sc.mode == "marginal"
                else self._variation_moyenne(p, sc)
            )

        if sc.plafond:
            seuil, taux = sc.plafond["seuil"], sc.plafond["taux"]
            p = np.where(p > seuil, p - taux * (p - seuil), p)

        # Le plancher s'applique en dernier : il doit être opposable au
        # résultat de tout ce qui précède, y compris de l'écrêtement.
        if sc.plancher:
            p = np.maximum(p, sc.plancher["seuil"])

        inv = self._compter_inversions(p)
        n = len(p)
        return Resultat(
            scenario=sc.nom,
            pensions_avant=self.pensions,
            pensions_apres=p,
            poids=self.poids,
            seuils_deciles=self.seuils,
            inversions=inv,
            taux_inversion=inv / (n * (n - 1) / 2) if n > 1 else 0.0,
            par_decile=self._ventiler(p),
            delta_par_caisse=self._imputer(p, sc),
        )

    def _variation_marginale(self, p, sc):
        """
        Barème par tranches : la fraction de pension comprise entre deux seuils
        de décile subit le taux du décile correspondant.
        """
        bornes = np.concatenate(([0.0], self.seuils, [np.inf]))
        resultat = np.zeros_like(p)
        for d in range(1, 11):
            bas, haut = bornes[d - 1], bornes[d]
            tranche = np.clip(p, bas, haut) - bas
            resultat += tranche * (1.0 + sc.variation_par_decile.get(d, 0.0))
        return resultat

    def _variation_moyenne(self, p, sc):
        taux = np.array([sc.variation_par_decile.get(d, 0.0) for d in range(1, 11)])
        return p * (1.0 + taux[self.decile - 1])

    # -- diagnostics --------------------------------------------------------

    def _compter_inversions(self, p) -> int:
        """
        Nombre de paires dont l'ordre s'inverse. Un scénario en produisant est
        difficilement défendable : il fait passer devant des retraités qui
        percevaient moins avant réforme.
        """
        ordre = np.argsort(self.pensions)
        suite = p[ordre]
        # Comptage O(n log n) par tri-fusion des inversions strictes
        return int(self._inversions(suite))

    @staticmethod
    def _inversions(a) -> int:
        def tri(v):
            if len(v) <= 1:
                return v, 0
            m = len(v) // 2
            g, ig = tri(v[:m])
            d, dr = tri(v[m:])
            fusion, i, j, inv = [], 0, 0, ig + dr
            while i < len(g) and j < len(d):
                if g[i] <= d[j]:
                    fusion.append(g[i]); i += 1
                else:
                    fusion.append(d[j]); j += 1
                    inv += len(g) - i
            fusion.extend(g[i:]); fusion.extend(d[j:])
            return fusion, inv

        return tri(list(a))[1]

    def _ventiler(self, p) -> list[dict]:
        lignes = []
        for d in range(1, 11):
            m = self.decile == d
            if not m.any():
                continue
            w = self.poids[m]
            avant = float((self.pensions[m] * w).sum())
            apres = float((p[m] * w).sum())
            lignes.append({
                "decile": d,
                "effectif": float(w.sum()),
                "pension_moyenne_avant": avant / w.sum(),
                "pension_moyenne_apres": apres / w.sum(),
                "variation_relative": (apres - avant) / avant if avant else 0.0,
                "economie_annuelle": (avant - apres) * 12,
            })
        return lignes

    def _imputer(self, p, sc) -> dict[str, float] | None:
        """
        Répartit la variation de pension entre caisses. Détermine quel organisme
        encaisse l'économie — donc la ventilation par sous-secteur d'APU.
        """
        if self.parts_caisses is None or self.noms_caisses is None:
            return None
        if sc.imputation != "proportionnelle":
            raise NotImplementedError(
                f"Règle d'imputation non implémentée : {sc.imputation!r}"
            )
        delta = (self.pensions - p) * self.poids
        par_caisse = (delta[:, None] * self.parts_caisses).sum(axis=0) * 12
        return dict(zip(self.noms_caisses, par_caisse.tolist()))
