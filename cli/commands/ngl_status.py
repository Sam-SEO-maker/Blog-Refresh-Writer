"""
`ngl-status` command - updates the editorial status (column F) in the
`New Growing List` du spreadsheet Superprof Ressources.

Distincte de `cw statuts`, qui cible l'onglet `⬆️ Growing` (autre spreadsheet/onglet).

Usage:
    cw ngl-status <url> "Rédigé"
"""

import click

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

    # Alias de `cw status --tab "New Growing List"` : même chemin générique.
    from scripts.sheets.tab_status import update_status
    res = update_status("superprof.fr-ressources", url, statuts_value, tab="New Growing List")
    if res is None:
        click.echo(f"[ERROR] URL not found in New Growing List: {url}", err=True)
        raise SystemExit(1)

    click.echo(f"[OK] New Growing List → statuts = \"{statuts_value}\"")
    click.echo(f"     {url[:90]}")
