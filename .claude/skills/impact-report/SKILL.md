---
name: impact-report
description: >-
  Rapport mensuel d'impact des refreshs (tous sites) : mesurer et raconter ce
  que le travail éditorial du mois a produit, chaque article comparé à
  lui-même sur sa propre fenêtre plutôt qu'au mois calendaire. Définit les deux
  étages du livrable (PDF directeur de 2 pages, annexe de monitoring par URL
  avec le déplacement sémantique requête par requête), le groupe de contrôle qui
  déduit la saisonnalité, et la façon d'écrire l'accroche sans surpromettre. S'appuie sur
  `python3 content_writer.py audit impact`. À invoquer le 10 du mois suivant,
  jamais le 1er : avant cette date les articles republiés en fin de mois n'ont
  pas le recul minimal et sortent silencieusement du rapport.
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

## 1. La mesure : chaque article contre lui-même

**L'unité de mesure est l'article, pas le mois.**

Pour chaque article republié : les N jours qui **suivent** sa republication
contre les N jours qui la **précèdent**, à durée strictement égale, le jour de
publication exclu des deux côtés (il porte les deux versions).

Pourquoi pas le mois calendaire, qui serait plus simple :

- Un article republié le 25 août, mesuré sur « août 2026 vs août 2025 », est
  jugé à 80 % sur les 24 jours **d'avant** son refresh. On mesure alors
  l'inertie de l'ancienne version.
- Un onglet contient des articles traités et des articles qui ne le sont pas.
  Le résultat décrit l'onglet, pas le travail.

> C'est exactement la divergence entre ce rapport et `/tab-perf`
> (`audit gsc-tab`) : ce dernier mesure **un périmètre sur un mois**, celui-ci
> mesure **un travail sur sa propre fenêtre**. Les deux peuvent conclure en
> sens opposés sans qu'aucun ne soit faux — ils ne portent pas sur le même
> objet. Quand les deux lectures circulent, **dire laquelle on cite**.

### Le recul (`--maturity`, 30 j par défaut)

**Question ouverte, et la mesure y répond mieux qu'une convention.** L'intuition
courante est qu'il faut *attendre* que Google repasse, donc qu'une fenêtre de
30 jours serait trop courte. La courbe de maturation mesurée sur la cohorte du
6 août 2026 (39 articles) montre autre chose :

| Fenêtre | Impressions/jour | Régime |
|---|---|---|
| Avant refresh | 246 | ×1,00 |
| J+1 → J+7 | 365 | ×1,48 |
| J+8 → J+14 | 548 | ×2,23 |
| J+15 → J+21 | 653 | ×2,65 |
| J+22 → J+28 | 900 | ×3,66 |
| J+29 → J+34 | 987 | ×4,01 |

Trois enseignements :

1. **Google repasse dès la première semaine.** Le signal est déjà à ×1,5 à
   J+7. Il n'y a pas de période aveugle à attendre.
2. **La courbe n'a pas atteint son palier à J+30.** Une mesure à 30 jours
   **sous-estime** l'effet — elle en capte la pente. Le rapport doit le dire :
   c'est un argument en faveur du travail, pas contre lui.
3. **Il n'existe donc pas de « bonne » fenêtre unique.** Courte, elle mesure un
   effet immature ; longue, elle exclut les articles récents. Ce qui compte
   n'est pas la valeur de N mais que **N soit identique des deux côtés** et
   que la courbe de maturation accompagne le chiffre.

Bornes retenues :

- **Moins de 7 jours** : article écarté. L'effet existe mais l'échantillon de
  jours est trop court pour distinguer le signal du bruit de recrawl.
- **Au-delà de 30 jours** : la fenêtre « avant » commence à mordre sur un
  refresh antérieur, la référence n'est plus une version stable. C'est la
  seule raison de plafonner — pas la maturité de l'effet.
- La fenêtre se ferme **3 jours avant aujourd'hui** : les derniers jours GSC
  sont sous-comptés, les inclure ferait passer une donnée incomplète pour une
  baisse de trafic.

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
entrer les articles récents, mais mesurerait tout le mois à ×1,5 au lieu de
×2-4 (voir la courbe ci-dessus) : la couverture serait sauvée, le résultat
divisé par deux, et les mois ne seraient plus comparables entre eux.

### Reculs inégaux dans un même rapport

Même à couverture complète, les articles n'ont pas tous le même recul : au 10
septembre, la vague du 6 août a 30 jours et celle du 25 en a 13. Comme l'effet
croît fortement avec le recul, **le total agrège des stades de maturation
différents** et sous-estime les vagues récentes.

Le rapport le signale dès que l'écart atteint 14 jours. Dans ce cas, **citer la
lecture par vague plutôt que le total** : c'est la seule qui compare des
articles au même stade.

> **Pour mesurer le palier plutôt que la pente**, relancer le mois M à M+2 avec
> `--maturity 60`. Le chiffre publié le mois même reste la lecture à 30 jours,
> comparable d'un mois sur l'autre ; la relecture tardive dit où l'effet s'est
> stabilisé.

### La source des dates de republication

C'est la question la plus piégeuse du dispositif. **Cascade à trois niveaux**,
du plus sûr au plus faible ; on ne descend d'un cran que faute du précédent.

| Rang | Source | Ce qu'elle date |
|---|---|---|
| 1 | **`wp_backups/_publications.jsonl`** | Chaque publication réussie de `push_to_wp` (journal append-only) |
| 2 | **`wp_backups/{id}_before.json`** (mtime) | La *première* publication d'un post par `push_to_wp` |
| 3 | **WordPress `modified`**, restreint aux articles que la Sheet dit publiés | La dernière modification — repli documenté ci-dessous |

Écartées : `outputs/<site>/html/` (date la *rédaction*, pas la mise en ligne, et
ce dossier est voué à être purgé) et la colonne « Date de refresh » seule
(saisie manuelle, incomplète).

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

Le reste du site (total GSC **moins** les articles traités) sur *exactement*
les mêmes dates que la vague mesurée. Sans lui, un mois de rentrée scolaire se
lit comme un succès éditorial.

Retirer les articles traités du contrôle n'est pas cosmétique : les laisser
dedans mettrait la mesure des deux côtés de la comparaison et écraserait
l'écart.

**Écart net par vague** = variation de la vague − variation de son contrôle.

**Au niveau du lot, ne pas moyenner les contrôles** : chaque vague a sa propre
fenêtre, donc sa propre saisonnalité, et appliquer à tout le mois le contrôle
de la vague dominante prêterait aux autres un contexte qu'elles n'ont pas
connu. Le rapport calcule un **contrefactuel pondéré** : pour chaque vague, ce
que ses articles auraient fait au rythme du reste du site, puis la somme.

D'où la formulation en volumes, la plus parlante : « ces articles auraient fait
15 008 impressions, ils en ont fait 26 712, soit +78,0 % au-dessus de
l'attendu ». C'est ce chiffre-là qu'on cite, pas le +120,7 % brut qui ne
retranche rien.

> Sur août 2026, le passage d'un contrôle mono-vague au contrefactuel pondéré
> a fait passer le contrôle de « −10,7 % de clics » à « +2,8 % » : la première
> lecture appliquait au mois entier la saisonnalité de la seule première
> semaine d'août.

---

## 2. Le spectre à étudier

**Le rapport a deux lecteurs, donc deux étages.** Les confondre est l'erreur qui
a produit la première version : trop de prose méthodologique pour un directeur,
trop peu de granularité pour piloter le travail (27 articles montrés sur 76,
aucun mot-clé).

### Étage 1 — le document envoyé (2 pages, PDF)

Un directeur arbitre trois choses : continuer, changer d'échelle, changer de
direction. Rien d'autre n'a sa place ici.

| # | Bloc | Répond à |
|---|---|---|
| 1 | **Verdict** : écart net d'impressions, en gros | « Ça a marché ou pas ? » |
| 2 | **Tuiles** : impr. nettes, clics nets, articles, effet médian | « De combien ? » |
| 3 | **Fiabilité** : camembert progression / stable / recul | « Puis-je y croire ? » |
| 4 | **Trajectoire** : écart net mois après mois | « Ça se cumule ? » |
| 5 | **Réserves** : couverture, reculs inégaux, retouches | « Le chiffre est-il propre ? » |
| 6 | **Méthode**, repliée | « D'où sort ce chiffre ? » |

**Le verdict porte le chiffre net, jamais le brut.** Le brut (+120,7 % en août
2026) ne retranche pas la saison et se fait démonter dès qu'on demande « et sans
la rentrée ? ». Le net (+78,0 %) est celui qui tient.

**Le camembert reste sous 6 secteurs** — trois ici. Au-delà, un secteur cesse
d'être lisible et il faut une table. C'est pourquoi les 12 catégories
éditoriales n'y sont pas : elles violeraient la règle, et elles n'intéressent
pas ce lecteur.

**Seuil de ±5 % sur la répartition.** En deçà, la variation n'est pas
distinguable du bruit GSC. Compter un article à +2 % comme une victoire faisait
passer août 2026 de 59 à 64 gagnants : le premier chiffre se défend, pas le
second.

### Étage 2 — l'annexe de monitoring (HTML, ~85 pages)

C'est l'outil de travail, celui qui dit **sur quoi** un article a bougé.

| Bloc | Contenu |
|---|---|
| **Tableau de synthèse** | les N articles : impressions, Δ, **Δ net**, clics, position, KW gagnés / perdus |
| **Fiche par article** | les mêmes métriques, puis le déplacement sémantique |

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

`--pdf` écrit l'étage 1 seul (2 pages). `--pdf-annex` y ajoute l'annexe (~85
pages sur un lot de 76 articles) — à réserver à l'archivage, jamais à l'envoi.
WeasyPrint est une dépendance optionnelle : son absence n'échoue pas la commande,
elle saute le PDF.

> **Contraintes WeasyPrint**, apprises à la mise au point : pas de
> `grid-template-columns: repeat(auto-fit, …)` (utiliser flex), pas de `<text>`
> SVG (poser le texte en HTML par-dessus), et `table-layout: fixed` +
> `<colgroup>` pour qu'un tableau large ne déborde pas de l'A4.

## 3. Écrire l'accroche

**Le chiffre net en gros, puis deux phrases.** Le lecteur voit l'écart net avant
de lire quoi que ce soit ; la prose ne fait que le qualifier.

### Le modèle

> **{écart net} %** — impressions nettes, saisonnalité déduite
>
> Les {N} articles refreshés de {mois} ont produit {après} impressions et
> {après} clics, contre {attendu} impressions et {attendu} clics attendus au
> rythme du reste du site sur les mêmes dates. Les clics nets ressortent à
> {net}. L'écart ne s'explique pas par la saison :
> il suit les articles qui ont été retravaillés.
>
> {N} de ces {total} articles ({part} %) ont moins de 21 jours de recul — le
> plus récent {n} jours. Leur effet n'est pas encore installé : le chiffre
> ci-dessus est donc un plancher, pas un palier.

**Le contrefactuel en volumes plutôt qu'en pourcentages.** « Le reste du site
fait +19,6 % » oblige le lecteur à faire le calcul lui-même ; « ces articles
auraient fait 15 008 impressions, ils en ont fait 26 712 » lui donne la
comparaison directement. La quatrième phrase n'est pas une précaution
rhétorique : sans elle, un lot dont la moitié est immature se lit comme un
résultat stabilisé, et le mois suivant paraîtra contredire celui-ci.

### Ce qui se joue dans la troisième phrase

Écrire « **il est attribuable au travail éditorial** » revendique une
causalité que la mesure n'établit pas seule : le contrôle écarte la
saisonnalité, il n'écarte pas une mise à jour d'algorithme qui aurait favorisé
ces pages-là.

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
# 1. Calcul + PDF directeur (deux requêtes GSC par fenêtre, pas par URL :
#    une pour les pages, une pour les requêtes)
python3 content_writer.py audit impact --site <site-slug> --month YYYY-MM --pdf

# 2. Lire le HTML de travail (les deux étages)
open "sites/<site-slug>/outputs/audit/impact_refresh_YYYY-MM_<site>.html"

# 3. Envoyer le PDF (2 pages)
open "sites/<site-slug>/outputs/audit/impact_refresh_YYYY-MM_<site>.pdf"
```

Options utiles : `--maturity N` (recul observé, 30 par défaut), `--top-queries N`
(requêtes listées par famille, 10 par défaut), `--no-queries` (saute la collecte
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

**Le rapport d'impact n'est pas produisible partout.** Il lui faut
`outputs/<site>/wp_backups/`, donc un site publié par `push_to_wp`. Sur un
site à publication manuelle (enseigna.fr aujourd'hui) il n'y a pas de dates de
republication à exploiter : seul `/tab-perf` s'y applique. Ne pas conclure
qu'un rapport manquant a été perdu — vérifier d'abord que le site trace ses
publications.

---

## Frontière avec les autres commandes

- `/tab-perf` (`audit gsc-tab`) — suivi d'un **périmètre** (onglet Sheet ou
  base Notion) sur un mois calendaire, avec les statuts éditoriaux. À utiliser
  pour « comment va cette liste de travail ».
- `/blog`, `/page` — perfs brutes d'un site ou d'une URL, sans notion de
  refresh.
- **Cette skill** — impact **du travail du mois**, article par article.
