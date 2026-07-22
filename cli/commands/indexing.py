"""
Indexing commands.

Usage:
    cw indexing request --site enseigna.fr [--spreadsheet-id <ID>]
    cw indexing scan --site enseigna.fr
    cw indexing bulk-diagnostic --site enseigna.fr
"""

import click
from cli.options import blog_option
from pathlib import Path

from scripts.indexing import IndexingRequester
from scripts.sheets import SheetsClient
from _shared.config.sites import SITE_CONFIGS


@click.group()
def indexing():
    """Google indexing management."""
    pass


@indexing.command()
@blog_option(required=True)
@click.option('--spreadsheet-id', required=True, help='Google Sheet ID')
def request(blog, spreadsheet_id):
    """
    Indexing request for URLs with status 'CONTENT DONE'.

    Uses the Google Indexing API to force indexing.
    """
    click.echo(f"\n📤 INDEXING REQUEST")
    click.echo(f"Blog: {blog}")
    click.echo()

    # Get blog config
    site_config = SITE_CONFIGS.get(blog)
    if not site_config:
        click.echo(f"❌ Unknown site slug: {blog}", err=True)
        raise click.Abort()

    gsc_property = site_config.get("gsc_property")

    # Get URLs with status = CONTENT DONE
    click.echo("[1/2] Reading spreadsheet...")
    sheets_client = SheetsClient(spreadsheet_id)
    rows = sheets_client.read_pending_for_refresh(action=None, site_slug=blog)
    urls_to_index = [row.blogpost_url for row in rows if row.status == "CONTENT DONE"]

    if not urls_to_index:
        click.echo("  ℹ No URL with status 'CONTENT DONE' to index")
        return

    click.echo(f"  ✓ {len(urls_to_index)} URLs to index")

    # Request indexing
    click.echo("[2/2] Requesting Google indexing...")
    requester = IndexingRequester(gsc_property)

    try:
        results = requester.batch_request_indexing(urls_to_index, delay=2.0)

        click.echo(f"\n📊 RESULTS:")
        click.echo(f"  Total:          {results['total']}")
        click.echo(f"  Succeeded:      {results['success']}")
        click.echo(f"  Failed:         {results['failed']}")
        click.echo(f"  Quota exceeded: {results['quota_exceeded']}")

        if results['failed'] > 0:
            click.echo(f"\n  ⚠ Failures (first 5):")
            for error in results.get('errors', [])[:5]:
                click.echo(f"    - {error}")

        if results['success'] > 0:
            click.echo(f"\n✅ {results['success']} URLs submitted for indexing")
        else:
            click.echo(f"\n❌ No URL successfully indexed")

    except Exception as e:
        click.echo(f"\n❌ ERROR: {str(e)}", err=True)
        raise click.Abort()


@indexing.command()
@blog_option(required=True)
@click.option('--limit', type=int, default=100, help='Maximum number of URLs to scan')
def scan(blog, limit):
    """
    Scans the indexing status of every URL of the site.

    Checks via the GSC API which URLs are indexed.
    """
    click.echo(f"\n🔍 INDEXING SCAN")
    click.echo(f"Blog:  {blog}")
    click.echo(f"Limit: {limit}")
    click.echo()

    click.echo("⚠ Feature to implement:")
    click.echo("  1. Fetch every URL of the site from the spreadsheet")
    click.echo("  2. Check the indexing status via the GSC API")
    click.echo("  3. Generate a report (indexed, not indexed, errors)")


@indexing.command(name='bulk-diagnostic')
@blog_option(required=True)
@click.option('--spreadsheet-id', required=True, help='Google Sheet ID')
def bulk_diagnostic(blog, spreadsheet_id):
    """
    Bulk indexing diagnostic.

    Runs scripts/indexing/bulk_index_diagnostic.py
    """
    click.echo(f"\n🔍 BULK INDEXING DIAGNOSTIC")
    click.echo(f"Blog: {blog}")
    click.echo()

    try:
        from scripts.indexing.bulk_index_diagnostic import main as bulk_diagnostic_main

        # Run diagnostic
        click.echo("Running diagnostic...")
        bulk_diagnostic_main()

        click.echo(f"\n✅ Diagnostic done")

    except ImportError:
        click.echo(f"❌ Module bulk_index_diagnostic not found", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"\n❌ ERROR: {str(e)}", err=True)
        raise click.Abort()
