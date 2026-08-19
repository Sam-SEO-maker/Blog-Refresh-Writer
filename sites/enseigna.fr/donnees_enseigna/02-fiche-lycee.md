# 2. Fiches lycée `/s/` — section « Après le bac »

> 📄 **Dossier « Enseignement supérieur »** — [Index](00-index.md) · [1. Principes](01-principes-et-perimetres.md) · [2. Fiches lycée](02-fiche-lycee.md) · [3. Pages ville et département](03-ville-et-departement.md) · [4. Fiches université](04-fiche-universite.md) · [5. Limites et tables](05-limites-et-tables.md)

---

## 1. Page `/s/` — sections ajoutées sur un LYCÉE à post-bac

**Concerne 2 586 lycées** (ceux qui portent au moins une formation post-bac).

### Où s'insérerait la section

Les fiches lycée suivent la chronologie de la scolarité. La section « Après le bac »
viendrait **entre « Réussite au bac et taux de mention » et « Corps enseignant »** :

| Ordre | Section (h2) | Statut |
|---|---|---|
| 1 | Spécialités proposées au Lycée {X} | existante — reçoit le tableau 1.5 |
| 2 | Réussite au bac et taux de mention | existante |
| 3 | **Après le bac : les formations du Lycée {X}** | **nouvelle — tableaux 1.1 à 1.4** |
| 4 | Corps enseignant | existante |

La logique de lecture est respectée : ce qu'on choisit (spécialités) → ce qu'on obtient
(le bac) → ce qu'on peut faire ensuite dans ce lycée (BTS, CPGE). Le bloc « Corps
enseignant » est institutionnel et reste en fin de page, où il ne coupe pas le fil.

Cet enchaînement met aussi en vis-à-vis deux informations complémentaires : le tableau 1.5
donne les débouchés **nationaux** des spécialités du lycée, la section « Après le bac »
donne les formations que **ce lycée** propose lui-même.

**Exemple** : `enseigna.fr/s/lycee-institut-saint-lo` porte 3 formations post-bac
(2 BTS MCO — voie scolaire et apprentissage — et 1 BTS Management opérationnel de la
sécurité). Aucune n'apparaît aujourd'hui sur la fiche.

⚠️ **Un cas à connaître** : cet établissement est enregistré à **Agneaux**, commune
limitrophe, sous le libellé « CFA Don Bosco - Lycée Institut Saint-Lo » (UAI `0500120J`).
La jointure se fait donc sur l'UAI, jamais sur le nom ou la commune — et sur la page ville,
ses formations apparaîtraient sur `/v/agneaux`, pas sur `/v/saint-lo`.

### Tableau 1.1 — « Les BTS du lycée {X} »

**4 colonnes** :

| Formation | Places | Candidats | Taux d'accès |
|---|---|---|---|
| BTS Communication | 35 | 2 493 | 8 % |
| BTS Commerce International | 70 | 4 427 | 9 % |
| BTS Gestion de la PME | 59 | 2 201 | 22 % |

*Exemple réel : lycée Ozenne, Toulouse.*

| Colonne affichée | Colonne du fichier `fr_esr_admissions_parcoursup.csv` |
|---|---|
| Formation | `Filière de formation (libellé)` |
| Places | `Capacité de l'établissement par formation` |
| Candidats | `Effectif total des candidats pour une formation` |
| Taux d'accès | `Taux d'accès` |

- **Requête** : filtre sur l'UAI du lycée + `Filière de formation très agrégée = BTS`.
- **Couverture** : 5 351 BTS dans 2 175 établissements, colonnes chiffrées à 100 %.

**Colonnes disponibles mais non retenues** — `Admis` (redondant avec Places, dont il est
très proche), `% mentions TB`, `% boursiers`, `% filles`, et les 6 colonnes de profil des
admis. Elles restent dans le fichier ; le profil détaillé pourrait vivre dans un dépliable
(§1.3) plutôt que dans le tableau principal.

### Tableau 1.2 — « Les prépas (CPGE) du lycée {X} »

Deux tableaux plutôt qu'un seul : chacun a sa source, sa granularité et tient en
**4 colonnes**. Les fusionner obligerait à mélanger deux niveaux de détail (voir plus bas).

#### 1.2a — « Les prépas du lycée {X} » (qui y étudie)

| Prépa | Nombre de filles | Nombre de garçons | Étudiants |
|---|---|---|---|
| ECG | 103 | 80 | 183 |
| BCPST | 70 | 22 | 92 |
| ENS Paris-Saclay Éco-Gestion | 30 | 38 | 68 |
| ECT | 44 | 21 | 65 |
| ENS Rennes D1 | 45 | 16 | 61 |
| TB | 38 | 17 | 55 |
| ATS Économie-Gestion | 18 | 15 | 33 |

*Exemple réel : lycée Ozenne, Toulouse — 557 étudiants en CPGE.*

- **Source unique** : `fr-esr-effectifs-cpge.csv`, une ligne par spécialité.
  Colonnes `Spécialité`, `Nombre de filles`, `Nombre de garçons`, `Étudiants (total)`.
- **Recouvrement : 99,0 %** (411 des 415 lycées à CPGE) — le meilleur du corpus.
- Format identique au tableau « Spécialités en Terminale » déjà en ligne : continuité de
  lecture immédiate.

**Ce que la ventilation par sexe apporte.** L'écart est très marqué et constitue une
information d'orientation réelle : à Fermat (Toulouse), la prépa Lettres compte 37 filles
pour 9 garçons, quand MP en compte 9 pour 34. Un effectif global le masquerait.

**Colonnes disponibles mais non retenues** — `Étudiants en 1re année`, `en 2e année`,
`Filière` (scientifique / économique / littéraire, utile pour grouper ailleurs).

#### 1.2b — « Admissions en prépa » (à quel point c'est sélectif)

| Prépa | Places | Candidats | Taux d'accès |
|---|---|---|---|
| ECG — Maths appliquées + ESH | 24 | 1 976 | 14 % |
| ENS Rennes D1 | 30 | 1 896 | 19 % |
| ECG — Maths approfondies + ESH | 24 | 1 387 | 26 % |
| ECG — Maths appliquées + HGG | 24 | 1 456 | 26 % |
| BCPST | 48 | 1 786 | 32 % |
| ENS Cachan D2 | 40 | 1 177 | 44 % |
| ECG — Maths approfondies + HGG | 24 | 1 098 | 50 % |
| TB | 30 | 355 | 64 % |

*Même lycée. Tri par taux d'accès croissant — de la plus sélective à la plus accessible.*

- **Source** : `fr_esr_admissions_parcoursup.csv`, filtre
  `Filière de formation très agrégée = CPGE`, jointure sur l'UAI.
- **Couverture** : 986 formations CPGE dans 415 lycées, taux d'accès à **100 %**.
- **Libellé de la colonne Prépa** : utiliser `Filière de formation détaillée bis`, et non
  `Filière de formation (libellé)` — voir l'avertissement ci-dessous.
- Ce tableau pourrait être **dépliable** si la page devient chargée.

⚠️ **Une prépa peut avoir plusieurs classes, aux taux très différents.** Ozenne a
**4 classes ECG** dont les taux d'accès vont de **14 % à 50 %**. C'est une information
réelle — les classes ne se valent pas —, mais elle impose de les distinguer à l'affichage.

`Filière de formation (libellé)` les nomme toutes « CPGE - ECG » : inutilisable tel quel.
La colonne **`Filière de formation détaillée bis`** les sépare correctement
(« ECG - Mathématiques approfondies + ESH », « ECG - Mathématiques appliquées + HGG »…).

**Colonnes disponibles mais non retenues** — `Admis` (quasiment toujours égal à `Places` :
48/48, 24/24, 31/30 — les CPGE remplissent leurs places, la colonne n'apprend rien),
`% mentions TB`, `% boursiers`, `% même académie`.

#### Pourquoi deux tableaux et non un seul

Les deux fichiers **n'ont pas la même granularité** : côté effectifs, Ozenne a **une** ligne
ECG (183 étudiants) ; côté admissions, il en a **quatre** (une par classe, 24 places
chacune). Afficher « Places 24 » à côté de « Étudiants 183 » sur la même ligne serait faux.

Les agréger côté admissions ne règle rien : places et candidats s'additionnent, mais **le
taux d'accès ne s'additionne pas**. Il faudrait afficher une fourchette (« 14–50 % ») ou un
taux recalculé, tous deux difficiles à expliquer au lecteur.

Deux tableaux séparés préservent les deux informations sans en fausser aucune — et c'est
déjà la logique des fiches actuelles, qui séparent « Spécialités en Terminale »
(filles/garçons) et « Réussite au bac par filière ».

⚠️ Cette ventilation par sexe **n'existe que pour les CPGE**. Ni les BTS ni les licences
n'en disposent : le fichier des admissions ne porte qu'un `% d'admis dont filles`, qui est
une part des admis, pas un effectif d'inscrits.

### Tableau 1.3 — « Profil des admis » (dépliable)

**4 colonnes**, dans un bloc dépliable sous les tableaux 1.1 et 1.2 :

| Formation | % bac général | % bac techno | % bac pro |
|---|---|---|---|
| BTS Communication | 62 % | 31 % | 7 % |

- **Source** : `fr_esr_admissions_parcoursup.csv`, colonnes `% d'admis néo bacheliers
  généraux` / `technologiques` / `professionnels`. Remplies à 100 %.
- Le dépliable permet d'assumer un tableau supplémentaire sans alourdir la page.

**Colonnes disponibles mais non retenues** — `% boursiers`, `% filles`,
`% même académie`, `% mentions TB`, `% mention (BG/BT/BP)`. Un second dépliable
« Origine sociale et géographique » resterait possible si le besoin apparaît.

### Bloc 1.4 — « Que deviennent les diplômés ? » (encadré, pas un tableau)

> Insertion des diplômés de BTS de cet établissement : **X %** en emploi 6 mois après la
> sortie · **Y %** poursuivent leurs études.

- **Source** : `fr-en-inserjeunes-lycee_pro-bts.csv`, jointure UAI. **1 030 établissements sur 1 971 ont un taux d'emploi**
  (52 %), et 81,7 % ont un taux de poursuite d'études.
- ⚠️ **Formulation à privilégier** : « diplômés de BTS **de cet établissement** », jamais
  « de ce BTS ». Le chiffre est une moyenne sur tous les BTS du lycée, et l'écart interne
  atteint 15 points en médiane (jusqu'à 55). La colonne `Nombre de formations BTS` dit sur
  combien de formations porte la moyenne.
- **Affichage conditionnel** : le bloc pourrait être masqué faute de donnée.

### Tableau 1.5 — « Où mènent ces spécialités ? »

#### Où l'afficher

Sur la fiche lycée, dans la section **« Spécialités proposées au Lycée {X} »**, qui existe
déjà et contient deux tableaux (« Spécialités en Première », « Spécialités en Terminale »).
Le nouveau tableau viendrait **juste sous « Spécialités en Terminale »**.

Exemple de page concernée : `enseigna.fr/s/lycee-condorcet-0693478F`.

Il ne relèverait **pas** de la section « Après le bac » (§1.1 à §1.4) : celle-ci traite des
BTS et CPGE hébergés par le lycée, alors qu'il s'agit ici du devenir des bacheliers
généraux.

#### Structure du tableau

**Une ligne par débouché** — c'est exactement une ligne du fichier source, sans agrégation :

| Spécialités | Débouché | Admis en France |
|---|---|---|
| HGGSP + SES | Licence Sciences juridiques | 23 396 |
| HGGSP + SES | Licence Histoire | 7 598 |
| HGGSP + SES | Licence Sciences politiques | 2 336 |
| Maths + Physique-Chimie | Formation d'ingénieur Bac+5 | 13 604 |
| Maths + Physique-Chimie | Licence PASS | 9 233 |
| Maths + Physique-Chimie | PCSI | 7 888 |

Les **doublets affichés sont ceux effectivement proposés par ce lycée** (ils viennent du
tableau « Spécialités en Terminale » déjà en base) ; les débouchés et les nombres viennent
du fichier des débouchés (ci-dessous).

Avec un top 5 par doublet, un lycée proposant 6 doublets afficherait 30 lignes : un
regroupement visuel par doublet, ou un dépliable, serait sans doute nécessaire.

#### Où trouver les données, colonne par colonne

Fichier : `fr-esr-parcoursup-enseignements-de-specialite-bacheliers-generaux-3.csv`
(17 211 lignes, bac 2025, séparateur `;`).

| Ce qu'on affiche | Colonne du fichier |
|---|---|
| Le doublet de spécialités | `Enseignements de spécialité` |
| Le nom du débouché | `Formation` |
| Le nombre d'admis | `Nombre de candidats bacheliers ayant accepté une proposition d'admission` |

**La requête** ressemblerait à :

1. Filtre `Niveau d'agrégation = 2` (le seul niveau détaillé — voir précaution 3).
2. Filtre `Enseignements de spécialité` sur le doublet de la ligne affichée.
3. Tri sur le nombre d'admis, décroissant.
4. Top 5.

**Couverture** : 75 doublets × 313 formations, soit 11 661 lignes exploitables au niveau 2.
Tous les doublets proposés en lycée sont couverts.

Deux colonnes complémentaires existent si un affichage plus riche est souhaité :
`Nombre de candidats bacheliers ayant confirmé au moins un vœu` (les candidats) et
`… ayant reçu au moins une proposition d'admission` (les propositions). Elles permettraient
d'afficher un taux d'admission par débouché — non retenu pour l'instant, pour rester
lisible.

**Pourquoi ce tableau plutôt qu'un autre.** Les fiches lycée affichent déjà les spécialités
proposées, avec les effectifs filles/garçons par doublet. Le lecteur type n'est pas un
candidat Parcoursup : c'est un **élève de Seconde et ses parents**, qui choisissent des
spécialités sans savoir ce qu'elles ouvrent. Aujourd'hui la page dit « 19 filles et
9 garçons ont pris SES + SVT ici » ; elle ne dit pas où ça mène. C'est la question que se
pose réellement la famille au moment du choix, et personne n'y répond avec des chiffres.

**Exemple réel — les doublets contenant HGGSP** (12 doublets, 80 966 admis cumulés) :

| Débouché | Admis |
|---|---|
| Licence Sciences juridiques | 23 396 |
| Licence Histoire | 7 598 |
| Lettres | 3 054 |
| Licence Langues et littératures étrangères | 2 617 |
| Licence LEA | 2 409 |
| Licence Sciences politiques | 2 336 |

⚠️ **Trois précautions**

1. **Les chiffres sont nationaux.** À écrire explicitement (« en France », « tous lycées
   confondus »), sinon la famille les lira comme les débouchés des élèves de ce lycée.

2. **Les libellés diffèrent entre les deux sources** — c'est le vrai travail de cette
   fonctionnalité. La fiche lycée affiche
   `SCIENCES ECONOMIQUES ET SOCIALES/SCIENCES DE LA VIE ET DE LA TERRE`
   (séparateur `/`, majuscules, sans accents) ; F8 écrit
   `Mathématiques Spécialité,Physique-Chimie Spécialité`
   (séparateur `,`, casse normale, suffixe « Spécialité »).

   ⚠️ **Ne pas découper F8 sur la virgule** : plusieurs libellés en contiennent une
   *à l'intérieur* — `Histoire-Géographie, Géopolitique et Sciences politiques`,
   `Langues, littératures et cultures étrangères et régionales`,
   `Humanités, Littérature et Philosophie`. Un `split(',')` produirait de fausses
   spécialités.

   **Piste** : une table de correspondance des **75 doublets** du fichier des débouchés vers
   les libellés de la base lycée. C'est fini, énumérable, et à faire une fois.

3. **Ne pas sommer les niveaux d'agrégation** : ce fichier empile trois niveaux (0, 1, 2) qui ne
   s'additionnent pas — sommer sans filtrer produirait un triple comptage. Filtrer sur `2`.

**Bénéfice de maillage** : ce tableau relie les fiches lycée aux formations post-bac, et
le chemin inverse fonctionne aussi — « les spécialités des admis en MPSI » sur une future
page CPGE.

### Ce qu'il ne serait pas affiché ici

- **Le rang du dernier appelé** : disponible dans la source, écarté pour ne pas alourdir.
  À redemander si besoin.
- **Les BTS en apprentissage** du lycée : ils sont dans F3, sans taux d'accès ni admis
  (voir [volet 5 — limites](05-limites-et-tables.md)).

---
