# Note explicative — Principaux établissements d'enseignement supérieur

---

Ce fichier est le **référentiel des établissements du supérieur** : qui ils sont, où ils
sont, de quelle académie ils relèvent, et combien d'étudiants ils accueillent.

Ce n'est pas une source de données de formation — c'est la **table d'identité** qui
manquait aux autres fichiers.

**Source** : data.enseignementsup-recherche.gouv.fr — jeu
`fr-esr-principaux-etablissements-enseignement-superieur`.

---

## 1. Format et volumétrie

| | |
|---|---|
| Séparateur | `;` (point-virgule) |
| Encodage | UTF-8 avec BOM |
| Colonnes | 20 (filtrées depuis 99) |
| Lignes | **245** |
| Taille | 61 Ko |

**Une ligne = un établissement.** L'UAI est unique, il n'y a aucun doublon.

| Type d'établissement | Lignes |
|---|---|
| École | 145 |
| **Université** | **65** |
| Grand établissement | 25 |
| Autre établissement | 10 |

Secteur : 160 publics, 85 privés. 32 académies représentées.

---

## 2. Pourquoi ce fichier est indispensable

Il apporte trois informations qu'**aucun autre fichier du dossier ne contient** :

### a. L'académie de rattachement (100 % renseignée)

`Code de l'académie` et `Académie` sont remplis sur les 245 lignes. C'est **le périmètre de
classement des universités** — une université n'appartient pas à un département, elle
relève d'une académie qui en couvre plusieurs.

Sans cette colonne, impossible d'afficher « ⭐ 2/4 académie de Montpellier » sur une fiche
université. La cartographie Parcoursup ne la porte pas.

Répartition : 30 académies portent au moins une université, avec une **médiane de
2 universités par académie** (maximum 5). Le classement par académie est donc un palmarès
court et lisible, pas une liste de 60 lignes.

### b. La typologie universitaire (100 % des universités)

`Typologie universitaire` distingue :

| Typologie | Universités |
|---|---|
| Université pluridisciplinaire avec santé | 33 |
| Université pluridisciplinaire hors santé | 20 |
| Université tertiaire - lettres et sciences humaines | 8 |
| Université scientifique et/ou médicale | 5 |
| Université tertiaire - droit et économie | 4 |

C'est la colonne qui permet de **comparer ce qui est comparable** : classer une université
tertiaire de 6 000 étudiants contre une pluridisciplinaire avec santé de 60 000 n'aurait
aucun sens.

⚠️ La colonne est **vide sur les 175 non-universités** (écoles, grands établissements) —
c'est normal, la typologie ne s'applique qu'aux universités et assimilés.

### c. Les effectifs étudiants (les 65 universités)

`Étudiants inscrits (2024)` est renseigné pour **les 65 universités**, soit
**1 542 863 étudiants** au total.

C'est la réponse au besoin d'afficher un nombre d'étudiants sur les fiches université,
en cohérence avec le « Nb de lycéens » déjà présent sur les fiches lycée. Les tentatives
via SISE avaient échoué (13,7 % de recouvrement seulement).

⚠️ Sur l'ensemble des 245 lignes, l'effectif n'est renseigné qu'à 44,5 % — les écoles et
grands établissements en sont souvent dépourvus.

---

## 3. Les 20 colonnes

### Identité

| Colonne | Remplissage | Usage |
|---|---|---|
| `Code UAI de l'établissement` | 100 % | **Clé de jointure**, unique |
| `Établissement` | 100 % | Nom d'usage (ex. « Avignon Université ») |
| `Sigle` | 53,1 % | Sigle court (ex. « AU ») |
| `Type d'établissement` | 100 % | Université / École / Grand établissement / Autre |
| `Typologie universitaire` | 28,6 % (100 % des universités) | Voir §2b |
| `Secteur` | 100 % | `public` / `privé` |
| `Statut juridique` | 100 % | EPSCP, EPA… |

### Géographie

| Colonne | Remplissage |
|---|---|
| `Code de l'académie` / `Académie` | 100 % |
| `Code du département` / `Département` | 100 % |
| `Région` | 100 % |
| `Code commune` / `Commune` | 100 % |
| `Coordonnées GPS` | 100 % |

⚠️ Cette géographie est celle du **siège**. Une université étant multi-sites, ses antennes
et IUT n'y figurent pas : ils se déduisent de la cartographie Parcoursup (84 UAI
multi-communes). Voir §5.

### Contact et affichage

| Colonne | Remplissage | Usage |
|---|---|---|
| `Adresse` | 98,4 % | **Adresse postale** — utile aux infobulles de la carte Leaflet |
| `Code postal` | 100 % | |
| `Localité` | 100 % | |
| `Site internet` | 99,2 % | Lien officiel |

### Effectif

| Colonne | Remplissage |
|---|---|
| `Étudiants inscrits (2024)` | 44,5 % (100 % des universités) |

---

## 4. ⚠️ Jointures : ce fichier ne joint pas Parcoursup directement

| Cible | Recouvrement |
|---|---|
| Tous les UAI du fichier des admissions | 168 / 245 |
| InserSup | **190 / 245** |
| UAI **universitaires** de Parcoursup | **71 / 460 (15,4 %)** |

Le dernier chiffre est le point important. Parcoursup référence des **IUT, composantes et
sites de formation**, chacun avec son propre UAI, alors que ce fichier référence les
**établissements mères**. Les deux ne se recouvrent qu'à la marge.

**Conséquence pratique** : ce fichier ne sert pas à enrichir ligne à ligne les tableaux de formations. Il sert à :

- **peupler la table `etablissements_sup`** (identité, académie, typologie, effectif)
- **faire le pont avec InserSup** (190 UAI communs), qui n'a pas de géographie fine
- **alimenter les fiches `/s/` des universités** — 65 fiches, un périmètre maîtrisable

La géographie des formations (pages `/v/` et `/d/`) continue de venir de la **cartographie
Parcoursup**, qui porte la commune de chaque formation, y compris pour les antennes.

---

## 5. Usage suggéré

**Fiches université `/s/`** — c'est son terrain principal. Les 65 universités ont toutes
leur académie, leur typologie et leur effectif : de quoi construire une fiche complète (nom, ville, statut, nombre d'étudiants, classement dans l'académie) sans dépendre d'aucune
autre source.

**Bloc de maillage « Les autres universités de l'académie de {X} »** — 2 universités par académie en médiane, donc un bloc court, dont le contenu varie d'une fiche à l'autre.

**Adresse postale des marqueurs Leaflet** — les colonnes `Adresse` / `Code postal` /
`Localité` (98–100 %) permettent des infobulles aussi riches que celles des lycées.

**À ne pas utiliser pour** : lister les formations d'une ville ou d'un département (c'est le rôle de la cartographie Parcoursup), ni pour rattacher une antenne à son département.
