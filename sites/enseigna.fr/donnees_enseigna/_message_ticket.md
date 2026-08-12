Réponse à ta demande sur les données du supérieur.

**Pièce jointe** : `donnees_superieur_enseigna.zip` (4,9 Mo) — 12 fichiers CSV filtrés,
leurs 12 notes explicatives, et la doc en 6 volets (index + 5).

---

### Ce qui est prêt

12 jeux de données, tous filtrés sur les colonnes utiles et documentés fichier par fichier
(une note `note_<nom>.md` par CSV : format, pièges, clés de jointure, couverture réelle).

| Fichier | Contenu | Lignes |
|---|---|---|
| `fr-esr-cartographie_formations_parcoursup.csv` | Inventaire : qui propose quoi, et où (2026) | 25 838 |
| `fr_esr_admissions_parcoursup.csv` | Places, candidats, admis, taux d'accès (2025) | 14 252 |
| `fr-esr-parcoursup-apprentissage.csv` | Inventaire + volume apprentissage (2025) | 11 536 |
| `fr-esr-parcoursup-enseignements-de-specialite-…csv` | Débouchés par doublet de spécialités | 17 211 |
| `fr-esr-insersup.csv` | Insertion des diplômés du supérieur | 10 399 |
| `fr-esr-mon_master.csv` | **Admissions en master (2025)** — candidats, propositions, origine | 3 644 |
| `fr-esr-atlas-effectifs-etablissements.csv` | **Effectifs par établissement et niveau** BAC+1→BAC+6 (2024) | 22 068 |
| `fr-esr-diplomes-prepares-etablissements.csv` | **Santé + IEP** : effectifs par filière (2024-25) | 6 150 |
| `fr-en-inserjeunes-cfa.csv` | Insertion après apprentissage | 2 758 |
| `fr-en-inserjeunes-lycee_pro-bts.csv` | Insertion après BTS scolaire | 1 971 |
| `fr-esr-effectifs-cpge.csv` | Effectifs CPGE par lycée, spécialité et sexe (2025-2026) | 1 707 |
| `fr-esr-principaux-etablissements-…csv` | Référentiel : académie, typologie, effectif | 245 |

### La doc, en 5 volets

Découpée pour être lisible par étapes plutôt qu'en un seul document.
**Commencer par `00-index.md`**, qui sert de sommaire.

| Volet | Contenu | Quand |
|---|---|---|
| `01-principes-et-perimetres.md` | Les fichiers, leurs conventions et clés, la règle ville / département / établissement, le gabarit des tableaux | **En premier** — conditionne les tables |
| `02-fiche-lycee.md` | Section « Après le bac » : BTS, CPGE, profil, insertion, débouchés | Priorité 1 |
| `03-ville-et-departement.md` | Bloc « Supérieur » sur `/v/`, classements sur `/d/` | Priorités 2 et 3 |
| `04-fiche-universite.md` | Licences, campus, masters — **pages à créer** | Priorité 4 |
| `05-limites-et-tables.md` | Limites open data, piste de tables, arbitrages | **Avant de modéliser** |

Chaque tableau proposé indique son en-tête exacte, un exemple chiffré réel et la
correspondance colonne → fichier.

---

### Les tableaux proposés

Tous tiennent dans le gabarit relevé sur les pages actuelles : **4 colonnes max sur une
fiche établissement, 5 à 6 sur une page ville ou département**.

| # | Page | Tableau | En-têtes |
|---|---|---|---|
| 1.1 | `/s/` lycée | Les BTS du lycée | Formation · Places · Candidats · Taux d'accès |
| 1.2a | `/s/` lycée | Les prépas du lycée | Prépa · Nb de filles · Nb de garçons · Étudiants |
| 1.2b | `/s/` lycée | Admissions en prépa | Prépa · Places · Candidats · Taux d'accès |
| 1.3 | `/s/` lycée | Profil des admis *(dépliable)* | Formation · % bac général · % techno · % pro |
| 1.4 | `/s/` lycée | Que deviennent les diplômés ? | *encadré* |
| 1.5 | `/s/` lycée | Où mènent ces spécialités ? | Spécialités · Débouché · Admis en France |
| 2.1 | `/v/` ville | Les formations post-bac | # · Formation · Établissement · Places · Taux d'accès |
| 2.2 | `/v/` ville | Bandeau stats | *bandeau* |
| 3.1 | `/d/` dépt. | Classement des prépas | # · Lycée · Prépa · Étudiants · Taux d'accès |
| 3.2 | `/d/` dépt. | Formations les plus sélectives | # · Formation · Établissement · Candidats · Taux d'accès |
| 4.1 | `/s/` université | Les licences | Licence · Places · Candidats · Taux d'accès |
| 4.2 | `/s/` université | Campus et antennes | Campus · Ville · Formations · Places |
| 4.3 | `/s/` université | **Les masters** | Mention · Candidats · Propositions · Part de propositions |
| 4.4 | `/s/` université | **Les étudiants par niveau** | Niveau · Étudiants · Part |
| 4.5 | `/s/` université | **Les études de santé** *(si concernée)* | Filière · Étudiants |
| 4.6 | `/s/` IEP | **Les IEP** *(2 chiffres seulement)* | Indicateur · Valeur |
| 4.7 | `/s/` université | Insertion *(partiel, à arbitrer)* | Domaine · Taux d'emploi 12 mois · Moyenne France |

---



---

### Deux ajouts de dernière minute

**Le nombre d'étudiants était renseigné pour 44 % des établissements seulement.** Le
référentiel ne le donne que pour 109 des 245 — les universités surtout, très peu les
écoles. `fr-esr-atlas-effectifs-etablissements.csv` récupère **108 des 136 manquants** :
le bandeau « X étudiants » passe à **89 % de couverture**. Il apporte en plus la
ventilation par niveau (BAC+1 → BAC+6), qui donne le profil d'un établissement d'un coup
d'œil.

Il alimente le **tableau 4.4** (« Les étudiants par niveau »), qui se lit comme une
pyramide : l'Université de Lille passe de 19 681 étudiants en BAC+1 à 6 366 en BAC+6 et plus.
### Six points à connaître avant de modéliser

Détaillés dans la doc, avec les chiffres et les exemples — résumés ici en une ligne.

| # | Point | Où c'est traité |
|---|---|---|
| 1 | **Aucun taux de réussite post-bac n'existe** en open data, par établissement. Le classement du bloc « Supérieur » ne peut donc pas suivre la logique Lycées / Collèges | [Volet 5 §a](05-limites-et-tables.md) |
| 2 | **Le taux d'accès n'existe que pour la voie scolaire** : en apprentissage l'admission dépend d'un contrat employeur. Le critère est la voie, pas le diplôme | [Volet 1](01-principes-et-perimetres.md) — « Voie scolaire vs apprentissage » |
| 3 | **Une université se classe par académie**, jamais par département : elle est multi-sites (84 UAI). Ville et département afficheraient les implantations | [Volet 1 §0](01-principes-et-perimetres.md) |
| 4 | **Les fiches université sont à créer** — 65 nouvelles entrées, aucune n'existe (`/s/sorbonne-universite` → 404) | [Volet 4](04-fiche-universite.md) |
| 5 | ⚠️ **En master, ne pas diviser les admis par les candidats** : 6,5 % au lieu de 21,2 %. La colonne `part_propositions` est déjà calculée sur le bon ratio | [Volet 5 §d](05-limites-et-tables.md) |
| 6 | **Décalage de millésime assumé** : inventaire 2026, chiffres 2025, effectifs 2024 | [Volet 5 §c et §e](05-limites-et-tables.md) |

Les deux qui coûteraient le plus cher à découvrir tard :

⚠️ **Le point 5** — le calcul faux produit des chiffres plausibles, pas une erreur visible.
Exemple : master Bio-informatique à Paris Cité, 4,7 % par les acceptations contre **14,3 %**
par les propositions.

⚠️ **L'insertion n'est pas un critère de classement** d'université. Elle ne compte pas les
poursuites d'études, or **63 % des diplômés de licence générale s'inscrivent en master**
(SIES, national) : le taux ne porte que sur une minorité non représentative. Affichable sur
les diplômes professionnalisants terminaux (BTS, apprentissage), pas ailleurs.
⚠️ Sa colonne d'effectif s'appelle `effectifhdccpge` = « **hors doubles comptes CPGE** » :
elle **exclut** les élèves de prépa, malgré ce que le nom laisse croire. Pour les CPGE,
c'est `fr-esr-effectifs-cpge.csv` qui fait foi.

**La santé et les IEP avaient besoin d'une source dédiée.**
`fr-esr-diplomes-prepares-etablissements.csv` donne les effectifs de médecine (44 UAI),
pharmacie (27), odontologie (23) et PASS/L.AS (64), plus le 2e cycle des IEP — les 18 IEP
étant absents de MonMaster, c'est la seule source qui les documente au-delà du post-bac.

Il alimente les **tableaux 4.5** (« Les études de santé », à n'afficher que sur les
universités concernées) et **4.6** (« Les IEP », deux chiffres seulement).

⚠️ **Trois limites à connaître** : la **maïeutique n'est pas isolable** (fondue dans
« autres formations de santé ») ; le **passage PASS/L.AS → 2e année de médecine n'existe
nulle part en open data** — ce sont les universités qui fixent leurs capacités depuis 2019,
donc aucun texte national à exploiter, et c'est précisément le chiffre que cherchent les
familles ; enfin ce fichier donne pour les IEP un **volume d'étudiants, pas une offre de
formation** — un tableau « les masters de {IEP} » n'est pas constructible.

---

### Deux clés de jointure

**Pour joindre deux établissements** → `UAI`, présent dans **10 des 12 fichiers** et déjà
dans la base lycées. Les deux exceptions sont la cartographie et le fichier des
spécialités, qui n'ont pas d'UAI (voir leurs notes).

Le nom de la colonne varie : `Code UAI de l'établissement` dans la plupart, `UAI` dans les
InserJeunes, `eta_uai` dans MonMaster, `etablissement_id_uai` dans le fichier santé/IEP.

⚠️ **L'Atlas est le seul à en avoir deux** : `id_etablissement` et `id_composante`. Les
IEP, IUT et UFR sont des **composantes** — une jointure qui ne regarde que
`id_etablissement` les perd tous. Il faut matcher sur l'une **ou** l'autre.

**Pour joindre deux formations** → la clé Parcoursup, qui porte trois noms différents selon
le fichier :

| Fichier | Nom de la colonne |
|---|---|
| Cartographie | `Code interne Parcoursup de la formation` |
| Admissions | `cod_aff_form` |
| Apprentissage | `Numéro d'identification de la formation dans Parcoursup` |

C'est **celle-ci** qu'il faut utiliser : 95 % de correspondances, toutes vérifiées sur le
même établissement.

⚠️ **Et surtout pas `code_formation`.** Cette colonne de la cartographie ressemble à
une clé de formation, mais c'est un code MESR, sans rapport avec l'identifiant Parcoursup.

Le problème n'est pas qu'elle ne trouverait rien — c'est qu'elle **trouverait de mauvaises
correspondances**. Exemple réel, le code `5` :

| Fichier | Établissement | Formation |
|---|---|---|
| Admissions | La Prépa des INP — Nancy | Formation d'ingénieur |
| Cartographie | Lycée Tani Malandi de Chirongui (Mayotte) | Classe préparatoire |

Une jointure sur ce code rapproche ces deux lignes. La requête s'exécute sans erreur, aucune
ligne ne manque — mais les chiffres de Mayotte se retrouvent sur la fiche de Nancy.

212 codes sont dans ce cas (~1,5 % des lignes), et **aucun des 212 ne désigne le même
établissement des deux côtés**. Une jointure vide se voit tout de suite ; celle-ci passe
inaperçue jusqu'à ce qu'un lecteur signale une formation qui n'existe pas dans
l'établissement affiché.

**En résumé** : joindre sur `Code interne Parcoursup de la formation` (ou son équivalent
selon le fichier), jamais sur `code_formation`.

Le volet 1 contient aussi une section **« Conventions des fichiers »** : ce que mesurent
réellement les colonnes `Taux d'accès`, `Places` et `Admis`, les libellés de CPGE abrégés
en majuscules, et les identifiants (`mefstat11`, `aca_id`).

---

Dis-moi ce qui manque ou ce qui coince, on ajuste.
