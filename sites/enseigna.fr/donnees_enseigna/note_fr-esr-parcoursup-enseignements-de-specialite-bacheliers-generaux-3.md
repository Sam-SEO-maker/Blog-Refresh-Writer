# Note explicative — Enseignements de spécialité et admissions

> **À garder — mais pour les pages spécialités, pas pour le chantier géographique.**
> Ce fichier ne contient ni UAI, ni établissement, ni géographie : il ne peut alimenter
> aucun tableau des pages `/v/`, `/d/` ou `/s/`. En revanche, il prolonge directement les
> **pages sur les enseignements de spécialité déjà publiées** sur Enseigna, en répondant à
> « où mènent ces spécialités ? ». Voir §4.

---

Ce fichier croise les **enseignements de spécialité du baccalauréat général** avec les
**formations post-bac** dans lesquelles ces bacheliers ont été admis. Il répond à la
question « avec telles spécialités, dans quelles formations entre-t-on ? ».

**Source** : data.enseignementsup-recherche.gouv.fr — jeu
`fr-esr-parcoursup-enseignements-de-specialite-bacheliers-generaux-3`.

---

## 1. Format et volumétrie

| | |
|---|---|
| Séparateur | `;` (point-virgule) |
| Encodage | UTF-8 avec BOM |
| Colonnes | 10 |
| Lignes | 17 211 |
| Année du baccalauréat | 2025 |
| Spécialités distinctes | 75 (des **couples**, ex. « Mathématiques + Physique-Chimie ») |
| Formations distinctes | 315 |

---

## 2. Les 10 colonnes

| Colonne | Contenu |
|---|---|
| `Enseignements de spécialité` | Le doublet de spécialités (75 valeurs) |
| `Regroupement de formations` / `abrégé` | Famille de formations (74 valeurs) |
| `Niveau d'agrégation` | `0`, `1` ou `2` — voir §3 |
| `Formation` | Formation visée (315 valeurs) |
| `Libellé complet` | Intitulé long (388 valeurs) |
| `Nombre de candidats bacheliers ayant confirmé au moins un vœu` | Candidats |
| `Nombre de candidats bacheliers ayant reçu au moins une proposition d'admission` | Propositions |
| `Nombre de candidats bacheliers ayant accepté une proposition d'admission` | Admis |
| `Année du Baccalauréat` | `2025` sur toutes les lignes |

Toutes les colonnes sont remplies à 100 %.

---

## 3. ⚠️ Le fichier mélange trois niveaux d'agrégation

`Niveau d'agrégation` distingue des lignes qui **ne s'additionnent pas** :

| Niveau | Lignes | Signification |
|---|---|---|
| `2` | 11 661 | Le plus fin — spécialité × formation précise |
| `1` | 5 475 | Spécialité × regroupement de formations (`Formation` = « Ensemble regroupement de formations ») |
| `0` | 75 | Total par spécialité (`Formation` = « Ensemble des bacheliers ») |

Sommer sans filtrer sur un seul niveau produirait un **triple comptage** : le niveau `2`
est celui à retenir pour un usage détaillé.

---

## 4. Ce que ce fichier ne permet pas — et ce qu'il permet

**Ne permet pas** — il n'y a **aucun code UAI, aucun nom d'établissement, aucune commune,
aucun département**. Les chiffres sont agrégés au niveau national. Ce fichier ne peut donc
alimenter :

- ni les pages ville `/v/`
- ni les pages département `/d/`
- ni les fiches établissement `/s/`

Il n'a aucun rapport avec un classement d'établissements et **ne se joint à aucun des
autres fichiers** du dossier (pas de clé commune).

**Permet** — d'enrichir les **pages sur les enseignements de spécialité déjà publiées**
sur Enseigna. Ces pages disent ce que l'élève choisit en terminale ; ce fichier dit ce que
ce choix donne ensuite.

### Tableau possible — « Où mènent ces spécialités ? »

Sur une page de doublet de spécialités :

| Formation | Nombre d'admis |
|---|---|

Exemple réel pour **Mathématiques + Physique-Chimie** (niveau d'agrégation 2) :

| Formation | Admis |
|---|---|
| Formation d'ingénieur Bac+5 | 13 604 |
| Licence PASS | 9 233 |
| PCSI | 7 888 |
| MPSI | 7 110 |
| Licence L.AS | 4 183 |
| Licence Mathématiques | 2 407 |

Le fichier couvre **75 doublets de spécialités × 313 formations**.

### Le chemin inverse

La même donnée se lit dans l'autre sens : depuis une formation, quelles spécialités ont
les admis. De quoi ajouter un bloc « Les spécialités des admis en MPSI » sur une future
page CPGE, et créer du **maillage interne** entre les pages spécialités existantes et le
bloc supérieur à venir.

⚠️ Les chiffres sont **nationaux** : « 7 110 admis en MPSI avec Maths + PC » vaut pour la
France entière, jamais pour un lycée donné. Affichés sur une fiche établissement sans
mention explicite, ils seraient lus comme locaux.

---

## 5. Recommandation

**À conserver**, mais sur un usage distinct des autres fichiers du dossier.

| | |
|---|---|
| Chantier géographique (`/v/`, `/d/`, `/s/`) | **N'y contribue pas** — aucune clé de jointure |
| Pages « enseignements de spécialité » déjà publiées | **Source principale** pour un bloc « où mènent ces spécialités ? » |

Aucun filtrage appliqué pour l'instant. Le jour où l'usage serait décidé, il resterait au
minimum à retenir `Niveau d'agrégation = 2` (voir §3), et sans doute à écarter
`Regroupement de formations abrégé` et `Libellé complet`, redondants.
