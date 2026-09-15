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


@audit.command("gsc-tab")
@site_option(required=True, dest='site')
@click.option('--tab', default=None,
              help='Declared tab name (sheets.tabs of site.json), e.g. "New Growing List". '
                   'Required for --source sheet, ignored for --source notion')
@click.option('--source', type=click.Choice(['sheet', 'notion']), default='sheet',
              help='Where the tracked URLs come from: Google Sheets tab (default) '
                   'or the Notion publications database (notion.publications of site.json)')
@click.option('--days', type=int, default=28, help='Current window in days (default: 28), ignored if --start/--end')
@click.option('--start', default=None, help='Current window start YYYY-MM-DD (with --end)')
@click.option('--end', default=None, help='Current window end YYYY-MM-DD (with --start)')
@click.option('--compare-start', default=None,
              help='Reference window start YYYY-MM-DD (with --compare-end). '
                   'Use it for year-over-year; default is the period of the same '
                   'length immediately before the current window')
@click.option('--compare-end', default=None,
              help='Reference window end YYYY-MM-DD (with --compare-start)')
@click.option('--category', 'categories', multiple=True,
              help='Restrict to these editorial categories (repeatable, accent/case '
                   'insensitive), e.g. --category "Soutien Scolaire" --category Langues. '
                   'Requires --source notion (a Sheet tab carries no category)')
@click.option('--top', type=int, default=15, help='Rows per movers table (default: 15)')
@click.option('--dry-run', is_flag=True, help='Do not write the local JSON dump')
def gsc_tab(site, tab, source, days, start, end, compare_start, compare_end,
            categories, top, dry_run):
    """Refresh monitoring of a work tab: GSC gains/losses vs the previous window."""
    from scripts.audit.gsc_tab_perf import run_gsc_tab

    if source == 'sheet' and not tab:
        raise click.UsageError('--tab is required with --source sheet')
    if categories and source != 'notion':
        raise click.UsageError('--category requires --source notion')

    def fmt_delta(n):
        return f"+{n:,}" if n > 0 else f"{n:,}"

    def fmt_pct(v):
        return "n/a" if v is None else (f"+{v}%" if v > 0 else f"{v}%")

    def fmt_ctr(v):
        return "n/a" if v is None else f"{v}%"

    def fmt_pos(pg):
        b, a = pg["position_before"], pg["position_after"]
        if b is None or a is None:
            return "pos   n/a      "
        arrow = "↑" if a < b else ("↓" if a > b else "=")
        return f"pos {b:>5} → {a:>5} {arrow}"

    click.echo(f"\n📈 GSC TAB DELTA - {site} / {tab or 'Publications Notion'} [{source}]")
    try:
        r = run_gsc_tab(site, tab=tab, days=days, start=start, end=end,
                        dry_run=dry_run, source=source,
                        compare_start=compare_start, compare_end=compare_end,
                        categories=list(categories) or None)
        p, pp, t = r["period"], r["previous_period"], r["totals"]
        click.echo(f"  Window:   {p['start']} → {p['end']}  (vs {pp['start']} → {pp['end']})")
        if r.get("length_mismatch"):
            click.echo(f"  ⚠️  Durées inégales : {p.get('days')} j vs {pp.get('days')} j "
                       "— volumes de clics non directement comparables")
        click.echo(f"  URLs:     {t['urls']} | ↗ {len(r['progressions'])} | "
                   f"↘ {len(r['regressions'])} | = {len(r['stable'])}")
        click.echo(f"  Clicks:   {t['clicks_before']:,} → {t['clicks_after']:,} "
                   f"({fmt_delta(t['clicks_delta'])}, {fmt_pct(t['clicks_delta_pct'])})")
        click.echo(f"  Impr.:    {t['impressions_before']:,} → {t['impressions_after']:,} "
                   f"({fmt_delta(t['impressions_delta'])}, "
                   f"{fmt_pct(t['impressions_delta_pct'])})")
        click.echo(f"  CTR:      {fmt_ctr(t['ctr_before'])} → {fmt_ctr(t['ctr_after'])}")

        nu, lfl = r.get("new_urls") or {}, r.get("like_for_like") or {}
        if nu.get("urls"):
            click.echo(f"\n  ⚠️  {nu['urls']}/{t['urls']} URLs sans impression sur la période "
                       f"de référence (+{nu['clicks_after']:,} clics, "
                       f"+{nu['impressions_after']:,} impr créés, pas gagnés)")
            click.echo(f"      À périmètre constant ({lfl['urls']} URLs) : "
                       f"clics {fmt_pct(lfl['clicks_delta_pct'])}, "
                       f"impr {fmt_pct(lfl['impressions_delta_pct'])}, "
                       f"CTR {fmt_ctr(lfl['ctr_before'])} → {fmt_ctr(lfl['ctr_after'])}")

        for axis_label, groups, sort_by_name in (
            ("Par statut éditorial", r.get("by_status") or {}, False),
            ("Par catégorie", r.get("by_category") or {}, False),
            ("Par année de publication", r.get("by_year") or {}, True),
        ):
            if not groups:
                continue
            click.echo(f"\n  {axis_label}:")
            items = sorted(groups.items()) if sort_by_name else sorted(
                groups.items(), key=lambda kv: kv[1]["clicks_after"], reverse=True)
            for name, g in items:
                click.echo(f"    {name:<28} {g['urls']:>4} URLs | "
                           f"{g['clicks_before']:>6,} → {g['clicks_after']:>6,} clics "
                           f"({fmt_delta(g['clicks_delta'])}, {fmt_pct(g['clicks_delta_pct'])})"
                           f" | {g['impressions_before']:>7,} → {g['impressions_after']:>7,} impr "
                           f"({fmt_pct(g['impressions_delta_pct'])})"
                           f" | CTR {fmt_ctr(g['ctr_before'])} → {fmt_ctr(g['ctr_after'])}")

        for title, rows in (("Top progressions", r["progressions"][:top]),
                            ("Top regressions", r["regressions"][:top])):
            if not rows:
                continue
            click.echo(f"\n  {title}:")
            for pg in rows:
                slug = pg["url"].rstrip("/").rsplit("/", 1)[-1]
                click.echo(f"    {fmt_delta(pg['clicks_delta']):>6} clicks "
                           f"({pg['clicks_before']:>4,} → {pg['clicks_after']:>4,}) | "
                           f"{fmt_pos(pg)} | {pg['status']:<22} | {slug}")

        if r.get('report_path'):
            click.echo(f"\n  📄 Report: {r['report_path']}")
            click.echo(f"     (open it in a browser: open \"{r['report_path']}\")")
        if r.get('output_path'):
            click.echo(f"  Raw data: {r['output_path']}")
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


@audit.command("impact")
@site_option(required=True, dest='site')
@click.option('--month', default=None,
              help='Month of the republications to measure, YYYY-MM (e.g. 2026-08). '
                   'Alternative to --start/--end')
@click.option('--start', default=None,
              help='Republication window start YYYY-MM-DD (with --end)')
@click.option('--end', default=None,
              help='Republication window end YYYY-MM-DD (with --start)')
@click.option('--maturity', type=int, default=30,
              help='Days observed after each republication, and as many before '
                   '(default: 30). Articles with less hindsight than 7 days are skipped')
@click.option('--top', type=int, default=15, help='Rows per article table (default: 15)')
@click.option('--no-wp-check', is_flag=True,
              help='Skip the WordPress consistency check. That check flags articles '
                   'modified again after their refresh (their "after" window mixes '
                   'two interventions); it costs one API call per article')
@click.option('--partial', is_flag=True,
              help='Produce the report even when the most recent articles lack the '
                   '7-day minimum hindsight. Off by default: run too early, a month '
                   'report silently drops its last weeks (August 2026 launched on '
                   'Sept 1st covered 44 of 78 articles)')
@click.option('--top-queries', type=int, default=10,
              help='Queries listed per family (held / gained / lost) on each '
                   'article card of the annex (default: 10)')
@click.option('--no-queries', is_flag=True,
              help='Skip the per-query GSC collection. That collection is what '
                   'shows the semantic shift of a refresh (which queries an '
                   'article gained or lost); it costs one extra paginated call '
                   'per window, not per URL')
@click.option('--pdf', is_flag=True,
              help='Also write an A4 PDF next to the HTML (needs WeasyPrint). '
                   'The PDF holds the director-facing pages only')
@click.option('--pdf-annex', is_flag=True,
              help='Include the per-URL annex in the PDF (~30 pages on a 76-article '
                   'lot). Off by default: the sent document is the short one')
@click.option('--dry-run', is_flag=True, help='Do not write the JSON/HTML report')
def impact(site, month, start, end, maturity, top, top_queries, no_queries,
           pdf, pdf_annex, no_wp_check, partial, dry_run):
    """Monthly impact report: every republished article compared to itself."""
    from scripts.audit.impact_cohort import run_impact

    def fmt_pct(v):
        return "n/a" if v is None else (f"+{v}%" if v > 0 else f"{v}%")

    click.echo(f"\n📈 IMPACT REFRESH - {site} / {month or f'{start} → {end}'}")
    try:
        r = run_impact(site, month=month, start=start, end=end,
                       maturity=maturity, top=top, top_queries=top_queries,
                       with_queries=not no_queries, pdf=pdf, pdf_annex=pdf_annex,
                       check_wp=not no_wp_check, partial=partial,
                       dry_run=dry_run)
        c, o, ctrl = r["counts"], r["overall"], r["control"]
        cov = r.get("coverage") or {}
        click.echo(f"  Republished: {c['republished']} | measurable {c['measurable']} "
                   f"| skipped {c['skipped']} | coverage {cov.get('pct')}%")
        if cov.get("pct", 100) < 100:
            click.echo(f"  ⚠️  Partial report: the most recent articles lack hindsight. "
                       f"Full lot measurable from {cov.get('ready_on')}")
        if cov.get("maturity_max", 0) - cov.get("maturity_min", 0) >= 14:
            click.echo(f"  ⚠️  Uneven hindsight ({cov['maturity_min']}-"
                       f"{cov['maturity_max']} d): read by wave, not by total")
        click.echo(f"  Impressions: {o['impressions_before']:,} → "
                   f"{o['impressions_after']:,} ({fmt_pct(o['impressions_pct'])})")
        click.echo(f"  Clicks:      {o['clicks_before']:,} → {o['clicks_after']:,} "
                   f"({fmt_pct(o['clicks_pct'])})")
        click.echo(f"  CTR:         {o['ctr_before']}% → {o['ctr_after']}%")
        click.echo(f"  Control:     impr {fmt_pct(ctrl['impressions_pct'])}, "
                   f"clicks {fmt_pct(ctrl['clicks_pct'])} (rest of the site, same dates)")
        click.echo(f"  Winners:     {r['winners']}/{c['measurable']} | "
                   f"median × {r['median_factor']}")
        click.echo(f"  Dates from:  {r['pushed_source']}")
        if r.get("touched_after_refresh"):
            click.echo(f"  ⚠️  {len(r['touched_after_refresh'])} articles modified again "
                       "after their refresh (mixed interventions)")

        if r.get("ramp"):
            click.echo("\n  Maturation of the main wave (impressions/day):")
            for w in r["ramp"]:
                click.echo(f"    {w['label']:<16} {w['per_day']:>8}/j  x{w['factor']}")

        click.echo("\n  By hindsight bucket:")
        for k, v in r["by_maturity"].items():
            click.echo(f"    {k:<14} {v['articles']:>3} art. | impr "
                       f"{fmt_pct(v['impressions_pct']):>9} | clics {fmt_pct(v['clicks_pct'])}")

        if r.get("html_path"):
            click.echo(f"\n  Report: {r['html_path']}")
            click.echo(f'  open "{r["html_path"]}"')
        if pdf:
            if r.get("pdf_path"):
                click.echo(f"  PDF:    {r['pdf_path']}")
            else:
                click.echo("  ⚠️  PDF skipped: WeasyPrint not installed "
                           "(pip install weasyprint)")
    except Exception as e:
        click.echo(f"\n❌ ERROR: {e}", err=True)
        raise click.Abort()
