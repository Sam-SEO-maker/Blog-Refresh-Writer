# CLAUDE.md — Orientation guide (Content Writer)

**Multi-site SEO refresh.** This file is an **orientation index**, not a manual:
it says *who you are*, *which sites exist*, *what the chain is*, and *which skill /
command to invoke*. The "how to write" lives in the skills (`.claude/skills/` cross-cutting +
`sites/<site-slug>/.claude/skills/` per site), loaded on demand.

**Version**: 4.1 (monthly impact report) · **Project**: Content Writer

---

## Role & Mission

You are **Claude**, the project's SEO refresh agent. You optimise **existing content**
from data signals (GSC + DataForSEO), preserving each site's editorial identity.
**Data-driven** decisions, never from intuition.

**Content generation = Claude Code subagent (Max subscription), never the paid API.**

## Golden Rule (absolute invariant)

**Never reduce the assets** (`assets_after ≥ assets_before`: images, tables, videos,
internal links — including links to competitors). Details + validation JSON: `refresh` skill.

## Multi-site architecture

Each site (any client: a Superprof country blog, `enseigna.fr`, a future client)
is grouped under **`sites/<site-slug>/`**:

```
sites/<site-slug>/
├── .claude/skills/        writing skills scoped to the site (native discovery)
├── prompts/
│   ├── site.md            tone, blacklist, WP format (master source, loaded)
│   ├── vs_concurrent.md   override for "versus" articles (enseigna.fr)
│   ├── reference.md       HTML example to imitate (superprof.fr-ressources)
│   └── blocks/            block annexes (enseigna.fr)
├── config/site.json       generation_skill/qc_skill, language, auth_mode, ytg…
├── linking_maps/          internal linking maps
└── outputs/               html/ csv/ acf/ metadata/ audit/ wp_backups/ …
```

> The `prompts/` files vary by site: only `site.md` is guaranteed.

> **`outputs/<site>/wp_backups/` is not a scratch folder — never purge it.**
> It now also holds `_publications.jsonl` (one line per successful push, the
> only source that dates *every* republication rather than the first) and
> `_modified_cache.json` (WordPress dates for manually republished articles,
> ~250 API calls not worth repaying).
> One file per article, written by `push_to_wp` on first publication, and the
> only durable trace of *when a refresh went live*: it is what `/impact` dates
> its cohorts on. WordPress `modified` cannot replace it (any later edit
> overwrites it — 69 of August 2026's 78 articles), nor can the Sheet's
> hand-typed "Date de refresh" column. `outputs/html/` can be purged freely;
> this one must be kept, or archived before any cleanup.

- **Catalog ≠ registry** (key distinction):
  - **Catalog** `_shared/config/superprof_sites_catalog.json` (6 ressources + 90 blogs) =
    the *menu* of onboardable sites, generated from GSC via `build_superprof_catalog.py`.
  - **Registry** `_shared/config/sites.json` = only the sites **actually materialised**
    (2 today), the only one read at runtime. **Gitignored** (local/generated); versioned =
    `sites.example.json` + catalog + Notion sync. Fed by `notion sync-sites`
    (Notion "config pays" → sites.json, one-way; the engine never reads Notion at runtime).
- **Path resolution**: `_shared/core/site_paths.py` (single point). `sites/` holds
  ONLY the sites being worked on; it grows on demand — never 90 folders.
- **Isolation per SEO Manager**: each country lead clones via **git sparse-checkout**
  (shared engine + their single `sites/<site-slug>/`); the other sites stay on GitHub, absent
  from disk. Onboarding walkthrough (English): `onboarding/` + `onboarding/scripts/setup_sparse.sh`.
- **Onboard a site**: `python3 content_writer.py site init <site-slug>` — scaffolds
  `sites/<site-slug>/` (config pre-filled from the catalog + prompts + outputs), adds
  the `sites.json` entry, and materialises the folder in the sparse-checkout (skipped on a
  full worktree). The editorial part (`site.md`, generation skill) is still to be written. `site list`
  browses the catalog.
- **Naming**: the site slug is **the domain as you type it** (`superprof.de`,
  `superprof.mx`, `enseigna.fr`). When one domain hosts two sites (blog + ressources,
  6 markets), the ressources site appends its real URL segment: `superprof.fr-ressources`,
  `superprof.es-apuntes`, `superprof.de-lernplattform`. Legacy slugs (`enseigna`,
  `superprof-ressources`, `es-es-ressources`…) are still accepted on input
  (`canonical_site_slug`, `_shared/core/constants.py`).
- **Per-site skills**: a site's own writing skills live under
  `sites/<site-slug>/.claude/skills/` (native scoped discovery, **already in place**);
  `edito-refresh`, `format-wordpress`, `source-research` are cross-cutting at the root.
  The site→skill mapping is **not hardcoded**: the subagent reads `generation_skill` /
  `qc_skill` from `site.json`.

**Override rule**: `Site > Strategy`. Prompt composition (`PromptComposer`) =
**strategy (`_shared/strategies/`) + site.md** (+ `vs_concurrent.md` for versus articles);
the other levels (base, category, template) are inactive.

## Workflow map (orientation — 1 line/step)

Identification (Sheet) → GSC → DataForSEO/SERP (+ YTG guide) → SERP/user intent →
Decision (engine) — *deterministic Python up to here* — then the **agent chain**:
Keyword → SERP reading → Sources → Outline → Writing → (finalize) → YTG QC →
Format → Internal linking → Sync.

> The *map* stays here. The *how-to* of each step is in the corresponding skill.

**Monthly loop, past publication**: `/impact` measures what the month's
refreshes produced (cohort per article, control group), and `/tab-perf`
tracks a work list. Neither belongs to the chain above — they read GSC well
after the fact, on the 10th of the following month for `/impact`.

> **The two are now both year-over-year, and can still conclude in opposite
> directions** — they don't read the same object. `/impact` compares each
> republished article to itself, anchored on *that article's own*
> republication date: the N days after it against the N days after the same
> calendar date a year earlier, over the **treated lot only**. `/tab-perf`
> compares a **whole scope** (a full Sheet tab or Notion base, worked or not)
> over a **calendar month** against the same month a year earlier, with no
> per-article anchor. An article republished late in the month carries its
> full weight here while barely registering in a calendar reading, and the
> tab mixes reworked articles with untouched ones — so the two totals can
> diverge sharply on the same URLs without either being wrong. `/impact`
> answers "did the work produce something", `/tab-perf` "how does this work
> list read over the calendar month". Both can be right at once — **when both
> readings circulate, say which one you are citing**. A report that cannot be
> regenerated by either command has no standing against them: the August 2026
> `gsc_tab_delta_medium_potential_*` came from a throwaway script and its
> −16,8 % contradicted nothing.

## Index — Slash commands (`.claude/commands/`)

| Command | Role |
|---|---|
| `/refresh <url> --site <site-slug> --main-keyword ""` | Full refresh: audit → decision → source research → generation → `cw finalize` |
| `/batch --site <site-slug> --tab "<tab-name>"` | Batch refresh from Google Sheets. Always pass `--tab` (name **exactly as declared** in `sheets.tabs` of the site config): the tab layout — status column, header rows — differs from one tab to the next and is read from the config, never assumed. Rows with a terminal status (`Publié`, `Redirection 301`, `Cannibalisation de KW`) are skipped, empty statuses are processed. Defaults: `--action FULL_REFRESH`, `--limit 50` (`--limit 0` = whole tab), spreadsheet id from the site config. `--rows 140-180` restricts the lot to a slice of the tab, using the row numbers Google Sheets displays (headers included); it filters before `--limit`, keeps only the rows that are also `A faire`, and requires `--tab`. Without `--tab`, only `enseigna.fr` has a default flow (Avis/Versus) |
| `/new-blogpost --site <site-slug> (--tab "<tab-name>" \| <url> --main-keyword "")` | **Create** an article that does not exist yet (no WP post behind the URL). Backlog read from the creation tab (`A ajouter` on enseigna.fr: url, main_keyword, title, H1 pre-filled) via `cw batch new-list`, or a single URL. Same agent chain as `/refresh`, prepared with `cw refresh --new` (no fetch, zero assets baseline, FULL_REFRESH). Deliverables stay local (html + acf + csv): WP cannot create a post through `push`, publication is manual |
| `/sheets-update --site <site-slug> --tab "<tab-name>" (--rows 201-210 \| --limit N)` | **Order** the refresh articles in Notion from a Sheet tab, before any writing: one row per URL with its `Main KW` read from the Sheet, `Type of article` = Refresh and the Country relation. Replaces the manual paste, which lands a batch of URLs in an arbitrary order: Notion dates pages to the second, so rows created in one burst share a `createdTime` and the orders view (no declared sort) shuffles them — the command spaces the creations so the batch reads in the Sheet's order. Matching is by normalised URL, so a URL already ordered is reported rather than duplicated (`--fix-keywords` corrects its keyword). Dry-run by default, writes only with `--apply`. Requires the **source** orders database to be shared with the `NOTION_TOKEN` integration, never the linked view embedded in the order page (the API rejects linked databases) |
| `/audit serp <url> --main-keyword ""` | Targeted SERP audit (PAA, SERP features, top 10). Always pass `--main-keyword`: without it the keyword is derived from the URL slug, so any typo or shorthand in the slug is queried verbatim and the SERP answers a keyword nobody searches |
| `/plan-check <url> --site <site-slug>` | Validate the editorial outline (`content_plan.md`) against the SEO invariants — heading hierarchy, PAA coverage, proof placement. Deterministic (no generation). Verdict OK / NEEDS_FIX before writing. Scaffold it first with `plan init` (CLI lays the file + injects signals; the agent fills the outline via the `seo-outline` skill) |
| `/site-status --site <site-slug>` | GSC SEO status of a site (→ Sheet) |
| `/blog --site <site-slug>` | SEO performance of a blog via GSC MCP: totals + top KW (chat summary) |
| `/page <url>` | SEO performance of a specific URL via GSC MCP (site inferred from the URL) |
| `/tab-perf --site <site-slug> (--tab "<tab-name>" \| --source notion)` | Refresh monitoring of a whole work list (not a single URL): GSC gains/losses per URL vs the previous window, grouped by editorial status — HTML report + JSON dump. Two sources: a Sheet tab (default) or the site's Notion publications base (`--source notion`, declared in `notion.publications` of `site.json`), which adds by-category and by-publication-year aggregates |
| `/impact --site <site-slug> --month YYYY-MM` | Impact of a month's refreshes, **each article compared to itself** on its own window (the N days after its republication vs the N days before, equal length), seasonality deducted by a control group (the rest of the site on the same dates). Distinct from `/tab-perf`, which measures a *scope* over a calendar month: on an article republished on the 25th, a calendar reading mostly judges the 24 days *before* the refresh. **Run on the 10th of the following month, never the 1st** — 7 days of minimum hindsight plus 3 of GSC latency, so a run on Sept 1st covered only 44 of August 2026's 78 articles; the command refuses under 90 % coverage and gives the date the lot is complete (`--partial` forces it). `--source notion` swaps that cascade for the site's Notion publications database (its "Planing de refresh" column, never "Date de publication" which dates creation), completed by the article sitemap's `lastmod` and bounded to the URLs the base declares online: the only mode that works on a site publishing by hand, where `wp_backups/` stays empty (enseigna.fr). Otherwise republication dates follow a three-rank cascade: the `_publications.jsonl` journal (every push), then the `{id}_before.json` mtimes (first push only), then — for articles the Sheet declares published but that no local trace covers — WordPress `modified`. That third rank exists because a manual republication from WordPress leaves no local trace at all: 58 such articles were missing from the August 2026 report, 43 % of the month, while it displayed "100 % coverage" (it counted *traced* articles, not *republished* ones). Each article carries a `date_source` field so the two are never presented as equivalent. The deliverable has three tiers: the verdict (with the **hindsight gradient** — on August 2026, 93 % of articles measured at 26-30 days are up against 54 % of those at 7-15 days, so most apparent failures are young measurements, not editorial ones), then one card per article, the 20 strongest rises and the 20 strongest falls first, then the rest of the lot: the 5 queries that weigh most (before or after, each tagged gained / held / lost), a written reading of where the volume comes from, and a **diagnosis** per URL (new keywords / ranking improved / query loss / decline on the same queries). No cell is ever truncated. `--pdf` writes all of it (~30 pages); `--pdf-annex` appends the tabular index of the lot; `--render-only` re-renders from the month's JSON without any GSC call |

**Publication = `finalize`, jamais avant validation.** Un article n'atteint
WordPress qu'une fois la chaîne `finalize` passée (save → assets → QC YTG →
maillage) sur un verdict `OPTIMAL`. `cw push <url> --site <site-slug>` (CLI, pas
de slash) **republie** un article déjà validé sans rejouer la chaîne — utile après
une correction manuelle, où relancer `finalize` reconsommerait le quota YTG et
réécrirait des fichiers édités à la main. Il ne contourne pas la garde : il relit
le verdict que `finalize` a persisté, refuse un article jamais validé, refuse un
`BLOCKED` même forcé, et vérifie que le verdict porte bien sur le fichier poussé.

**Un push réussi pose le statut `Rédigé` dans la Sheet** (`mark_published`,
appelé par `finalize` comme par `push`). `Rédigé` et non `Publié` : le push met
le contenu en ligne, la validation éditoriale reste à faire à la main. Sans cette
écriture, la ligne restait `A faire` et `batch refresh --rows` reproposait
indéfiniment des URLs déjà traitées — un lot entier a été re-préparé pour rien,
guides YTG et audits SERP reconsommés. L'écriture ne peut pas faire échouer une
publication : l'article est déjà en ligne quand elle a lieu, donc une Sheet
injoignable n'affiche qu'un avertissement. `cw status <url> "<statut>"` reste
disponible pour corriger une ligne à la main.

Actual CLI (the commands wrap it): `python3 content_writer.py <group> <cmd>`.
Up-to-date list of groups/commands: `python3 content_writer.py --help` (and
`… <group> --help`), auto-generated by Click — source of truth.

> Onboarding (no slash, CLI only): `site list` (catalog) and
> `site init <site-slug>` (scaffold site + sites.json + sparse-checkout). See `onboarding/`.

## Index — Skills (`.claude/skills/`)

| Skill | Scope | When to invoke |
|---|---|---|
| `edito-refresh` | root (cross-cutting) | SEO/GEO/E-E-A-T ranking rules, applied to every article |
| `seo-outline` | root (cross-cutting) | build the SEO/GEO editorial outline (content_plan.md) before writing — /refresh step 2bis |
| `format-wordpress` | root (cross-cutting) | cross-cutting HTML/WP rules (accents, dash, anchors, lists) |
| `source-research <topic\|url>` | root (cross-cutting) | document a topic with verified sources (E-E-A-T brief) |
| `impact-report` | root (cross-cutting) | monthly refresh impact report: measurement method, sections to cover, how to write the headline without overclaiming — invoked by `/impact` |
| `generate-enseigna-avis` | `sites/enseigna.fr/` | write an Enseigna review article (ACF JSON, verdict at the end) |
| `sp-ressources-gutenberg` | `sites/superprof.fr-ressources/` | write a Superprof Ressources article (in-house Gutenberg, 5 blocks) |
| `qc-sp-ressources` | `sites/superprof.fr-ressources/` | post-generation QC checklist for Superprof Ressources |

> The business skills are **scoped per site** (`sites/<site-slug>/.claude/skills/`) and
> resolved via `generation_skill`/`qc_skill` from the config. Cross-cutting at the root:
> `edito-refresh`, `format-wordpress`, `source-research`. The `refresh` orchestrator is a
> **slash command** (`.claude/commands/refresh.md`), not a skill — see the table above.

## Index — Agent chain (`.claude/agents/`)

Past the deterministic audit, **the analysis stays in the main session and only
the execution is delegated**, to 4 specialised agents. All run under the Max
subscription, never the paid API, and none returns HTML in the chat.

Inline (no agent): keyword check, SERP/PAA reading, editorial outline
(`content_plan.md` looped on `plan check` until `OK`). These rest on signals
already fetched at step 1 and on the conversation's own context; delegating them
would mean serialising your analysis to disk for another agent to re-read, which
loses information at every hop and buys no parallelism (the outline waits on the
brief anyway).

| # | Agent | Trade | Web |
|---|---|---|---|
| 1 | `source-researcher` | verified sources → `sources_brief.md` | **yes** |
| 2 | `content-generator` | the substance + text-bearing blocks → HTML | no |
| 3 | `ytg-qc` | semantic density SOSEO/DSEO (after `finalize`) | no |
| 4 | `gutenberg-formatter` | format compliance, **last pass** | no |

What justifies an agent is a **capability boundary**, not a change of subject:

- **Only link 1 reaches the web.** Links 2-4 physically cannot fetch a source,
  so a gap in the brief stays visible instead of being invented mid-writing —
  a tool-level guarantee, not a rule the model must remember. This is why source
  research stays delegated while the analysis around it does not.
- **The writer burns the tokens.** Generation is the one step whose context
  would otherwise swamp the session.
- **Format closes the chain.** `finalize` creates the `.gutenberg.html`, then
  `ytg-qc` rewords *inside* the blocks; the formatter runs last, on the file
  that actually ships.
- **Each link is a restart point.** A failed article restarts at the failed
  link, not from the audit.

**Neither the audit nor the SERP fetch is an agent**: they are
`cw refresh` / `cw batch refresh`, deterministic Python (`SERPAnalyzer.analyze()`
calls DataForSEO once per URL, and `audit_data.json` carries the whole `serp`
block: PAA, top 10, features, dominant format, position). You *read* that file
and never re-query — re-fetching would double the API cost per URL and
desynchronise the analysed signals from those that drove the strategy decision.
An LLM in the fetch itself would replace tested code on the very data that
drives every downstream decision.

**The YTG guide is keyed on the root `main_keyword`** (`provided_keyword or
GSC`), never on `performance.main_keyword`. Reading the GSC field alone made a
page with no traffic — exactly the pages worth refreshing — fall through to the
slug and build a guide on the wrong sense of the word.

**The `context_dir` is shared between the CLI and the agents.** Re-running an
audit archives only the artefacts the CLI regenerates
(`RefreshOrchestrator._CLI_ARTIFACTS`); the agents' briefs stay in place, since
nothing else would rewrite them and a missing brief is indistinguishable from
a brief that never existed.

**Parallelism.** The unit of speed is the **article**, not the step: within an
article the steps are a data dependency chain (the outline needs the brief,
the writing needs the outline), so splitting it buys isolation, not wall-clock.
Articles are independent — `batch refresh --parallel N` (1-8) prepares N at
once. The YTG quota (15 req/min) is held by a cross-process counter
(`_shared/core/cross_process_rate_limit.py`); without it, N concurrent
processes would each start from a blank counter and blow the quota.

## Where to find the "how"

- **Writing / format / forbidden things** → `format-wordpress` skill.
- **SEO / GEO / E-E-A-T** (ranking, cross-cutting) → `edito-refresh` skill
  (`SKILL.md` + `references/{geo-strategies,eeat-framework,semantic-density}.md`).
- **Building the outline before writing** (PAA→sections, proof placement, heading
  hierarchy invariants) → `seo-outline` skill (`/refresh` step 2bis → `content_plan.md`).
- **Formats & metadata, refresh template** → `format-wordpress` skill
  (the refresh delta lives in `_shared/strategies/`).
- **Site-specific rules** → `sites/<site-slug>/prompts/site.md`.
- **Measuring what a month's work produced** (windows, date sources, control
  group, headline wording) → `impact-report` skill (`/impact`, run on the 10th).
- **Writing strategies** → `_shared/strategies/` (full_refresh, semantic_reorientation,
  format_adaptation, title_optimization; dispatch via `_shared/config/prompts_dispatch.json`).
  They carry only the strategy *delta*; the cross-cutting editorial rules live
  in the `edito-refresh` skill.

## 3 Pillars

1. **Preservation**: never reduce the assets (Golden Rule).
2. **Data-driven**: GSC + DataForSEO decisions, no intuition.
3. **Multi-site**: respect each site's editorial identity, flat registry.
