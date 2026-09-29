# Rapport d'impact mensuel des refreshs — template de reproduction

Document de reproduction : **comment relancer ce rapport chaque mois**, et **ce
qu'il doit contenir** une fois produit. Valable pour tout site qui remplit les
prérequis (section 1), pas seulement superprof.fr-ressources.

La méthode et ses justifications vivent dans la skill `impact-report` ; ce
document-ci est le mode d'emploi. En cas de divergence, la skill fait foi sur la
méthode, ce fichier sur la procédure.

---

## 1. Prérequis — le rapport est-il produisible sur ce site ?

Trois conditions. Les vérifier **avant** de promettre un rapport : sur un site
qui n'en remplit aucune, la commande échoue ou, pire, produit un lot faux.

| # | Condition | Comment vérifier | Si absente |
|---|---|---|---|
| 1 | La propriété GSC du site est accessible | `python3 content_writer.py audit gsc-state --site <slug>` répond | Rien n'est mesurable, s'arrêter là |
| 2 | Les refreshs du mois sont **datés** | l'onglet de suivi déclare `col_date` dans `sheets.tabs` du `site.json` | voir « Sites sans date » ci-dessous |
| 3 | GSC a 16 mois d'historique sur ces URLs | le site existait et était indexé l'an dernier | les articles sortent en « nouveau », sans comparaison |

### État par site (à mettre à jour quand un site est onboardé)

| Site | Onglet daté | Trace de publication | Rapport produisible |
|---|---|---|---|
| `superprof.fr-ressources` | oui — onglet `Medium Potential`, `col_date` déclaré | `wp_backups/` alimenté par `push_to_wp` | **oui**, mode `--tab` |
| `enseigna.fr` | non — aucun onglet ne déclare `col_date`, mais la base Notion porte « Planing de refresh » | `wp_backups/` **vide** (publication manuelle), complété par le `lastmod` du sitemap | **oui**, mode `--source notion` |

### Sites sans date de refresh (cas enseigna.fr)

Le rapport ne peut pas être produit tant qu'il n'existe aucune date de
republication. Ce n'est pas un bug à contourner : sans date, il n'y a pas de
fenêtre à mesurer. Deux façons d'y remédier, dans cet ordre de préférence :

1. **Ajouter une colonne « Date de refresh » à l'onglet**, puis la déclarer dans
   `sites/<slug>/config/site.json` :
   ```json
   "sheets": { "tabs": [ { "name": "Avis", "col_date": 7 } ] }
   ```
   (`col_date` est l'index de colonne, 0 = colonne A.) C'est la source la plus
   fiable : elle date un acte éditorial, saisi par la personne qui a fait le
   refresh.
2. **Publier via `push_to_wp`** plutôt qu'à la main, ce qui alimente
   `outputs/<site>/wp_backups/` et le journal `_publications.jsonl`. La date
   devient alors automatique.

> Ne **jamais** se rabattre sur le champ `modified` de WordPress pour définir le
> périmètre. Il date la dernière écriture quelconque sur le post : en août 2026
> ce repli a fait passer le rapport de 86 articles déclarés à 166 mesurés, en y
> faisant entrer des refreshs de juin simplement réédités depuis.

---

## 2. Quand lancer

**Le 10 du mois suivant.** Pas le 1er.

Un article republié le 31 n'a pas les 7 jours de recul minimum, et GSC ajoute
3 jours de latence de consolidation. Lancé le 1er septembre, le rapport d'août
2026 ne couvrait que 44 de ses 78 articles — et le biais est invisible dans un
total, puisque ce sont toujours les derniers publiés qui manquent.

La commande **refuse** d'elle-même de produire un rapport sous 90 % de
couverture et indique la date à laquelle le lot sera complet.

> **Ne pas contourner un refus en baissant `--maturity`.** La couverture serait
> sauvée, mais tout le mois serait mesuré à un stade précoce et les mois
> cesseraient d'être comparables entre eux.

---

## 3. La commande

```bash
python3 content_writer.py audit impact \
    --site superprof.fr-ressources \
    --month 2026-08 \
    --tab "Medium Potential" \
    --pdf
```

Adapter `--site`, `--month` et `--tab` (le nom exact déclaré dans
`sheets.tabs`). Sur un autre site, ne rien changer d'autre.

### Options utiles

| Option | Effet | Quand s'en servir |
|---|---|---|
| `--tab "<nom>"` | périmètre **et** dates viennent de la colonne de l'onglet | dès que l'onglet a un `col_date` — le mode fiable |
| `--source notion` | périmètre **et** dates viennent de la base Notion (colonne « Planing de refresh »), complétés par le `lastmod` du sitemap | site à publication manuelle, sans `wp_backups` (enseigna.fr) |
| `--pdf` | écrit le PDF A4 à côté du HTML | pour le document qu'on envoie |
| `--pdf-annex` | ajoute le tableau exhaustif au PDF | archivage seulement, pas pour l'envoi |
| `--no-wp-check` | saute le contrôle WordPress (1 appel API par article) | pour aller vite ; on perd la liste des articles retouchés après refresh |
| `--maturity N` | jours observés après republication (30 par défaut) | relecture tardive à 60 j, pour mesurer le palier |
| `--top-queries N` | requêtes listées sur chaque fiche, les N qui pèsent le plus avant ou après (5) | affichage seul, ne coûte aucun appel GSC |
| `--render-only` | re-rend HTML et PDF depuis le JSON du mois, sans aucun appel | pour changer la mise en forme sans repayer la collecte |
| `--partial` | force un rapport à couverture incomplète | seulement si une lecture anticipée est indispensable |
| `--dry-run` | calcule sans rien écrire | vérifier un périmètre avant de produire |

### Sorties

Trois fichiers dans `sites/<slug>/outputs/audit/` :

- `impact_refresh_<mois>_<site>.html` — le livrable de travail, complet ;
- `impact_refresh_<mois>_<site>.pdf` — le document envoyé ;
- `impact_refresh_<mois>_<site>.json` — les données, pour le drill-down.

> Le rendu (HTML/PDF) se régénère depuis le JSON sans refaire d'appel GSC. Utile
> quand seule la mise en forme change : inutile de repayer la collecte.

---

## 4. Ce que le rapport doit contenir

Trois étages, dans cet ordre. Chacun répond à une question différente et
s'adresse à un lecteur différent.

### Étage 1 — le verdict (page 1)

Ce qu'un directeur lit, et rien d'autre.

| Bloc | Contenu | Répond à |
|---|---|---|
| **Verdict** | variation d'impressions sur un an, en gros | « ça a marché ? » |
| **Chiffres clés** | impressions, clics, position — en volumes `avant → après` | « de combien ? » |
| **Fiabilité** | répartition progression / stable / recul | « puis-je y croire ? » |
| **Recul disponible** | jours mesurés après refresh (min-médiane-max) | « c'est mesuré sur quoi ? » |
| **Réserves** | couverture, articles retouchés depuis | « le chiffre est-il propre ? » |
| **Méthode**, repliée | fenêtres, sources de dates | « d'où sort ce chiffre ? » |

**Les chiffres se donnent en volumes bruts, avant → après.** « 25 654 → 33 829
impressions » se lit sans connaître la méthode ; un pourcentage seul, non. Les
deux ensemble valent mieux qu'un pourcentage seul : « +153 % de clics » sur
84 → 213 clics est vrai et modeste, le pourcentage seul surpromet.

**Un seuil de ±5 % sur la répartition.** En deçà, la variation n'est pas
distinguable du bruit GSC : l'article est compté stable, pas gagnant.

### Étage 2 — ce sur quoi on agit

L'outil de travail : il dit **sur quelles requêtes** un article a bougé.

| Bloc | Contenu |
|---|---|
| **Ont grimpé** | les 20 plus fortes progressions, en fiche : métriques, diagnostic, les 5 requêtes qui pèsent le plus (avant ou après) avec leur statut, lecture rédigée |
| **N'ont pas fonctionné** | les 20 plus fortes baisses, même format |
| **Le reste du lot** | même fiche pour chaque article restant, puis des paragraphes commentant les cas notables |

**Les extrêmes d'abord, mais chaque article a sa fiche.** La direction lit
les 5 requêtes de chaque URL et leur lecture ; les 40 extrêmes ouvrent la
section parce qu'ils appellent une décision. Aucune cellule n'est tronquée.

**Le déplacement sémantique, en trois familles** — c'est ce qui distingue deux
réussites très différentes que les métriques par page confondent :

- **maintenues** : présentes les deux années, avec le delta de position — le
  mouvement de classement ;
- **gagnées** : absentes avant, présentes après — l'élargissement de couverture ;
- **perdues** : l'inverse, le seul signal d'alerte éditorial.

**La position se lit à l'envers.** Passer de 12 à 7 est un gain de 5. Le rapport
affiche le signe déjà retourné.

**Une progression depuis zéro s'affiche en volume, pas en pourcentage.** Une
page invisible l'an dernier n'a pas de taux de progression : afficher « n/a »
effacerait une vraie réussite, le rapport affiche « nouveau » et le volume créé.

### Étage 3 — l'annexe (`--pdf-annex`)

Le tableau exhaustif. Pour l'archivage, jamais pour l'envoi.

---

## 5. Avant de diffuser — la checklist

1. **Vérifier le compte d'articles.** Il doit correspondre à ce que l'onglet
   déclare pour le mois. S'il le dépasse, le rapport a élargi son périmètre tout
   seul : c'est le symptôme exact du faux d'août 2026. Comparer
   `counts.republished` du JSON au nombre de lignes de l'onglet datées dans le
   mois.
2. **Vérifier la couverture.** Si elle n'est pas à 100 %, ce sont les articles
   les plus récents qui manquent. Attendre la date indiquée plutôt que de
   baisser `--maturity`.
3. **Lire les réserves.** Des articles retouchés après leur refresh mélangent
   deux interventions : ne pas les citer comme preuve isolée.
4. **Regarder les reculs avant de conclure.** S'ils sont nombreux ou concentrés
   sur une catégorie, c'est le vrai sujet du mois, quel que soit le total.
5. **Relire l'accroche** contre les règles de la section 6.

---

## 6. Écrire l'accroche

**Le chiffre d'abord, puis deux phrases.** Le lecteur voit le résultat avant de
lire quoi que ce soit ; la prose ne fait que le qualifier.

### Le modèle

> Les {N} articles refreshés de {mois} ont produit **{impressions} impressions**
> et **{clics} clics**. Un an plus tôt, ces mêmes articles faisaient
> **{impressions N-1} impressions** et **{clics N-1} clics** sur les mêmes
> dates, soit {variation} d'impressions et {variation} de clics.

### Règles

- **Le titre porte le résultat, pas la méthode.**
- **Volumes bruts systématiquement à côté des pourcentages.** Donner les deux
  protège le rapport.
- **Aucune projection.** « Septembre devrait être supérieur » n'est pas une
  mesure. Noter qu'une vague n'a pas encore livré son effet est un fait sur le
  recul ; en tirer un chiffre à venir, non.
- **Pas de causalité surjouée.** Écrire « attribuable au travail éditorial »
  revendique ce que la mesure n'établit pas. « Il suit les articles qui ont été
  retravaillés » énonce ce qui a été observé et se défend devant l'objection.
- **Si le mois est mauvais, le titre le dit.** Une accroche toujours positive ne
  se lit plus.
- Français, pas de jargon SEO non explicité, pas de tiret cadratin.

---

## 7. Pièges de lecture

- **Un recul contre l'an dernier n'est pas forcément un refresh raté.** Le
  « après » est mesuré 3 à 4 semaines après le refresh, quand l'effet monte
  encore ; le « avant » est une photo d'il y a un an qui peut avoir été
  exceptionnellement haute. Trancher au cas par cas sur la fiche de l'article,
  via son mouvement de requêtes.
- **Un article sans impression les deux années est écarté**, pas compté à zéro :
  il fausserait le dénominateur.
- **Un petit effectif produit des pourcentages spectaculaires.** Ne jamais
  titrer sur un lot de moins de 5 articles.
- **Les gains en impressions arrivent avant les gains en clics.** Un fort delta
  d'impressions avec des clics plats est la séquence normale, pas un échec.
- **Un même slug peut porter deux `post_id`** (doublon WordPress) : la commande
  dédoublonne en gardant la republication la plus récente.
- **Ne jamais recalculer à la main ce que la commande produit.** Un rapport
  calculé dans un scratchpad n'est pas reproductible et ses chiffres ne
  correspondent plus à la méthode.

---

## 8. Tenue du dossier `outputs/<site>/audit/`

Un rapport par mois et par site, en HTML + JSON + PDF. Purger le reste : ce
dossier accumule vite des lectures qui se contredisent en apparence parce
qu'elles ne mesurent pas le même objet.

Ce qui se supprime sans hésiter : les rapports calculés à la main hors de
`audit impact`, et les rapports restreints par catégorie quand le rapport
complet de la même période existe.

> **Ne pas purger `outputs/<site>/wp_backups/`.** C'est la seule trace durable
> de l'historique de publication sur les sites qui publient via `push_to_wp`.
> `outputs/html/` peut être purgé sans dommage ; celui-ci non.

> `outputs/` est gitignoré : ces suppressions sont définitives, aucune
> restauration par git.

---

## 9. Frontière avec les autres commandes

- **`/impact`** (ce document) — l'impact du **travail du mois**, article par
  article, chacun comparé à lui-même un an plus tôt à date fixe, sur le lot
  effectivement retravaillé.
- **`/tab-perf`** (`audit gsc-tab`) — le suivi d'un **périmètre** (onglet Sheet
  ou base Notion) sur un mois calendaire, articles traités ou non.
- **`/blog`, `/page`** — perfs brutes d'un site ou d'une URL, sans notion de
  refresh.

Les deux premières peuvent diverger sans qu'aucune soit fausse : elles ne
portent pas sur le même périmètre ni sur le même ancrage de dates. **Quand les
deux lectures circulent, dire laquelle on cite.**
