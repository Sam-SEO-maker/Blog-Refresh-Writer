---
description: Perfs SEO d'une URL précise via le MCP GSC (requêtes, clics, impressions, position).
argument-hint: <url> [--days 28] [--dry-run]
allowed-tools: Bash(python3 content_writer.py audit gsc-page:*), Read
---

Récupère les performances GSC d'une **page précise** : les requêtes sur lesquelles
elle se positionne, avec clics, impressions et position, sur la fenêtre donnée.

```bash
python3 content_writer.py audit gsc-page $ARGUMENTS
```

Le site est déduit automatiquement de l'URL (aucun `--site` à passer).
Routage : superprof.* → MCP gsc-remote (fallback service account) ; le MCP
plafonne l'affichage à ~20 requêtes.

Options : `<url>` (requis), `--days` (défaut 28), `--dry-run` (pas de dump JSON).

Pour les perfs du **blog entier**, utiliser `/blog --site <site-slug>`.
Lecture seule. Rapporter un résumé compact (trafic + principales requêtes).
