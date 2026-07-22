# Maintainer checklist — onboarding a new SEO Manager

For the maintainer (**@Sam-SEO-maker**). SEO Managers: nothing to do here — this
page just shows what you'll receive and from whom.

The repo carries **zero secrets** (`.env` is git-ignored, the repo is public).
Every credential below travels through a **secure channel** (password manager or
equivalent — never chat, never email in clear, never git).

## 1. Send the welcome kit (before their step 01)

| Item | Value to send | Used for |
|---|---|---|
| DataForSEO | `DATAFORSEO_LOGIN` + `DATAFORSEO_PASSWORD` (shared account) | SERP/PAA analysis |
| YourTextGuru | `YTG_NEW_API_KEY` (shared key) | semantic guides + QC |
| Claude Code | shared account login (`superteamseo@gmail.com`, Max plan) | the assistant itself |

Nothing to send for **GSC**: `superprof.*` properties go through the shared MCP
server, auth lives server-side.

## 2. Coordinate with the tech team (their step 02, part 3b)

- WordPress **login + Application Password** for the manager's blog
  (`WP_<SITE>_USER` / `WP_<SITE>_APP_PASSWORD`). Needed only when they start
  pushing articles — audit and generation work without it.

## 3. Repo-side gestures (their step 02, part 7)

- Add their CODEOWNERS line:
  `/sites/<site-slug>/  @Sam-SEO-maker @their-github-handle`
- Give them write access to the GitHub repo.
- Review and merge their onboarding pull request.

## 4. Optional, when they adopt sheet-driven batches

- Create their Google Sheet, share it with the service account, send them the
  spreadsheet id (`SPREADSHEET_ID_<SITE>` in their `.env`, matching
  `spreadsheet_env` in their `site.json`).

## Not needed for managers

- `NOTION_TOKEN` (Notion → sites.json sync) — maintainer-only.
- Google service-account file — only for non-Superprof sites (agency clients).
