# Note explicative — Cartographie des formations Parcoursup

---

Ce fichier est le **référentiel d'inventaire** des formations post-bac accessibles via
Parcoursup : il dit **qui propose quoi, et où**. Il ne contient **aucun chiffre
d'admission** — les candidats, admis, taux d'accès et % mentions TB viennent d'un
second fichier, à livrer séparément (voir §6).

---

## 1. Format et volumétrie

| | |
|---|---|
| Séparateur | `;` (point-virgule) |
| Encodage | UTF-8 **avec BOM** |
| Colonnes | 17 (15 filtrées depuis 25, + 2 ajoutées : traçabilité §2bis et `Type principal` §2ter) |
| Lignes | 25 838 |
| Session | 2026 |
| Établissements distincts | 6 511 |

**Une ligne = une formation dans un établissement**, pas un établissement. Une même
université apparaît sur des dizaines de lignes (une par licence proposée).

---

## 2. Les 17 colonnes

| Colonne | Usage |
|---|---|
| `Session` | Année de la campagne. Vaut `2026` sur toutes les lignes ici (colonne conservée comme clé, voir §5c) |
| `Identifiant de l'établissement` | **UAI — clé pivot** de tout l'écosystème MESR, déjà présent dans la base lycées |
| `Nom de l'établissement` | **Nettoyé** — suffixe géographique retiré, prêt à afficher (voir §2bis) |
| `Nom etablissement (source)` | **Ajoutée.** Libellé brut d'origine, conservé pour traçabilité. Ne pas afficher |
| `Types d'établissement` | `Publics` / `Privés` / `Privés en contrat avec l'Etat / EESC` |
| `Types de formation` | Libellé **brut** de la source. ⚠️ Multi-valué (68 combinaisons). Bon pour le **filtrage thématique**, pas pour grouper — voir §2ter |
| `Type principal` | **Ajoutée.** Un seul type par ligne, 22 valeurs — **la colonne à utiliser pour grouper** les formations sur `/v/` et `/d/`. Voir §2ter |
| `Nom long de la formation` | Libellé complet |
| `Mentions/Spécialités` | Spécialité de la formation |
| `Nom court de la formation` | Libellé court (ex. `L1-LLCER`), pratique pour les tableaux |
| `Région` | Géographie |
| `Département` | Géographie — alimente les pages `/d/` |
| `Commune` | Géographie — alimente les pages `/v/` et la table `implantations` |
| `Localisation` | `lat, lon` (renseignée à 100 %) |
| `Code interne Parcoursup de la formation` | **Clé unique de ligne** et clé de jointure avec les admissions (voir §4) |
| `Code interne Parcoursup pour les portails` | Regroupement des formations en portail |
| `code_formation` | Code MESR. ⚠️ **Pas une clé unique**, voir §4 |

### Colonnes supprimées (10) et pourquoi

`Formations en apprentissage` (une seule valeur distincte, booléen déguisé — l'info est
dans `Nom long de la formation`) · `Internat` (3,3 % remplie) · `Aménagement` (texte libre,
hors spec) · `Informations complémentaires` (16,8 %, texte libre) · `Lien vers la fiche
formation` et `Lien vers les données statistiques` (liens sortants Parcoursup, hors spec) ·
`Site internet de l'établissement` (hors spec) · `etablissement_id_paysage` (31,7 %,
référentiel concurrent de l'UAI) · `composante_id_paysage` (1,2 %, inexploitable) ·
`rnd` (technique).

Le fichier source complet (25 colonnes, sessions 2020→2026) reste disponible si besoin.

---

## 2bis. Nettoyage déjà appliqué au libellé des établissements

Dans la source, **100 % des libellés** portent un suffixe géographique :
`Lycée Condorcet (Saint-Priest - 69)`, `Lycée Elisa Lemonnier (Paris 12e  Arrondissement - 75)`.
Le nettoyage a été fait en amont, **directement dans la colonne
`Nom de l'établissement`** : elle est prête à afficher.

**Convention retenue : le nom nu, sans parenthèse géographique.** C'est le format déjà
en production sur le site — la page ville de Saint-Priest
(`enseigna.fr/v/saint-priest-3`) affiche « Lycée Condorcet » et « Lycée professionnel
Fernand Forest », sans mention de ville ni de département. Le contexte géographique est
porté par la page elle-même ; le répéter sur chaque ligne du tableau serait redondant.

| Cas | Exemple source | Après nettoyage |
|---|---|---|
| Ville + code département | `Lycée Condorcet (Saint-Priest - 69)` | `Lycée Condorcet` |
| Arrondissement | `Lycée Elisa Lemonnier (Paris 12e  Arrondissement - 75)` | `Lycée Elisa Lemonnier` |
| Code département seul | `Groupe Alternance Limoges (87)` | `Groupe Alternance Limoges` |
| Double parenthèse | `KEDGE… - Campus de Paris ( Paris 12e Arrondissement) (75)` | `KEDGE… - Campus de Paris` |
| Établissement étranger | `ESSCA School of Management - Malaga (Espagne)` | *inchangé* — voir ci-dessous |

Règle appliquée : la parenthèse finale n'est retirée que si son contenu est un code
département français valide (`01`→`95`, `2A`/`2B`, DOM), une mention d'arrondissement,
ou un couple `Ville - NN`. Les libellés à deux parenthèses sont traités en deux passes.
Les espaces multiples sont normalisés.

**Ce qui n'est PAS touché** — les parenthèses qui font partie du nom de l'établissement
sont conservées : `(EPE)` (149 lignes), `(Sciences-U Lyon)`, `(Cours Diderot - EDNH - EGPN)`,
`(CFAI)`… 206 formes distinctes au total, aucune de nature géographique.

⚠️ **Les 21 campus à l'étranger gardent leur pays** (`… - Malaga (Espagne)`,
`… Campus de Rabat-Salé (Maroc)`). Leurs colonnes `Département` et `Commune` sont **vides** :
le libellé est leur seule information géographique, la retirer l'effacerait complètement.
Ces lignes sont à exclure des pages `/v/` et `/d/`.

### Résultat et contrôles

| Contrôle | Résultat |
|---|---|
| Lignes | 25 838 — inchangé |
| Lignes modifiées | 25 805 (33 libellés étaient déjà propres) |
| Nom vide après nettoyage | ✅ aucun (garde-fou : si le nettoyage viderait le nom, la source est gardée) |
| Aucun caractère inventé ni réordonné | ✅ le nom nettoyé est toujours un extrait exact de la source |
| Résidus « Arrondissement » | ✅ 0 |
| Libellé source préservé | ✅ colonne `Nom etablissement (source)`, intégrale |
| Noms distincts | 7 128 après nettoyage, contre 7 602 avant |

---

## 2ter. Colonne `Type principal` — pour grouper les formations

`Types de formation` cumule plusieurs types sur **3 220 lignes (12,5 %)**, soit 68
combinaisons distinctes. Impossible de grouper proprement les formations par type sur les
pages `/v/` et `/d/` avec cette colonne. La colonne **`Type principal`** ramène chaque ligne
à **un seul type — 22 valeurs au total**. La colonne brute est conservée : elle reste un bon
**filtre thématique** (voir plus bas).

### La règle : le diplôme prime sur la thématique

Quand une ligne cumule plusieurs types, l'un désigne le **diplôme** (BTS, Licence, CPGE…) et
l'autre une **thématique** (Études de santé, Métiers du sport, Travail social). C'est le
diplôme qui est retenu — c'est ainsi qu'un lycéen cherche (« BTS à Lyon », « prépa à
Toulouse »), et le `Nom long de la formation` le confirme à chaque fois :

| `Types de formation` (brut) | `Type principal` | `Nom long` — vérification |
|---|---|---|
| `Etudes de santé,Licence` | `Licence` | « Licence - Parcours d'Accès Spécifique Santé (PASS)… » |
| `Licence sélective,Licence` | `Licence` | « Double licence - Droit / Histoire de l'art… » |
| `Formations diplômantes du travail social,BTS - BTSA - BTSM` | `BTS - BTSA - BTSM` | « BTS - Services - Economie sociale familiale » |
| `I.A.E - Instituts d'administration des entreprises,CPGE` | `CPGE` | « CPGE - ENS Rennes D1 » |
| `Formations aux métiers du sport,Certificats de spécialisation et FCIL` | `Certificats de spécialisation et FCIL` | « Certificat de Spécialisation - Encadrement secteur sportif… » |

⚠️ **La règle n'est donc pas « garder Licence »** : sur `Travail social,BTS` le type
structurant est le BTS, sur `I.A.E,CPGE` c'est la CPGE. C'est le **type de diplôme** qui
prime, quel qu'il soit.

### ⚠️ Piège : toutes les virgules ne sont pas des séparateurs

Deux libellés contiennent une virgule **dans leur nom** :

- `Formations d'art, de design et du spectacle vivant` (458 lignes)
- `Formations d'architecture, du paysage et du patrimoine` (45 lignes)

Un `split(',')` naïf les casserait en faux types (« de design et du spectacle vivant »).
Ces deux libellés sont traités comme **atomiques** dans le calcul — un point à reproduire
si la règle était un jour recalculée côté base.

### Résultat

| Contrôle | Résultat |
|---|---|
| Valeurs distinctes | **22** (contre 68 en brut) |
| Lignes où `Type principal` ≠ brut | 2 718 |
| Valeurs vides | ✅ aucune |
| Virgule séparatrice résiduelle | ✅ aucune (hors les 2 libellés atomiques) |
| Colonne brute préservée | ✅ intacte |

Répartition : BTS/BTSA/BTSM 14 680 · Licence 3 929 · Certificats de spécialisation et FCIL
1 184 · CPGE 982 · BUT 957 · Écoles d'ingénieurs 707 · Formations professionnelles 649 ·
Études de santé 526 · Art & design 458 · Travail social 440 · Écoles de commerce 284 ·
DCG 196 · Licence sélective 166 · DEUST 160 · Métiers du sport 146 · autres < 110.

**Un cas limite assumé** : 2 lignes cumulent `Formations des écoles de commerce et de
management,Formations des écoles d'ingénieurs` (EFREI Paris, EPF Paris-Cachan / EXCELIA) —
de véritables doubles cursus commerce × ingénieur, où aucun type n'est plus « principal »
que l'autre. Elles sont classées en « écoles d'ingénieurs ». Aucun autre cas de ce genre.

### Ne pas jeter la colonne brute

Les types thématiques évincés (`Etudes de santé`, `Formations aux métiers du sport`,
`Formations diplômantes du travail social`, `Licence sélective`…) sont de **bons filtres
secondaires**. Exemple : les 723 licences PASS/LAS sont repérables uniquement via
`Etudes de santé` dans la colonne brute — `Type principal` les range, à juste titre, avec
les autres licences. Grouper sur `Type principal`, filtrer sur `Types de formation`.

---

## 3. ⚠️ Clé de jointure : avant de charger

**`code_formation` n'est pas unique.** Sur la session 2026, **1 301 couples
(UAI, `code_formation`) sont dupliqués** — cas des portails type PASS, où plusieurs
formations partagent le même code MESR.

**`Code interne Parcoursup de la formation`** est la clé fiable : vérifiée strictement unique sur
la session, et c'est ce code (`g_ta_cod`) qui joint le fichier d'admissions.

Recommandation : charger avec un contrôle de couverture sur la jointure, plutôt que de
supposer un appariement 1:1.

---

## 4. Trois pièges au chargement

**a. `Nom de l'établissement` contenait la ville et le département — déjà traité**
Exemple : `Lycée Condorcet (Saint-Priest - 69)` → `Lycée Condorcet`. **Le nettoyage est
fait dans la colonne elle-même** (voir §2bis) : elle est directement affichable, au format
déjà en production sur le site. La colonne `Nom etablissement (source)` conserve le libellé
brut pour traçabilité et n'est pas destinée à l'affichage.

**b. `Types de formation` est multi-valué — colonne `Type principal` ajoutée**
12,5 % des lignes (3 220) cumulent plusieurs types séparés par des virgules
(`Etudes de santé,Licence`, `Formations diplômantes du travail social,BTS - BTSA - BTSM`),
soit 68 combinaisons distinctes. Inutilisable tel quel pour grouper les formations par type
sur les pages `/v/` et `/d/`. Une colonne **`Type principal`** a donc été calculée : **22
valeurs** au lieu de 68, une seule par ligne. Voir §2ter pour la règle et les pièges.

---

## 5. Ce que ce fichier ne permet PAS

Aucun chiffre d'admission : ni candidats, ni admis, ni taux d'accès, ni % mentions TB,
ni profil des admis. Donc **pas de classement ni de sélectivité** avec ce fichier seul.

⚠️ **Décalage de session à anticiper** : la session 2026 de la cartographie décrit l'offre
ouverte aux candidatures, pas des résultats. Les chiffres d'admission 2026 ne seront
publiés qu'après la fin de la procédure. Les tableaux chiffrés s'appuieront
donc sur les **admissions 2025**, alors que l'inventaire des formations vient de 2026.

Conséquence pratique : la jointure inventaire 2026 ↔ admissions 2025 sera **partielle par
construction**. Les formations ouvertes pour la première fois en 2026 n'ont pas de chiffres
2025, et quelques formations fermées entre-temps existent côté admissions sans ligne
d'inventaire. Un affichage tolérant l'absence de chiffres sur une formation
(l'inventaire reste affichable seul), plutôt qu'une jointure stricte qui masquerait les
formations neuves.

---

## 6. Ce que ce fichier permet, dès maintenant

### Pages VILLE `/v/` — l'usage principal
Liste des formations post-bac accessibles via Parcoursup dans la ville, **groupées par
type** (BTS, CPGE, BUT, Licence, IFSI…), chaque ligne pointant vers son établissement.

### Pages DÉPARTEMENT `/d/` — le comptage
Nombre de formations post-bac disponibles dans le département, ventilé par type et par
commune. Bandeau de stats agrégées.

⚠️ Pas de **classement** à ce stade : classer suppose le taux d'accès, donc le fichier
d'admissions.

### Fiches Etablissements `/s/` — la liste des formations post-bac par établissement
Section « Après le bac : les formations du lycée {X} », alimentée par jointure sur l'UAI
avec la base lycées existante. Jointure directe et gratuite, l'UAI étant commun.

**Sur l'exhaustivité** — deux réserves à connaître :

1. **Exhaustif sur le périmètre Parcoursup uniquement.** Toute formation recrutant via
   la plateforme y figure. Mais certaines formations post-bac de lycées recrutent **hors
   Parcoursup** (BTS en apprentissage via CFA, certaines FCIL, alternance à recrutement
   direct) : elles sont absentes. « Exhaustif Parcoursup » ≠ « exhaustif post-bac ».
2. **Seuls les lycées ayant du post-bac figurent au fichier.** Un lycée général sans BTS
   ni CPGE en est absent — ce n'est pas une donnée manquante, c'est l'information
   « pas de post-bac » — un `has_postbac = false` plutôt qu'un trou à combler.

Ordre de grandeur : ~2 610 établissements portant « lycée » dans leur libellé sur la
session 2026, dont ~1 969 publics, et 414 UAI hébergeant au moins une CPGE. Ces chiffres
sont estimés **par le libellé du nom**, faute de colonne distinguant lycée / CFA / école.
Le décompte fiable viendrait d'une jointure sur l'UAI avec la base lycées — elle donnerait
aussi le taux de couverture réel.