"""
Commande ngl-status — met à jour le statut éditorial (colonne F) dans l'onglet
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
    """Met à jour le statut (col F) d'une URL dans l'onglet New Growing List.

    STATUTS : A faire | Rédigé | Draft in WP | Publié
    """
    if statuts_value not in STATUTS_VALUES:
        click.echo(
            f"[ERREUR] Valeur invalide : '{statuts_value}'\n"
            f"Valeurs acceptées : {', '.join(STATUTS_VALUES)}",
            err=True,
        )
        raise SystemExit(1)

    found = mark_ngl_status_by_url(url, statuts_value)
    if not found:
        click.echo(f"[ERREUR] URL introuvable dans New Growing List : {url}", err=True)
        raise SystemExit(1)

    click.echo(f"[OK] New Growing List → statuts = \"{statuts_value}\"")
    click.echo(f"     {url[:90]}")
