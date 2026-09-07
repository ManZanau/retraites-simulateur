"""
Moteur de calage sur marges (Iterative Proportional Fitting / raking).

PROBLÈME RÉSOLU
    Les sources publiques ne donnent que des marges : effectifs par sexe × âge,
    par régime, par tranche de pension. Le croisement complet
    régime × génération × sexe × tranche n'est publié nulle part.

    L'IPF construit la distribution jointe qui (a) respecte exactement toutes
    les marges connues et (b) reste le plus proche possible d'une structure
    a priori. C'est l'estimateur de maximum d'entropie sous contraintes de
    marges — autrement dit, la solution qui n'invente aucune association
    non imposée par les données.

CE QUE ÇA NE FAIT PAS
    L'IPF préserve les odds-ratios de la structure a priori. Si le seed est
    uniforme, on suppose l'indépendance conditionnelle entre dimensions non
    contraintes conjointement. Toute association réelle non capturée par une
    marge croisée sera absente du résultat. D'où l'importance de fournir des
    marges croisées (sexe × âge, régime × tranche) plutôt qu'une collection
    de marges univariées.

RÉFÉRENCE
    Deming & Stephan (1940). Utilisé notamment par l'Insee pour le calage
    sur marges des enquêtes ménages.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class Marge:
    """
    Contrainte de marge sur un sous-ensemble de dimensions.

    dimensions : noms des dimensions concernées, dans l'ordre du tableau cible
    valeurs    : tableau des totaux à respecter, de forme correspondante
    source     : référence bibliographique, obligatoire — toute marge sans
                 source identifiée est une hypothèse déguisée
    """

    nom: str
    dimensions: tuple[str, ...]
    valeurs: np.ndarray
    source: str
    provisoire: bool = False

    def __post_init__(self):
        self.valeurs = np.asarray(self.valeurs, dtype=float)
        if self.valeurs.ndim != len(self.dimensions):
            raise ValueError(
                f"Marge {self.nom!r} : {len(self.dimensions)} dimensions déclarées "
                f"mais tableau de dimension {self.valeurs.ndim}"
            )
        if np.any(self.valeurs < 0):
            raise ValueError(f"Marge {self.nom!r} : valeurs négatives interdites")

    @property
    def total(self) -> float:
        return float(self.valeurs.sum())


@dataclass
class Diagnostic:
    """Résultat du calage, avec de quoi juger s'il est utilisable."""

    converge: bool
    iterations: int
    ecart_max_relatif: float
    historique: list[float] = field(default_factory=list)
    marges_provisoires: list[str] = field(default_factory=list)
    divergence_kl: float | None = None

    def __str__(self) -> str:
        etat = "CONVERGE" if self.converge else "NON CONVERGE"
        lignes = [
            f"Calage : {etat} en {self.iterations} itérations",
            f"  écart max aux marges : {self.ecart_max_relatif:.2e}",
        ]
        if self.divergence_kl is not None:
            lignes.append(f"  divergence KL au seed : {self.divergence_kl:.4f}")
        if self.marges_provisoires:
            lignes.append(
                f"  /!\\ marges provisoires utilisées : "
                f"{', '.join(self.marges_provisoires)}"
            )
        return "\n".join(lignes)


class Calage:
    """
    Calage IPF d'un tableau multidimensionnel sur un jeu de marges.

    Exemple
    -------
    >>> c = Calage(dimensions={"sexe": 2, "regime": 3})
    >>> c.ajouter(Marge("par_sexe", ("sexe",), [60., 40.], source="EACR t.A"))
    >>> c.ajouter(Marge("par_regime", ("regime",), [50., 30., 20.], source="EACR t.A"))
    >>> tableau, diag = c.executer()
    """

    def __init__(self, dimensions: dict[str, int], seed: np.ndarray | None = None):
        self.noms = tuple(dimensions)
        self.formes = tuple(dimensions.values())
        self.marges: list[Marge] = []
        if seed is None:
            self._seed = np.ones(self.formes, dtype=float)
        else:
            seed = np.asarray(seed, dtype=float)
            if seed.shape != self.formes:
                raise ValueError(
                    f"Seed de forme {seed.shape}, attendu {self.formes}"
                )
            if np.any(seed < 0):
                raise ValueError("Seed : valeurs négatives interdites")
            self._seed = seed

    # -- construction -------------------------------------------------------

    def ajouter(self, marge: Marge) -> "Calage":
        inconnues = set(marge.dimensions) - set(self.noms)
        if inconnues:
            raise ValueError(
                f"Marge {marge.nom!r} : dimensions inconnues {sorted(inconnues)}"
            )
        attendu = tuple(self.formes[self.noms.index(d)] for d in marge.dimensions)
        if marge.valeurs.shape != attendu:
            raise ValueError(
                f"Marge {marge.nom!r} : forme {marge.valeurs.shape}, attendu {attendu}"
            )
        self.marges.append(marge)
        return self

    # -- vérifications préalables ------------------------------------------

    def verifier_coherence(self, tolerance: float = 1e-6) -> None:
        """
        Les marges doivent toutes porter le même total. Un écart signale une
        incohérence entre sources qu'il faut trancher AVANT de caler, jamais
        laisser l'algorithme arbitrer silencieusement.
        """
        if not self.marges:
            raise ValueError("Aucune marge déclarée")
        totaux = {m.nom: m.total for m in self.marges}
        reference = next(iter(totaux.values()))
        if reference <= 0:
            raise ValueError("Total des marges nul ou négatif")
        divergents = {
            n: t for n, t in totaux.items()
            if abs(t - reference) / reference > tolerance
        }
        if divergents:
            detail = ", ".join(f"{n} = {t:,.0f}" for n, t in totaux.items())
            raise ValueError(
                "Marges de totaux incohérents — à arbitrer explicitement avant "
                f"calage. Totaux observés : {detail}"
            )

    # -- exécution ----------------------------------------------------------

    def _preparer(self):
        """
        Pré-calcule, pour chaque marge : les axes à sommer, les valeurs cibles
        réordonnées selon l'ordre croissant des axes, et la forme de diffusion.
        """
        prep = []
        for m in self.marges:
            positions = [self.noms.index(d) for d in m.dimensions]
            tri = np.argsort(positions)
            valeurs = np.transpose(m.valeurs, tri)
            axes_sommes = tuple(
                i for i in range(len(self.noms)) if i not in positions
            )
            forme_diffusion = [1] * len(self.noms)
            for p in positions:
                forme_diffusion[p] = self.formes[p]
            prep.append((m, axes_sommes, valeurs, tuple(forme_diffusion)))
        return prep

    def executer(
        self, max_iterations: int = 1000, tolerance: float = 1e-9
    ) -> tuple[np.ndarray, Diagnostic]:
        self.verifier_coherence()
        prep = self._preparer()

        x = self._seed.copy()
        # Amorçage sur le bon total, pour que l'écart relatif soit lisible dès
        # la première itération.
        x *= self.marges[0].total / x.sum()

        historique = []
        converge = False
        it = 0

        for it in range(1, max_iterations + 1):
            for _, axes_sommes, cible, forme in prep:
                courant = x.sum(axis=axes_sommes)
                with np.errstate(divide="ignore", invalid="ignore"):
                    facteur = np.where(courant > 0, cible / courant, 0.0)
                x = x * facteur.reshape(forme)

            ecart = self._ecart_max(x, prep)
            historique.append(ecart)
            if ecart < tolerance:
                converge = True
                break

        seed_norm = self._seed * (x.sum() / self._seed.sum())
        masque = (x > 0) & (seed_norm > 0)
        kl = float(np.sum(x[masque] * np.log(x[masque] / seed_norm[masque])))

        return x, Diagnostic(
            converge=converge,
            iterations=it,
            ecart_max_relatif=historique[-1] if historique else float("nan"),
            historique=historique,
            marges_provisoires=[m.nom for m in self.marges if m.provisoire],
            divergence_kl=kl,
        )

    @staticmethod
    def _ecart_max(x, prep) -> float:
        pire = 0.0
        for _, axes_sommes, cible, _ in prep:
            courant = x.sum(axis=axes_sommes)
            denom = np.where(cible > 0, cible, 1.0)
            pire = max(pire, float(np.max(np.abs(courant - cible) / denom)))
        return pire
