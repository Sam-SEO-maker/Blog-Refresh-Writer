# PoC GSC API-directe vs MCP `gsc-remote` — résultats (Phase 6c)

**Date** : 2026-07-15
**Objectif** : valider que le MCP `gsc-remote` peut se substituer à l'accès GSC
service-account (`GSCAnalyzer`) avant la bascule progressive méthode par méthode.
Aucune modification du pipeline de décision : PoC hors chemin critique.

## Protocole

Même requête « 30 jours, dimension `query`, filtre `page=URL` » exécutée via :
- **API directe** : `scripts/audit/gsc_mcp_poc.py` (réplique le corps de requête de
  `GSCAnalyzer._fetch_performance_direct`, service account local).
- **MCP** : tool `mcp__gsc-remote__get_search_by_page_query(site, page, days=30)`.

- Propriété : `https://www.superprof.fr/ressources/`
- URL testée : `.../histoire/histoire-tous-niveaux/chef-royaume-republique.html`
  (3851 clics / 37954 impressions sur 30j — page à fort trafic).

## Résultat : sources identiques là où elles se recouvrent

| Métrique | API directe | MCP |
|---|---|---|
| Top keyword | `roi de france` | `roi de france` (idem) |
| Clics (20 kw partagés) | 2394 | 2394 (**identique**) |
| Impressions (20 kw partagés) | 13395 | 13395 (**identique**) |
| Mismatches par requête (top 20) | — | **0** |

- **0 divergence** de clics/impressions sur les 20 mots-clés partagés.
- Aucun mot-clé MCP absent de l'API directe.

## Seule différence : profondeur d'affichage (pas de la donnée)

- API directe : `rowLimit=50` → 50 lignes (2567 clics / 14724 impr au total).
- MCP `get_search_by_page_query` : **plafonne l'affichage à ~20 lignes**.

→ Ce n'est PAS un écart de données mais une limite de rendu du tool MCP.
**Point à porter dans la migration** : pour les usages qui ont besoin de >20
requêtes (`fetch_top_keywords_12m`, `limit=20` OK ; au-delà, vérifier la
pagination/limite du tool MCP avant de basculer cette méthode).

## ⚠️ Contrainte décisive : enseigna N'EST PAS sur le MCP

`mcp__gsc-remote__list_properties` ne renvoie **que des propriétés `superprof.*`**
(200+). **`enseigna.fr` en est absent.** Le MCP `gsc-remote` (serveur
`superprof.cloud`) ne couvre donc PAS enseigna.

Conséquence : **le service account reste la seule voie GSC pour enseigna** tant
qu'enseigna n'est pas ajouté au serveur MCP. Supprimer le SA couperait GSC pour
enseigna → **on NE supprime PAS le SA**.

## Décision d'architecture (2026-07-15) : bascule par capacité, PAS par suppression

Le SA n'est **pas** obligatoire à supprimer (la suppression était un objectif de
*distribution*, pas une contrainte technique). Le conserver ne crée **aucun
conflit** : SA et MCP sont deux canaux de lecture indépendants sur des propriétés
**disjointes** (MCP = superprof.* ; SA = enseigna + repli superprof), et le choix
est déjà routé par tenant via `auth_mode` (Phase 4bis-B) au point unique
`_shared/core/google_auth.py::get_credentials`. Le SA n'alourdit pas le repo :
**aucune clé n'est dans l'arbre git** (JSON hors repo, `GOOGLE_SA_PATH`
= `~/.credentials/...`) ; seule reste la lib `google-api-python-client`, de toute
façon nécessaire à Google Sheets.

→ Cible révisée : `GSCAnalyzer` devient un **adaptateur qui route par propriété** :
MCP `gsc-remote` quand la propriété y est exposée (superprof.*), **SA en repli**
(enseigna, et sécurité si le MCP est indisponible). Le SA est **rétrogradé au rang
de fallback permanent**, pas supprimé.

## Prochaine étape de bascule (révisée)

1. ✅ PoC comparatif (cette note) — **fait**.
2. ✅ Décision d'archi : SA conservé en fallback, routage par propriété — **fait** (cette note).
3. ✅ Routage MCP/SA installé dans `GSCAnalyzer` (`data_source`/`uses_mcp`,
   `gsc_source_for_property`). Garantie **enseigna ⇒ toujours SA** — **fait**.
4. ✅ **Fetch réel via MCP câblé** (`fetch_top_keywords_12m` + `fetch_top_keyword_12m`).
   Découverte : **le MCP EST appelable depuis Python** — le serveur
   `http://mcp.superprof.cloud:3001/sse` parle MCP sur SSE+JSON-RPC, joignable
   sans auth (`supergateway` n'est qu'un pont pour Claude Code, pas une barrière).
   Client pur `requests` : `scripts/audit/gsc_mcp_client.py` (aucune dépendance
   nouvelle). Parité live vérifiée : **0 mismatch** vs SA sur 20 kw (30j et 12m).
   Fallback SA sur toute `GSCMCPError`. **Row-limit** : `limit>20` bypasse le MCP
   (retombe sur le SA qui pagine à 50) pour ne pas tronquer silencieusement.
5. ~~Suppression du service account~~ → **SA conservé en fallback permanent** tant
   qu'enseigna (et tout tenant hors MCP) n'est pas exposé sur `gsc-remote`.

### `_fetch_performance_direct` : refactoré, PAS basculé (blocage row-limit)

Analysé et refactoré (row-acquisition isolée de l'agrégation, prêt pour MCP),
mais **volontairement laissé sur le SA**. Deux raisons distinctes :

1. **Totaux période courante** (`clicks_30d`/`impressions_30d`) = **somme sur
   TOUTES les requêtes** de l'URL, alimente directement le moteur de décision et
   le calcul de tendance. Le MCP plafonne à ~20 requêtes → sous-compte les URLs à
   longue traîne. Constaté sur l'URL test : **MCP 2394 vs SA 2567 clics** (−7%),
   tendance faussée (impr_trend −62% MCP vs −58% SA). Router la somme via MCP
   corromprait la détection de déclin. → **reste SA tant que le row-limit MCP
   n'est pas levé** (la structure est prête, il suffira de router `_fetch_current
   _period_rows`).
2. **Tendances** (`_calculate_trends_direct`) : baseline = **total par page** de la
   période N-1. `compare_search_periods` (dimensions=page) le fournit MAIS trie
   « top-N par variation de clics » → une page hors top-N n'a pas de baseline
   (tendance→0 silencieuse). Trop risqué pour le cœur décision. → **reste SA**.

Bilan : perf/tendances **inchangés (SA)**, mais refactoré proprement + blocage
documenté. Non-régression vérifiée (totaux 2567/14724 identiques).

### Précisions row-limit (mesures batch)

- **Usage réel** : le refresh d'une URL consomme ~20 kw catégorisés (quick_wins
  top5 + long_tail top10 + core top5) → tiennent dans les 20 lignes MCP. Le batch
  `keyword_discovery` n'extrait que le **main_keyword** (fallback DataForSEO).
- **main_keyword = max impressions → TOUJOURS dans le top-20** : parité MCP/SA
  5/5 URLs. Basculé via `fetch_main_keyword()` (méthode dédiée, routage MCP/SA),
  câblé dans `orchestrator.batch_keyword_discovery` (remplace
  `_fetch_performance_direct().main_keyword`, plus léger).
- **Le `TOTAL` du MCP n'est PAS le total par page** : mesuré, il ne somme que ses
  20 lignes affichées et sous-compte massivement (2394 vs 3851 clics réels ;
  impressions 45k vs 110k). Cause : GSC masque une grosse part du trafic en
  requêtes anonymisées hors top-N. → **Option "utiliser le TOTAL MCP pour les
  sommes" ÉCARTÉE.** `clicks_30d`/`impressions_30d` (dimension page) restent SA.
- **Latence** : MCP 1,44 s/appel ≈ SA 1,41 s/appel (mesuré). Batch 50 URLs ≈ 72 s
  dans les deux cas. Le MCP n'est ni gain ni perte ; le plafond de 20 ne gêne
  aucun usage réel (refresh ni batch). Optim future possible : réutiliser une
  session MCP pour N appels (économiser les handshakes) + paralléliser.
- **Bug corrigé** : le stream SSE sans charset tombait en latin-1 → accents FR
  cassés ("3ème"→"3Ã¨me"). Fix `r.encoding="utf-8"` dans le client + test dédié.

### Reste à évaluer
- `_detect_quick_wins_direct` : lecture par requête (top ~20 OK) — candidat MCP.
- `_check_indexation*` : tools MCP `check_indexing_issues`, `inspect_url_enhanced`.
- `clicks_30d`/`impressions_30d` (sommes déclin) : restent SA (dimension page non
  fournie par le MCP). À rouvrir seulement si un tool MCP "totaux par page" apparaît.

## Rejouer le PoC sur une autre URL

```
python -m scripts.audit.gsc_mcp_poc <gsc_property> <page_url> [days]
```
puis comparer à `mcp__gsc-remote__get_search_by_page_query(<property>, <page_url>, <days>)`.
