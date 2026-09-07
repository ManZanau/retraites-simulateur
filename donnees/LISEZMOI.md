# Fichiers de données

Ce dossier doit contenir les deux fichiers Excel de l'enquête annuelle auprès
des caisses de retraite (EACR), diffusés par la Drees en open data.

## Où les récupérer

Portail Drees (source primaire) :
https://data.drees.solidarites-sante.gouv.fr/explore/dataset/donnes_eacr/information/

Miroir data.gouv.fr :
https://www.data.gouv.fr/datasets/donnees-de-lenquete-annuelle-aupres-des-caisses-de-retraite

## Fichiers attendus

    62_EACR_diffusée_Part_1_-_version_du_26_mai_2026.xlsx   (~24 Mo)
    62_EACR_diffusée_Part_2_-_version_du_26_mai_2026.xlsx   (~16 Mo)

Le nom doit être conservé tel quel, accents compris. Si vous utilisez un
millésime plus récent, adaptez les chemins dans `modeles/chemins.py`.

## Sans ces fichiers

Le simulateur fonctionne : les barèmes, les calculs par foyer, l'application
web et l'ensemble des tests ne dépendent pas de ces données. Seuls les
chiffrages à l'échelle nationale les nécessitent.

## Licence

Licence ouverte 2.0. Elle impose de mentionner la source à chaque utilisation :

    Source : Drees, enquête annuelle auprès des caisses de retraite (EACR),
    enrichie avec le modèle Ancetre

Cette mention doit figurer sur toute sortie publiée du simulateur.
