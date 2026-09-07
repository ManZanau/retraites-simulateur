"""
Rendement net d'un écrêtement de 30 %, par niveau de pension.
Met en évidence la non-monotonie annoncée : l'ASPA annule le rendement en bas,
la fiscalité le rogne en haut.
"""
import pathlib as _pl, sys as _sys
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parent.parent))

from modeles.fiscal import Fiscalite

f = Fiscalite.charger()
plafond_aspa = f._aspa["montants_annuels"]["personne_seule"]

print("\n" + "=" * 86)
print("RENDEMENT NET D'UN ÉCRÊTEMENT DE 30 % — retraité seul, 1 part")
print("=" * 86)
print(f"\nPlafond ASPA personne seule : {plafond_aspa:,.0f} €/an "
      f"({plafond_aspa/12:,.0f} €/mois)\n")
print(f"{'pension/mois':>13}{'éco. brute':>12}{'perte CSG':>11}{'perte IR':>10}"
      f"{'hausse ASPA':>13}{'éco. nette':>12}{'rendement':>11}")
print("-" * 86)

resultats = []
for mensuel in (700, 900, 1_100, 1_300, 1_600, 2_000, 2_500, 3_500, 5_000, 8_000):
    annuel = mensuel * 12
    c = f.cascade(annuel, annuel * 0.7, rfr=annuel * 0.9, nb_pensionnes=1, parts=1.0)
    resultats.append((mensuel, c.taux_de_rendement))
    print(f"{mensuel:>12,}€{c.economie_brute:>11,.0f}€{c.perte_csg:>10,.0f}€"
          f"{c.perte_ir:>9,.0f}€{c.effet_aspa:>12,.0f}€"
          f"{c.economie_nette:>11,.0f}€{c.taux_de_rendement:>10.1%}")

print("-" * 86)
pic = max(resultats, key=lambda r: r[1])
print(f"\nRendement maximal : {pic[1]:.1%} pour une pension de {pic[0]:,} €/mois")
print(f"Rendement au plus bas de l'échelle : {resultats[0][1]:.1%}")
print(f"Rendement au plus haut de l'échelle : {resultats[-1][1]:.1%}")
print("\nLecture : sur les petites pensions, l'ASPA compense intégralement la")
print("baisse — l'économie budgétaire est nulle et le retraité n'est pas touché.")
print("Sur les grosses pensions, le retour fiscal reprend une part croissante.")
print("Le rendement maximal se situe entre les deux.\n")
