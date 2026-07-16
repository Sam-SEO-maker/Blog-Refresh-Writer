# Onboarding — Content Writer (Superprof SEO)

Welcome! This repo is the **multi-tenant SEO refresh agent** used across Superprof
markets. Every country blog is a **tenant** (a folder under `tenants/`). You are the
SEO Manager for one market (ES, UK, US, MX, ID, JP, …) and you work on **your tenant only**.

## How this works in one picture

- **One shared repo.** Everyone clones the same repository.
- **You only see your own market.** Thanks to a git *sparse-checkout*, your computer
  materialises the shared engine (`_shared/`, `cli/`, `scripts/`, …) **plus your single
  `tenants/{your-id}/` folder**. The other tenants stay on GitHub but are **not** written
  to your disk — no clutter, no risk of editing someone else's market. Note that the
  sparse-checkout is a *disk convenience*: the engine files it does materialise are
  fully writable locally — nothing about sparse-checkout makes them read-only.
- **The engine is off-limits for you — enforced at merge time, not on your disk.** You
  never modify `_shared/`, `cli/`, `scripts/`, `.github/` or `content_writer.py`. Those
  belong to the maintainer. You *can* edit them locally, but a pull request that touches
  them is **blocked until the maintainer approves it**: `main` is protected and those
  paths require a Code Owner review (see [`.github/CODEOWNERS`](../.github/CODEOWNERS)).
  So the real guarantee is the branch protection rule on `main` — not the clone. You only
  ship changes inside your own tenant folder.

## Your path (do these in order)

1. **[01 — Set up your machine](01-setup-machine.md)** — install VS Code, Python, clone
   the repo (sparse), create the virtual environment, configure `.env` and credentials.
2. **[02 — Onboard my tenant](02-onboard-my-tenant.md)** — create your market folder,
   fill in its config, write your `site.md`, install your writing skill.
3. **[03 — Daily usage](03-daily-usage.md)** — the architecture, the slash commands and
   CLI, and the end-to-end refresh workflow.

Reference model to copy from: **[tenant-model/](tenant-model/README.md)**.

## Need help?

Anything about the **engine** (`_shared/`, `cli/`, `scripts/`, `.github/`), a new
credential, or your **CODEOWNERS** line → ask Samuel(**@Sam-SEO-maker**).
Everything inside `tenants/{your-id}/` is yours to change and ship via a pull request.
