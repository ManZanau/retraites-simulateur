# Simulateur de dépense publique — volet retraites

Outil de pilotage des retraites françaises : quantifier l'effet net d'une
mesure sur les finances publiques (jour 1 et jusqu'en 2070), en distinguant
l'effet brut affiché de l'effet réel après impôt, prélèvements sociaux et
minimum vieillesse.

**Pour reprendre ce projet sans relire tout l'historique de conversation :
ce fichier + `docs/hypotheses.md` + `docs/inventaire_sources.md` suffisent.**

---

## Démarrage en 30 secondes

```bash
# L'application : aucune installation, aucune dépendance
open app/retraites.html          # ou double-clic

# Le moteur Python : vérifie que tout fonctionne
python3 -m venv .venv                      # environnement isolé (recommandé)
source .venv/bin/activate                  # Windows : .venv\Scripts\activate
pip install -r requirements.txt
python3 run.py
```

`python3 run.py` fait tourner les 6 suites de tests et affiche un rapport.
Doit afficher "tout est vert" partout. Si un test casse, c'est la première
chose à corriger avant tout ajout.

L'environnement isolé (`venv`) évite les collisions avec une installation
Python système encombrée (une Anaconda, par exemple). Installation propre
vérifiée le 2026-09-09 : Python 3.10, les 6 suites au vert. `test_app.py`
demande Node.js ; sans Node, ce test se déclare non exécutable au lieu de
passer à tort.

---

## Architecture

```
app/retraites.html      L'application — UN SEUL FICHIER, HTML+CSS+JS inline,
                         126 Ko, zéro dépendance externe sauf Google Fonts
                         (avec repli si indisponible). C'est le livrable
                         final envoyé aux utilisateurs.
app/version-precedente.html   Version antérieure à la refonte du 3 sept 2026,
                         conservée par précaution. 9 onglets, plus lourde.

modeles/                Moteurs Python, chacun testé indépendamment.
  baseline.py            Âge légal + durée d'assurance par génération,
                          sous 3 scénarios législatifs (voir § Droit)
  fiscal.py               CSG/CRDS/CASA, IR, ASPA, cascade de décomposition
  reforme.py              Application d'un scénario à une distribution
                          (barème marginal par décile, plafond, plancher)
  projection.py           Projection démographique 2025-2070 (mortalité,
                          liquidations, revalorisation)
  calage.py                Moteur IPF générique (calage sur marges)
  distribution_eir.py     Distribution empirique des pensions (EIR 2020 +
                          queue de Pareto au-delà de 4 500 €)
  population_eacr.py      Chargement des fichiers EACR bruts (Excel Drees)
  chemins.py               Résolution des chemins de fichiers

parametres/              Barèmes en YAML, lisibles sans coder
  baselines_retraites.yaml     âge légal, durée, 3 scénarios de sortie
  parametres_fiscaux_2026.yaml  IR, CSG, ASPA — chaque valeur a un statut
                                (confirme / arbitre / manquant)
  marges_eacr.yaml              structure des marges de calage EACR

tests/                   Une suite par moteur + un test de l'app web
  test_app.py             Exécute le JS de retraites.html sous Node avec un
                          DOM simulé ; vérifie balisage (pas d'id manquant/
                          dupliqué), rendu (chaque section a du contenu),
                          et VALEURS (résultats de référence figés, voir
                          § Valeurs de contrôle)

analyses/                Scripts ponctuels de calcul (courbes, comparaisons)
                         Utiles pour explorer, pas pour le produit final.

docs/
  hypotheses.md            LE document le plus important après ce README.
                          Chaque paramètre incertain, avec son sens de biais.
  inventaire_sources.md    Sources primaires, avec dates de consultation.

donnees/                 Vide par défaut. Fichiers EACR (Drees) à télécharger
                         manuellement — voir LISEZMOI.md. Pas nécessaires
                         pour l'application web, seulement pour regénérer
                         les grilles de population dans les analyses.

run.py                   Lanceur unique : `python3 run.py` teste tout,
                         `python3 run.py app` ouvre l'application.
```

### Pourquoi un seul fichier HTML

Décision assumée : `retraites.html` contient tout (données, calcul, UI) en
inline, sans build step, sans framework. Ça permet :
- diffusion par simple partage de fichier ou hébergement statique gratuit
  (Cloudflare Pages, GitHub Pages)
- fonctionnement offline total après premier chargement des polices
- lien de partage qui encode l'état complet du scénario dans l'URL (`#...`)

Le prix : le fichier est volumineux (126 Ko) et toute modification touche un
fichier monolithique. **Ne pas re-fragmenter en plusieurs fichiers** sans
raison forte — c'est un choix de diffusion, pas un oubli d'architecture.

---

## Stack technique

- **Aucune dépendance de build.** Pas de npm, pas de webpack, pas de framework
  JS. Vanilla JS dans une balise `<script>`, CSS dans une balise `<style>`.
- **Polices** : Google Fonts (Instrument Sans + IBM Plex Mono), avec pile de
  repli système complète si hors ligne.
- **Python 3.10+** pour les moteurs (`modeles/`), testés avec `pandas`,
  `numpy`, `scipy`, `openpyxl`, `pyyaml` (voir `requirements.txt`).
- **Node.js** requis uniquement pour `tests/test_app.py`, qui exécute le JS
  de l'app sous un DOM simulé (`document.getElementById` etc. mockés à la
  main dans le test). Sans Node, ce test se déclare "non exécutable" plutôt
  que de faussement passer.
- **Aucune base de données, aucun serveur.** Tout est statique.

---

## État du code (3 septembre 2026)

**Tout est vert.** 6 suites de tests, ~830 lignes de tests, ~1825 lignes de
moteurs Python, 30 contrôles sur l'application web (voir `test_app.py`).

### Ce qui est calé sur données réelles

| Donnée | Valeur | Source |
|---|---|---|
| Retraités droit direct, France | 16 429 118 | Drees, EACR 2024 |
| Pension moyenne droit direct | 1 705 €/mois | Drees, EACR 2024 |
| Distribution des pensions | 46 tranches EIR 2020 | Fournie par l'utilisateur, validée à 3,6 % près contre l'EACR |
| Masses par régime | 335 Md€ | Drees, EACR 2024, table A-Cadrage |
| Allocataires ASPA | 754 460 | chiffre officiel 2024 |
| Valeur du point (CSG / cotisation) | 17,6 Md€ / 6,2 Md€ | Sécurité sociale, données 2024 |
| Trajectoire de référence | COR, rapport juin 2026 | reproduit au dixième sur les variantes de productivité |
| Espérance de vie | Insee 2025 | calée exactement, dérive vers cibles COR 2070 |
| Barèmes fiscaux 2026 | IR, CSG, ASPA | LF 2026, art. L.136-8 CSS |

### Ce qui reste une hypothèse (voir `docs/hypotheses.md` pour le détail)

- **Moyenne des pensions > 4 500 €/mois** : non publiée par la Drees. Modélisée
  par une loi de Pareto, 3 variantes (5 000 / 5 800 / 7 000 €). C'est le plus
  gros facteur d'incertitude de l'outil — un plafond à 8 000 € varie d'un
  facteur 100 selon la variante retenue.
- **Répartition par régime sous 2 000 €/mois** : proportionnelle aux masses,
  faute de croisement régime × niveau de pension dans les données publiques.
- **Taux de recours à l'ASPA** : fixé à 100 % par défaut (pilotable).
- **Devenir de la cohorte reportée par un décalage d'âge** : 65 % restent en
  emploi par défaut (pilotable), fourchette littérature 62-75 %.
- ~~**3 paramètres non vérifiés contre le texte légal**~~ — **résolus le
  7-9 septembre 2026** : plafond de l'abattement 10 % = **par foyer** (4 439 €,
  BOFiP art. 158-5-a) ; seuil CSG à 2 parts = **40 604 €** (Assurance retraite,
  grille 2026) ; tables d'âge légal = **conformes** aux art. L. 161-17-2 et
  L. 161-17-3 CSS (LFSS 2026, art. 105), vérifiées mot pour mot sur Légifrance.
  Voir `parametres/parametres_fiscaux_2026.yaml` et
  `parametres/baselines_retraites.yaml` (champs `note_verification` /
  `reference_legale`).

### Valeurs de contrôle (figées dans `test_app.py`, ne doivent jamais bouger sans raison)

```
Écrêtement D9 -10%, D10 -30%          → 5,44 Md€
CSG +1 point                          → 17,6 Md€
Âge légal +1 an                       → 13,1 Md€ (effet direct)
Productivité 0,4% / 0,7% / 1,0%       → 16,1% / 15,3% / 14,5% du PIB en 2070
Durée d'assurance = 0,894 × équivalent-âge (10,6% partent déjà à 67 ans)
Plafond à 3000€ → 100% de l'effet au-dessus de 2000€/mois (CNAV)
```

Si l'un de ces nombres change après une modification, c'est soit un bug,
soit une correction méthodologique — dans les deux cas, il faut comprendre
pourquoi avant de continuer, et mettre à jour `docs/hypotheses.md`.

---

## Droit applicable modélisé (baseline.py)

Trois scénarios sur l'âge légal et la durée d'assurance :
- **B0** — réforme 2023 (loi Borne), calendrier initial sans suspension
- **B1** — droit en vigueur : suspension par la LFSS 2026 (loi n°2025-1403,
  art. 105) pour les générations 1964-1968, jusqu'au 1er janvier 2028
- **B2** — post-suspension, avec 3 modes de sortie possibles (la loi ne
  tranche pas) : retour progressif / rattrapage abrupt / gel pérenne

L'application web utilise B1 (droit en vigueur) comme référence, avec des
curseurs pour l'écart d'âge et de durée par rapport à ce point de départ.

---

## Fonctionnalités de l'application (`retraites.html`)

### Deux modes
- **Simple** (par défaut) : 3 groupes de pensions (bas/moyen/haut), âge,
  cotisations. Résultat en langue courante. Cible : grand public.
- **Détaillé** : tous les leviers ci-dessous. Cible : décideurs, journalistes,
  économistes.

### Bloc résultat unifié (en tête, toujours visible)
Fusionne l'effet jour 1 ET la trajectoire 2025-2070 dans un seul graphique :
la courbe part de l'effet immédiat et va jusqu'en 2070. Sous la courbe, une
table de projection des dépenses de retraite à 2027/2030/2040/2050 (euros
courants + % PIB + écart à la référence).

### Leviers (mode détaillé)
- 10 curseurs de décile (taux marginal, comme un barème d'impôt)
- Plafond et plancher de pension
- Minimum vieillesse : montant garanti + taux de recours
- Âge légal (avec avertissement si collision avec l'âge d'annulation à 67 ans)
- Durée d'assurance (avec explication de l'asymétrie femmes/hommes)
- Cotisations salariales / patronales (séparées) + CSG
- Sous-indexation des pensions, avec **durée limitée** (paramètre clé,
  pour éviter qu'une mesure de mandat soit lue comme permanente)
- Productivité (hypothèse de contexte, pas un levier de décision — étiqueté
  comme tel)

### Onglets (mode détaillé)
- **Décider** — pilotage principal
- **Qui paie** — cascade fiscale, incidence par décile, masses par régime
  et autorité de décision (loi / paritaire / employeur public)
- **Atteindre une cible** — solveur inverse : fixer une somme, choisir les
  leviers autorisés, l'outil calcule le dosage (dichotomie sur 6 profils)
- **Comparer** — deux scénarios A/B, mêmes lignes, écarts colorés
- **Méthode** — sources, limites, controverses non tranchées

### Export / partage
- Lien d'URL encodant l'état complet du scénario (`#...`)
- Rapport imprimable/PDF avec repères budgétaires contextualisés (Md€ en
  équivalent budget Justice, points de cotisation, etc.)
- Partage natif mobile (Web Share API) avec repli presse-papier puis
  affichage texte sélectionnable

---

## Ce qui a été corrigé en cours de route (pour ne pas refaire les mêmes erreurs)

Une douzaine de bugs substantiels trouvés par les tests ou par les questions
de l'utilisateur, listés ici pour éviter de les réintroduire :

1. Double compte des polypensionnés (effectifs par caisse vs par personne) :
   erreur initiale de +40%, réalité +130%
2. Rendement d'un point de cotisation : uniforme à tort (14,5 Md€), corrigé
   par assiette réelle (6,2 Md€ vieillesse, 17,6 Md€ CSG) — facteur 2,3
3. PIB projeté : +40% par croissance nominale non sourcée (3,2%), corrigée
   par décomposition productivité+emploi+inflation (2,45%)
4. Sensibilité à la productivité : mécanisme 2,5× trop sensible avant
   calage sur les variantes officielles du COR
5. Mortalité : table paramétrique non calée sous-estimait l'espérance de
   vie de 20% ; calée sur Insee 2025 + cibles COR 2070
6. ASPA : modèle comptait 3,6M allocataires (5× la réalité de 754 460) faute
   de tenir compte des ressources du ménage et du non-recours ; calé par
   facteur uniforme
7. Solveur de l'onglet Objectif : variable globale polluée entre appels,
   rendait le levier "plafond" totalement inopérant sans erreur visible
8. Imputation par régime : confondait "variation de pension totale" et
   "localisation de la mesure" — une revalorisation du bas apparaissait
   fictivement comme touchant 48% le haut de la distribution
9. Sous-indexation appliquée sur 45 ans par défaut au lieu d'une durée de
   mandat — rendait les projections à long terme artificiellement flatteuses
10. Queue de distribution : modèle uniforme remplacé par Pareto, la grille
    de quantiles ne contenait littéralement personne au-dessus de 8000€
11. Identifiants HTML dupliqués (boutons de mode cumul/remplacer en double)
    rendaient une partie de l'interface silencieusement inerte
12. Lien de partage : montant ASPA arrondi à l'entier, cassait l'aller-retour

**Leçon générale** : le test `test_app.py` a été construit de façon à ne PAS
pouvoir laisser passer ces classes d'erreurs (DOM simulé strict, valeurs de
référence figées). Le maintenir strict est plus important que d'ajouter des
fonctionnalités.

---

## Prochaines étapes (par ordre de priorité déjà discuté)

1. ~~**Vérifier 3 paramètres contre le texte légal**~~ — **fait (7-9 sept. 2026)** :
   - Plafond de l'abattement 10 % pensions : **par foyer** (4 439 €). Source
     BOFiP art. 158-5-a CGI + réponse ministérielle AN n°21770.
   - Seuil CSG médian à 2 parts : **40 604 €** (débat 39 886 vs 40 604 tranché).
     Source Assurance retraite, « Prélèvements sociaux en 2026 », MàJ 09/01/2026.
     Grille complète 1 à 3 parts + supplément par demi-part ajoutés au YAML.
   - Tables âge légal / durée : **conformes** aux art. L. 161-17-2 et
     L. 161-17-3 CSS (LFSS 2026, art. 105), lus mot pour mot sur Légifrance.
     Les décrets n°2026-344 / 2026-345 ne portent pas la grille générale
     (carrière longue, fonction publique, Mayotte, handicap uniquement) —
     piège documenté dans `baselines_retraites.yaml`. Carrière longue
     « avant 20 ans » complétée depuis D. 351-1-1 II CSS.
   - Reste en suspens : seuils CSG **outre-mer** (grille 2026 ajoutée mais
     source secondaire unique, à recouper) ; version archivée de B0 non
     recontrôlée ligne à ligne (contrefactuel).
2. **Héberger** (Cloudflare Pages recommandé — gratuit, pas de plafond de
   bande passante). Sans hébergement, le lien de partage de scénario ne
   fonctionne pas pour un tiers (pointe vers `file://`).
3. **Écrire à la Drees** (drees-infos@sante.gouv.fr) pour obtenir la moyenne
   de la tranche EIR > 4 500 € — lèverait le plus gros facteur d'incertitude
   de l'outil.
4. **Diffusion** : messages privés à des économistes pour avis avant tout
   partage public ; LinkedIn avant X ; éviter la monétisation par impressions
   (peu rentable, dévalorise la crédibilité méthodologique du projet).

### Non prioritaire / explicitement écarté
- Module santé (même architecture, mais hors périmètre pour l'instant)
- Gains chiffrés d'une fusion des régimes : demanderait un moteur de règles
  par régime (type openfisca-france-pension) + données EIC via CASD — projet
  à part entière, pas une extension incrémentale
- Obfuscation du code pour "protéger" l'outil : inefficace par nature (tout
  le JS est visible côté client) ; la vraie protection est le dépôt de
  preuve d'antériorité (e-Soleau/APP) + une licence d'attribution

---

## Accès aux données manquantes

- **Fichiers EACR** (Drees, nécessaires seulement pour régénérer les grilles
  de population dans `analyses/`) : `data.drees.solidarites-sante.gouv.fr`,
  jeu de données `donnes_eacr`. Voir `donnees/LISEZMOI.md`.
- **EIR détaillé / EIC** (pour lever l'incertitude sur les hautes pensions
  et sur les carrières individuelles) : accès CASD, procédure ~1 an, passe
  par accord préalable Drees + Comité du secret statistique. Nécessite en
  pratique un rattachement institutionnel (université, labo, think tank).

---

## Licence et citation

Code, paramètres et analyses : **licence MIT** (voir `LICENSE`). Réutilisation
libre, y compris commerciale, à condition de conserver la mention de paternité.

Les données publiques sous-jacentes (EACR, Drees) restent sous **Licence
Ouverte 2.0** et imposent, sur toute sortie publiée :

    Source : Drees, enquête annuelle auprès des caisses de retraite (EACR),
    enrichie avec le modèle Ancetre

**Comment citer ce travail :**

    Aurain, S. (2026). Simulateur de dépense publique — volet retraites.
    https://github.com/ManZanau/retraites-simulateur

Voir aussi `CITATION.cff` (GitHub affiche un bouton « Cite this repository »).

---

*Dernière mise à jour de ce document : 9 septembre 2026. Si tu reprends ce
projet dans un nouveau chat, lis ce fichier, `docs/hypotheses.md`, lance
`python3 run.py`, puis ouvre `app/retraites.html`. Tu n'as pas besoin de
l'historique de conversation complet.*
