# 03 — Daily usage

Goal: understand the architecture well enough to run refreshes on your site and find
the right command or skill.

## The mental model

- **Engine (shared, not yours to edit):** `_shared/`, `cli/`, `scripts/`,
  `content_writer.py`. It runs the audit → decision → generation → QC → linking chain.
- **Your site:** `sites/<site-slug>/` — config, `prompts/site.md`, your writing skill,
  linking maps, and generated `outputs/`. This is the only part you change.
- **Catalog vs registry:**
  - *Catalog* `_shared/config/superprof_sites_catalog.json` = the menu of all onboardable
    sites (6 ressources + 90 blogs).
  - *Registry* `_shared/config/sites.json` = the sites actually materialised on your
    machine, read at runtime. It's local and git-ignored.
- **Golden rule:** a refresh **never reduces assets** (`assets_after >= assets_before`) —
  images, tables, videos, internal links, even links to competitors are always kept.

For the full architecture, read **[CLAUDE.md](../CLAUDE.md)** at the repo root.

## Slash commands (in Claude Code)

Type these in the Claude Code chat. They wrap the CLI and load the right skills.

| Command | What it does |
|---|---|
| `/refresh <url> --site <site-slug>` | Full refresh: audit → decision → sources → generation → finalize |
| `/batch --action X --site <site-slug>` | Batch refresh from your Google Sheet |
| `/audit serp <url>` | Targeted SERP audit (PAA, secondary keywords) |
| `/decide --site <site-slug>` | Data-driven decision engine on your sheet's URLs |
| `/site-status --site <site-slug>` | GSC state of your site → sheet |
| `/blog --site <site-slug>` | SEO performance of your blog via GSC (totals + top keywords) |
| `/page <url>` | SEO performance of a single URL via GSC |
| `/ytg <url>` | Semantic QC (YourTextGuru) of an article |

## CLI (what the slash commands call)

The source of truth for commands is always `--help` (auto-generated):

```bash
python3 content_writer.py --help
python3 content_writer.py <group> --help    # e.g. refresh, batch, audit, site
```

Key groups: `refresh`, `batch`, `audit`, `finalize`, `linking`, `ytg`, `notion`,
`site`, `workflow` — plus `audit gsc-state` (via `/site-status`).

## Skills (loaded on demand)

- Cross-cutting (repo root): `edito-refresh` (SEO/GEO/E-E-A-T ranking rules),
  `format-wordpress` (HTML/WP formatting), `recherche-sources` (verified sourcing).
- Your site's writing/QC skills live under `sites/<site-slug>/.claude/skills/` and are
  selected via `generation_skill` / `qc_skill` in your `site.json`.

## A typical refresh, end to end

1. Pick a URL on your blog that needs work (from your sheet or `/site-status`).
2. Run `/refresh <url> --site <site-slug>`.
3. The engine audits it (GSC + DataForSEO/SERP), decides a strategy, researches sources,
   then a subagent generates the new HTML into `sites/<site-slug>/outputs/`.
4. Review the output, run `/ytg <url>` for semantic QC, and publish per your site's flow.

## Do / don't

- **Do** keep every change inside `sites/<site-slug>/`.
- **Do** run `python3 -m pytest tests/ -q` if you ever touch shared code (you normally won't).
- **Don't** edit `_shared/`, `cli/`, `scripts/`, `content_writer.py`, or `.github/` —
  those are the maintainer's. Open an issue or ping **@Sam-SEO-maker** instead.
- **Don't** commit `.env`, credentials, or `sites.json` (all git-ignored on purpose).
