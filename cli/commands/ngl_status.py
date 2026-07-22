"""
`ngl-status` command - updates the editorial status (column F) in the
`New Growing List` du spreadsheet Superprof Ressources.

Distincte de `cw statuts`, qui cible l'onglet `⬆️ Growing` (autre spreadsheet/onglet).

Usage:
    cw ngl-status <url> "Rédigé"
"""

import click

from scripts.agent.prepare_weekly_batch import mark_ngl_status_by_url
from scripts.audit.superprof_gsc_audit import STATUTS_VALUES


@click.command(name="ngl-status")
@click.argument("url")
@click.argument("statuts_value", metavar="STATUTS")
def ngl_status(url, statuts_value):
    """Updates the status (col F) of a URL in the New Growing List tab.

    STATUTS: A faire | Rédigé | Draft in WP | Publié
    """
    if statuts_value not in STATUTS_VALUES:
        click.echo(
            f"[ERROR] Invalid value: '{statuts_value}'\n"
            f"Accepted values: {', '.join(STATUTS_VALUES)}",
            err=True,
        )
        raise SystemExit(1)

    found = mark_ngl_status_by_url(url, statuts_value)
    if not found:
        click.echo(f"[ERROR] URL not found in New Growing List: {url}", err=True)
        raise SystemExit(1)

    click.echo(f"[OK] New Growing List → statuts = \"{statuts_value}\"")
    click.echo(f"     {url[:90]}")
