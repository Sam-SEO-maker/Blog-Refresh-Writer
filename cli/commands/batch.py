"""
Batch processing commands.

Usage:
    cw batch keyword-discovery [--site enseigna.fr]
    cw batch audit-gsc [--site enseigna.fr] [--limit 10]
    cw batch audit-serp [--site enseigna.fr]
    cw batch decision [--site enseigna.fr]
    cw batch refresh --action FULL_REFRESH [--site enseigna.fr] [--tab "🍼 Medium Potential"]
    cw batch workflow-auto [--site enseigna.fr] [--no-auto-refresh]
"""

import click
from cli.options import blog_option
from pathlib import Path

from scripts.agent import RefreshOrchestrator


@click.group()
def batch():
    """Batch processing from Google Sheets."""
    pass


DEFAULT_BATCH_LIMIT = 50


@batch.command()
@click.option('--spreadsheet-id', default=None,
              help='Google Sheet ID (default: the one declared in the site config)')
@click.option('--action', default='FULL_REFRESH', show_default=True,
              type=click.Choice(['PARTIAL_REFRESH', 'REFRESH_TITLES', 'FULL_REFRESH']),
              help='Refresh type')
@blog_option()
@click.option('--tab', default=None,
              help='Declared tab name (sheets.tabs of site.json), e.g. "Medium Potential". '
                   'Without it, the site default flow is used (enseigna.fr Avis/Versus).')
@click.option('--limit', type=int, default=DEFAULT_BATCH_LIMIT, show_default=True,
              help='Maximum number of URLs to process. Use --limit 0 for no cap.')
@click.option('--parallel', type=int, default=None,
              help='Prepare N articles concurrently (1-8, suggested 3). '
                   'Omit for the sequential behaviour. The YTG quota (15 req/min) '
                   'is enforced by a shared cross-process counter.')
def refresh(spreadsheet_id, action, blog, tab, limit, parallel):
    """
    Batch refresh.

    Generates the content for all URLs with the given action.

    With --tab, the URLs are read from that declared tab (config-driven layout:
    col_url/col_keyword/col_status/header_row), skipping rows whose status is
    terminal (Publié, Redirection 301, Cannibalisation de KW).

    Capped at 50 URLs by default: each one costs a WP fetch + a GSC audit +
    a SERP call + a YTG guide, all paid upfront. --limit 0 lifts the cap.

    With --parallel N, the deterministic preparation (WP fetch, GSC, SERP, YTG
    guide, prompt composition) runs for N articles at once and writes a work
    plan; the writing itself stays with the Claude Code subagents (Max plan).
    """
    if not spreadsheet_id:
        if not blog:
            raise click.UsageError("--spreadsheet-id is required when --site is not given.")
        from _shared.core.sheets_config import get_spreadsheet_id
        spreadsheet_id = get_spreadsheet_id(blog)
        if not spreadsheet_id:
            raise click.UsageError(
                f"No spreadsheet_id declared for site '{blog}' — pass --spreadsheet-id.")

    click.echo(f"\n✍️  BATCH REFRESH")
    click.echo(f"Action: {action}")
    if blog:
        click.echo(f"Blog:   {blog}")
    if tab:
        click.echo(f"Tab:    {tab}")
    click.echo(f"Limit:  {limit if limit else 'no cap'}")
    if parallel:
        click.echo(f"Parallel: {parallel} article(s) in flight")
    click.echo()

    # Init orchestrator
    orchestrator = RefreshOrchestrator(
        base_path=Path.cwd(),
        spreadsheet_id=spreadsheet_id
    )

    # Chemin parallèle : préparation concurrente + plan de travail pour l'agent.
    # La rédaction reste hors CLI (subagents Claude Code, abonnement Max).
    if parallel:
        import logging
        logging.basicConfig(level=logging.INFO, format="%(message)s")

        from scripts.agent.parallel_batch import MAX_PARALLEL
        if parallel < 1 or parallel > MAX_PARALLEL:
            raise click.UsageError(
                f"--parallel must be between 1 and {MAX_PARALLEL} "
                f"(beyond that, DataForSEO/GSC saturate without extra throughput)."
            )

        click.echo("Preparing articles in parallel...")
        try:
            results = orchestrator.batch_prepare_parallel(
                action=action, site_slug=blog, limit=limit, tab=tab, parallel=parallel
            )
        except Exception as e:
            click.echo(f"\n❌ ERROR: {str(e)}", err=True)
            raise click.Abort()

        click.echo(f"\n📊 PREPARATION RESULTS:")
        click.echo(f"  Processed: {results['processed']}")
        click.echo(f"  Prepared:  {results['prepared']}")
        click.echo(f"  Skipped:   {results['skipped']}")
        click.echo(f"  Failed:    {results['failed']}")

        for error in results.get('errors', [])[:5]:
            click.echo(f"    - {error}")

        if results['prepared'] == 0:
            click.echo(f"\n❌ No article prepared")
            raise click.exceptions.Exit(1)

        click.echo(f"\n📋 Work plan: {results['plan_path']}")
        click.echo("Next: the agent reads the plan and runs the writing subagents.")
        click.echo("Each prepared article carries its `finalize_command` "
                   "(publishes on OPTIMAL verdict) - fill in --html-file.")
        return

    # Run batch refresh
    click.echo("Running batch refresh...")
    try:
        results = orchestrator.batch_refresh(action=action, site_slug=blog, limit=limit, tab=tab)

        click.echo(f"\n📊 RESULTS:")
        click.echo(f"  Processed:       {results['processed']}")
        click.echo(f"  Succeeded:       {results['success']}")
        click.echo(f"  Assets restored: {results.get('assets_restored', 0)}")

        if results.get('failed') > 0:
            click.echo(f"  Failed:          {results['failed']}")

        errors = results.get('errors', [])
        if errors:
            click.echo(f"\n  ⚠ Errors:")
            for error in errors[:5]:
                click.echo(f"    - {error}")

        # Une sélection vide n'est jamais un succès : c'est presque toujours un
        # onglet mal orthographié ou un filtre trop strict, pas « rien à faire ».
        if errors or results['processed'] == 0:
            click.echo(f"\n❌ Batch refresh: no URL processed")
            raise click.exceptions.Exit(1)

        click.echo(f"\n✅ Batch refresh done")

    except click.exceptions.Exit:
        raise  # code de sortie déjà décidé ci-dessus, pas une erreur inattendue
    except Exception as e:
        click.echo(f"\n❌ ERROR: {str(e)}", err=True)
        raise click.Abort()


@batch.command(name='benchmark')
@blog_option(required=True)
@click.option('--source-sheet', default='GSC_Perfs',
              help="Name of the tab holding the URLs (default: GSC_Perfs)")
@click.option('--rows', default='2:16',
              help='1-indexed row range, a:b format (default: 2:16 = 15 URLs)')
@click.option('--spreadsheet-id', default=None,
              help="Spreadsheet ID (override; otherwise read from the site config)")
def benchmark(blog, source_sheet, rows, spreadsheet_id):
    """
    Benchmark of the mechanical pipeline (fetch + GSC audit + decision + sheets + context).

    Reads URLs from a tab/range, runs the automated pipeline for each URL,
    and produces a timing report (console + JSON).

    NB: the actual LLM generation is out-of-process (Claude Code operator).
    This benchmark only covers the automated part.

    Example:
      cw batch benchmark --site superprof.fr-ressources --source-sheet GSC_Perfs --rows 2:16
    """
    import logging
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    from scripts.agent.benchmark_runner import run_benchmark

    click.echo(f"\n🧪 MECHANICAL PIPELINE BENCHMARK")
    click.echo(f"Blog:          {blog}")
    click.echo(f"Source sheet:  {source_sheet}")
    click.echo(f"Row range:     {rows}")
    click.echo()

    try:
        report = run_benchmark(
            site_slug=blog,
            source_sheet=source_sheet,
            row_range=rows,
            spreadsheet_id=spreadsheet_id,
        )
    except Exception as e:
        click.echo(f"\n❌ ERROR: {str(e)}", err=True)
        raise click.Abort()

    if any(not t.success for t in report.timers):
        raise click.exceptions.Exit(1)


@batch.command(name='extract-tables')
@click.option('--site-id', default='superprof.fr-ressources', show_default=True,
              help='Site identifier (e.g. superprof.fr-ressources, enseigna.fr)')
@click.option('--input-dir', type=click.Path(exists=True, file_okay=False, path_type=Path),
              default=None, help='Source HTML folder (default: sites/{site-slug}/outputs/html/)')
@click.option('--output-dir', type=click.Path(file_okay=False, path_type=Path),
              default=None, help='Destination CSV folder (default: sites/{site-slug}/outputs/csv/)')
@click.option('--file', 'single_file', type=click.Path(exists=True, dir_okay=False, path_type=Path),
              default=None,
              help="Process a single *_refreshed.html file (exact path) instead of scanning --input-dir")
def extract_tables(site_id, input_dir, output_dir, single_file):
    """Extracts the HTML tables of the articles into CSV files for TablePress.

    Without --file: recursively scans every *_refreshed.html of the source
    folder (subfolders included) and writes one CSV per table found.
    With --file: only processes that exact file (used at the end of Phase 2,
    right after generating an article, to guarantee the extraction without
    relying on a global scan).

    Example:
      cw batch extract-tables --site-id superprof.fr-ressources
      cw batch extract-tables --site-id superprof.fr-ressources --file sites/superprof.fr-ressources/outputs/html/my-article.gutenberg.html
    """
    import logging
    logging.basicConfig(level=logging.WARNING, format="%(message)s")

    from scripts.utils.table_csv_extractor import extract_tables_to_csv

    from _shared.core.site_paths import SitePaths
    base_dir = SitePaths(base_path=Path(__file__).parents[2]).output_dir(site_id)
    html_dir = input_dir or base_dir / "html"
    csv_dir = output_dir or base_dir / "csv"

    if single_file:
        html_files = [single_file]
    else:
        if not html_dir.exists():
            click.echo(f"Folder not found: {html_dir}", err=True)
            raise click.Abort()
        # Le HTML nu est supprime par OutputManager._cleanup_bare_html des que
        # le .gutenberg.html existe : chercher *_refreshed.html seul ne ramenait
        # plus rien. On prend les deux, en ignorant un nu doublonne par son
        # gutenberg pour ne pas extraire deux fois les memes tableaux.
        gutenberg = sorted(html_dir.rglob("*.gutenberg.html"))
        bare = [
            f for f in sorted(html_dir.rglob("*_refreshed.html"))
            if not f.name.endswith(".gutenberg.html")
            and f.with_suffix("").with_suffix(".gutenberg.html") not in gutenberg
        ]
        html_files = sorted(gutenberg + bare)
        if not html_files:
            click.echo(f"No *.gutenberg.html or *_refreshed.html file found in {html_dir}")
            return

    click.echo(f"\nCSV extraction - {site_id}")
    click.echo(f"Destination: {csv_dir}")
    click.echo(f"Files to process: {len(html_files)}\n")

    total_tables = 0
    files_with_tables = 0
    files_without_tables = 0

    for html_file in html_files:
        html_content = html_file.read_text(encoding="utf-8")
        # Noms reels : "<slug>.html_refreshed.gutenberg.html" ou "<slug>_refreshed.html".
        # Sans nettoyer .gutenberg / .html, le slug polluait le nom des CSV.
        file_slug = (
            html_file.name
            .removesuffix(".html")
            .removesuffix(".gutenberg")
            .removesuffix("_refreshed")
            .removesuffix(".html")
        )
        csv_files = extract_tables_to_csv(html_content, csv_dir, file_slug)

        if csv_files:
            files_with_tables += 1
            total_tables += len(csv_files)
            click.echo(f"  ✓ {file_slug} → {len(csv_files)} table(s)")
        else:
            files_without_tables += 1
            click.echo(f"  - {file_slug} → 0 tables (no <table> tag)")

    click.echo(f"\nResult: {total_tables} tables extracted "
               f"({files_with_tables} articles with tables, "
               f"{files_without_tables} without)")
