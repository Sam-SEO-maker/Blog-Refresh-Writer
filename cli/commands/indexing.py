"""
Commandes d'indexation.

Usage:
    cw indexing request --site enseigna [--spreadsheet-id <ID>]
    cw indexing scan --site enseigna
    cw indexing bulk-diagnostic --site enseigna
"""

import click
from cli.options import blog_option
from pathlib import Path

from scripts.indexing import IndexingRequester
from scripts.sheets import SheetsClient
from _shared.config.sites import SITE_CONFIGS


@click.group()
def indexing():
    """Gestion de l'indexation Google."""
    pass


@indexing.command()
@blog_option(required=True)
@click.option('--spreadsheet-id', required=True, help='Google Sheet ID')
def request(blog, spreadsheet_id):
    """
    Demande d'indexation pour URLs avec status 'CONTENT DONE'.

    Utilise l'API Google Indexing pour forcer l'indexation.
    """
    click.echo(f"\n📤 DEMANDE INDEXATION")
    click.echo(f"Blog: {blog}")
    click.echo()

    # Get blog config
    site_config = SITE_CONFIGS.get(blog)
    if not site_config:
        click.echo(f"❌ Blog ID inconnu: {blog}", err=True)
        raise click.Abort()

    gsc_property = site_config.get("gsc_property")

    # Get URLs with status = CONTENT DONE
    click.echo("[1/2] Lecture spreadsheet...")
    sheets_client = SheetsClient(spreadsheet_id)
    rows = sheets_client.read_pending_for_refresh(action=None, site_slug=blog)
    urls_to_index = [row.blogpost_url for row in rows if row.status == "CONTENT DONE"]

    if not urls_to_index:
        click.echo("  ℹ Aucune URL avec status 'CONTENT DONE' à indexer")
        return

    click.echo(f"  ✓ {len(urls_to_index)} URLs à indexer")

    # Request indexing
    click.echo("[2/2] Demande indexation Google...")
    requester = IndexingRequester(gsc_property)

    try:
        results = requester.batch_request_indexing(urls_to_index, delay=2.0)

        click.echo(f"\n📊 RÉSULTATS:")
        click.echo(f"  Total:          {results['total']}")
        click.echo(f"  Succès:         {results['success']}")
        click.echo(f"  Échecs:         {results['failed']}")
        click.echo(f"  Quota dépassé:  {results['quota_exceeded']}")

        if results['failed'] > 0:
            click.echo(f"\n  ⚠ Échecs (premiers 5):")
            for error in results.get('errors', [])[:5]:
                click.echo(f"    - {error}")

        if results['success'] > 0:
            click.echo(f"\n✅ {results['success']} URLs soumises à l'indexation")
        else:
            click.echo(f"\n❌ Aucune URL indexée avec succès")

    except Exception as e:
        click.echo(f"\n❌ ERREUR: {str(e)}", err=True)
        raise click.Abort()


@indexing.command()
@blog_option(required=True)
@click.option('--limit', type=int, default=100, help='Limite du nombre d\'URLs à scanner')
def scan(blog, limit):
    """
    Scan indexation status pour toutes les URLs du blog.

    Vérifie via GSC API quelles URLs sont indexées.
    """
    click.echo(f"\n🔍 SCAN INDEXATION")
    click.echo(f"Blog:  {blog}")
    click.echo(f"Limit: {limit}")
    click.echo()

    click.echo("⚠ Fonctionnalité à implémenter:")
    click.echo("  1. Récupérer toutes les URLs du blog depuis spreadsheet")
    click.echo("  2. Vérifier status indexation via GSC API")
    click.echo("  3. Générer rapport (indexé, non-indexé, erreurs)")


@indexing.command(name='bulk-diagnostic')
@blog_option(required=True)
@click.option('--spreadsheet-id', required=True, help='Google Sheet ID')
def bulk_diagnostic(blog, spreadsheet_id):
    """
    Diagnostic bulk indexation.

    Exécute scripts/indexing/bulk_index_diagnostic.py
    """
    click.echo(f"\n🔍 DIAGNOSTIC BULK INDEXATION")
    click.echo(f"Blog: {blog}")
    click.echo()

    try:
        from scripts.indexing.bulk_index_diagnostic import main as bulk_diagnostic_main

        # Run diagnostic
        click.echo("Exécution diagnostic...")
        bulk_diagnostic_main()

        click.echo(f"\n✅ Diagnostic terminé")

    except ImportError:
        click.echo(f"❌ Module bulk_index_diagnostic non trouvé", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"\n❌ ERREUR: {str(e)}", err=True)
        raise click.Abort()
