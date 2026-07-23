"""
Audit commands.

Usage:
    cw audit editorial <url> --site enseigna.fr
    cw audit gsc <url>
    cw audit serp <url> --main-keyword "parcoursup"
    cw audit cannibalization <url>
"""

import os
import click
from cli.options import blog_option, site_option
from pathlib import Path

from scripts.agent import RefreshOrchestrator
from scripts.audit import GSCAnalyzer, SERPAnalyzer
from scripts.sheets import SheetsClient


@click.group()
def audit():
    """Quality and performance audits."""
    pass


@audit.command()
@click.argument('url')
@click.option('--main-keyword', '--keyword', 'keyword',
              help='Main keyword (optional). --keyword = legacy alias.')
def serp(url, keyword):
    """
    SERP audit (PAA, secondary keywords).

    Analyzes the SERP via the direct DataForSEO API.
    """
    click.echo(f"\n🔍 AUDIT SERP")
    click.echo(f"URL: {url}")
    if keyword:
        click.echo(f"KW:  {keyword}\n")

    # Analyze SERP
    click.echo("Analyzing SERP...")
    analyzer = SERPAnalyzer()

    try:
        # Si pas de keyword, déduire depuis le slug de l'URL
        if not keyword:
            from urllib.parse import urlparse
            path = urlparse(url).path
            parts = [p for p in path.split("/") if p]
            last = parts[-1].replace(".html", "") if parts else ""
            keyword = last.replace("-", " ") if last else url
            click.echo(f"  (Keyword derived from the slug: '{keyword}')")

        from urllib.parse import urlparse
        our_domain = urlparse(url).netloc

        result = analyzer.to_dict(analyzer.analyze(keyword, our_domain))

        click.echo(f"\n📊 RESULTS:")
        if result.get('our_url_found'):
            click.echo(f"  Our position:       {result.get('our_position')}")
        else:
            click.echo(f"  Our position:       outside top 10")
        click.echo(f"  Dominant format:    {result.get('dominant_format')}")
        if result.get('format_mismatch'):
            click.echo(f"  ⚠️  Format mismatch → recommended: {result.get('recommended_format')}")
        click.echo(f"  PAA questions:      {len(result.get('paa_questions', []))}")

        if result.get('paa_questions'):
            click.echo(f"\n  PAA:")
            for q in result['paa_questions']:
                click.echo(f"    - {q}")

        if result.get('top_10_results'):
            click.echo(f"\n  Top 10 SERP:")
            for r in result['top_10_results']:
                click.echo(f"    {r['position']:>2}. [{r['format_type']}] {r['domain']}")

    except Exception as e:
        click.echo(f"\n❌ ERROR: {str(e)}", err=True)
        raise click.Abort()


@audit.command("ahrefs-state")
@site_option(required=True, dest='site')
@click.option('--months', type=int, default=None, help='Period in months (default: config)')
@click.option('--limit', type=int, default=None, help='Max number of keywords (default: config)')
@click.option('--from-csv', type=str, default=None, help='Read an Ahrefs CSV export instead of the API')
@click.option('--dry-run', is_flag=True, help='Local dump only, no Sheets push')
def ahrefs_state(site, months, limit, from_csv, dry_run):
    """SEO state of play via Ahrefs (ranking keywords → dedicated Google Sheet)."""
    from scripts.audit.ahrefs_state import run_ahrefs_state

    click.echo(f"\n📊 AHREFS STATE - {site}")
    if dry_run:
        click.echo("(dry-run mode)")

    try:
        result = run_ahrefs_state(site, months=months, limit=limit, dry_run=dry_run, from_csv=from_csv)
        click.echo(f"\n✅ Done:")
        click.echo(f"  KW:         {result['nb_kw']}")
        click.echo(f"  Categories: {result['nb_categories']}")
        click.echo(f"  Pages:      {result['nb_pages']}")
        if result.get('output_path'):
            click.echo(f"  Dump:       {result['output_path']}")
        if result.get('spreadsheet_id'):
            click.echo(f"  Sheet:      https://docs.google.com/spreadsheets/d/{result['spreadsheet_id']}")
    except Exception as e:
        click.echo(f"\n❌ ERROR: {e}", err=True)
        raise click.Abort()


@audit.command("enseigna-refresh-list")
@click.option('--months', type=int, default=6, help='GSC period in months (default: 6)')
@click.option('--dry-run', is_flag=True, help='Local dump only, no Sheets push')
def enseigna_refresh_list(months, dry_run):
    """Pull enseigna GSC, filter Avis/Versus, push the refresh list Sheet."""
    from scripts.audit.enseigna_refresh_list import run

    click.echo(f"\n📊 ENSEIGNA REFRESH LIST ({months}m)")
    if dry_run:
        click.echo("(dry-run mode)")
    try:
        result = run(months=months, dry_run=dry_run)
        click.echo(f"\n✅ Done:")
        click.echo(f"  Avis:   {result['avis']}")
        click.echo(f"  Versus: {result['versus']}")
        if result.get('output_path'):
            click.echo(f"  Dump:   {result['output_path']}")
        if result.get('spreadsheet_id'):
            click.echo(f"  Sheet:  https://docs.google.com/spreadsheets/d/{result['spreadsheet_id']}")
    except Exception as e:
        click.echo(f"\n❌ ERROR: {e}", err=True)
        raise click.Abort()


@audit.command("gsc-perf")
@blog_option(required=True)
@click.option('--days', type=int, default=28, help='Window in days (default: 28)')
@click.option('--top-kw', type=int, default=20, help='Number of queries to return (default: 20)')
@click.option('--dry-run', is_flag=True, help='Do not write the local JSON dump')
def gsc_perf(blog, days, top_kw, dry_run):
    """SEO performance of a site via the GSC MCP: totals + top keywords (chat summary)."""
    from scripts.audit.gsc_perf import run_gsc_perf

    click.echo(f"\n📊 GSC PERF - {blog} ({days}d, top {top_kw} KW)")
    try:
        r = run_gsc_perf(blog, days=days, top_kw=top_kw, dry_run=dry_run)
        t = r["totals"]
        click.echo(f"  Source:      {r['source']}")
        click.echo(f"  Clicks:      {t['clicks']:,}")
        click.echo(f"  Impressions: {t['impressions']:,}")
        click.echo(f"  CTR:         {t['ctr']}%")
        click.echo(f"  Position:    {t['position']}")
        top = r.get("top_keywords", [])
        if top:
            click.echo(f"\n  Top {len(top)} queries:")
            for k in top:
                click.echo(f"    {k['clicks']:>6,} clicks | pos {k['position']:>4} | {k['query']}")
        if r.get('output_path'):
            click.echo(f"\n  Dump: {r['output_path']}")
    except Exception as e:
        click.echo(f"\n❌ ERROR: {e}", err=True)
        raise click.Abort()


@audit.command("gsc-page")
@click.argument('url')
@click.option('--days', type=int, default=28, help='Window in days (default: 28)')
@click.option('--dry-run', is_flag=True, help='Do not write the local JSON dump')
def gsc_page(url, days, dry_run):
    """GSC performance of a specific URL via the MCP: queries, clicks, impressions, position."""
    from scripts.audit.gsc_perf import run_gsc_page

    click.echo(f"\n📄 GSC PAGE - {url} ({days}d)")
    try:
        r = run_gsc_page(url, days=days, dry_run=dry_run)
        t = r["totals"]
        click.echo(f"  Site: {r['site_id']} | Source: {r['source']}")
        click.echo(f"  Clicks:      {t['clicks']:,}")
        click.echo(f"  Impressions: {t['impressions']:,}")
        click.echo(f"  CTR:         {t['ctr']}%")
        click.echo(f"  Position:    {t['position']} (impression-weighted average)")
        kws = r.get("keywords", [])
        if kws:
            click.echo(f"\n  {len(kws)} queries:")
            for k in kws:
                click.echo(f"    {k['clicks']:>4,} clicks | {k['impressions']:>6,} impr | pos {k['position']:>4} | {k['query']}")
        else:
            click.echo("  (no queries - page had no traffic over the period)")
        if r.get('output_path'):
            click.echo(f"\n  Dump: {r['output_path']}")
    except Exception as e:
        click.echo(f"\n❌ ERROR: {e}", err=True)
        raise click.Abort()


@audit.command("gsc-state")
@site_option(required=True, dest='site')
@click.option('--months', type=int, default=3, help='Period in months (default: 3)')
@click.option('--top-pos', type=int, default=30, help='Max position to keep (default: 30)')
@click.option('--min-impressions', type=int, default=0, help='Min impressions to keep')
@click.option('--dry-run', is_flag=True, help='Local dump only')
def gsc_state(site, months, top_pos, min_impressions, dry_run):
    """SEO state of play via the GSC API (top-N ranking keywords → dedicated Sheet, GSC_* tabs)."""
    from scripts.audit.gsc_state import run_gsc_state

    click.echo(f"\n📊 GSC STATE - {site} (top {top_pos}, {months}m)")
    if dry_run:
        click.echo("(dry-run mode)")
    try:
        result = run_gsc_state(site, months=months, top_pos=top_pos, min_impressions=min_impressions, dry_run=dry_run)
        click.echo(f"\n✅ Done:")
        click.echo(f"  KW:         {result['nb_kw']}")
        click.echo(f"  Categories: {result['nb_categories']}")
        click.echo(f"  Pages:      {result['nb_pages']}")
        if result.get('output_path'):
            click.echo(f"  Dump:       {result['output_path']}")
        if result.get('spreadsheet_id'):
            click.echo(f"  Sheet:      https://docs.google.com/spreadsheets/d/{result['spreadsheet_id']}")
    except Exception as e:
        click.echo(f"\n❌ ERROR: {e}", err=True)
        raise click.Abort()
