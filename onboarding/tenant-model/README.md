# Tenant model — what to copy for your market

This folder ships **on every machine** (it's part of `onboarding/`), so you always have a
template to copy from — even though the reference tenant `tenants/superprof-ressources/`
is **not** on your disk (sparse-checkout only materialises your own tenant + the engine).

Copy these model files into your tenant and adapt each one. Don't leave any `<...>`
placeholder or `_TODO` behind.

## Model files in this folder

| Model file (here) | Copy to | Action |
|---|---|---|
| [`config/tenant.model.json`](config/tenant.model.json) | `tenants/<your-id>/config/tenant.json` | **Adapt.** `tenant init` already pre-filled the identity fields — merge, don't overwrite them. Fill tone_profile, seo_settings, wp_api_config, sheets, `generation_skill`. |
| [`prompts/site.model.md`](prompts/site.model.md) | `tenants/<your-id>/prompts/site.md` | **Adapt.** A section skeleton — rewrite each section for your language/market. |
| [`skill/SKILL.model.md`](skill/SKILL.model.md) | `tenants/<your-id>/.claude/skills/<your-skill-name>/SKILL.md` | **Write your own.** This is your market's SEO/editorial expertise — not a template to replicate. The model only shows the required front-matter shape (`name:`/`description:`); the rules are yours. `name:` must equal `generation_skill` in tenant.json. |

`linking_maps/` and `outputs/` aren't modelled here: `outputs/` is generated at runtime
(never create it by hand — `tenant init` does), and `linking_maps/` is your own internal
linking data, added later.

## Want the full, mature reference?

The model files above are deliberately minimal. The complete, battle-tested version is the
`superprof-ressources` tenant, which isn't on your disk. If you want to see it in full
(its ~800-line `site.md`, the `sp-ressources-gutenberg` skill, etc.), **ask the maintainer
(@Sam-SEO-maker)** — don't try to sparse-add another tenant yourself.

## Minimal viable tenant

To be usable, your market needs at least:

1. `config/tenant.json` — completed (no `<...>` / `_TODO` left, `generation_skill` set).
2. `prompts/site.md` — real editorial rules for your market.
3. One writing skill under `.claude/skills/` whose `name:` matches `generation_skill`.

QC skill, guides, and reference examples are recommended but optional. See
[02 — Onboard my tenant](../02-onboard-my-tenant.md) for the step-by-step.
