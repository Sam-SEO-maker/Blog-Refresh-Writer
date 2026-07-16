# Content Writer

Agent autonome de **refresh SEO multi-tenant** : optimise des contenus existants
à partir de signaux data (GSC + DataForSEO), en préservant l'identité éditoriale
de chaque tenant. Décisions data-driven (audit → décision → génération → QC → maillage).

Tenants actuels : `enseigna`, `superprof-ressources`. Le registre est ouvert
(`_shared/config/sites.json`) : onboarder un marché = `python3 content_writer.py
tenant init <id>` (squelette `tenants/{id}/` + entrée `sites.json` + sparse-checkout),
puis compléter l'éditorial. Voir [onboarding/](onboarding/README.md).

## Onboarding (nouveaux SEO Managers)

Un SEO Manager de marché (ES, UK, US, MX, ID, JP…) ne clone **que son tenant** grâce à
un git sparse-checkout : le moteur commun + son seul `tenants/{id}/`, jamais les autres
marchés. Parcours complet (en anglais) : **[onboarding/README.md](onboarding/README.md)**.

Clone recommandé (sparse) :

```bash
bash onboarding/scripts/setup_sparse.sh <tenant-id>   # ex. es-es-ressources
```

## Installation (mainteneur / clone complet)

```bash
pip install -r requirements.txt
cp .env.example .env   # puis renseigner les credentials (DataForSEO, WP, GSC…)
```

## Utilisation

Le CLI est `content_writer.py`. La liste des groupes et commandes à jour est
auto-générée par Click :

```bash
python3 content_writer.py --help
python3 content_writer.py <groupe> --help    # ex. refresh, batch, audit, tenant
python3 content_writer.py tenant list        # catalogue des marchés onboardables
python3 content_writer.py tenant init <id>   # onboarder un tenant (squelette + sparse)
```

Exemple : `python3 content_writer.py refresh <url> --blog enseigna`

## Règle d'Or (invariant)

Ne jamais réduire les assets d'un article refreshé : `assets_after ≥ assets_before`
(images, tableaux, vidéos, liens internes **et** externes, y compris vers des concurrents).

## Documentation

- **Orientation générale** (rôle, architecture, workflow, index skills/commandes) :
  [CLAUDE.md](CLAUDE.md).
- **Règles éditoriales** (SEO/GEO/E-E-A-T, forme HTML/WP) : les skills
  [`edito-refresh`](.claude/skills/edito-refresh/SKILL.md) et
  [`format-wordpress`](.claude/skills/format-wordpress/SKILL.md), chargées par le
  subagent de génération.
- **Règles par tenant** : `tenants/{id}/prompts/site.md`.
- **Architecture des sorties** : [OUTPUT_ARCHITECTURE.md](_shared/docs/OUTPUT_ARCHITECTURE.md).

## Tests

```bash
python3 -m pytest tests/ -q
```

## Licence

Projet interne, tous droits réservés.
