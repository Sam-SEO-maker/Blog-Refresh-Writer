"""
`status` command - updates the editorial status of a URL, whatever the work tab.

Searches the URL across every tab declared in the site's `sheets.tabs`
(site.json) and writes the status in that tab's status column. Replaces the
tab-specific commands (`statuts` = ⬆️ Growing, `ngl-status` = New Growing
List), which remain as thin aliases.

Usage:
    cw status <url> "Rédigé" [--site superprof.fr-ressources] [--tab "⬆️ Growing"]
"""

import click

from cli.options import site_option
from scripts.audit.superprof_gsc_audit import STATUTS_VALUES
from scripts.sheets.tab_status import update_status


@click.command(name="status")
@click.argument("url")
@click.argument("statuts_value", metavar="STATUS")
@site_option(required=False, dest="site")
@click.option("--tab", default=None, help="Restrict the search to one declared tab")
def status(url, statuts_value, site, tab):
    """Updates the editorial status of a URL in any declared work tab.

    STATUS: A faire | Rédigé | Draft in WP | Publié
    """
    if statuts_value not in STATUTS_VALUES:
        click.echo(
            f"[ERROR] Invalid value: '{statuts_value}'\n"
            f"Accepted values: {', '.join(STATUTS_VALUES)}",
            err=True,
        )
        raise SystemExit(1)

    site = site or "superprof.fr-ressources"
    try:
        res = update_status(site, url, statuts_value, tab=tab)
    except (ValueError, RuntimeError) as e:
        click.echo(f"[ERROR] {e}", err=True)
        raise SystemExit(1)

    if res is None:
        click.echo(f"[ERROR] URL not found in any declared tab of {site}: {url}", err=True)
        raise SystemExit(1)
    if not res.written:
        click.echo(f"[ERROR] {res.reason} (URL found in '{res.tab}' row {res.row})", err=True)
        raise SystemExit(1)

    click.echo(f"[OK] {res.tab} (row {res.row}) → status = \"{statuts_value}\"")
    click.echo(f"     {url[:90]}")
