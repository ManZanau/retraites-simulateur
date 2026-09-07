"""Points de contrôle du fichier de baselines. Exécuter : python3 test_baseline.py"""
import pathlib as _pl, sys as _sys
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parent.parent))

from modeles.baseline import Baselines

b = Baselines.charger()
echecs = []


def verifier(nom, condition, detail=""):
    statut = "OK  " if condition else "ECHEC"
    print(f"  [{statut}] {nom}" + (f"  — {detail}" if detail else ""))
    if not condition:
        echecs.append(nom)


print("\n" + "=" * 70)
print("POINTS DE CONTROLE — BASELINES LEGISLATIFS RETRAITE")
print("=" * 70)

print("\n1. Convergence à 64 ans pour les générations tardives")
verifier(
    "B0[1975] == B1[1975] == 768",
    b.age_legal(1975, "B0_reforme_2023") == b.age_legal(1975, "B1_suspension") == 768,
    f"B0={b.age_legal(1975, 'B0_reforme_2023')}, B1={b.age_legal(1975, 'B1_suspension')}",
)

print("\n2. Neutralité pour les générations antérieures à 1964")
for g in (1960, 1962, 1963):
    verifier(
        f"génération {g} inchangée",
        b.age_legal(g, "B0_reforme_2023") == b.age_legal(g, "B1_suspension"),
        f"{b.age_legal(g, 'B1_suspension')} mois",
    )

print("\n3. Gain de la suspension, génération par génération")
print(f"  {'gén.':<8}{'âge B0':>10}{'âge B1':>10}{'gain':>8}{'durée B0':>11}{'durée B1':>11}{'gain':>7}")
for g in range(1963, 1971):
    c = b.comparer(g)
    print(
        f"  {g:<8}{c['age_B0_mois']:>10}{c['age_B1_mois']:>10}{c['gain_age_mois']:>8}"
        f"{c['duree_B0']:>11}{c['duree_B1']:>11}{c['gain_duree_trimestres']:>7}"
    )

print("\n4. Générations 1966-1968 : gain d'âge sans gain de durée")
for g in (1966, 1967, 1968):
    c = b.comparer(g)
    verifier(
        f"génération {g} : -3 mois, 0 trimestre",
        c["gain_age_mois"] == 3 and c["gain_duree_trimestres"] == 0,
        f"gain âge {c['gain_age_mois']} mois, gain durée {c['gain_duree_trimestres']} trim.",
    )

print("\n5. Bornes infra-annuelles de la génération 1965")
t1 = b.parametres(1965, "B1_suspension", trimestre=1)
t3 = b.parametres(1965, "B1_suspension", trimestre=3)
verifier("1965 T1 gelé à 62 ans 9 mois", t1.age_legal_mois == 753, t1.age_legal_texte)
verifier("1965 T3 relevé à 63 ans", t3.age_legal_mois == 756, t3.age_legal_texte)
verifier("1965 T1 : 170 trimestres", t1.duree_assurance_trimestres == 170)
verifier("1965 T3 : 171 trimestres", t3.duree_assurance_trimestres == 171)

print("\n6. Monotonie de l'âge légal")
for nom in ("B0_reforme_2023", "B1_suspension"):
    ages = [b.age_legal(g, nom) for g in range(1955, 1980)]
    verifier(f"{nom} non décroissant", all(x <= y for x, y in zip(ages, ages[1:])))

print("\n7. Plafond de durée d'assurance")
durees = [
    b.duree(g, nom)
    for g in range(1955, 1980)
    for nom in ("B0_reforme_2023", "B1_suspension")
]
verifier("durée maximale == 172 trimestres", max(durees) == 172, f"max observé {max(durees)}")

print("\n8. Sélection automatique du baseline par date d'effet")
cas = [
    ("2026-08-31", "B0_reforme_2023"),
    ("2026-09-01", "B1_suspension"),
    ("2027-12-31", "B1_suspension"),
    ("2028-01-01", "B2_post_2028"),
]
for date, attendu in cas:
    obtenu = b.baseline_applicable(date)
    verifier(f"pension au {date}", obtenu == attendu, obtenu)

print("\n9. Héritage B2 depuis B1")
verifier(
    "B2 reprend la grille B1 en mode retour_progressif",
    b.age_legal(1966, "B2_post_2028") == b.age_legal(1966, "B1_suspension"),
)

print("\n" + "=" * 70)
if echecs:
    print(f"{len(echecs)} ECHEC(S) : " + ", ".join(echecs))
else:
    print("Tous les points de contrôle sont satisfaits.")
print("=" * 70 + "\n")

print("Exemple de sortie détaillée :\n")
print(b.parametres(1964, "B1_suspension"))
print()
print(b.parametres(1964, "B0_reforme_2023"))


# =====================================================================
# 10-12. Modes de sortie de suspension (B2)
# =====================================================================
print("\n10. Modes de sortie disponibles")
modes = b.modes_disponibles()
verifier("trois modes implémentés", len(modes) == 3, ", ".join(modes))

print("\n11. Cohérence des trois modes")
verifier(
    "rattrapage_abrupt restitue exactement B0",
    all(
        b.age_legal(g, "B2_post_2028", mode="rattrapage_abrupt")
        == b.age_legal(g, "B0_reforme_2023")
        and b.duree(g, "B2_post_2028", mode="rattrapage_abrupt")
        == b.duree(g, "B0_reforme_2023")
        for g in range(1960, 1980)
    ),
)
verifier(
    "retour_progressif restitue exactement B1",
    all(
        b.age_legal(g, "B2_post_2028", mode="retour_progressif")
        == b.age_legal(g, "B1_suspension")
        for g in range(1960, 1980)
    ),
)
verifier(
    "ordonnancement gel <= progressif <= rattrapage",
    all(
        b.age_legal(g, "B2_post_2028", mode="gel_perenne")
        <= b.age_legal(g, "B2_post_2028", mode="retour_progressif")
        <= b.age_legal(g, "B2_post_2028", mode="rattrapage_abrupt")
        for g in range(1960, 1980)
    ),
)
verifier(
    "gel_perenne plafonne à 62 ans 9 mois",
    max(b.age_legal(g, "B2_post_2028", mode="gel_perenne") for g in range(1964, 1990))
    == 753,
)

print("\n12. Fourchette post-2028 par génération")
print(f"  {'gén.':<7}{'gel':>14}{'progressif':>15}{'rattrapage':>15}{'amplitude':>12}")
for g in (1965, 1967, 1969, 1975):
    f = b.fourchette_post_2028(g)
    print(
        f"  {g:<7}{f['gel_perenne']['age_legal_texte']:>14}"
        f"{f['retour_progressif']['age_legal_texte']:>15}"
        f"{f['rattrapage_abrupt']['age_legal_texte']:>15}"
        f"{str(f['amplitude_mois']) + ' mois':>12}"
    )

print("\n" + "=" * 70)
print("BILAN FINAL : " + (f"{len(echecs)} ECHEC(S)" if echecs else "tout est vert"))
print("=" * 70 + "\n")
