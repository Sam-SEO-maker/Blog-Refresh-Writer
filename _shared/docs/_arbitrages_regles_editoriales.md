# Arbitrages & plan de consolidation des règles éditoriales

> État 2026-07-16. Résout les contradictions entre `_shared/docs/`, `strategies/`,
> `tenants/*/prompts/` et les skills. Décision utilisateur cadre (2026-07-16) :
> **migrer SEO/GEO/EEAT dans une skill générique et supprimer `_shared/docs/`** ;
> pour SP, **`site.md` = règles maîtresses** (déjà le seul fichier chargé),
> **`reference.md` = exemple HTML Gutenberg à imiter**.

## Vision cible (canaux de règles)

| Contenu | Destination | Statut actuel |
|---|---|---|
| SEO + GEO + EEAT (transverse, ranking) | **skill générique `edito-refresh`** (à créer) | inertes dans `/docs` |
| `_shared/docs/{SEO,GEO,EEAT}_*.md` | **supprimés** après migration | 878 lignes |
| STYLE_GUIDE §11 (SOSEO/DSEO occurrences) | skill `edito-refresh` (référence densité) | inerte |
| CONTENT_REFRESH matrice de tiers | garder (nourrit `strategy_selector`/`decide`) | partiellement dupliqué |
| OUTPUT_ARCHITECTURE | garder (doc technique infra) | ok |
| SP règles maîtresses | `site.md` (déjà seul chargé par composer) | ✓ actif |
| SP exemple à imiter | `reference.md` (23k, inerte) | chemins skill à corriger |

## Faits établis (à corriger au passage)

- **`_shared/prompts/sites/` N'EXISTE PAS** : les skills SP pointent vers des chemins morts.
  À corriger : `sp-ressources-gutenberg/SKILL.md:24-26`, `qc-sp-ressources/SKILL.md:97,120`
  → remplacer `_shared/prompts/sites/superprof-ressources-reference.md` par
  `tenants/superprof-ressources/prompts/reference.md`, et `…superprof-ressources.md`
  par `tenants/superprof-ressources/prompts/site.md`.
- Le composer ne charge QUE `tenants/{id}/prompts/site.md` (TenantPaths.site_prompt).
  `reference.md` et `tenant.json` (seo_settings…) sont **inertes** (jamais lus).

## Décisions de format (mode autonome, révocables)

- **Migration docs→skill = progressive disclosure** (pattern déjà en place dans le repo :
  `tenants/enseigna/prompts/blocks/INDEX.md` + fichiers annexes chargés à la demande).
  Structure cible :
  ```
  .claude/skills/edito-refresh/
  ├── SKILL.md            ← règles dures appliquées à CHAQUE article (~150 l.)
  └── references/
      ├── geo-strategies.md   ← 9 stratégies GEO détaillées
      ├── eeat-framework.md   ← paires ❌/✅ + signaux par pilier
      └── seo-onpage.md       ← recherche kw, liens, on-page
  ```
  `SKILL.md` = actionnable + pointeurs « voir references/X.md pour le détail ».
  `references/` = savoir détaillé, **réellement accessible** (le subagent a Read+Skill+Glob,
  vérifié), contrairement aux `_shared/docs/` actuels inertes. On ne jette PAS le savoir
  utile : on le déplace dans references/ et on ne garde dans SKILL.md que l'essentiel.
  Seul le méta pur (contexte marché, métriques à suivre, timeline, sources biblio) est jeté.
- **SP** : `site.md` reste la source maîtresse (ne rien y déplacer) ; `reference.md`
  reste l'exemple (corriger juste les chemins qui le référencent).

## Arbitrages ponctuels (tranchés, adossés à une source du repo)

| # | Sujet | Décision | Fondement |
|---|---|---|---|
| A1 | Callouts `#4caf50` | **Interdits** | format-wordpress + skills + `feedback_no_callouts_cta` ; strategies = vestige |
| A2 | Structure post-intro | **Tenant prime sur strategy** | strategies contredisent les 2 tenants |
| A3 | Emojis titres | **Tenant-spécifique** (SP oui) | `feedback_faq_question_emoji` |
| A4 | Tableaux CSV vs TablePress | **CSV défaut, TablePress SP** | `feedback_csv_naming_tablepress` |
| B5 | Densité | **Occurrences (STYLE §11 SOSEO)** | source la + détaillée/récente |
| B6 | Longueur | **Config source unique** (à câbler) | tenant.json déjà tranché — OUVERT côté code |
| B7 | Meta desc | **155 car** | format-wordpress |
| B8 | Espacement liens | **150-200 mots** | format-wordpress |
| B9 | FAQ | **3-5 défaut** + exception étendue | majorité |
| C10 | Min sources | **≥3 institutionnelles** | strategies+SP ; corrige contradiction interne EEAT |
| C11 | Bio auteur HTML | **Jamais (géré WP)** | eeat_rewrite+Enseigna |
| C12 | Déclaration indépendance | **Interdite** | `feedback_no_independence_declaration` ; nettoyer tenant.json:79 (valeur fausse) |
| C13 | Featured snippet | **2 cas** : 40-60 (snippet) / 50-100 (FAQ) | clarification |

## Séquencement d'exécution

1. **Corriger les chemins morts** dans les 2 skills SP (sûr, immédiat).
2. **Créer la skill `edito-refresh`** : condenser SEO+GEO+EEAT+STYLE§11 en consignes,
   en appliquant les arbitrages ci-dessus (occurrences, ≥3 sources, pas de bio HTML…).
3. **Câbler la skill** : la référencer dans content-generator.md (chargée pour tous tenants).
4. **Supprimer `_shared/docs/{SEO,GEO,EEAT}_*.md`** + STYLE_GUIDE (contenu migré).
   Garder CONTENT_REFRESH (matrice tiers) + OUTPUT_ARCHITECTURE (technique).
5. **Nettoyer les strategies** des règles remontées (callouts, structure, chiffres).
6. **OUVERT** : B6 (câbler tenant.json→prompt), lecture de reference.md par le subagent.

Voir mémoires [[project_regles_editoriales_3_destinations]] [[project_docs_prompts_injection_deadflow]].
