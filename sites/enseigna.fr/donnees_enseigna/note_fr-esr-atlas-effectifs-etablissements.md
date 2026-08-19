# Note explicative — Atlas des effectifs par établissement

---

Ce fichier donne **combien d'étudiants sont inscrits**, par établissement et par **niveau
post-bac** (BAC+1 à BAC+6 et plus). Il répond à une question qu'aucun autre fichier du
corpus ne couvre : le **volume et le profil** d'un établissement du supérieur.

Il ne dit rien des admissions — ni places, ni candidats, ni taux d'accès. Pour ça, voir
`note_fr_esr_admissions_parcoursup.md` (post-bac) et `note_fr-esr-mon_master.md` (master).

**Source** : data.enseignementsup-recherche.gouv.fr — jeu
`fr-esr-atlas_regional-effectifs-d-etudiants-inscrits-detail_etablissements`, filtré sur la
**rentrée 2024**.

---

## 1. Format et volumétrie

| | |
|---|---|
| Séparateur | `;` (point-virgule) |
| Encodage | UTF-8 **avec BOM** |
| Colonnes | 19 (filtrées depuis 27) |
| Lignes | 22 068 |
| Rentrée | **2024** — la plus récente publiée |
| Établissements distincts | 6 294 |
| Composantes distinctes | 7 941 |

**Une ligne = un établissement (ou une composante) × un niveau d'études.**

⚠️ **Il n'existe pas de millésime 2025.** L'Atlas s'arrête à la rentrée 2024, publiée avec
un an de décalage. À ne pas confondre avec les fichiers Parcoursup (session 2025) ni avec
`fr-esr-effectifs-cpge.csv` (année scolaire 2025-2026).

---

## 2. Les 19 colonnes

### Établissement et composante (6)

| Colonne | Usage |
|---|---|
| `id_etablissement` | **UAI de l'établissement** — clé de jointure principale |
| `libelle_etablissement_1` | Nom de l'établissement |
| `sigle_etablissement` | Sigle |
| `id_composante` | **UAI de la composante** quand elle en a un (IEP, UFR, IUT) |
| `libelle_composante_1` | Nom de la composante |
| `sigle_composante` | Sigle de la composante |

⚠️ **C'est le point le plus important de ce fichier — voir §3.**

### Catégorie et géographie (7)

`categorie_etablissement` (Lycées 5 854, Universités 5 591, Écoles d'ingénieurs 1 045…) ·
`secteur_etablissement` · `reg_nom` · `aca_nom` · `dep_num_nom` · `com_nom` · `geo`

Les identifiants techniques correspondants (`reg_id`, `aca_id`, `dep_id`, `uucr_id`,
`com_code`) ont été **retirés au filtrage** : les libellés suffisent à l'affichage.

### Niveau et effectifs (6)

| Colonne | Usage |
|---|---|
| `degetu` | Code du niveau (0 à 6) |
| `degre_etudes` | **Libellé du niveau** — c'est celui qu'on affiche |
| `effectifhdccpge` | **L'effectif** — attention au nom, voir §4 |
| `dont_femmes` / `dont_hommes` | Ventilation par sexe |

Répartition nationale par niveau (rentrée 2024) :

| Niveau | Lignes | Étudiants |
|---|---|---|
| Inférieur ou égal au bac | 409 | 20 060 |
| BAC + 1 | 7 199 | 934 346 |
| BAC + 2 | 6 853 | 663 774 |
| BAC + 3 | 2 883 | 470 885 |
| BAC + 4 | 2 084 | 371 585 |
| BAC + 5 | 1 972 | 388 044 |
| BAC + 6 et plus | 668 | 178 768 |

---

## 3. ⚠️ Établissement ou composante — le piège des IEP

**Les IEP, IUT et UFR sont des *composantes*, pas des établissements.** Ils apparaissent
sous `id_composante`, pas sous `id_etablissement`. Une jointure qui ne regarde que
`id_etablissement` les perd tous.

**Ne jamais filtrer sur le libellé.** Chercher « politiques » dans `libelle_composante_1`
ramasse les IEP **et** les UFR de droit et science politique, qui n'ont rien à voir :

| Libellé trouvé | Effectif | Est-ce un IEP ? |
|---|---|---|
| `INST ETUDES POLITIQUES PARIS` | 12 494 | ✅ oui |
| `UFR DROIT SCIENCES POLITIQUES` | 10 329 | ❌ **non** |
| `SCIENCES PO AIX` | 1 707 | ✅ oui |
| `FAC SC HIST ART POLITIQUES` | 2 291 | ❌ **non** |

**La méthode qui marche** : extraire la liste des **UAI d'IEP depuis
`fr_esr_admissions_parcoursup.csv`** (18 UAI), puis matcher dans l'Atlas sur
`id_composante` **ou** `id_etablissement`. Résultat mesuré : **11 IEP retrouvés sur 18**.

| IEP | UAI | Effectif 2024 |
|---|---|---|
| Sciences Po Paris | 0753431X | 12 494 |
| Sciences Po Bordeaux | 0330192E | 2 333 |
| Sciences Po Lyon | 0690173N | 1 995 |
| Sciences Po Grenoble | 0380134P | 1 953 |
| Sciences Po Lille | 0595876S | 1 756 |
| Sciences Po Aix | 0130221V | 1 707 |
| Sciences Po Toulouse | 0310133B | 1 638 |
| Sciences Po Strasbourg | 0670178E | 1 617 |
| Sciences Po Rennes | 0352317D | 1 377 |
| Sciences Po Saint-Germain-en-Laye | 0783640H | 919 |
| IEP de Fontainebleau (UPEC) | 0772910V | 721 |

**Les 7 absents sont des campus délocalisés** de Paris et Lyon (Menton, Dijon, Reims,
Nancy, Le Havre, Poitiers, Saint-Étienne) : leurs étudiants sont comptés dans
l'établissement mère. **Ce n'est pas un trou de couverture** — mais leur fiche `/s/` ne
pourra pas afficher d'effectif propre.

⚠️ Noter que `0772910V` porte le libellé générique `AUTRE COMPOSANTE` : un filtre textuel
l'aurait manqué même en cherchant « IEP » ou « politiques ».

---

## 4. ⚠️ `effectifhdccpge` ne contient PAS les CPGE

Le nom de la colonne se lit **« effectif Hors Doubles Comptes CPGE »**. C'est un décompte
qui **exclut** les élèves de classes préparatoires — ceux-ci sont inscrits à la fois dans
leur lycée et à l'université, et seraient sinon comptés deux fois.

**Vérifié** : zéro ligne CPGE dans ce fichier, ni dans `categorie_etablissement`, ni dans
`degre_etudes`.

**Pour les CPGE, utiliser `fr-esr-effectifs-cpge.csv`**, qui est plus riche sur tous les
plans : année 2025-2026 (plus récente d'un an), 469 lycées, 37 spécialités, 1re et 2e année
séparées, ventilation par sexe. L'Atlas ne le remplace ni ne le complète.

**Conséquence secondaire** : le total Atlas d'un établissement est légèrement inférieur à
son effectif brut, et ne coïncide pas exactement avec `Étudiants inscrits (2024)` du
référentiel `fr-esr-principaux-etablissements`. Les deux sont justes, ils ne comptent pas
la même chose — ne pas chercher à les faire correspondre.

---

## 5. Ce que ce fichier permet

### Bandeau 4.0 des fiches université — l'apport principal

Le référentiel `fr-esr-principaux-etablissements` ne renseigne l'effectif que pour
**109 établissements sur 245 (44 %)**. L'Atlas en récupère **108 des 136 manquants** :
la couverture du bandeau « X étudiants » passe donc de **44 % à 89 %**.

C'est le seul fichier du corpus qui comble ce trou.

### Profil d'un établissement par niveau

La ventilation BAC+1 → BAC+6 se lit comme une pyramide et caractérise un établissement
d'un coup d'œil :

| Niveau | Université de Lille | Université de Bordeaux |
|---|---|---|
| BAC + 1 | 19 681 | 12 273 |
| BAC + 2 | 11 435 | 8 178 |
| BAC + 3 | 11 761 | 7 480 |
| BAC + 4 | 10 452 | 6 371 |
| BAC + 5 | 11 535 | 7 195 |
| BAC + 6 et plus | 6 366 | 6 587 |

La comparaison est parlante : Bordeaux compte proportionnellement **beaucoup plus de
doctorants** (13,7 % de ses effectifs contre 8,9 % à Lille), signe d'une université plus
orientée recherche.

### Ce qu'il ne permet pas

- **Aucune donnée d'admission** : ni places, ni candidats, ni propositions, ni taux d'accès.
- **Le niveau n'est pas le diplôme** : BAC+1 mélange L1, PASS et 1re année d'école ; BAC+5
  mélange M2 et dernière année d'ingénieur.
- **Aucun croisement avec la discipline** : impossible d'obtenir « BAC+3 en droit ». Pour
  une ventilation disciplinaire, voir `note_fr-esr-diplomes-prepares-etablissements.md`
  (mais couverture restreinte).
