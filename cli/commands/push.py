"""
`push` command - re-publish an article ALREADY VALIDATED by `finalize`.

Publication stays gated on validation: an article reaches WordPress only once
`finalize` has run its chain (save → assets → YTG QC → linking) and recorded an
OPTIMAL verdict. This command does not bypass that gate — it re-reads the
verdict `finalize` persisted in the article context and refuses to publish
anything that was never validated.

What it avoids is re-running the whole chain just to push again after a manual
fix: that would re-spend the YTG quota (15 req/min, shared counter) on an
article whose QC has already passed, and rewrite files edited by hand.

`finalize` remains the normal path to publication, and the only one that can
validate. `push` only replays the last step of it.

Usage:
    cw push <url> --site superprof.fr-ressources
    cw push <url> --site enseigna.fr --type avis
    cw push <url> --site enseigna.fr --html-file path/to/file.gutenberg.html
    cw push <url> --site superprof.fr-ressources --dry-run
"""

import json
from pathlib import Path

import click

from cli.options import blog_option


@click.command()
@click.argument("url")
@blog_option(required=True, dest="site_slug")
@click.option("--html-file", "html_file", default=None,
              help="Exact .gutenberg.html to push. Skips discovery — use it "
                   "whenever the article has several output files.")
@click.option("--type", "article_type", default=None,
              help="Article subtype narrowing discovery to html/{type}/ "
                   "(enseigna.fr: 'avis' | 'versus').")
@click.option("--status", default="publish", show_default=True,
              type=click.Choice(["publish", "draft", "pending", "private"]),
              help="Target WP status.")
@click.option("--post-id", "post_id", type=int, default=None,
              help="Explicit WP post ID. Otherwise the ID recorded at fetch "
                   "time is reused, then the URL slug is resolved.")
@click.option("--dry-run", is_flag=True, default=False,
              help="Resolve the file and the target post, then stop without writing.")
@click.option("--force-publish", "force_publish", is_flag=True, default=False,
              help="Publish despite a NEEDS_FIX/SKIP verdict (never BLOCKED): "
                   "pushes the current draft for human editors to finish. "
                   "Explicit opt-in, off by default.")
def push(url, site_slug, html_file, article_type, status, post_id, dry_run, force_publish):
    """
    Re-publish an article already validated by `finalize` (no regeneration).

    URL of the live article, --site the site. The content pushed is the
    .gutenberg.html found in the site outputs, or --html-file if given.
    Refused unless `finalize` recorded an OPTIMAL verdict for this article.
    """
    base = Path.cwd()

    click.echo(f"\n{'='*70}")
    click.echo("PUSH TO WORDPRESS")
    click.echo(f"{'='*70}")
    click.echo(f"URL:  {url}")
    click.echo(f"Site: {site_slug}")

    # ------------------------------------------------------------------
    # 1. Résolution du fichier à pousser
    # ------------------------------------------------------------------
    if html_file:
        gutenberg_path = Path(html_file)
        if not gutenberg_path.is_absolute():
            gutenberg_path = base / gutenberg_path
        if not gutenberg_path.exists():
            click.echo(f"[ERROR] File not found: {gutenberg_path}", err=True)
            raise click.Abort()
    else:
        gutenberg_path = _discover_gutenberg(base, site_slug, url, article_type)
        if gutenberg_path is None:
            raise click.Abort()

    click.echo(f"Content: {gutenberg_path}")

    # Un fichier sans délimiteur de bloc est du HTML nu : le pousser publie
    # un article que l'éditeur affichera en bloc « HTML classique ».
    content = gutenberg_path.read_text(encoding="utf-8")
    if "<!-- wp:" not in content:
        click.echo("[ERROR] This file carries no Gutenberg block delimiter. "
                   "Run `cw finalize` to convert it before pushing.", err=True)
        raise click.Abort()

    # ------------------------------------------------------------------
    # 2. Verdict QC — la publication reste conditionnée à la validation
    # ------------------------------------------------------------------
    verdict, qc_html_path = _read_qc_verdict(base, url)
    if verdict is None:
        click.echo("[ERROR] No QC verdict recorded for this article: it has "
                   "never been validated by `finalize`.", err=True)
        click.echo("        Run `cw finalize` first - it validates AND publishes.",
                   err=True)
        raise click.Abort()

    click.echo(f"QC verdict: {verdict}")

    # Le verdict porte sur un fichier précis. Pousser un autre fichier sous
    # couvert de ce verdict republierait un contenu jamais analysé — le cas
    # typique étant un .gutenberg.html d'une passe antérieure resté sur disque.
    if qc_html_path and Path(qc_html_path).resolve() != gutenberg_path.resolve():
        click.echo("[ERROR] The recorded verdict covers a different file:", err=True)
        click.echo(f"          validated: {qc_html_path}", err=True)
        click.echo(f"          about to push: {gutenberg_path}", err=True)
        click.echo("        Re-run `cw finalize` on this file, or pass "
                   "--html-file with the validated one.", err=True)
        raise click.Abort()

    # BLOCKED n'est jamais publiable, même forcé : c'est la règle de `finalize`
    # (return anticipé avant toute publication), et un chemin de republication
    # qui la relâcherait rendrait la garde contournable par simple changement
    # de commande.
    if verdict == "BLOCKED":
        click.echo("[ERROR] BLOCKED verdict - never publishable. "
                   "Human review required.", err=True)
        raise click.Abort()

    # Whitelist explicite, alignée sur `_maybe_publish` : un SKIP signifie
    # « QC pas faite », pas « QC passée ».
    if verdict != "OPTIMAL" and not force_publish:
        click.echo(f"[ERROR] Publish refused: verdict is {verdict}, not OPTIMAL.",
                   err=True)
        click.echo("        Fix the article and re-run `cw finalize`, or use "
                   "--force-publish to push the current draft as-is.", err=True)
        raise click.Abort()
    if verdict != "OPTIMAL":
        click.echo(f"⚠ Force-publishing despite verdict {verdict} "
                   "(--force-publish): draft pushed for human editors to finish.")

    # ------------------------------------------------------------------
    # 3. Metadata (title + SEOPress)
    # ------------------------------------------------------------------
    url_slug = url.rstrip("/").rsplit("/", 1)[-1]
    metadata_path = _discover_metadata(gutenberg_path, url_slug, url)
    if metadata_path:
        click.echo(f"Metadata: {metadata_path.name}")
    else:
        click.echo("Metadata: none found - title/SEOPress left untouched.")

    # ------------------------------------------------------------------
    # 4. Client + cible
    # ------------------------------------------------------------------
    from scripts.utils.push_to_wp import build_client, publish_article, resolve_wp_post_id

    try:
        client = build_client(site=site_slug, base_path=base)
    except (ValueError, FileNotFoundError, KeyError) as e:
        click.echo(f"[ERROR] WP client unavailable for '{site_slug}': {e}", err=True)
        raise click.Abort()

    target_id = post_id or resolve_wp_post_id(url, base)
    click.echo(f"Target post: "
               f"{f'id={target_id}' if target_id else 'resolved by URL slug'}")
    click.echo(f"Status: {status}")

    if dry_run:
        click.echo("\n[dry-run] Nothing written. Re-run without --dry-run to publish.")
        return

    # ------------------------------------------------------------------
    # 5. Publication
    # ------------------------------------------------------------------
    click.echo("\nPublishing...")
    res = publish_article(
        client=client,
        site=site_slug,
        url=url,
        gutenberg_path=gutenberg_path,
        metadata_path=metadata_path,
        base_path=base,
        status=status,
        post_id=post_id,
    )

    if res["ok"]:
        attempts = res.get("attempts")
        retried = f" (after {attempts} attempts)" if attempts else ""
        click.echo(f"✅ Published - post id={res.get('id')}{retried}")
        if res.get("warning"):
            click.echo(f"⚠ {res['warning']} - open the post in the editor "
                       "and check the blocks.")
    else:
        click.echo(f"❌ Publish failed: {res.get('error')}", err=True)
        raise click.exceptions.Exit(1)


def _read_qc_verdict(base: Path, url: str):
    """Relit le verdict QC que `finalize` a persisté pour cet article.

    Source : le bloc `ytg_qc` de `_shared/context/{slug}/audit_data.json`,
    écrit par `YTGQualityCheck.persist()` à l'étape QC de `finalize`. C'est ce
    qui permet à `push` de rester soumis à la validation plutôt que de la
    court-circuiter.

    Returns:
        (verdict, html_path) — (None, None) si l'article n'a jamais été validé.
    """
    try:
        from scripts.audit.ytg_qc import url_to_context_slug

        audit_path = (base / "_shared" / "context"
                      / url_to_context_slug(url) / "audit_data.json")
        if not audit_path.exists():
            return None, None
        data = json.loads(audit_path.read_text(encoding="utf-8"))
        qc = data.get("ytg_qc") or {}
        verdict = qc.get("verdict")
        if not verdict:
            return None, None
        return verdict, qc.get("html_path") or None
    except Exception:
        return None, None


def _discover_gutenberg(base: Path, site_slug: str, url: str,
                        article_type: str = None) -> Path:
    """Trouve le .gutenberg.html de l'article dans les sorties du site.

    La découverte est volontairement stricte et refuse l'ambiguïté. Les
    dossiers de sortie accumulent les fichiers d'anciennes passes ; un tri
    par nom ou par date sortirait un fichier antérieur, et publier la version
    d'avant QC est indétectable une fois en ligne. Face à plusieurs candidats
    on liste et on s'arrête : `--html-file` tranche.
    """
    from _shared.core.site_paths import SitePaths

    html_dir = SitePaths(base_path=base).output_dir(site_slug) / "html"
    if article_type:
        html_dir = html_dir / article_type
    if not html_dir.exists():
        click.echo(f"[ERROR] Output folder not found: {html_dir}", err=True)
        return None

    url_slug = url.rstrip("/").rsplit("/", 1)[-1]
    if url_slug.endswith(".html"):
        url_slug = url_slug[:-5]

    candidates = sorted(html_dir.rglob("*.gutenberg.html"))
    if not candidates:
        click.echo(f"[ERROR] No .gutenberg.html file in {html_dir}", err=True)
        return None

    # Appariement par préfixe uniquement. Une correspondance par simple
    # inclusion rapprochait des articles distincts — l'URL `conjugaison.html`
    # ramenait `modes-de-conjugaison...`, c'est-à-dire un autre article publié
    # sans que rien ne le signale. Un slug qui ne préfixe aucun fichier est un
    # cas à trancher à la main, pas à deviner.
    matches = [p for p in candidates if p.name.startswith(url_slug)]

    if len(matches) == 1:
        return matches[0]

    if not matches:
        click.echo(f"[ERROR] No file matching '{url_slug}' in {html_dir}.", err=True)
        near = [p for p in candidates if url_slug in p.name]
        if near:
            click.echo("        Files containing that slug (NOT auto-selected, "
                       "they may be different articles):", err=True)
            for p in near[:5]:
                click.echo(f"          {p.relative_to(base)}", err=True)
        click.echo("        Pass --html-file with the exact path.", err=True)
        return None

    click.echo(f"[ERROR] {len(matches)} files match '{url_slug}' - ambiguous:", err=True)
    for m in matches[:10]:
        click.echo(f"          {m.relative_to(base)}", err=True)
    click.echo("        Pass --html-file to pick one.", err=True)
    return None


def _discover_metadata(gutenberg_path: Path, url_slug: str, url: str = "") -> Path:
    """Apparie le JSON de metadata au fichier poussé (cf. `output_lookup`)."""
    from scripts.utils.output_lookup import (
        find_metadata, metadata_dir_for, strip_output_suffixes,
    )

    return find_metadata(
        metadata_dir_for(gutenberg_path),
        url=url,
        url_slug=url_slug,
        file_slug=strip_output_suffixes(gutenberg_path.name),
    )
