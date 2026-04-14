"""
Commandes de maillage interne automatisé.

NOTE: Le pipeline cocon-aware basé sur la colonne `cocon_branch` du spreadsheet
a été retiré (avril 2026). Les commandes ci-dessous sont conservées comme
placeholders et renvoient un message explicatif. Pour réinjecter du linking
interne, utiliser directement `LinkInjector` avec un mapping CSV manuel
(voir `_shared/config/linking_maps/`).
"""

import click


@click.group()
def linking():
    """Maillage interne (désactivé — voir docstring du module)."""
    pass


@linking.command()
def preview():
    """Désactivé. La colonne cocon_branch n'existe plus dans le spreadsheet."""
    click.echo(
        "[DEPRECATED] La commande 'linking preview' reposait sur la colonne "
        "cocon_branch du spreadsheet, qui a été retirée. Utilisez un mapping "
        "CSV manuel dans _shared/config/linking_maps/ + LinkInjector."
    )


@linking.command()
def run():
    """Désactivé. La colonne cocon_branch n'existe plus dans le spreadsheet."""
    click.echo(
        "[DEPRECATED] La commande 'linking run' reposait sur la colonne "
        "cocon_branch du spreadsheet, qui a été retirée. Utilisez un mapping "
        "CSV manuel dans _shared/config/linking_maps/ + LinkInjector."
    )
