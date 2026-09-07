"""Chemins du projet, résolus depuis l'emplacement du paquet."""
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
PARAMETRES = RACINE / "parametres"
DONNEES = RACINE / "donnees"
APP = RACINE / "app"

BASELINES = PARAMETRES / "baselines_retraites.yaml"
FISCAL = PARAMETRES / "parametres_fiscaux_2026.yaml"
MARGES = PARAMETRES / "marges_eacr.yaml"
EACR_PART1 = DONNEES / "62_EACR_diffusée_Part_1_-_version_du_26_mai_2026.xlsx"
EACR_PART2 = DONNEES / "62_EACR_diffusée_Part_2_-_version_du_26_mai_2026.xlsx"
