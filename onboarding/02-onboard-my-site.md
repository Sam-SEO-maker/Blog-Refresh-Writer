# 02 — Onboard my site

Goal: create your site's folder — `sites/<site-slug>/`, where `<site-slug>` is your
**`site_slug`** from the catalog (e.g. `en-ae-blog`) — then configure it and give it the
editorial rules and writing skill it needs. This is where you "load your files".

> Prerequisite: you've finished [01 — Set up your machine](01-setup-machine.md) and
> `python3 content_writer.py --help` works.

## 1. Find your site id

```bash
python3 content_writer.py site list
```

This prints the catalog. The value you want is the **`site_slug`** column — that string
*is* your `<site-slug>` everywhere in these guides. Ressources sites use
`lang-country-ressources` (e.g. `es-es-ressources`, `en-uk-ressources`); country blogs
use `lang-country-blog` (e.g. `en-ae-blog`, `es-mx-blog`). A `[x]` means the site is
already onboarded.

## 2. Scaffold your site

```bash
python3 content_writer.py site init <site-slug>
```

This does three things:
1. Creates `sites/<site-slug>/` with `config/`, `prompts/`, `linking_maps/`, `outputs/`.
   (Your writing-skill folder `.claude/skills/` is **not** created here — you'll add it
   yourself in step 6. That's expected.)
2. Writes a **minimal** `config/site.json` — only the identity fields it can derive
   from the catalog (`site_slug`, `display_name`, `domain`, `url_base`, `gsc_property`,
   `language`, plus safe defaults for `auth_mode`/`content_type`) — and a `_TODO` line
   listing everything **you** must still add by hand (tone_profile, seo_settings,
   wp_api_config, sheets, …). It is a **skeleton, not a finished config**: expect ~12
   lines, not the rich hundred-line file a mature site ends up with. You'll flesh it
   out in steps 3–4, using the model files in
   [`site-model/`](site-model/README.md) as your starting point (that folder is on
   your disk; the reference site `superprof-ressources` is **not**).
3. Adds your folder to the sparse-checkout (so it shows up in your working tree) and
   registers your site in `_shared/config/sites.json`.

## 3. Connect your WordPress login

Your site now exists, so you can set up the WordPress credentials for your blog. They
live in **two files you connect together** — this is the step people find fiddly, so
follow the two parts in order.

**a. Add the `wp_api_config` block to your site config.** Open
`sites/<site-slug>/config/site.json` (in VS Code: `Cmd/Ctrl+P`, then type
`site.json`). `site init` did **not** create this block — you add it now. Every value
is derived from **your own** site, from the `gsc_property` already in the file. Build it
with these three rules:

- **`api_base_url`** = your `gsc_property` + `wp-json/wp/v2`.
  If `gsc_property` is `https://www.superprof.it/blog/`, then
  `api_base_url` is `https://www.superprof.it/blog/wp-json/wp/v2`.
- **`user_env_var`** / **`password_env_var`** = `WP_<SITE>_USER` /
  `WP_<SITE>_APP_PASSWORD`, where `<SITE>` is your `site_slug` upper-cased with `-`
  turned into `_`. For `it-it-blog` → `WP_IT_IT_BLOG_USER` /
  `WP_IT_IT_BLOG_APP_PASSWORD`. (Pick any consistent name — it just has to match `.env`
  in part b; the slug-based convention keeps it unambiguous.)

So a `superprof.it` blog gets:

```jsonc
"wp_api_config": {
  "api_base_url": "https://www.superprof.it/blog/wp-json/wp/v2",
  "user_env_var": "WP_IT_IT_BLOG_USER",
  "password_env_var": "WP_IT_IT_BLOG_APP_PASSWORD",
  "timeout": 30
}
```

The two `*_env_var` values are just **names** — the real login/password go in `.env`
(part b), never in this file. Copy the block from
[`site-model/config/site.model.json`](site-model/config/site.model.json) and
swap in your own URL and names.

**b. Put the real values in `.env`.** Generate an *Application Password* on your WP site
(WP admin → *Users → Application Passwords*), then open the `.env` you created in
[01 — step 7](01-setup-machine.md) and add exactly the two names you wrote in part a, with
your values (continuing the `superprof.it` example):

```bash
WP_IT_IT_BLOG_USER=your-wp-login
WP_IT_IT_BLOG_APP_PASSWORD=xxxx xxxx xxxx xxxx xxxx xxxx
```

The names in `.env` must match the `*_env_var` names in your `site.json`
**character for character** — that string is the only link between the two files. Fill in
**only** your blog's two lines.

> 🔒 Your Application Password goes **only** into `.env` — never pasted into the Claude
> Code chat. You can ask Claude to write the line into `.env` for you; just don't show it
> the value in the conversation. (Same golden rule as [01 — step 7](01-setup-machine.md).)

> Not `superprof_sites_catalog.json` — that's the site *catalog*, unrelated to
> credentials. The only files involved are your site's `site.json` (to read) and
> `.env` (to write).

## 4. Complete the rest of your `site.json`

Back in `sites/<site-slug>/config/site.json`, replace the remaining `_TODO` values:

- `tone_profile` — voice and register for your site.
- `seo_settings` — your SEO thresholds/targets.
- `sheets` — your Google Sheet id(s), if you drive refreshes from a sheet.
- `generation_skill` / `qc_skill` — the name of the writing/QC skills you'll create
  in step 6 (this is how the generator finds them; it is **not** hardcoded).

Copy from **[`site-model/config/site.model.json`](site-model/config/site.model.json)**
and fill every `<...>` / `_TODO`. See **[site-model/](site-model/README.md)** for the
field-by-field guide.

## 5. Write your `site.md`

`sites/<site-slug>/prompts/site.md` is the master editorial source for your site:
tone, blacklist, WordPress format specifics. The scaffold left a placeholder — replace
it. Copy the skeleton from
[`site-model/prompts/site.model.md`](site-model/prompts/site.model.md) and rewrite
each section for your language and country.

Drop any extra editorial material (guides, block examples) under
`sites/<site-slug>/prompts/`.

## 6. Install your writing skill

Your site's writing rules live in a **skill scoped to your site**. This folder
doesn't exist yet (the scaffold didn't create it) — **you create it now**, at:

```
sites/<site-slug>/.claude/skills/<your-skill-name>/SKILL.md
```

**Write it your way** — this skill is where *your* SEO and editorial expertise for your
site's country lives, and you know that country better than anyone. There's no house template to
replicate: the writing rules, structure, and tone are yours to decide.

The only hard requirements are technical, so the engine can find and run your skill:

- It lives at `sites/<site-slug>/.claude/skills/<your-skill-name>/SKILL.md`.
- Its front-matter has a `name:` and a `description:` (the `description` is what tells the
  engine when to use it — write it well).
- Your `site.json` `generation_skill` (and optionally `qc_skill` (quality_check)) points at that exact
  `name:`.

If you'd like a concrete starting point, [`site-model/skill/SKILL.model.md`](site-model/skill/SKILL.model.md)
shows the front-matter shape and the kinds of sections a skill can have — treat it as a
blank canvas, not a pattern to copy. Want to see a fully worked example? Ask the
maintainer.

> **What's already on your machine vs what you create.** The **cross-cutting** skills
> (`edito-refresh`, `format-wordpress`, `recherche-sources`) and the **slash commands**
> (`/refresh`, `/audit`, `/batch`, …) live at the repo root under `.claude/`, which is
> part of the shared engine — they're already on your disk and working, **you don't
> install or recreate them**. The only skill you create is **your own** writing (and
> optional QC) skill under `sites/<site-slug>/.claude/skills/`. You never see other
> sites' skills (e.g. `superprof-ressources`'s) because their site folders aren't on
> your disk — and you don't need them.

## 7. Ask for your CODEOWNERS line

The `.github/` folder is locked to the maintainer, so you can't add yourself. Ask
**@Sam-SEO-maker** to add your ownership line:

```
/sites/<site-slug>/   @Sam-SEO-maker @your-github-handle
```

This makes you the required reviewer for your own site.

## 8. Ship your site (pull request)

Commit **only your site folder** and open a pull request:

```bash
git checkout -b onboard/<site-slug>
git add sites/<site-slug>
git commit -m "feat(site): onboard <site-slug>"
git push -u origin onboard/<site-slug>
```

Then open the PR on GitHub. Note: `_shared/config/sites.json` is git-ignored (it's your
local runtime registry) — it is **not** part of your commit, and that's expected.

## Done

Your site is live locally and reviewable. Next: **[03 — Daily usage](03-daily-usage.md)**.
