---
description: Audit d'une URL — SERP (PAA, secondary keywords) ou état GSC/Ahrefs.
argument-hint: serp <url> [--main-keyword K]  |  gsc-state --site <site-slug>
allowed-tools: Bash(python3 content_writer.py audit:*), Read
---

Lance un audit ciblé (lecture seule, sans effet de bord).

```bash
python3 content_writer.py audit $ARGUMENTS
```

Sous-commandes utiles :

- `audit serp <url> [--main-keyword K]` — PAA, secondary keywords, features SERP.
- `audit gsc-state --site <site-slug>` — état des lieux SEO GSC (KW positionnés top-N).
- `audit ahrefs-state` — état des lieux via Ahrefs.

Rapporter le résultat de façon compacte (pas de dump brut).
