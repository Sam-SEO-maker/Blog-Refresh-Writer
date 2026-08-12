# 5. Limites, structure de tables et arbitrages

> 📄 **Dossier « Enseignement supérieur »** — [Index](00-index.md) · [1. Principes](01-principes-et-perimetres.md) · [2. Fiches lycée](02-fiche-lycee.md) · [3. Pages ville et département](03-ville-et-departement.md) · [4. Fiches université](04-fiche-universite.md) · [5. Limites et tables](05-limites-et-tables.md)

---

## 5. Cinq limites à connaître avant de dimensionner les tables

### a. Aucun taux de réussite n'existe en open data

**Ni pour les BTS, ni pour les licences, par établissement.** Les deux portails
ministériels ont été explorés sous de nombreux angles. Le seul jeu « réussite en licence »
disponible date de 2017 (cohorte 2012) et **n'a pas de code UAI** : données nationales par
discipline, inexploitables pour classer des établissements.

**Conséquence** : le bloc « Supérieur » ne pourra pas être un classement par taux de
réussite, contrairement aux blocs Lycées / Collèges / Écoles existants.

Les critères disponibles ne le remplacent pas : le **taux d'accès** mesure la sélectivité à
l'entrée, l'**insertion** l'emploi en sortie. Aucun des deux ne dit ce que vaut la
formation. Voir le point b ci-dessous pour les réserves sur l'insertion.

Le **taux de poursuite d'études** est dans le même cas : il n'existe pas par établissement,
seulement au niveau national (63 % des diplômés 2024 de licence générale s'inscrivent en
master l'année suivante — SIES). Utilisable en contenu rédactionnel, pas en colonne.

### b. L'insertion est très inégalement couverte

| Public | Source | Couverture |
|---|---|---|
| BTS voie scolaire | F4 | **59,2 %** |
| BTS apprentissage | F5 | 32,7 % |
| Licence / Master | F6 | 15,7 % |
| **BUT** | — | **0 %** |

Le cas du BUT mérite explication : InserSup le couvre (702 lignes) mais rattache les BUT à
l'**université mère**, alors que Parcoursup les rattache à l'**IUT**, qui a son propre UAI.
**Recouvrement nul.** Les BUT resteront donc sans indicateur d'insertion, sauf à construire
une table de correspondance IUT → université mère (chantier à part, gain discutable
puisque le taux serait moyenné sur toute l'université).

⚠️ **Au-delà de la couverture, une réserve de fond sur l'insertion au niveau licence.**
L'indicateur ne compte pas les poursuites d'études : un diplômé qui entre en master n'est
pas une sortie vers l'emploi. Comme **63 % des diplômés de licence générale poursuivent**,
le taux ne porte que sur une minorité non représentative. Il mesure par ailleurs un statut
à une date, sans qualification — un diplômé employé en dessous de son niveau compte comme
inséré. **Recommandation** : le réserver aux diplômes professionnalisants terminaux (BTS,
apprentissage), et ne pas en faire un critère de classement d'université.

### c. Décalage de session : inventaire 2026, chiffres 2025

F1 décrit l'offre **2026** (formations ouvertes aux candidatures), F2 et F3 donnent les
résultats **2025** — les chiffres 2026 n'existeront qu'après la procédure en cours.

**La jointure est donc partiellement incomplète par construction** : les formations
ouvertes pour la première fois en 2026 n'ont pas de chiffres.

Un affichage qui tolère l'absence de chiffres (l'inventaire restant affichable seul)
semble préférable à une jointure stricte, qui masquerait précisément les formations neuves.

Couverture mesurée : **89,3 %** des formations de la cartographie ont des chiffres via les
fichiers admissions et apprentissage.

### d. En master, le taux d'accès ne se calcule pas comme en post-bac

⚠️ **Reproduire le calcul Parcoursup sur `fr-esr-mon_master.csv` donne un résultat faux.**

| Calcul | Médiane observée |
|---|---|
| `admis / candidats` | **6,5 %** ❌ |
| `propositions / candidats` | **21,2 %** ✅ |

En master, un candidat postule à des dizaines de mentions et n'en accepte qu'une : le
premier rapport mesure surtout le choix des candidats admis ailleurs, pas la sélectivité de
l'établissement. Exemple réel, master Bio-informatique à Paris Cité — 406 candidats,
58 propositions, 19 acceptations : 4,7 % par les acceptations, **14,3 %** par les
propositions.

La colonne `part_propositions` est **déjà calculée** dans le fichier, sur le bon ratio.

⚠️ **Ne pas non plus reconstituer un taux de poursuite licence → master.** Ni MonMaster ni
l'Atlas ne le permettent : MonMaster est vu depuis le master d'arrivée et ne porte **aucun
UAI d'origine** des candidats, l'Atlas compte des inscrits et non des diplômés. Le ratio
BAC+4 / BAC+3 d'une université produirait des chiffres plausibles (88 % à Aix-Marseille,
47 % à La Rochelle) qui **ne sont pas un taux de poursuite** : le numérateur inclut les
redoublants et les entrants venus d'ailleurs, et les deux niveaux sont deux cohortes
différentes observées la même année.

### e. Les effectifs du supérieur ont un an de retard supplémentaire

F11 (Atlas) est en **rentrée 2024**, F12 (santé/IEP) en **2024-25** : il n'existe pas de
millésime 2025 pour ces deux fichiers, publiés avec un an de décalage. Les CPGE (F9) sont
en revanche bien en **2025-2026**.

Une table d'effectifs gagnerait donc à porter son millésime en clé plutôt qu'à le supposer
aligné sur celui des admissions.

⚠️ **Deux mesures d'effectif coexistent et ne coïncident pas** : `Étudiants inscrits (2024)`
du référentiel (F7, renseigné à 44 % seulement) et `effectifhdccpge` de l'Atlas (F11, « hors
doubles comptes CPGE »). Les deux sont justes mais ne comptent pas la même chose. Le plus
simple serait de retenir le référentiel en priorité et l'Atlas en repli, en conservant la
source retenue dans une colonne.

---

---

## 6. Structure de tables — piste de départ

1. **`etablissements_sup`** — UAI, nom, type, académie, statut. **Sans commune ni
   département** : une université est multi-sites, sa géographie vit dans `implantations`.
   Les lycées à BTS/CPGE restent dans la table établissements actuelle, avec un flag
   `has_postbac`.

2. **`implantations`** — id, UAI de l'établissement mère, nom du site, UAI propre s'il
   existe (cas des IUT), commune, département. **C'est cette table que requêtent les pages
   ville et département**, jamais `etablissements_sup`. Alimentée par F1 : communes
   distinctes d'un même UAI.

3. **`formations_parcoursup`** — **une ligne par formation × session** : UAI, code interne
   Parcoursup, libellé, type principal, voie (scolaire/apprentissage), commune, places,
   candidats, admis, taux d'accès, % TB, % boursiers, % filles, % bac général/techno/pro,
   % même académie. Garder l'année en clé → historiques gratuits plus tard.
   ⚠️ Une colonne `voie` serait utile : c'est elle qui détermine si un taux d'accès existe.

4. **`insertion_etablissement`** — UAI, année, type de public (BTS scolaire / apprentissage
   / supérieur), taux d'emploi 6 mois, 12 mois, poursuite d'études, nombre de formations
   agrégées. Alimentée par F4, F5, F6.

5. **`formations_master`** — **une ligne par mention × établissement × modalité** : UAI,
   mention, discipline, alternance (0/1), candidats, classés, propositions, part de
   propositions, origine dominante et sa part, nombre de parcours agrégés, lieux.
   Alimentée par F10.
   ⚠️ **Table distincte de `formations_parcoursup`**, volontairement : le master ne passe
   pas par Parcoursup, n'a **pas de code interne Parcoursup**, et sa maille est la
   *mention*, pas la formation. Vouloir les fusionner obligerait à inventer une clé et à
   mélanger deux définitions de « taux d'accès » qui ne se calculent pas pareil (voir la
   note du fichier).

6. **`effectifs_etablissement`** — UAI (établissement **ou** composante), année, niveau
   (BAC+1 → BAC+6), effectif, dont femmes / hommes, source retenue. Alimentée par F11, en
   repli sur F7. Une table séparée plutôt qu'une colonne d'`etablissements_sup` : un
   établissement a **plusieurs lignes**, une par niveau.
   ⚠️ F11 porte **deux colonnes d'UAI** (`id_etablissement` et `id_composante`) : les IEP,
   IUT et UFR n'apparaissent que sous la seconde. Une jointure sur la seule première les
   perdrait tous.

7. **`effectifs_filiere_sante`** (optionnelle) — UAI, année, périmètre (SANTE / PASS_LAS /
   IEP), discipline, diplôme, effectif. Alimentée par F12. À ne créer que si les fiches
   affichent la ventilation santé ; sinon F12 se consulte à la demande.

Toutes les jointures se font sur **UAI + année** — y compris `formations_master`, qui n'a
pas d'autre clé exploitable.

---

---

## 7. Arbitrages déjà tranchés côté données

Ces points sont tranchés, notés ici pour mémoire :

- **Indicateur d'insertion affiché** : emploi à **6 mois** (le plus rempli) en principal,
  poursuite d'études en complément pour les BTS. La valeur ajoutée du fichier CFA (−12 à +12) est
  plus juste mais moins lisible : à garder pour une V2.
- **Jointure du fichier BTS/insertion** : sur l'UAI seul, données déjà agrégées par établissement.
- **Rang du dernier appelé** et **sélectivité administrative** : écartés, non affichés.
- **BUT sans insertion** : accepté en l'état.
