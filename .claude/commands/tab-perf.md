---
description: Refresh monitoring of a Sheet tab or a Notion publications base - GSC gains/losses per URL vs the previous window, grouped by editorial status.
argument-hint: --site <site-slug> (--tab "New Growing List" | --source notion) [--days 28 | --start YYYY-MM-DD --end YYYY-MM-DD] [--top 15] [--dry-run]
allowed-tools: Bash(python3 content_writer.py audit gsc-tab:*), Read
---

Monitors the impact of refreshes on **every URL of a declared work tab**:
compares the current GSC window with the previous window of the same length,
and reports progressions / regressions per URL plus aggregates per editorial
status from the Sheet (`Publié` = refresh live — that line is the refresh
impact read; the other statuses are the control group). Two GSC queries total
(dimension `page`, service account) — no per-URL calls, a several-hundred-row
tab is fine.

```bash
python3 content_writer.py audit gsc-tab $ARGUMENTS
```

Options: `--site` (required), `--source` (`sheet` by default, or `notion`),
`--tab` (required with `--source sheet`, must be declared in `sheets.tabs` of
the site's `site.json` — the error lists the declared tabs if it isn't; ignored
with `--source notion`), current window = `--days` (default 28) **or** explicit
`--start`/`--end` (YYYY-MM-DD); the comparison window defaults to the period of
the same length immediately before, **or** is set explicitly with
`--compare-start`/`--compare-end`. `--top` (rows per movers table, default
15), `--dry-run` (no local JSON dump).

**Like-for-like**: whenever some tracked URLs had zero impressions over the
reference window (published since, or not yet indexed), the report states it and
gives the evolution restricted to the URLs already live in both windows. Those
URLs *create* traffic rather than grow it, so the headline percentage is not the
progression of the existing stock — on a list of recent content the two readings
can diverge by a lot, and on an ageing one the headline can hide an outright
decline. Quote the like-for-like figure when the question is "did our work move
what was already there".

**Year-over-year**: pass `--compare-start`/`--compare-end` to compare like with
like on the same calendar month, instead of the sliding previous period which
would put July against June — two months whose school-year seasonality has
nothing in common. The direction of the result can flip entirely between the
two readings, so state which comparison a figure comes from.

```bash
python3 content_writer.py audit gsc-tab --site enseigna.fr --source notion \
    --start 2026-07-01 --end 2026-08-01 \
    --compare-start 2025-07-01 --compare-end 2025-08-01
```

The reference window enters the output filename whenever it is explicit, so a
year-over-year report never overwrites the sliding one for the same window. The
report flags unequal window lengths (clicks not directly comparable) and refuses
a reference period that does not precede the current one.

The command writes a **self-contained HTML report** (French, non-dev friendly,
Superprof coral header) next to the JSON dump:
`outputs/<site-slug>/audit/gsc_tab_delta_*.html` — KPI tiles, alert block for
regressing `Publié` URLs, by-status table, top movers with delta bars. Clicks,
**impressions and CTR** are reported side by side at every level (tiles,
aggregate tables, per-URL rows): clicks alone cannot tell "we are shown less"
from "we are shown as much but clicked less" (AI Overview, SERP feature) — two
causes with two different remedies, and only the first is fixed by a refresh. That
report is the shareable deliverable: give its path and the `open "<path>"`
command to view it in a browser.

In the chat, report the monitoring view, not raw per-URL metrics: overall
delta, the by-status table (call out how `Publié` moves vs the rest — `Publié`
= refresh live), and the top progressions/regressions. Flag regressing
`Publié` URLs — refreshed articles losing ground, first candidates for a
follow-up pass. The JSON dump is for drill-down only.

**Notion source** (`--source notion`): the tracked URLs come from the site's
publications database instead of a Sheet tab, declared in the
`notion.publications` block of `site.json` (`database_id` + the column names
carrying the URL, keyword, refresh status, category and publication date).
Only rows bearing an http URL are measured — a row without a URL is an article
still to produce, with nothing to read in GSC. That source also carries two
extra aggregate axes the Sheet doesn't have, rendered in the report on top of
the by-status table: **by category** (which vertical grows) and **by
publication year** (2023 = the ageing stock, the natural refresh candidates).
Requires `NOTION_TOKEN` in `.env`.

**Filtering by category** (`--category`, repeatable, Notion source only): restricts
the scope to the given editorial categories, matched ignoring accents and case
(`--category "formations diplomantes"` matches `Formations Diplômantes`). An
unknown value fails and lists the declared ones. The selected categories appear
in the report header and in the output filename, so two scopes never overwrite
each other.

Note this is a filter over the **tracked publication rows**, not a URL-pattern
filter: the categories are a Notion column, and on a site like `enseigna.fr` they
do not map to any URL segment. Generated directory sections (`/v/` cities, `/s/`
schools, `/d/` departments on enseigna.fr) are already excluded by construction —
they are not rows of the publications base. They also carry the overwhelming
majority of the site's traffic, so a figure from this report describes the
editorial scope alone and must never be read as the site's performance.

Read-only (no write to the Sheet or to Notion). For the whole blog use `/blog`;
for a single URL's queries use `/page <url>`.
