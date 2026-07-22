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
@click.option("--publish", is_flag=True, default=False,
              help="Publish to WordPress (REST) after QC OK. Blast radius: "
                   "human confirmation required. Refused on NEEDS_FIX/BLOCKED verdict.")
@click.option("--yes", "assume_yes", is_flag=True, default=False,
              help="Skip the interactive publish confirmation (informed batch usage).")
def finalize(url, site_slug, html_file, title, article_type, keyword, guide_id, apply_linking, publish, assume_yes):
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
    verdict = _run_ytg_qc(base, site_slug, url, saved, main_keyword=keyword, guide_id=guide_id)

    # BLOCKED = problème de fond → arrêt + alerte humaine (pas de maillage)
    if verdict == "BLOCKED":
        click.echo("\n❌ BLOCKED verdict - stopping. Severe over-optimization: "
                   "human review required, no automatic re-generation.")
        click.echo("   Internal linking NOT applied (article cannot be finalized as is).")
        _echo_timers(base, url, finalize_t0)
        return

    # -------------------------------------------------------------------
    # 4. Maillage interne
    # -------------------------------------------------------------------
    click.echo("\n[4/4] Internal linking...")
    _run_linking(base, site_slug, url, apply_linking)

    # -------------------------------------------------------------------
    # 5. Publication WordPress (optionnelle, --publish) — fort blast radius
    # -------------------------------------------------------------------
    if publish:
        _maybe_publish(base, site_slug, url, url_slug, saved, verdict, assume_yes)

    click.echo(f"\n{'='*70}")
    if verdict == "NEEDS_FIX":
        click.echo("⚠ FINALIZE OK - NEEDS_FIX verdict: the subagent must fix "
                   "the flagged terms then re-run `finalize` (loop, cap 2-3).")
    else:
        click.echo("✅ FINALIZE OK - article ready (content + YTG verdict + links).")
    _echo_timers(base, url, finalize_t0)
    click.echo(f"{'='*70}")


def _echo_timers(base: Path, url: str, finalize_t0: float) -> None:
    """Affiche la durée du finalize et, si disponible, celle du pipeline complet.

    Le départ du pipeline (`refresh_started_at`) est écrit par `cw refresh` dans
    `_shared/context/{slug}/timing.json`. Absent (finalize rejoué seul, contexte
    archivé…) → seule la durée du finalize est affichée.
    """
    import time
    from datetime import datetime

    click.echo(f"⏱ Finalize: {_fmt_duration(time.perf_counter() - finalize_t0)}")

    try:
        from scripts.audit.ytg_qc import url_to_context_slug
        timing_path = (base / "_shared" / "context"
                       / url_to_context_slug(url) / "timing.json")
        started = json.loads(timing_path.read_text(encoding="utf-8"))["refresh_started_at"]
        total = (datetime.now() - datetime.fromisoformat(started)).total_seconds()
        click.echo(f"⏱ Full pipeline (refresh → finalize): {_fmt_duration(total)}")
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
                   verdict: str, assume_yes: bool) -> None:
    """Publie l'article sur WordPress via REST, uniquement si le QC est OK.

    Garde-fous (fort blast radius, site public) :
    - refus si verdict NEEDS_FIX ou BLOCKED (BLOCKED n'atteint jamais ce point) ;
    - confirmation humaine explicite avant le POST, sauf --yes.
    """
    from scripts.utils.push_to_wp import build_client, publish_article

    click.echo("\n[5/5] Publishing to WordPress (REST)...")

    if verdict == "NEEDS_FIX":
        click.echo("  ⛔ Publish refused: NEEDS_FIX verdict. "
                   "Fix the article then re-run `finalize --publish`.")
        return

    # Contenu à pousser = .gutenberg.html adjacent au HTML nu sauvegardé.
    gutenberg_path = saved.with_name(saved.stem + ".gutenberg.html")
    if not gutenberg_path.exists():
        click.echo(f"  ⛔ Cannot publish: {gutenberg_path.name} not found.")
        return

    # Metadata (title + meta_description) — save_metadata() nomme par url_slug,
    # save_refreshed_html() par file_slug (issu du titre) : les deux peuvent
    # différer. On tente les deux, puis un fallback glob si un seul candidat.
    meta_dir = saved.parent.parent / "metadata"
    file_slug = saved.stem[: -len("_refreshed")] if saved.stem.endswith("_refreshed") else saved.stem
    metadata_path = None
    for cand in (meta_dir / f"{url_slug}_metadata.json",
                 meta_dir / f"{file_slug}_metadata.json"):
        if cand.exists():
            metadata_path = cand
            break
    if metadata_path is None and meta_dir.exists():
        candidates = list(meta_dir.glob("*_metadata.json"))
        if len(candidates) == 1:
            metadata_path = candidates[0]
    if metadata_path is None:
        click.echo("  ⚠ metadata not found - "
                   "publishing the content without title/SEOPress update.")

    # Construire le client (peut échouer si wp_api_config absent pour ce site).
    try:
        client = build_client(site=site_slug, base_path=base)
    except (ValueError, FileNotFoundError, KeyError) as e:
        click.echo(f"  ⛔ WP client unavailable for '{site_slug}': {e}")
        return

    # Confirmation humaine — le seul Y/N qui doit subsister (blast radius).
    click.echo(f"  Target: {url}")
    click.echo(f"  Site: {site_slug}  |  QC verdict: {verdict}")
    click.echo(f"  Content: {gutenberg_path.name}")
    if not assume_yes:
        if not click.confirm("  ⚠ PUBLISH to the public site now?", default=False):
            click.echo("  Publish cancelled by the user.")
            return

    res = publish_article(
        client=client,
        site=site_slug,
        url=url,
        gutenberg_path=gutenberg_path,
        metadata_path=metadata_path,
        base_path=base,
    )
    if res["ok"]:
        click.echo(f"  ✅ Published - post id={res.get('id')}")
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
                main_keyword: str = "", guide_id: str = "") -> str:
    """Lance YTGQualityCheck.check_html sur le HTML sauvegardé. Retourne le verdict.

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
        return VERDICT_SKIP

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
        if res.verdict == VERDICT_NEEDS_FIX and res.under_optimized_terms:
            click.echo(f"  Terms to enrich: {', '.join(res.under_optimized_terms[:8])}")
        if res.verdict == VERDICT_NEEDS_FIX and res.over_optimized_terms:
            click.echo(f"  Terms to reduce: {', '.join(res.over_optimized_terms[:8])}")
        return res.verdict
    except Exception as e:
        click.echo(f"  Non-blocking QC, error ignored: {str(e)[:120]}")
        return VERDICT_SKIP


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
