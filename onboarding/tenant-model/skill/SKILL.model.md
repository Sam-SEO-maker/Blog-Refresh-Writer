---
name: <your-writing-skill-name>
description: >-
  Writes/refreshes a <your market> article in the format your WordPress expects.
  Describe here, in 2-3 sentences, what the skill enforces (format, mandatory blocks,
  tone, language) so the subagent knows when and how to apply it.
  Invoke via /<your-writing-skill-name>.
disable-model-invocation: true
---

# Article generation — <your market>

<!--
MINIMAL TECHNICAL scaffold — it fixes only what the engine requires, not how to write.
The content of this skill is YOUR market SEO/editorial expertise: it's yours to write,
there is no "correct model" to replicate.

Non-negotiable constraints (everything else is up to you):
- File: tenants/<your-id>/.claude/skills/<your-writing-skill-name>/SKILL.md
- Front-matter: `name:` + `description:` (the description tells the engine WHEN to apply it).
- `name:` MUST match `generation_skill` in your tenant.json — that's the link between them.

A fully worked example exists (the superprof-ressources tenant's skill) but it isn't on
your disk and carries no normative weight; ask the maintainer only if you want to see one
concrete implementation.
-->

<!-- From here on, write your market's editorial rules freely. Structure, tone, format,
     sources: your call. Blank canvas, by design. -->

> Useful reminder: the **cross-cutting** rules (SEO/GEO/E-E-A-T ranking, generic WP
> formatting) already live in the root skills `edito-refresh` and `format-wordpress` and
> apply to everyone. No need to restate them here — your skill carries only what's
> *specific* to your market.
