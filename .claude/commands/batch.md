---
description: Batch refresh from Google Sheets (all URLs of a given action for a blog), optionally preparing N articles in parallel.
argument-hint: --site <site-slug> --tab "<tab name>" [--action <FULL_REFRESH|PARTIAL_REFRESH|REFRESH_TITLES>] [--limit N] [--parallel N]
allowed-tools: Bash(python3 content_writer.py batch refresh:*), Bash(python3 content_writer.py plan init:*), Bash(python3 content_writer.py plan check:*), Bash(python3 content_writer.py finalize:*), Bash(python3 content_writer.py ytg qc:*), Task, Read, Write, WebSearch, WebFetch, Skill
---

Runs a batch refresh. Only `--site` and `--tab` are needed: the spreadsheet id
comes from the site config, `--action` defaults to `FULL_REFRESH` and `--limit`
to 50.

> 🚫 **Non-negotiable rule - blacklist BEFORE any web fetch.** Read
> `.claude/skills/source-research/references/blacklisted-domains.md` **once at the
> start of the batch**, before the first WebFetch/WebSearch, then **re-check at the
> start of each article** in the loop (re-read or re-summarise the list): the
> constraint must never leave working memory between two iterations. A blacklisted
> domain is never fetched nor kept as a source. Exceptions (Golden Rule, review
> article whose subject IS the platform): see the blacklist file.

## Step 1 - Serial preparation (`cw` CLI)

```bash
python3 content_writer.py batch refresh $ARGUMENTS
```

### Which tab is targeted

**`--tab` selects the work tab explicitly** — always pass it. It takes the tab
name **exactly as declared in `sheets.tabs` of the site config**
(`sites/<site-slug>/config/site.json`), including any emoji the tab name carries.
Everything else has a default, so the usual call is just site + tab:

```bash
python3 content_writer.py batch refresh \
  --site superprof.fr-ressources --tab "Medium Potential"
```

Defaults: `--action FULL_REFRESH`, `--limit 50`, and `--spreadsheet-id` read
from the site config. `--limit 0` lifts the cap — the whole tab gets prepared,
which on a large tab means hours of WP/GSC/SERP/YTG calls paid upfront.

The layout is read from that tab's config entry (`col_url`, `col_keyword`,
`col_status`, `header_row`) — never assumed. Tabs do **not** share a geometry:
`New Growing List` has its status in column F with 1 header row, `🍼 Medium
Potential` in column I with 2. An undeclared `--tab` fails loudly and lists the
declared tabs, rather than silently returning 0 URL.

Rows whose status is **terminal** are skipped: `Publié`, `Redirection 301`,
`Cannibalisation de KW`. Everything else is processed, **including rows with an
empty status** (a freshly opened tab has no status filled in yet).

Without `--tab`, only `enseigna.fr` has a default flow (its Avis/Versus tabs);
any other site errors out asking for `--tab`.

`cw batch refresh` reads the URLs to process from the **Google Sheet** (the tab's
rows, filtered as above), then prepares the context for each one: **fetching the
article's `post_content` from WordPress via the REST API** (`WordPressAPIClient`,
when `wp_api_config` is present; fallback to scraping the public page only when
the REST API is blocked) → GSC/SERP/PAA/intent audit → strategy decision →
`generation_prompt.txt`. This is step 1 of `/refresh`, run serially. For each
URL, note: `context_dir`, `Strategy`, `Keyword` (main keyword), `YTG guide`,
`Assets before`, the `Output HTML`/`Output JSON` paths (and
`Type: avis|versus` for enseigna).

URLs in `NO_ACTION`, `BLOCKED_QUALITY_ISSUES`, `ERROR` or
`REDIRECT_301_SUGGESTED` drop out of the batch: report them, nothing to generate.

## Step 2 - Per-article chain (same as /refresh, steps 2 → 4)

Each article goes through the same chain as `/refresh`: **the analysis stays in
the main session, only the execution is delegated** to 4 specialised agents,
each with its own tools and trade, each consuming the previous one's output:

| # | Agent | Trade | Web access |
|---|---|---|---|
| 1 | `source-researcher` | verified sources → `sources_brief.md` | **yes** (only one) |
| 2 | `content-generator` | the substance + text-bearing blocks → HTML | no |
| 3 | `ytg-qc` | semantic density SOSEO/DSEO (after `finalize`) | no |
| 4 | `gutenberg-formatter` | format compliance, **last pass** | no |

Steps 1 and 2 below stay **in the main session**: they read signals already
fetched at step 1 and need the conversation's context, not an isolated process.
Delegating them would serialise your own analysis to disk for another agent to
re-read, at a cost per URL multiplied by the size of the batch.

For each prepared URL:

1. **Keyword check** (inline) - read the `Keyword:` printed at step 1 **with its
   source**. `cli`/`notion`/`sheet`/`gsc` → take it as is; `none` → article
   blocked. Only the `slug` fallback deserves a look: check spelling, in-house
   shorthand, a leftover year or category segment.

   > The `slug` fallback is the one nobody questions: a typo or an in-house
   > shorthand goes verbatim to DataForSEO and the whole chain answers a query
   > nobody types — silently, once per URL. Fix it before the SERP call and the
   > YTG guide, which are both keyed on it.

2. **SERP reading** (inline) - read `audit_data.json` yourself: its `serp` block
   carries `paa_questions`, `top_10_results`, `features`, `dominant_format` and
   `our_position`, **already fetched at step 1, never re-queried**. Rank the
   questions by editorial value, name the ones you drop and why, and state the
   competitive gap.

   > Re-querying DataForSEO here would double the SERP cost of the batch (50
   > URLs = 50 duplicate calls) and desynchronise the analysed signals from the
   > ones that drove the strategy decision.

3. **Sources** - `source-researcher` agent (URL/topic, keyword, `context_dir`,
   `site_slug`) → `sources_brief.md`. Only link that can reach the web: what it
   does not find, no later link can invent.

4. **Outline** (inline) - run `plan init`, fill the outline from the SERP
   reading + sources brief using the `seo-outline` skill, and loop on
   `plan check` **until `OK`**. Never generate on an unvalidated plan — in batch
   even more than on a single URL, this is the gate before burning writing
   tokens.

5. **Writing** - `content-generator` agent, with `generation_prompt.txt`, the
   validated `content_plan.md`, the sources brief, the `site_slug`, the output
   paths, the `Strategy` and the assets-before count (Golden Rule: assets after
   ≥ before). It writes the files, never HTML in the chat.

6. **Finalisation + semantic QC**:

   ```bash
   python3 content_writer.py finalize <url> --site <site-slug> --html-file <Output HTML> [--type <avis|versus>] [--main-keyword "<keyword>"] [--guide-id <YTG guide>]
   ```

   Carry over the **arbitrated** keyword and the `YTG guide` into
   `--main-keyword`/`--guide-id`: the QC then scores against the right guide and
   reuses it instead of recreating it (credit savings). The target is **not
   uniform** — it depends on the SERP of **each query**: **article SOSEO > TOP 3
   and TOP 10 averages**, **DSEO strictly < both**. Verdict:
   - `OPTIMAL` → article done, internal linking applied;
   - `NEEDS_FIX` → `ytg-qc` agent fixes in place and re-checks (cap 2-3);
   - `BLOCKED` → stop **this article** + human alert, move on to the next one.

7. **Format** - `gutenberg-formatter` agent on the **`.gutenberg.html`** (the
   file that ships), `site_slug`: loads the site's `qc_skill` +
   `format-wordpress` and fixes encoding in place (numeric count-up, no orphan
   H3, `?` on questions, FAQ emoji, AdvGB blocks with UUID on a single line, no
   em dash). Substance is never rewritten — what it cannot fix without touching
   the content, it reports.

   > Last on purpose: `finalize` creates the `.gutenberg.html` and `ytg-qc` then
   > rewords inside the blocks, which can break the single-line AdvGB
   > constraint. Nothing touches the file after this agent.

## Parallel mode (`--parallel N`)

By default the batch stays **sequential**: one article finished before the next
starts. Nothing changes unless you ask for it.

```bash
python3 content_writer.py batch refresh \
  --site superprof.fr-ressources --tab "Medium Potential" --parallel 3
```

**Phase A - concurrent preparation (CLI, N articles in flight, 1-8).** WP fetch,
GSC audit, SERP/PAA, YTG guide, decision and `generation_prompt.txt` run for N
articles at once. This phase is network-bound, so the gain is roughly
proportional to N. It writes a work plan to
`_shared/context/parallel_batch_plan.json` listing, per article: `context_dir`,
`output_html`, `output_json`, `strategy`, `main_keyword`, `ytg_guide_id`,
`article_type`, `assets_before` — plus the `SKIPPED`/`FAILED` ones with their
reason. A failed article never sinks the batch.

**Phase B - the agent chain, one per article.** Read the plan and run the 7-link
chain above for each `PREPARED` entry. Several **articles** may be in flight at
once (their `context_dir` is keyed by URL slug, so they never collide), but
**within one article the chain stays ordered** — that order is a data
dependency, not a convention: the SERP brief needs the arbitrated keyword, the
outline needs the briefs, the writing needs the outline, the QC needs the
finished text, the formatter needs the shipped file.

> **Why the article, and not the step, is the unit of *speed*.** Splitting one
> article across successive links buys **isolation and restartability**, not
> wall-clock: each link waits on the previous one, so the duration is the same
> sum. Articles, on the other hand, are genuinely independent — that is where
> time is won.

> **A blocked keyword saves a whole article's cost.** When the step-1 keyword
> check leaves you with nothing usable (source `none`, or a slug that reads like
> no query at all), drop that URL from the batch and report it: every step after
> it would have been paid for an audit of the wrong query.

> **YTG quota.** The API caps at 15 req/min. The limiter used to count per
> process, which was fine while a single `cw finalize` ran at a time; with N in
> flight, each process would start from a blank counter and blow the quota. The
> counter is now shared across processes
> (`_shared/core/cross_process_rate_limit.py`), so `--parallel` cannot exceed
> the quota — which is also why N is capped at 8: past that, DataForSEO/GSC
> saturate without extra throughput.

## Step 3 - Batch report

Report: number of URLs processed / discarded (and why), strategy per URL,
`plan check` verdict, YTG verdict with SOSEO/DSEO scores vs target, assets
verdict (before/after), and output paths (`sites/<site-slug>/outputs/`).
