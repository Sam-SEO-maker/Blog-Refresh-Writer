# Note explicative — Diplômes préparés (santé et IEP)

---

Ce fichier donne les **effectifs par filière de formation** pour deux périmètres précis :
les **études de santé** (médecine, pharmacie, odontologie, PASS/L.AS) et le **2e cycle des
IEP**. Ce sont les deux angles que les autres fichiers du corpus ne couvrent pas.

**Source** : data.enseignementsup-recherche.gouv.fr — jeu
`fr-esr-principaux-diplomes-et-formations-prepares-etablissements-publics`, millésime
**2024-25**, filtré sur ces deux périmètres.

> ⚠️ **Fichier volontairement restreint.** Le jeu source contient 30 007 lignes couvrant
> toutes les disciplines, mais seulement **103 UAI** — trop partiel pour servir de source
> d'offre de formation générale, et faisant doublon avec MonMaster sur les masters (101 UAI
> contre 110, sans les données d'admission). Il a donc été filtré à ses deux apports
> propres : **13,9 Mo → 1,8 Mo**.

---

## 1. Format et volumétrie

| | |
|---|---|
| Séparateur | `;` (point-virgule) |
| Encodage | UTF-8 **avec BOM** |
| Colonnes | 22 (filtrées depuis 75) |
| Lignes | 6 150 |
| Année universitaire | **2024-25** |

**Une ligne = un établissement × un diplôme × un niveau.**

### La colonne `perimetre` — à utiliser en premier

Ajoutée au filtrage pour rendre le découpage lisible dans le fichier :

| `perimetre` | Lignes | UAI | Étudiants | Contenu |
|---|---|---|---|---|
| `SANTE` | 4 959 | 46 | 218 241 | Médecine, pharmacie, odontologie |
| `PASS_LAS` | 1 142 | 64 | 57 150 | PASS, PluriPASS, Licence accès santé |
| `IEP` | 49 | 10 | 18 271 | 2e cycle des IEP |

⚠️ **Ne pas additionner `SANTE` et `PASS_LAS`** sans y penser : les PASS relevaient en
partie de la discipline « Pluridisciplinaire santé » avant filtrage. Ils sont désormais
rangés sous `PASS_LAS`, ce qui est plus juste, mais fait que `SANTE` seul ne représente pas
« tous les étudiants en santé ».

---

## 2. Les 22 colonnes

### Établissement (7)

| Colonne | Usage |
|---|---|
| `etablissement_id_uai` | **Clé de jointure** — UAI |
| `etablissement_actuel_lib` | **Nom à afficher** (tient compte des fusions d'universités) |
| `etablissement_lib` | Nom historique |
| `etablissement_type` | Université, école, grand établissement |
| `etablissement_compos_lib` | Composante, quand renseignée (38 % des lignes source) |
| `implantation_commune` / `implantation_departement` / `implantation_academie` | Géographie du **lieu de formation** |

⚠️ `etablissement_commune` était **vide à 100 %** dans le jeu source : elle a été retirée.
La géographie utilisable est celle de l'**implantation**.

### Formation (8)

`cursus_lmd_lib` (1er/2e/3e cycle) · `diplome_lib` · `libelle_intitule_1` · `niveau_lib` ·
`degetu_lib` · `gd_disciscipline_lib` · `discipline_lib` · `sect_disciplinaire_lib`

### Effectifs (3)

`effectif` · `femmes` · `hommes`

---

## 3. Périmètre SANTÉ — ce qu'il contient vraiment

**Le fichier classe par *discipline*, pas par diplôme d'exercice.** Il n'existe aucun
libellé « DE docteur en médecine » ou « DE sage-femme » — chercher ces intitulés renvoie
zéro ligne.

| `discipline_lib` | Lignes | UAI | Étudiants |
|---|---|---|---|
| Médecine | 4 396 | 44 | 175 180 |
| Pharmacie | 367 | 27 | 32 654 |
| Odontologie | 178 | 23 | 10 196 |
| Pluridisciplinaire santé | 18 | — | 211 |

⚠️ **La maïeutique (sage-femme) n'est pas isolable.** Elle n'apparaît ni comme discipline,
ni comme secteur disciplinaire — elle est vraisemblablement fondue dans « Autres formations
de santé » du jeu source, qui n'a pas été retenu car il mélange des formations paramédicales
hétérogènes. **Ne pas annoncer la maïeutique comme une filière disponible.**

### PASS et L.AS

| `diplome_lib` | Lignes | UAI | Étudiants |
|---|---|---|---|
| Licence accès santé (L.AS) | 1 087 | 64 | 27 497 |
| PASS et PluriPASS | 42 | 32 | 25 439 |
| Licence sciences pour la santé (majeure santé) | 13 | 6 | 4 214 |

Top établissements PASS + L.AS : Université Paris Cité 3 836 · Université de Lille 3 353 ·
Aix-Marseille Université 2 750 · Claude Bernard Lyon 1 2 677 · Bourgogne Europe 2 565.

---

## 4. ⚠️ Ce que ce fichier NE dit PAS — le goulot d'étranglement de la santé

**Le passage PASS/L.AS → 2e année (MMOP) n'existe nulle part en open data.** Ni les
capacités d'accueil, ni les taux de réussite, par université.

Raison structurelle vérifiée sur Legifrance ([arrêté du 4 novembre 2019](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000039309386/),
art. 7-I) : **ce sont les universités qui fixent elles-mêmes leurs capacités d'accueil**,
il n'existe donc aucun texte national contenant les chiffres par établissement. Chaque fac
publie son propre PDF, non structuré.

Recherche exhaustive : **0 occurrence** de « numerus » ou « apertus » dans les 214 datasets
MESR, et 0 résultat sur data.gouv.fr (73 702 jeux).

⚠️ **Piège à ne surtout pas utiliser comme substitut** : le jeu SISE permet de filtrer
`degetu=2` (BAC+2), ce qui ressemble à « 2e année de médecine ». C'est faux — sur 20 363
étudiants en BAC+2 médecine, 12 635 sont en « autres formations de santé » et 6 799 en
paramédical. Ce proxy produirait des chiffres inventés sur une page d'orientation.

**Recommandation** : traiter ce manque comme un **angle éditorial** (« pourquoi personne ne
peut vous dire combien de places il y a dans votre fac ») plutôt que comme un trou à
combler. C'est précisément le chiffre que cherchent lycéens et parents, et il n'est pas
récupérable à l'échelle.

> À vérifier avant toute publication : le numerus apertus aurait été supprimé en juin 2025.
> Information issue de sources de presse, **non confirmée en source primaire**.

---

## 5. Périmètre IEP — un complément, pas une source d'admission

49 lignes, 10 UAI, **exclusivement du 2e cycle** (aucun 1er cycle dans ce fichier).

| Établissement | Effectif 2e cycle |
|---|---|
| Sciences Po (Paris) | 6 791 |
| Sciences Po Bordeaux | 2 252 |
| Université de Lille | 1 689 |
| Sciences Po Lyon | 1 567 |
| Université Grenoble Alpes | 1 486 |
| Université Toulouse Capitole | 1 107 |
| Université de Rennes | 1 000 |
| Université de Strasbourg | 859 |
| CY Cergy Paris Université | 760 |
| Sciences Po Aix | 760 |

**C'est le seul chiffre master disponible pour les IEP** — ils sont totalement absents de
MonMaster et de tout l'écosystème Trouver Mon Master (vérifié sur 3 jeux distincts).

⚠️ **C'est un volume d'étudiants, pas une offre de formation ni des admissions.** Il n'y a
ni mention de master, ni candidats, ni places. Un tableau « les masters de {IEP} » n'est
pas constructible ; seul un chiffre global l'est.

⚠️ **Double comptage tutelle / composante** : certains IEP apparaissent sous leur propre
UAI, d'autres sous celui de leur université de tutelle (Lille, Grenoble, Toulouse, Rennes,
Strasbourg, Cergy dans le tableau ci-dessus sont des lignes d'université). **Ne pas
additionner** ces effectifs avec ceux de l'université correspondante — ce seraient les mêmes
étudiants comptés deux fois. Choisir : la composante pour une fiche IEP, la tutelle pour une
fiche université.

---

## 6. Ce que ce fichier permet

- **Fiches université avec santé** : afficher les effectifs de médecine / pharmacie /
  odontologie et le volume PASS/L.AS, par établissement (46 et 64 UAI).
- **Fiches IEP** : un effectif de 2e cycle, à défaut d'admissions.

### Ce qu'il ne permet pas

Pas de taux de réussite, pas de capacités d'accueil, pas d'admissions. Pour l'entrée en
PASS/L.AS, la source reste `fr_esr_admissions_parcoursup.csv` (287 formations PASS,
513 L.AS, taux d'accès renseigné à 100 %).
