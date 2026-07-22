---
description: Refresh SEO complet d'une URL (fetch WP REST/scrape → GSC/SERP/PAA/intent → décision → recherche sources → génération via subagent).
argument-hint: <url> --site <enseigna|superprof-ressources> [--strategy X] [--keyword K]
allowed-tools: Bash(python3 content_writer.py refresh:*), Bash(python3 content_writer.py finalize:*), Task, Read, Write, WebSearch, WebFetch, Skill
---

Lance le refresh de l'URL fournie en séquençant la chaîne du workflow :
récupération contenu → GSC → SERP/PAA → user intent → décision →
**recherche sources** → génération → (QC YTG / maillage en Phase 3bis).

> 🚫 **Règle non négociable — blacklist AVANT tout fetch web.** Lire
> `.claude/skills/recherche-sources/references/blacklisted-domains.md` **avant le
> premier WebFetch/WebSearch** de la session (résultats SERP compris). Un domaine
> blacklisté n'est jamais fetché, jamais retenu dans un top N, jamais cité — le tri
> se fait a priori, pas après curation. Exceptions (liens existants = Règle d'Or,
> article avis dont le sujet EST la plateforme) : voir le fichier blacklist.

## Étape 1 — Récupération + audit + décision déterministes (CLI `cw`)

Exécute :

```bash
python3 content_writer.py refresh $ARGUMENTS
```

⚠️ **Cette commande couvre déjà les étapes 1 à 6 du workflow** (via `_fetch_html`
+ `AuditEngine.full_audit` + `process_url`) ; ne PAS les refaire à la main :

- **Récupération du `post_content`** en 2 stratégies automatiques (`_fetch_html`) :
  1. **WordPress REST API** (`WordPressAPIClient`, si `wp_api_config` présent pour
     le blog),
  2. **Fallback scraping** page publique (`ContentExtractor`) quand la REST est
     bloquée.
- **Perfs SEO GSC** (clics/impressions/CTR/position, `GSCAnalyzer`, fallback
  mot-clé 12 mois),
- **Résolution du mot-clé principal** (GSC → multi-source `KeywordResolver`),
- **Analyse SERP** : PAA, features, TOP concurrents (`SERPAnalyzer`),
- **User intent** + format dominant (`IntentDetector`),
- **Décision stratégie** (moteur data-driven) + **composition du prompt**.

Sortie dans le `context_dir` affiché :

- `generation_prompt.txt` (prompt composé : stratégie + site, signaux
  GSC/SERP/PAA/intent déjà intégrés),
- chemins `Output HTML` / `Output JSON`, `Strategy`, `Assets avant`.

Si l'action est `NO_ACTION`, `BLOCKED_QUALITY_ISSUES`, `ERROR` ou
`REDIRECT_301_SUGGESTED` : **s'arrêter** et rapporter, rien à générer.

## Étape 2 — Recherche de sources (brief E-E-A-T) — la brique manquante

`cw refresh` ne va **pas** chercher de sources : sans cette étape, `eeat_sources`
serait inventé par le LLM. Avant de générer, invoquer la skill **recherche-sources**
sur le sujet/URL (cascade : bibliothèque curée par matière si dispo → complément
web `WebSearch`/`WebFetch` / `deep-research`). Produire un brief structuré
(source → claim → url → année), sans jamais fabriquer de chiffre.

> Tant que `sites/<site-slug>/sources/` n'existe pas (Phase 4), la skill opère en
> mode web seul.

## Étape 2bis — Outline éditorial optimisé (artefact vérifiable)

Avant de générer, produire un **outline traçable** dans `content_plan.md`. Objectif :
vérifier la couverture **avant** de brûler les tokens de rédaction, et rendre la
correction (si l'outline est mauvais) cent fois moins chère qu'une re-génération.

**Scaffold déterministe** — poser d'abord le squelette au bon chemin, avec les
signaux (PAA, mot-clé, intent, assets) injectés depuis `audit_data.json` :

```bash
python3 content_writer.py plan init <url> --site <site-slug>
```

Puis invoquer la skill **`seo-outline`** pour **remplir** cet outline (mapping
PAA→sections, placement des preuves, gap top 10) à partir des signaux de
`generation_prompt.txt` + le brief de sources. Le CLI a posé la structure ; l'agent
rédige les H2/H3.

La skill `seo-outline` porte le détail (mapping PAA→sections, placement des preuves,
gap concurrentiel, invariants de titres : ≥ 3 H2, pas de H2/H3 orphelin, 2-4 H3 par
H2 au-delà de 150 mots, `?` sur les titres interrogatifs).

Une fois `content_plan.md` écrit, **le valider mécaniquement** (déterministe, zéro
token) avant de générer :

```bash
python3 content_writer.py plan check <url> --site <site-slug>
```

- **OK** → passer à l'étape 3 ;
- **A_CORRIGER** → corriger le plan selon les manquements listés (bon marché), puis
  relancer `plan check`. Ne **pas** générer sur un plan `A_CORRIGER`.

Le `content_plan.md` validé est une **entrée supplémentaire** transmise au subagent à
l'étape 3 : il rédige *à partir de l'outline*, il ne le ré-invente pas.

## Étape 3 — Génération (subagent `content-generator`)

Déléguer la rédaction au subagent **content-generator** (abonnement Max, jamais
l'API payante) via l'outil Task. Lui transmettre :

- le chemin `generation_prompt.txt` (contient déjà PAA, intent, SERP, mot-clé),
- **le `content_plan.md` de l'étape 2bis** (outline validé : le subagent rédige à
  partir de ce plan, section par section),
- **le brief de sources vérifiées de l'étape 2** (à injecter dans le contenu et
  dans `eeat_sources`, pas d'invention),
- le `site_slug` (pour charger la bonne skill de rédaction),
- les chemins `Output HTML` / `Output JSON`,
- la `Strategy` et les `Assets avant` (Règle d'Or : assets après ≥ avant).

Le subagent écrit directement le HTML brut + métadonnées dans les fichiers de
sortie ; il **ne renvoie pas** de HTML dans le chat. Note le chemin du HTML brut
écrit (`Output HTML`), il est requis à l'étape 4.

## Étape 4 — Finalisation déterministe (`cw finalize`)

Une fois le HTML brut écrit, chaîner save → assets → QC YTG → maillage :

```bash
python3 content_writer.py finalize <url> --site <site-slug> --html-file <Output HTML> [--type <avis|versus>] [--keyword "<Mot-clé>"] [--guide-id <YTG guide>]
```

> **Mot-clé + guide YTG.** L'étape 1 (`cw refresh`) affiche `Mot-clé:` et
> `YTG guide:` quand le STEP 2.5 a créé un guide. **Reporter les deux** dans
> `--keyword`/`--guide-id` : le QC post-génération score alors sur le bon guide
> (le vrai mot-clé, pas le slug) et **réutilise** le guide sans le recréer
> (économie de crédits). Absents → le QC re-résout le mot-clé (fallback slug).

> **Type d'article (enseigna).** L'étape 6 du CLI `refresh` affiche une ligne
> `Type: avis|versus` quand l'URL est classée (règle : slug `superprof-vs-*` →
> versus ; slug contenant `avis` → avis ; sinon rien). Si un `Type:` est affiché,
> **le reporter tel quel dans `--type`** : la sortie HTML est alors routée dans
> `sites/enseigna/outputs/html/{type}/` et le prompt versus (`vs_concurrent.md`)
> est déjà injecté à la génération. Sans `Type:`, ne pas passer `--type`.

Cette commande (déterministe) :

- **sauvegarde** le HTML nu + `.gutenberg.html` + CSV des tableaux,
- **valide les assets** (Règle d'Or ; restaure les manquants),
- lance le **QC sémantique YTG** → verdict :
  - `OPTIMAL` → poursuit le maillage,
  - `A_CORRIGER` → renvoie les termes sous/sur-optimisés : **relancer le subagent
    content-generator** pour recorriger le HTML (boucle, cap 2-3 itérations), puis
    relancer `finalize`,
  - `BLOQUE` → **arrêt + alerte humaine** (sur-optimisation grave, pas de maillage,
    pas de re-génération auto),
- applique le **maillage** (`EnseignaAvisLinker` pour enseigna ; pour superprof les
  liens de landing sont injectés en amont par `SuperprofRotator`). Ajouter
  `--apply-linking` pour écrire les liens (sinon dry-run).

## Étape 5 — Rapport

Rapporter : stratégie appliquée, sources retenues, chemins de sortie
(`sites/<site-slug>/outputs/`), verdict YTG, verdict assets (avant/après), et
liens ajoutés. Objectif : URL → contenu + verdict + liens, sans reprise manuelle.