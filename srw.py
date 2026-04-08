#!/usr/bin/env python3
"""
SRW - Super Refresh Writer CLI

CLI unifié pour le workflow de refresh SEO.
Remplace les scripts ad-hoc dispersés dans le projet.

Usage:
    srw refresh <url> --blog enseigna
    srw workflow run <url> --blog enseigna [--row 3]
    srw audit editorial <url> --blog enseigna
    srw cocon identify
    srw batch audit-gsc --blog enseigna
    srw debug workflow <url> --blog enseigna
"""

import sys
from pathlib import Path

# Ajouter le répertoire au path
sys.path.insert(0, str(Path(__file__).parent))

import click
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()


@click.group()
@click.version_option(version="2.0.0", prog_name="SRW")
@click.pass_context
def cli(ctx):
    """
    🚀 Super Refresh Writer - CLI unifié pour le refresh SEO

    Agent autonome de rafraîchissement de contenus SEO.
    Piloté par Google Sheets avec détection de cannibalisation,
    audit qualité, et mode Ghostwriter.
    """
    ctx.ensure_object(dict)


# Import des groupes de commandes
from cli.commands import refresh, workflow, audit, cocon, batch, indexing, debug, linking
from cli.commands import ytg, notion_cmd, report

# Enregistrer les commandes
cli.add_command(refresh.refresh)
cli.add_command(workflow.workflow)
cli.add_command(audit.audit)
cli.add_command(cocon.cocon)
cli.add_command(batch.batch)
cli.add_command(indexing.indexing)
cli.add_command(debug.debug)
cli.add_command(linking.linking)
cli.add_command(ytg.ytg)
cli.add_command(notion_cmd.notion)
cli.add_command(report.report)


if __name__ == "__main__":
    cli()
