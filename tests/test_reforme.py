"""Points de contrôle du moteur de réforme. Exécuter : python3 test_reforme.py"""
import pathlib as _pl, sys as _sys
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parent.parent))

import numpy as np

from modeles.reforme import MoteurReforme, Scenario

echecs = []


def verifier(nom, cond, detail=""):
    print(f"  [{'OK  ' if cond else 'ECHEC'}] {nom}" + (f"  — {detail}" if detail else ""))
    if not cond:
        echecs.append(nom)


# ---------------------------------------------------------------------------
# Population illustrative — NON CALIBRÉE.
# Log-normale calée à la louche sur l'ordre de grandeur des pensions
# françaises. Sert uniquement à exercer le moteur : aucun chiffre produit
# ci-dessous n'a de valeur de chiffrage.
# ---------------------------------------------------------------------------
rng = np.random.default_rng(7)
N = 200_000
pensions = np.clip(rng.lognormal(mean=7.25, sigma=0.55, size=N), 100, 25_000)
poids = np.full(N, 17_200_000 / N)

caisses = ["cnav", "agirc_arrco", "fonction_publique"]
parts = rng.dirichlet([3.0, 2.0, 1.0], size=N)

m = MoteurReforme(pensions, poids, parts_caisses=parts, noms_caisses=caisses)

print("\n" + "=" * 74)
print("POINTS DE CONTROLE — MOTEUR DE REFORME")
print("=" * 74)
print("\nPopulation illustrative NON CALIBRÉE — aucun chiffre n'est un chiffrage.")
print(f"  effectif simulé : {N:,} individus, pondérés à {poids.sum():,.0f} retraités")
print("  seuils de décile de référence (€/mois) :")
print("   " + "  ".join(f"D{i+1}:{s:,.0f}" for i, s in enumerate(m.seuils)))

# ---------------------------------------------------------------------------
print("\n1. Scénario neutre")
r = m.appliquer(Scenario("neutre"))
verifier("aucune variation", np.allclose(r.pensions_apres, pensions))
verifier("économie nulle", abs(r.economie_brute_annuelle) < 1e-6)
verifier("aucune inversion", r.inversions == 0)

# ---------------------------------------------------------------------------
print("\n2. Mode marginal : préservation de l'ordre")
sc = Scenario("ecretement_haut", mode="marginal", variation_par_decile={9: -0.10, 10: -0.30})
r_marg = m.appliquer(sc)
verifier("aucune inversion de classement", r_marg.inversions == 0)
verifier("les déciles bas sont épargnés", 
         all(abs(l["variation_relative"]) < 1e-12 for l in r_marg.par_decile if l["decile"] <= 8))
verifier("économie strictement positive", r_marg.economie_brute_annuelle > 0,
         f"{r_marg.economie_brute_annuelle/1e9:,.1f} Md€")

# ---------------------------------------------------------------------------
print("\n3. Mode moyen : le défaut se matérialise")
r_moy = m.appliquer(
    Scenario("ecretement_haut", mode="moyen", variation_par_decile={9: -0.10, 10: -0.30})
)
verifier("inversions de classement détectées", r_moy.inversions > 0,
         f"{r_moy.taux_inversion:.2%} des paires")
verifier("économie supérieure au mode marginal", 
         r_moy.economie_brute_annuelle > r_marg.economie_brute_annuelle,
         f"{r_moy.economie_brute_annuelle/1e9:,.1f} contre "
         f"{r_marg.economie_brute_annuelle/1e9:,.1f} Md€")

# Illustration concrète de l'effet de seuil
seuil_d9 = m.seuils[8]
juste_sous = np.argmin(np.abs(pensions - seuil_d9 * 0.999))
juste_sur = np.argmin(np.abs(pensions - seuil_d9 * 1.001))
print(f"\n     Effet de seuil au passage D9 -> D10 ({seuil_d9:,.0f} €/mois) :")
print(f"       avant réforme : {pensions[juste_sous]:,.0f} €  <  {pensions[juste_sur]:,.0f} €")
print(f"       mode moyen    : {r_moy.pensions_apres[juste_sous]:,.0f} €  vs  "
      f"{r_moy.pensions_apres[juste_sur]:,.0f} €   <-- inversion")
print(f"       mode marginal : {r_marg.pensions_apres[juste_sous]:,.0f} €  <  "
      f"{r_marg.pensions_apres[juste_sur]:,.0f} €   ordre préservé")

# ---------------------------------------------------------------------------
print("\n4. Plafond dur")
r = m.appliquer(Scenario("plafond_4500", plafond={"seuil": 4500.0, "taux": 1.0}))
verifier("aucune pension au-dessus du plafond", r.pensions_apres.max() <= 4500.0 + 1e-9,
         f"max {r.pensions_apres.max():,.0f} €")
verifier("les pensions sous le plafond sont intactes",
         np.allclose(r.pensions_apres[pensions <= 4500], pensions[pensions <= 4500]))
verifier("aucune inversion", r.inversions == 0)

print("\n5. Plancher")
r = m.appliquer(Scenario("plancher_1200", plancher={"seuil": 1200.0}))
verifier("aucune pension sous le plancher", r.pensions_apres.min() >= 1200.0 - 1e-9)
verifier("coût, non économie", r.economie_brute_annuelle < 0,
         f"{-r.economie_brute_annuelle/1e9:,.1f} Md€ de dépense supplémentaire")

print("\n6. Plancher et plafond combinés")
r = m.appliquer(
    Scenario("tunnel", plafond={"seuil": 4000.0, "taux": 1.0}, plancher={"seuil": 1000.0})
)
verifier("distribution bornée des deux côtés",
         r.pensions_apres.min() >= 1000.0 - 1e-9 and r.pensions_apres.max() <= 4000.0 + 1e-9,
         f"[{r.pensions_apres.min():,.0f} ; {r.pensions_apres.max():,.0f}]")

print("\n7. Le plancher prime sur l'écrêtement")
# Un plafond sous le plancher doit être rejeté à la construction.
try:
    Scenario("incoherent", plafond={"seuil": 900.0}, plancher={"seuil": 1500.0})
    verifier("scénario incohérent rejeté", False, "aucune erreur levée")
except ValueError:
    verifier("scénario incohérent rejeté", True)

print("\n8. Écrêtement partiel (taux < 1)")
r = m.appliquer(Scenario("ecretement_50", plafond={"seuil": 3000.0, "taux": 0.5}))
i = np.argmax(pensions)
attendu = 3000.0 + 0.5 * (pensions[i] - 3000.0)
verifier("fraction au-dessus du seuil réduite de moitié",
         np.isclose(r.pensions_apres[i], attendu),
         f"{pensions[i]:,.0f} -> {r.pensions_apres[i]:,.0f} €")

print("\n9. Imputation entre caisses")
r = m.appliquer(Scenario("ecretement_haut", variation_par_decile={10: -0.30}))
total_caisses = sum(r.delta_par_caisse.values())
verifier("somme des imputations = économie totale",
         np.isclose(total_caisses, r.economie_brute_annuelle, rtol=1e-9),
         f"{total_caisses/1e9:,.2f} Md€")
for nom, v in r.delta_par_caisse.items():
    print(f"       {nom:<20} {v/1e9:>8,.2f} Md€")

print("\n10. Hausse des déciles bas")
r = m.appliquer(Scenario("revalo_bas", variation_par_decile={1: 0.15, 2: 0.10}))
verifier("coût positif", r.economie_brute_annuelle < 0,
         f"{-r.economie_brute_annuelle/1e9:,.1f} Md€")
verifier("aucune inversion en mode marginal", r.inversions == 0)

# ---------------------------------------------------------------------------
print("\n11. Ventilation par décile — écrêtement D9/D10 en mode marginal")
print(f"  {'déc.':<6}{'pension avant':>16}{'après':>12}{'variation':>12}{'économie/an':>16}")
for l in r_marg.par_decile:
    print(f"  D{l['decile']:<5}{l['pension_moyenne_avant']:>15,.0f}€"
          f"{l['pension_moyenne_apres']:>11,.0f}€"
          f"{l['variation_relative']:>11.1%}"
          f"{l['economie_annuelle']/1e9:>14,.2f} Md€")

print("\n" + "=" * 74)
print("BILAN : " + (f"{len(echecs)} ECHEC(S) — " + ", ".join(echecs) if echecs else "tout est vert"))
print("=" * 74 + "\n")
