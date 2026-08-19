# Note explicative — InserSup (insertion des diplômés du supérieur)

---

Ce fichier donne le **devenir des diplômés de l'enseignement supérieur** : taux d'emploi
stable à 6 et 12 mois, par établissement et par discipline. C'est le pendant
« universités » des deux fichiers InserJeunes (CFA et lycée pro).

**Source** : data.enseignementsup-recherche.gouv.fr — jeu `fr-esr-insersup`
(⚠️ portail de l'Enseignement supérieur, pas celui de l'Éducation nationale).
URL : https://data.enseignementsup-recherche.gouv.fr/explore/dataset/fr-esr-insersup/

---

## 1. Format et volumétrie

| | |
|---|---|
| Séparateur | `;` (point-virgule) |
| Encodage | UTF-8 avec BOM |
| Colonnes | 14 (filtrées depuis 101) |
| Lignes | **10 399** (filtrées depuis 1 036 781) |
| Millésime de publication | `2026_S1` |
| Promotion | 2024 (la plus récente) |
| Établissements distincts | 414 |

---

## 2. Le filtre déjà appliqué au téléchargement

Le jeu source compte **1 036 781 lignes**. Deux filtres l'ont ramené à 10 399 :

**a. `promo = 2024`** — la promotion la plus récente. Le jeu couvre 2019→2024.

**b. Le niveau agrégé** — les colonnes `genre`, `nationalite`, `obtention_diplome` et
`regime_inscription` de la source, toutes filtrées sur `ensemble` puis supprimées. Le fichier ventile en effet chaque résultat par
ces quatre axes : sans ce filtre, la même formation apparaît sur une vingtaine de lignes
(homme/femme, apprentissage/formation initiale…). Ces ventilations sont réutilisables si
un besoin éditorial précis apparaît, mais elles n'ont aucun intérêt pour un classement.


### Identité et jointure

| Colonne | Remplissage | Usage |
|---|---|---|
| `Code UAI de l'établissement` | 100 % | **Clé de jointure** — mais 1 559 lignes valent `all` |
| `Établissement` | 100 % | Nom lisible de l'établissement |
| `Code de l'académie` / `Académie` | 100 % | **Le périmètre de classement des universités** |
| `Région` | 100 % | Géographie |
| `Promotion` | 100 % | Constant à `2024` — trace du millésime conservé |

### Discipline (le « par matière »)

| Colonne | Granularité |
|---|---|
| `Domaine disciplinaire` | **5 domaines** — Sciences-technologies-santé (3 238), Droit-économie-gestion (2 179), Sciences humaines et sociales (1 470), Lettres-langues-arts (982), Tous domaines (2 530) |
| `Discipline` | Niveau intermédiaire |
| `Secteur disciplinaire` | Niveau fin |

### Diplôme

`Type de diplôme` — Master LMD (3 645), Licence générale (1 750), Licence professionnelle
(1 415), Diplôme d'ingénieurs (1 383), BUT (702), diplômes visés grade master (610) et
grade licence (515), Master MEEF (197).

### Les indicateurs

| Colonne | Remplissage | Usage |
|---|---|---|
| `Taux d'emploi stable à 12 mois` | 71,5 % | **Indicateur principal** (7 433 lignes) |
| `Taux d'emploi stable à 6 mois` | 71,4 % | Idem à 6 mois |
| `Effectif de sortants à 12 mois` | 99,9 % | Sert à juger la fiabilité du taux |
| `Libellé du diplôme` | 100 % | Intitulé exact du diplôme |

Les variantes « emploi salarié en France » et « emploi non salarié » de la source ont été
écartées : l'emploi **stable** est l'indicateur le plus lisible, et les trois se recoupent
largement.

---

## 3. ⚠️ Trois limites à connaître avant de bâtir dessus

### a. Le salaire est totalement absent

`salaire_q1_*`, `salaire_q2_*` (médiane) et `salaire_q3_*` valent **`nd` sur 100 % des
lignes**. Données non dévoilées. Vérifié aussi sur le jeu complet non filtré : aucune ligne renseignée.

C'était l'argument le plus fort de cette source — il tombe. Aucun classement par salaire
n'est possible.

### b. 1 559 lignes sont des agrégats nationaux

`Code UAI de l'établissement = 'all'` sur 1 559 lignes (15 %) : ce sont des moyennes France entière, pas
des établissements : elles n'ont pas leur place dans un tableau par établissement, mais
sont utiles comme
point de comparaison (« X % contre Y % en moyenne nationale »), sur le modèle des
comparaisons lycée/France déjà présentes sur le site.

Restent **8 840 lignes portant un vrai UAI**.

### c. La jointure avec Parcoursup est faible : 15,7 %

Seuls **72 UAI sur 460** établissements universitaires côté admissions Parcoursup se
retrouvent ici.

L'explication est structurelle : InserSup suit les **diplômés** (surtout master et licence
pro), tandis que Parcoursup référence l'**entrée en L1**. Ce sont deux populations
différentes, et le fichier inclut beaucoup d'écoles privées absentes de Parcoursup.

---

## 4. Ce que ce fichier permet — et ne permet pas

**Permet** : un classement des établissements du supérieur par taux d'emploi stable,
ventilé par domaine disciplinaire et par académie. Avec une comparaison à la moyenne
nationale grâce aux lignes `all`.

**Ne permet pas** :
- de classer par salaire (voir la limite a. ci-dessus)
- d'alimenter largement les pages ville : la jointure à 15,7 % laisserait la plupart des formations sans donnée
- de renseigner la qualité d'une **L1**, ce que cherche un lycéen. L'indicateur porte sur des diplômés de master : « l'université X place bien ses diplômés de master » n'est pas la même promesse que « la L1 de droit à X est de qualité »

**Usage recommandé** : les **fiches université**, où l'insertion après
master est un indicateur légitime et attendu. Beaucoup moins pertinent sur les pages ville et département.
