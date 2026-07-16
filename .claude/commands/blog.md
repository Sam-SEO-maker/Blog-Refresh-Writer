---
description: Perfs SEO d'un blog/tenant via le MCP GSC (totaux de trafic + top keywords).
argument-hint: --market <tenant-id> [--days 28] [--top-kw 20] [--dry-run]
allowed-tools: Bash(python3 content_writer.py audit gsc-perf:*), Read
---

Récupère les performances SEO d'un blog via le MCP GSC : totaux de trafic
(clics, impressions, CTR, position moyenne) + top requêtes sur la fenêtre.

```bash
python3 content_writer.py audit gsc-perf $ARGUMENTS
```

Options : `--market`/`--blog` (requis, id du tenant), `--days` (défaut 28),
`--top-kw` (défaut 20), `--dry-run` (pas de dump JSON local).

Routage automatique : superprof.* → MCP gsc-remote (fallback service account) ;
enseigna et tenants hors MCP → service account. La source utilisée est indiquée
dans le résumé (`source: mcp` ou `service_account`).

Lecture seule. Rapporter un résumé compact (totaux + quelques top requêtes).
