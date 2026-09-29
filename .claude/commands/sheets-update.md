---
description: Order refresh articles in Notion from a Sheet tab - one row per URL, with its main keyword and the Refresh tag, in the Sheet's own order.
argument-hint: --site <site-slug> --tab "Medium Potential" (--rows 201-210 | --limit 10) [--status "A faire"] [--apply] [--fix-keywords]
allowed-tools: Bash(python3 content_writer.py notion push-orders:*), Read
---

Creates the editorial orders in Notion from the work Sheet, so a batch of URLs
no longer has to be pasted in by hand. For each selected row it writes one line
in the site's orders database: **`Local resource URL`**, **`Main KW`** (read
from the Sheet), **`Type of article` = Refresh**, and the **Country relation**
without which the row shows up in no market view.

```bash
python3 content_writer.py notion push-orders $ARGUMENTS
```

**Dry-run by default.** Without `--apply` the command only prints the plan:
what it would create, what is already ordered, and any row missing a keyword.
Nothing reaches Notion until you re-run with `--apply`.

Options: `--site` and `--tab` (required; the tab must be declared in
`sheets.tabs` of the site's `site.json`), `--rows 201-210` to restrict to a
range of Sheet rows **as Google Sheets displays them** (headers included, same
semantics as `/batch`), `--limit N` to cap the batch (0 = no cap), `--status`
(default `A faire`, pass `--status ""` to take any status), `--apply` to write,
`--fix-keywords` to also correct `Main KW` on rows already ordered whose
keyword diverges from the Sheet.

`--rows` filters **before** `--limit`, so the cap counts inside the range.

## What it protects

**The order of the batch.** Pasting ten URLs into Notion lands them in an
arbitrary order. Notion dates pages to the second, so rows created in one burst
share a `createdTime` and the orders view — which declares no sort — shows them
shuffled. The command creates one row at a time, spaced just over a second, so
`createdTime` is strictly increasing and the batch reads in the Sheet's order:
the order of the work you decided to commission.

**No duplicate orders.** Rows are matched on the normalised URL (no scheme, no
`www`, no trailing slash), never on position. A URL already in the database is
never ordered twice; it is reported, with its Notion keyword, so a keyword that
diverges is visible instead of silently duplicated. A URL repeated inside the
Sheet is ordered once.

**The PO's columns.** Only the four columns above are written. `Writer`,
`Deadline`, `Price`, `Status`, `Month`, `Keywords` and
`Notes / Instructions` are never touched, on creation or correction.
`Title (Main KW)` is deliberately left empty, as on the existing refresh rows:
the URL identifies the article.

## Before the first run

The orders database must be shared with the integration behind `NOTION_TOKEN`
(in Notion: open the database, `...` > Connections, add the integration). It is
the **source** database that must be shared, not the linked view embedded in the
order page: the API rejects linked databases outright. If access is missing the
command says so and writes nothing.

## Afterwards

The orders are in Notion but nothing is written yet. The chain proper starts
with `/batch --site <site-slug> --tab "<tab-name>"`, which prepares the same
rows for refresh.
