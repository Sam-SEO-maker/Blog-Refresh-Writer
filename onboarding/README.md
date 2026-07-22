# Onboarding — Content Writer (Superprof SEO)

Welcome! This repo is the **multi-site SEO refresh agent** created for Superprof blogs. Every country blog is a **site** (a folder under `sites/`). You are the
SEO Manager for one country (ES, UK, US, MX, ID, JP, …) and you work on **your site only**.

## How this works in one picture

- **One shared repo.** Everyone clones the same repository.
- **You only see your own site.** Thanks to a git *sparse-checkout*, your computer
  materialises the shared engine (`_shared/`, `cli/`, `scripts/`, …) **and your single
  `sites/{site-slug}/` folder**. The other sites stay on GitHub but are **not** written
  to your disk — no clutter, no risk of editing someone else's site. Note that the
  sparse-checkout is a *disk convenience*: the engine files it does materialise are
  fully writable locally — nothing about sparse-checkout makes them read-only.
- **The engine is off-limits for you — enforced at merge time, not on your disk.** You
  never modify `_shared/`, `cli/`, `scripts/`, `.github/` or `content_writer.py`. Those
  belong to the maintainer. You *can* edit them locally, but a pull request that touches
  them is **blocked until the maintainer approves it**: `main` is protected and those
  paths require a Code Owner review (see [`.github/CODEOWNERS`](../.github/CODEOWNERS)).
  So the real guarantee is the branch protection rule on `main` — not the clone. You only
  ship changes inside your own site folder.

## Your path (do these in order)

1. **[01 — Set up your machine](01-setup-machine.md)** — install VS Code, Python, clone
   the repo (sparse), create the virtual environment, configure `.env` and credentials.
2. **[02 — Onboard my site](02-onboard-my-site.md)** — create your site folder,
   fill in its config, write your `site.md`, install your writing skill.
3. **[03 — Daily usage](03-daily-usage.md)** — the architecture, the slash commands and
   CLI, and the end-to-end refresh workflow.

Reference model to copy from: **[site-model/](site-model/README.md)**.

## Need help?

Anything about the **engine** (`_shared/`, `cli/`, `scripts/`, `.github/`), a new
credential, or your **CODEOWNERS** line → ask Samuel(**@Sam-SEO-maker**).
Everything inside `sites/{site-slug}/` is yours to change and ship via a pull request.
