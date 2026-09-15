---
description: Monthly refresh impact report - every republished article compared to itself on its own window, seasonality deducted by a control group.
argument-hint: --site <site-slug> --month YYYY-MM [--pdf] [--maturity 30] [--top-queries 10] [--no-queries] [--no-wp-check]
allowed-tools: Bash(python3 content_writer.py audit impact:*), Read, Skill
---

Mesure **ce que le travail éditorial du mois a produit**, article par article.

```bash
python3 content_writer.py audit impact $ARGUMENTS
```

**Invoquer la skill `impact-report` avant de commenter le résultat** : elle
porte la méthode (sources de dates, fenêtres, groupe de contrôle), le spectre
des sections et la façon d'écrire l'accroche sans surpromettre.

Chaque article est comparé **à lui-même** sur sa propre fenêtre : les N jours
suivant sa republication contre les N jours la précédant, à durée égale. C'est
ce qui distingue cette commande de `/tab-perf` (`audit gsc-tab`), qui mesure un
**périmètre** sur un mois calendaire — sur un article republié le 25 du mois,
une lecture calendaire juge surtout les 24 jours *d'avant* le refresh. Les deux
peuvent conclure en sens opposés sans qu'aucune soit fausse ; **dire laquelle
on cite**.

**Lancer le 10 du mois suivant, pas le 1er.** Un article republié le 31 n'a pas
les 7 jours de recul minimum (plus 3 j de latence GSC) et sort du rapport :
lancé au 1er septembre, le rapport d'août 2026 ne couvrait que 44 de ses 78
articles, et rien dans le total ne l'aurait signalé. La commande **refuse** de
produire un rapport sous 90 % de couverture, indique combien d'articles
manquent et à partir de quand le lot est complet.

Options : `--site` (requis), `--month YYYY-MM` **ou** `--start`/`--end`,
`--maturity` (recul observé, 30 j par défaut ; en deçà de 7 j l'article est
écarté), `--top` (lignes par tableau, 15), `--no-wp-check` (saute le contrôle
de cohérence WordPress, un appel API par article), `--partial` (force un
rapport à couverture incomplète, avec bandeau de réserve), `--dry-run`.

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

**Groupe de contrôle** : le reste du site (hors articles traités) sur
exactement les mêmes dates. C'est lui qui déduit la saisonnalité et rend
l'« écart net » défendable — sans lui, un mois de rentrée se lit comme un
succès éditorial.

**Déplacement sémantique** : une requête GSC supplémentaire par fenêtre (pas par
URL) donne, article par article, les requêtes **maintenues** (avec le delta de
position), **gagnées** et **perdues**. C'est ce qui distingue une remontée de
classement d'un élargissement de couverture — deux réussites très différentes
que les métriques par page confondent. `--no-queries` la désactive.

**Trajectoire mensuelle** : le rapport compare l'écart net d'un mois à l'autre
dès qu'au moins deux mois sont mesurables. `wp_backups/` ne remontant pas avant
août 2026, le premier point de comparaison arrivera avec le rapport de
septembre ; d'ici là le bloc affiche « premier point de mesure ».

**Deux livrables, deux lecteurs.** Le **PDF** (`--pdf`, 2 pages, charte corail)
est ce qu'on envoie : verdict net, tuiles, camembert de fiabilité, réserves.
Le **HTML** garde en plus l'annexe de monitoring — tableau des N articles puis
une fiche par URL avec son **déplacement sémantique** (requêtes maintenues,
gagnées, perdues, positions avant/après). `--pdf-annex` met l'annexe dans le PDF
(~85 pages) : pour l'archive, jamais pour l'envoi. Le JSON sert au drill-down.

Dans le chat, restituer l'écart net vs contrôle, la répartition
progression/stable/recul, et les **articles en recul** avec leurs requêtes
perdues (candidats à une seconde passe) — pas les métriques brutes par URL.
