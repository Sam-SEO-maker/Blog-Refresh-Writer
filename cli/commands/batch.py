"""
Batch processing commands.

Usage:
    cw batch keyword-discovery [--site enseigna.fr]
    cw batch audit-gsc [--site enseigna.fr] [--limit 10]
    cw batch audit-serp [--site enseigna.fr]
    cw batch decision [--site enseigna.fr]
    cw batch refresh --action FULL_REFRESH [--site enseigna.fr]
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


@batch.command(name='keyword-discovery')
@click.option('--spreadsheet-id', required=True, help='Google Sheet ID')
@blog_option()
def keyword_discovery(spreadsheet_id, blog):
    """
    STEP 0: Keyword Discovery.

    Fills main_keyword (col D) for URLs where it is empty.
    Cascade: ranked_keywords (vol>=50) → GSC → suggestions (vol>=100) → related_keywords → slug.
    """
    click.echo(f"\n🔍 STEP 0: KEYWORD DISCOVERY")
    if blog:
        click.echo(f"Blog: {blog}")
    click.echo()

    orchestrator = RefreshOrchestrator(
        base_path=Path.cwd(),
        spreadsheet_id=spreadsheet_id
    )

    click.echo("Discovering missing keywords...")
    try:
        results = orchestrator.batch_keyword_discovery(site_slug=blog)

        click.echo(f"\n📊 RESULTS:")
        click.echo(f"  Processed:   {results['processed']}")
        click.echo(f"  DataForSEO:  {results['dataforseo']}")
        click.echo(f"  GSC:         {results['gsc']}")
        click.echo(f"  Slug:        {results['slug']}")
        click.echo(f"  Failed:      {results['failed']}")

        if results.get('failed') > 0:
            click.echo(f"\n  ⚠ Errors:")
            for error in results.get('errors', [])[:5]:
                click.echo(f"    - {error}")

        click.echo(f"\n✅ Keyword Discovery done")

    except Exception as e:
        click.echo(f"\n❌ ERROR: {str(e)}", err=True)
        raise click.Abort()


@batch.command(name='keyword-refresh')
@click.option('--spreadsheet-id', required=True, help='Google Sheet ID')
@blog_option()
@click.option('--min-volume', default=10, type=int, show_default=True, help='Minimum accepted volume (keywords below it are re-searched)')
def keyword_refresh(spreadsheet_id, blog, min_volume):
    """
    Re-checks and improves existing keywords with insufficient volume.

    For each row with a main_keyword already filled:
    - Checks the volume via DataForSEO keyword_overview
    - If volume < MIN_VOLUME, re-runs the discovery cascade
    - Updates the spreadsheet when a better keyword is found

    Useful to fix keywords with 0-10 volume or not indexed by Ahrefs.
    """
    click.echo(f"\n🔄 KEYWORD REFRESH (volume threshold: {min_volume})")
    if blog:
        click.echo(f"Blog: {blog}")
    click.echo()

    orchestrator = RefreshOrchestrator(
        base_path=Path.cwd(),
        spreadsheet_id=spreadsheet_id
    )

    click.echo(f"Re-checking existing keywords (volume < {min_volume})...")
    try:
        results = orchestrator.batch_keyword_re_discovery(
            min_volume=min_volume,
            site_slug=blog,
        )

        click.echo(f"\n📊 RESULTS:")
        click.echo(f"  Processed:      {results['processed']}")
        click.echo(f"  Low volume:     {results['low_volume']}")
        click.echo(f"  Updated:        {results['updated']}")
        click.echo(f"  Unchanged:      {results['unchanged']}")

        if results.get('errors'):
            click.echo(f"\n  ⚠ Errors ({len(results['errors'])}):")
            for error in results['errors'][:5]:
                click.echo(f"    - {error}")

        click.echo(f"\n✅ Keyword Refresh done")

    except Exception as e:
        click.echo(f"\n❌ ERROR: {str(e)}", err=True)
        raise click.Abort()


@batch.command(name='audit-gsc')
@click.option('--spreadsheet-id', required=True, help='Google Sheet ID')
@blog_option()
@click.option('--limit', type=int, help='Maximum number of URLs')
def audit_gsc(spreadsheet_id, blog, limit):
    """
    Batch GSC audit.

    Fetches GSC data for all pending URLs.
    """
    click.echo(f"\n📊 BATCH AUDIT GSC")
    if blog:
        click.echo(f"Blog: {blog}")
    if limit:
        click.echo(f"Limit: {limit}")
    click.echo()

    # Init orchestrator
    orchestrator = RefreshOrchestrator(
        base_path=Path.cwd(),
        spreadsheet_id=spreadsheet_id
    )

    # Run batch audit GSC
    click.echo("Running batch GSC audit...")
    try:
        results = orchestrator.batch_audit_gsc(site_slug=blog)

        click.echo(f"\n📊 RESULTS:")
        click.echo(f"  Processed: {results['processed']}")
        click.echo(f"  Succeeded: {results['success']}")
        click.echo(f"  Failed:    {results['failed']}")

        if results.get('failed') > 0:
            click.echo(f"\n  ⚠ Errors:")
            for error in results.get('errors', [])[:5]:
                click.echo(f"    - {error}")

        click.echo(f"\n✅ Batch GSC done")

    except Exception as e:
        click.echo(f"\n❌ ERROR: {str(e)}", err=True)
        raise click.Abort()


@batch.command(name='audit-serp')
@click.option('--spreadsheet-id', required=True, help='Google Sheet ID')
@blog_option()
def audit_serp(spreadsheet_id, blog):
    """
    Batch SERP audit.

    Fetches PAA and secondary keywords for all URLs.
    """
    click.echo(f"\n📊 BATCH AUDIT SERP")
    if blog:
        click.echo(f"Blog: {blog}")
    click.echo()

    # Init orchestrator
    orchestrator = RefreshOrchestrator(
        base_path=Path.cwd(),
        spreadsheet_id=spreadsheet_id
    )

    # Run batch audit SERP
    click.echo("Running batch SERP audit...")
    try:
        results = orchestrator.batch_audit_serp(site_slug=blog)

        click.echo(f"\n📊 RESULTS:")
        click.echo(f"  Processed: {results['processed']}")
        click.echo(f"  Succeeded: {results['success']}")
        click.echo(f"  Failed:    {results['failed']}")

        if results.get('failed') > 0:
            click.echo(f"\n  ⚠ Errors:")
            for error in results.get('errors', [])[:5]:
                click.echo(f"    - {error}")

        click.echo(f"\n✅ Batch SERP done")

    except Exception as e:
        click.echo(f"\n❌ ERROR: {str(e)}", err=True)
        raise click.Abort()


@batch.command()
@click.option('--spreadsheet-id', required=True, help='Google Sheet ID')
@blog_option()
def decision(spreadsheet_id, blog):
    """
    Batch decision.

    Makes strategy decisions for all audited URLs.
    """
    click.echo(f"\n🎯 BATCH DECISION")
    if blog:
        click.echo(f"Blog: {blog}")
    click.echo()

    # Init orchestrator
    orchestrator = RefreshOrchestrator(
        base_path=Path.cwd(),
        spreadsheet_id=spreadsheet_id
    )

    # Run batch decision
    click.echo("Running batch decision...")
    try:
        results = orchestrator.batch_decision(site_slug=blog)

        click.echo(f"\n📊 RESULTS:")
        click.echo(f"  NO ACTION:        {results['no_action']}")
        click.echo(f"  PARTIAL REFRESH:  {results['partial_refresh']}")
        click.echo(f"  REFRESH TITLES:   {results['refresh_titles']}")
        click.echo(f"  FULL REFRESH:     {results['full_refresh']}")

        click.echo(f"\n✅ Batch decision done")

    except Exception as e:
        click.echo(f"\n❌ ERROR: {str(e)}", err=True)
        raise click.Abort()


@batch.command()
@click.option('--spreadsheet-id', required=True, help='Google Sheet ID')
@click.option('--action', required=True,
              type=click.Choice(['PARTIAL_REFRESH', 'REFRESH_TITLES', 'FULL_REFRESH']),
              help='Refresh type')
@blog_option()
@click.option('--limit', type=int, help='Maximum number of URLs to process')
def refresh(spreadsheet_id, action, blog, limit):
    """
    Batch refresh.

    Generates the content for all URLs with the given action.
    """
    click.echo(f"\n✍️  BATCH REFRESH")
    click.echo(f"Action: {action}")
    if blog:
        click.echo(f"Blog:   {blog}")
    if limit:
        click.echo(f"Limit:  {limit}")
    click.echo()

    # Init orchestrator
    orchestrator = RefreshOrchestrator(
        base_path=Path.cwd(),
        spreadsheet_id=spreadsheet_id
    )

    # Run batch refresh
    click.echo("Running batch refresh...")
    try:
        results = orchestrator.batch_refresh(action=action, site_slug=blog, limit=limit)

        click.echo(f"\n📊 RESULTS:")
        click.echo(f"  Processed:       {results['processed']}")
        click.echo(f"  Succeeded:       {results['success']}")
        click.echo(f"  Assets restored: {results.get('assets_restored', 0)}")

        if results.get('failed') > 0:
            click.echo(f"  Failed:          {results['failed']}")
            click.echo(f"\n  ⚠ Errors:")
            for error in results.get('errors', [])[:5]:
                click.echo(f"    - {error}")

        click.echo(f"\n✅ Batch refresh done")

    except Exception as e:
        click.echo(f"\n❌ ERROR: {str(e)}", err=True)
        raise click.Abort()


@batch.command(name='workflow-auto')
@click.option('--spreadsheet-id', required=True, help='Google Sheet ID')
@blog_option()
@click.option('--auto-refresh/--no-auto-refresh', default=True,
              help='Auto-run the refreshes (default: yes)')
def workflow_auto(spreadsheet_id, blog, auto_refresh):
    """
    Full automated workflow.

    Runs GSC → SERP → Decision → Refresh automatically.
    """
    click.echo(f"\n🚀 FULL AUTOMATED WORKFLOW")
    if blog:
        click.echo(f"Blog: {blog}")
    click.echo(f"Auto-refresh: {'YES' if auto_refresh else 'NO'}")
    click.echo()

    # Init orchestrator
    orchestrator = RefreshOrchestrator(
        base_path=Path.cwd(),
        spreadsheet_id=spreadsheet_id
    )

    # Run workflow auto
    click.echo("Running automated workflow...")
    try:
        results = orchestrator.batch_workflow_auto(
            site_slug=blog,
            auto_refresh=auto_refresh
        )

        # Display summary
        click.echo(f"\n{'='*70}")
        click.echo(f"📊 WORKFLOW SUMMARY")
        click.echo(f"{'='*70}")

        if results["step1_audit_gsc"]:
            gsc = results['step1_audit_gsc']
            click.echo(f"Step 1 (GSC):   {gsc['success']} succeeded / {gsc['failed']} failed")

        if results["step2_audit_serp"]:
            serp = results['step2_audit_serp']
            click.echo(f"Step 2 (SERP):  {serp['success']} succeeded / {serp['failed']} failed")

        if results["step3_decision"]:
            dec = results["step3_decision"]
            click.echo(f"Step 3 (Decision):")
            click.echo(f"  - NO ACTION:      {dec['no_action']}")
            click.echo(f"  - PARTIAL REFRESH: {dec['partial_refresh']}")
            click.echo(f"  - REFRESH TITLES:  {dec['refresh_titles']}")
            click.echo(f"  - FULL REFRESH:    {dec['full_refresh']}")

        if results["step4_refresh"]:
            click.echo(f"Step 4 (Refresh): {len(results['step4_refresh'])} actions run")

        click.echo(f"⏱️  Total duration: {results['total_duration_seconds']:.1f}s")
        click.echo(f"{'='*70}\n")

        click.echo(f"✅ Automated workflow done")

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
              default=None, help='Source HTML folder (default: _shared/outputs/{site_id}/html/)')
@click.option('--output-dir', type=click.Path(file_okay=False, path_type=Path),
              default=None, help='Destination CSV folder (default: _shared/outputs/{site_id}/csv/)')
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
      cw batch extract-tables --site-id superprof.fr-ressources --file _shared/outputs/superprof.fr-ressources/html/my-article_refreshed.html
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
        html_files = sorted(html_dir.rglob("*_refreshed.html"))
        if not html_files:
            click.echo(f"No *_refreshed.html file found in {html_dir}")
            return

    click.echo(f"\nCSV extraction - {site_id}")
    click.echo(f"Destination: {csv_dir}")
    click.echo(f"Files to process: {len(html_files)}\n")

    total_tables = 0
    files_with_tables = 0
    files_without_tables = 0

    for html_file in html_files:
        html_content = html_file.read_text(encoding="utf-8")
        file_slug = html_file.stem.removesuffix("_refreshed")
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
