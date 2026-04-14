"""
Commandes d'audit.

Usage:
    cw audit editorial <url> --blog enseigna
    cw audit gsc <url>
    cw audit serp <url> --keyword "parcoursup"
    cw audit cannibalization <url>
"""

import os
import click
from pathlib import Path

from scripts.audit import EditorialAuditor, GSCAnalyzer, SERPAnalyzer
from scripts.cocon import CannibalizationDetector, SiblingFetcher
from scripts.wordpress.stseo_client import STSEOClient
from scripts.sheets import SheetsClient


@click.group()
def audit():
    """Audits de qualité et performance."""
    pass


@audit.command()
@click.argument('url')
@click.option('--blog', required=True, help='Blog ID')
@click.option('--spreadsheet-id', default=lambda: os.environ.get('SPREADSHEET_ID'), help='Google Sheet ID (auto depuis .env)')
def editorial(url, blog, spreadsheet_id):
    """
    Audit éditorial (E-E-A-T, fraîcheur, vérité, généralité).

    Quality Gate: score < 4.0/10 bloque le refresh.
    """
    click.echo(f"\n🔍 AUDIT ÉDITORIAL")
    click.echo(f"URL:  {url}")
    click.echo(f"Blog: {blog}\n")

    # Fetch content via STSEO API
    click.echo("[1/2] Récupération contenu via STSEO API...")
    stseo = STSEOClient()
    stseo_result = stseo.get_post_content_by_link(url)

    if not stseo_result or not stseo_result.get("post_content"):
        click.echo("  ✗ Impossible de récupérer le contenu via STSEO", err=True)
        raise click.Abort()

    html = stseo_result["post_content"]
    click.echo(f"  ✓ HTML récupéré ({len(html)} chars)")

    # Run editorial audit
    click.echo("[2/2] Audit éditorial...")
    auditor = EditorialAuditor(blog_id=blog, base_path=Path.cwd())

    try:
        report = auditor.audit_article(html, url)

        click.echo(f"\n📊 RÉSULTATS:")
        click.echo(f"  Score global:     {report.overall_score:.1f}/10")
        click.echo(f"  Verdict:          {report.verdict}")
        click.echo(f"  Blocage:          {'OUI' if report.is_blocking else 'NON'}")
        click.echo(f"\n  Détails:")
        click.echo(f"    Truth:         {report.truth_score:.1f}/10")
        click.echo(f"    E-E-A-T:       {report.eeat_score:.1f}/10")
        click.echo(f"    Freshness:     {report.freshness_score:.1f}/10")
        click.echo(f"    Genericness:   {report.genericness_score:.1f}/10")

        if report.blocking_issues:
            click.echo(f"\n  ⚠ Issues bloquants ({len(report.blocking_issues)}):")
            for issue in report.blocking_issues[:5]:
                click.echo(f"    - {issue}")

        if report.is_blocking:
            click.echo("\n❌ Quality Gate: BLOQUÉ (score < 4.0/10)")
        else:
            click.echo("\n✅ Quality Gate: PASSÉ")

    except Exception as e:
        click.echo(f"\n❌ ERREUR: {str(e)}", err=True)
        raise click.Abort()


@audit.command()
@click.argument('url')
@click.option('--blog', required=True, help='Blog ID')
@click.option('--spreadsheet-id', default=lambda: os.environ.get('SPREADSHEET_ID'), help='Google Sheet ID (auto depuis .env)')
def cannibalization(url, blog, spreadsheet_id):
    """
    Détection de cannibalization entre siblings.

    Vérifie si des H2 cannibalisent les H1 des siblings.
    """
    click.echo(f"\n🔍 AUDIT CANNIBALIZATION")
    click.echo(f"URL:  {url}")
    click.echo(f"Blog: {blog}\n")

    if not spreadsheet_id:
        click.echo("❌ --spreadsheet-id requis pour fetch siblings", err=True)
        raise click.Abort()

    # Scrape HTML
    click.echo("[1/3] Scraping HTML...")
    scraper = WebScraper()
    html = scraper.fetch_html(url)

    if not html:
        click.echo("  ✗ Impossible de scraper l'URL", err=True)
        raise click.Abort()

    click.echo(f"  ✓ HTML téléchargé ({len(html)} chars)")

    # Fetch siblings
    click.echo("[2/3] Récupération siblings...")
    sheets_client = SheetsClient(spreadsheet_id)
    fetcher = SiblingFetcher(sheets_client)
    siblings = fetcher.fetch_siblings(url)

    if not siblings:
        click.echo("  ℹ Aucun sibling trouvé (article STANDALONE)")
        return

    click.echo(f"  ✓ {len(siblings)} siblings trouvés")

    # Detect cannibalization
    click.echo("[3/3] Détection cannibalization...")
    detector = CannibalizationDetector()
    report = detector.detect_cannibalization(html, url, siblings)

    click.echo(f"\n📊 RÉSULTATS:")
    click.echo(f"  Matches trouvés:  {report.matches_count}")
    click.echo(f"  HIGH risk:        {report.high_risk_count}")

    if report.has_cannibalization:
        click.echo(f"\n  ⚠ CANNIBALIZATION DÉTECTÉE:")
        for match in report.matches[:5]:
            click.echo(f"\n    H2: {match.h2_section[:60]}")
            click.echo(f"    Sibling H1: {match.sibling_h1[:60]}")
            click.echo(f"    Score: {match.similarity_score:.2f} ({match.severity})")
            click.echo(f"    URL sibling: {match.sibling_url}")

        click.echo(f"\n❌ Action requise: Remplacer {report.high_risk_count} H2 sections")
    else:
        click.echo(f"\n✅ Pas de cannibalization détectée")


@audit.command()
@click.argument('url')
@click.option('--keyword', help='Mot-clé principal (optionnel)')
def serp(url, keyword):
    """
    Audit SERP (PAA, secondary keywords).

    Analyse le SERP via DataforSEO API directe.
    """
    click.echo(f"\n🔍 AUDIT SERP")
    click.echo(f"URL: {url}")
    if keyword:
        click.echo(f"KW:  {keyword}\n")

    # Analyze SERP
    click.echo("Analyse SERP...")
    analyzer = SERPAnalyzer()

    try:
        # Si pas de keyword, essayer d'extraire du title
        if not keyword:
            scraper = WebScraper()
            html = scraper.fetch_html(url)
            # Extraire title (simpliste)
            import re
            title_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
            keyword = title_match.group(1) if title_match else url

        result = analyzer.analyze_serp(keyword)

        click.echo(f"\n📊 RÉSULTATS:")
        click.echo(f"  PAA questions:      {len(result.get('paa', []))}")
        click.echo(f"  Secondary keywords: {len(result.get('secondary_kw', []))}")

        if result.get('paa'):
            click.echo(f"\n  PAA:")
            for q in result['paa'][:5]:
                click.echo(f"    - {q}")

        if result.get('secondary_kw'):
            click.echo(f"\n  Secondary KW:")
            for kw in result['secondary_kw'][:10]:
                click.echo(f"    - {kw}")

    except Exception as e:
        click.echo(f"\n❌ ERREUR: {str(e)}", err=True)
        raise click.Abort()


@audit.command("ahrefs-state")
@click.option('--site', required=True, type=click.Choice(['superprof-ressources', 'enseigna']), help='Site cible')
@click.option('--months', type=int, default=None, help='Période en mois (défaut: config)')
@click.option('--limit', type=int, default=None, help='Nb max de KW (défaut: config)')
@click.option('--from-csv', type=str, default=None, help='Lire un export CSV Ahrefs au lieu de l\'API')
@click.option('--dry-run', is_flag=True, help='Dump local seulement, pas de push Sheets')
def ahrefs_state(site, months, limit, from_csv, dry_run):
    """État des lieux SEO via Ahrefs (KW positionnés → Google Sheets dédiée)."""
    from scripts.audit.ahrefs_state import run_ahrefs_state

    click.echo(f"\n📊 AHREFS STATE — {site}")
    if dry_run:
        click.echo("(dry-run mode)")

    try:
        result = run_ahrefs_state(site, months=months, limit=limit, dry_run=dry_run, from_csv=from_csv)
        click.echo(f"\n✅ Terminé:")
        click.echo(f"  KW:         {result['nb_kw']}")
        click.echo(f"  Catégories: {result['nb_categories']}")
        click.echo(f"  Pages:      {result['nb_pages']}")
        if result.get('output_path'):
            click.echo(f"  Dump:       {result['output_path']}")
        if result.get('spreadsheet_id'):
            click.echo(f"  Sheet:      https://docs.google.com/spreadsheets/d/{result['spreadsheet_id']}")
    except Exception as e:
        click.echo(f"\n❌ ERREUR: {e}", err=True)
        raise click.Abort()


@audit.command("enseigna-refresh-list")
@click.option('--months', type=int, default=6, help='Période GSC en mois (défaut: 6)')
@click.option('--dry-run', is_flag=True, help='Dump local seulement, pas de push Sheets')
def enseigna_refresh_list(months, dry_run):
    """Pull GSC enseigna, filtre Avis/Versus, push Sheet refresh list."""
    from scripts.audit.enseigna_refresh_list import run

    click.echo(f"\n📊 ENSEIGNA REFRESH LIST ({months}m)")
    if dry_run:
        click.echo("(dry-run mode)")
    try:
        result = run(months=months, dry_run=dry_run)
        click.echo(f"\n✅ Terminé:")
        click.echo(f"  Avis:   {result['avis']}")
        click.echo(f"  Versus: {result['versus']}")
        if result.get('output_path'):
            click.echo(f"  Dump:   {result['output_path']}")
        if result.get('spreadsheet_id'):
            click.echo(f"  Sheet:  https://docs.google.com/spreadsheets/d/{result['spreadsheet_id']}")
    except Exception as e:
        click.echo(f"\n❌ ERREUR: {e}", err=True)
        raise click.Abort()


@audit.command("gsc-state")
@click.option('--site', required=True, type=click.Choice(['superprof-ressources', 'enseigna']), help='Site cible')
@click.option('--months', type=int, default=3, help='Période en mois (défaut: 3)')
@click.option('--top-pos', type=int, default=30, help='Position max à conserver (défaut: 30)')
@click.option('--min-impressions', type=int, default=0, help='Impressions min à conserver')
@click.option('--dry-run', is_flag=True, help='Dump local seulement')
def gsc_state(site, months, top_pos, min_impressions, dry_run):
    """État des lieux SEO via GSC API (KW positionnés top N → Sheet dédiée, onglets GSC_*)."""
    from scripts.audit.gsc_state import run_gsc_state

    click.echo(f"\n📊 GSC STATE — {site} (top {top_pos}, {months}m)")
    if dry_run:
        click.echo("(dry-run mode)")
    try:
        result = run_gsc_state(site, months=months, top_pos=top_pos, min_impressions=min_impressions, dry_run=dry_run)
        click.echo(f"\n✅ Terminé:")
        click.echo(f"  KW:         {result['nb_kw']}")
        click.echo(f"  Catégories: {result['nb_categories']}")
        click.echo(f"  Pages:      {result['nb_pages']}")
        if result.get('output_path'):
            click.echo(f"  Dump:       {result['output_path']}")
        if result.get('spreadsheet_id'):
            click.echo(f"  Sheet:      https://docs.google.com/spreadsheets/d/{result['spreadsheet_id']}")
    except Exception as e:
        click.echo(f"\n❌ ERREUR: {e}", err=True)
        raise click.Abort()
