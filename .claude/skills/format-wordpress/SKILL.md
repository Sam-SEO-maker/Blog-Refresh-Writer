---
name: format-wordpress
description: >-
  Cross-cutting HTML/WordPress formatting rules for all blogs: allowed tags,
  clean HTML without WP wrappers, dual Gutenberg output, mandatory French
  accents, em dash forbidden, anchors without <strong>, no links inside H2/H3,
  bullet-list punctuation. Referenced by the other writing skills. Read-only
  (formatting guide).
disable-model-invocation: false
---

# WordPress format: cross-cutting output rules

**Form** rules shared by every writing skill
(`generate-enseigna-avis`, `sp-ressources-gutenberg`). The site-specific skills
add their own blocks/tone; this guide sets the HTML/WP invariants.

## Allowed tags

`<h2>`, `<h3>`, `<p>`, `<ul>`, `<ol>`, `<li>`, `<strong>`, `<em>`, `<a>`,
`<table>`, `<img>`, `<blockquote>`.

**Never**: `<script>`, massive inline `<style>`, unsecured `<iframe>`,
`<font>`, `<center>`.

## No WordPress wrappers

The HTML is a **flat list of blocks**. Never emit:
`<article>`, `<div class="content-wrap">`, `<header>`,
`<div class="entry-content">`, `<div class="post-thumbnail">`.

- **No H1 inside a `<header>`**: WordPress handles the H1 depending on the
  blog's context (Enseigna: H1 = ACF field, no H1 in the body; Superprof Ressources:
  H1 = first `wp:heading {"level":1}` block). See the site's skill.
- **No featured image** in the HTML: WordPress handles it.

## Dual Gutenberg output

Each refresh produces two files: `{slug}_refreshed.html` (bare HTML, debug)
and `{slug}_refreshed.gutenberg.html` (pasteable into the WP code editor,
`<!-- wp:* -->` comments + `wp-block-*` classes). **Only the `.gutenberg.html`
is used for publication**; delete the bare one after generation. Ref.
[[feedback-delete-nu-html-keep-gutenberg]].

- **Refresh images**: keep the existing `id`s via `class="wp-image-NNN"`.
  If no id is detectable, emit a `wp:image` without `id`.
  Keep the source `width`/`height` and any inline `style` **verbatim**; never invent
  or recompute them (an absent dimension beats a wrong one). Keep the `size-*` class
  matching the file actually served.
  **Never carry over `srcset`, `sizes`, `loading` or `decoding`.** WordPress computes
  them at render time from the media library. A `srcset` frozen into the content makes
  it emit `sizes="auto, …"`, and the browser's own stylesheet then applies
  `contain:size !important` — the image is cut off from its real size and inherits the
  declared intrinsic size instead (observed: a 1920x1280 image rendered 35694px tall).
- **Pros/cons convention** (Enseigna): `<div class="pros-cons"><div class="cons">…</div><div class="pros">…</div></div>`
  → auto-converted to `wp:columns`.

## French language: accents (MANDATORY)

French content (HTML **and** JSON) uses correct accents (é è ê à ù ç î ô û ï).
Never « ameliorer », « systeme », « debutant ». A French word without its accent
is a **blocking bug** to fix before delivery.

## French typography: detailed reference

The full mechanics of written French live in `references/typographie-fr.md`
(read it before any FR writing): **non-breaking spaces** before `: ; ? ! % €`
and inside `« »` quotation marks, typographic apostrophe `'`, number/date
formats, capitalisation (sentence case, languages/subjects in lowercase),
**inclusive writing with the middle dot** (allowed), **AI connector phrases to
ban** (« Il est important de noter que », « En outre »…) and anglicisms.

## Em dash forbidden

Never use `—`. For parentheticals: commas, parentheses, or an en dash `–` if a
visual separator is indispensable. All blogs. Ref.
[[feedback-no-em-dash]].

## Links

- **Anchors without `<strong>`**: `<a href="…">texte</a>`, never
  `<a href="…"><strong>texte</strong></a>` (over-optimisation anti-pattern).
- **No links inside H2/H3**: an `<a>` inside a heading is an SEO red flag.
- **Never a _new_ link to Wikipedia** (all sites): link the primary source,
  not the encyclopedia article ([[feedback-no-wikipedia-links]]). (An existing
  Wikipedia link stays, per the Golden Rule; the ban is on adding new ones.)
- **Sources**: no « Consulté le [date] » ([[feedback-no-consulte-le]]).

## Bullet-list punctuation

French content: each `<li>` ends with a **comma**; the **last** `<li>` ends
with a **period**.

```html
<ul>
  <li>Premier élément,</li>
  <li>Deuxième élément,</li>
  <li>Dernier élément.</li>
</ul>
```

## Density & conclusion

- Minimum **3 H2 sections**, fully developed (no single-paragraph H2).
- **No "Conclusion" H2** (except the Enseigna blog): end with a short condensed
  paragraph (3-5 sentences), actionable tone, no exhaustive recap.
- No "Related articles / Further reading" section: internal links are woven
  **naturally into a sentence**, spaced 150-200 words apart.

## Tables

**Every article ships at least one table — no exception.** A refresh that
produces zero `<table>` is incomplete, even when the original had none and
nothing looks "naturally tabular": there is always a comparison, a set of
criteria, a list of cases or a recap of formulas worth laying out in a grid.
Target **1 to 3 tables per article** (3 is the hard cap).

A table must earn its place: it condenses something the prose states in a
scattered way (symbol / unit / role, criterion / case A / case B,
step / action / result). Never a two-line table of decoration, never a
reformatted bullet list.

Mechanics:
- Wrap in a `<!-- wp:table -->` block, `<table>` as the **direct** child
  (no `<figure class="wp-block-table">` wrapper, no `has-fixed-layout`
  class unless the matching `{"hasFixedLayout":true}` attribute is set) —
  a mismatch between markup and block attributes makes the editor
  report "block seems broken".
- A `<figcaption class="wp-element-caption">` goes **inside** the block.
- Each `<table>` → a **CSV** in `csv/` (`{slug}_tableau_{descriptif}.csv`),
  **no shortcode** `[table id=X /]` in the HTML. Ref.
  [[feedback-csv-naming-tablepress]].
- Generate the CSVs with the pipeline extractor, never by hand:
  `scripts/utils/generate_table_csv.gen_for(slug, html, batch_folder)`.

## Golden Rule: never reduce the assets

Absolute invariant, all blogs: generated content **never** reduces the
original's asset count (`assets_after ≥ assets_before`): images, tables,
videos, internal links **and** external links (including links to competitors).
Enrich, never impoverish. Keep every existing link identical
(URL **and** anchor text), without injecting new ones. The exact scope of
counted assets is site-specific: see the site's skill. Note that **tables are
mandatory everywhere**, Superprof Ressources included (see "Tables" above) —
the Golden Rule is a floor, not a licence to emit none.

## JSON metadata

`title` (WP post_title, ≤ 60 chars), `h1` (editorial H1 of the body, may differ),
`meta_description` (150-155 chars), `target_keywords`, `word_count`, `assets`
(count images/tables/videos/internal_links), `eeat_sources` (source/url/year).

## Colored callouts forbidden

No `wp:html` with `#4caf50` (green CTA), `#fff9e6` (yellow), `#e8f4f8` (blue)
on Enseigna or Superprof Ressources: legacy system. Ref.
[[feedback-no-callouts-cta]]. (The AdvGB `advgb/infobox` blocks allowed on
Superprof Ressources are a separate mechanism; see [[sp-ressources-gutenberg]].)
