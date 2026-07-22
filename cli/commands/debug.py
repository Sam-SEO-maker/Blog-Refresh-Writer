"""
Debug commands.

Usage:
    cw debug workflow <url> --site enseigna.fr
    cw debug config [--site enseigna.fr]
    cw debug extract-structures --spreadsheet-id <ID>
"""

import os
import click
from cli.options import blog_option
import traceback
from pathlib import Path

import requests
from scripts.agent import RefreshOrchestrator
from _shared.config.sites import SITE_CONFIGS


@click.group()
def debug():
    """Debug utilities."""
    pass


@debug.command()
@click.argument('url')
@blog_option(required=True)
@click.option('--spreadsheet-id', default=lambda: os.environ.get('SPREADSHEET_ID'), help='Google Sheet ID (auto from .env)')
@click.option('--strategy',
              type=click.Choice([
                  'TITLE_OPTIMIZATION',
                  'PARTIAL_REFRESH',
                  'FULL_REFRESH',
                  'SEMANTIC_REORIENTATION',
                  'FORMAT_ADAPTATION',
                  'EEAT_REWRITE'
              ]),
              default='FULL_REFRESH',
              help='Forced strategy (default: FULL_REFRESH)')
def workflow(url, blog, spreadsheet_id, strategy):
    """
    Debug the full workflow with traceback.

    Migrated from debug_workflow.py.
    Runs the workflow with full error display.
    """
    click.echo(f"\n{'='*70}")
    click.echo(f"🐛 DEBUG WORKFLOW")
    click.echo(f"{'='*70}")
    click.echo(f"URL:       {url}")
    click.echo(f"Blog:      {blog}")
    click.echo(f"Strategy:  {strategy}")
    click.echo()

    # Init orchestrator
    click.echo("[1/3] Initializing orchestrator...")
    orchestrator = RefreshOrchestrator(
        base_path=Path.cwd(),
        spreadsheet_id=spreadsheet_id
    )

    # Fetch content via direct HTTP scraping
    click.echo("[2/3] Fetching content via HTTP scraping...")
    try:
        resp = requests.get(
            url,
            timeout=30,
            headers={"User-Agent": "Mozilla/5.0 (compatible; ContentWriter/1.0)"},
            allow_redirects=True,
        )
        resp.raise_for_status()
        html = resp.text
    except Exception as e:
        click.echo(f"  ✗ Could not fetch the content: {e}", err=True)
        raise click.Abort()
    click.echo(f"  ✓ HTML fetched ({len(html)} chars)")

    # Process URL
    click.echo("[3/3] Running workflow with full debug...")
    try:
        result = orchestrator.process_url(
            url=url,
            site_slug=blog,
            html_content=html,
            force_action=strategy,
            custom_prompt=None,
            provided_keyword=None
        )

        click.echo(f"\n✅ SUCCESS:")
        click.echo(f"  URL:           {result.url}")
        click.echo(f"  Success:       {result.success}")
        click.echo(f"  Action:        {result.action_taken}")
        click.echo(f"  Audit score:   {result.audit_score}")
        click.echo(f"  Assets valid:  {result.assets_valid}")
        click.echo(f"  Time:          {result.execution_time_seconds:.1f}s")

        if result.errors:
            click.echo(f"\n  ⚠ Errors ({len(result.errors)}):")
            for error in result.errors:
                click.echo(f"    - {error}")

    except Exception as e:
        click.echo(f"\n❌ ERROR CAUGHT:")
        click.echo(f"Type:    {type(e).__name__}")
        click.echo(f"Message: {str(e)}")
        click.echo(f"\nFULL TRACEBACK:")
        traceback.print_exc()
        raise click.Abort()


@debug.command()
@blog_option()
@click.option('--show-all', is_flag=True, help='Show every site')
def config(blog, show_all):
    """
    Shows the configuration.

    Checks the configs loaded from _shared/config/sites.py
    """
    click.echo(f"\n🔧 CONFIGURATION")

    if blog:
        # Afficher config d'un blog spécifique
        site_config = SITE_CONFIGS.get(blog)
        if not site_config:
            click.echo(f"❌ Unknown site slug: {blog}", err=True)
            raise click.Abort()

        click.echo(f"\nBlog: {blog}")
        click.echo(f"{'='*70}")
        click.echo(f"Domain:        {site_config.get('domain')}")
        click.echo(f"GSC Property:  {site_config.get('gsc_property')}")
        click.echo(f"Spreadsheet:   {site_config.get('sheet_id') or site_config.get('sheets_config', {}).get('spreadsheet_id')}")
        click.echo(f"YMYL:          {site_config.get('ymyl_level')}")
        click.echo(f"E-E-A-T:       {site_config.get('eeat_level')}")

    elif show_all:
        # Afficher tous les blogs
        click.echo(f"\nAll sites:")
        click.echo(f"{'='*70}")
        for site_slug, config in SITE_CONFIGS.items():
            click.echo(f"\n{site_slug}:")
            click.echo(f"  Domain:  {config.get('domain')}")
            click.echo(f"  YMYL:    {config.get('ymyl_level')}")
            click.echo(f"  E-E-A-T: {config.get('eeat_level')}")

    else:
        # Afficher résumé
        click.echo(f"\nConfigured sites: {len(SITE_CONFIGS)}")
        for site_slug in SITE_CONFIGS.keys():
            click.echo(f"  - {site_slug}")

        click.echo(f"\nUse --site <ID> to see the detailed config")
        click.echo(f"Use --show-all to see every config")


@debug.command(name='extract-structures')
@click.option('--spreadsheet-id', required=True, help='Google Sheet ID')
def extract_structures(spreadsheet_id):
    """
    Extracts the H1/H2 structures of every URL.

    Generates articles_structure_*.json for analysis.
    """
    import json
    from datetime import datetime
    from scripts.sheets import SheetsClient
    from scripts.audit import HTMLAnalyzer

    click.echo(f"\n📚 H1/H2 STRUCTURE EXTRACTION")
    click.echo(f"Spreadsheet: {spreadsheet_id}\n")

    # Read spreadsheet
    # ⚠️ L'onglet "Refreshs_Audit" est obsolète (n'existe plus dans les Sheets réels).
    # Les onglets réels sont Enseigna → "Avis"/"Versus", Superprof → "New Growing List".
    click.echo("[1/3] Reading spreadsheet...")
    sheets_client = SheetsClient(spreadsheet_id)
    sheet_data = sheets_client._read_sheet('Refreshs_Audit')
    if not sheet_data:
        click.echo(
            "[ERROR] Tab 'Refreshs_Audit' missing/empty (obsolete). "
            "Use the real tabs: 'Avis'/'Versus' (Enseigna) or "
            "'New Growing List' (Superprof).",
            err=True,
        )
        return

    articles = []
    for i, row in enumerate(sheet_data[1:], start=2):
        if len(row) > 4:
            url = row[2] if len(row) > 2 else None
            site_slug = row[0] if len(row) > 0 else None
            title = row[4] if len(row) > 4 else ""

            if url and site_slug:
                articles.append({
                    'row': i,
                    'url': url,
                    'site_slug': site_slug,
                    'title': title
                })

    click.echo(f"  ✓ {len(articles)} URLs found")

    # Fetch and extract structures
    click.echo("[2/3] Extracting H1/H2 structures...")
    analyzer = HTMLAnalyzer()

    for idx, article in enumerate(articles, 1):
        url = article['url']
        click.echo(f"  [{idx}/{len(articles)}] {url[:60]}...")

        try:
            resp = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"}, allow_redirects=True)
            html = resp.text if resp.ok else None
            if html:
                audit = analyzer.analyze_html(html, url)
                article['h1'] = audit.h1_title
                article['h2s'] = audit.h2_sections
            else:
                article['h1'] = ""
                article['h2s'] = []
        except Exception as e:
            click.echo(f"    ⚠ Error: {str(e)[:60]}")
            article['h1'] = ""
            article['h2s'] = []

    # Save to JSON
    click.echo("[3/3] Saving JSON...")
    outputs_dir = Path("outputs")
    outputs_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    json_file = outputs_dir / f"articles_structure_{timestamp}.json"

    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

    click.echo(f"  ✓ File created: {json_file}")
    click.echo(f"\n✅ Extraction done")
    click.echo(f"Structure file generated: {json_file}")
