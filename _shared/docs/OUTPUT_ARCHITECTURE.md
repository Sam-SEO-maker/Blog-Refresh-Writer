# Output Architecture

**Version**: 3.0 (multi-site) · **Last updated**: 2026-07-23

Every site owns its outputs. Nothing is written outside the site folder:

```
sites/<site-slug>/outputs/          # gitignored (see .gitignore: outputs/)
├── html/                           # generated article bodies (.gutenberg.html)
│   ├── avis/ | versus/             # enseigna.fr only: one subfolder per article type
│   └── YYYY-MM-DD/                 # batch runs are grouped in dated subfolders
├── acf/                            # structured data (ACF JSON, one per article)
├── csv/                            # tables exported for TablePress (max 3/article)
├── metadata/                       # per-article metadata JSON (title, meta, H1, notes)
├── json/                           # raw analysis artifacts
├── audit/ · editorial_audits/      # audit reports
└── _scrape_cache/                  # scraped original HTML (before/after comparison)
```

Some sites carry extra folders created by their own workflows (e.g.
`batches/`, `csv_zips/`, `wp_backups/` on superprof.fr-ressources). That is
fine: the invariant is only that **everything lives under
`sites/<site-slug>/outputs/`**.

## Rules

- **Path resolution goes through `_shared/core/site_paths.py`** (single point):
  `output_dir(site_slug)`, `scrape_cache_dir(site_slug)`, etc. Never build an
  output path by hand. `OutputManager` (`scripts/utils/output_manager.py`) is
  the write layer on top of it (`save_refreshed_html`, `save_metadata`,
  `save_temp_html`...).
- **`outputs/` is gitignored**: generated content never lands in the public
  repo. The scaffold (`site init`) creates the folder skeleton.
- **Scrape cache** (`_scrape_cache/`) holds the original HTML fetched before a
  refresh, used for the editorial audit comparison and the Golden Rule asset
  check (`assets_after >= assets_before`). Safe to purge; regenerated on the
  next refresh.
- **Publication source**: publish from the dated batch subfolder (or the
  article-type subfolder), and keep only `.gutenberg.html` files (the bare
  debug HTML is deleted after generation).

## History

- v2.0 (2026-02) described the old centralised layout (`_shared/temp/` +
  `_shared/outputs/`, git-tracked). That structure no longer exists: outputs
  were migrated into each site folder (`sites/<site-slug>/outputs/`,
  gitignored), and the scrape cache moved to `outputs/_scrape_cache/`.
