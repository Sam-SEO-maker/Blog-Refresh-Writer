# Note explicative — Admissions Parcoursup

---

Ce fichier est le **volet chiffré** de Parcoursup : pour chaque formation, combien de
places, combien de candidats, combien d'admis, à quel taux d'accès et avec quel profil.
Il complète `fr-esr-cartographie_formations_parcoursup.csv`, qui donne l'inventaire
(qui propose quoi, et où) mais aucun chiffre.

**Source** : data.enseignementsup-recherche.gouv.fr — jeu `fr-esr-parcoursup`
(« Parcoursup 2025 : vœux de poursuite d'études et réponses des établissements »).

---

## 1. Format et volumétrie

| | |
|---|---|
| Séparateur | `;` (point-virgule) |
| Encodage | UTF-8 **avec BOM** |
| Colonnes | 30 (filtrées depuis 118) |
| Lignes | 14 252 |
| Session | 2025 |
| Établissements distincts | 4 058 |

**Une ligne = une formation dans un établissement**, comme dans la cartographie.
La session 2025 est la **dernière disponible** : les résultats 2026 ne seront publiés
qu'après la fin de la procédure en cours (voir §3).

---

## 2. Les 30 colonnes

### Jointure (2)

| Colonne | Usage |
|---|---|
| `cod_aff_form` | **Clé de jointure** avec la cartographie. Strictement unique (14 252/14 252) |
| `Code UAI de l'établissement` | UAI — pivot MESR, commun avec la base lycées |

### Établissement et géographie (9)

`Établissement` · `Code départemental de l'établissement` · `Département de l'établissement` ·
`Région de l'établissement` · `Académie de l'établissement` · `Commune de l'établissement` ·
`Coordonnées GPS de la formation` · `Statut de l'établissement de la filière de formation` ·
`Session`

Ces colonnes font en partie doublon avec la cartographie, mais elles sont conservées
volontairement : elles rendent le fichier **exploitable seul**, sans jointure préalable.

⚠️ Nuance à connaître : la géographie est ici celle de **l'établissement**, alors que la
cartographie porte celle de **la formation**. Pour un établissement multi-sites (université
avec antennes, IUT), les deux peuvent légitimement différer. Pour les pages `/v/` et `/d/`,
c'est la géographie de la **formation** (cartographie) qui fait foi.

`Académie de l'établissement` est utile au-delà de l'affichage : c'est le périmètre de
classement des universités, absent de la cartographie.

### Formation (4)

| Colonne | Usage |
|---|---|
| `Filière de formation très agrégée` | **11 valeurs** — l'équivalent du `Type principal` calculé sur la cartographie. Sert au regroupement et au contrôle croisé |
| `Filière de formation (libellé)` | Libellé fin, 3 150 valeurs (« BTS - Services - Management Commercial Opérationnel ») |
| `Filière de formation (regroupement)` | Niveau intermédiaire, 53 valeurs (« BTS - Services ») |
| `Filière de formation détaillée bis` | Spécialité seule, 438 valeurs |

⚠️ **Les deux colonnes `Filière de formation` ont été renommées.** Voir §3 — c'est le
piège principal de ce fichier.

Répartition par `Filière de formation très agrégée` : BTS 5 351 · Licence 3 052 ·
Autre formation 1 815 · CPGE 986 · BUT 820 · École d'Ingénieur 585 · Licence_Las 513 ·
IFSI 344 · PASS 287 · École de Commerce 256 · EFTS 243.

### Le cœur des données

| Colonne | Tableau |
|---|---|
| `Capacité de l'établissement par formation` | Places |
| `Effectif total des candidats pour une formation` | Candidats |
| `Effectif total des candidats ayant accepté la proposition de l'établissement (admis)` | Admis |
| `Taux d'accès` | Taux d'accès — **la colonne de classement** |

### Profil des admis (11 colonnes)

`% d'admis néo bacheliers` · `% d'admis néo bacheliers généraux` · `% d'admis néo bacheliers
technologiques` · `% d'admis néo bacheliers professionnels` · `% d'admis néo bacheliers
boursiers` · `% d'admis dont filles` · `% d'admis néo bacheliers issus de la même académie` ·
`% d'admis néo bacheliers avec mention Très Bien au bac` · `Dont % d'admis avec mention (BG)` ·
`(BT)` · `(BP)`

Les pourcentages ont été préférés aux effectifs bruts équivalents : c'est ce que les
tableaux affichent, et ils sont directement comparables entre formations de
tailles différentes.

---

## 3. Ce que ce fichier permet

### Fiches LYCÉE `/s/` — la section « Après le bac »
Tableau « Admissions Parcoursup » et « Profil des admis ».
Le fichier couvre **415 UAI portant une CPGE** et **2 175 UAI portant un BTS**.

### Pages DÉPARTEMENT `/d/` — les classements
« Classement des prépas (CPGE) du département » et tri sur `Taux d'accès` croissant. 986 lignes CPGE disponibles.

### Pages VILLE `/v/` — enrichissement du tableau d'inventaire
Les colonnes Places / Candidats / Taux d'accès viennent compléter le tableau « Formations
Parcoursup à {ville} » alimenté par la cartographie.
