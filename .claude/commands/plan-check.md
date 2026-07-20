---
description: Valide la qualité SEO d'un content_plan.md (hiérarchie titres, couverture PAA, preuves) — déterministe, sans génération.
argument-hint: <url> --blog <id> [--plan-file path] [--json]
allowed-tools: Bash(python3 content_writer.py plan check:*), Bash(python3 content_writer.py plan init:*), Read
---

> Cycle du plan : `plan init` (scaffold + signaux injectés) → l'agent remplit
> l'outline via la skill `seo-outline` → **`plan check`** (cette commande) valide.
> `plan init` pose le fichier au bon chemin ; le CLI ne rédige jamais le contenu.

Note la qualité SEO du plan éditorial (`content_plan.md`) produit à l'étape 2bis
de `/refresh` (skill `seo-outline`). **100% déterministe** : aucune génération,
aucun appel API — la commande ne fait que *vérifier*, jamais rédiger.

Exécute :

```bash
python3 content_writer.py plan check $ARGUMENTS
```

Contrôles mécaniques appliqués (invariants de la skill `seo-outline`) :

- **Hiérarchie des titres** : ≥ 3 H2, pas de H2 ni H3 orphelin, 2-4 H3 par H2,
  subdivision requise au-delà de 150 mots, `?` sur les titres interrogatifs ;
- **Couverture PAA** : chaque question PAA de l'`audit_data.json` apparaît dans le
  plan (résolue automatiquement depuis le context_dir de l'URL) ;
- **Preuves** : ≥ 3 liens sources et ≥ 2 statistiques chiffrées placées.

Verdict :

- **OK** (exit 0) → le plan est sain, passer à la génération (étape 3 de `/refresh`) ;
- **A_CORRIGER** (exit 1) → liste des manquements ; corriger le plan (bon marché)
  **avant** de rédiger l'article, pas après.

Le plan est résolu depuis l'URL (`_shared/context/<slug>/content_plan.md`) ; passer
`--plan-file` pour pointer un fichier explicite, `--json` pour une sortie scriptable.
