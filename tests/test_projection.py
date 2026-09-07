"""Points de contrôle du moteur de projection."""
import pathlib as _pl, sys as _sys
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parent.parent))

import numpy as np
from modeles.baseline import Baselines
from modeles.projection import (Cohorte, ComportementDepart, MoteurProjection,
                        ReglesIndexation, TableMortalite)

echecs = []
def verifier(nom, cond, detail=""):
    print(f"  [{'OK  ' if cond else 'ECHEC'}] {nom}" + (f"  — {detail}" if detail else ""))
    if not cond: echecs.append(nom)

b = Baselines.charger()
mort = TableMortalite()

print("\n" + "="*78)
print("POINTS DE CONTROLE — MOTEUR DE PROJECTION")
print("="*78)

print("\n1. Vraisemblance de la table de mortalité (substitut paramétrique)")
# Cibles INSEE approximatives pour la France : ~19,7 ans (H) et ~23,4 ans (F).
for sexe, cible in [("homme", 19.7), ("femme", 23.4)]:
    e = mort.esperance_de_vie(65, sexe)
    ecart = (e - cible) / cible
    statut = "OK  " if abs(ecart) < 0.05 else "CALIB"
    print(f"  [{statut}] espérance de vie à 65 ans, {sexe} — {e:.1f} ans "
          f"vs cible {cible} ({ecart:+.1%})")
if True:
    print("         -> table paramétrique NON CALIBRÉE : sous-estime la longévité,")
    print("            donc sous-estime les effectifs et la masse des pensions.")
verifier("mortalité croissante avec l'âge",
         all(mort.qx(a, "homme") < mort.qx(a+1, "homme") for a in range(60, 100)))
verifier("surmortalité masculine", mort.qx(75,"homme") > mort.qx(75,"femme"))

print("\n2. Garde-fous")
try:
    ComportementDepart(etalement={0: 0.5, 1: 0.3})
    verifier("étalement ne sommant pas à 1 rejeté", False)
except ValueError:
    verifier("étalement ne sommant pas à 1 rejeté", True)

# --- population illustrative ------------------------------------------------
INFLATION = {a: 0.018 for a in range(2026, 2050)}
SALAIRES  = {a: 0.028 for a in range(2026, 2050)}

def population():
    c = []
    for g in range(1935, 1990):
        age = 2026 - g
        eff = 260_000 * np.exp(-((age-70)/28)**2) if age >= 20 else 0
        for sexe, part in (("femme", 0.52), ("homme", 0.48)):
            liquide = age >= 64
            c.append(Cohorte(
                generation=g, sexe=sexe,
                effectif_non_liquide=0.0 if liquide else eff*part,
                effectif_retraite=eff*part if liquide else 0.0,
                pension_base=950.0, pension_complementaire=560.0,
            ))
    return c

def moteur(idx):
    return MoteurProjection(population(), b, mort, idx)

print("\n3. Conservation : les effectifs ne peuvent pas augmenter sans liquidations")
idx = ReglesIndexation(INFLATION, SALAIRES)
m = moteur(idx)
r = m.projeter(2026, 2046)
verifier("décès strictement positifs chaque année", all(x.deces_retraites > 0 for x in r))
verifier("liquidations positives", sum(x.nouveaux_liquidants for x in r) > 0)
verifier("pension moyenne strictement positive", all(x.pension_moyenne_mensuelle > 0 for x in r))

print("\n4. Sensibilité au baseline législatif")
res = {}
for nom, mode in [("B0 (réforme 2023)", None), ("B1 (suspension)", None),
                  ("B2 / gel pérenne", "gel_perenne")]:
    bl = "B0_reforme_2023" if nom.startswith("B0") else ("B1_suspension" if nom.startswith("B1") else "B2_post_2028")
    rr = moteur(idx).projeter(2026, 2046)
    res[nom] = rr[-1].masse_pensions_annuelle
    rr2 = moteur(idx).projeter(2026, 2046, baseline=bl, mode=mode)
    res[nom] = rr2[-1].masse_pensions_annuelle
print(f"  {'scénario':<22}{'masse 2046':>16}")
for nom, v in res.items():
    print(f"  {nom:<22}{v/1e9:>15,.1f} Md€")
verifier("le gel pérenne coûte plus cher que la réforme 2023",
         res["B2 / gel pérenne"] > res["B0 (réforme 2023)"],
         f"écart {(res['B2 / gel pérenne']-res['B0 (réforme 2023)'])/1e9:,.1f} Md€")

print("\n5. Sensibilité à la règle d'indexation — l'effet dominant")
scenarios = {
    "indexation inflation":        ReglesIndexation(INFLATION, SALAIRES),
    "sous-indexation -1 pt":       ReglesIndexation(INFLATION, SALAIRES, sous_indexation_base=0.01, sous_indexation_complementaire=0.01),
    "gel des complémentaires":     ReglesIndexation(INFLATION, SALAIRES, regle_complementaire="gel"),
    "gel total":                   ReglesIndexation(INFLATION, SALAIRES, regle_base="gel", regle_complementaire="gel"),
    "indexation sur salaires":     ReglesIndexation(INFLATION, SALAIRES, regle_base="salaires", regle_complementaire="salaires"),
}
ref = None
print(f"  {'scénario':<28}{'masse 2046':>15}{'écart / référence':>20}")
for nom, ix in scenarios.items():
    v = moteur(ix).projeter(2026, 2046)[-1].masse_pensions_annuelle
    if ref is None: ref = v
    print(f"  {nom:<28}{v/1e9:>14,.1f} Md€{(v/ref-1):>19.1%}")

print("\n6. Horizons demandés — scénario central")
h = MoteurProjection.aux_horizons(moteur(idx).projeter(2026, 2046), base=2026)
print(f"  {'horizon':>8}{'année':>7}{'retraités':>13}{'masse':>14}{'évol. masse':>14}")
for x in h:
    print(f"  {x['horizon']:>7}an{x['annee']:>7}{x['effectif']/1e6:>12,.1f}M"
          f"{x['masse']/1e9:>12,.0f}Md{x['evol_masse']:>13.1%}")
verifier("six horizons produits", len(h) == 6)

print("\n" + "="*78)
print("BILAN : " + (f"{len(echecs)} ECHEC(S) — " + ", ".join(echecs) if echecs else "tout est vert"))
print("="*78 + "\n")
