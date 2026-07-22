"""
Notion commands.

Usage:
    cw notion sync [--site moments-yoga]
    cw notion check-title --site moments-yoga --title "Les bienfaits du yoga"
    cw notion list-sujets [--site moments-yoga]
    cw notion create-sujet --site moments-yoga --title "Nouveau sujet" --db-id ABC123
"""

import json
import sys
from pathlib import Path

import click
from cli.options import blog_option

from scripts.notion import NotionClient


def _load_db_id(site_slug: str, db_type: str) -> str:
    """Charge le DB ID Notion depuis sites.json."""
    sites_path = Path.cwd() / "_shared" / "config" / "sites.json"
    if not sites_path.exists():
        return ""
    try:
        with open(sites_path) as f:
            data = json.load(f)
        for site in data.get("sites", []):
            if (site.get("site_slug") or site.get("id")) == site_slug:
                key = f"notion_{db_type}_db_id"
                return site.get(key, "") or ""
    except Exception:
        return ""
    return ""


@click.group()
def notion():
    """Notion integration - orders and topics."""
    pass


@notion.command(name='sync')
@blog_option()
@click.option('--db-id', help='Notion Commandes database ID (overrides sites.json)')
def sync(blog, db_id):
    """
    Shows a summary of the Notion orders per site.

    Reads the Notion "Commandes" database and shows the number of
    articles per status and per site.
    """
    click.echo(f"\n[Notion] Syncing orders")
    if blog:
        click.echo(f"Blog: {blog}")
    click.echo()

    client = NotionClient()
    if not client.is_configured:
        click.echo(
            "[ERROR] NOTION_TOKEN missing. Add it to .env or "
            "~/.credentials/notion/credentials.json",
            err=True
        )
        sys.exit(1)

    # Déterminer le DB ID
    database_id = db_id
    if not database_id and blog:
        database_id = _load_db_id(blog, "commandes")

    if not database_id:
        click.echo(
            "[ERROR] DB ID missing. Provide --db-id or configure "
            "notion_commandes_db_id in _shared/config/sites.json",
            err=True
        )
        sys.exit(1)

    commandes = client.get_commandes(database_id, site_slug=blog)

    # Résumé par statut
    by_status: dict[str, int] = {}
    by_blog: dict[str, int] = {}
    for c in commandes:
        by_status[c.status or "inconnu"] = by_status.get(c.status or "inconnu", 0) + 1
        by_blog[c.site_slug or "inconnu"] = by_blog.get(c.site_slug or "inconnu", 0) + 1

    click.echo(f"Total articles: {len(commandes)}")
    click.echo()
    click.echo("By status:")
    for status, count in sorted(by_status.items()):
        click.echo(f"  {status:<20} {count}")
    click.echo()
    click.echo("By site:")
    for b, count in sorted(by_blog.items()):
        click.echo(f"  {b:<25} {count}")


@notion.command(name='check-title')
@blog_option(required=True)
@click.option('--title', required=True, help='Title to check')
@click.option('--db-id', help='Notion Commandes database ID (overrides sites.json)')
@click.option('--threshold', default=0.85, show_default=True,
              help='Jaccard similarity threshold (0.0-1.0)')
def check_title(blog, title, db_id, threshold):
    """
    Checks whether a title already exists in the Notion orders.

    Uses an exact match, then a normalized match (accents stripped),
    then Jaccard similarity on the words.
    """
    click.echo(f"\n[Notion] Checking title: '{title}'")
    click.echo(f"Blog: {blog} | Threshold: {threshold}\n")

    client = NotionClient()
    if not client.is_configured:
        click.echo("[ERROR] NOTION_TOKEN missing.", err=True)
        sys.exit(1)

    database_id = db_id or _load_db_id(blog, "commandes")
    if not database_id:
        click.echo("[ERROR] DB ID missing (notion_commandes_db_id in sites.json).", err=True)
        sys.exit(1)

    commandes = client.get_commandes(database_id, site_slug=blog)
    match = client.find_title_match(commandes, title, threshold=threshold)

    if match:
        click.echo(f"[MATCH FOUND]")
        click.echo(f"  Existing title : {match.title}")
        click.echo(f"  URL            : {match.url or 'N/A'}")
        click.echo(f"  Status         : {match.status or 'N/A'}")
        click.echo(f"  Date           : {match.date or 'N/A'}")
        click.echo(f"\n  → Warning: potential cannibalization with this article.")
    else:
        click.echo(f"[OK] No similar article found among the {len(commandes)} orders.")


@notion.command(name='list-sujets')
@blog_option()
@click.option('--db-id', required=True, help='Notion Sujets database ID')
def list_sujets(blog, db_id):
    """
    Lists the topics to process from the Notion database.

    Shows the not-yet-processed topics with their priority.
    """
    click.echo(f"\n[Notion] Topics to process")
    if blog:
        click.echo(f"Blog: {blog}")
    click.echo()

    client = NotionClient()
    if not client.is_configured:
        click.echo("[ERROR] NOTION_TOKEN missing.", err=True)
        sys.exit(1)

    sujets = client.get_sujets(db_id, site_slug=blog)

    if not sujets:
        click.echo("No topic found.")
        return

    click.echo(f"{len(sujets)} topics found:\n")
    for s in sujets:
        priority_icon = {"high": "!!!", "medium": " ! ", "low": "   "}.get(
            (s.priority or "").lower(), "   "
        )
        click.echo(
            f"  [{priority_icon}] {s.title:<50} "
            f"| {s.site_slug or '?':<20} | {s.status or '?'}"
        )


@notion.command(name='create-sujet')
@blog_option(required=True)
@click.option('--title', required=True, help='Topic title')
@click.option('--db-id', required=True, help='Notion Sujets database ID')
@click.option('--category', default='', help='Thematic category')
@click.option('--priority', default='medium',
              type=click.Choice(['high', 'medium', 'low']),
              show_default=True, help='Priority')
def create_sujet(blog, title, db_id, category, priority):
    """
    Creates a new topic in the Notion database.

    Useful to manually record a topic discovered during a content
    analysis or keyword research.
    """
    click.echo(f"\n[Notion] Creating topic: '{title}'")
    click.echo(f"Blog: {blog} | Priority: {priority}\n")

    client = NotionClient()
    if not client.is_configured:
        click.echo("[ERROR] NOTION_TOKEN missing.", err=True)
        sys.exit(1)

    page = client.create_sujet(
        database_id=db_id,
        title=title,
        site_slug=blog,
        category=category,
        priority=priority,
    )

    if page:
        page_id = page.get("id", "?")
        click.echo(f"[OK] Topic created - page_id: {page_id}")
    else:
        click.echo("[ERROR] Creation failed.", err=True)
        sys.exit(1)


@notion.command(name='sync-sites')
@click.option('--apply', 'do_apply', is_flag=True, default=False,
              help='Write sites.json (otherwise dry-run diff).')
@click.option('--dump-schema', 'dump_schema', is_flag=True, default=False,
              help='Show the real properties of the Notion "config pays" database.')
def sync_sites(do_apply, dump_schema):
    """One-way sync: Notion "config pays" page → sites.json.

    Notion (edited by humans) is the source; sites.json is its machine
    projection. The engine never reads Notion at runtime. Additive merge,
    dry-run by default. Requires a valid NOTION_TOKEN in .env.
    """
    from scripts.notion.sync_sites_from_notion import main as sync_main
    argv = []
    if do_apply:
        argv.append('--apply')
    if dump_schema:
        argv.append('--dump-schema')
    # Le module lit sys.argv via argparse ; on le pilote directement.
    import sys as _sys
    old = _sys.argv
    _sys.argv = ['sync_sites_from_notion'] + argv
    try:
        code = sync_main()
    finally:
        _sys.argv = old
    if code:
        sys.exit(code)
