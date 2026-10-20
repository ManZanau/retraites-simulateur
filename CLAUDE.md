# CLAUDE.md — reprise du projet

Simulateur « Où va l'argent des retraites ». Détail du projet, de l'architecture
et des sources : `README.md`, `docs/hypotheses.md`, `docs/inventaire_sources.md`.
Ne pas relire ces fichiers en entier sans besoin : chercher la section utile.

## Travailler avec Stan (Stanislas Aurain, auteur)
- Répondre en français, concret, résumé d'abord, sans jargon (il n'est pas
  développeur ; il dicte souvent, d'où des fautes de transcription).
- **Faire soi-même commit + push** sur `main` après chaque changement validé,
  puis vérifier le déploiement (voir plus bas). Messages de commit en français.
- Demander avant tout ce qui coûte de l'argent ou touche à ses comptes.

## Où vit quoi
- En ligne : https://ou-va-largent-des-retraites.pages.dev — Cloudflare Pages,
  projet `ou-va-largent-des-retraites`, déploiement **automatique** à chaque push
  sur `main` (~1 min). Toute autre branche = prévisualisation automatique sur
  `https://<branche>.ou-va-largent-des-retraites.pages.dev`.
- Vérifier un déploiement : connecteur MCP Cloudflare, `GET /accounts/{id}/pages/
  projects/ou-va-largent-des-retraites/deployments` (déclencheur `github:push`).
- Dépôt : https://github.com/ManZanau/retraites-simulateur (public, MIT).
- Police Instrument Sans servie depuis `/fonts/` (plus de Google Fonts).
- L'app = **un seul fichier** `app/retraites.html` (~2 350 lignes, HTML+CSS+JS).
  Ne pas le lire en entier : `grep -n` puis lire la zone. Ne pas le découper.
- `_redirects` : la racine `/` sert le simulateur (liens de scénario `/#...`).
- App installable (PWA) : `manifest.webmanifest`, `sw.js`, `icons/`.
- `/stats` (`stats.html`) : page privée des compteurs (connexions, rapports
  partagés), non liée. Compteurs : service abacus.jasoncameron.dev, espace
  `retraites-simulateur-manzanau` — ne pas renommer (remettrait à zéro).
- Ancienne adresse GitHub Pages encore active en secours, sans PWA.

## Tests (machine Windows de Stan)
- Anaconda est cassé (numpy) : utiliser le venv du projet.
  `PYTHONIOENCODING=utf-8 PYTHONUTF8=1 ./.venv/Scripts/python.exe run.py`
  (6 suites) ou seulement `tests/test_app.py` après un changement de l'app.
- Contrôle de syntaxe rapide du JS de l'app :
  `node -e "const h=require('fs').readFileSync('app/retraites.html','utf8');new Function(h.split('<script>')[1].split('</script>')[0]);console.log('OK')"`
- `test_app.py` exécute le JS sous Node avec un DOM simulé : `window` n'y a ni
  `addEventListener` ni `innerWidth`, `navigator` est vide → toujours protéger
  ces appels. Il vérifie que chaque id passé à `$('…')`, `html('…')`, `txt('…')`
  existe dans le balisage (avant la première balise `<script>`).
- Les avertissements git « LF will be replaced by CRLF » sont sans effet.

## En cours (au 20/10/2026)
1. Nouvelle mise en page + corrections d'accessibilité (contrastes, textes
   ≥ 13 px, curseurs lisibles par lecteur d'écran, onglets au clavier, police
   hébergée dans `fonts/`) : **publiées sur `main` le 20/10/2026**.
2. **Reste de la revue d'ergonomie** (après la maquette), par priorité :
   - « Atteindre une cible » : bouton « Appliquer au simulateur » sur chaque dosage.
   - « Comparer » : comparer d'office au « sans réforme », bouton « Garder ce
     scénario » depuis Décider (aujourd'hui allers-retours entre onglets).
   - Curseurs « Âge de départ » et « Cotisations » : afficher l'unité (« 64 ans »,
     « pt »), et les bornes −/+ des curseurs.
   - Plus tard : version anglaise, nom de domaine (≈ 10 €/an, achat par Stan).

## Règles apprises (à respecter)
- Toute constante chiffrée de l'app (PIB, budgets, barèmes) doit citer sa source
  et sa date en commentaire, et être recoupée avec la publication officielle la
  plus récente avant d'être affichée. Un PIB 2025 périmé (2 900 au lieu de
  2 991,1 Md€) a faussé toute la trajectoire d'environ 3 % sans être vu.
- Ne jamais figer en dur un chiffre que le modèle sait calculer.
- Date de vérification des données : constante `DATE_DONNEES` dans l'app
  (affichée dans la Méthode, le pied de page et le rapport) — la mettre à jour.
- Les valeurs de contrôle de `README.md` (§ Valeurs de contrôle) ne doivent pas
  bouger sans explication.
- Âge légal et durée d'assurance : la grille générale est dans la loi
  (art. L. 161-17-2 et L. 161-17-3 CSS), pas dans les décrets 2026-344/345.
