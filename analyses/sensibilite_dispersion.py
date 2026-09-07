"""
Coût de la donnée manquante : sensibilité d'un chiffrage à la dispersion.

Les effectifs et la pension moyenne sont EXACTS (EACR 2024). La dispersion
intra-cellule n'est publiée nulle part : c'est le seul paramètre libre.
Ce script mesure à quel point le résultat en dépend.

Nécessite les fichiers EACR dans donnees/.
"""
import pathlib as _pl, sys as _sys
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parent.parent))

import numpy as np

from modeles.fiscal import Fiscalite
from modeles.population_eacr import MENTION_SOURCE, PopulationEACR
from modeles.reforme import MoteurReforme, Scenario

try:
    pop = PopulationEACR.charger()
except FileNotFoundError as e:
    print(f"\n{e}\n"); _sys.exit(0)

f = Fiscalite.charger()
f.arbitrer("prelevements_sociaux.seuils_rfr.deux_parts.plafond_taux_median", 40604,
           "sources divergentes, valeur haute retenue sur décision")
rng = np.random.default_rng(3)

print("\n" + "=" * 80)
print("COÛT DE LA DONNÉE MANQUANTE")
print("Écrêtement de 30 % sur le décile 10, mode marginal, retraités seuls")
print("=" * 80)
print(pop.rapport())
print("\n" + "-" * 80)
print(f"{'sigma':>7}{'D1':>9}{'médiane':>10}{'D9':>10}{'éco. brute':>14}{'éco. nette':>14}{'rendt':>8}")
print("-" * 80)

res = []
for sigma in (0.35, 0.45, 0.55, 0.65, 0.75):
    p, poids, _ = pop.tirer(150_000, sigma_intra=sigma, graine=1)
    r = MoteurReforme(p, poids).appliquer(
        Scenario("ecret_D10", variation_par_decile={10: -0.30}))
    idx = np.flatnonzero(r.pensions_avant != r.pensions_apres)
    ech = rng.choice(idx, min(3000, len(idx)), replace=False)
    brute = nette = 0.0
    for i in ech:
        c = f.cascade(r.pensions_avant[i] * 12, r.pensions_apres[i] * 12,
                      rfr=r.pensions_avant[i] * 12, nb_pensionnes=1, parts=1.0)
        brute += c.economie_brute; nette += c.economie_nette
    fac = len(idx) / len(ech) * (pop.effectif_total / len(p))
    brute *= fac; nette *= fac
    q = np.percentile(p, [10, 50, 90])
    res.append(nette)
    print(f"{sigma:>7.2f}{q[0]:>8.0f}€{q[1]:>9.0f}€{q[2]:>9.0f}€"
          f"{brute/1e9:>12,.1f}Md{nette/1e9:>12,.1f}Md{nette/brute:>7.0%}")

print("-" * 80)
print(f"\nÉconomie nette : de {min(res)/1e9:,.1f} à {max(res)/1e9:,.1f} Md€ "
      f"— rapport x{max(res)/min(res):.1f}")
print("""
Le seul paramètre libre suffit à faire varier le chiffrage d'un facteur trois.
Aucun chiffrage d'écrêtement ciblé n'est publiable tant que la dispersion n'est
pas fixée sur données observées (Panorama Drees, ou EIR via le CASD).
""")
print(MENTION_SOURCE)
