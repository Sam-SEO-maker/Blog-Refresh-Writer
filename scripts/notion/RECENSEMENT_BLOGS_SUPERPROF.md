# Recensement des sites Superprof (Phase 6d)

Source de vérité runtime = `_shared/config/sites.json`. Ce recensement documente
les sites Superprof éligibles à devenir des sites Content Writer, pour
alimenter la page Notion « config pays » (amont) puis `sites.json` (aval, via
`sync_sites_from_notion.py`).

## Sites « Ressources » Superprof (6 sites matures)

Le blog éditorial existe dans ~90 pays (`superprof.{tld}/blog/`), mais un **site
Ressources dédié** n'existe que dans **6 sites**. Toutes les propriétés GSC
ci-dessous sont **confirmées présentes** dans `mcp gsc-remote list_properties`
(vérifié 2026-07-15).

| Pays | URL site Ressources | GSC property | Site ID (convention) | url_base | Site CW ? |
|------|---------------------|--------------|------------------------|----------|-------------|
| FR | superprof.fr/ressources/ | `https://www.superprof.fr/ressources/` | `superprof-ressources` (dérog.) | — | ✅ existant |
| ES | superprof.es/**apuntes**/ | `https://www.superprof.es/apuntes/` | `es-es-ressources` | `/apuntes/` | ❌ candidat |
| DE | superprof.de/**lernplattform**/ | `https://www.superprof.de/lernplattform/` | `de-de-ressources` | `/lernplattform/` | ❌ candidat |
| UK | superprof.co.uk/resources/ | `https://www.superprof.co.uk/resources/` | `en-uk-ressources` | `/resources/` | ❌ candidat |
| US | superprof.com/resources/ | `https://www.superprof.com/resources/` | `en-us-ressources` | `/resources/` | ❌ candidat |
| BR | superprof.com.br/recursos/ | `https://www.superprof.com.br/recursos/` | `pt-br-ressources` | `/recursos/` | ❌ candidat |

**Pièges de chemin** : ES = `/apuntes/` (pas `/recursos/`), DE = `/lernplattform/`
(pas `/ressourcen/`). Le chemin variable vit dans `url_base` (config), **jamais
dans l'ID** (convention `lang-country-type`). Ne pas confondre le site Ressources
ES `es-es-ressources` (chemin `/apuntes/`) avec le **client autonome** `apuntes`
(marque distincte).

## Onboarding d'un candidat = zéro code

Rappel architecture (Phase 4) : onboarder un site = 1 dossier `sites/<site-slug>/`
+ 1 entrée `sites.json`, **zéro code**. La résolution GSC route automatiquement
ces 5 candidats vers le MCP `gsc-remote` (domaines `superprof.*`, cf. Phase 6c) ;
enseigna reste sur le service account.

## Chaîne de sync (Phase 6d)

```
Page Notion « config pays »   (source humaine, éditée)
   │  sync unidirectionnel : python -m scripts.notion.sync_sites_from_notion --apply
   ▼
_shared/config/sites.json     (index machine UNIQUE — pas de registre séparé)
   │
   ▼
moteur (runtime)              (lit sites.json, JAMAIS Notion)
```

Le sync est **additif** : il préserve tous les champs existants et les clés
top-level ; il n'écrase que ce que Notion fournit. `--dump-schema` affiche les
propriétés réelles de la base pour caler `PROPERTY_MAP` au 1er run.

## Sites SANS site Ressources (hors périmètre Ressources)

Canada, Mexique, Italie, et tout LATAM hispanophone (AR/CL/CO/PE…) n'ont **pas**
de site Ressources. Cibles naturelles de futurs sites Ressources sur le modèle
FR : les 5 candidats ci-dessus (ES, DE, UK, US, BR).

## Blogs éditoriaux `/blog/` (90 sites) — transposabilité multi-langue

Le catalogue inclut aussi les **90 blogs `superprof.{tld}/blog/`** (le but est de
refresher tous les sites). Chaque entrée porte `country` (ISO-2) et `language`
(langue de rédaction du pays), résolus par une table exhaustive TLD→pays→langue
dans `build_superprof_catalog.py` (sous-domaines `nl.superprof.be`,
`de.superprof.ch` et domaines à trait d'union `super-prof.me/.nl` gérés à part).

**Le workflow est transposable sans « traduction » par le responsable pays** :
- Le **pipeline** (GSC, SERP, décision, QC) est agnostique à la langue.
- Les **guides éditoriaux** sont en **anglais** (méta-langue de travail des Market
  Co-ordinators) — un responsable estonien/portugais les lit tel quel.
- La **langue de sortie du contenu** est imposée EXPLICITEMENT par
  `blog_config.language` → `language_directive()` injecte « Rédige en {langue} »
  dans le prompt de génération. Un blog `et-ee-blog` produit donc en estonien,
  `pt-br-blog` en portugais, sans dépendre de la langue de la source scrapée.
- Le responsable pays adapte seulement **son `sites/<site-slug>/prompts/site.md`** et ses
  guides pays — pas le workflow.

Onboarder un blog : `cw site init <lang>-<country>-blog` (ex. `et-ee-blog`).
