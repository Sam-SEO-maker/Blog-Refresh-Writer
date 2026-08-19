# Note explicative — InserJeunes lycée pro (insertion après BTS)

---

Ce fichier donne le **devenir des diplômés de BTS en voie scolaire** : taux d'emploi et
poursuite d'études, par établissement. C'est le pendant de `fr-en-inserjeunes-cfa.csv`
pour la voie scolaire.

**Source** : data.education.gouv.fr — jeu `fr-en-inserjeunes-lycee_pro-formation-fine`
(⚠️ portail de l'Éducation nationale, pas celui de l'Enseignement supérieur).

---

## 1. Format et volumétrie

| | |
|---|---|
| Séparateur | `;` (point-virgule) |
| Encodage | UTF-8 avec BOM |
| Colonnes | 9 (filtrées depuis 17) |
| Lignes | 1 971 (une par établissement) |
| Millésime | **`cumul 2023-2024`** (le plus récent ; 5 antérieurs retirés) |
| Établissements | 1 971 |
| Taille | 226 Ko (24 Mo avant filtrage) |

**Une ligne = un établissement.** Voir §5 : les données ont été agrégées par UAI.

---

## 2. Filtre `Type diplome = BTS` déjà appliqué

La source couvrait 7 types de diplômes, dont la plupart sont **hors périmètre post-bac**.
Seuls les BTS ont été conservés :

| Type diplôme | Lignes | Dans le périmètre ? |
|---|---|---|
| BAC PRO | 58 264 | non |
| **BTS** | **35 679** | **oui** |
| CAP | 33 116 | non |
| MC3 / MC4 / MC5 (mentions complémentaires) | 4 052 | non |
| BP | 1 013 | non |

La source comptait 6 233 lignes BTS sur le dernier millésime, réparties sur **1 971 UAI**
et 175 formations distinctes. Après agrégation par établissement (§5), le fichier livré
contient **1 971 lignes**. La colonne `Type diplome` est conservée (constante à `BTS`)
comme trace du filtre appliqué.

---

## 3. Les colonnes utiles

| Colonne | Remplissage | Usage |
|---|---|---|
| `UAI` | 100 % | **Clé de jointure** avec les admissions Parcoursup — unique par ligne |
| `Libellé` | 100 % | Nom de l'établissement |
| `Type diplome` | 100 % | Constant à `BTS` — trace du filtre, voir §2 |
| `Année` | 100 % | Constant à `cumul 2023-2024` — trace du millésime conservé |
| `Région` | 100 % | Seule géographie du fichier |
| `Nombre de formations BTS` | 100 % | **Ajoutée** — combien de BTS l'établissement porte (voir §5) |
| `Taux emploi 6 mois` | 52,3 % | Indicateur principal |
| `Taux emploi 12 mois` | 52,3 % | Indicateur principal |
| `Taux poursuite études` | 81,7 % | Complément — pertinent pour un BTS |

### Colonnes supprimées (9)

- `Code formation mefstat11` et `Libellé formation` — nomenclature Éducation nationale
  sans correspondance Parcoursup, devenues inutiles après agrégation (§5)
- `Taux emploi 18 mois` et `24 mois` — **0 % sur le millésime conservé**
- `DEVENIR Part poursuite études` / `Part en emploi` / `Part autre situation` — 19,9 %
- `Durée formation`, `Diplôme rénové ou nouveau` — hors usage

⚠️ Ce fichier **n'a pas de colonne de valeur ajoutée**, contrairement à la version CFA.

---

## 4. Couverture : la meilleure des trois sources d'insertion

Mesuré contre les 5 351 BTS en voie scolaire de `fr_esr_admissions_parcoursup.csv` :

| | |
|---|---|
| UAI présents dans InserJeunes | 1 763 / 2 175 (**81,1 %**) |
| UAI avec un taux d'emploi renseigné | 996 / 2 175 (45,8 %) |
| **Lignes BTS couvertes** | **3 168 / 5 351 (59,2 %)** |

Ces taux sont **inchangés après l'agrégation** (§5) : aucune couverture n'a été perdue.

Près de 6 BTS scolaires sur 10 pourraient afficher un taux d'emploi — nettement mieux que
l'apprentissage (32,7 %) ou les universités via InserSup (15,7 %).

---

## 5. Données agrégées par établissement

La source donnait une ligne **par formation** (6 233 lignes BTS), identifiée par un
`Code formation mefstat11` et des libellés du type « europlastics et composites, option
co ». Cette nomenclature Éducation nationale **n'a aucune correspondance avec les codes
Parcoursup** : exploiter la granularité fine aurait supposé un rapprochement de libellés
manuel, pour un gain nul tant que les tableaux n'affichent pas l'insertion formation par
formation.

Les données ont donc été **agrégées par UAI** : une ligne par établissement, les taux
étant la **moyenne** de ses BTS. Les deux colonnes de formation ont été supprimées, et une
colonne `Nombre de formations BTS` ajoutée pour savoir sur combien de BTS la moyenne porte.

**Répartition** : 575 établissements ne portent qu'un seul BTS (le taux est alors exact),
1 396 en portent plusieurs (médiane 2, maximum 18).

### ⚠️ Ce que la moyenne masque

Au sein d'un même établissement, l'écart entre le BTS le mieux inséré et le moins bien
inséré atteint **15 points en médiane**, et jusqu'à **55 points**. 160 établissements
dépassent 20 points d'écart.

Côté rédaction, mieux vaudrait écrire « insertion des diplômés de BTS de cet
établissement », jamais « insertion de ce BTS ». Pour un établissement portant plusieurs
BTS, le chiffre est une moyenne d'ensemble, pas la performance d'une formation donnée.

Si l'insertion par formation devient un besoin, il faudra retélécharger la source : les
lignes fines ont été agrégées, pas conservées.

---

## 6. Reste à faire

Reste à choisir l'indicateur affiché : emploi à 6 mois, à 12 mois, ou taux de poursuite
d'études — ce dernier étant particulièrement parlant pour un BTS, beaucoup de diplômés
poursuivant en licence pro.
