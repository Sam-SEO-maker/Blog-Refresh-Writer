# Brief de reprise — Refonte orchestrateur (à coller en session fraîche)

## État au 2026-07-15 (fin de session)

Repo : `/Users/samuel/Desktop/Claude Code/Content Writer` (git, remote `origin` = github.com/Sam-SEO-maker/content-writer).

**Phases 0 → 5 de la refonte sont TERMINÉES et mergées dans `main`** :
- `a0cfc48` — Phase 5 (#2) : CLAUDE.md 668→99 lignes + consolidation _shared/docs (12→8)
- `bbfe0ff` — Phases 0→4bis (#1) : skills, commandes, subagent, monorepo tenants/{id}/, dé-hardcode

`main` local et `origin/main` sont synchronisés, working tree propre.

## Ce qui a été livré (Phases 0→5)

- **0** : `.claudeignore`.
- **1** : 5 skills `.claude/skills/` (generate-enseigna-avis, sp-ressources-gutenberg, format-wordpress, qc-sp-ressources, recherche-sources).
- **2** : réduction à 2 stratégies (full_refresh + eeat_rewrite), fix bug fallback FULL_REFRESH (ghostwriter), PromptComposer à 2 niveaux.
- **3** : slash commands `.claude/commands/` (refresh/batch/audit/decide/market-status), subagent `.claude/agents/content-generator.md`, permissions.
- **3bis** : commande `cw finalize` (save → assets → QC YTG → maillage), câblage `/refresh` → finalize.
- **4** : monorepo **`tenants/{id}/`** (prompts/site.md, config/tenant.json, linking_maps/, outputs/), résolveur **`_shared/core/tenant_paths.py`** (point unique des chemins), normalisation domaine→id, dé-hardcode des 13 scripts superprof, CODEOWNERS.
- **4bis-A** : layout Sheet externalisé par tenant (bloc `sheets` dans tenant.json).
- **4bis-B** : `auth_mode` service_account|oauth_user (`_shared/core/google_auth.py`).
- **5** : CLAUDE.md = index d'orientation ; docs consolidés (E-E-A-T canonique = EEAT_GUIDE.md).

## Architecture clé (à connaître pour reprendre)

- **Onboarder un tenant = 1 dossier `tenants/{id}/` + 1 entrée `_shared/config/sites.json`, ZÉRO code** (vérifié en Phase 4 avec un tenant factice).
- **Résolution des chemins** : tout passe par `TenantPaths` (site_prompt, blog_config, blog_config_files, linking_maps_dir, output_dir, output_dirs). Le layout monorepo n'est connu que de ce module.
- **Convention de nommage tenants** (tranchée) : Superprof pays = `lang-country-type` (`es-es-ressources`, `en-uk-ressources`) ; client autonome = slug marque (`enseigna`, `apuntes`). `superprof-ressources` = dérogation historique. Chemin URL variable → `url_base`, jamais dans l'ID. Voir mémoire `reference_tenant_naming_convention`.
- **CLI réel** : `python3 content_writer.py <groupe> <cmd>` (pas `cw` : shebang cassé CRLF).
- **Génération = subagent Claude Code (Max), jamais l'API payante.**
- **Piège doc_cache** : `get_combined_guidelines()` injecte CLAUDE.md + STYLE_GUIDE + COCONS + E-E-A-T/SEO/GEO dans le prompt de génération. Si tu touches CLAUDE.md ou ces docs, vérifier que le générateur ne perd rien.

## CE QUI RESTE À FAIRE (par priorité)

### Phase 6 — Multi-tenant runtime + Notion (prochaine phase du plan)
- Alias `--market` (= `--blog`) dans les commandes CLI.
- Flag `--publish` sur `cw refresh` (branche `push_to_wp.py`, déjà dé-hardcodé) — blast radius, confirmation humaine.
- Migration GSC service-account → MCP `gsc-remote` (chantier progressif : PoC comparatif → bascule méthode par méthode → suppression SA). `GSCAnalyzer` devient un adaptateur fin.
- Sync unidirectionnel page Notion « config pays » → `sites.json` (NOTION_TOKEN en .env, curl). Recensement blogs Superprof pays (WebFetch superprof.fr/blog/superprof-dans-le-monde/ + les 6 sites Ressources connus, voir mémoire `reference_superprof_ressources_sites_par_pays`).

### Dettes documentées (hors périmètre à l'époque)
- **§4bis-C** : mapping skill→tenant hardcodé dans `.claude/agents/content-generator.md` (L~33). À externaliser en champs `generation_skill`/`qc_skill` par tenant + migration des skills métier sous `tenants/{id}/.claude/skills/` (discovery scopée). Voir mémoire `project_multimarket_skill_decoupling`.
- **§4bis-A résiduel** : scripts Sheet single-tenant autonomes non rewirés (`sheets_client.ENSEIGNA_TABS`, `prepare_weekly_batch` NGL_SHEET, `keyword_discovery_growing_list`, `update_planning_sp_ressources`). Le layout autoritatif EST externalisé et lu par `keyword_resolver`.
- **Biblio `recherche-sources`** : socle `tenants/{id}/sources/{matière}.md` à construire (skill existe, mode web seul aujourd'hui).

### Hygiène
- **9 branches locales redondantes** à supprimer (déjà dans main via squash) : phase0/2/3/3bis/3bis-old/4/4.1/4.2/5. `git branch -D` est en deny — à faire manuellement ou lever le deny.
- **36 tests en échec PRÉEXISTANTS** (pas la refonte) : DiffEngine API (`calculate_similarity`), fixtures HTMLAnalyzer (TypeError), condition-eval, dossier `json` vs `metadata` dans test_output_manager. Un vert franc serait sain pour ne plus masquer les vraies régressions.

### Rappel en attente
- `pending_eeat_level` : ajouter `eeat_level: HIGH` aux 2 tenants après la 1re production de contenu validée.

## Règles d'or (non négociables, valables pour toute la refonte)
1. Une phase à la fois, arrêt + vérification après chacune.
2. Génération = subagent Max, jamais l'API payante, jamais de HTML dans le chat.
3. CLAUDE.md déjà réécrit (Phase 5) — ne plus le réécrire en masse.
4. Commit/push seulement sur demande explicite.
5. Mode batch autonome : ne pas poser de question, investiguer (code/config/git/mémoires) et trancher, documenter la décision.

## Fichiers plan (source de vérité)
- `MULTI_MARKET_ORCHESTRATOR_PLAN.md` — architecture + séquencement (Phases 5-6 en détail).
- `BRIEF_SIMPLIFICATION_PLAN.md` — Étape 0 + briefs A→F.
- `REFONTE_KICKOFF_BRIEF.md` — tableau des phases.

## Première action en session fraîche
Vérifier `git status` (doit être sur `main`, propre, synchro origin). Lire les mémoires projet pertinentes. Puis décider avec l'utilisateur : Phase 6, une dette précise (§4bis-C), ou l'hygiène (tests verts / nettoyage branches).
