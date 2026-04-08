"""
Commandes de rapports planifies.

Usage:
    srw report monday-indexation
    srw report monday-indexation --blog moments-yoga --dry-run
    srw report monday-indexation --save-json --limit 10
"""

import os
import click

from scripts.reports.monday_report import MondayIndexationReport


@click.group()
def report():
    """Rapports planifies et dashboards."""
    pass


@report.command(name="monday-indexation")
@click.option(
    "--spreadsheet-id",
    default=lambda: os.environ.get("SPREADSHEET_ID"),
    help="Google Sheet ID (default: env SPREADSHEET_ID)",
)
@click.option("--blog", default=None, help="Filtrer un seul blog (default: tous les 6)")
@click.option("--delay", type=float, default=1.5, help="Delai entre appels GSC (default: 1.5s)")
@click.option("--limit", type=int, default=None, help="Limiter URLs par blog (pour tests)")
@click.option("--dry-run", is_flag=True, help="Simuler sans ecriture spreadsheet")
@click.option("--save-json", is_flag=True, help="Sauvegarder rapport JSON dans outputs/reports/")
@click.option("--verbose", is_flag=True, help="Logs detailles")
def monday_indexation(spreadsheet_id, blog, delay, limit, dry_run, save_json, verbose):
    """
    Rapport hebdomadaire d'indexation multi-tenant.

    Scanne les 6 blogs via GSC URL Inspection API, detecte les pages
    desindexees, met a jour le spreadsheet, et affiche un rapport
    avec metriques de performance par URL a probleme.

    Concu pour etre execute automatiquement chaque lundi via GitHub Actions.
    """
    if not spreadsheet_id:
        click.echo("Erreur: --spreadsheet-id requis (ou definir SPREADSHEET_ID dans .env)", err=True)
        raise click.Abort()

    blog_ids = [blog] if blog else None

    reporter = MondayIndexationReport(
        spreadsheet_id=spreadsheet_id,
        dry_run=dry_run,
        verbose=verbose,
    )

    try:
        result = reporter.run_all_blogs(
            blog_ids=blog_ids,
            delay=delay,
            limit=limit,
        )

        if save_json:
            reporter.save_json_report(result)

        # Exit code based on issues found
        total_issues = result.get("aggregate", {}).get("total_issues", 0)
        if total_issues > 0:
            click.echo(f"\n{total_issues} problemes d'indexation detectes.")

    except Exception as e:
        click.echo(f"\nERREUR: {str(e)}", err=True)
        raise click.Abort()
