# 3. Pages ville `/v/` et département `/d/`

> 📄 **Dossier « Enseignement supérieur »** — [Index](00-index.md) · [1. Principes](01-principes-et-perimetres.md) · [2. Fiches lycée](02-fiche-lycee.md) · [3. Pages ville et département](03-ville-et-departement.md) · [4. Fiches université](04-fiche-universite.md) · [5. Limites et tables](05-limites-et-tables.md)

---

## 2. Page VILLE `/v/` — bloc « Supérieur »

**Concerne 1 651 communes.** Il se placerait **au-dessus du bloc Lycées** : la page descend
l'échelle scolaire (lycée → collège → primaire), le supérieur vient donc en tête.

⚠️ **Le H1 actuel devra évoluer** — « Classement des lycées à {ville} » ne couvrira plus le
contenu de la page. C'est un arbitrage SEO à part entière, la page rankant déjà sur cette
requête.

### Tableau 2.1 — « Les formations post-bac à {ville} » (le tableau principal)

**5 colonnes**, au format des tableaux ville existants (colonne `#` étroite comprise) :

| # | Formation | Établissement | Places | Taux d'accès |
|---|---|---|---|---|
| 1 | BTS Communication | Lycée Ozenne | 35 | 8 % |
| 2 | BTS Commerce International | Lycée Ozenne | 70 | 9 % |
| 3 | CPGE ECG | Lycée Ozenne | 24 | 14 % |

| Colonne affichée | Source |
|---|---|
| Formation | `Nom court de la formation` ou `Filière de formation (libellé)` |
| Établissement | `Nom de l'établissement` de la cartographie (déjà nettoyé) |
| Places | `Capacité de l'établissement par formation` |
| Taux d'accès | `Taux d'accès` (admissions) |

- **Inventaire** : `fr-esr-cartographie_formations_parcoursup.csv`, colonne `Commune`
  (remplie à 99,5 %), enrichi par `fr_esr_admissions_parcoursup.csv` et
  `fr-esr-parcoursup-apprentissage.csv` sur la clé formation.
- **Groupé par `Type principal`** — colonne déjà calculée dans la cartographie (22 valeurs :
  BTS, Licence, CPGE, BUT, Études de santé, IFSI…). Le regroupement remplace une colonne
  « Type », qui serait redondante et coûteuse en largeur.
  ⚠️ Ne pas grouper sur le libellé de formation : voir
  `note_fr-esr-cartographie_formations_parcoursup.md`, §2ter.
- **Filtrable par Type** — c'est ce tableau qui capte la longue traîne (« BTS MCO Lyon »,
  « prépa MPSI Toulouse »).
- ⚠️ **`Taux d'accès` sera vide sur les formations en apprentissage** : elles n'en ont pas,
  l'admission dépendant d'un contrat employeur. **Le critère est la voie, pas le diplôme** —
  un BTS scolaire a un taux d'accès, le même BTS en apprentissage n'en a pas. L'affichage
  se conditionne sur le fichier d'origine de la ligne.
- **Exemple Rouen** : 93 formations, 26 établissements — 56 BTS, 15 licences, 8 CPGE,
  5 études de santé, 3 art/design, 2 BUT, 4 autres.

**Colonnes disponibles mais non retenues** — `Candidats`, `Admis`, `% mentions TB`,
`Commune` (implicite sur une page ville), `Statut de l'établissement` (public/privé).
Cette dernière figure pourtant dans les tableaux Lycées et Collèges existants : à
réintroduire si la cohérence entre blocs prime sur la largeur.

### Bandeau 2.2 — stats de la ville

> **X formations post-bac** · **Y places** · taux d'accès moyen **Z %**

- **Source** : `fr-esr-cartographie_formations_parcoursup.csv` + `fr_esr_admissions_parcoursup.csv`, agrégation sur la commune.

### Cartes 2.3 — une par type d'établissement (optionnel, si le tableau seul est trop dense)

Une carte = un type, avec nom + 2 chiffres clés + lien vers la fiche :
Universités · Prépas (CPGE) · BTS · IUT (BUT) · Écoles (IFSI, écoles post-bac).

### Carte géographique

Les formations post-bac gagneraient à apparaître sur la **carte Leaflet existante**
(`id="map-school"`), au même titre que les lycées, collèges et écoles — sinon le supérieur
serait le seul bloc sans marqueur. F1 et F3 portent `Coordonnées GPS de la formation`
(remplie à 99–100 %).

⚠️ **Deux points d'attention** : les coordonnées sont livrées en **une seule chaîne**
(`"45.6943, 4.94283"`), à séparer en lat/lng au chargement. Et l'infobulle des marqueurs
affiche une **adresse postale** que ces fichiers ne contiennent pas — il faudrait la tirer
de l'Annuaire de l'éducation, faute de quoi les marqueurs du supérieur auraient une
infobulle plus pauvre que ceux des lycées.

### ⚠️ Éviter qu'un même lycée apparaisse deux fois

Un lycée portant un BTS ou une CPGE figurerait à la fois dans le bloc « Lycées » (pour son bac) et dans le bloc « Supérieur » (pour sa formation post-bac) — deux fois le même établissement à quelques centimètres d'intervalle, et deux marqueurs superposés sur la carte.

L'enjeu n'est pas marginal : sur Rouen, **56 des 93 formations post-bac sont des BTS**, portés très majoritairement par des lycées. Un bloc « Supérieur » exhaustif y serait donc composé pour l'essentiel des établissements déjà listés juste au-dessus.

#### Structure proposée

| Bloc | Contenu | Ce qui change |
|---|---|---|
| **Lycées** (existant) | Les lycées de la ville, avec une colonne **« Post-bac »** indiquant `BTS`, `CPGE`, `BTS · CPGE` ou `—` | Une colonne ajoutée ; le détail (formations, places, taux d'accès) vit sur la fiche `/s/` du lycée |
| **Supérieur** (nouveau) | Universités, IUT, écoles d'ingénieurs, écoles de commerce, IFSI, écoles d'art — l'enseignement supérieur hors lycée | Ne reprendrait pas les lycées |

Trois raisons de pencher pour cette répartition :

1. **Elle suivrait la logique de la page**, qui liste des **établissements**, pas des formations. Un lycée à BTS reste un lycée : le post-bac est une caractéristique de plus, au même titre que son taux de réussite.
2. **Le bloc Supérieur y gagnerait une identité claire** — sur Rouen, il passerait de 93 lignes à environ 25, toutes réellement post-bac.
3. **La carte resterait lisible** : un marqueur par établissement, sans superposition.

#### Le point à surveiller

« BTS MCO Rouen » est une requête réelle, et la page doit continuer d'y répondre. Le contenu ne disparaît pas — il est porté par la fiche lycée plutôt que par le tableau de la page ville. Un libellé explicite dans la colonne « Post-bac » (par exemple `BTS MCO, BTS GPME`) plutôt qu'un simple `BTS` permettrait de garder ces termes sur la page ville.

C'est le seul arbitrage de ce document où le gain SEO et la lisibilité tirent dans des directions un peu différentes : à trancher ensemble si le sujet paraît sensible.

#### Cas concret

`enseigna.fr/s/lycee-la-nativite` (Aix-en-Provence) porte **deux CPGE économiques** (ECG Maths approfondies + ESH, ECG Maths appliquées + ESH) — 598 candidats pour 32 places
sur la première, 350 pour 16 sur la seconde. La fiche actuelle n'en dit rien.

Avec cette répartition : la page ville d'Aix signalerait `CPGE` dans la colonne Post-bac du bloc Lycées, et le détail chiffré vivrait dans la section « Après le bac » de la fiche
(voir [volet 2](02-fiche-lycee.md)).

---

---

## 3. Page DÉPARTEMENT `/d/` — classements

**Concerne 104 départements.** Pas d'inventaire ici (ce serait dupliquer la page ville) :
uniquement ce qui n'existe qu'à cette échelle.

### Tableau 3.1 — « Classement des prépas (CPGE) du {département} »

**5 colonnes** :

| # | Lycée | Prépa | Étudiants | Taux d'accès |
|---|---|---|---|---|
| 1 | Lycée Pierre de Fermat | MPSI | 141 | 7 % |
| 2 | Lycée Ozenne | BTS Communication | 92 | 8 % |

| Colonne affichée | Source |
|---|---|
| Lycée | `Établissement` (admissions) |
| Prépa | `Spécialité` (effectifs CPGE) ou `Filière de formation (libellé)` |
| Étudiants | `Étudiants (total)` de `fr-esr-effectifs-cpge.csv` |
| Taux d'accès | `Taux d'accès` de `fr_esr_admissions_parcoursup.csv` |

- **Tri** : `Taux d'accès` **croissant** — plus le taux est bas, plus la prépa est
  sélective.
- **Couverture** : 986 CPGE dans 415 lycées, taux d'accès à 100 %, effectifs à 99 %.
- Chaque ligne pointerait vers la fiche `/s/` du lycée — maillage gratuit, l'UAI est commun.

**Colonnes disponibles mais non retenues** — `Places`, `Candidats`, `% mentions TB`,
`Nombre de filles` / `Nombre de garçons`, `Filière`.

### Tableau 3.2 — « Les formations les plus sélectives du {département} »

**5 colonnes** :

| # | Formation | Établissement | Candidats | Taux d'accès |
|---|---|---|---|---|
| 1 | BTS Maintenance | Lycée Alexis de Tocqueville | 412 | 27 % |
| 2 | BTS Biologie médicale | Lycée Emile Littré | 388 | 52 % |

- **Source** : `fr_esr_admissions_parcoursup.csv`, tri taux d'accès croissant, **top 10**.
- ⚠️ **Les formations en apprentissage sont à exclure** : sans taux d'accès, elles ne
  peuvent pas être classées.

⚠️ **Un point éditorial à trancher.** Le bloc Lycées de vos pages classe par **taux de
réussite** (un indicateur de qualité) ; ce tableau classerait par **taux d'accès** (un
indicateur de difficulté d'entrée). Ce ne sont pas les mêmes choses, et un lecteur pressé
lira « 42e » comme « mauvais établissement ».

Exemple : l'Institut Saint-Lô affiche 93 % de taux d'accès sur son BTS MCO — soit
42e sur 45 dans la Manche. Cela ne dit rien de la qualité de sa formation, seulement qu'elle
accueille presque tous ses candidats.

Deux garde-fous possibles : conserver le titre « **les plus sélectives** » plutôt que
« classement », et ajouter une phrase du type « la sélectivité mesure la difficulté d'accès,
pas la qualité de la formation ».

**Colonnes disponibles mais non retenues** — `Places`, `Admis`, `% mentions TB`, `Commune`.

### Bandeau 3.3 — stats du département

> **X formations post-bac** · **Y places** · taux d'accès moyen **Z %** (vs **W %** France)

### Ce qu'on n'affiche PAS : le classement des universités

**Voir le [volet 1](01-principes-et-perimetres.md)** — une université se classe par **académie**, jamais par département.

Sur une page département : lister les **implantations présentes** (campus, antenne, IUT)
avec un lien vers la fiche de l'université mère, et une phrase de contexte
(« Le Morbihan relève de l'académie de Rennes, qui compte 4 universités »). Le classement
lui-même vit sur la fiche `/s/`.

---
