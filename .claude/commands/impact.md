---
description: Monthly refresh impact report - every republished article compared to itself a year earlier, same calendar date, market drift deducted by a control group.
argument-hint: --site <site-slug> --month YYYY-MM [--pdf] [--maturity 30] [--top-queries 5] [--no-queries] [--no-wp-check]
allowed-tools: Bash(python3 content_writer.py audit impact:*), Read, Skill
---

Mesure **ce que le travail éditorial du mois a produit**, article par article.

```bash
python3 content_writer.py audit impact $ARGUMENTS
```

**Invoquer la skill `impact-report` avant de commenter le résultat** : elle
porte la méthode (sources de dates, fenêtres, groupe de contrôle), le spectre
des sections et la façon d'écrire l'accroche sans surpromettre.

Chaque article est comparé **à lui-même, un an plus tôt, à date fixe** : les N
jours suivant sa republication contre les N jours suivant la même date un an
auparavant, à durée égale. Comparer les mêmes dates calendaires à un an
d'écart élimine la saisonnalité par construction plutôt que de la déduire
après coup. C'est ce qui distingue cette commande de `/tab-perf`
(`audit gsc-tab`) : les deux comparent désormais une période à son année
précédente, mais `/tab-perf` le fait sur un **périmètre** (un onglet entier,
articles retravaillés ou non) et un **mois calendaire**, quand `/impact` le
fait **article par article**, chacun ancré sur SA date de republication, sur
le **lot effectivement retravaillé**. Les deux peuvent conclure en sens
opposés sans qu'aucune soit fausse ; **dire laquelle on cite**.

**Lancer le 10 du mois suivant, pas le 1er.** Un article republié le 31 n'a pas
les 7 jours de recul minimum (plus 3 j de latence GSC) et sort du rapport :
lancé au 1er septembre, le rapport d'août 2026 ne couvrait que 44 de ses 78
articles, et rien dans le total ne l'aurait signalé. La commande **refuse** de
produire un rapport sous 90 % de couverture, indique combien d'articles
manquent et à partir de quand le lot est complet.

**Sites sans trace locale de publication.** `--source notion` lit les dates
dans la base de suivi Notion du site (colonne « Planing de refresh », jamais
« Date de publication » qui date la création) et complète avec le `lastmod`
du sitemap des articles, borné aux URLs que la base déclare en ligne. C'est
le seul mode qui marche sur enseigna.fr, où `wp_backups/` est vide parce que
la publication est manuelle.

Options : `--site` (requis), `--month YYYY-MM` **ou** `--start`/`--end`,
`--maturity` (recul observé, 30 j par défaut ; en deçà de 7 j l'article est
écarté), `--top` (lignes par tableau, 15), `--top-queries` (requêtes listées
sur chaque fiche, les N qui pèsent le plus avant ou après, 5 par défaut —
affichage seulement, aucun appel GSC supplémentaire), `--pdf` (document
envoyé, ~30 pages) / `--pdf-annex` (y ajoute l'index tabulaire du lot, pour
l'archivage), `--render-only` (re-rend HTML et PDF depuis le JSON du mois sans
aucun appel GSC ni WordPress, pour itérer sur la mise en forme), `--no-wp-check` (saute le contrôle
de cohérence WordPress, un appel API par article), `--partial` (force un
rapport à couverture incomplète, avec bandeau de réserve), `--dry-run`.

**Le rapport a trois étages** : le verdict (avec la distribution du recul
disponible côté « après », seul recul qui varie encore selon la date de
republication dans le mois), puis les 20 plus fortes progressions et les 20
plus fortes baisses détaillées requête par requête avec un **diagnostic** par
URL (nouveaux mots-clés / classement amélioré / perte de requêtes / recul sur
mêmes requêtes), chaque fiche portant les 5 requêtes qui pèsent le plus
(avant ou après, avec leur statut gagnée / maintenue / perdue) et une lecture
rédigée de deux à quatre phrases, puis le reste du lot avec la même fiche,
complété de quelques paragraphes sur ses cas les plus notables (trafic et
position qui divergent). Aucune cellule n'est tronquée.

> Ne pas contourner un refus en baissant `--maturity` : la couverture serait
> sauvée mais tout le mois serait mesuré à un stade précoce (×1,5 au lieu de
> ×2-4), et les mois cesseraient d'être comparables.

**Dates de republication : `outputs/<site>/wp_backups/`**, écrit par
`push_to_wp` — la seule source qui date un *acte de refresh*. Ni la colonne
« Date de refresh » de la Sheet (saisie manuelle, incomplète), ni le champ
`modified` de WordPress : ce dernier date la dernière modification quelconque
et une retouche ultérieure l'écrase (69 des 78 articles d'août 2026). Il sert
donc de **contrôle** : il signale les articles retouchés après leur refresh,
dont la fenêtre « après » mélange deux interventions.

> Corollaire : **ne pas purger `wp_backups/`**. `outputs/html/` peut l'être,
> pas cette trace, sans quoi tout rapport rétrospectif devient impossible.

**Groupe de contrôle** : le reste du site (hors articles traités), comparé lui
aussi à J-365 sur exactement les mêmes dates que la vague mesurée. La
saisonnalité étant déjà éliminée par la fenêtre année-sur-année, ce contrôle
capte surtout une dérive de marché résiduelle (le reste du site progresse ou
régresse structurellement d'une année sur l'autre) et rend l'« écart net »
défendable.

**Déplacement sémantique** : une requête GSC supplémentaire par fenêtre (pas par
URL) donne, article par article, les requêtes **maintenues** (avec le delta de
position), **gagnées** et **perdues**. C'est ce qui distingue une remontée de
classement d'un élargissement de couverture — deux réussites très différentes
que les métriques par page confondent. `--no-queries` la désactive.

**Mois mesuré** : le rapport HTML n'affiche que l'écart net du mois demandé,
sans comparaison visuelle avec les mois précédents (une barre isolée ne trace
pas de trajectoire). L'historique mois par mois continue d'être écrit dans le
JSON (`trajectory`), qui reste la source si une lecture comparative dans le
temps est nécessaire.

**Deux livrables, deux lecteurs.** Le **PDF** (`--pdf`, 2 pages, charte corail)
est ce qu'on envoie : verdict net, tuiles, camembert de fiabilité, réserves.
Le **HTML** garde en plus l'annexe de monitoring — tableau des N articles puis
une fiche par URL avec son **déplacement sémantique** (requêtes maintenues,
gagnées, perdues, positions avant/après). `--pdf-annex` met l'annexe dans le PDF
(~85 pages) : pour l'archive, jamais pour l'envoi. Le JSON sert au drill-down.

Dans le chat, restituer l'écart net vs contrôle, la répartition
progression/stable/recul, et les **articles en recul** avec leurs requêtes
perdues (candidats à une seconde passe) — pas les métriques brutes par URL.
