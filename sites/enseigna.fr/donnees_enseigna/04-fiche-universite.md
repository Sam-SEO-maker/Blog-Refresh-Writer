# 4. Fiches université `/s/`

> 📄 **Dossier « Enseignement supérieur »** — [Index](00-index.md) · [1. Principes](01-principes-et-perimetres.md) · [2. Fiches lycée](02-fiche-lycee.md) · [3. Pages ville et département](03-ville-et-departement.md) · [4. Fiches université](04-fiche-universite.md) · [5. Limites et tables](05-limites-et-tables.md)

---

## 4. Page `/s/` — sections ajoutées sur une UNIVERSITÉ (chantier distinct)

> ⚠️ **À la différence des volets 2 et 3, ce volet ne complète pas des pages
> existantes : les fiches d'universités sont à créer.** Aucune n'existe aujourd'hui —
> `/s/sorbonne-universite`, `/s/universite-paris-1-pantheon-sorbonne` et
> `/s/universite-sorbonne-nouvelle-paris-3` renvoient toutes un 404, et la page ville de
> Paris n'affiche que Lycées, Collèges et Écoles.
>
> Ce n'est pas un nouveau **type** d'URL — `/s/` existe et sert déjà tous les
> établissements — mais **65 nouvelles entrées** en base établissements (145 écoles et
> 25 grands établissements en plus si le périmètre s'élargit).

**Même gabarit `/s/` que les fiches lycée** ([volet 2](02-fiche-lycee.md)), même fil d'Ariane — seules les sections affichées diffèrent.
Autre différence : **le périmètre de classement est l'académie**, pas le département
(« ⭐ 2/4 académie de Rennes »).

Le référentiel `fr-esr-principaux-etablissements-enseignement-superieur.csv` fournit de quoi
créer ces fiches : **65 universités**, avec nom, sigle, adresse, code postal, coordonnées
GPS, académie, typologie et effectif étudiant — tous renseignés à 100 %.

### Ce qui est faisable maintenant, et ce qui demande une récolte

| Contenu | Disponible ? | Source |
|---|---|---|
| **Licences** (offre + admissions) | ✅ **Oui** | `fr_esr_admissions_parcoursup.csv` — 3 852 formations, dont 98 pour Sorbonne Université, 46 pour Paris 1 |
| **Campus et antennes** | ✅ Oui | `fr-esr-cartographie_formations_parcoursup.csv` — 84 UAI multi-communes |
| **Effectif, académie, typologie** | ✅ Oui | Le référentiel ci-dessus |
| **Masters** (offre + admissions) | ✅ **Oui** | `fr-esr-mon_master.csv` — session 2025, 110 UAI, 315 mentions. Le master ne passe pas par Parcoursup mais par **MonMaster** |
| **Insertion professionnelle** | ⚠️ Partiel — 15,7 % de jointure | `fr-esr-insersup.csv`, surtout au niveau master |
| **Doctorats** | ❌ **Non** | Aucune ligne doctorat dans les fichiers réunis |
| **UFR / composantes** | ❌ **Non** | 0 UFR dans le référentiel, qui s'arrête à l'établissement. L'organisation interne des universités n'est pas publiée en open data — même mur que pour les IUT, qui portent leur propre UAI sans lien exploitable vers l'université mère |

**Périmètre proposé pour une V1** : licences + campus + masters, soit les tableaux 4.1 à
4.3 ci-dessous.

Le master a été ajouté après analyse de `fr-esr-mon_master` : contrairement à ce qu'on
pensait, le millésime **2025** est disponible et bien rempli (110 UAI, volumes à 100 %).
Il répond à la question que se pose un lycéen choisissant une licence — **où mène-t-elle ?**
— et évite qu'une fiche université s'arrête à bac+3 sans dire ce qu'il y a après.

**À prévoir pour une V2 — une seconde phase de recherche de données** :

| Niveau | Piste identifiée | Réserve |
|---|---|---|
| **Doctorat** | `fr-esr-effectifs-doctorants-docteurs-ecoles-doctorales` repéré au catalogue | ⚠️ **Pertinence à trancher** : le doctorat est probablement hors scope d'Enseigna, dont le lecteur est un lycéen ou un parent d'élève. À arbitrer avant toute récolte |
| **UFR / composantes** | Aucune | La récolte a de fortes chances de ne rien trouver en open data : ce serait un chantier de collecte manuelle, université par université |

Le doctorat a une pertinence éditoriale faible : c'est un choix qui se fait cinq ans plus
tard, hors du moment de décision que couvre le site.

### Bandeau 4.0 — indicateurs clés

> **34 926 étudiants** · Université pluridisciplinaire avec santé · **⭐ 1/4 académie de
> Rennes**
>
> *Exemple : Université de Rennes.*

- **Source** : `fr-esr-principaux-etablissements-enseignement-superieur.csv`. `Étudiants inscrits (2024)` est renseigné pour **les 65 universités**
  (1 542 863 étudiants au total), `Typologie universitaire` également.
- ⚠️ **Mais seulement pour 109 des 245 établissements du référentiel (44 %)** — les écoles
  et grands établissements en sont largement dépourvus. **`fr-esr-atlas-effectifs-etablissements.csv`
  récupère 108 des 136 manquants**, portant la couverture du bandeau à **89 %**. C'est le
  seul fichier du corpus qui comble ce trou.
- Les deux sources ne donnent pas exactement le même total : l'Atlas est « hors doubles
  comptes CPGE ». Ne pas chercher à les faire coïncider — choisir une source par
  établissement, référentiel en priorité, Atlas en repli.
- L'Atlas permet en plus une **ventilation par niveau** (BAC+1 → BAC+6), qui caractérise le
  profil d'un établissement : Aix-Marseille passe de 18 294 en BAC+1 à 6 538 en BAC+6.
- Le rang se calcule **dans l'académie** : médiane de 2 universités par académie, maximum 5
  — le palmarès est donc court et lisible.
- ⚠️ **Classer par typologie**, pas en vrac : comparer une université tertiaire de 6 000
  étudiants à une pluridisciplinaire avec santé de 60 000 n'aurait pas de sens.
- L'effectif répond au besoin d'un « Nb d'étudiants » cohérent avec le « Nb de lycéens »
  des fiches lycée. C'est F7 qui le fournit — la tentative via SISE échouait à 13,7 % de
  recouvrement.

### Bloc 4.0-bis — maillage « Les autres universités de l'académie de {X} »

Liste de liens (nom + rang), fiche courante exclue. Bloc navigationnel dont le contenu
varie d'une fiche à l'autre — pas un tableau de classement dupliqué (voir [volet 1 — principes](01-principes-et-perimetres.md)).

### Tableau 4.1 — « Les licences de {université} »

**4 colonnes** :

| Licence | Places | Candidats | Taux d'accès |
|---|---|---|---|
| Licence Droit | 620 | 4 812 | 38 % |
| Licence Psychologie | 340 | 3 105 | 22 % |

- **Source** : `fr_esr_admissions_parcoursup.csv`, filtre `Licence` / `Licence_Las` / `PASS`,
  jointure UAI.
- **Couverture** : 3 052 licences + 513 L.AS + 287 PASS, chiffres à 100 %.

**Colonnes disponibles mais non retenues** — `Admis`, `% mentions TB`, `% boursiers`,
`% même académie`.

### Tableau 4.2 — « Campus et antennes »

**4 colonnes** :

| Campus / antenne | Ville | Formations | Places |
|---|---|---|---|
| Université de Rennes (siège) | Rennes | 32 | 3 584 |
| Site de Saint-Brieuc | Saint-Brieuc | 2 | 275 |
| Antenne de Lorient | Lorient | 3 | 67 |
| Antenne de Vannes | Vannes | 3 | 60 |
| Antenne de Pontivy | Pontivy | 1 | 22 |

*Exemple réel : Université de Rennes, présente dans 3 des 4 départements de son académie.*

⚠️ **« Formations » signifie ici formations Parcoursup**, pas l'offre totale de
l'établissement. 32 formations pour une université de 34 926 étudiants peut surprendre :
Parcoursup ne référence que l'offre post-bac ouverte aux lycéens (essentiellement les
licences). Ni les masters, ni les doctorats, ni la formation continue n'y figurent.

⚠️ **Les composantes portent leur propre UAI** et apparaissent comme des établissements
distincts dans les fichiers : `I.U.T de Rennes` (6 formations),
`UFR Sciences Médicales - Université de Rennes` (3), `ENSSAT Lannion`… Les rattacher à leur
université mère demanderait une table de correspondance qui n'existe pas en open data —
c'est le même mur que pour les IUT (voir le tableau de disponibilité ci-dessus).

À ne pas confondre non plus : **Université de Rennes** et **Université Rennes 2** sont deux
établissements distincts (respectivement 32 et 54 formations Parcoursup), pas deux
composantes d'un même ensemble.

- **Source** : `fr-esr-cartographie_formations_parcoursup.csv`, communes distinctes du même
  UAI. **84 UAI sont multi-communes.**
- C'est ce tableau qui fait le maillage retour vers les pages ville et département : chaque
  ligne pointerait vers `/v/{ville}`.
- La colonne `Département` a été écartée — elle se déduit de la ville et coûterait une
  cinquième colonne.

### Tableau 4.3 — « Les masters de {université} »

**4 colonnes** :

| Mention | Candidats | Propositions | Part de propositions |
|---|---|---|---|
| Anthropologie | 258 | 67 | 26 % |
| Administration et liquidation d'entreprises | 612 | 69 | 11 % |

*Exemple réel : Aix-Marseille Université.*

- **Source** : `fr-esr-mon_master.csv`, session 2025, jointure UAI.
- **Couverture** : 110 UAI, **24 mentions par université en médiane** — un tableau
  substantiel mais lisible.
- ⚠️ **Le calcul se fait sur les propositions, jamais sur les acceptations.** En master, un
  candidat postule à des dizaines de mentions et n'en accepte qu'une : `admis / candidats`
  donne une médiane de 6,5 %, contre 21,2 % pour `propositions / candidats`. Le premier
  calcul mesure surtout le choix des candidats admis ailleurs, pas la sélectivité de
  l'établissement. Détail et exemple chiffré dans `note_fr-esr-mon_master.md`.
- La colonne `origine_dominante` (« Licence générale — 89 % ») complète en **dépliable**,
  comme le tableau 1.3 : elle ferait sinon une cinquième colonne, hors gabarit.
- **Filtrer sur `alternance`** : les mentions en alternance sont sur des lignes distinctes
  et relèvent d'une logique d'admission différente.
- ⚠️ **Tableau par établissement uniquement, jamais géographique.** MonMaster ne référence
  que les masters recrutant par la plateforme : **les 18 IEP en sont totalement absents**,
  ainsi que les écoles à recrutement propre. Un tableau « les masters à {ville} » serait
  donc faux par omission — certaines académies n'y sont représentées que par leurs
  universités.

**Colonnes disponibles mais non retenues** — `n_clas_total` (classés), `n_accept_total`,
`pct_femmes_admis`, `nb_parcours`, `lieux`.

### Tableau 4.4 — « Les étudiants par niveau »

**3 colonnes** :

| Niveau | Étudiants | Part |
|---|---|---|
| BAC + 1 | 19 681 | 28 % |
| BAC + 2 | 11 435 | 16 % |
| BAC + 3 | 11 761 | 16 % |
| BAC + 4 | 10 452 | 15 % |
| BAC + 5 | 11 535 | 16 % |
| BAC + 6 et plus | 6 366 | 9 % |

*Exemple réel : Université de Lille, 71 524 étudiants (rentrée 2024).*

- **Source** : `fr-esr-atlas-effectifs-etablissements.csv`, jointure UAI, agrégation par
  `degre_etudes`.
- **Couverture** : 6 294 établissements et 7 941 composantes — la plus large du corpus.
- La lecture en pyramide caractérise un établissement d'un coup d'œil : une université de
  masse décroît régulièrement, une école spécialisée est concentrée sur BAC+4/+5.
- La ligne « Inférieur ou égal au baccalauréat » (294 étudiants à Lille, 0,4 %) gagnerait à
  être masquée : elle est marginale et brouille la lecture.
- `dont_femmes` / `dont_hommes` permettraient une 4e colonne, mais l'écart entre niveaux
  reste modéré (51 à 65 % à Lille) — peu discriminant, donc écarté.

⚠️ **Le niveau n'est pas le diplôme** : BAC+1 mélange L1, PASS et 1re année d'école ; BAC+5
mélange M2 et dernière année d'ingénieur. Ce tableau décrit un **volume**, pas une offre de
formation.

⚠️ **Ne pas rapprocher ce total de l'effectif du référentiel** (bandeau 4.0) : l'Atlas est
« hors doubles comptes CPGE » et ne compte donc pas la même population.

### Tableau 4.5 — « Les études de santé » (universités concernées)

**3 colonnes** :

| Filière | Étudiants | |
|---|---|---|
| Médecine | 8 634 | |
| Pharmacie | 1 521 | |
| Odontologie | 694 | |
| PASS et PluriPASS | 1 381 | *1re année* |
| Licence accès santé (L.AS) | 242 | *1re année* |

*Exemple réel : Université de Bordeaux.*

- **Source** : `fr-esr-diplomes-prepares-etablissements.csv`, filtre sur `perimetre`
  (`SANTE` puis `PASS_LAS`), jointure UAI.
- **Couverture** : Médecine 44 UAI · Pharmacie 27 · Odontologie 23 · PASS/L.AS 64.
  À n'afficher que sur les universités concernées.
- Séparer visuellement les **1res années** (PASS, L.AS) des **filières** : ce ne sont pas
  des populations comparables, la première alimente les secondes.

⚠️ **La maïeutique (sage-femme) n'est pas isolable** dans ce fichier — ne pas l'annoncer
comme une filière affichable.

⚠️ **Aucun chiffre sur le passage en 2e année.** Ni capacités d'accueil, ni taux de
réussite : depuis 2019 chaque université fixe ses propres capacités, il n'existe donc aucune
source nationale. C'est précisément la question que se posent les familles — elle relèverait
d'un traitement éditorial, pas d'un tableau. Détail dans
`note_fr-esr-diplomes-prepares-etablissements.md`.

### Tableau 4.6 — « Les IEP » (fiches IEP uniquement)

**Les 18 IEP recensés dans Parcoursup** n'ont ni fiche université, ni données MonMaster.
Deux chiffres seulement seraient affichables, sur le même modèle pour chacun :

| Indicateur | Source |
|---|---|
| Étudiants (tous cycles, 2024) | `fr-esr-atlas-effectifs-etablissements.csv` |
| Étudiants en 2e cycle (2024-25) | `fr-esr-diplomes-prepares-etablissements.csv` |

Valeurs réelles pour les IEP couverts par les deux fichiers :

| IEP | Tous cycles (Atlas) | 2e cycle (Diplômes) | Rattachement du 2e cycle |
|---|---|---|---|
| Sciences Po Paris | 12 494 | 6 791 | IEP |
| Sciences Po Bordeaux | 2 333 | 2 252 | IEP |
| Sciences Po Lyon | 1 995 | 1 567 | IEP |
| Sciences Po Grenoble | 1 953 | 1 486 | Université Grenoble Alpes |
| Sciences Po Lille | 1 756 | 1 689 | Université de Lille |
| Sciences Po Aix | 1 707 | 760 | IEP |
| Sciences Po Toulouse | 1 638 | 1 107 | Université Toulouse Capitole |
| Sciences Po Strasbourg | 1 617 | 859 | Université de Strasbourg |
| Sciences Po Rennes | 1 377 | 1 000 | Université de Rennes |
| Sciences Po Saint-Germain-en-Laye | 919 | — | — |
| IEP de Fontainebleau (UPEC) | 721 | — | — |

⚠️ Les deux colonnes viennent de **fichiers et de millésimes différents** et ne se
soustraient pas. La 4e colonne explique pourquoi : dans le fichier Diplômes, plus de la
moitié des IEP voient leur 2e cycle **rattaché à leur université de tutelle**, pas à l'IEP.
Une jointure sur le seul UAI de l'IEP les perdrait.

À noter, `CY Cergy Paris Université` porte également 760 étudiants en 2e cycle IEP — même
valeur que Sciences Po Aix, sans lien entre les deux.

- L'admission post-bac reste portée par `fr_esr_admissions_parcoursup.csv` (18 IEP,
  59 formations, taux d'accès renseigné à 100 %) — c'est le tableau 1.1 appliqué à un IEP.
  **Tous les IEP y figurent**, y compris les 7 campus délocalisés.
- ⚠️ **Filtrer par la liste des UAI d'IEP**, jamais par le libellé : « politiques » ramasse
  aussi les UFR de droit et science politique. 11 IEP sur 18 sont retrouvés dans l'Atlas,
  les 7 autres étant des campus délocalisés de Paris et Lyon.
- ⚠️ **Aucune offre de master affichable** : les IEP recrutent hors MonMaster, seul le
  volume d'étudiants est connu.

### Bloc 4.7 — insertion (partiel, à arbitrer)

| Domaine disciplinaire | Taux d'emploi à 12 mois | Moyenne France |
|---|---|---|

- **Source** : `fr-esr-insersup.csv`. `Domaine disciplinaire` a 5 valeurs (Sciences-technologies-santé,
  Droit-économie-gestion, Sciences humaines et sociales, Lettres-langues-arts).
- Les lignes `Code UAI = all` de ce fichier donnent la **moyenne France** : à écarter des
  tableaux par établissement, mais utilisables comme colonne de comparaison.
- ⚠️ **Couverture faible : 15,7 %** (72 UAI joignables sur 460).
- ⚠️ **Réserve de fond, au-delà de la couverture.** L'insertion ne couvre pas les poursuites
  d'études : un diplômé de licence qui entre en master n'est pas une sortie vers l'emploi.
  Or **63 % des diplômés 2024 de licence générale s'inscrivent en master l'année suivante**
  (SIES, niveau national) — l'indicateur ne porte donc que sur une minorité non
  représentative. Il mesure par ailleurs un statut à une date, sans qualification : un
  diplômé employé en dessous de son niveau compte comme inséré, celui qui trouve son poste
  après la fenêtre d'enquête ne compte pas.
- **Recommandation** : affichable comme information sur les diplômes professionnalisants
  terminaux (BTS, apprentissage — voir [volet 2](02-fiche-lycee.md)), mais **pas comme
  critère de classement** d'une université, et pas comme indice de qualité d'une formation.

---
