# Note explicative — InserJeunes CFA (insertion après apprentissage)

---

Ce fichier donne le **devenir des apprentis après leur formation** : taux d'emploi,
poursuite d'études, et une **valeur ajoutée** comparable à celle des lycées déjà affichée
sur le site.

C'est le seul indicateur de qualité disponible pour les formations en apprentissage, qui
n'ont ni taux d'accès ni taux de réussite publiés (voir
`note_fr-esr-parcoursup-apprentissage.md`).

**Source** : data.education.gouv.fr — jeu `fr-en-inserjeunes-cfa`
(⚠️ portail de l'Éducation nationale, pas celui de l'Enseignement supérieur).

---

## 1. Format et volumétrie

| | |
|---|---|
| Séparateur | `;` (point-virgule) |
| Encodage | UTF-8 avec BOM |
| Colonnes | 9 (filtrées depuis 15) |
| Lignes | 2 758 |
| Millésime | **`cumul 2023-2024`** (le plus récent ; 5 antérieurs retirés) |
| CFA distincts | 2 758 |

**Une ligne = un CFA.** Un seul millésime étant conservé, il n'y a plus de doublon par établissement.

---

## 2. Les colonnes utiles

| Colonne | Remplissage | Usage |
|---|---|---|
| `UAI` | 100 % | **Clé de jointure** avec `fr-esr-parcoursup-apprentissage.csv` |
| `Libellé` | 100 % | Nom du CFA |
| `Année` | 100 % | Constant à `cumul 2023-2024` — trace du millésime conservé |
| `Région` | 100 % | Seule géographie du fichier |
| `Taux emploi 6 mois` | 71,5 % | Indicateur principal |
| `Taux emploi 12 mois` | 71,5 % | Indicateur principal |
| `VA emploi 6 mois` | 71,5 % | **Valeur ajoutée** — voir §3 |
| `Taux poursuite études` | 80,1 % | Complément utile |
| `Taux emploi 6 mois attendu` | 71,5 % | Sert à interpréter la VA |

---

## 2. La valeur ajoutée : l'indicateur le plus intéressant

`VA emploi 6 mois` = écart entre le taux d'emploi **réel** et le taux **attendu** compte
tenu du profil des apprentis et du contexte local. Elle s'étale de **−12 à +12** points.

C'est exactement la logique de la valeur ajoutée des lycées déjà utilisée sur le site :
elle distingue un CFA qui fait mieux que ce que son public laissait prévoir d'un CFA qui
affiche un bon taux brut simplement parce qu'il recrute dans un bassin d'emploi favorable.
1 973 CFA la portent sur le dernier millésime.

---

## 3. ⚠️ Couverture : environ un tiers des formations

Mesuré contre `fr-esr-parcoursup-apprentissage.csv` :

| | |
|---|---|
| UAI joignables (tous millésimes) | 1 185 / 3 896 (**30,4 %**) |
| Lignes de formation avec un taux d'emploi (dernier millésime) | **3 769 / 11 536 (32,7 %)** |

L'écart s'explique par la nature du fichier : InserJeunes couvre les **CFA**, alors que
beaucoup d'UAI de l'apprentissage Parcoursup sont des lycées portant un BTS en
apprentissage, ou de petits organismes privés hors contrat — souvent absents du dispositif
ou masqués sous le seuil statistique.

Un affichage conditionnel serait donc nécessaire : deux tiers des formations en apprentissage
n'auront pas d'indicateur d'insertion.

---

## 4. ⚠️ La donnée est par établissement, pas par formation

Le taux est calculé **au niveau du CFA**, tous diplômes confondus. Le même chiffre s'appliquera donc à tous les BTS d'un même centre.

Côté rédaction, la formulation « insertion des apprentis de cet établissement » serait plus
honnête que « insertion des diplômés de ce BTS ». Pour une insertion par formation en voie
scolaire, voir `note_fr-en-inserjeunes-lycee_pro-bts.md`.

---

## 5. Reste à faire

Reste à choisir l'indicateur affiché : taux brut à 6 mois, à 12 mois, ou valeur ajoutée.
La VA est plus juste, le taux brut plus immédiatement lisible.
