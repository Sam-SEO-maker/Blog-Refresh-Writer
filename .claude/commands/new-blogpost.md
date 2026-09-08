---
description: Create a NEW article (no WordPress post behind the URL yet) - backlog from a Sheet tab or a single URL, then the same agent chain as /refresh (sources → outline → writing → YTG QC → format). Deliverables stay local, publication is manual.
argument-hint: --site <site-slug> (--tab "<tab name>" [--limit N] | <url> --main-keyword "<kw>" [--title "<title>"])
allowed-tools: Bash(python3 content_writer.py batch new-list:*), Bash(python3 content_writer.py refresh:*), Bash(python3 content_writer.py plan init:*), Bash(python3 content_writer.py plan check:*), Bash(python3 content_writer.py finalize:*), Bash(python3 content_writer.py ytg qc:*), Task, Read, Write, WebSearch, WebFetch, Skill
---

Creates an article that **does not exist yet** on the site. `/refresh` and
`/batch` refuse such URLs on purpose (`Could not fetch the content`: nothing to
audit, no assets baseline, no GSC history). This command is the creation
counterpart: the same chain, prepared **without a fetch**.

> 🚫 **Non-negotiable rule - blacklist BEFORE any web fetch.** Read
> `.claude/skills/source-research/references/blacklisted-domains.md` **once at
> the start**, then **re-check at the start of each article**. A review article
> whose subject IS the platform may fetch that platform as a primary source
> about itself (pricing, features, terms) - never as an authority on a general
> claim. Everything else in the list holds.

## What differs from a refresh (read this first)

| | `/refresh` | `/new-blogpost` |
|---|---|---|
| Original content | fetched from WP, preserved (Golden Rule) | **none** - `original.html` is empty, assets baseline = 0 |
| Keyword | GSC → Sheet → slug | **must be given** (`--main-keyword`, or the tab's `main_keyword` column): the page has no GSC data and a slug is not a query |
| Strategy | decided from data | always `FULL_REFRESH` (the whole article is written) |
| Title / H1 | read from the page | come from the tab (`blogpost_title`, `blogpost_h1`) or `--title` |
| Publication | `finalize` pushes on `OPTIMAL` | **manual**: `push` can only update an existing post (and the enseigna REST API is disabled). Always run `finalize --no-publish` |

## Step 1 - Backlog (`cw` CLI, read-only)

With a tab:

```bash
python3 content_writer.py batch new-list --site <site-slug> --tab "<tab name>" [--limit N]
```

The tab is read **by header name** (`url`, `main_keyword`, `blogpost_title`,
`blogpost_h1`, `blog_category`, `publish_date`), so it does not need to be
declared in `sheets.tabs`. A row is pending when `url` is filled and
`publish_date` is empty. Nothing is written to the Sheet. On `enseigna.fr` the
creation tab is **`A ajouter`** (sorted by search volume, highest first): do
not confuse it with the `Avis` tab, whose "A faire" rows without URL are the
same backlog mirrored without the data `/batch` needs.

With a single URL, skip this step: `<url> --main-keyword "<kw>"` is the backlog.

Process the rows **in tab order** (volume descending) unless told otherwise.

## Step 2 - Per-article chain

For each pending row:

1. **Keyword check** (inline) - the keyword comes from the tab or the flag,
   never from the slug. Sanity-check it once (spelling, brand casing, an
   accent that changes the query: `cours thalès avis` vs `cours thales avis`
   are the same Google query, keep the tab's spelling). No keyword → **drop
   the row and report it**, do not guess one.

2. **Preparation** (`cw` CLI, deterministic):

   ```bash
   python3 content_writer.py refresh <url> --site <site-slug> --main-keyword "<kw>" --title "<blogpost_title>" --new
   ```

   `--new` skips the fetch, writes an empty `original.html`, a zero assets
   baseline and `audit_data.new_article = true`, forces `FULL_REFRESH`, and
   runs the rest unchanged: SERP/PAA/intent (DataForSEO, once), **YTG guide on
   the given keyword**, decision, `generation_prompt.txt` (whose header says
   "Création d'un nouvel article", not "Refresh"). Note `context_dir`,
   `Output HTML`, `Type: avis|versus` (enseigna), `Keyword`, `YTG guide`.

3. **SERP reading** (inline) - read `audit_data.json` (`serp` block: PAA,
   top 10, features, dominant format). Never re-query. Rank the PAA questions,
   name the dropped ones and why, state the competitive gap. `our_position` is
   meaningless here (the page does not exist): ignore it.

4. **Sources** - `source-researcher` agent (URL/topic, keyword, `context_dir`,
   `site_slug`) → `sources_brief.md`. For a review, the platform itself is the
   primary source for its own pricing/features (blacklist exception 2): dated
   facts, checked on the live site, never inherited from anywhere.

5. **Outline** (inline) - `plan init <url> --site <site-slug>`, fill
   `content_plan.md` with the `seo-outline` skill from the SERP reading + the
   brief, loop on `plan check` **until `OK`**. The H1 is the tab's
   `blogpost_h1` (enseigna: H1 is an ACF field, **never in the body**).

6. **Writing** - `content-generator` agent with `generation_prompt.txt`, the
   validated `content_plan.md`, `sources_brief.md`, the `site_slug`, the
   output paths, the title/H1/category from the tab and the site's
   `generation_skill` (read from `site.json`). Tell it explicitly: **new
   article, no original to preserve, assets-before = 0**. It writes the files
   (html + acf JSON + csv on enseigna), never HTML in the chat.

7. **Finalisation + semantic QC** - always `--no-publish`:

   ```bash
   python3 content_writer.py finalize <url> --site <site-slug> --html-file <Output HTML> [--type <avis|versus>] --main-keyword "<kw>" --guide-id <YTG guide> --no-publish
   ```

   Assets validation passes trivially (0 ≥ 0). YTG verdict as in `/refresh`
   (target = the guide's range, variable per SERP): `OPTIMAL` → done;
   `NEEDS_FIX` → `ytg-qc` agent, cap 2-3 passes; `BLOCKED` → stop this article,
   alert, next one.

8. **Format** - `gutenberg-formatter` agent on the **`.gutenberg.html`**
   (`site_slug`): last pass, nothing touches the file afterwards.

## Step 3 - Report

Per article: keyword, `plan check` verdict, YTG verdict (SOSEO/DSEO vs
range), output paths (`sites/<site-slug>/outputs/html/<type>/…`, `acf/`,
`csv/`), and the rows dropped (no keyword, BLOCKED) with the reason.

State plainly that **nothing was published**: the editor imports the CSV
tables into TablePress, fills the ACF fields from `acf/{slug}_acf.json`,
pastes the Gutenberg body, and sets `publish_date` in the tab - which is what
removes the row from `batch new-list` next time.
