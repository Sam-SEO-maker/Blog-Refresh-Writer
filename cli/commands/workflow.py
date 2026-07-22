"""
Full workflow commands.

Usage:
    cw workflow run <url> --site enseigna.fr [--row 3]
"""

import os
import click
from cli.options import blog_option
from pathlib import Path

import requests
from scripts.agent import RefreshOrchestrator
from scripts.sheets import SheetsClient


@click.group()
def workflow():
    """Full workflow with spreadsheet update."""
    pass


@workflow.command()
@click.argument('url')
@blog_option(required=True)
@click.option('--spreadsheet-id', default=lambda: os.environ.get('SPREADSHEET_ID'), help='Google Sheet ID (auto from .env)')
@click.option('--row', type=int, help='Row number in the spreadsheet')
def run(url, blog, spreadsheet_id, row):
    """
    Runs the full workflow for a URL.

    Equivalent to run_workflow_parcoursup.py.
    Runs every step + spreadsheet update.
    """
    click.echo(f"\n{'='*70}")
    click.echo(f"🚀 FULL WORKFLOW")
    click.echo(f"{'='*70}")
    click.echo(f"URL:         {url}")
    click.echo(f"Blog:        {blog}")
    if spreadsheet_id:
        click.echo(f"Spreadsheet: {spreadsheet_id}")
    if row:
        click.echo(f"Row:         {row}")
    click.echo()

    # Init orchestrator
    click.echo("[1/5] Initializing orchestrator...")
    orchestrator = RefreshOrchestrator(
        base_path=Path.cwd(),
        spreadsheet_id=spreadsheet_id
    )

    # Init sheets client
    if spreadsheet_id:
        sheets_client = SheetsClient(spreadsheet_id)
    else:
        sheets_client = None

    # Fetch content via direct HTTP scraping
    click.echo("[2/5] Fetching content via HTTP scraping...")
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
    click.echo(f"  ✓ HTML fetched: {len(html)} chars")

    # Process URL avec workflow complet
    click.echo("[3/5] Running full workflow (Ingest + Editorial Audit + Audit + Decision)...")

    try:
        result = orchestrator.process_url(
            url=url,
            site_slug=blog,
            html_content=html,
            force_action=None,
            custom_prompt=None,
            provided_keyword=None
        )

        click.echo(f"\n[4/5] Workflow results:")
        click.echo(f"  Success:       {result.success}")
        click.echo(f"  Action:        {result.action_taken}")
        click.echo(f"  Audit score:   {result.audit_score}")
        click.echo(f"  Assets valid:  {result.assets_valid}")
        click.echo(f"  Time:          {result.execution_time_seconds:.1f}s")

        if result.errors:
            click.echo(f"  ⚠ Errors ({len(result.errors)}):")
            for error in result.errors[:3]:
                click.echo(f"    - {error[:100]}")

        # Vérifier spreadsheet
        if sheets_client:
            click.echo("\n[5/5] Checking spreadsheet...")
            row_index = sheets_client._find_url_row(url, sheets_client.SHEET_REFRESHS_AUDIT)

            if row_index:
                click.echo(f"  ✓ URL found in spreadsheet (row {row_index})")
                click.echo(f"  Updated columns:")
                click.echo(f"    - X (editorial_audit_score)")
                click.echo(f"    - Y (editorial_audit_date)")
                click.echo(f"    - Z (editorial_verdict)")
                click.echo(f"    - AA (blocking_issues_count)")
                click.echo(f"    - AB (editorial_audit_report_url)")
                if result.action_taken == "BLOCKED_QUALITY_ISSUES":
                    click.echo(f"    - G (status) = 'blocked_quality_issues'")
                    click.echo(f"    - V (error_message) = blocking details")
            else:
                click.echo(f"  ⚠ URL not found in spreadsheet")
                click.echo(f"  The editorial audit ran but the columns were not updated")
        else:
            click.echo("\n[5/5] No spreadsheet configured (skip)")

        click.echo(f"\n{'='*70}")
        click.echo("WORKFLOW DONE")
        click.echo(f"{'='*70}\n")

        if result.action_taken == "BLOCKED_QUALITY_ISSUES":
            click.echo("❌ Quality Gate blocked the refresh")
            click.echo("See the editorial audit report for details:")
            click.echo(f"  sites/{blog}/outputs/editorial_audits/")
        else:
            click.echo("✅ Workflow completed successfully")

    except Exception as e:
        click.echo(f"\n❌ ERROR: {str(e)[:200]}", err=True)
        import traceback
        traceback.print_exc()
        raise click.Abort()
