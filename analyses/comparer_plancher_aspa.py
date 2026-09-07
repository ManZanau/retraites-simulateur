"""
Deux voies pour garantir 1 200 €/mois à un retraité :
  A. PLANCHER de pension contributive, automatique et individuel
  B. ASPA ÉTENDUE au même montant, sous condition de ressources du ménage

Même objectif affiché, propriétés opposées. Ce script les compare.

POPULATION ILLUSTRATIVE, NON CALIBRÉE. Les euros produits ici n'ont aucune
valeur de chiffrage : seule compte la structure des écarts entre les deux voies.
"""
import pathlib as _pl, sys as _sys
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parent.parent))

import numpy as np
from modeles.fiscal import Fiscalite

f = Fiscalite.charger()
f.arbitrer(
    "prelevements_sociaux.seuils_rfr.deux_parts.plafond_taux_median",
    39886,
    "valeur basse des deux sources en conflit — maximise l'assiette du taux "
    "plein, donc le retour fiscal ; hypothèse haute sur le rendement",
)
base = f.parametres_aspa_defaut()

GARANTIE_MENSUELLE = 1200.0
GARANTIE = GARANTIE_MENSUELLE * 12

rng = np.random.default_rng(11)
N = 100_000
POIDS = 17_200_000 / N

pension = np.clip(rng.lognormal(7.25, 0.55, N), 100, 25_000) * 12
en_couple = rng.random(N) < 0.55
# Ressources du conjoint et revenus du patrimoine, corrélés à la pension
autres = np.where(en_couple, np.clip(rng.lognormal(7.1, 0.7, N), 0, 30_000) * 12, 0.0)
autres += np.clip(rng.lognormal(5.5, 1.2, N), 0, 40_000)
age = rng.integers(62, 95, N)

# --- Voie A : plancher de pension ------------------------------------------
pension_A = np.maximum(pension, GARANTIE)
cout_A_brut = ((pension_A - pension) * POIDS).sum()

# Un plancher est une pension : imposable et assujettie à la CSG.
retour_A = 0.0
touches_A = pension < GARANTIE
for i in np.flatnonzero(touches_A)[:4000]:   # échantillon pour le coût de calcul
    parts = 2.0 if en_couple[i] else 1.0
    nb = 2 if en_couple[i] else 1
    c = f.cascade(pension_A[i], pension[i], rfr=pension[i] + autres[i],
                  nb_pensionnes=nb, parts=parts)
    # cascade(haut, bas) : les "pertes" sont ici les recettes GAGNÉES par la hausse
    retour_A += c.perte_csg + c.perte_crds_casa + c.perte_ir
echantillon = min(4000, touches_A.sum())
retour_A = retour_A / echantillon * touches_A.sum() * POIDS
cout_A_net = cout_A_brut - retour_A

# --- Voie B : ASPA étendue --------------------------------------------------
facteur = GARANTIE / base.montant_annuel_seul
variantes = {
    "recours 100 %": base.revalorise(facteur),
    "recours 60 %":  base.revalorise(facteur).__class__(
        **{**base.revalorise(facteur).__dict__, "taux_recours": 0.60}),
    "recours 60 %, sans cond. ressources": base.revalorise(facteur).__class__(
        **{**base.revalorise(facteur).__dict__, "taux_recours": 0.60,
           "sous_condition_ressources": False}),
    "recours 100 %, âge abaissé à 62":  base.revalorise(facteur).__class__(
        **{**base.revalorise(facteur).__dict__, "age_minimum": 62}),
}

print("\n" + "=" * 84)
print(f"GARANTIR {GARANTIE_MENSUELLE:,.0f} €/MOIS — DEUX VOIES")
print("=" * 84)
print("\nPopulation illustrative NON CALIBRÉE. Seuls les écarts relatifs comptent.\n")

print(f"{'':<40}{'coût brut':>13}{'retour fiscal':>15}{'coût net':>13}")
print("-" * 84)
print(f"{'A. PLANCHER de pension':<40}{cout_A_brut/1e9:>12,.1f}€"
      f"{retour_A/1e9:>14,.1f}€{cout_A_net/1e9:>12,.1f}€")
print(f"{'   (automatique, individuel, imposable)':<40}")
print()

for nom, p in variantes.items():
    montants = np.array([
        f.aspa_parametree(pension[i], autres[i], en_couple[i], age[i], p)
        for i in range(N)
    ])
    cout = (montants * POIDS).sum()
    beneficiaires = (montants > 0).sum() * POIDS
    print(f"{'B. ASPA — ' + nom:<40}{cout/1e9:>12,.1f}€{0.0:>14,.1f}€{cout/1e9:>12,.1f}€")
    print(f"{'   bénéficiaires : ' + f'{beneficiaires/1e6:,.1f} M':<40}")

print("-" * 84)
beneficiaires_A = touches_A.sum() * POIDS
print(f"\nBénéficiaires du plancher : {beneficiaires_A/1e6:,.1f} M")
print(f"Ratio coût plancher / coût ASPA à recours plein : "
      f"{cout_A_brut / (np.array([f.aspa_parametree(pension[i], autres[i], en_couple[i], age[i], variantes['recours 100 %']) for i in range(N)]) * POIDS).sum():.2f}")
print()
