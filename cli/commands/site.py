"""Site commands — Superprof catalog + onboarding.

Usage:
    cw site list [--type ressources|blog]     # browse the catalog
    cw site init <id> [--force] [--no-sparse]  # onboard a site

User-facing output is in English (common language across all Superprof sites).
See onboarding/ for the full SEO Manager guide.
"""

import json
from pathlib import Path

import click


@click.group()
def site():
    """Superprof blog catalog and site onboarding."""
    pass


@site.command(name="list")
@click.option("--type", "type_filter", type=click.Choice(["ressources", "blog"]),
              help="Filter by type (ressources | blog).")
def list_sites(type_filter):
    """List blogs from the catalog (superprof_sites_catalog.json)."""
    from scripts.utils.site_onboard import CATALOG_PATH
    if not CATALOG_PATH.exists():
        click.echo("[ERROR] Catalog missing. Generate it with "
                   "`python -m scripts.utils.build_superprof_catalog`.", err=True)
        raise click.Abort()
    cat = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))

    # Already-onboarded sites (to mark with a check).
    sites_path = Path.cwd() / "_shared" / "config" / "sites.json"
    onboarded = set()
    if sites_path.exists():
        onboarded = {s.get("site_slug") or s.get("id")
                     for s in json.loads(sites_path.read_text()).get("sites", [])}

    all_sites = cat.get("sites", [])
    groups = []
    if type_filter in (None, "ressources"):
        groups.append(("RESSOURCES", [e for e in all_sites if e.get("type") == "ressources"]))
    if type_filter in (None, "blog"):
        groups.append(("BLOGS", [e for e in all_sites if e.get("type") == "blog"]))

    for label, entries in groups:
        click.echo(f"\n=== {label} ({len(entries)}) ===")
        for e in entries:
            mark = "x" if e["site_slug"] in onboarded else " "
            click.echo(f"  [{mark}] {e['site_slug']:24} {e.get('country',''):3} "
                       f"{e['gsc_property']}")
    click.echo("\n[x] = already onboarded (in sites.json). "
               "Onboard one: cw site init <site-slug>")


@site.command(name="init")
@click.argument("site_slug")
@click.option("--force", is_flag=True, default=False,
              help="Overwrite an existing site.")
@click.option("--no-sparse", is_flag=True, default=False,
              help="Do not touch the git sparse-checkout (CI / full worktree).")
def init_site(site_slug, force, no_sparse):
    """Onboard a site from the catalog: sites/<site-slug>/ skeleton + sites.json."""
    from scripts.utils.site_onboard import onboard_site
    try:
        report = onboard_site(site_slug, base_path=Path.cwd(),
                                force=force, no_sparse=no_sparse)
    except ValueError as e:
        click.echo(f"[ERROR] {e}", err=True)
        raise click.Abort()

    click.echo(f"\nSite '{report['site_slug']}' onboarded.")
    click.echo(f"   Folder   : {report['site_dir']}/")
    click.echo(f"   Config   : {report['config']}")
    click.echo(f"   Registry : sites.json {'updated' if report['registry_updated'] else 'already had it'}")
    if report.get("sparse_added"):
        click.echo(f"   Sparse   : sites/{report['site_slug']} added to your working tree")
    elif not no_sparse:
        click.echo("   Sparse   : skipped (full worktree — nothing to isolate)")

    click.echo("\n   Next steps (country SEO Manager):")
    click.echo(f"   1. Fill in {report['config']} (tone, seo, wp_api_config, sheets).")
    click.echo(f"   2. Write {report['site_dir']}/prompts/site.md and drop your editorial guides.")
    click.echo(f"   3. Add your writing skill under {report['site_dir']}/.claude/skills/.")
    click.echo("   4. Ask the maintainer to add your CODEOWNERS line.")
    click.echo("   See onboarding/02-onboard-my-site.md for details.")
