"""
`statuts` command - updates the editorial status of a URL in the Growing sheet.

Usage:
    cw statuts <url> <statuts>

Valeurs valides :
    "A faire"    URL non encore traitée (valeur par défaut)
    "Rédigé"     Contenu refreshé généré
    "Draft in WP" Contenu envoyé sur WordPress (draft)
    "Publié"     Article publié

Exemples :
    cw statuts https://www.superprof.fr/ressources/maths/... "Rédigé"
    cw statuts https://www.superprof.fr/ressources/maths/... "Draft in WP"
"""

import click
from scripts.audit.superprof_gsc_audit import STATUTS_VALUES


@click.command()
@click.argument("url")
@click.argument("statuts_value", metavar="STATUTS")
def statuts(url, statuts_value):
    """Updates the editorial status of a URL in the Growing sheet (Superprof Ressources).

    STATUTS: A faire | Rédigé | Draft in WP | Publié
    """
    if statuts_value not in STATUTS_VALUES:
        click.echo(
            f"[ERROR] Invalid value: '{statuts_value}'\n"
            f"Accepted values: {', '.join(STATUTS_VALUES)}",
            err=True,
        )
        raise SystemExit(1)

    # Alias de `cw status --tab "⬆️ Growing"` : même chemin générique config-driven.
    from scripts.sheets.tab_status import update_status
    res = update_status("superprof.fr-ressources", url, statuts_value, tab="⬆️ Growing")
    if res is None:
        click.echo(f"[ERROR] URL not found in Growing: {url}", err=True)
        raise SystemExit(1)

    click.echo(f"[OK] Row {res.row} → statuts = \"{statuts_value}\"")
    click.echo(f"     {url[:90]}")
