"""
Commandes de maillage interne automatisé.

Usage:
    srw linking run --blog coachsportlyon.fr --branch 1 --spreadsheet-id ABC123
    srw linking preview --blog coachsportlyon.fr --branch 1 --spreadsheet-id ABC123
"""

import click
import logging

from scripts.sheets import SheetsClient
from scripts.linking import LinkInjector
from scripts.linking.cocon_auto_mapper import CoconAutoMapper

logger = logging.getLogger(__name__)


@click.group()
def linking():
    """Maillage interne automatisé pour les cocons sémantiques."""
    pass


@linking.command()
@click.option('--spreadsheet-id', required=True, help='Google Sheet ID')
@click.option('--blog', required=True, help='Blog ID (ex: coachsportlyon.fr)')
@click.option('--branch', required=True, type=int, help='Numéro de branche cocon')
@click.option('--verbose', '-v', is_flag=True, help='Logging détaillé')
def preview(spreadsheet_id, blog, branch, verbose):
    """
    Prévisualise les mappings de liens sans injecter.

    Affiche les liens qui seraient créés pour chaque article du cocon.
    """
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    click.echo(f"\n--- PREVIEW MAILLAGE INTERNE ---")
    click.echo(f"Blog: {blog}")
    click.echo(f"Branche cocon: {branch}\n")

    # Init
    sheets = SheetsClient(spreadsheet_id=spreadsheet_id)
    mapper = CoconAutoMapper(sheets_client=sheets)

    # Generate mappings
    mappings = mapper.generate_mappings(blog, branch)

    if not mappings:
        click.echo("Aucun mapping généré. Vérifiez blog_id et cocon_branch dans le spreadsheet.")
        return

    click.echo(f"Total: {len(mappings)} liens à injecter\n")

    # Group by source URL for display
    by_source: dict[str, list] = {}
    for m in mappings:
        by_source.setdefault(m.url_source, []).append(m)

    for url_source, source_mappings in by_source.items():
        slug = url_source.rstrip('/').split('/')[-1]
        click.echo(f"  {slug}/")
        for m in source_mappings:
            target_slug = m.url_cible.rstrip('/').split('/')[-1]
            click.echo(f"    -> [{m.type_relation}] {target_slug}/ (ancre: '{m.mot_cle_principal}')")
        click.echo("")

    click.echo(f"--- {len(mappings)} liens prêts à injecter ---")
    click.echo("Lancez 'srw linking run' pour injecter.")


@linking.command()
@click.option('--spreadsheet-id', required=True, help='Google Sheet ID')
@click.option('--blog', required=True, help='Blog ID (ex: coachsportlyon.fr)')
@click.option('--branch', required=True, type=int, help='Numéro de branche cocon')
@click.option('--verbose', '-v', is_flag=True, help='Logging détaillé')
def run(spreadsheet_id, blog, branch, verbose):
    """
    Injecte les liens internes pour une branche de cocon.

    Lit les URLs depuis Refreshs_Audit (filtrées par blog + branche),
    génère les mappings automatiquement, et injecte les liens dans
    les fichiers HTML de sortie.
    """
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    click.echo(f"\n--- MAILLAGE INTERNE AUTOMATISÉ ---")
    click.echo(f"Blog: {blog}")
    click.echo(f"Branche cocon: {branch}\n")

    # 1. Init
    sheets = SheetsClient(spreadsheet_id=spreadsheet_id)
    mapper = CoconAutoMapper(sheets_client=sheets)

    # 2. Generate mappings
    click.echo("[1/3] Génération des mappings de liens...")
    mappings = mapper.generate_mappings(blog, branch)

    if not mappings:
        click.echo("Aucun mapping généré. Vérifiez blog_id et cocon_branch dans le spreadsheet.")
        return

    click.echo(f"  {len(mappings)} liens à injecter")

    # 3. Inject links
    click.echo("[2/3] Injection des liens dans les fichiers HTML...")
    injector = LinkInjector(site_id=blog)
    reports = injector.inject_batch(mappings)

    # 4. Display results
    click.echo(f"\n[3/3] Résultats:")
    total_injected = 0
    total_skipped = 0
    total_failed = 0

    for report in reports:
        slug = report.url_source.rstrip('/').split('/')[-1]
        status = "OK" if report.validation_passed else "WARN"
        click.echo(
            f"  [{status}] {slug}/: "
            f"{report.links_injected} injectés, "
            f"{report.links_skipped_duplicate} dupliqués, "
            f"{report.links_failed} échoués "
            f"({report.internal_links_before} -> {report.internal_links_after} liens)"
        )
        total_injected += report.links_injected
        total_skipped += report.links_skipped_duplicate
        total_failed += report.links_failed

    click.echo(f"\n--- TOTAL: {total_injected} injectés, {total_skipped} dupliqués, {total_failed} échoués ---")
