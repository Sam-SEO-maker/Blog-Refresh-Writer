# CLAUDE.md — Orientation guide (Content Writer)

**Multi-site SEO refresh.** This file is an **orientation index**, not a manual:
it says *who you are*, *which sites exist*, *what the chain is*, and *which skill /
command to invoke*. The "how to write" lives in the skills (`.claude/skills/` cross-cutting +
`sites/<site-slug>/.claude/skills/` per site), loaded on demand.

**Version**: 4.0 (monorepo overhaul) · **Project**: Content Writer

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
└── outputs/               html/ csv/ acf/ metadata/ audit/ …
```

> The `prompts/` files vary by site: only `site.md` is guaranteed.

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

## Index — Slash commands (`.claude/commands/`)

| Command | Role |
|---|---|
| `/refresh <url> --site <site-slug> --main-keyword ""` | Full refresh: audit → decision → source research → generation → `cw finalize` |
| `/batch --site <site-slug> --tab "<tab-name>"` | Batch refresh from Google Sheets. Always pass `--tab` (name **exactly as declared** in `sheets.tabs` of the site config): the tab layout — status column, header rows — differs from one tab to the next and is read from the config, never assumed. Rows with a terminal status (`Publié`, `Redirection 301`, `Cannibalisation de KW`) are skipped, empty statuses are processed. Defaults: `--action FULL_REFRESH`, `--limit 50` (`--limit 0` = whole tab), spreadsheet id from the site config. Without `--tab`, only `enseigna.fr` has a default flow (Avis/Versus) |
| `/audit serp <url> --main-keyword ""` | Targeted SERP audit (PAA, SERP features, top 10). Always pass `--main-keyword`: without it the keyword is derived from the URL slug, so any typo or shorthand in the slug is queried verbatim and the SERP answers a keyword nobody searches |
| `/plan-check <url> --site <site-slug>` | Validate the editorial outline (`content_plan.md`) against the SEO invariants — heading hierarchy, PAA coverage, proof placement. Deterministic (no generation). Verdict OK / NEEDS_FIX before writing. Scaffold it first with `plan init` (CLI lays the file + injects signals; the agent fills the outline via the `seo-outline` skill) |
| `/site-status --site <site-slug>` | GSC SEO status of a site (→ Sheet) |
| `/blog --site <site-slug>` | SEO performance of a blog via GSC MCP: totals + top KW (chat summary) |
| `/page <url>` | SEO performance of a specific URL via GSC MCP (site inferred from the URL) |
| `/tab-perf --site <site-slug> (--tab "<tab-name>" \| --source notion)` | Refresh monitoring of a whole work list (not a single URL): GSC gains/losses per URL vs the previous window, grouped by editorial status — HTML report + JSON dump. Two sources: a Sheet tab (default) or the site's Notion publications base (`--source notion`, declared in `notion.publications` of `site.json`), which adds by-category and by-publication-year aggregates |

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
- **Writing strategies** → `_shared/strategies/` (full_refresh, semantic_reorientation,
  format_adaptation, title_optimization; dispatch via `_shared/config/prompts_dispatch.json`).
  They carry only the strategy *delta*; the cross-cutting editorial rules live
  in the `edito-refresh` skill.

## 3 Pillars

1. **Preservation**: never reduce the assets (Golden Rule).
2. **Data-driven**: GSC + DataForSEO decisions, no intuition.
3. **Multi-site**: respect each site's editorial identity, flat registry.
