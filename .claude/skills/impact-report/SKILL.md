---
name: impact-report
description: >-
  Rapport mensuel d'impact des refreshs (tous sites) : mesurer et raconter ce
  que le travail éditorial du mois a produit, chaque article comparé à
  lui-même un an plus tôt, à date fixe, plutôt qu'au mois calendaire. Définit
  les deux étages du livrable (verdict, les plus fortes progressions et
  baisses détaillées requête par requête avec leur diagnostic, le reste du lot
  en tableau avec ses cas notables commentés), le groupe de contrôle qui
  déduit la dérive de marché résiduelle une fois la saisonnalité éliminée par
  construction, et la façon d'écrire l'accroche sans surpromettre. S'appuie
  sur `python3 content_writer.py audit impact`. À invoquer le 10 du mois
  suivant, jamais le 1er : avant cette date les articles republiés en fin de
  mois n'ont pas le recul minimal côté « après » et sortent silencieusement du
  rapport.
disable-model-invocation: false
---

# Rapport d'impact mensuel des refreshs

Une skill de **méthode et de restitution**. Le calcul est déterministe
(`audit impact`) ; ce qui se joue ici est le choix de la mesure, le périmètre
étudié et la façon de l'énoncer à quelqu'un qui n'ouvrira pas le JSON.

Le lecteur est un décideur, pas un analyste : il veut savoir si le travail du
mois a produit quelque chose, et si le chiffre tient. Tout le reste est du
support de preuve.

---

## 1. La mesure : chaque article contre lui-même, un an plus tôt

**L'unité de mesure est l'article, pas le mois.**

Pour chaque article republié : les N jours qui **suivent** sa republication
contre les N jours qui suivent la **même date un an plus tôt**
(`pushed - 365 j`), à durée strictement égale. Le jour de publication est
exclu de la fenêtre « après » (il porte les deux versions) ; son homologue à
J-365 est exclu par symétrie, pas parce qu'un refresh y aurait eu lieu.

Concrètement, pour un article republié le 2026-08-12 : « après » couvre les N
jours qui suivent le 2026-08-12 ; « avant » couvre les N jours qui suivent le
2025-08-12, la même date un an plus tôt — et non plus les N jours qui
précèdent le refresh.

**Pourquoi l'année-sur-année plutôt que le avant/après immédiat qu'utilisait
ce rapport auparavant.** L'ancienne méthode comparait chaque article aux
quelques semaines qui précédaient directement son refresh. Elle isolait bien
le travail (contrairement au mois calendaire, voir plus bas), mais laissait la
saisonnalité à la charge du groupe de contrôle : un article refreshé juste
avant la rentrée scolaire voyait sa fenêtre « avant » tomber en plein creux
d'été, et il fallait déduire cet effet après coup plutôt que l'éviter par
construction. Comparer les mêmes dates calendaires à un an d'écart élimine
cette saisonnalité mécaniquement : les deux fenêtres tombent dans le même
mois, avec la même proximité aux vacances, aux examens, aux mêmes pics de
recherche. Le groupe de contrôle n'a donc plus besoin d'absorber un effet de
saison ; il capte ce qu'il reste une fois la saison neutralisée, à savoir une
dérive de marché résiduelle (voir plus bas).

Pourquoi pas le mois calendaire, qui resterait plus simple :

- Un onglet contient des articles traités et des articles qui ne le sont pas.
  Le résultat décrit l'onglet, pas le travail.
- Un mois calendaire n'ancre pas la comparaison sur la date de republication
  de chaque article : il traite pareil un article refreshé le 2 et un autre
  refreshé le 28, alors que leur recul disponible diffère du tout au tout.

> C'est la distinction entre ce rapport et `/tab-perf` (`audit gsc-tab`) : les
> deux comparent désormais une période à son année précédente, mais
> `/tab-perf` le fait sur **un périmètre entier** (l'onglet, articles
> retravaillés ou non) **sur un mois calendaire**, quand celui-ci le fait
> **article par article**, chacun ancré sur SA date de republication, sur **le
> lot effectivement retravaillé**. Les deux peuvent conclure en sens opposés
> sans qu'aucun ne soit faux — ils ne portent pas sur le même objet. Quand les
> deux lectures circulent, **dire laquelle on cite**.

### Le recul (`--maturity`, 30 j par défaut)

Le recul ne joue plus le même rôle des deux côtés de la fenêtre. Côté
**« avant »**, il est quasiment toujours disponible : GSC conserve environ 16
mois d'historique, largement assez pour couvrir `pushed - 365 j` jusqu'à
`pushed - 365 j + N`. Ce n'est donc plus lui qui limite N.

Côté **« après »**, en revanche, le recul continue de dépendre de la date de
republication dans le mois : un article republié le 2 a près de 30 jours de
recul au moment du rapport, un article republié le 28 n'en a que quelques-uns.
`--maturity` (30 j par défaut) plafonne ce recul pour garder les rapports
comparables d'un mois sur l'autre ; en deçà de `MIN_MATURITY` (7 j), l'article
est écarté faute de recul suffisant pour distinguer un signal du bruit de
recrawl.

La courbe de maturation mesurée sur la cohorte du 6 août 2026 (39 articles,
sous l'ancienne méthode avant/après) illustre pourquoi une fenêtre courte
sous-estime l'effet d'un refresh, un phénomène qui reste vrai côté « après »
avec la méthode YoY :

| Fenêtre | Impressions/jour | Régime |
|---|---|---|
| Avant refresh | 246 | ×1,00 |
| J+1 → J+7 | 365 | ×1,48 |
| J+8 → J+14 | 548 | ×2,23 |
| J+15 → J+21 | 653 | ×2,65 |
| J+22 → J+28 | 900 | ×3,66 |
| J+29 → J+34 | 987 | ×4,01 |

Deux enseignements qui restent valides :

1. **Google repasse dès la première semaine.** Le signal est déjà à ×1,5 à
   J+7. Il n'y a pas de période aveugle à attendre.
2. **La courbe n'a pas atteint son palier à J+30.** Une mesure à 30 jours
   **sous-estime** l'effet côté « après » — elle en capte la pente. C'est un
   argument en faveur du travail, pas contre lui, et une raison de citer la
   lecture par vague plutôt que le total quand les reculs sont très inégaux.

Bornes retenues :

- **Moins de 7 jours** de recul « après » : article écarté. L'effet existe
  mais l'échantillon de jours est trop court pour distinguer le signal du
  bruit de recrawl.
- **Au-delà de 30 jours** : plafond de comparabilité entre rapports, pas une
  contrainte de disponibilité des données (la fenêtre « avant » n'a plus de
  raison de mordre sur un refresh antérieur, elle est ancrée un an plus tôt).
- La fenêtre se ferme **3 jours avant aujourd'hui** côté « après » : les tout
  derniers jours GSC sont sous-comptés, les inclure ferait passer une donnée
  incomplète pour une baisse de trafic.

### Quand lancer le rapport

**Pas le 1er du mois.** Un rapport lancé le 1er septembre pour août ne peut pas
mesurer les articles republiés fin août : ils n'ont pas les 7 jours de recul
minimum, et la latence GSC retire encore 3 jours. Sur le lot réel d'août 2026,
un lancement au 1er septembre ne couvrait que **44 des 78 articles**.

Le biais est le pire possible : il est **systématique** (ce sont toujours les
derniers publiés du mois) et **invisible** dans un total — le rapport
annoncerait « 44 articles republiés » sans que rien ne signale qu'il en manque
34.

> **Date de disponibilité = fin de période + 10 jours** (7 j de recul minimum
> + 3 j de latence GSC). Pour un mois plein, le **10 du mois suivant**.

La commande calcule cette date et **refuse de produire** un rapport dont la
couverture tombe sous 90 %, en affichant combien d'articles manquent et à
partir de quand le lot sera complet. `--partial` lève le refus quand une
lecture anticipée est vraiment nécessaire ; le rapport porte alors un bandeau
qui dit ce qu'il ne couvre pas.

**Ne pas contourner en réduisant `--maturity`.** Passer à 7 jours ferait bien
entrer les articles récents, mais mesurerait tout le mois sur une fenêtre
« après » plus courte et donc plus proche de la pente que du palier (voir la
courbe ci-dessus) : la couverture serait sauvée, le résultat amoindri, et les
mois ne seraient plus comparables entre eux.

### Reculs inégaux dans un même rapport

Même à couverture complète, les articles n'ont pas tous le même recul côté
« après » : au 10 septembre, la vague du 6 août a 30 jours et celle du 25 en a
13. Comme l'effet grandit avec le temps d'observation, **le total agrège des
stades de maturation différents côté « après »** et sous-estime les vagues
récentes. (Côté « avant », en revanche, le recul est fixe : environ un an,
quasiment toujours disponible côté GSC — ce n'est plus une source d'inégalité
entre articles.)

Dans un rapport aux reculs très inégaux, **citer la lecture par vague plutôt
que le total** : c'est la seule qui compare des articles au même stade côté
« après ». Le bloc « Recul disponible après refresh » (page 1) donne la
distribution de ce recul en un coup d'œil, sans reconstituer un gradient par
tranche — l'ancien gradient de recul comparait des stades de maturation côté
« avant », qui n'existent plus depuis le passage au YoY (voir plus bas,
« Étage 1 »).

> **Pour mesurer le palier plutôt que la pente**, relancer le mois M à M+2 avec
> `--maturity 60`. Le chiffre publié le mois même reste la lecture à 30 jours,
> comparable d'un mois sur l'autre ; la relecture tardive dit où l'effet s'est
> stabilisé.

### La source des dates de republication

C'est la question la plus piégeuse du dispositif, et **celle qui a produit le
plus gros faux du rapport** (voir l'encadré ci-dessous).

**Quand l'onglet tient une colonne « Date de refresh », c'est elle qui fait foi,
et `--tab` est le mode par défaut.** Elle est la seule source qui date un *acte
éditorial* : elle est remplie par la personne qui a fait le refresh. Les trois
autres datent un événement *technique* — une publication, ou pire, n'importe
quelle écriture sur le post.

| Mode | Source | Ce qu'elle date |
|---|---|---|
| **`--tab <onglet>`** | colonne `col_date` de l'onglet | Le **refresh éditorial**, saisi à la main. Périmètre = l'onglet |
| **`--source notion`** | colonne « Planing de refresh » de la base Notion | Le **refresh éditorial**, saisi à la main. Périmètre = les lignes que la base déclare en ligne |
| `--source notion`, complément | `lastmod` du sitemap des articles | La dernière écriture sur la page, **bornée aux URLs que la base suit** |
| défaut, rang 1 | `wp_backups/_publications.jsonl` | Chaque publication réussie de `push_to_wp` |
| défaut, rang 2 | `wp_backups/{id}_before.json` (mtime) | La *première* publication d'un post par `push_to_wp` |
| défaut, rang 3 | WordPress `modified`, restreint aux articles que la Sheet dit publiés | La dernière modification quelconque — **repli dangereux**, voir encadré |

> ### Le faux d'août 2026 : 166 articles annoncés, 86 réels
>
> Le rapport comptait **166 articles** là où l'onglet Medium Potential n'en
> déclarait que **86**. Les 80 de trop venaient du rang 3.
>
> Trois causes se sont combinées :
>
> 1. `published_statuses` n'était pas configuré pour le site, donc le défaut du
>    code acceptait **« Prêt pour relecture »** — un statut qui signifie
>    « rédigé », pas « mis en ligne en août ». 89 des 90 articles récupérés par
>    le rang 3 portaient ce statut.
> 2. `modified` est écrasé par **toute** retouche ultérieure. Des articles
>    refreshés en juin, simplement réédités depuis, se sont datés d'août.
> 3. Le périmètre n'était borné par aucun onglet : des articles d'autres listes
>    de travail entraient dans un rapport censé mesurer un lot précis.
>
> Résultat : `clovis-premier-dynastie-germaine`, **refreshé en juin** et absent
> de l'onglet suivi, ressortait comme **la plus forte progression du mois**
> (+8 138 impressions). Vérification faite sur un échantillon de 10 articles
> datés par `modified`, **3 servaient en ligne une version rédigée en juin**.
>
> La leçon n'est pas « `modified` est mauvais » — c'était déjà écrit — mais
> qu'un repli de dernier rang **ne doit jamais élargir un périmètre**. Il comble
> un trou dans un lot connu ; il ne définit pas le lot.

Écartée : `outputs/<site>/html/` (date la *rédaction*, pas la mise en ligne, et
ce dossier est voué à être purgé).

**En mode `--tab`, le groupe de contrôle exclut aussi les refreshs du mois hors
périmètre.** Ils ont bougé, leur progression n'est pas de la dérive de marché
naturelle du site : les laisser dans la référence gonflerait le rythme
« naturel » du site et sous-estimerait l'écart net du lot.

**Le trou qui a motivé le rang 3.** `push_to_wp` ne trace que ses propres
publications. Quand `cw push` échoue et que la republication se fait à la main
depuis WordPress — après relecture, cas courant — l'article part en ligne sans
laisser la moindre trace locale. Mesuré sur superprof.fr-ressources en
septembre 2026 : **58 articles republiés manuellement**, absents du rapport
d'août alors qu'ils étaient bien en ligne. Le rapport annonçait « couverture
100 % » parce qu'il comptait les articles *tracés*, pas les articles
*republiés* : 43 % du travail du mois manquait sans que rien ne le signale.

**Pourquoi `modified` est acceptable en rang 3 et proscrit ailleurs.** La règle
générale tient toujours (voir le piège ci-dessous) : `modified` est écrasé par
toute retouche ultérieure, donc c'est une mauvaise source *quand une meilleure
existe*. Pour ces articles-là il n'en existe aucune autre — le choix n'est pas
entre `modified` et mieux, mais entre `modified` et ne pas mesurer la moitié du
mois. La substitution a été **validée empiriquement** contre les 20 lignes qui
portaient aussi une date saisie à la main : 10 dates identiques, 10 à +1 jour
exactement, aucun écart erratique.

Deux garde-fous encadrent ce repli :

- il ne s'applique **qu'aux articles que la Sheet déclare publiés** (statut
  éditorial), jamais à l'ensemble du site ;
- chaque article porte un champ `date_source` (`wp_backups` ou `wp_modified`),
  pour que le rapport puisse distinguer les deux plutôt que de les présenter
  comme équivalentes.

Les dates sont mises en cache (`wp_backups/_modified_cache.json`) : ~250 appels
WordPress, plusieurs minutes et autant d'occasions de se faire refuser par le
WAF, pour des valeurs qui ne bougent plus une fois l'article publié.

> **Remplir la Sheet** : `python3 -m scripts.sheets.backfill_refresh_dates
> --site <slug>` montre ce qu'il écrirait, `--apply` écrit. Il ne remplit que
> les cellules **vides** — une saisie humaine est une information, pas un
> doublon à corriger. Les colonnes diffèrent d'un onglet à l'autre
> (« Date de refresh », « Date de publication ») et certains onglets n'en ont
> pas.


**Le piège de `modified`.** C'est la source qui semble la plus solide (elle
vient de WordPress, aucune saisie humaine) et c'est celle qui donne le
résultat le plus faux. Elle est écrasée par toute retouche ultérieure :
correction manuelle, passe de QC, plugin. Mesuré sur août 2026, **69 des 78
articles** avaient un `modified` postérieur à leur refresh — s'en servir
comme source les aurait presque tous datés de septembre et vidé le rapport.

`modified` garde pourtant une utilité, mais inversée : en **contrôle de
cohérence**. Un article dont le `modified` tombe après le refresh et dans la
fenêtre de mesure a subi une seconde intervention ; son évolution ne s'impute
plus au seul refresh. Le rapport les liste (36 articles en août 2026). Ne pas
les citer comme preuve isolée.

**Limite connue de `wp_backups`** : `push_to_wp` n'écrit le fichier que s'il
est absent, donc le mtime date la **première** publication. Un article
refreshé deux fois reste daté de sa passe initiale. Le contrôle `modified` ne
corrige pas cette limite mais la rend visible.

> **Conséquence opérationnelle : ne pas purger `wp_backups/`.** C'est la seule
> trace durable de l'historique de publication. `outputs/html/` peut être
> purgé sans dommage pour ce rapport ; `wp_backups/` non, ou alors archivé
> ailleurs d'abord.

### Le groupe de contrôle

Le reste du site (total GSC **moins** les articles traités), comparé lui aussi
à J-365 sur *exactement* les mêmes dates que la vague mesurée : ses propres
J+1→J+N de cette année contre ses J+1→J+N de l'année dernière, à l'identique
de ce que fait chaque article traité.

**Son rôle a changé avec le passage au YoY.** Sous l'ancienne méthode
avant/après, le contrôle portait presque tout le travail de déduction de la
saisonnalité : sans lui, un mois de rentrée scolaire se lisait comme un succès
éditorial. La fenêtre année-sur-année élimine déjà cette saisonnalité par
construction (les deux côtés tombent dans le même mois, à un an d'écart) ; le
contrôle sert désormais surtout à capter ce qui *reste* une fois la saison
neutralisée : une **dérive de marché résiduelle**, structurelle et non
saisonnière — le reste du site progresse ou régresse d'une année sur l'autre
pour des raisons qui ne tiennent pas au calendrier (formations supprimées,
intérêt qui se déplace durablement, changements d'algorithme). Le concept
reste donc utile, pas décoratif : sans lui, une dérive de marché généralisée se
lirait comme un effet du travail éditorial dans un sens ou dans l'autre.

Retirer les articles traités du contrôle n'est pas cosmétique : les laisser
dedans mettrait la mesure des deux côtés de la comparaison et écraserait
l'écart.

**Écart net par vague** = variation de la vague − variation de son contrôle.

**Au niveau du lot, ne pas moyenner les contrôles** : chaque vague a sa propre
paire de dates (l'une ancrée sur sa date de republication, l'autre un an plus
tôt), donc sa propre dérive de marché, et appliquer à tout le mois le contrôle
de la vague dominante prêterait aux autres un contexte qu'elles n'ont pas
connu. Le rapport calcule un **contrefactuel pondéré** : pour chaque vague, ce
que ses articles auraient fait au rythme du reste du site, puis la somme.

D'où la formulation en volumes, la plus parlante : « ces articles auraient fait
15 008 impressions, ils en ont fait 26 712, soit +78,0 % au-dessus de
l'attendu ». C'est ce chiffre-là qu'on cite, pas le brut qui ne retranche rien.

---

## 2. Le spectre à étudier

**Le rapport a deux lecteurs, donc deux étages.** Les confondre est l'erreur qui
a produit la première version : trop de prose méthodologique pour un directeur,
trop peu de granularité pour piloter le travail (27 articles montrés sur 76,
aucun mot-clé).

### Étage 1 — le verdict (pages 1-2)

Un directeur arbitre trois choses : continuer, changer d'échelle, changer de
direction. Rien d'autre n'a sa place ici.

| # | Bloc | Répond à |
|---|---|---|
| 1 | **Verdict** : écart net d'impressions, en gros | « Ça a marché ou pas ? » |
| 2 | **Tuiles** : impressions nettes, clics nets, articles traités | « De combien ? » |
| 3 | **Fiabilité** : camembert progression / stable / recul | « Puis-je y croire ? » |
| 4 | **Recul disponible après refresh** : distribution des jours mesurés côté « après » | « Le lot est-il homogène ? » |
| 5 | **Mois mesuré** : écart net du mois demandé, seul | « Combien ce mois-ci ? » |
| 6 | **Réserves** : couverture, reculs inégaux, retouches | « Le chiffre est-il propre ? » |
| 7 | **Situer ce résultat** : pourquoi il diffère d'un suivi d'onglet | « Et par rapport à un suivi de périmètre ? » |
| 8 | **Méthode**, repliée | « D'où sort ce chiffre ? » |

**Trois tuiles, pas quatre : pas d'« effet médian ».** Le multiplicateur médian
d'impressions a été retiré. Il se lisait mal — « impressions de l'article
médian » n'apprend rien à qui ne connaît pas la formule — et surtout il **ne
déduit pas la dérive de marché**, contrairement aux deux tuiles nettes posées
juste à côté : le lecteur comparait un chiffre brut à des chiffres nets sur la
même ligne. Le calcul reste dans le JSON et la sortie CLI, où le praticien sait
ce qu'il lit.

**Le gradient de recul par tranche de maturité a disparu avec le passage au
YoY.** Il comparait des articles à des stades de maturation différents côté
« avant » (les jours précédant la republication) : c'était le bloc qui
expliquait pourquoi certaines baisses n'étaient que des mesures trop jeunes.
Depuis que « avant » est ancré à J-365 avec le même recul que « après », ce
recul est quasiment toujours disponible côté GSC (16 mois d'historique) — il
n'explique plus rien, et un article en recul l'est vraiment, pas parce que sa
mesure est jeune.

Ce qui reste vrai : le recul côté « après » varie encore selon la date de
republication dans le mois (7 à ~30 jours). Le bloc « Recul disponible après
refresh » en donne la distribution simple (min, max, médiane), pour situer
d'un coup d'œil si le lot est homogène ou étalé — sans reconstituer un gradient
qui n'a plus rien à expliquer.

**« Trajectoire mensuelle » est devenue « Mois mesuré ».** L'ancienne section
affichait une barre par mois, y compris les mois précédents : dans un rapport
qui ne mesure qu'un mois donné, une barre de comparaison avec le mois
précédent porte à confusion (chaque mois compare sa propre vague à sa propre
année précédente, pas l'un à l'autre). Le bloc n'affiche donc plus que l'écart
net du mois courant, sans comparaison visuelle. L'historique mois par mois
continue d'être écrit dans le JSON (`trajectory`) pour qui veut une lecture
comparative dans le temps.

**« Situer ce résultat » désamorce la contradiction avant qu'elle ne circule.**
Quand un suivi d'onglet (`/tab-perf`) tourne en parallèle, ses chiffres peuvent
être de signe opposé. Les deux lectures sont désormais l'une et l'autre
année-sur-année, mais elles ne portent pas sur le même objet : celle-ci ancre
la comparaison sur la date de republication de CHAQUE article et ne porte que
sur le lot retravaillé, `/tab-perf` ancre sur le mois calendaire et porte sur
tout un périmètre (articles retravaillés ou non). Un article republié en fin
de mois pèse tout son poids ici alors qu'il compte à peine dans une lecture
calendaire ; l'onglet mélange des articles retravaillés avec d'autres qui ne
le sont pas. **C'est le point d'ancrage et le périmètre qui changent, pas le
principe de la comparaison.** Le dire dans le rapport évite d'avoir à le
réexpliquer à chaque diffusion.

**Le verdict porte le chiffre net, jamais le brut.** Le brut ne retranche pas
la dérive de marché résiduelle et se fait démonter dès qu'on demande « et sans
ça ? ». Le net est celui qui tient.

**Le camembert reste sous 6 secteurs** — trois ici. Au-delà, un secteur cesse
d'être lisible et il faut une table. C'est pourquoi les 12 catégories
éditoriales n'y sont pas : elles violeraient la règle, et elles n'intéressent
pas ce lecteur.

**Seuil de ±5 % sur la répartition.** En deçà, la variation n'est pas
distinguable du bruit GSC. Compter un article à +2 % comme une victoire faisait
passer août 2026 de 59 à 64 gagnants : le premier chiffre se défend, pas le
second.

### Étage 2 — ce sur quoi on agit (~25 pages)

C'est l'outil de travail, celui qui dit **sur quoi** un article a bougé.

| Bloc | Contenu |
|---|---|
| **Ont grimpé** | les 20 plus fortes progressions, en fiche : métriques, diagnostic, les 5 requêtes qui pèsent le plus (avant ou après) avec leur statut, et une lecture rédigée |
| **N'ont pas fonctionné** | les 20 plus fortes baisses, même format, triées par écart net croissant |
| **Le reste du lot** | même fiche pour chaque article restant, du plus fort gain au plus fort recul ; suivi de quelques paragraphes sur ses cas les plus notables |
| **Annexe** (`--pdf-annex`, toujours dans le HTML) | l'index tabulaire du lot : impressions, Δ net, clics, position, KW +/−, diagnostic, requête principale |

**Les extrêmes d'abord, mais chaque article a sa fiche.** Le reste du lot
tenait en une ligne par article avec une seule « requête principale » : la
direction a demandé les 5 requêtes de chaque URL, et un tableau qui les
tronquait ne répondait pas. Les 20 plus fortes progressions et les 20 plus
fortes baisses restent en tête parce qu'elles ouvrent sur une décision ; le
ventre mou suit avec la même fiche, et ses cas qui contredisent l'intuition
sont commentés en plus (voir plus bas).

**Une seule table de requêtes par fiche, jamais tronquée.** Les 5 requêtes
qui pèsent le plus, classées sur `max(avant, après)` et non sur le seul
« après » : une requête perdue à 414 impressions l'an dernier pèse plus dans
la lecture d'un recul qu'une requête gagnée à 2 impressions, et une requête
maintenue qui s'effondre (368 → 5) n'entrerait jamais dans un classement sur
« après ». Chaque ligne porte son statut (gagnée / maintenue / perdue), ce
qui conserve les trois familles sans les mettre côte à côte. Le JSON garde
les trois familles (`queries.held/gained/lost`) et la liste fusionnée
(`queries.top`).

**La lecture rédigée, sous la table.** Deux à quatre phrases générées depuis
les chiffres de la fiche : d'où vient le volume (requêtes nouvelles ou
requêtes déjà captées, avec les deux exemples qui pèsent le plus), ce que fait
le classement sur les requêtes historiques, ce qui a disparu (« à surveiller »
si la requête perdue faisait 10 impressions ou plus, « marginale » sinon).
Deux garde-fous : **GSC n'attribue pas toutes les impressions d'une page à une
requête** (les requêtes rares sont anonymisées ; sur `theorie-calculs-travail`
la page fait 309 impressions et ses 5 requêtes visibles en totalisent 6), donc
quand la borne haute du volume attribuable passe sous 50 % du volume de la
page, la lecture commence par le dire et parle ensuite de « la part visible » ;
et **une position ne se cite que sur du volume** (au moins 3 impressions de
chaque côté, 5 d'un côté), sans quoi « gagne 58 places » sur une requête à 2
impressions passerait pour un résultat.

**Les baisses se trient par écart net, jamais par volume perdu.** Un article qui
perd 400 impressions sur 5 000 va bien ; un qui en perd 120 sur 157 est en
difficulté. C'est le second qu'il faut regarder.

**Le diagnostic par URL.** Pas une cause — la mesure n'établit aucune causalité —
mais la description de *ce qui a bougé*, dérivée des trois familles de requêtes.
Les libellés sont volontairement auto-explicatifs (une relecture a signalé que
« Couverture élargie » et « Audience resserrée » ne l'étaient pas) :

| Étiquette | Règle | Ce qu'elle dit |
|---|---|---|
| **Nouveaux mots-clés** | gagnées > maintenues | l'article ressort sur de nouvelles requêtes |
| **Classement amélioré** | les maintenues remontent | même périmètre, meilleur rang |
| **Perte de requêtes** | perdues > 2 × gagnées, et > 5 | le seul vrai signal d'alerte |
| **Recul sur mêmes requêtes** | baisse sans perte massive | volume en repli, périmètre stable |

**Un article qui baisse ne porte jamais une étiquette positive.** Le test
`gagnées > maintenues` est vrai trivialement quand l'article tient peu de
requêtes : `forces-et-effets` (+1 gagnée, 0 maintenue, −28 % net) ressortait
« nouveaux mots-clés » alors qu'il recule.

> **Le diagnostic « recul insuffisant » a disparu avec le passage au YoY.**
> Il reposait sur `maturity`, qui bornait alors le recul côté « avant » (les
> jours précédant la republication) : sous 15 jours, une requête « perdue »
> était souvent une requête pas encore reprise. Depuis que « avant » est
> ancré à J-365 avec le même recul que « après », ce recul est presque
> toujours disponible côté GSC ; il ne sert plus de réserve sur la mesure. Le
> recul qui varie encore (celui côté « après », voir Étage 1) est déjà
> reflété dans le champ `maturity` de chaque article sans qu'un diagnostic
> séparé soit nécessaire : un article à 7 jours de recul produit des volumes
> plus petits, pas un statut à part.

**Le reste du lot n'est plus une pure liste sèche.** Trois à six cas sont
sélectionnés automatiquement pour un court paragraphe explicatif — en
priorité ceux où le signe du delta d'impressions et celui du delta de
position divergent (le trafic monte alors que la position recule, ou
l'inverse), sinon les plus gros mouvements bruts du ventre mou. Le paragraphe
donne les vrais chiffres de l'article (jamais inventés) puis une hypothèse
SEO/GEO, présentée explicitement comme une hypothèse et non comme une cause
établie (voir « Ce qui se joue dans la troisième phrase », section 3) :
cannibalisation par une autre page du site, dilution du signal de pertinence
si le contenu a été élargi, concurrence accrue sur le mot-clé, ou baisse de
la demande. Sur `theorie-calculs-travail` (le cas qui a motivé cette
section) : le trafic passe de 18 à 309 impressions et de 0 à 6 clics, mais la
position recule de 7 à 14 — un refresh qui capte plus de volume sans
améliorer, voire en dégradant, son classement moyen.

**Une progression depuis zéro s'affiche en volume, pas en pourcentage.** Une page
invisible avant refresh n'a pas de taux de progression. Afficher « n/a » effaçait
de vraies réussites : sur août 2026, quatre articles créaient 968 impressions et
ressortaient tous comme non mesurables. Le rapport affiche « nouveau » et le
volume créé.

**Le déplacement sémantique, en trois familles.** Un refresh réussi se lit de
deux façons très différentes, et les confondre fait passer un élargissement de
couverture pour une remontée de classement :

- **maintenues** : présentes des deux côtés, avec le delta de position — le
  mouvement de classement ;
- **gagnées** : absentes avant, présentes après — l'élargissement de couverture ;
- **perdues** : l'inverse, seul signal d'alerte éditorial du lot.

> Exemple d'août 2026 : `polariser-lumiere-physique` fait +329 % d'impressions
> alors que sa position *recule* (9,9 → 10,6). La fiche l'explique — 43 requêtes
> avant, 103 après, dont 83 gagnées sur les variantes « en km/h », « kmh ». Le
> gain vient de la couverture, pas du classement. Aucune métrique par page ne
> pouvait le dire.

**La position se lit à l'envers.** Passer de 12 à 7 est un gain de 5. Le rapport
affiche le signe déjà retourné (`+5` en vert) : afficher le delta brut ferait
lire un succès comme un recul.

**Ajouter une section seulement si elle répond à une question qu'on nous a
posée.** Un tableau qui n'ouvre sur aucune décision allonge le rapport et dilue
les autres. C'est au nom de cette règle que les sections « par catégorie »,
« par recul », « courbe de maturation », « top progressions » et « top reculs »
ont été retirées : toutes utiles au praticien, aucune à un comité — et le
praticien a désormais l'annexe, qui les remplace avec plus de granularité.

### Le PDF

`--pdf` écrit le document envoyé : verdict, les 20 plus fortes progressions et
les 20 plus fortes baisses détaillées requête par requête, puis le reste du lot
en tableau. Environ **25 pages** sur un lot de 165 articles — deux fiches par
page. `--pdf-annex` y ajoute le tableau exhaustif de tous les articles, à
réserver à l'archivage.

Le HTML porte exactement les mêmes sections et reste le livrable partageable
(autonome, charte corail `#FE5C5D`). WeasyPrint est une dépendance optionnelle :
son absence n'échoue pas la commande, elle saute le PDF.

> **Contraintes WeasyPrint**, apprises à la mise au point : pas de
> `grid-template-columns: repeat(auto-fit, …)` (utiliser flex), pas de `<text>`
> SVG (poser le texte en HTML par-dessus), et `table-layout: fixed` +
> `<colgroup>` pour qu'un tableau large ne déborde pas de l'A4.

> **Aucune cellule tronquée.** Les trois familles côte à côte (3 × ~200 px)
> laissaient ~75 px à la requête, coupée en « vitesse de l... », et la colonne
> position débordait sur la voisine ; le tableau du reste du lot coupait les
> slugs (« energies-nuc... ») et cassait « Nouveaux mots-clés » au milieu d'un
> mot. Une seule table pleine largeur par fiche, les colonnes larges renvoient
> à la ligne, `tr { page-break-inside: avoid }` pour qu'une ligne ne soit pas
> coupée entre deux pages. Au-delà de +1 000 %, l'affichage passe en
> multiplicateur (« × 175 ») : « +17 420,0 % » ne se lit pas.

## 3. Écrire l'accroche

**Le chiffre net en gros, puis deux phrases.** Le lecteur voit l'écart net avant
de lire quoi que ce soit ; la prose ne fait que le qualifier.

### Le modèle

> **{écart net} %** — impressions nettes, chaque article comparé à lui-même
> un an plus tôt
>
> Les {N} articles refreshés de {mois} ont produit {après} impressions et
> {après} clics, contre {attendu} impressions et {attendu} clics attendus au
> rythme du reste du site sur les mêmes dates (un an plus tôt à un an plus
> tard). Les clics nets ressortent à {net}. L'écart ne s'explique pas par la
> saison, déjà éliminée par la comparaison à date fixe :
> il suit les articles qui ont été retravaillés.
>
> {N} de ces {total} articles ({part} %) ont moins de 21 jours de recul côté
> « après » — le plus récent {n} jours. Leur effet n'est pas encore installé :
> le chiffre ci-dessus est donc un plancher, pas un palier.

**Le contrefactuel en volumes plutôt qu'en pourcentages.** « Le reste du site
fait +19,6 % » oblige le lecteur à faire le calcul lui-même ; « ces articles
auraient fait 15 008 impressions, ils en ont fait 26 712 » lui donne la
comparaison directement. La quatrième phrase n'est pas une précaution
rhétorique : sans elle, un lot dont la moitié a un recul court côté « après »
se lit comme un résultat stabilisé, et le mois suivant paraîtra contredire
celui-ci.

### Ce qui se joue dans la troisième phrase

Écrire « **il est attribuable au travail éditorial** » revendique une
causalité que la mesure n'établit pas seule : le contrôle écarte la
saisonnalité et une bonne partie de la dérive de marché, il n'écarte pas une
mise à jour d'algorithme qui aurait favorisé ces pages-là.

Écrire « **il suit les articles qui ont été retravaillés** » énonce exactement
ce qui a été observé, et se défend devant l'objection. La formulation est plus
sobre et le rapport est plus solide. Le lecteur fera lui-même l'inférence.

### Règles

- **Le chiffre d'abord.** Le titre porte le résultat, pas la méthode.
- **Volumes bruts systématiquement à côté des pourcentages.** « +153 % de
  clics » sur 84 → 213 clics est vrai et modeste ; le pourcentage seul
  surpromet. Donner les deux protège le rapport.
- **Aucune projection.** « Septembre devrait être supérieur » n'est pas une
  mesure. On peut noter qu'une vague n'a pas encore livré son effet, c'est un
  fait sur le recul ; en tirer un chiffre à venir, non.
- **Si le mois est mauvais, le titre le dit.** Un rapport dont l'accroche est
  toujours positive ne se lit plus.
- Français, pas de jargon SEO non explicité, pas de tiret cadratin dans le
  contenu rédigé.

---

## 4. Procédure mensuelle

**Lancer le 10 du mois suivant, pas le 1er.** Avant cette date les articles
republiés en fin de mois n'ont pas le recul minimal et sortent du rapport (au
1er septembre, le rapport d'août 2026 perdait 34 de ses 78 articles). La
commande refuse d'elle-même sous 90 % de couverture et indique la date utile.

```bash
# 1. Calcul + PDF (deux requêtes GSC par fenêtre, pas par URL : une pour les
#    pages, une pour les requêtes). --tab dès que l'onglet tient une colonne
#    de date : c'est le périmètre ET les dates qui deviennent fiables.
python3 content_writer.py audit impact --site <site-slug> --month YYYY-MM \
    --tab "<onglet>" --pdf

# 2. Lire le HTML de travail
open "sites/<site-slug>/outputs/audit/impact_refresh_YYYY-MM_<site>.html"

# 3. Envoyer le PDF
open "sites/<site-slug>/outputs/audit/impact_refresh_YYYY-MM_<site>.pdf"
```

**Vérifier le compte avant tout commentaire.** Le nombre d'articles annoncé doit
correspondre à ce que l'onglet déclare pour le mois. S'il le dépasse, le rapport
a élargi son périmètre tout seul — c'est le symptôme exact du faux d'août 2026.
Contrôle rapide : compter les lignes de l'onglet dont la colonne de date tombe
dans le mois, et comparer au `counts.republished` du JSON.

Options utiles : `--maturity N` (recul observé, 30 par défaut), `--top-queries N`
(requêtes listées sur chaque fiche, 5 par défaut — affichage seulement, la
collecte récupère toutes les requêtes et l'augmenter ne coûte aucun appel GSC,
mais au-delà de 5 une fiche ne tient plus en tiers de page), `--render-only`
(re-rend HTML et PDF depuis le JSON du mois, sans appel GSC ni WordPress : pour
itérer sur la mise en forme), `--no-queries` (saute la collecte
par requête — le rapport perd alors le déplacement sémantique, seul intérêt :
économiser un appel GSC par fenêtre), `--pdf` / `--pdf-annex`, `--no-wp-check`
(saute le contrôle de cohérence WordPress, un appel API par article),
`--partial`, `--dry-run`.

Puis, avant de diffuser :

1. **Vérifier la couverture.** Si elle n'est pas à 100 %, le rapport ne porte
   pas sur tout le mois et ce sont les articles les plus récents qui manquent.
   Attendre la date indiquée plutôt que de baisser `--maturity`, qui
   dégraderait le résultat de tous les autres articles.
2. **Lire la section « Articles retouchés ».** S'ils sont nombreux, le total
   mélange refresh et interventions ultérieures : le dire, et ne pas citer ces
   articles-là en exemple individuel.
3. **Relire l'accroche** contre la section 3 : chiffre d'abord, volumes bruts
   présents, pas de causalité surjouée, pas de projection.
4. **Regarder les reculs avant de conclure.** S'ils sont nombreux ou
   concentrés sur une catégorie, c'est le vrai sujet du mois, quel que soit le
   total.
5. **Comparer au mois précédent** : les mêmes cohortes vieillissent et leur
   effet doit continuer de croître. Une cohorte qui retombe est un signal.

Le HTML est le livrable partageable (autonome, charte corail Superprof
`#FE5C5D`). Le JSON sert au drill-down.

---

## 5. Pièges de lecture

- **Un article sans impression des deux côtés est écarté**, pas compté à zéro :
  il est hors index ou sous le seuil de remontée GSC, et il fausserait le
  dénominateur.
- **Un très petit effectif produit des pourcentages spectaculaires.** Une vague
  de 2 articles à « +973 % » ne dit presque rien. Toujours lire le Δ avec la
  colonne « Articles » ; ne jamais titrer sur une vague de moins de 5 articles.
- **Le contrôle global est calé sur la vague la plus fournie**, seule assez
  large pour porter une comparaison saisonnière. C'est écrit en pied de page.
- **Les gains en impressions arrivent avant les gains en clics.** Un mois
  peut afficher un fort Δ impressions et un Δ clics plat : c'est la séquence
  normale, pas un échec, mais ça se dit.
- **Un même slug peut porter deux `post_id`** (doublon WordPress) : deux
  fichiers de backup, un seul article en ligne, une seule URL dans GSC. En août
  2026, 78 fichiers correspondaient à 76 articles. La commande dédoublonne en
  gardant la republication la plus récente.
- **Le rapport publié le mois même mesure une pente, pas un palier.** C'est
  volontaire (comparabilité d'un mois sur l'autre) mais ça se dit, sinon la
  relecture à 60 jours donnera l'impression que les chiffres ont changé.
- **Ne jamais recalculer à la main ce que la commande produit.** Le rapport
  d'août 2026 a été calculé ad hoc dans un scratchpad et n'était pas
  reproductible ; c'est précisément ce que ce dispositif corrige.

---

## 6. Tenue du dossier `outputs/<site>/audit/`

**Un rapport par mois et par site**, en HTML + JSON (le JSON sert au
drill-down, il se garde avec son HTML). Purger le reste à chaque nouvelle
production : ce dossier accumule vite des lectures qui se contredisent en
apparence parce qu'elles ne mesurent pas le même objet.

Ce qui se supprime sans hésiter :

- **les rapports calculés à la main** hors de `audit impact` — non
  reproductibles, et leurs chiffres ne correspondent plus à la méthode ;
- **les fenêtres glissantes** quand la lecture year-over-year du même mois
  existe (`_vs_` dans le nom) : la seconde est interprétable, la première
  compare juillet à juin ;
- **les rapports restreints par `--category`** quand le rapport complet de la
  même période existe : c'est un sous-ensemble.

Ce qui se garde : un `gsc_tab_delta_*` par onglet suivi (deux onglets = deux
périmètres, pas un doublon) et le `impact_refresh_*` du mois.

> `outputs/` est **gitignoré** : ces suppressions sont définitives, aucune
> restauration par git. Vérifier le contenu avant de supprimer, pas après.

**Le rapport d'impact demande une source de dates, pas forcément
`wp_backups`.** Trois configurations existent :

- **site publié par `push_to_wp`** : la cascade locale (journal → mtimes →
  `modified`) suffit, c'est le mode par défaut ;
- **site avec un onglet daté** : `--tab`, le mode le plus fiable ;
- **site à publication manuelle suivi dans Notion** : `--source notion`.

### Le mode Notion (enseigna.fr)

`wp_backups/` y est **vide** et le restera : le site publie à la main depuis
WordPress, `push_to_wp` n'y écrit jamais, et l'accès REST est désactivé — aucun
rang de la cascade habituelle n'est disponible. La base Notion de suivi
(`notion.publications` du `site.json`) porte la date qui manque.

**Lire la bonne colonne.** La base en a deux, et prendre la mauvaise vide le
rapport :

| Colonne | Ce qu'elle date | Usage |
|---|---|---|
| `Planing de refresh` | la **republication** | la source du rapport |
| `Date de publication` | la **création** de l'article | à ne jamais utiliser ici |

Sur les 42 articles en ligne d'enseigna.fr, 30 portent une « Date de
publication » de 2023 : la prendre pour une date de refresh mettrait presque
tout le catalogue hors de n'importe quel mois mesuré.

**Le sitemap complète, il ne définit pas.** La colonne Notion est saisie à la
main, donc elle oublie : en août 2026, elle datait 8 des 9 refreshs réels. Le
`lastmod` du sitemap des articles (`post-sitemap*.xml`) voit le neuvième. Il
n'est admis qu'en complément, et **borné aux URLs que la base déclare en
ligne** — c'est exactement la leçon du faux d'août 2026 : un repli de dernier
rang comble un trou dans un lot connu, il ne définit jamais le lot.

Ce qui autorise ce second rang : sur les 19 refreshs que Notion date,
**18 portent un `lastmod` identique au jour près**, le dernier à 5 jours. Ce
qui l'empêche de passer au premier : un `lastmod` ne distingue pas un refresh
d'une correction de coquille. Chaque article porte un `date_source`
(`notion_column` ou `notion_sitemap`) pour que les deux ne soient jamais
présentées comme équivalentes.

**La catégorie vient aussi de Notion.** Les URLs d'enseigna.fr sont à plat,
sans segment de rubrique : sans la colonne « Catégorie », toutes les fiches
s'affichaient « hors arborescence ».

---

## Frontière avec les autres commandes

- `/tab-perf` (`audit gsc-tab`) — suivi d'un **périmètre** (onglet Sheet ou
  base Notion) sur un mois calendaire, avec les statuts éditoriaux. À utiliser
  pour « comment va cette liste de travail ».
- `/blog`, `/page` — perfs brutes d'un site ou d'une URL, sans notion de
  refresh.
- **Cette skill** — impact **du travail du mois**, article par article.
