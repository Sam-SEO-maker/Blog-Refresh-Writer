# Note explicative — Effectifs en CPGE

---

Ce fichier donne le **nombre d'étudiants en classes préparatoires aux grandes écoles**,
par lycée et par spécialité. C'est le pendant post-bac du « Nb de lycéens » déjà affiché
sur les fiches lycée.

**Source** : data.enseignementsup-recherche.gouv.fr — jeu
`fr-esr-effectifs-d-etudiants-inscrits-en-classes-preparatoires-aux-grandes-ecole`
(⚠️ le nom se termine par `-ecole`, sans « s »).

---

## 1. Format et volumétrie

| | |
|---|---|
| Séparateur | `;` (point-virgule) |
| Encodage | UTF-8 avec BOM |
| Colonnes | 18 (filtrées depuis 23) |
| Lignes | **1 707** |
| Année scolaire | **2025-2026** (la plus récente) |
| Lycées | 469 |
| **Étudiants en CPGE** | **87 258** |
| Taille | 371 Ko |

**Une ligne = un lycée × une spécialité de CPGE** (ex. « Lycée Lalande × MP »).
Voir §3 : les données ont été agrégées.

---

## 2. ⭐ La meilleure couverture de tout le dossier

Mesuré contre les 986 CPGE du fichier des admissions Parcoursup :

| | |
|---|---|
| Lycées à CPGE retrouvés | **411 / 415 (99,0 %)** |
| Formations CPGE couvertes | **979 / 986** |

C'est le taux de recouvrement le plus élevé de toutes les sources examinées — devant
l'insertion des BTS (59,2 %) et très loin devant InserSup (15,7 %).

Autrement dit : **presque toutes les CPGE affichées sur le site pourront porter un
effectif étudiant.**

---

## 3. Agrégation appliquée

La source livrait **4 139 lignes**, ventilées par **sexe** (F/H) et par **année d'études**
(1re/2e) — soit jusqu'à 4 lignes pour une même CPGE.

Les données ont été **pivotées** par lycée × spécialité : les deux ventilations deviennent
des colonnes, au lieu de multiplier les lignes.

| Axe de la source | Devenu |
|---|---|
| `sexe` (F/H) | colonnes `Nombre de filles` / `Nombre de garçons` |
| `degre_d_etudes` (1/2) | colonnes `Étudiants en 1re année` / `2e année` |

**Aucun effectif n'est perdu, et les deux ventilations sont conservées.** Vérifié sur les
1 707 lignes : `filles + garçons = total` et `1re + 2e année = total`. Le total national
reste de **87 258 étudiants** (34 433 filles, 52 825 garçons).

Repères : 41 étudiants par ligne en médiane ; 89 étudiants de CPGE par lycée en médiane
(maximum 1 446).

---

## 4. Les 16 colonnes

### Identité et jointure

| Colonne | Remplissage | Usage |
|---|---|---|
| `Code UAI de l'établissement` | 100 % | **Clé de jointure** avec les admissions Parcoursup et la base lycées |
| `Établissement` | 100 % | Nom du lycée |
| `Secteur` | 100 % | Public / Privé |
| `Année scolaire` | 100 % | Constant à `2025-2026` — trace du millésime conservé |

### Géographie

| Colonne | Remplissage |
|---|---|
| `Commune` / `Code commune` | 100 % |
| `Département` | 100 % |
| `Académie` / `Code de l'académie` | 100 % |
| `Région` | 100 % |
| `Coordonnées GPS` | **100 %** — format `lat, lon`, prêt pour la carte Leaflet |

### Formation

| Colonne | Valeurs |
|---|---|
| `Filière` | **3 valeurs** : scientifique (2 608 lignes source), économique (952), littéraire (579) |
| `Spécialité` | **37 valeurs** : MPSI, PCSI, MP, PC, PSI, BCPST, ECG, LETTRES, TSI, PTSI… |

`Filière` est le bon niveau pour **grouper** sur une page ville ou département ;
`Spécialité` pour le **détail** sur une fiche lycée.

### Effectifs (5 colonnes, toutes à 100 %)

| Colonne | Total national |
|---|---|
| `Étudiants en 1re année` | 43 045 |
| `Étudiants en 2e année` | 44 213 |
| **`Nombre de filles`** | **34 433** |
| **`Nombre de garçons`** | **52 825** |
| `Étudiants (total)` | **87 258** |

En **valeur absolue**, donc additionnables sans erreur pour agréger plusieurs CPGE (par
lycée, par ville ou par filière).

### Colonnes supprimées (9)

`sexe` et `degre_d_etudes` (devenus 4 colonnes, §3) · `mef_stat_11` et `fortrams_7`
(codes techniques Éducation nationale, sans correspondance Parcoursup) ·
`etablissement_id_paysage` (39,2 % de remplissage) · `uucr_id` / `uucr_nom` (unité urbaine,
redondant avec la commune).

---

## 5. Usage recommandé

### Fiche lycée `/s/` — tableau « Les prépas du lycée {X} »

| Spécialité | Nombre de filles | Nombre de garçons | Étudiants | dont 1re année | dont 2e année |
|---|---|---|---|---|---|

Les colonnes filles/garçons reprennent la structure du tableau « Spécialités en Terminale »
déjà en ligne sur les fiches lycée, ce qui donne une continuité de lecture.

**L'écart est très marqué selon la filière**, ce qui rend la colonne informative :

| Lycée | Spécialité | Filles | Garçons |
|---|---|---|---|
| Fermat (Toulouse) | Lettres 1re année | 37 | 9 |
| Fermat (Toulouse) | BCPST | 121 | 71 |
| Fermat (Toulouse) | MP (Maths-Physique) | **9** | **34** |
| Ozenne (Toulouse) | ENS Rennes | 45 | 16 |

Prépas littéraires et biologie très féminines, prépas mathématiques très masculines : une
information réelle sur l'orientation, que le seul effectif total masquerait.

À combiner avec les données d'admission Parcoursup (places, candidats, taux d'accès) sur la
même ligne : la jointure se fait sur l'UAI, et les deux fichiers couvrent quasiment le même
périmètre.

### Page ville `/v/` et département `/d/`

L'effectif enrichit les lignes CPGE du tableau d'inventaire, et permet un bandeau du type
« **X étudiants en CPGE** dans la ville ». Un regroupement sur `Filière` (3 valeurs) serait
plus lisible que sur `Spécialité` (37 valeurs).

Les colonnes filles/garçons étant en valeur absolue, elles s'additionnent sans erreur à
l'échelle d'une ville ou d'un département.

### Ce qu'il ne permet pas

Ce fichier ne contient **aucun indicateur de résultat** : ni taux de réussite aux concours,
ni taux d'intégration aux grandes écoles (données propriétaires, non publiques). Il donne
la **taille** d'une CPGE, pas sa **performance**.

Le seul critère de classement des CPGE reste le **taux d'accès** du fichier des admissions
(renseigné à 100 % sur les 986 CPGE).
