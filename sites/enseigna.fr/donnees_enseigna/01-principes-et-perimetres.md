# 1. Principes et périmètres

> 📄 **Dossier « Enseignement supérieur »** — [Index](00-index.md) · [1. Principes](01-principes-et-perimetres.md) · [2. Fiches lycée](02-fiche-lycee.md) · [3. Pages ville et département](03-ville-et-departement.md) · [4. Fiches université](04-fiche-universite.md) · [5. Limites et tables](05-limites-et-tables.md)

---

## Les fichiers livrés (dossier `donnees_enseigna/`)

| # | Fichier | Contenu | Lignes |
|---|---|---|---|
| **F1** | `fr-esr-cartographie_formations_parcoursup.csv` | **Inventaire** : qui propose quoi, et où (session 2026) | 25 838 |
| **F2** | `fr_esr_admissions_parcoursup.csv` | **Chiffres voie scolaire** : places, candidats, admis, taux d'accès (2025) | 14 252 |
| **F3** | `fr-esr-parcoursup-apprentissage.csv` | **Inventaire + volume apprentissage** (2025) | 11 536 |
| **F4** | `fr-en-inserjeunes-lycee_pro-bts.csv` | Insertion après BTS scolaire, par établissement | 1 971 |
| **F5** | `fr-en-inserjeunes-cfa.csv` | Insertion après apprentissage, par CFA | 2 758 |
| **F6** | `fr-esr-insersup.csv` | Insertion après diplôme du supérieur | 10 399 |
| **F7** | `fr-esr-principaux-etablissements-enseignement-superieur.csv` | **Référentiel** des établissements : académie, typologie, effectif étudiant | 245 |
| **F8** | `fr-esr-parcoursup-enseignements-de-specialite-bacheliers-generaux-3.csv` | **Débouchés par doublet de spécialités** (national, bac 2025) | 17 211 |
| **F9** | `fr-esr-effectifs-cpge.csv` | **Effectifs étudiants en CPGE** par lycée, spécialité et sexe (2025-2026) | 1 707 |
| **F10** | `fr-esr-mon_master.csv` | **Admissions en master** (2025) : candidats, propositions, origine des candidats | 3 644 |
| **F11** | `fr-esr-atlas-effectifs-etablissements.csv` | **Effectifs par établissement et par niveau** BAC+1 → BAC+6 (rentrée 2024) | 22 068 |
| **F12** | `fr-esr-diplomes-prepares-etablissements.csv` | **Santé et IEP** : effectifs par filière (2024-25) | 6 150 |

Chaque fichier a sa note (`note_<nom>.md`) : format, pièges, clés de jointure.

Les codes **F1 à F12** ne servent que de raccourci dans ce tableau. **Dans les sections
suivantes, chaque tableau nomme son fichier en toutes lettres** — pas besoin de revenir ici.

⚠️ **Trois millésimes différents cohabitent, c'est normal** : Parcoursup et MonMaster sont
en **session 2025**, les CPGE en **année scolaire 2025-2026**, l'Atlas en **rentrée 2024** et
les diplômes en **2024-25**. Les effectifs du supérieur sont publiés avec un an de décalage ;
il n'existe pas de millésime 2025 pour F11 et F12.

⚠️ **F11 : la colonne `effectifhdccpge` ne contient PAS les CPGE** (« hors doubles
comptes CPGE »). Pour les CPGE, c'est **F9** qui fait foi — plus récent et plus détaillé.
Voir `note_fr-esr-atlas-effectifs-etablissements.md`.

⚠️ **F8 n'a ni UAI ni géographie** : il n'alimente aucun tableau des pages `/v/`, `/d/`
ou `/s/`. Il sert un usage distinct, sur les **fiches lycée existantes** — voir [§1.5](02-fiche-lycee.md).

---

## Conventions des fichiers

Ce mémo ne porte pas sur les diplômes eux-mêmes, mais sur la façon dont **ces fichiers**
les nomment et les comptent — là où les conventions ne sont pas devinables.

### Trois notions qui ne veulent pas dire ce qu'on croit

| Terme du fichier | Ce que c'est vraiment |
|---|---|
| **Taux d'accès** | Part des candidats ayant reçu une proposition. Mesure la **difficulté d'entrée**, jamais la qualité de la formation |
| **Places** (`Capacité`) | Places ouvertes à la rentrée — donc les **entrants**, pas l'effectif total de la formation, qui compte 1re et 2e année |
| **Admis** | Candidats ayant **accepté** la proposition. Quasiment toujours égal aux places (48/48, 24/24) : peu discriminant, écarté des tableaux |

### Les libellés de CPGE sont abrégés en majuscules

Le fichier des effectifs écrit `CL. PREPAR. ECON.&COMMERC.GENER.` pour ECG,
`BCPST (BIO.CHIM.PHYS.SC TERRE)`, `CL.PR.ENS RENNES (DEP.DR.EC.MAN.)`. **37 spécialités**
au total, réparties en 3 filières (`Filière` : scientifique, économique, littéraire).

Une table de correspondance sera nécessaire pour un affichage propre — le fichier des
admissions, lui, utilise des libellés lisibles (`ECG - Mathématiques appliquées + ESH`).

### Voie scolaire vs apprentissage

Ce n'est pas une nuance de vocabulaire mais **le critère qui détermine si un taux d'accès
existe** : en apprentissage, l'admission dépend de la signature d'un contrat avec un
employeur, pas d'un classement de dossiers. D'où l'absence de taux d'accès et d'admis dans
`fr-esr-parcoursup-apprentissage.csv`.

Le même diplôme peut exister dans les deux voies, avec des chiffres différents — l'Institut
Saint-Lô propose le même BTS MCO en voie scolaire (24 places) et en apprentissage
(8 places).

### Les identifiants

| Clé | Où | Usage |
|---|---|---|
| **UAI** | Tous les fichiers | Pivot de toutes les jointures — celui de la base lycées |
| **Code interne Parcoursup de la formation** | Cartographie | Clé de la formation. Nommée `cod_aff_form` dans les admissions, `Numéro d'identification de la formation dans Parcoursup` dans l'apprentissage |
| **`code_formation`** | Cartographie | ⚠️ **Piège** — ressemble à une clé, n'en est pas une. Voir ci-dessous |
| **`mefstat11`** | InserJeunes | Code Éducation nationale, **sans correspondance** avec les codes Parcoursup |
| **`aca_id`** | Référentiel, InserSup | Code académie — périmètre de classement des universités |

**La clé à utiliser pour joindre deux formations est `Code interne Parcoursup de la
formation`** (ligne 2 du tableau) : 95 % de correspondances, toutes vérifiées sur le même
établissement.

⚠️ **Le piège `code_formation`.** Cette colonne de la cartographie ressemble à une clé de
formation, mais n'a aucun rapport avec l'identifiant Parcoursup : c'est un code MESR.

Le risque n'est pas une jointure vide — c'est une jointure qui **rapproche les mauvaises
lignes**. Exemple réel, le code `5` :

| Fichier | Établissement | Formation |
|---|---|---|
| Admissions | La Prépa des INP — Nancy | Formation d'ingénieur |
| Cartographie | Lycée Tani Malandi de Chirongui (Mayotte) | Classe préparatoire |

Les deux codes sont identiques, donc la base les apparie. La requête s'exécute sans erreur
et aucune ligne ne manque, mais les données de Mayotte atterrissent sur la fiche de Nancy.

**212 codes sont dans ce cas** (~1,5 % des lignes), et aucun des 212 ne désigne le même
établissement des deux côtés — ce sont des collisions numériques pures.

Une jointure qui ne trouve rien se repère immédiatement : le tableau est vide. Celle-ci
publie des chiffres faux sans rien signaler.

**En résumé** : joindre sur `Code interne Parcoursup de la formation` (ou son équivalent
selon le fichier), jamais sur `code_formation`.

---

## Vue d'ensemble : quoi sur quelle page

**Trois types de pages seulement** : `/s/` établissement, `/v/` ville, `/d/` département.

`/s/` est **un gabarit unique qui sert tous les établissements**, du primaire au supérieur —
`/s/ecole-primaire-privee-institut-saint-lo` et `/s/lycee-general-et-technologique-ozenne`
sont la même page avec des sections différentes. Ce chantier n'ajoute donc **aucun type
d'URL** : il ajoute des sections qui s'affichent selon la nature de l'établissement.

| Page | Ce qu'on ajoute | Sections | Page existe ? | Priorité |
|---|---|---|---|---|
| **`/s/`** *lycée à post-bac* | Section « Après le bac » : ses BTS et CPGE | [volet 2](02-fiche-lycee.md) | ✅ oui | **1** |
| **`/v/` ville** | Bloc « Supérieur » : universités, IUT, écoles — hors lycées | [volet 3](03-ville-et-departement.md) | ✅ oui | **2** |
| **`/d/` département** | Classement des CPGE + formations les plus sélectives | [volet 3](03-ville-et-departement.md) | ✅ oui | **3** |
| **`/s/`** *université* | Licences, campus, insertion | [volet 4](04-fiche-universite.md) | ⚠️ **à créer** | **4** |

Les trois premières priorités **enrichissent des pages en production**. La quatrième
suppose de créer **65 fiches d'universités**, qui n'existent pas aujourd'hui — d'où sa
position en fin de séquence (détail dans le [volet 4](04-fiche-universite.md)).

Sur `/s/`, le rendu se brancherait sur la nature de l'établissement plutôt que sur un
template distinct :

| Établissement | Sections supérieur affichées |
|---|---|
| École primaire, collège | aucune — page inchangée |
| Lycée **sans** post-bac | aucune — page inchangée |
| Lycée **avec** BTS ou CPGE | **[volet 2](02-fiche-lycee.md)** — Après le bac |
| Université, IUT, école du supérieur | **[volet 4](04-fiche-universite.md)** — licences, campus, insertion |

C'est la majorité des fiches qui reste inchangée : sur l'ensemble des établissements du
site, seuls **2 586 lycées** portent une formation post-bac.

**L'ordre de priorité** (1 → 4) suit le rapport effort/gain : les fiches de lycées existent
déjà et se joignent par l'UAI ; les fiches d'universités sont à créer et leurs sources
restent incomplètes au-delà de la licence (voir [volet 4](04-fiche-universite.md) et [volet 5](05-limites-et-tables.md)).

**Aucun nouveau type d'URL ne semble nécessaire** — tout pourrait s'insérer dans les pages
existantes. Voir le point suivant, qui conditionne la structure des tables.

---

---

## 0. ⚠️ Point de structure : l'académie est un périmètre, pas une page

**La question s'est posée de créer des pages par académie.** Notre avis : plutôt non — mais
l'académie resterait indispensable comme **périmètre de classement**. C'est la nuance qui structure tout
le reste, et elle a des conséquences directes sur les tables.

### Le problème

Une **université ne relève pas d'un département** : elle est rattachée à une **académie**,
qui en couvre plusieurs, et elle est **multi-sites**.

Exemple de l'académie de **Rennes**, qui couvre 4 départements (Côtes-d'Armor, Finistère,
Ille-et-Vilaine, Morbihan) et compte 4 universités :

| Université | Étudiants | Département du siège |
|---|---|---|
| Université de Rennes | 34 926 | Ille-et-Vilaine |
| Université de Bretagne Occidentale | 24 418 | Finistère |
| Université Rennes 2 | 20 843 | Ille-et-Vilaine |
| Université Bretagne Sud | 10 545 | Morbihan |

Classer « les universités du Morbihan » reviendrait à en afficher **une seule**, alors que
trois autres y ont des implantations. L'Université de Rennes a des antennes à **Lorient**,
**Vannes**, **Saint-Brieuc** et **Pontivy** ; l'Université de Brest un site à **Quimper** ;
Rennes 2 des UFR à **Saint-Brieuc**. Le département n'est donc pas le bon périmètre.

Vérifié dans les données : **84 UAI sont multi-communes** dans la cartographie Parcoursup.

### Alors quoi — par ville ?

Non plus : la ville pose le même problème, en pire. L'Université de Rennes a des formations
dans **5 communes**. Sur `/v/lorient`, elle n'apparaîtrait que pour ses 3 formations et
67 places — ce qui ne dit rien de l'université, et donnerait une image fausse si on la
classait là-dessus.

**Un compromis serait de séparer deux objets** qui n'ont ni le même périmètre ni la même
page :

| Objet | Ce que c'est | Périmètre | Où il s'affiche |
|---|---|---|---|
| **L'implantation** | Un campus, une antenne, un IUT — un lieu physique | Commune, département | `/v/`, `/d/` — en inventaire |
| **L'établissement** | L'université elle-même | **Académie** | `/s/` — avec son classement |

Concrètement, pour l'Université de Rennes :

- Sur **`/v/lorient`** : « Université de Rennes — Antenne de Lorient · 3 formations ·
  67 places », avec un lien vers la fiche. **Aucun classement, aucune note** : c'est un
  inventaire de ce qui est physiquement présent dans la ville.
- Sur **`/v/rennes`** : la même université, mais pour ses 32 formations Parcoursup et
  3 584 places.
- Sur **`/s/universite-de-rennes`** : « ⭐ 1/4 académie de Rennes », le classement complet,
  et le tableau des 5 implantations ([volet 4](04-fiche-universite.md)).

C'est la distinction que portent les deux tables `implantations` et `etablissements_sup`
du [volet 5](05-limites-et-tables.md) : la première a la commune et le département, la seconde a l'académie et **pas** de
commune.

⚠️ **Le rang académique ne s'afficherait pas sur les pages ville et département.** Un
lecteur de `/v/lorient` verrait « 1/4 académie de Rennes » sans contexte — l'information ne
l'aide pas à choisir, et elle serait dupliquée sur toutes les communes où l'université est
présente.

### Pourquoi des pages `/a/{academie}` ne semble pas souhaitables

1. **Personne ne cherche par académie.** Les requêtes sont « BTS MCO Lyon », « prépa MPSI
   Toulouse » — jamais « formations académie de Grenoble ». Ce serait ~30 pages sans
   volume, quand les 1 651 communes et 104 départements captent déjà la longue traîne.
2. **Ça casserait la cohérence du site**, entièrement bâti sur ville → département, avec le
   fil d'Ariane Accueil > Département > Ville > Établissement. L'académie serait un
   troisième axe orphelin, sans équivalent pour les lycées, collèges et écoles.
3. **BTS et CPGE ne sont pas concernés** : ils sont hébergés dans des lycées, qui ont bien
   une ville et un département. Or ils constituent l'essentiel du post-bac — sur Rouen,
   56 BTS et 8 CPGE contre 15 licences.

### La règle suggérée

| Niveau | Ce qu'on affiche | Périmètre |
|---|---|---|
| Page **ville** `/v/` | Les **implantations** présentes (campus, antenne, IUT) + lien vers la fiche de l'université mère | Commune |
| Page **département** `/d/` | Idem + une phrase de contexte : « Le Morbihan relève de l'académie de Rennes, qui compte 4 universités » | Département |
| Fiche **université** `/s/` | Le **classement complet** : « ⭐ 2/4 académie de Rennes » + bloc « Les autres universités de l'académie » | **Académie** |

**L'unité géographique des pages ville et département est le site de formation** (campus,
antenne, IUT), **pas l'établissement**. C'est déjà le cas dans les données : le fichier des
admissions rattache « Université de Rennes - Antenne de Lorient » à la commune de Lorient,
et « Université de Brest - Site de Quimper » à Quimper.

Le classement par académie ne vit donc que sur les fiches `/s/`, ce qui évite aussi le
duplicate content : un tableau d'académie répété sur 5 pages département serait pénalisé.

### Conséquences pour les tables

- **`etablissements_sup`** porte l'**académie**, pas la commune (voir [la structure de tables](05-limites-et-tables.md)).
- **`implantations`** porte la commune et le département : **c'est elle que requêtent les
  pages ville et département**, jamais `etablissements_sup` directement ([volet 5](05-limites-et-tables.md)).
- Le champ académie vient de `fr-esr-principaux-etablissements-enseignement-superieur.csv`
  (renseigné à 100 %), **absent de la cartographie Parcoursup**.

### Si une entrée académie devenait souhaitée

Elle gagnerait à être traitée comme un **filtre ou un bloc** sur les pages existantes,
plutôt que comme un nouveau type d'URL.

---

---

## 0-bis. Le format des tableaux existants (contrainte de largeur)

Les tableaux proposés ci-dessous respectent le gabarit déjà en production. Relevé sur les
pages actuelles :

| Page | Tableau existant | Colonnes |
|---|---|---|
| Fiche lycée | Spécialités en Terminale | **3** — Spécialité · Nombre de filles · Nombre de garçons |
| Fiche lycée | Taux de réussite au bac par filière | **4** — Filière · Effectif présenté · Taux de réussite · Taux de mention |
| Page ville | Classement des lycées | **7** — # · Lycées · Nb de lycéens · Nb par professeur · Taux de réussite · Public/privé · Pro./Général |
| Page ville | Classement des collèges | **6** |
| Page ville | Écoles primaires | **5** |

**Règle retenue** : **4 colonnes maximum sur une fiche établissement**, **6 maximum sur une
page ville ou département** (hors colonne `#` de rang, très étroite).

Chaque tableau ci-dessous tient dans ce gabarit. Les données écartées sont listées sous
chaque tableau, en « colonnes disponibles mais non retenues » : elles restent dans les
fichiers si un arbitrage différent est préféré.

---
