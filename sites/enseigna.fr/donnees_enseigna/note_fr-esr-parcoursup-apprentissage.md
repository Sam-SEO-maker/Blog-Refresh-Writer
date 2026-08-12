# Note explicative — Parcoursup apprentissage

---

Ce fichier couvre les formations post-bac **en apprentissage** proposées sur Parcoursup.
Elles sont absentes de `fr_esr_admissions_parcoursup.csv`. Les deux fichiers sont complémentaires, sans aucun recouvrement.

**Source** : data.enseignementsup-recherche.gouv.fr — jeu `fr-esr-parcoursup-apprentissage`.

---

## 1. Format et volumétrie

| | |
|---|---|
| Séparateur | `;` (point-virgule) |
| Encodage | UTF-8 **avec BOM** |
| Colonnes | 16 (filtrées depuis 44) |
| Lignes | 11 536 |
| Session | 2025 |
| Établissements distincts | 3 896 |
| Communes / départements | 1 385 / 102 |

**Une ligne = une formation dans un établissement.**

---

## 2. ⚠️ À lire avant chargement

Ce fichier ne contient **ni taux d'accès, ni admis, ni mentions au bac**. En apprentissage,
l'admission dépend de la signature d'un contrat avec un employeur, pas d'un classement de
dossiers : la notion de sélectivité n'a pas le même sens qu'en voie scolaire.

Les colonnes de propositions d'admission de la source ont d'ailleurs été supprimées :
**50,9 % d'entre elles étaient à zéro** (médiane 0). Affichées comme un taux d'admission,
elles auraient été trompeuses.

**Conséquence pour l'affichage** : **aucune formation de ce fichier ne peut avoir de
« Taux d'accès » ni d'« Admis »** — les 11 536 lignes, toutes filières confondues. Ces deux
colonnes viennent de `fr_esr_admissions_parcoursup.csv`, qui ne couvre que la voie
scolaire. Dans un tableau qui mêle les deux voies, elles resteront donc vides sur toutes
les lignes en apprentissage : c'est une absence normale, pas une donnée manquante à aller
chercher. Ces formations ne peuvent pas non plus entrer dans un classement par taux d'accès.

⚠️ **Le critère est la voie, pas le diplôme.** Un même type de diplôme est chiffré ou non
selon le fichier dont il provient — un BTS en voie scolaire a un taux d'accès (5 351 lignes
dans le fichier des admissions), le même BTS en apprentissage n'en a pas (9 547 lignes
ici). Il ne faut donc pas conditionner l'affichage sur le type de formation, mais sur le
fichier d'origine de la ligne.

Ce que le fichier permet : **l'inventaire** (qui propose quoi, et où) et le **volume**
(places, candidats).

---

## 3. Les 16 colonnes

### Jointure (2)

| Colonne | Usage |
|---|---|
| `Numéro d'identification de la formation dans Parcoursup` | **Clé unique** (11 536/11 536). Joint `Code interne Parcoursup de la formation` de la cartographie |
| `Code UAI de l'établissement` | Pivot MESR — joint la base lycées. 1 446 des 3 896 UAI portent « Lycée » dans leur libellé |

⚠️ La clé ne porte **pas** le même nom que dans le fichier des admissions
(`cod_aff_form`), alors qu'elle joint la même colonne de la cartographie.

### Établissement et géographie (9)

`Session` · `Établissement` · `Code départemental de l'établissement` ·
`Département de l'établissement` · `Région de l'établissement` ·
`Académie de l'établissement` · `Commune de l'établissement` ·
`Coordonnées GPS de la formation` · `Statut de l'établissement de la filière de formation`

Toutes remplies à 100 %, sauf les coordonnées GPS (99,0 %).

### Formation (3)

| Colonne | Contenu |
|---|---|
| `Filière de formation très agrégée` | **8 valeurs** — pour grouper (voir §4) |
| `Filière de formation` | 388 valeurs — libellé lisible, à afficher |
| `Filière de formation détaillée bis` | 344 valeurs — la spécialité seule |

### Volume (2)

| Colonne | Repère |
|---|---|
| `Capacité de l'établissement par formation` | Places — médiane 16, total 264 386 |
| `Effectif total des candidats pour la formation` | Candidats — médiane 72, max 7 911 |

Ce sont les **seules données chiffrées fiables** du fichier. Elles permettent d'afficher
« X places, Y candidats », mais **pas** de calculer un taux d'accès : sans le nombre
d'admis, le rapport candidats/places ne mesure que la pression, pas la sélectivité.

---

## 4. La colonne de regroupement a été nettoyée

`Filière de formation très agrégée` portait un préfixe numérique technique dans la source
(`1_BTS`, `5_Formation professionnelle`). Il a été **retiré** : les valeurs sont désormais
directement affichables.

| Valeur | Lignes |
|---|---|
| BTS | 9 547 |
| Formation professionnelle | 661 |
| Certificat de spécialisation (dont agricole) | 645 |
| EFTS | 207 |
| BUT | 141 |
| Autres | 129 |
| DCG | 104 |
| DEUST | 102 |

**C'est cette colonne qu'il faut utiliser pour grouper**, pas le préfixe de
`Filière de formation`. Ce dernier semble équivalent, mais il se trompe sur trois cas :

- **EFTS** (207 lignes) éclaterait en une dizaine de libellés distincts
  (`D.E Educateur Spécialisé`, `D.E Assistant de Service Social`…), dispersant les
  formations du travail social sur les pages ville.
- **Autres** (129 lignes) mélange BPJEPS, BTS et DSP — **12 lignes commencent par « BTS »
  sans être classées en BTS**, elles seraient donc comptées à tort avec les BTS.
- **Certificat de spécialisation** se scinderait en version agricole et non agricole.

---

## 5. Jointures — mesures réelles

| Test | Résultat |
|---|---|
| Vers la cartographie (`Code interne Parcoursup de la formation`) | **82,6 %** |
| Chevauchement avec `fr_esr_admissions_parcoursup.csv` | **0** — aucun doublon possible |
| Cartographie couverte par les deux fichiers de chiffres | **89,3 %** |

Le chevauchement nul confirme que les deux fichiers sont strictement complémentaires :
une formation est soit en voie scolaire, soit en apprentissage, jamais les deux.

Les ~17 % non appariés s'expliquent par le décalage de session — la cartographie décrit
l'offre **2026**, ce fichier donne les résultats **2025**. Un affichage tolérant l'absence de
chiffres serait préférable à une jointure stricte, qui masquerait les formations ouvertes
pour la première fois en 2026.

---

## 6. Une caractéristique à connaître : 45 % de privé hors contrat

| Statut | Lignes | Part |
|---|---|---|
| Privé hors contrat | 5 229 | 45 % |
| Public | 3 268 | 28 % |
| Privé sous contrat d'association | 2 741 | 24 % |
| Privé enseignement supérieur | 298 | 3 % |

La répartition est très différente de celle de la voie scolaire. La colonne
`Statut de l'établissement` est conservée pour cette raison : c'est une information utile
au lecteur, et sans doute à afficher explicitement sur les formations en apprentissage.
