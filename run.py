#!/usr/bin/env python3
"""
Point d'entrée du simulateur de dépense publique — volet retraites.

    python run.py              vérifie que tout fonctionne
    python run.py analyses     lance les analyses
    python run.py app          ouvre le simulateur dans le navigateur
    python run.py donnees      contrôle la présence des fichiers EACR

Aucune connaissance de Python n'est nécessaire pour la première commande :
elle affiche un rapport lisible et signale ce qui manque.
"""

import runpy
import subprocess
import sys
import webbrowser
from pathlib import Path

RACINE = Path(__file__).resolve().parent
sys.path.insert(0, str(RACINE))

VERT, ROUGE, JAUNE, GRAS, FIN = "\033[32m", "\033[31m", "\033[33m", "\033[1m", "\033[0m"

TESTS = [
    ("Baselines législatifs", "tests/test_baseline.py"),
    ("Moteur de calage", "tests/test_calage.py"),
    ("Moteur de réforme", "tests/test_reforme.py"),
    ("Module fiscal", "tests/test_fiscal.py"),
    ("Moteur de projection", "tests/test_projection.py"),
    ("Application web", "tests/test_app.py"),
]

ANALYSES = [
    ("Rendement d'une coupe par niveau de pension", "analyses/courbe_rendement.py"),
    ("Plancher de pension contre ASPA étendue", "analyses/comparer_plancher_aspa.py"),
    ("Coût de la donnée manquante", "analyses/sensibilite_dispersion.py"),
]


def titre(t):
    print(f"\n{GRAS}{'=' * 74}\n{t}\n{'=' * 74}{FIN}")


def verifier_dependances() -> bool:
    manquants = []
    for mod, paquet in [("yaml", "pyyaml"), ("numpy", "numpy"),
                        ("pandas", "pandas"), ("openpyxl", "openpyxl"),
                        ("scipy", "scipy")]:
        try:
            __import__(mod)
        except ImportError:
            manquants.append(paquet)
    if manquants:
        print(f"{ROUGE}Bibliothèques manquantes : {', '.join(manquants)}{FIN}")
        print(f"\nInstallez-les avec :\n\n    pip install {' '.join(manquants)}\n")
        return False
    return True


def etat_donnees() -> bool:
    from modeles import chemins
    presents = [f for f in (chemins.EACR_PART1, chemins.EACR_PART2) if f.exists()]
    titre("FICHIERS DE DONNÉES")
    if len(presents) == 2:
        for f in presents:
            print(f"  {VERT}présent{FIN}  {f.name}  ({f.stat().st_size / 1e6:.0f} Mo)")
        print(f"\n  Les chiffrages calés sur données réelles sont disponibles.")
        return True
    print(f"  {JAUNE}Les fichiers EACR ne sont pas dans donnees/{FIN}")
    print("\n  Le simulateur fonctionne quand même : tous les calculs par foyer,")
    print("  les barèmes et les tests tournent sans ces fichiers. Seuls les")
    print("  chiffrages nationaux les demandent.")
    print(f"\n  Pour les ajouter, voir : donnees/LISEZMOI.md")
    return False


def lancer(fichiers, entete) -> int:
    titre(entete)
    echecs = 0
    for nom, chemin in fichiers:
        print(f"\n{GRAS}» {nom}{FIN}")
        r = subprocess.run([sys.executable, chemin], cwd=RACINE,
                           capture_output=True, text=True)
        sortie = r.stdout.strip()
        if r.returncode != 0:
            echecs += 1
            print(f"{ROUGE}  ERREUR{FIN}")
            print("  " + (r.stderr.strip().splitlines() or ["(sans message)"])[-1])
            continue
        # On ne réaffiche que la ligne de bilan, pour rester lisible
        bilan = [l for l in sortie.splitlines() if "BILAN" in l or "ECHEC" in l.upper()]
        if any("ECHEC" in l.upper() for l in bilan):
            echecs += 1
            print(f"{ROUGE}  " + " / ".join(bilan) + FIN)
        else:
            print(f"{VERT}  tout est vert{FIN}")
    return echecs


def main():
    commande = sys.argv[1] if len(sys.argv) > 1 else "verifier"

    if not verifier_dependances():
        sys.exit(1)

    if commande in ("app", "pilotage"):
        page = RACINE / "app" / "retraites.html"
        print(f"Ouverture de la table de pilotage : {page}")
        webbrowser.open(page.as_uri())
        return

    if commande == "donnees":
        etat_donnees()
        return

    if commande == "analyses":
        echecs = lancer(ANALYSES, "ANALYSES")
        sys.exit(1 if echecs else 0)

    # Vérification complète
    titre("SIMULATEUR DE DÉPENSE PUBLIQUE — VOLET RETRAITES")
    print("  Vérification de l'installation.\n")
    echecs = lancer(TESTS, "CONTRÔLES DES MOTEURS")
    donnees_ok = etat_donnees()

    titre("RÉSULTAT")
    if echecs:
        print(f"  {ROUGE}{echecs} module(s) en échec.{FIN} Relancez le test concerné")
        print(f"  directement pour voir le détail, par exemple :")
        print(f"      python tests/test_fiscal.py")
        sys.exit(1)

    print(f"  {VERT}Tous les moteurs fonctionnent.{FIN}\n")
    print("  Ensuite :")
    print("      python run.py app          ouvrir le simulateur")
    print("      python run.py analyses     lancer les analyses")
    if not donnees_ok:
        print("      (ajoutez les fichiers EACR pour les chiffrages nationaux)")
    print()


if __name__ == "__main__":
    main()
