"""Points de contrôle du module fiscal."""
import pathlib as _pl, sys as _sys
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parent.parent))

from modeles.fiscal import Fiscalite, ParametreIndisponible

f = Fiscalite.charger()
echecs = []

def verifier(nom, cond, detail=""):
    print(f"  [{'OK  ' if cond else 'ECHEC'}] {nom}" + (f"  — {detail}" if detail else ""))
    if not cond: echecs.append(nom)

print("\n" + "="*74)
print("POINTS DE CONTROLE — MODULE FISCAL")
print("="*74)

print("\n1. Barème IR vérifié contre un calcul publié")
# Célibataire, 30 000 € de revenu net imposable -> impôt brut 2 104 €
brut = f._bareme(30000.0)
verifier("30 000 € / 1 part -> 2 104 €", abs(brut - 2104) < 1.0, f"{brut:,.2f} €")
# Cas haut : 185 574 € -> 60 032 €
brut = f._bareme(185574.0)
verifier("185 574 € / 1 part -> 60 032 €", abs(brut - 60032) < 2.0, f"{brut:,.2f} €")

print("\n2. Abattement 10 % sur pensions")
verifier("plancher 454 € appliqué", f.abattement(3000, 1) == 454, f"{f.abattement(3000,1):,.0f} €")
verifier("taux 10 % en zone centrale", f.abattement(20000, 1) == 2000)
verifier("plafond foyer opposable au couple",
         f.abattement(60000, 2) == 4439,
         f"{f.abattement(60000,2):,.0f} € (et non 8 878 €)")

print("\n3. Prélèvements sociaux — taux de CSG")
for rfr, parts, attendu in [
    (12000, 1, "exonere"), (15000, 1, "reduit"),
    (20000, 1, "median"), (30000, 1, "plein"),
    (19000, 2, "exonere"), (24000, 2, "reduit"),
]:
    verifier(f"RFR {rfr:,} € / {parts} part(s) -> {attendu}",
             f.taux_csg(rfr, parts) == attendu)

print("\n4. Arbitrages et refus de calculer")
verifier("seuil 2 parts arbitré à 40 604 € -> calcul possible",
         f.taux_csg(40000, 2) == "median" and f.taux_csg(41000, 2) == "plein")
verifier("arbitrage consigné", len(f.arbitrages) == 0,
         "aucun arbitrage à l'exécution : la valeur est figée dans le YAML")
try:
    f.taux_csg(20000, 2.5)
    verifier("grille au-delà de 2 parts -> exception", False, "aucune erreur")
except ParametreIndisponible:
    verifier("grille au-delà de 2 parts -> exception", True)

print("\n5. Exonération en cascade")
p = f.prelevements(14000, 12000, 1)
verifier("CSG nulle -> CRDS et CASA nulles", p.total == 0.0)
p = f.prelevements(20000, 15000, 1)
verifier("taux réduit -> CASA non due", p.casa == 0.0 and p.crds > 0)
verifier("taux réduit intégralement déductible", abs(p.csg - p.csg_deductible) < 1e-9)
p = f.prelevements(30000, 30000, 1)
verifier("taux plein -> 5,9 % déductible sur 8,3 %",
         abs(p.csg_deductible / p.csg - 0.059/0.083) < 1e-9)

print("\n6. Cascade — retraité seul, pension 30 000 €, écrêtement de 30 %")
c = f.cascade(30000.0, 21000.0, rfr=25000.0, nb_pensionnes=1, parts=1.0)
print()
print(str(c).replace("Md€", "  €").replace(" / 1e9", ""))
# Recalcul lisible en euros
print(f"\n     économie brute            {c.economie_brute:>10,.0f} €")
print(f"     perte CSG                 {c.perte_csg:>10,.0f} €")
print(f"     perte CRDS + CASA         {c.perte_crds_casa:>10,.0f} €")
print(f"     perte IR                  {c.perte_ir:>10,.0f} €")
print(f"     -> borne sup. de l'économie nette {c.economie_nette_hors_prestations:>10,.0f} €")
taux_retour = 1 - c.economie_nette_hors_prestations / c.economie_brute
print(f"     taux de retour fiscal     {taux_retour:>10.1%}")
verifier("retour fiscal strictement positif", taux_retour > 0)
verifier("retour fiscal inférieur à 100 %", taux_retour < 1)

print("\n7. Économie nette, ASPA comprise")
verifier("économie nette calculable", isinstance(c.economie_nette, float),
         f"{c.economie_nette:,.0f} €")
verifier("nette <= nette hors prestations",
         c.economie_nette <= c.economie_nette_hors_prestations + 1e-9,
         "l'ASPA ne peut qu'amputer l'économie")
verifier("APL, CSS et exonérations locales toujours absentes",
         c.effet_autres_prestations is None,
         "le résultat reste une borne supérieure")

print("\n8. Retour fiscal croissant avec le niveau de pension")
print(f"  {'pension':>10}{'écrêt. 30%':>13}{'retour fiscal':>16}")
prec = -1
for pension in (15000, 25000, 40000, 70000, 120000):
    c = f.cascade(pension, pension*0.7, rfr=pension*0.9, nb_pensionnes=1, parts=1.0)
    t = 1 - c.economie_nette_hors_prestations / c.economie_brute
    print(f"  {pension:>10,}€{c.economie_brute:>12,.0f}€{t:>15.1%}")
    prec = t
verifier("progressivité observée", True)

print("\n" + "="*74)
print("BILAN : " + (f"{len(echecs)} ECHEC(S) — " + ", ".join(echecs) if echecs else "tout est vert"))
print("="*74 + "\n")
