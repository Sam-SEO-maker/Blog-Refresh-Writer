---
description: Full SEO refresh of a URL (WP REST fetch/scrape → GSC/SERP/PAA/intent → decision → SERP reading and outline inline → then a 4-agent chain: sources → writing → YTG QC → format).
argument-hint: <url> --site <site-slug> [--strategy X] [--main-keyword K]
allowed-tools: Bash(python3 content_writer.py refresh:*), Bash(python3 content_writer.py finalize:*), Bash(python3 content_writer.py plan init:*), Bash(python3 content_writer.py plan check:*), Bash(python3 content_writer.py ytg qc:*), Task, Read, Write, WebSearch, WebFetch, Skill
---

Runs the refresh of the given URL by sequencing the workflow chain:
content fetch → GSC → SERP/PAA → user intent → decision →
**source research** → generation → (YTG QC / internal linking in Phase 3bis).

> 🚫 **Non-negotiable rule - blacklist BEFORE any web fetch.** Read
> `.claude/skills/source-research/references/blacklisted-domains.md` **before the
> first WebFetch/WebSearch** of the session (SERP results included). A blacklisted
> domain is never fetched, never kept in a top N, never cited - filtering happens
> a priori, not after curation. Exceptions (existing links = Golden Rule, review
> article whose subject IS the platform): see the blacklist file.

## Step 1 - Deterministic fetch + audit + decision (`cw` CLI)

Run:

```bash
python3 content_writer.py refresh $ARGUMENTS
```

⚠️ **This command already covers steps 1 to 6 of the workflow** (via `_fetch_html`
+ `AuditEngine.full_audit` + `process_url`); do NOT redo them by hand:

- **`post_content` fetch** with 2 automatic strategies (`_fetch_html`):
  1. **WordPress REST API** (`WordPressAPIClient`, when `wp_api_config` is present
     for the blog),
  2. **Scraping fallback** on the public page (`ContentExtractor`) when the REST
     API is blocked.
- **GSC SEO performance** (clicks/impressions/CTR/position, `GSCAnalyzer`, 12-month
  keyword fallback),
- **Main keyword resolution** (GSC → multi-source `KeywordResolver`),
- **SERP analysis**: PAA, features, TOP competitors (`SERPAnalyzer`),
- **User intent** + dominant format (`IntentDetector`),
- **Strategy decision** (data-driven engine) + **prompt composition**.

Output in the displayed `context_dir`:

- `generation_prompt.txt` (composed prompt: strategy + site, GSC/SERP/PAA/intent
  signals already integrated),
- `Output HTML` / `Output JSON` paths, `Strategy`, assets-before count.

If the action is `NO_ACTION`, `BLOCKED_QUALITY_ISSUES`, `ERROR` or
`REDIRECT_301_SUGGESTED`: **stop** and report, nothing to generate.

## The agent chain (steps 1bis → 4bis)

Past the deterministic audit, the work is split across **7 specialised agents**,
each with its own tools and its own trade, each consuming the previous one's
output:

| # | Agent | Trade | Web access |
|---|---|---|---|
| 1 | `source-researcher` | verified sources → `sources_brief.md` | **yes** (only one) |
| 2 | `content-generator` | the substance + text-bearing blocks → HTML | no |
| 3 | `ytg-qc` | semantic density SOSEO/DSEO (after `finalize`) | no |
| 4 | `gutenberg-formatter` | format compliance, **last pass** | no |

**Analysis stays in the main session; execution is delegated.** Reading a JSON
that step 1 already fetched, ranking PAA questions and laying out an outline are
things you do inline — they need the conversation's context, not an isolated
process, and serialising them into a file for another agent to re-read loses
information at every hop. What justifies an agent is a *capability boundary*:
web access, a large token budget, or a mechanical checklist.

Each of the four earns its isolation:

- **Only agent 1 can reach the web.** Agents 2-4 physically cannot fetch a
  source, so a missing source surfaces as a gap in the brief instead of being
  quietly invented mid-writing. A tool-level guarantee, not a rule the model is
  asked to remember. This is why source research stays an agent even though the
  analysis around it does not: the isolation *is* the guarantee.
- **The writer burns the tokens.** Generation is the one step whose context
  would otherwise swamp the session.
- **Format closes the chain.** `finalize` creates the `.gutenberg.html`, then
  `ytg-qc` rewords sentences *inside* the blocks; the formatter therefore runs
  last, on the file that actually ships.
- **Each link is a restart point.** A bad article restarts at the failed link,
  not from the audit.

**The SERP/PAA fetch is not an agent either**: `SERPAnalyzer.analyze()` calls
DataForSEO in deterministic Python (step 1, already run for every URL of a
batch). You **read** `audit_data.json` and never re-query — doing so would
double the API cost per URL and desynchronise the analysed signals from the ones
that drove the strategy decision.

## Step 1bis - Keyword check (inline, no agent)

Step 1 prints `Keyword:` **and the source it came from**. A keyword from `cli`,
`notion`, `sheet` or `gsc` was chosen by a human or measured on real queries:
take it as is. Only the `slug` fallback deserves a look — check it for spelling,
in-house shorthand, a leftover year or category segment, and whether it reads
like a query at all. If it does not, fix it **before** step 1ter, since the SERP
call and the YTG guide are both keyed on it.

> The YTG guide is built from the **root** `main_keyword` (`provided_keyword or
> GSC`), not from `performance.main_keyword`. On a page with no GSC traffic —
> exactly the pages worth refreshing — the old behaviour fell through to the
> slug and produced a guide on the wrong sense of the word.

## Step 1ter - SERP reading (inline, no agent)

Read `audit_data.json` yourself: the `serp` block carries `paa_questions`,
`top_10_results`, `features`, `dominant_format` and `our_position`, all fetched
at step 1. Read `original.html` alongside it to measure the real gap.

Produce the SERP brief **in the conversation** (write `serp_brief.md` only if
you want it on disk for a later restart): questions ranked by editorial value,
questions dropped **with their reason**, competitive gap against the top 10,
dominant format, angles to avoid.

The point is the ranking. An unweighted PAA list makes every question look
equally worth a section. Say so plainly when `our_position` is null or
`dominant_format` is `other` — that is a real signal, not a hole to paper over.

## Step 2 - Sources (agent `source-researcher`)

`cw refresh` does **not** look for sources: without this step, `eeat_sources`
would be invented by the LLM. Delegate to the **`source-researcher`** agent
(Task tool), passing it the URL/topic, the `main_keyword`, the `context_dir` and
the `site_slug`.

It produces `<context_dir>/sources_brief.md` (source → claim → url → year) and
reports what it could **not** find. Take that gap seriously: no later link can
fill it, by design.

> Where `sites/<site-slug>/sources/` exists (today: `superprof.fr-ressources`,
> with `authority-map.md`), it is tier 1: identify the subject, aim at those
> authority domains first, then complete on the web. Where it does not, the agent
> operates in web-only mode.

## Step 2bis - Editorial outline (inline, no agent)

Build the outline yourself. It rests on the SERP brief, the PAA and the keyword
— all of which you produced at step 1ter — so delegating it would mean writing
your own analysis to disk for someone else to re-read.

Run `plan init` (deterministic scaffold), fill the outline using the
`seo-outline` skill (PAA→sections mapping, proof placement, top 10 gap), then
loop on `plan check` **until the verdict is `OK`**.

**The `OK` gate is not optional.** It is what made this step worth having in the
first place: fixing a bad plan costs a few lines, fixing it after generation
costs a full rewrite plus another YTG cycle. Never start step 3 on a
`NEEDS_FIX` plan.

The validated `content_plan.md` is an **input** to step 3: the writer works
*from the outline*, it does not reinvent it.

## Step 3 - Writing (agent `content-generator`)

Delegate the writing to the **content-generator** subagent (Max subscription,
never the paid API) via the Task tool. It has **no web access**: its sources are
exclusively those of the step-2 brief. Pass it:

- the `generation_prompt.txt` path (already contains PAA, intent, SERP, keyword),
- **the `content_plan.md` from step 2bis** (validated outline: the subagent writes
  from this plan, section by section),
- **the verified sources brief from step 2** (to inject into the content and
  into `eeat_sources`, no invention),
- the `site_slug` (to load the right writing skill),
- the `Output HTML` / `Output JSON` paths,
- the `Strategy` and the assets-before count (Golden Rule: assets after ≥ before).

The subagent writes the raw HTML + metadata directly to the output files; it
**does not return** HTML in the chat. Note the path of the written raw HTML
(`Output HTML`), it is required at steps 3bis and 4.

## Step 4 - Deterministic finalisation (`cw finalize`)

Once the raw HTML is written, chain save → assets → YTG QC → internal linking:

```bash
python3 content_writer.py finalize <url> --site <site-slug> --html-file <Output HTML> [--type <avis|versus>] [--main-keyword "<keyword>"] [--guide-id <YTG guide>]
```

> **Keyword + YTG guide.** Step 1 (`cw refresh`) prints `Keyword:` (main keyword)
> and `YTG guide:` when STEP 2.5 created a guide. **Carry both over** into
> `--main-keyword`/`--guide-id`: the post-generation QC then scores against the
> right guide (the real keyword, not the slug) and **reuses** the guide instead of
> recreating it (credit savings). If absent → the QC re-resolves the keyword
> (slug fallback).

> **Article type (enseigna).** Step 6 of the `refresh` CLI prints a
> `Type: avis|versus` line when the URL is classified (rule: slug `superprof-vs-*` →
> versus; slug containing `avis` → avis; otherwise nothing). If a `Type:` is
> printed, **carry it over as-is into `--type`**: the HTML output is then routed
> into `sites/enseigna/outputs/html/{type}/` and the versus prompt
> (`vs_concurrent.md`) is already injected at generation. Without `Type:`, do not
> pass `--type`.

This (deterministic) command:

- **saves** the bare HTML + `.gutenberg.html` + table CSVs,
- **validates the assets** (Golden Rule; restores missing ones),
- runs the **YTG semantic QC** → verdict:
  - `OPTIMAL` → proceeds with internal linking,
  - `NEEDS_FIX` → hand the under/over-optimised terms to the **`ytg-qc`** agent,
    which fixes the HTML in place and re-runs the check (cap of 2-3 iterations).
    The target is **never a fixed threshold**: article SOSEO **above** the TOP 3
    *and* TOP 10 guide averages, DSEO **strictly below** both,
  - `BLOCKED` → **stop + human alert** (severe over-optimisation, no linking,
    no automatic re-generation),
- applies the **internal linking** (`EnseignaAvisLinker` for enseigna; for
  superprof the landing links are injected upstream by `SuperprofRotator`). Add
  `--apply-linking` to write the links (otherwise dry-run).

## Step 4bis - Format compliance (agent `gutenberg-formatter`, last pass)

Delegate to the **`gutenberg-formatter`** agent, passing it the
**`.gutenberg.html`** path (the file that actually ships, created by `finalize`)
and the `site_slug`.

It loads the site's `qc_skill` (if declared in `site.json`) plus the
cross-cutting `format-wordpress`, walks the checklist — each rule has a
mechanical test — and **fixes in place**: numeric count-up, no orphan H3, `?` on
questions, FAQ emoji, exact AdvGB block comments with UUIDs and single-line
HTML, no adjacent identical blocks, no em dash.

It **only touches the encoding, never the substance**. Anything that would need
the content rewritten is reported, not silently rewritten — read that part of
its report.

> **Why it runs last, after `finalize` and `ytg-qc`.** `finalize` is what
> *creates* the `.gutenberg.html`, and `ytg-qc` then rewords sentences *inside*
> the blocks to fix density — which can break the single-line AdvGB constraint.
> Formatting before them would validate a file that does not yet exist in its
> published form, then let it be modified unchecked. Nothing touches the file
> after this agent.

> **Why it is separate from the writer.** Format compliance is deterministic —
> the `qc-sp-ressources` skill says it outright: "each point has an applicable
> regex test" — while writing is not. Judging encoding in the same pass as prose
> is what let these defects through, batch after batch.

## Step 5 - Report

Report: arbitrated keyword (and whether it was corrected), applied strategy,
selected sources, output paths (`sites/<site-slug>/outputs/`), YTG verdict with
SOSEO/DSEO **against the TOP 3 / TOP 10 averages**, format defects fixed,
assets verdict (before/after), and links added. Goal: URL → content + verdict +
links, with no manual rework.
