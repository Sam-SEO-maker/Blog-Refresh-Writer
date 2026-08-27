"""
`finalize` command - deterministic post-generation chain (Phase 3bis).

À lancer APRÈS que le subagent `content-generator` a écrit le HTML brut. Chaîne :
  1. save_refreshed_html()  → HTML nu + .gutenberg.html + CSV tableaux
  2. AssetManager           → valide + restaure les assets (Règle d'Or)
  3. YTGQualityCheck        → verdict OPTIMAL / NEEDS_FIX / BLOCKED
  4. Maillage               → EnseignaAvisLinker (enseigna) ; rappel directive
                              SuperprofRotator (superprof, injectée pré-génération)

La GÉNÉRATION reste hors de cette commande (subagent, abonnement Max). `finalize`
est déterministe et re-jouable : un second passage après correction d'un
NEEDS_FIX refait save → QC → maillage sans régénérer.
"""

import json
from pathlib import Path

import click
from cli.options import blog_option


@click.command()
@click.argument("url")
@blog_option(required=True, dest="site_slug")
@click.option("--html-file", "html_file", required=True,
              help="Path to the raw HTML written by the generation subagent.")
@click.option("--title", default="", help="Article title (col E); defaults to the URL slug.")
@click.option("--type", "article_type", default=None,
              help="Article subtype routing the HTML output into html/{type}/ "
                   "(enseigna: 'avis' | 'versus'). Default: no subfolder.")
@click.option("--main-keyword", "--keyword", "keyword", default="",
              help="Main keyword (YTG QC guide on the right term, not the slug). "
                   "Carry it over from the `cw refresh` output. --keyword = legacy alias.")
@click.option("--guide-id", "guide_id", default="",
              help="ID of the YTG guide already created at STEP 2.5 (reused, not "
                   "recreated). Carry it over from the `cw refresh` output.")
@click.option("--apply-linking", is_flag=True, default=False,
              help="Apply the internal linking (writes the files). Otherwise dry-run.")
@click.option("--publish/--no-publish", "publish", default=True,
              help="Publish to WordPress (REST) once QC verdict is OPTIMAL. "
                   "On by default. Refused on NEEDS_FIX/BLOCKED/SKIP verdict "
                   "unless --force-publish.")
@click.option("--force-publish", "force_publish", is_flag=True, default=False,
              help="Publish even on NEEDS_FIX/SKIP (never BLOCKED): pushes the "
                   "best draft obtained so far for human editors to finish. "
                   "Explicit opt-in, off by default.")
@click.option("--yes", "assume_yes", is_flag=True, default=True,
              help="Deprecated no-op: publish no longer prompts for confirmation.")
def finalize(url, site_slug, html_file, title, article_type, keyword, guide_id, apply_linking, publish, force_publish, assume_yes):
    """
    Post-generation chain: save → assets → YTG QC → internal linking.

    URL of the article, --site the site, --html-file the generated raw HTML.
    """
    import time
    finalize_t0 = time.perf_counter()

    base = Path.cwd()
    html_path = Path(html_file)
    if not html_path.is_absolute():
        html_path = base / html_path
    if not html_path.exists():
        click.echo(f"[ERROR] HTML not found: {html_path}", err=True)
        raise click.Abort()

    html = html_path.read_text(encoding="utf-8")
    url_slug = url.rstrip("/").rsplit("/", 1)[-1]

    click.echo(f"\n{'='*70}")
    click.echo("FINALIZE (post-generation)")
    click.echo(f"{'='*70}")
    click.echo(f"URL:  {url}")
    click.echo(f"Blog: {site_slug}")
    if article_type:
        click.echo(f"Type: {article_type}  (→ html/{article_type}/)")

    # -------------------------------------------------------------------
    # 1. Sauvegarde (nu + gutenberg + CSV)
    # -------------------------------------------------------------------
    click.echo("\n[1/4] Saving (bare + gutenberg + CSV)...")
    from scripts.utils.output_manager import OutputManager

    om = OutputManager(base_path=base)
    saved = om.save_refreshed_html(
        site_id=site_slug,
        url_slug=url_slug,
        html_content=html,
        title=title or None,
        article_type=article_type or None,
    )
    click.echo(f"  ✓ {saved}")

    # -------------------------------------------------------------------
    # 2. Validation des assets (Règle d'Or)
    # -------------------------------------------------------------------
    click.echo("\n[2/4] Validating assets (Golden Rule)...")
    assets_report = _validate_assets(base, site_slug, url, html, saved)
    click.echo(f"  {assets_report}")

    # -------------------------------------------------------------------
    # 3. QC sémantique YTG
    # -------------------------------------------------------------------
    click.echo("\n[3/4] YTG semantic QC...")
    verdict, ytg_message = _run_ytg_qc(base, site_slug, url, saved, main_keyword=keyword, guide_id=guide_id)

    # BLOCKED recouvre deux causes distinctes (cf. scripts/audit/ytg_qc.py) :
    # sur-optimisation sévère de contenu (vrai problème de fond) OU panne
    # d'infra (API YTG en erreur/429, "Analyse YTG échouée (API)") - la
    # docstring du module classe volontairement les deux ensemble, mais
    # seule la première justifie un arrêt qu'aucun --force-publish ne doit
    # franchir. La seconde n'a jamais vérifié le contenu : elle reste
    # bloquante par défaut, mais --force-publish peut la traverser (le
    # contenu peut être publiable même si l'API n'a pas pu le confirmer).
    if verdict == "BLOCKED":
        api_failure = "API)" in (ytg_message or "") or "introuvable" in (ytg_message or "")
        if api_failure and force_publish:
            click.echo(f"\n⚠ BLOCKED verdict (infra: {ytg_message}) - "
                       "bypassed by --force-publish, content not semantically verified.")
            verdict = "SKIP"
        else:
            click.echo(f"\n❌ BLOCKED verdict - stopping ({ytg_message}). "
                       "Human review required, no automatic re-generation.")
            click.echo("   Internal linking NOT applied (article cannot be finalized as is).")
            _echo_timers(base, url, finalize_t0)
            return

    # -------------------------------------------------------------------
    # 4. Maillage interne
    # -------------------------------------------------------------------
    click.echo("\n[4/4] Internal linking...")
    _run_linking(base, site_slug, url, apply_linking)

    # -------------------------------------------------------------------
    # 5. Publication WordPress (auto sur verdict OPTIMAL, --no-publish pour désactiver)
    # -------------------------------------------------------------------
    if publish:
        _maybe_publish(base, site_slug, url, url_slug, saved, verdict, assume_yes, force_publish)

    click.echo(f"\n{'='*70}")
    if verdict == "NEEDS_FIX":
        click.echo("⚠ FINALIZE OK - NEEDS_FIX verdict: the subagent must fix "
                   "the flagged terms then re-run `finalize` (loop, cap 2-3).")
    elif verdict == "SKIP":
        # SKIP = le QC n'a pas pu tourner (quota 429, mot-clé refusé en 400,
        # YTG désactivé). L'article n'est PAS validé sémantiquement, et le dire
        # comme un succès est ce qui a fait passer 3 articles du lot L71 pour
        # bons alors qu'aucun verdict n'existait.
        click.echo("⚠ FINALIZE terminé SANS QC sémantique (verdict SKIP) : "
                   "contenu et assets écrits, densité NON vérifiée. "
                   "Rejouer `finalize` quand YTG répond.")
    else:
        click.echo("✅ FINALIZE OK - article ready (content + YTG verdict + links).")
    _echo_timers(base, url, finalize_t0)
    click.echo(f"{'='*70}")


def _echo_timers(base: Path, url: str, finalize_t0: float) -> None:
    """Affiche ET persiste les durées machine de l'article.

    `refresh_started_at` est écrit à la préparation, aussi bien par `cw refresh`
    que par `cw batch refresh`, dans `_shared/context/{slug}/timing.json`.
    Les durées y sont réinjectées pour rester exploitables après coup : sans
    persistance, le temps machine par URL n'existait qu'à l'écran et disparaissait
    avec le scrollback.
    """
    import time
    from datetime import datetime

    finalize_seconds = time.perf_counter() - finalize_t0
    click.echo(f"⏱ Finalize: {_fmt_duration(finalize_seconds)}")

    try:
        from scripts.audit.ytg_qc import url_to_context_slug
        timing_path = (base / "_shared" / "context"
                       / url_to_context_slug(url) / "timing.json")
        data = json.loads(timing_path.read_text(encoding="utf-8"))
        started = data["refresh_started_at"]
        ended = datetime.now()
        total = (ended - datetime.fromisoformat(started)).total_seconds()
        click.echo(f"⏱ Full pipeline (refresh → finalize): {_fmt_duration(total)}")

        data.update({
            "finalize_ended_at": ended.isoformat(),
            "finalize_seconds": round(finalize_seconds, 1),
            "total_seconds": round(total, 1),
        })
        timing_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        pass  # pas de timing.json exploitable — durée totale omise


def _fmt_duration(seconds: float) -> str:
    """65.3 → '1m 05s' ; 42.1 → '42.1s'."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes, secs = divmod(int(round(seconds)), 60)
    if minutes < 60:
        return f"{minutes}m {secs:02d}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes:02d}m {secs:02d}s"


def _maybe_publish(base: Path, site_slug: str, url: str, url_slug: str, saved: Path,
                   verdict: str, assume_yes: bool, force_publish: bool = False) -> None:
    """Publie l'article sur WordPress via REST, uniquement si le QC est OK.

    Garde-fou restant (fort blast radius, site public) : refus si verdict
    NEEDS_FIX/SKIP, sauf --force-publish (décision du 2026-08-06 : pousser le
    meilleur brouillon obtenu pour finition par des rédacteurs humains — cf.
    memory project_finalize_autopublish_default). BLOCKED n'atteint jamais ce
    point (return plus haut dans `finalize`) : jamais publiable, même forcé.
    """
    from scripts.utils.push_to_wp import build_client, publish_article

    click.echo("\n[5/5] Publishing to WordPress (REST)...")

    # Whitelist explicite, pas blacklist : un verdict SKIP (YTG désactivé,
    # ou API en erreur/429 - cf. `_run_ytg_qc`'s except-clause) ne veut pas
    # dire "QC passée", seulement "QC pas faite". Le laisser filtrer au même
    # titre qu'OPTIMAL a publié un NEEDS_FIX réel sous un 429 (incident du
    # 2026-08-06) : seul OPTIMAL, vérifié, ouvre la publication par défaut.
    if verdict != "OPTIMAL" and not force_publish:
        click.echo(f"  ⛔ Publish refused: verdict is {verdict}, not OPTIMAL. "
                   "Fix the article, re-run `finalize --publish`, or use "
                   "--force-publish to push the current draft as-is.")
        return
    if verdict != "OPTIMAL":
        click.echo(f"  ⚠ Force-publishing despite verdict {verdict} "
                   "(--force-publish): draft pushed for human editors to finish.")

    # Contenu à pousser = .gutenberg.html adjacent au HTML nu sauvegardé.
    # `saved` est déjà nommé "*_refreshed.gutenberg.html" (voir save_refreshed_html) :
    # ne pas rajouter ".gutenberg.html" à son stem, qui le contient déjà, sous peine
    # de produire "*.gutenberg.gutenberg.html" (fichier inexistant).
    gutenberg_path = saved if saved.suffixes[-2:] == [".gutenberg", ".html"] \
        else saved.with_name(saved.stem + ".gutenberg.html")
    if not gutenberg_path.exists():
        click.echo(f"  ⛔ Cannot publish: {gutenberg_path.name} not found.")
        return

    # Le fichier a bien été converti à l'étape 1, mais le QC sémantique réécrit
    # de la prose DANS ces blocs entre-temps : une réécriture qui reconstruit le
    # HTML sans reporter les délimiteurs laisse un fichier nu sous un nom
    # `.gutenberg.html`. WP l'accepte et le range en `core/freeform` : article
    # non éditable en blocs, images et tableaux non reconnus, sur un 200.
    # Même garde que `cw push` — le seul chemin de publication qui l'avait.
    gutenberg_html = gutenberg_path.read_text(encoding="utf-8")
    if "<!-- wp:" not in gutenberg_html:
        click.echo(f"  ⛔ Cannot publish: {gutenberg_path.name} carries no "
                   "Gutenberg block delimiter (bare HTML under a .gutenberg "
                   "name). A post-conversion step stripped them - re-run the "
                   "formatter on this file before publishing.")
        return

    # Même piège, un cran plus fin : le fichier porte bien des délimiteurs, mais
    # le bloc pros/cons est resté à sa forme SOURCE (`<div class="pros-cons">`),
    # que la génération écrit et que l'étape 1 convertit normalement en
    # `wp:columns`. Une édition manuelle du `.gutenberg.html` APRÈS le dernier
    # finalize le laisse à l'état brut : WP le range alors en bloc « HTML
    # classique », non éditable en colonnes, sur un 200 parfaitement trompeur.
    if 'class="pros-cons"' in gutenberg_html:
        click.echo(f"  ⛔ Cannot publish: {gutenberg_path.name} still carries a "
                   "raw <div class=\"pros-cons\"> instead of the converted "
                   "wp:columns block (WP would store it as a classic-HTML "
                   "block, not editable as columns). Re-run the formatter on "
                   "this file before publishing.")
        return

    # Metadata (title + meta_description) : trois conventions de nommage
    # coexistent selon le chemin qui a écrit le fichier — appariement partagé
    # avec `cw push` dans `output_lookup`, pour que les deux commandes poussent
    # la même metadata pour le même article.
    from scripts.utils.output_lookup import find_metadata, strip_output_suffixes

    metadata_path = find_metadata(
        saved.parent.parent / "metadata",
        url=url,
        url_slug=url_slug,
        file_slug=strip_output_suffixes(saved.name),
    )
    if metadata_path is None:
        click.echo("  ⚠ metadata not found - "
                   "publishing the content without title/SEOPress update.")

    # Construire le client (peut échouer si wp_api_config absent pour ce site).
    try:
        client = build_client(site=site_slug, base_path=base)
    except (ValueError, FileNotFoundError, KeyError) as e:
        click.echo(f"  ⛔ WP client unavailable for '{site_slug}': {e}")
        return

    click.echo(f"  Target: {url}")
    click.echo(f"  Site: {site_slug}  |  QC verdict: {verdict}")
    click.echo(f"  Content: {gutenberg_path.name}")

    res = publish_article(
        client=client,
        site=site_slug,
        url=url,
        gutenberg_path=gutenberg_path,
        metadata_path=metadata_path,
        base_path=base,
    )
    if res["ok"]:
        attempts = res.get("attempts")
        retried = f" (after {attempts} attempts)" if attempts else ""
        click.echo(f"  ✅ Published - post id={res.get('id')}{retried}")
        if res.get("warning"):
            click.echo(f"  ⚠ {res['warning']} - open the post in the editor "
                       "and check the blocks.")
    else:
        click.echo(f"  ❌ Publish failed: {res.get('error')}")


def _validate_assets(base: Path, site_slug: str, url: str, html: str, saved: Path) -> str:
    """Valide assets_after ≥ assets_before via AssetManager + le contexte d'audit."""
    from scripts.assets.asset_manager import AssetManager

    # Assets baseline : audit_data.json du contexte (écrit à l'étape refresh)
    from scripts.audit.ytg_qc import url_to_context_slug
    slug = url_to_context_slug(url)
    audit_path = base / "_shared" / "context" / slug / "audit_data.json"
    if not audit_path.exists():
        return "baseline not found (audit_data.json missing) - validation skipped."

    try:
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
    except Exception as e:
        return f"unreadable baseline ({str(e)[:60]}) - validation skipped."

    original_assets = {"counts": audit.get("assets_counts", {})}
    if not original_assets["counts"]:
        return "empty baseline counts - validation skipped."

    # HTML original du contexte : délimite les violations blacklist (delta —
    # seuls les liens blacklistés ajoutés sont supprimables, jamais l'existant).
    original_html_path = audit_path.parent / "original.html"
    original_content = None
    if original_html_path.exists():
        try:
            original_content = original_html_path.read_text(encoding="utf-8")
        except Exception:
            original_content = None

    am = AssetManager()
    result = am.validate(
        original_assets=original_assets,
        new_content=html,
        original_content=original_content,
    )
    if getattr(result, "is_valid", True):
        return "✓ assets preserved (after ≥ before)."

    # Tentative de restauration
    restored = am.restore_missing_assets(html, original_assets, result)
    if restored != html:
        saved.write_text(restored, encoding="utf-8")
        return "missing assets restored and rewritten."
    return "⚠ missing assets NOT restorable - check manually."


def _run_ytg_qc(base: Path, site_slug: str, url: str, saved: Path,
                main_keyword: str = "", guide_id: str = "") -> tuple:
    """Lance YTGQualityCheck.check_html sur le HTML sauvegardé. Retourne (verdict, message).

    main_keyword/guide_id (issus du STEP 2.5 de `cw refresh`) évitent de re-résoudre
    le mot-clé sur le slug et de recréer un guide.
    """
    from scripts.audit.ytg_qc import (
        YTGQualityCheck, VERDICT_NEEDS_FIX, VERDICT_BLOCKED, VERDICT_SKIP,
    )

    from _shared.core.site_paths import SitePaths
    cfg_path = SitePaths(base_path=base).site_config(site_slug)
    ytg_cfg = {}
    if cfg_path.exists():
        try:
            ytg_cfg = json.loads(cfg_path.read_text(encoding="utf-8")).get("ytg", {}) or {}
        except Exception:
            ytg_cfg = {}
    if ytg_cfg.get("enabled") is False:
        click.echo("  YTG disabled for this site - QC skipped.")
        return VERDICT_SKIP, ""

    try:
        engine = YTGQualityCheck()
        html = saved.read_text(encoding="utf-8")
        res = engine.check_html(
            site_slug, url=url, html=html, ytg_config=ytg_cfg,
            main_keyword=main_keyword or "", guide_id=guide_id or "",
        )
        res.html_path = str(saved)
        engine.persist(res)
        click.echo(f"  Verdict: {res.verdict} - {res.message}")
        # Les termes à enrichir n'ont de sens que si l'action est d'enrichir :
        # les afficher sous un verdict ELAGUER enverrait le maillon suivant
        # rallonger un article déjà trop couvert.
        action = getattr(res, "action", "")
        if res.verdict == VERDICT_NEEDS_FIX:
            if action in ("ENRICHIR", "") and res.under_optimized_terms:
                click.echo(f"  Terms to enrich: {', '.join(res.under_optimized_terms[:8])}")
            if action in ("ELAGUER", "REECRIRE", "") and res.over_optimized_terms:
                click.echo(f"  Terms to reduce: {', '.join(res.over_optimized_terms[:8])}")
        return res.verdict, res.message
    except Exception as e:
        # Le QC n'a PAS tourné (429, 400, panne). Sans cette mention, l'appelant
        # affiche « FINALIZE OK » à l'identique d'un vrai passage : c'est ce qui
        # a fait passer 3 articles du lot L71 pour validés alors qu'aucun
        # verdict n'existait.
        click.echo(f"  ⚠ QC NON JOUÉ (erreur ignorée, non bloquante): {str(e)[:110]}")
        return VERDICT_SKIP, ""


def _run_linking(base: Path, site_slug: str, url: str, apply_linking: bool):
    """Applique le maillage selon le site."""
    if site_slug == "enseigna.fr":
        from scripts.linking.enseigna_avis_linker import EnseignaAvisLinker

        linker = EnseignaAvisLinker(base_path=base)
        results = linker.process(urls=[url], dry_run=not apply_linking)
        for r in results:
            if r.error:
                click.echo(f"  ⚠ {r.url} : {r.error}")
            else:
                click.echo(f"  {r.url}: {len(r.links_added)} link(s) "
                           f"{'applied' if apply_linking else 'planned (dry-run)'}")
        if not apply_linking:
            click.echo("  (dry-run - re-run with --apply-linking to write)")
    elif site_slug == "superprof.fr-ressources":
        click.echo("  Superprof: landing links are injected by "
                   "SuperprofRotator.get_prompt_directive() BEFORE generation. "
                   "Check they are present in the generated HTML.")
    else:
        click.echo(f"  No automatic internal linking wired for '{site_slug}'.")
