---
description: Refresh batch depuis Google Sheets (toutes les URLs d'une action donnée pour un blog).
argument-hint: --action <PARTIAL_REFRESH|FULL_REFRESH|REFRESH_TITLES> --site <site-slug> [--limit N]
allowed-tools: Bash(python3 content_writer.py batch refresh:*), Bash(python3 content_writer.py plan init:*), Bash(python3 content_writer.py plan check:*), Bash(python3 content_writer.py finalize:*), Task, Read, Write, WebSearch, WebFetch, Skill
---

Lance un refresh batch. Le `--spreadsheet-id` est repris de `.env` si absent.

> 🚫 **Règle non négociable — blacklist AVANT tout fetch web.** Lire
> `.claude/skills/recherche-sources/references/blacklisted-domains.md` **une fois en
> début de batch**, avant le premier WebFetch/WebSearch, puis **re-vérifier au début
> de chaque article** de la boucle (relire ou re-résumer la liste) : la contrainte
> ne doit jamais sortir de la mémoire de travail entre deux itérations. Un domaine
> blacklisté n'est jamais fetché ni retenu comme source. Exceptions (Règle d'Or,
> article avis dont le sujet EST la plateforme) : voir le fichier blacklist.

## Étape 1 — Préparation en série (CLI `cw`)

```bash
python3 content_writer.py batch refresh $ARGUMENTS
```

`cw batch refresh` lit les URLs à traiter dans le **Google Sheet** (lignes du blog
dont l'action correspond), puis prépare le contexte de chacune : **récupération du
`post_content` de l'article dans WordPress via la REST API** (`WordPressAPIClient`,
si `wp_api_config` présent ; fallback scraping de la page publique seulement quand
la REST est bloquée) → audit GSC/SERP/PAA/intent → décision de stratégie →
`generation_prompt.txt`. C'est l'étape 1 de `/refresh`, en série. Noter pour
chaque URL : `context_dir`, `Strategy`, `Mot-clé`, `YTG guide`, `Assets avant`,
chemins `Output HTML`/`Output JSON` (et `Type: avis|versus` pour enseigna).

Les URLs en `NO_ACTION`, `BLOCKED_QUALITY_ISSUES`, `ERROR` ou
`REDIRECT_301_SUGGESTED` sortent du lot : les rapporter, rien à générer.

## Étape 2 — Boucle par article (identique à /refresh, étapes 2 → 4)

La suite n'est **pas** batchable : dérouler la chaîne complète **article par
article**, dans la session principale pour les étapes déterministes, via le
subagent **content-generator** (abonnement Max, jamais l'API payante) pour la
rédaction. Pour chaque URL préparée :

1. **Sources (brief E-E-A-T)** — invoquer la skill **`recherche-sources`** sur le
   sujet/URL. Sans ce brief, `eeat_sources` serait inventé par le LLM.

2. **Plan optimisé SEO (obligatoire, comme en /refresh étape 2bis)** :

   ```bash
   python3 content_writer.py plan init <url> --site <site-slug>
   ```

   puis invoquer la skill **`seo-outline`** pour remplir `content_plan.md`
   (mapping PAA→sections, placement des preuves, gap top 10), et valider :

   ```bash
   python3 content_writer.py plan check <url> --site <site-slug>
   ```

   `OK` → générer ; `A_CORRIGER` → corriger le plan puis relancer `plan check`.
   Ne **jamais** générer sur un plan non validé — en batch encore plus qu'en
   unitaire, c'est le garde-fou avant de brûler les tokens de rédaction.

3. **Génération** — subagent **content-generator** via Task, avec
   `generation_prompt.txt`, le `content_plan.md` validé, le brief de sources,
   le `site_slug`, les chemins de sortie, la `Strategy` et les `Assets avant`
   (Règle d'Or : assets après ≥ avant). Le subagent écrit les fichiers,
   jamais de HTML dans le chat.

4. **Finalisation + QC sémantique YTG (SOSEO/DSEO)** :

   ```bash
   python3 content_writer.py finalize <url> --site <site-slug> --html-file <Output HTML> [--type <avis|versus>] [--keyword "<Mot-clé>"] [--guide-id <YTG guide>]
   ```

   Reporter le `Mot-clé` et le `YTG guide` de l'étape 1 dans
   `--keyword`/`--guide-id` : le QC score alors SOSEO/DSEO sur le bon guide et
   réutilise le guide sans le recréer. La cible n'est **pas uniforme** : elle
   dépend de la SERP de **chaque requête**. Règle (moyennes du guide YTG,
   `top3_soseo`/`top3_dseo` et `top10_soseo`/`top10_dseo`, récupérées au
   STEP 2.5 de l'étape 1) : **SOSEO de l'article > moyenne TOP 3 et TOP 10** ;
   **DSEO strictement < moyenne TOP 3 et TOP 10**. Verdict :
   - `OPTIMAL` → article terminé, maillage appliqué ;
   - `A_CORRIGER` → relancer le subagent avec les termes sous/sur-optimisés,
     puis re-`finalize` (cap 2-3 itérations) ;
   - `BLOQUE` → arrêt de **cet article** + alerte humaine, passer au suivant.

Ne pas paralléliser la génération : un article terminé (finalize + verdict YTG)
avant de passer au suivant.

## Étape 3 — Rapport de lot

Rapporter : nombre d'URLs traitées / écartées (et pourquoi), stratégie par URL,
verdict `plan check`, verdict YTG avec scores SOSEO/DSEO vs cible, verdict
assets (avant/après), et chemins de sortie (`sites/<site-slug>/outputs/`).
