"""Commandes tenant — catalogue Superprof + onboarding (Phase 6d).

Usage:
    cw tenant list [--type ressources|blog]     # parcourir le catalogue
    cw tenant init <id>                          # onboarder un tenant (squelette + sites.json)
"""

import json
from pathlib import Path

import click


@click.group()
def tenant():
    """Catalogue des blogs Superprof et onboarding des tenants."""
    pass


@tenant.command(name="list")
@click.option("--type", "type_filter", type=click.Choice(["ressources", "blog"]),
              help="Filtrer par type (ressources | blog).")
def list_tenants(type_filter):
    """Liste les blogs du catalogue (superprof_blogs_catalog.json)."""
    from scripts.utils.tenant_onboard import CATALOG_PATH
    if not CATALOG_PATH.exists():
        click.echo("[ERREUR] Catalogue absent. Générer via "
                   "`python -m scripts.utils.build_superprof_catalog`.", err=True)
        raise click.Abort()
    cat = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))

    # Tenants déjà onboardés (pour marquer ✓).
    sites_path = Path.cwd() / "_shared" / "config" / "sites.json"
    onboarded = set()
    if sites_path.exists():
        onboarded = {s.get("id") for s in json.loads(sites_path.read_text()).get("sites", [])}

    groups = []
    if type_filter in (None, "ressources"):
        groups.append(("RESSOURCES", cat.get("ressources_sites", [])))
    if type_filter in (None, "blog"):
        groups.append(("BLOGS", cat.get("blogs", [])))

    for label, entries in groups:
        click.echo(f"\n=== {label} ({len(entries)}) ===")
        for e in entries:
            mark = "✓" if e["tenant_id"] in onboarded else " "
            click.echo(f"  [{mark}] {e['tenant_id']:24} {e.get('country',''):3} "
                       f"{e['gsc_property']}")
    click.echo("\n✓ = déjà onboardé (dans sites.json). "
               "Onboarder : cw tenant init <id>")


@tenant.command(name="init")
@click.argument("tenant_id")
@click.option("--force", is_flag=True, default=False,
              help="Écrase un tenant existant.")
def init_tenant(tenant_id, force):
    """Onboarde un tenant depuis le catalogue : squelette tenants/{id}/ + sites.json."""
    from scripts.utils.tenant_onboard import onboard_tenant
    try:
        report = onboard_tenant(tenant_id, base_path=Path.cwd(), force=force)
    except ValueError as e:
        click.echo(f"[ERREUR] {e}", err=True)
        raise click.Abort()

    click.echo(f"\n✅ Tenant '{report['tenant_id']}' onboardé.")
    click.echo(f"   Dossier : {report['tenant_dir']}/")
    click.echo(f"   Config  : {report['config']}")
    click.echo(f"   Registre sites.json : {'ajouté' if report['registry_updated'] else 'déjà présent'}")
    click.echo("\n   Prochaines étapes (responsable pays) :")
    click.echo(f"   1. Compléter {report['config']} (ton, seo, wp_api, sheets).")
    click.echo(f"   2. Déposer les guides éditoriaux dans {report['tenant_dir']}/prompts/.")
