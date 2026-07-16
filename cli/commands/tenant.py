"""Tenant commands — Superprof catalog + onboarding.

Usage:
    cw tenant list [--type ressources|blog]     # browse the catalog
    cw tenant init <id> [--force] [--no-sparse]  # onboard a tenant

User-facing output is in English (common language across all Superprof markets).
See onboarding/ for the full SEO Manager guide.
"""

import json
from pathlib import Path

import click


@click.group()
def tenant():
    """Superprof blog catalog and tenant onboarding."""
    pass


@tenant.command(name="list")
@click.option("--type", "type_filter", type=click.Choice(["ressources", "blog"]),
              help="Filter by type (ressources | blog).")
def list_tenants(type_filter):
    """List blogs from the catalog (superprof_blogs_catalog.json)."""
    from scripts.utils.tenant_onboard import CATALOG_PATH
    if not CATALOG_PATH.exists():
        click.echo("[ERROR] Catalog missing. Generate it with "
                   "`python -m scripts.utils.build_superprof_catalog`.", err=True)
        raise click.Abort()
    cat = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))

    # Already-onboarded tenants (to mark with a check).
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
            mark = "x" if e["tenant_id"] in onboarded else " "
            click.echo(f"  [{mark}] {e['tenant_id']:24} {e.get('country',''):3} "
                       f"{e['gsc_property']}")
    click.echo("\n[x] = already onboarded (in sites.json). "
               "Onboard one: cw tenant init <id>")


@tenant.command(name="init")
@click.argument("tenant_id")
@click.option("--force", is_flag=True, default=False,
              help="Overwrite an existing tenant.")
@click.option("--no-sparse", is_flag=True, default=False,
              help="Do not touch the git sparse-checkout (CI / full worktree).")
def init_tenant(tenant_id, force, no_sparse):
    """Onboard a tenant from the catalog: tenants/{id}/ skeleton + sites.json."""
    from scripts.utils.tenant_onboard import onboard_tenant
    try:
        report = onboard_tenant(tenant_id, base_path=Path.cwd(),
                                force=force, no_sparse=no_sparse)
    except ValueError as e:
        click.echo(f"[ERROR] {e}", err=True)
        raise click.Abort()

    click.echo(f"\nTenant '{report['tenant_id']}' onboarded.")
    click.echo(f"   Folder   : {report['tenant_dir']}/")
    click.echo(f"   Config   : {report['config']}")
    click.echo(f"   Registry : sites.json {'updated' if report['registry_updated'] else 'already had it'}")
    if report.get("sparse_added"):
        click.echo(f"   Sparse   : tenants/{report['tenant_id']} added to your working tree")
    elif not no_sparse:
        click.echo("   Sparse   : skipped (full worktree — nothing to isolate)")

    click.echo("\n   Next steps (country SEO Manager):")
    click.echo(f"   1. Fill in {report['config']} (tone, seo, wp_api_config, sheets).")
    click.echo(f"   2. Write {report['tenant_dir']}/prompts/site.md and drop your editorial guides.")
    click.echo(f"   3. Add your writing skill under {report['tenant_dir']}/.claude/skills/.")
    click.echo("   4. Ask the maintainer to add your CODEOWNERS line.")
    click.echo("   See onboarding/02-onboard-my-tenant.md for details.")
