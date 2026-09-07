# Simulateur de dépenses publiques — Volet retraites
## Note d'inventaire des sources

*Version 1.0 — 19 août 2026*

---

## 0. Résumé exécutif

Trois constats structurent la suite du projet :

1. **Le scénario de référence est instable.** La LFSS 2026 a suspendu le calendrier de relèvement de l'âge légal pour les générations 1964-1968, avec effet **au 1er septembre 2026** — soit dans douze jours. Le droit applicable change pendant la construction du modèle, et la suspension prend fin au 1er janvier 2028, avant l'échéance présidentielle. Le baseline doit donc être **paramétrable, pas codé en dur**.

2. **Le cadrage macro vient d'être entièrement renouvelé.** L'INSEE a publié en juin 2026 de nouvelles projections démographiques, nettement plus pessimistes que celles de 2021, et le COR a publié son rapport annuel le 11 juin 2026 en les intégrant. Tout calage sur les millésimes antérieurs serait périmé dès le départ.

3. **Aucune source unique ne permet le croisement régime × génération × décile × fiscalité.** Il faut assembler deux mondes de données qui ne se parlent pas : les sources « retraite » (EIR/EIC, riches par régime, pauvres sur le ménage) et les sources « fiscales » (ERFS, riches sur le ménage, pauvres par régime). C'est le principal risque méthodologique du projet.

---

## 1. Scénario de référence : le droit en vigueur

### 1.1 État du droit

| Élément | Statut |
|---|---|
| Réforme 2023 (« Borne ») | En vigueur, non abrogée |
| Relèvement âge légal 62 → 64 ans | **Suspendu** pour générations 1964-1968 |
| Allongement durée d'assurance | **Suspendu** pour les mêmes générations |
| Autres mesures 2023 (carrières longues, surcote parentale, cumul emploi-retraite, retraite progressive) | En vigueur, non affectées |

**Base légale de la suspension :** article 105 de la loi n° 2025-1403 du 30 décembre 2025 (LFSS 2026).

**Fenêtre d'application :** pensions prenant effet du 1er septembre 2026 au 1er janvier 2028.

**Effet par génération :**
- Génération 1964 et premier trimestre 1965 : âge légal maintenu à 62 ans et 9 mois
- Né à partir du 1er avril 1965 : reprise de la hausse d'un trimestre par génération
- Générations 1966-1968 : décalage uniforme de 3 mois par rapport au calendrier 2023
- Génération 1969 et suivantes : 64 ans, inchangé
- Fonction publique catégorie active : borne des 59 ans décalée de la génération 1973 à 1974

### 1.2 Conséquence pour l'architecture

Le simulateur doit distinguer **trois baselines** distincts et permettre de les comparer :

- **B0** — droit 2023 sans suspension (contrefactuel)
- **B1** — droit en vigueur au 1er septembre 2026 (suspension active)
- **B2** — droit post-2028 (reprise du calendrier)

Sans cette distinction, tout chiffrage de réforme mélangera l'effet de la réforme testée avec l'effet du calendrier de suspension. C'est une source d'erreur majeure et facile à commettre.

---

## 2. Sources de cadrage macro

### 2.1 Projections démographiques INSEE 2026

**Référence :** Blanpain N., Pointet J., Thélot H., *Projections de population 2026 pour la France*, Insee Résultats, juin 2026. Synthèse : Insee Première n° 2108.

**Statut :** publié, librement téléchargeable, avec données détaillées.

**Point de départ :** population au 1er janvier 2023 (dernière estimation définitive du recensement), puis bilan démographique jusqu'au 1er janvier 2026.

**Hypothèses centrales :**
- Fécondité : baisse jusqu'à 1,45 enfant par femme en 2028 (1,56 en 2025), puis stabilisation. Hypothèses basse et haute à ± 0,25 à partir de 2030.
- Âge moyen à la maternité : 31,2 ans en 2025 → 33,0 ans en 2050
- Espérance de vie : prolongement de la baisse des risques de décès sur le rythme des 20 dernières années, hors 2020-2022
- Solde migratoire : révisé à la hausse

**Résultats saillants :**
- 65,9 millions d'habitants en 2070, soit 3,2 millions de moins qu'en 2026
- Pic à 69,8 millions en 2037, puis décroissance
- Solde naturel négatif depuis 2025 (première fois depuis 1945)
- +5,8 millions de personnes de 65 ans ou plus d'ici 2070
- Rapport de dépendance démographique : 40 personnes de 65 ans ou plus pour 100 personnes de 20-64 ans en 2026 → 49 en 2040 → 62 en 2070
- Fourchette 2070 selon scénarios : 61 à 71 millions

**À récupérer :** les **16 scénarios alternatifs** publiés en complément du scénario central. Ils constituent le socle naturel de l'analyse de sensibilité du simulateur.

**Ressource complémentaire :** pyramides des âges interactives de projections 2026 sur le site INSEE.

### 2.2 Rapport annuel du COR — juin 2026

**Référence :** Conseil d'orientation des retraites, 13e rapport annuel, *Évolutions et perspectives des retraites en France*, 11 juin 2026.

**Statut :** publié. PDF principal (~5,6 Mo), synthèse séparée, diaporama et **données chiffrées téléchargeables** sur le site du COR.

**Nouveautés de l'édition 2026 :**
- Intégration des nouvelles projections démographiques INSEE
- Hypothèses économiques reconduites depuis le scénario antérieur
- Deux nouveaux cas types de non-salariés : exploitant agricole et médecin libéral
- Approche générationnelle de l'écart de pension femmes/hommes, en complément de l'approche annuelle

**Chiffrage de référence :** déficit du système de retraite estimé à 5,1 milliards d'euros en 2025, soit environ 0,2 % du PIB. Pas de retour à l'équilibre à long terme dans le scénario central.

**Usage pour le projet :** c'est le **document de calage principal**. Les annexes chiffrées fournissent les trajectoires par régime auxquelles la microsimulation devra être recalée. Les hypothèses économiques du COR (productivité, chômage, indexation) doivent être reprises telles quelles dans `docs/hypotheses.md`, avec mention explicite de leur origine.

**À faire :** télécharger le rapport, la synthèse et surtout les **fichiers de données**, et archiver le millésime. Le COR republie chaque année ; il faut figer la version utilisée.

---

## 3. Sources agrégées par régime

### 3.1 Panorama DREES « Les retraités et les retraites »

| Édition | Année couverte | Parution |
|---|---|---|
| 2025 | 2023 | juillet 2025 |
| **2026** | **2024** | **septembre 2026** (annoncée) |

**Chiffres clés de l'édition 2025 (année 2023) :**
- 17,2 millions de retraités de droit direct des régimes français fin 2023, en hausse de 1,3 % sur un an
- 370 milliards d'euros de pensions versées, soit 13,1 % du PIB — premier poste de dépenses de la protection sociale
- Âge conjoncturel de départ : 62 ans et 9 mois fin 2023
- Écart de pension de droit direct femmes/hommes : −37,5 % en 2023, réduit après prise en compte de la réversion
- Cumul emploi-retraite : 606 000 personnes en 2023, contre 466 000 en 2018

**Sources sous-jacentes :** EIR, EACR (enquête annuelle auprès des caisses de retraite), et modèle ANCETRE.

**Décision à prendre :** l'édition 2026 sort en septembre, dans quelques semaines. Deux options — démarrer sur l'édition 2025 et rebaser ensuite, ou attendre. Recommandation : **démarrer maintenant sur 2025**, en isolant proprement les fichiers de calage pour que le rebasage soit une opération mécanique.

### 3.2 Données open data EACR / ANCETRE

**Statut : disponible immédiatement, sans démarche d'accès.** C'est le gisement le plus rapidement exploitable.

Mise à disposition de mai 2026 : effectifs de retraités et montants de pensions versées, **de 2004 à 2024**, ventilés par sexe, âge, lieu de naissance, conditions de liquidation et montant perçu. Couvre également les rentes d'invalidité et d'incapacité permanente.

**Rôle dans le projet :** matrice de calage principale de la population synthétique. Les données 2024 étant déjà publiées alors que le Panorama correspondant ne sortira qu'en septembre, elles constituent le millésime le plus récent disponible.

### 3.3 Sources par caisse

À collecter individuellement : CNAV, AGIRC-ARRCO, SRE (fonction publique d'État), CNRACL, MSA, SSI, CNAVPL/CIPAV.

**Point d'attention :** l'AGIRC-ARRCO est un régime de droit privé géré paritairement. Ses comptes ne figurent pas dans le périmètre LFSS. Toute réforme touchant les pensions complémentaires relève de la négociation entre partenaires sociaux, pas de la loi — distinction à faire apparaître dans le simulateur, car elle conditionne la faisabilité politique d'un scénario autant que son chiffrage.

### 3.4 Comptes publics

- Annexes du PLFSS (rapport à la Commission des comptes de la Sécurité sociale)
- Rapports annuels de la Cour des comptes sur l'application des LFSS
- Comptes de la protection sociale (DREES)

Nécessaires pour la ventilation par sous-secteur d'administration publique (État / ASSO / APUL) exigée par la cascade de décomposition.

---

## 4. Sources individuelles

C'est le nœud du projet. Aucune de ces sources n'est en accès libre.

### 4.1 EIR — Échantillon interrégimes de retraités

**Contenu :** panel permettant de reconstituer le montant de pension **tous régimes** par retraité, ainsi que les conditions de départ. Construit par appariement des données administratives de la quasi-totalité des régimes français, en « double aveugle ».

**Périodicité :** collecte tous les 4 ans.

**Millésime en cours :** EIR 2024, dont l'appariement avec les données fiscales est réalisé **en 2026**. Cet appariement fiscal est précisément ce dont le module d'imposition a besoin : il permet d'apprécier les revenus du ménage, le niveau de vie des retraités, le lien entre pension et autres revenus, et le non-recours au minimum vieillesse.

**Accès :** ADISP/Progedo pour les versions diffusables (l'EIR 2016 dispose d'un DOI : 10.13144/lil-1535) ; CASD pour les versions appariées (panel tous actifs, ENIACRAMS, enquête Vie quotidienne et santé).

**Base juridique :** loi n° 84-575 du 9 juillet 1984, art. 1er ; articles R161-59 à R161-69 du code de la sécurité sociale. Appariement fiscal prévu par l'article 2 du décret n° 2015-1570 du 1er décembre 2015.

### 4.2 EIC — Échantillon interrégimes de cotisants

**Contenu :** reconstitution de la **carrière complète année par année** pour un échantillon anonyme, tous régimes confondus. Caractéristiques individuelles renseignées par les caisses : sexe, année de naissance, département de naissance, nombre d'enfants, département de résidence, catégorie sociale.

**Usage de référence :** c'est la source sur laquelle la DREES a construit en 2012-2013 le modèle de microsimulation **TRAJECTOiRE**, utilisé pour projeter effectifs de retraités et âges de liquidation sous différentes hypothèses de fin de carrière et différents paramètres législatifs.

**Pourquoi c'est indispensable :** sans carrières individuelles, impossible de simuler l'effet d'un changement de durée d'assurance ou d'âge légal. Les agrégats ne suffisent pas.

**Accès :** CASD, y compris versions appariées (Pôle Emploi, panel tous actifs, EDP).

### 4.3 ERFS — Enquête Revenus fiscaux et sociaux

**Contenu :** environ 50 000 ménages, avec plusieurs centaines de variables. Réunit les informations sociodémographiques de l'enquête Emploi, les données administratives CNAF / CNAV / CCMSA, et le **détail des revenus déclarés à l'administration fiscale**.

**Rôle :** c'est la seule source permettant de calculer l'IR au niveau du foyer fiscal réel. Indispensable au module d'imposition.

**Limites de champ, à documenter explicitement :**
- France métropolitaine uniquement
- **Logements ordinaires uniquement** — les personnes en établissement collectif sont exclues. Pour une étude sur les retraités, cela exclut les résidents d'EHPAD, population non négligeable et atypique en termes de revenus et de prestations. À signaler dans toute sortie du simulateur.

**Décalage temporel :** à l'été N+1, quand on simule la législation de l'année N, l'ERFS la plus récente porte sur les revenus de N−2. Il y a donc structurellement deux ans de retard, à combler par vieillissement des données.

**Accès :** strictement contrôlé en raison des données fiscales. Via CASD.

---

## 5. Moteurs de calcul réutilisables

### 5.1 OpenFisca-France-Pension

- Modélisation des principaux régimes de retraite français, inspirée de TiL-Pension
- Python ≥ 3.9, licence AGPL v3, statut « Production/Stable » sur PyPI
- Dépôt : `openfisca/openfisca-france-pension`

**Rôle :** moteur de règles de liquidation. Évite de recoder décote, surcote, durée d'assurance, minimum contributif, réversion, régime par régime.

**À vérifier en priorité :** le rythme de maintenance du dépôt et la présence des paramètres post-réforme 2023 et post-suspension LFSS 2026. Si les paramètres récents manquent, il faudra les ajouter — travail non trivial mais borné, et de toute façon nécessaire.

### 5.2 OpenFisca-France

- Modélisation du système socio-fiscal français : IR, CSG, prestations
- Même moteur que le module pension, donc chaînage naturel
- API web publique disponible (documentation Swagger), utile pour prototyper sans installation

### 5.3 INES

- Co-produit par INSEE, DREES et CNAF
- Simule sur barèmes les prestations et prélèvements de chaque ménage à partir de l'ERFS
- **Open source depuis 2016**, publié sur la forge ADULLACT
- Migration de SAS vers **R** à partir de la version Ines 2023
- Permet de simuler n'importe quelle année de législation récente sur n'importe quel millésime d'ERFS récent
- Utilisé par l'OFCE, la Cour des comptes, l'IGF, l'IGAS et divers Hauts Conseils

**Arbitrage à trancher :** OpenFisca-France ou INES pour le module fiscal ?

| | OpenFisca-France | INES |
|---|---|---|
| Langage | Python | R (depuis 2023) |
| Intégration avec le module pension | Native | À construire |
| Légitimité institutionnelle | Bonne | Référence officielle |
| Données | Agnostique | Adossé à l'ERFS |
| Accès aux données requis | Non | Oui (CASD) |

**Recommandation :** OpenFisca-France pour la v1, pour l'homogénéité technique et l'absence de dépendance à un accès CASD. INES comme **référence de validation** : rejouer un cas de figure connu dans les deux modèles et comparer les écarts est le meilleur test de crédibilité disponible.

---

## 6. Trous identifiés et risques

### 6.1 Le trou structurel : joindre pension et fiscalité

L'EIR donne la pension par régime sans le ménage. L'ERFS donne le ménage et l'impôt sans le détail par régime. **Aucun fichier public ne fait les deux.** L'appariement EIR 2024 × données fiscales, réalisé en 2026 par la DREES, est exactement le pont manquant — mais il est interne à la DREES et son accès externe reste à vérifier.

**Contournement pour la v1 :** appariement statistique entre les deux sources sur variables communes (âge, sexe, tranche de pension, situation matrimoniale). Méthode standard, mais qui introduit une incertitude à quantifier et à documenter, pas à masquer.

### 6.2 Périodicité de l'EIR

Collecte quadriennale : entre deux vagues, le modèle ANCETRE assure l'interpolation. Toute analyse par génération sur les cohortes récentes repose donc partiellement sur de l'estimation, pas de l'observation. La DREES le signale elle-même pour les générations à partir de 1954.

### 6.3 Délais d'accès aux données

Les demandes CASD supposent un projet de recherche formalisé, une habilitation et un délai d'instruction. **À lancer immédiatement si la voie microdonnées réelles est retenue** — c'est le chemin critique du projet, très en amont du développement.

### 6.4 Le baseline mouvant

Réforme suspendue jusqu'en janvier 2028, élection présidentielle en 2027. L'OFCE écarte explicitement, dans ses propres travaux, tant l'hypothèse d'une suspension définitive que celle d'un rattrapage abrupt — c'est-à-dire que les deux extrêmes sont plausibles mais non retenus par convention. Le simulateur devrait pouvoir tester les deux.

### 6.5 Champ géographique

ERFS limité à la France métropolitaine. Les données de pension couvrent les retraités résidant en France **ou à l'étranger**. Les champs ne coïncident pas : à harmoniser explicitement, sous peine d'écarts inexpliqués au calage.

---

## 7. Séquencement proposé

| Phase | Contenu | Dépendance |
|---|---|---|
| **0** | Baseline législatif paramétré (B0/B1/B2). Archivage des millésimes COR 2026 et INSEE 2026. | Aucune — démarrable immédiatement |
| **1** | Population synthétique de retraités calée sur EACR/ANCETRE 2024, par régime, génération et tranche de pension. | Open data seul |
| **2** | Adjonction d'une structure de ménage par appariement statistique sur ERFS agrégée. | Open data + tables de contingence publiées |
| **3** | Module fiscal : chaînage OpenFisca-France (CSG, IR, prestations sous conditions de ressources). | Phase 2 |
| **4** | Cascade de décomposition et ventilation par sous-secteur d'APU. | Phase 3 |
| **5** | Dynamique de projection 1 / 2 / 5 / 10 / 15 / 20 ans sur hypothèses INSEE 2026 et COR 2026. | Phase 1 |
| **6** | Substitution des microdonnées réelles (EIR/EIC) si accès CASD obtenu. | Démarche à lancer dès maintenant, en parallèle |
| **7** | *Différé* — bouclage macroéconomique : consommation, TVA, activité. | Phases 1-6 |

Les phases 0 à 5 sont réalisables **sans aucun accès à des données confidentielles**. C'est le point important : le projet peut avancer jusqu'à un prototype complet et validable avant même que la moindre demande CASD n'aboutisse.

---

## 8. Actions immédiates

1. Télécharger et archiver : rapport COR juin 2026 + fichiers de données ; INSEE projections 2026 scénario central **et 16 variantes** ; open data EACR/ANCETRE 2004-2024
2. Lire le texte de l'article 105 de la LFSS 2026 et les décrets d'application, notamment le décret adaptant les paliers carrières longues
3. Auditer l'état de `openfisca-france-pension` : dernière activité du dépôt, couverture des paramètres 2023-2026
4. Décider : démarrer sur Panorama 2025 ou attendre l'édition 2026 de septembre
5. Si microdonnées réelles souhaitées : initier la démarche CASD sans attendre

---

*Toute hypothèse retenue dans la suite du projet doit être consignée dans `docs/hypotheses.md` avec sa source, son millésime et sa date de consultation. C'est ce qui rendra le modèle réutilisable pour les autres postes de dépense publique.*
