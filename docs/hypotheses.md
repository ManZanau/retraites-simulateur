# Registre des hypothèses

*Document vivant. Toute hypothèse introduite dans le modèle doit y figurer,
avec sa source, son millésime et le sens du biais qu'elle induit.*

Dernière mise à jour : 19 août 2026

---

## Comment lire ce registre

Chaque entrée porte un **niveau** :

| Niveau | Signification |
|---|---|
| `observé` | Valeur mesurée, issue d'une source publiée et vérifiable |
| `arbitré` | Sources divergentes, choix explicite documenté |
| `hypothèse` | Aucune source ; valeur choisie pour faire tourner le modèle |
| `manquant` | Non renseigné ; le module refuse de calculer ou signale une borne |

Et un **sens du biais** : dans quelle direction l'hypothèse pousse le résultat.
C'est la partie la plus importante. Une hypothèse dont on ignore le sens du
biais est inutilisable pour un chiffrage.

---

## 1. Ce qui est observé

| Élément | Valeur | Source |
|---|---|---|
| Retraités de droit direct, France, fin 2024 | 16 429 117 | EACR 2024, table C |
| Retraités de droit direct, tous lieux | 17 298 245 | EACR 2024, table A |
| Pension moyenne de droit direct (m1), France | 1 705,0 €/mois | EACR 2024 |
| Pension moyenne, femmes | 1 349,1 €/mois | EACR 2024 |
| Pension moyenne, hommes | 2 123,3 €/mois | EACR 2024 |
| Écart femmes/hommes | −36,5 % | calculé sur EACR 2024 |
| Réversion seule | 886 134 | EACR 2024 |
| Répartition par tranche de CSG | 22,1 / 13,4 / 21,6 / 42,9 % | EACR 2024, table A-Prelev_sociaux |
| Barème de l'impôt 2026 | 11 600 / 29 579 / 84 577 / 181 917 € | LF 2026 |
| Taux de CSG | 8,3 / 6,6 / 3,8 % | art. L.136-8 CSS |
| ASPA 2026, personne seule | 1 043,59 €/mois | revalorisation du 1er janvier 2026 |
| ASPA 2026, couple | 1 620,18 €/mois | idem |
| Suspension de la réforme 2023 | générations 1964-1968 | LFSS 2026, art. 105 |

---

## 2. Arbitrages — sources divergentes, choix explicite

### 2.1 Seuil de CSG au taux médian, deux parts

- **Valeur retenue** : 40 604 €
- **Alternative écartée** : 39 886 € (deux sources sur trois)
- **Décidé le** : 19 août 2026
- **Sens du biais** : le seuil retenu étant le plus haut, davantage de foyers
  restent à 6,6 % au lieu de basculer à 8,3 %. Le retour de CSG est donc
  **minoré** et l'économie nette d'une réforme **majorée**. Hypothèse
  favorable au rendement des coupes.
- **À faire** : confirmer sur la grille officielle Assurance retraite ou URSSAF.

### 2.2 Plafond de l'abattement de 10 % sur les pensions

- **Valeur retenue** : 4 439 € **par foyer fiscal**, minimum 454 € par pensionné
- **Alternative écartée** : plafond individuel, doublé pour un couple
- **Fondement** : art. 158-5-a CGI ; trois sources sur quatre ; cohérent avec le
  contraste explicite entre les 14 555 € des salariés (individuels) et les
  4 439 € des retraités (mutualisés)
- **Sens du biais** : si l'interprétation retenue était fausse, l'abattement
  serait sous-estimé de 4 439 € par couple concerné, donc la perte d'IR
  **surestimée** sur les déciles hauts.
- **Criticité** : élevée. C'est le paramètre à vérifier en priorité.

### 2.3 Lissage des taux de CSG

- **Règle retenue** : la condition de dépassement sur deux années consécutives
  ne s'applique qu'au passage 3,8 % → 6,6 %
- **Alternative écartée** : règle générale à tous les franchissements
- **Fondement** : une source syndicale circonstanciée, militant pour l'extension
  de la règle — ce qui n'aurait pas de sens si elle était déjà générale
- **À faire** : vérifier à l'art. L.136-8 CSS.

### 2.4 Mode de sortie de la suspension au 1er janvier 2028

- **Non écrit dans la loi.** Trois modes implémentés : `retour_progressif`,
  `rattrapage_abrupt`, `gel_perenne`
- **Amplitude** : 15 mois d'âge légal sur les générations 1969 et suivantes
- **Règle** : tout chiffrage à horizon 2028+ doit être publié sous forme de
  **fourchette balayant les trois modes**, jamais sous un mode unique.

---

## 3. Hypothèses — aucune source

### 3.1 Dispersion des pensions — **RÉSOLU le 20 août 2026**

- **Statut** : observé. La distribution provient désormais de l'EIR 2020,
  tableau 5, en 46 tranches de 100 €. Elle n'est plus supposée.
- **Validation croisée** : la moyenne implicite du tableau 5 est de 1 624 €,
  contre 1 568 € pour m1 + m2 dans l'EACR 2020 sur le même champ. L'écart de
  3,6 % correspond à la majoration pour trois enfants, incluse dans le champ
  du tableau 5 et absente de m1 + m2. Deux sources construites indépendamment
  concordent.
- **Ce que l'ancienne hypothèse valait** : la dispersion réelle correspond à un
  σ log-normal équivalent de **0,679**. La fourchette 0,35–0,75 que je balayais
  encadrait donc correctement la vérité, mais vers le haut. Un chiffrage retenu
  à σ = 0,55 aurait sous-estimé l'économie d'un écrêtement d'environ 35 %.
- **Ce que la log-normale ratait** : le décile 1 réel est à 512 €, bien en
  dessous de ce qu'une log-normale ajustée sur le reste prédirait. La vraie
  distribution a une queue basse épaisse — carrières courtes, polypensionnés à
  droits faibles. Le modèle utilise donc la distribution empirique, pas une
  forme paramétrique.
- **Recalage** : forme 2020, niveau 2024 par un facteur de 1,1920, égal au
  rapport des m1 + m2 entre les deux millésimes. Hypothèse standard : entre
  deux millésimes proches, la déformation de la distribution est du second
  ordre devant son déplacement en niveau.

### 3.1 bis Moyenne de la tranche supérieure à 4 500 € — **seul paramètre libre restant**

- **Statut** : hypothèse, balayée sur 5 000 / 5 800 / 7 000 €
- **Pourquoi** : la Drees regroupe tout au-dessus de 4 500 € sans publier de
  moyenne. Cette tranche pèse 1,82 % des retraités.
- **Effet mesuré** : sur un écrêtement de D9 et D10, l'économie nette varie de
  5,1 à 6,4 Md€ — écart de 25 %. Sur un **plafond à 4 000 €**, elle varie de
  6,8 à 11,8 Md€, soit un écart de 73 %, puisque la mesure porte presque
  entièrement sur cette tranche.
- **Sens du biais** : l'hypothèse basse **minore** l'économie de toute mesure
  ciblant le haut de la distribution.
- **Résolution** : la tranche est ventilée dans les fichiers détaillés de
  l'EIR, accessibles via le CASD.

### 3.2 Minimum vieillesse — calé, non modélisé

- **Problème** : le modèle ne connaît que la pension individuelle. Il ignore les
  ressources du conjoint, la condition d'âge de 65 ans, les revenus du
  patrimoine et le non-recours. Sans correction, il compte **3,6 millions**
  d'allocataires pour **21 Md€**.
- **Réalité observée** : 754 460 bénéficiaires fin 2024, allocation moyenne de
  530 €/mois pour l'ASPA et 470 € pour l'ASV. La Drees estime qu'environ la
  moitié des personnes seules éligibles ne demandent pas l'allocation.
- **Correction retenue** : facteur de calage uniforme de 0,209, qui ramène le
  modèle à 755 000 allocataires et 4,4 Md€.
- **Limite du calage** : il est uniforme, alors que l'inéligibilité réelle se
  concentre sur des profils particuliers — retraités à petite pension vivant
  dans un ménage aisé, personnes de moins de 65 ans. Les ordres de grandeur
  agrégés sont corrects ; la **répartition par décile** de l'effet minimum
  vieillesse reste approximative.
- **Leviers ouverts** : montant garanti (zéro = suppression) et taux de recours
  effectif, tous deux pilotables dans l'application.
- **Sens du biais** : le calage étant fondé sur les effectifs actuels, il
  suppose que le taux d'éligibilité reste constant lorsqu'on modifie les
  pensions. Une forte baisse des pensions basses rendrait en réalité éligibles
  des personnes qui ne l'étaient pas — le modèle **sous-estime** donc le
  contre-effet des mesures visant le bas de la distribution.

### 3.3 Devenir de la cohorte reportée par un décalage d'âge

- **Statut** : paramétré et sourcé, plus abattu forfaitairement.
- **Question** : quand un décalage d'âge empêche un départ, la personne
  travaille-t-elle réellement, ou bascule-t-elle vers le chômage, l'invalidité
  ou les minima sociaux ? C'est le point faible de tout chiffrage d'un recul
  de l'âge.
- **Sources d'évaluation de la réforme de 2010** :
  - Cour des comptes, février 2025 : de 2010 à 2020, l'âge effectif de départ
    a progressé de 2,1 ans, mais la durée passée en emploi de 1 an et 7 mois
    seulement — environ trois quarts du décalage.
  - IPP : pour les non éligibles aux carrières longues, +20 à 25 points
    d'emploi entre 60 et 62 ans, mais aussi +12 à 15 points de chômage
    indemnisé.
  - Dubois et Koubi (2017) : à 60 ans, la probabilité d'emploi passe de 33 à
    49 %, celle de non-emploi de 17 à 26 % — soit environ 64 % vers l'emploi.
  - Drees, remise au COR d'octobre 2016 : 1,2 à 1,5 Md€ de surcoût pour
    l'invalidité et 600 M€ pour les minima sociaux, pour le passage de 60 à
    62 ans. À 60 ans, près d'une personne sur trois n'est ni en emploi ni à la
    retraite.
- **Fourchette de la littérature** : 62 à 75 % restant en emploi. Défaut
  retenu : 65 %, pilotable dans l'application.
- **Résultat contre-intuitif, à assumer** : le gain net d'une année de décalage
  ne varie que de 11,5 à 16,9 Md€ entre 50 % et 100 % d'emploi. Une allocation
  de chômage ou d'invalidité coûte moins qu'une pension : le report vers le
  chômage reste budgétairement moins coûteux que le départ en retraite, même
  s'il est socialement bien pire. **Le taux d'emploi est donc un enjeu social
  majeur et un enjeu budgétaire secondaire.**
- **Le vrai paramètre incertain** : la part du flux réellement contrainte par
  l'âge légal, fixée à 70 %. Les départs au taux plein automatique à 67 ans et
  une partie des carrières longues ne sont pas décalés. C'est ce paramètre qui
  détermine l'ordre de grandeur.
- **Non modélisé, et minorant le gain** : les trimestres validés pendant le
  chômage ou l'invalidité accroissent la pension future ; le surcoût d'arrêts
  maladie, chiffré à 68 M€ par le CEET pour la réforme de 2010.

### 3.4 Table de mortalité — **RÉSOLU le 20 août 2026**

- **Statut** : forme paramétrique de Gompertz-Makeham, **calée** sur les
  espérances de vie publiées par l'Insee pour 2025.
- **Cibles reproduites exactement** : e(65) = 19,7 ans pour les hommes et
  23,4 ans pour les femmes ; e(60) = 27,9 ans pour les femmes.
- **Écart résiduel** : e(60) obtenu de 24,0 ans pour les hommes contre environ
  23,5 attendus, la pente étant supposée commune aux deux sexes faute d'une
  seconde cible masculine publiée.
- **Dérive de longévité** : les quotients baissent de 1,475 % par an pour les
  hommes et 0,928 % pour les femmes, calage sur les cibles COR 2070 de 24,8 et
  26,7 ans d'espérance de vie à 65 ans.
- **Avant calage** : e(65) donnait 16,2 et 18,6 ans, soit 18 à 20 % de moins
  que la réalité — les dépenses futures étaient donc systématiquement
  sous-estimées.
- **Amélioration possible** : tables INSEE réelles, via
  `TableMortalite.depuis_tableau`. Aucune modification du moteur nécessaire.

### 3.5 Pension d'entrée des nouveaux liquidants

- **Valeur** : paramètre unique, croissant de 1 % par an
- **Défaut** : devrait varier par génération et par régime.

### 3.6 Structure de ménage

- **Statut** : absente
- **Conséquence** : l'impôt sur le revenu se calcule au foyer fiscal et l'ASPA
  sur les ressources du ménage. Un modèle purement individuel **surestime le
  contre-effet ASPA** et **déforme la perte d'IR**.
- **Résolution** : appariement statistique sur l'ERFS, ou EIR 2024 apparié aux
  données fiscales.

---

## 4. Éléments manquants qui vont tous dans le même sens

Les termes suivants **réduisent** l'économie nette d'une réforme. Leur absence
rend tout résultat produit par le simulateur une **borne supérieure**.

| Élément | Criticité |
|---|---|
| Aides au logement (APL) | importante |
| Complémentaire santé solidaire | secondaire |
| Exonérations locales (taxe foncière) | secondaire, mais relève des APUL |
| Seuils de CSG outre-mer | importante — le module refuse de traiter les DROM |
| Grille de CSG au-delà de deux parts | secondaire |
| Récupération de l'ASPA sur succession | importante pour le taux de recours |
| Bouclage macroéconomique (consommation, TVA) | reporté en phase 7 |

---

## 5. Ce que le simulateur ne prétend pas faire

- Il ne calcule **aucun droit individuel à retraite**.
- Il ne produit **aucun chiffrage national d'écrêtement ciblé** tant que la
  dispersion n'est pas observée.
- Il ne tranche **aucune question contestée** : ni la qualification de la
  contribution employeur de l'État, ni le mode de sortie de la suspension.
- Il ne modélise **pas les changements de comportement** induits par une réforme
  (report de départ, recours à l'ASPA, arbitrages d'épargne).
