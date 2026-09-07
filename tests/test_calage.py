"""Points de contrôle du moteur de calage. Exécuter : python3 test_calage.py"""
import pathlib as _pl, sys as _sys
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parent.parent))

import numpy as np

from modeles.calage import Calage, Marge

echecs = []


def verifier(nom, condition, detail=""):
    print(f"  [{'OK  ' if condition else 'ECHEC'}] {nom}" + (f"  — {detail}" if detail else ""))
    if not condition:
        echecs.append(nom)


print("\n" + "=" * 72)
print("POINTS DE CONTROLE — MOTEUR DE CALAGE IPF")
print("=" * 72)

# -----------------------------------------------------------------------
print("\n1. Solution analytique connue (indépendance)")
# Avec deux marges univariées et un seed uniforme, la solution exacte est
# le produit des marges divisé par le total.
c = Calage({"sexe": 2, "regime": 3})
c.ajouter(Marge("sexe", ("sexe",), [60.0, 40.0], source="test"))
c.ajouter(Marge("regime", ("regime",), [50.0, 30.0, 20.0], source="test"))
x, d = c.executer()
attendu = np.outer([60.0, 40.0], [50.0, 30.0, 20.0]) / 100.0
verifier("produit des marges retrouvé", np.allclose(x, attendu), f"écart {np.abs(x - attendu).max():.2e}")
verifier("convergence immédiate", d.iterations == 1 and d.converge)

# -----------------------------------------------------------------------
print("\n2. Dimensions déclarées dans le désordre")
# La marge porte sur (regime, sexe) alors que le tableau est (sexe, regime).
c = Calage({"sexe": 2, "regime": 3})
croisee = np.array([[30.0, 20.0], [18.0, 12.0], [12.0, 8.0]])  # regime x sexe
c.ajouter(Marge("croisee", ("regime", "sexe"), croisee, source="test"))
x, d = c.executer()
verifier("marge croisée respectée malgré l'ordre inversé", np.allclose(x.T, croisee))
verifier("total conservé", np.isclose(x.sum(), 100.0), f"{x.sum():.4f}")

# -----------------------------------------------------------------------
print("\n3. Cas tridimensionnel avec marges croisées")
rng = np.random.default_rng(42)
vrai = rng.gamma(2.0, 1.0, size=(4, 3, 5))
vrai *= 1_000_000 / vrai.sum()
c = Calage({"generation": 4, "sexe": 3, "tranche": 5})
c.ajouter(Marge("gen_sexe", ("generation", "sexe"), vrai.sum(axis=2), source="test"))
c.ajouter(Marge("sexe_tranche", ("sexe", "tranche"), vrai.sum(axis=0), source="test"))
c.ajouter(Marge("generation", ("generation",), vrai.sum(axis=(1, 2)), source="test"))
x, d = c.executer()
verifier("convergence", d.converge, f"{d.iterations} itérations")
verifier("marge gen×sexe exacte", np.allclose(x.sum(axis=2), vrai.sum(axis=2)))
verifier("marge sexe×tranche exacte", np.allclose(x.sum(axis=0), vrai.sum(axis=0)))
verifier("total exact", np.isclose(x.sum(), 1_000_000))

# -----------------------------------------------------------------------
print("\n4. Préservation des odds-ratios du seed")
# L'IPF conserve les rapports de cotes de la structure a priori.
seed = np.array([[4.0, 1.0], [1.0, 4.0]])
c = Calage({"a": 2, "b": 2}, seed=seed)
c.ajouter(Marge("a", ("a",), [70.0, 30.0], source="test"))
c.ajouter(Marge("b", ("b",), [60.0, 40.0], source="test"))
x, _ = c.executer()
or_seed = (seed[0, 0] * seed[1, 1]) / (seed[0, 1] * seed[1, 0])
or_res = (x[0, 0] * x[1, 1]) / (x[0, 1] * x[1, 0])
verifier("odds-ratio conservé", np.isclose(or_seed, or_res), f"seed {or_seed:.3f} / résultat {or_res:.3f}")
verifier("seed uniforme donnerait un OR de 1", not np.isclose(or_res, 1.0))

# -----------------------------------------------------------------------
print("\n5. Détection des incohérences entre sources")
c = Calage({"a": 2, "b": 2})
c.ajouter(Marge("source_1", ("a",), [50.0, 50.0], source="EACR"))
c.ajouter(Marge("source_2", ("b",), [60.0, 45.0], source="Panorama"))
try:
    c.executer()
    verifier("totaux divergents rejetés", False, "aucune erreur levée")
except ValueError as e:
    verifier("totaux divergents rejetés", "incohérents" in str(e))
    print(f"         -> {str(e)[:100]}...")

# -----------------------------------------------------------------------
print("\n6. Garde-fous de saisie")
for libelle, action in [
    (
        "dimension inconnue refusée",
        lambda: Calage({"a": 2}).ajouter(Marge("m", ("z",), [1.0, 1.0], source="t")),
    ),
    (
        "forme incompatible refusée",
        lambda: Calage({"a": 2}).ajouter(Marge("m", ("a",), [1.0, 1.0, 1.0], source="t")),
    ),
    (
        "valeurs négatives refusées",
        lambda: Marge("m", ("a",), [-1.0, 2.0], source="t"),
    ),
    (
        "seed de mauvaise forme refusé",
        lambda: Calage({"a": 2, "b": 2}, seed=np.ones((3, 3))),
    ),
]:
    try:
        action()
        verifier(libelle, False, "aucune erreur levée")
    except ValueError:
        verifier(libelle, True)

# -----------------------------------------------------------------------
print("\n7. Traçabilité des marges provisoires")
c = Calage({"a": 2, "b": 2})
c.ajouter(Marge("solide", ("a",), [50.0, 50.0], source="EACR 2024 t.A"))
c.ajouter(Marge("bancale", ("b",), [70.0, 30.0], source="estimation", provisoire=True))
_, d = c.executer()
verifier("marge provisoire signalée dans le diagnostic", d.marges_provisoires == ["bancale"])
print("\n" + str(d).replace("\n", "\n  "))

# -----------------------------------------------------------------------
print("\n8. Robustesse aux zéros structurels")
# Une case vide dans le seed doit le rester : un régime qui n'existe pas
# pour une génération ne doit pas se voir attribuer d'effectif.
seed = np.ones((3, 3))
seed[0, 2] = 0.0  # combinaison impossible
c = Calage({"generation": 3, "regime": 3}, seed=seed)
c.ajouter(Marge("gen", ("generation",), [30.0, 40.0, 30.0], source="test"))
c.ajouter(Marge("reg", ("regime",), [40.0, 35.0, 25.0], source="test"))
x, d = c.executer()
verifier("zéro structurel préservé", x[0, 2] == 0.0)
verifier("marges tout de même respectées", d.converge, f"{d.iterations} itérations")

print("\n" + "=" * 72)
print("BILAN : " + (f"{len(echecs)} ECHEC(S) — " + ", ".join(echecs) if echecs else "tout est vert"))
print("=" * 72 + "\n")
