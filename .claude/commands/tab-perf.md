---
description: Refresh monitoring of a Sheet tab - GSC gains/losses per URL vs the previous window, grouped by editorial status.
argument-hint: --site <site-slug> --tab "New Growing List" [--days 28 | --start YYYY-MM-DD --end YYYY-MM-DD] [--top 15] [--dry-run]
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

Options: `--site` (required), `--tab` (required, must be declared in
`sheets.tabs` of the site's `site.json` — the error lists the declared tabs if
it isn't), current window = `--days` (default 28) **or** explicit
`--start`/`--end` (YYYY-MM-DD); the comparison window is always the period of
the same length immediately before. `--top` (rows per movers table, default
15), `--dry-run` (no local JSON dump).

The command writes a **self-contained HTML report** (French, non-dev friendly,
Superprof coral header) next to the JSON dump:
`outputs/<site-slug>/audit/gsc_tab_delta_*.html` — KPI tiles, alert block for
regressing `Publié` URLs, by-status table, top movers with delta bars. That
report is the shareable deliverable: give its path and the `open "<path>"`
command to view it in a browser.

In the chat, report the monitoring view, not raw per-URL metrics: overall
delta, the by-status table (call out how `Publié` moves vs the rest — `Publié`
= refresh live), and the top progressions/regressions. Flag regressing
`Publié` URLs — refreshed articles losing ground, first candidates for a
follow-up pass. The JSON dump is for drill-down only.

Read-only (no write to the Sheet). For the whole blog use `/blog`; for a
single URL's queries use `/page <url>`.
