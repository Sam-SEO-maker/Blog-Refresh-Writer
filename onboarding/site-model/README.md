# Site model — what to copy for your site

This folder ships **on every machine** (it's part of `onboarding/`), so you always have a
template to copy from — even though the reference site `sites/superprof-ressources/`
is **not** on your disk (sparse-checkout only materialises your own site + the engine).

Copy these model files into your site and adapt each one. Don't leave any `<...>`
placeholder or `_TODO` behind.

## Model files in this folder

| Model file (here) | Copy to | Action |
|---|---|---|
| [`config/site.model.json`](config/site.model.json) | `sites/<site-slug>/config/site.json` | **Adapt.** `site init` already pre-filled the identity fields — merge, don't overwrite them. Fill tone_profile, seo_settings, wp_api_config, sheets, `generation_skill`. |
| [`prompts/site.model.md`](prompts/site.model.md) | `sites/<site-slug>/prompts/site.md` | **Adapt.** A section skeleton — rewrite each section for your language/country. |
| [`skill/SKILL.model.md`](skill/SKILL.model.md) | `sites/<site-slug>/.claude/skills/<your-skill-name>/SKILL.md` | **Write your own.** This is your site's SEO/editorial expertise — not a template to replicate. The model only shows the required front-matter shape (`name:`/`description:`); the rules are yours. `name:` must equal `generation_skill` in site.json. |

`linking_maps/` and `outputs/` aren't modelled here: `outputs/` is generated at runtime
(never create it by hand — `site init` does), and `linking_maps/` is your own internal
linking data, added later.

## Want the full, mature reference?

The model files above are deliberately minimal. The complete, battle-tested version is the
`superprof-ressources` site, which isn't on your disk. If you want to see it in full
(its ~800-line `site.md`, the `sp-ressources-gutenberg` skill, etc.), **ask the maintainer
(@Sam-SEO-maker)** — don't try to sparse-add another site yourself.

## Minimal viable site

To be usable, your site needs at least:

1. `config/site.json` — completed (no `<...>` / `_TODO` left, `generation_skill` set).
2. `prompts/site.md` — real editorial rules for your site.
3. One writing skill under `.claude/skills/` whose `name:` matches `generation_skill`.

QC skill, guides, and reference examples are recommended but optional. See
[02 — Onboard my site](../02-onboard-my-site.md) for the step-by-step.
