# Note explicative — MonMaster

---

Ce fichier est l'équivalent de Parcoursup **pour l'entrée en master** : pour chaque mention
de master, combien de candidats se sont présentés, combien ont reçu une proposition, et
d'où ils venaient (licence générale, licence pro, BUT). Le master ne passe **pas** par
Parcoursup mais par la plateforme MonMaster — c'est pourquoi il ne figure dans aucun des
huit autres fichiers.

**Source** : data.enseignementsup-recherche.gouv.fr — jeu `fr-esr-mon_master`
(« MonMaster 2024 & 2025 : vœux de poursuite d'études et de réorientation en master et
réponses des établissements »), filtré sur la **session 2025**.

---

## 1. Format et volumétrie

| | |
|---|---|
| Séparateur | `;` (point-virgule) |
| Encodage | UTF-8 **avec BOM** |
| Colonnes | 24 (filtrées et calculées depuis 137) |
| Lignes | 3 644 |
| Session | 2025 |
| Établissements distincts (UAI) | 110 |
| Mentions distinctes | 315 |

**Une ligne = une mention de master dans un établissement**, pour une modalité donnée
(classique ou alternance).

⚠️ **Le fichier source est au parcours, pas à la mention.** Les 8 167 lignes d'origine
décrivent 6 423 parcours répartis sous 2 750 mentions : une université médiane en compte
**34 parcours pour 24 mentions**, et la plus fournie 241 parcours. Afficher les parcours
tels quels donnerait des fiches de 200 lignes. **L'agrégation à la mention a donc été faite
en amont** — les effectifs sont sommés, les taux recalculés après sommation, jamais
moyennés.

---

## 2. Les 24 colonnes

### Jointure et identification (5)

| Colonne | Usage |
|---|---|
| `eta_uai` | **Clé de jointure** — UAI, commun avec les 8 autres fichiers |
| `eta_nom` | Nom de l'établissement |
| `acad` / `acad_lib` | Académie — le périmètre de classement des universités |
| `session` | 2025 sur toutes les lignes |

### Formation (6)

| Colonne | Usage |
|---|---|
| `mention` | **Le libellé à afficher** (« ANTHROPOLOGIE », « DROIT DES AFFAIRES ») — 315 valeurs |
| `disci_lib` | Discipline, pour le regroupement |
| `secteur_disci_lib` | Secteur disciplinaire, niveau intermédiaire |
| `alternance` | `0` = classique (7 009 lignes source), `1` = alternance (1 158) |
| `nb_parcours` | Nombre de parcours agrégés sous cette mention — indique la finesse perdue |
| `lieux` | Sites de la formation, séparés par ` \| ` |

### Le cœur des données (5)

| Colonne | Tableau |
|---|---|
| `n_can_pp` | Candidats (phase principale) |
| `n_clas_total` | Candidats classés par l'établissement |
| `n_prop_total` | **Propositions faites** |
| `n_accept_total` | Acceptations |
| `part_propositions` | **`n_prop_total / n_can_pp`** — la colonne de classement (voir §3) |

### Origine des candidats (7)

`n_can_lg3_pp` (licence générale) · `n_can_lp3_pp` (licence pro) · `n_can_but3_pp` (BUT) ·
`n_can_master_pp` · `n_can_autre_pp` · `origine_dominante` · `part_origine_dominante`

Les deux dernières sont **calculées** : l'origine la plus représentée et sa part. Elles
évitent d'afficher cinq colonnes d'effectifs pour une information qui tient en une phrase.

Répartition de `origine_dominante` sur les lignes source : Licence générale 6 753 ·
BUT 402 · Autre 250 · Licence pro 144 · Master 137.

---

## 3. ⚠️ Le piège de calcul — ne pas diviser les admis par les candidats

**C'est le point principal de cette note.** La tentation est de reproduire le taux d'accès
Parcoursup en faisant `n_accept_total / n_can_pp`. **Ce calcul est faux en master.**

| Calcul | Médiane observée |
|---|---|
| `n_accept_total / n_can_pp` | **6,5 %** ❌ |
| `n_prop_total / n_can_pp` | **21,2 %** ✅ |

En master, un candidat postule à des dizaines de mentions et n'en accepte qu'une. Le rapport
acceptations/candidats mélange donc **la sélectivité de l'établissement** avec **le choix des
candidats admis ailleurs** — et ce second effet domine largement.

Exemple réel, master Bio-informatique à l'Université Paris Cité : 406 candidats,
60 classés, **58 propositions**, 19 acceptations. Le calcul par les acceptations donne
4,7 % et ferait passer ce master pour plus sélectif que Polytechnique. Le calcul par les
propositions donne **14,3 %**, qui est la vraie sélectivité.

**Colonne à utiliser : `part_propositions`.** `n_accept_total` reste dans le fichier pour
information, mais ne doit jamais servir de dénominateur d'un taux d'accès.

---

## 4. Conventions et limites

**Phases `pp` et `pc`.** La procédure a une phase principale et une phase complémentaire.
Le fichier source distingue les deux ; **seule la phase principale (`pp`) est retenue ici**
— 8 161 lignes source sur 8 167, contre 3 580 en phase complémentaire. Additionner les deux
double-compterait les candidats présents dans les deux phases.

**⚠️ Couverture : 110 UAI, et des absents notables.** MonMaster ne couvre que les masters
recrutant **par la plateforme**. Tout établissement à procédure propre en est absent —
et il ne s'agit pas de cas marginaux :

- **Les IEP / Sciences Po** : zéro ligne dans le fichier, sur les 18 IEP recensés dans
  Parcoursup. Aucun de leurs masters n'y apparaît — ils recrutent par concours ou admission
  interne après leur cycle 1.
- **Les écoles de commerce et d'ingénieurs** à recrutement propre.
- Plus largement, toute mention à recrutement dérogatoire.

Concrètement, une académie peut n'être représentée que par ses universités : celle
d'Aix-Marseille ne contient que **deux** établissements dans ce fichier (Aix-Marseille
Université et Avignon Université), alors que son IEP existe et recrute.

**Conséquence d'affichage** : ce fichier alimente des tableaux **par établissement**
(« les masters de {université} »), jamais un panorama géographique. Un tableau « les masters
à {ville} » construit sur ce fichier serait **faux par omission** — et l'omission porterait
sur des établissements réputés, que les lecteurs locaux repèrent immédiatement.

Les 110 UAI recouvrent les **65 universités** du référentiel
`fr-esr-principaux-etablissements`, le reste étant des grands établissements et des
écoles effectivement présentes sur la plateforme.

**Alternance.** Comme pour l'apprentissage Parcoursup (voir
`note_fr-esr-parcoursup-apprentissage.md`), une mention en alternance a une logique
d'admission différente. Les deux modalités sont ici sur des **lignes distinctes** :
filtrer sur `alternance` plutôt que de les additionner.

**Ce que ce fichier ne dit pas.** Il est vu **depuis le master d'arrivée**, jamais depuis la
licence de départ. Il n'y a **pas d'UAI d'origine** des candidats : impossible de construire
« les licenciés de l'université X vont majoritairement en master à Y ». Le **taux de
poursuite après licence** n'existe pas non plus dans ce fichier — ni ailleurs en open data
par établissement. Il n'est publié qu'au niveau **national** par le SIES (63 % des diplômés
2024 de licence générale s'inscrivent en master l'année suivante) : c'est de la matière
d'article, pas une colonne de tableau.

---

## 5. Ce que ce fichier permet

### Fiches UNIVERSITÉ `/s/` — tableau 4.3 « Les masters »

| Mention | Candidats | Propositions | Part de propositions |
|---|---|---|---|

Le champ `origine_dominante` complète en dépliable ou en note de bas de tableau — il ferait
sinon une cinquième colonne, hors gabarit.

**Couverture** : 110 UAI, 24 mentions par université en médiane. Une fiche affiche donc un
tableau substantiel sans être ingérable, à condition de rester à la mention.

### Ce qu'il ne permet pas

Ni classement par qualité de formation, ni taux de réussite en master, ni devenir des
diplômés. `part_propositions` est une mesure **d'accès**, de la même famille que le taux
d'accès Parcoursup — pas un indice de qualité.
