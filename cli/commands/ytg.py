"""
Commandes YourTextGuru (YTG).

Usage:
    srw ytg create-guide --keyword "bienfaits yoga"
    srw ytg check-guide --guide-id ABC123
    srw ytg batch-prefetch --spreadsheet-id ID [--blog moments-yoga]
    srw ytg analyze --guide-id ABC123 --html-file path/to/article.html
"""

import json
import sys
from pathlib import Path
from typing import Optional

import click

from scripts.audit.ytg_analyzer import YTGAnalyzer, YTGAPIError, YTGGuideTimeoutError


@click.group()
def ytg():
    """Gestion des guides sémantiques YourTextGuru."""
    pass


@ytg.command(name='create-guide')
@click.option('--keyword', required=True, help='Mot-clé principal pour le guide')
@click.option('--lang', default='fr', show_default=True, help='Langue (fr, en, ...)')
@click.option('--country', default='fr', show_default=True, help='Pays (fr, us, ...)')
def create_guide(keyword, lang, country):
    """
    Crée un guide YTG pour un mot-clé et attend le résultat.

    Affiche le guide_id, les scores SOSEO/DSEO concurrents et la liste
    des termes à optimiser.
    """
    click.echo(f"\n[YTG] Création guide pour : '{keyword}'")
    click.echo(f"      Langue: {lang} | Pays: {country}\n")

    analyzer = YTGAnalyzer()
    if not analyzer.is_configured:
        click.echo(
            "[ERREUR] YTG_API_KEY manquant. Ajouter dans .env ou "
            "~/.credentials/ytg/credentials.json",
            err=True
        )
        sys.exit(1)

    try:
        result = analyzer.create_and_wait(keyword, language=lang, country=country)
        if not result:
            click.echo("[ERREUR] Création du guide échouée.", err=True)
            sys.exit(1)

        click.echo(f"Guide ID   : {result.guide_id}")
        click.echo(f"Statut     : {result.status}")
        click.echo()
        click.echo("Scores concurrents :")
        click.echo(f"  TOP 3  — SOSEO: {result.top3_soseo:.1f}%  DSEO: {result.top3_dseo:.1f}%")
        click.echo(f"  TOP 10 — SOSEO: {result.top10_soseo:.1f}%  DSEO: {result.top10_dseo:.1f}%")
        click.echo()
        click.echo(f"Termes à optimiser ({len(result.semantic_terms)}) :")

        # Grouper par couleur
        by_color = {"blue": [], "green": [], "orange": [], "red": []}
        for term in result.terms:
            by_color.get(term.color, by_color["green"]).append(term.term)

        if by_color["blue"]:
            click.echo(f"  Sous-optimisés (bleu)  : {', '.join(by_color['blue'][:15])}")
        if by_color["orange"]:
            click.echo(f"  Forte optim. (orange)  : {', '.join(by_color['orange'][:15])}")
        if by_color["red"]:
            click.echo(f"  En surdose (rouge)     : {', '.join(by_color['red'][:15])}")
        if by_color["green"]:
            click.echo(f"  Normal (vert)          : {', '.join(by_color['green'][:15])}")

        click.echo()
        click.echo(
            f"[OK] Guide pret. Ajouter dans audit_data.json : "
            f'"ytg_guide_id": "{result.guide_id}"'
        )

    except YTGAPIError as e:
        click.echo(f"[ERREUR API] {e}", err=True)
        sys.exit(1)
    except YTGGuideTimeoutError as e:
        click.echo(f"[TIMEOUT] Guide non pret apres {e.attempts} tentatives.", err=True)
        click.echo(f"Reessayer plus tard : srw ytg check-guide --guide-id {e.guide_id}")
        sys.exit(1)


@ytg.command(name='check-guide')
@click.option('--guide-id', required=True, help='ID du guide YTG à vérifier')
def check_guide(guide_id):
    """Vérifie le statut d'un guide YTG existant."""
    click.echo(f"\n[YTG] Vérification guide : {guide_id}\n")

    analyzer = YTGAnalyzer()
    if not analyzer.is_configured:
        click.echo("[ERREUR] YTG_API_KEY manquant.", err=True)
        sys.exit(1)

    try:
        raw = analyzer.get_guide_status(guide_id)
        if not raw:
            click.echo("[ERREUR] Impossible de récupérer le guide.", err=True)
            sys.exit(1)

        status = raw.get("status") or raw.get("data", {}).get("status", "?")
        click.echo(f"Statut : {status}")

        if status == "ready":
            result = analyzer.get_guide(guide_id)
            if result:
                click.echo(f"TOP 3  SOSEO: {result.top3_soseo:.1f}%  DSEO: {result.top3_dseo:.1f}%")
                click.echo(f"TOP 10 SOSEO: {result.top10_soseo:.1f}%  DSEO: {result.top10_dseo:.1f}%")
                click.echo(f"Termes      : {len(result.semantic_terms)}")
                if result.semantic_terms:
                    click.echo(f"Apercu      : {', '.join(result.semantic_terms[:10])}...")
        else:
            click.echo("Guide pas encore prêt. Relancer dans quelques minutes.")
    except YTGAPIError as e:
        click.echo(f"[ERREUR API] {e}", err=True)
        sys.exit(1)


@ytg.command(name='list-guides')
@click.option('--lang', default=None, help='Filtrer par langue (ex: fr)')
@click.option('--status', default=None, help='Filtrer par statut (ready, in_progress, ...)')
def list_guides(lang, status):
    """
    Liste les guides YTG dans le groupe thematic-websites.

    Permet de vérifier les guides existants avant d'en créer de nouveaux.
    """
    click.echo(f"\n[YTG] Liste des guides (groupId={YTGAnalyzer.DEFAULT_GROUP_ID})\n")

    analyzer = YTGAnalyzer()
    if not analyzer.is_configured:
        click.echo("[ERREUR] YTG_API_KEY manquant.", err=True)
        sys.exit(1)

    try:
        guides = analyzer.list_guides(
            group_id=YTGAnalyzer.DEFAULT_GROUP_ID,
            status=status,
        )
        if not guides:
            click.echo("Aucun guide trouvé.")
            return

        click.echo(f"{'ID':<12} {'Statut':<14} {'Langue':<8} {'Query'}")
        click.echo("-" * 70)
        for g in guides:
            gid = str(g.get("id", "?"))
            if g.get("ready"):
                gstatus = "ready"
            elif g.get("inProgress"):
                gstatus = "in_progress"
            elif g.get("error"):
                gstatus = "error"
            else:
                gstatus = "waiting"
            glang = str(g.get("lang", "?"))
            query = str(g.get("query", g.get("keyword", "?")))
            click.echo(f"{gid:<12} {gstatus:<14} {glang:<8} {query}")

        click.echo(f"\nTotal : {len(guides)} guide(s)")
    except YTGAPIError as e:
        click.echo(f"[ERREUR API] {e}", err=True)
        sys.exit(1)


@ytg.command(name='batch-prefetch')
@click.option('--spreadsheet-id', required=True, help='Google Sheet ID')
@click.option('--blog', help='Filtrer par blog_id')
@click.option('--lang', default='fr', show_default=True, help='Langue des guides')
@click.option('--country', default='fr', show_default=True, help='Pays des guides')
@click.option('--create-missing', is_flag=True, default=False,
              help='Créer les guides manquants (sinon: match uniquement)')
def batch_prefetch(spreadsheet_id, blog, lang, country, create_missing):
    """
    Match la colonne D du spreadsheet (main_keyword) avec les guides YTG existants.

    1. Télécharge TOUS les guides YTG du groupe en une seule passe
    2. Lit le spreadsheet (col D = main_keyword) pour chaque URL
    3. Mappe localement : main_keyword == YTG query
    4. Pour chaque match → écrit ytg_guide_id dans audit_data.json
    5. Avec --create-missing : crée les guides absents

    A lancer AVANT srw batch audit-serp pour que le STEP 2.5 soit
    un cache hit (< 1s) et n'impacte pas le temps du workflow principal.
    """
    import glob
    from scripts.sheets.sheets_client import SheetsClient

    click.echo(f"\n[YTG] Batch prefetch — matching col D vs guides YTG")
    if blog:
        click.echo(f"Blog: {blog}")
    click.echo()

    analyzer = YTGAnalyzer()
    if not analyzer.is_configured:
        click.echo("[ERREUR] YTG_API_KEY manquant.", err=True)
        sys.exit(1)

    # ÉTAPE 1 : Télécharger TOUS les guides YTG en une seule passe
    click.echo("[1/3] Téléchargement des guides YTG...")
    all_guides = analyzer.list_guides_all()
    query_index = analyzer.build_query_index(all_guides)
    click.echo(f"      {len(all_guides)} guides téléchargés, index prêt")
    click.echo()

    # ÉTAPE 2 : Lire le spreadsheet pour récupérer les main_keywords (col D)
    click.echo("[2/3] Lecture du spreadsheet (col D = main_keyword)...")
    sheets = SheetsClient(spreadsheet_id=spreadsheet_id)
    sheet_rows = []
    try:
        data = sheets._read_sheet(sheets.SHEET_REFRESHS_AUDIT)
        for i, row in enumerate(data[1:], start=2):  # skip header
            if len(row) < 4:
                continue
            row_blog = row[0] if len(row) > 0 else ""
            row_url = row[2] if len(row) > 2 else ""   # col C
            row_kw = row[3] if len(row) > 3 else ""    # col D
            if not row_kw or not row_url:
                continue
            if blog and row_blog != blog:
                continue
            sheet_rows.append({
                "blog_id": row_blog,
                "url": row_url,
                "main_keyword": row_kw,
                "row_idx": i,
            })
    except Exception as e:
        click.echo(f"[ERREUR] Lecture spreadsheet: {e}", err=True)
        sys.exit(1)

    click.echo(f"      {len(sheet_rows)} URLs avec main_keyword")
    click.echo()

    # ÉTAPE 3 : Matching local + mise à jour audit_data.json
    click.echo("[3/3] Matching et mise à jour audit_data.json...")
    context_dir = Path.cwd() / "_shared" / "context"

    matched = 0
    already_cached = 0
    created = 0
    missing = 0
    failed = 0

    for row in sheet_rows:
        kw = row["main_keyword"]
        kw_norm = kw.lower().strip()
        url = row["url"]

        # Trouver l'audit_data.json correspondant à cette URL
        audit_file = _find_audit_file(context_dir, url)

        # Vérifier si déjà en cache dans audit_data.json
        audit_data = {}
        if audit_file and audit_file.exists():
            try:
                with open(audit_file) as f:
                    audit_data = json.load(f)
            except Exception:
                pass

        if audit_data.get("ytg_guide_id"):
            already_cached += 1
            continue

        # Matching local dans l'index
        guide = query_index.get(kw_norm)

        if guide:
            guide_id = str(guide.get("id", ""))
            if not guide_id:
                continue

            # Guide trouvé et ready → fetch le détail pour les termes
            if guide.get("ready"):
                try:
                    raw = analyzer.get_guide_status(guide_id)
                    if raw and analyzer._is_ready(raw):
                        result = analyzer._parse_guide_result(guide_id, kw, raw)
                        _save_ytg_to_audit(audit_file, audit_data, result, url, row["blog_id"])
                        click.echo(
                            f"  [MATCH] {kw[:45]:<45} → guide {guide_id} "
                            f"({len(result.semantic_terms)} termes)"
                        )
                        matched += 1
                    else:
                        click.echo(f"  [WAIT]  {kw[:45]} guide {guide_id} pas encore prêt")
                        missing += 1
                except Exception as e:
                    click.echo(f"  [ERR]   {kw[:45]}: {e}", err=True)
                    failed += 1
            else:
                click.echo(f"  [WAIT]  {kw[:45]} guide {guide_id} en cours de génération")
                missing += 1
        else:
            # Pas de guide existant
            if create_missing:
                click.echo(f"  [CREATE] {kw[:45]}...")
                try:
                    result = analyzer.create_and_wait(kw, language=lang, country=country)
                    if result:
                        _save_ytg_to_audit(audit_file, audit_data, result, url, row["blog_id"])
                        click.echo(
                            f"           OK — guide {result.guide_id} "
                            f"({len(result.semantic_terms)} termes, "
                            f"SOSEO cible={result.top3_soseo:.0f}%)"
                        )
                        created += 1
                    else:
                        failed += 1
                except (YTGAPIError, YTGGuideTimeoutError) as e:
                    click.echo(f"           ERREUR: {e}", err=True)
                    failed += 1
            else:
                click.echo(f"  [MISS]  {kw[:45]} — aucun guide (utiliser --create-missing)")
                missing += 1

    click.echo()
    click.echo("[YTG] Résumé :")
    click.echo(f"  Matchés (maj audit_data) : {matched}")
    click.echo(f"  Déjà en cache            : {already_cached}")
    if create_missing:
        click.echo(f"  Créés                    : {created}")
    click.echo(f"  Sans guide               : {missing}")
    click.echo(f"  Erreurs                  : {failed}")


def _find_audit_file(context_dir: Path, url: str) -> Optional[Path]:
    """
    Cherche le fichier audit_data.json pour une URL donnée.

    Stratégie : slug de l'URL → répertoire dans _shared/context/.
    Ex: https://moments-yoga.fr/les-bienfaits-du-yoga
    → _shared/context/https_www_moments_yoga_fr_les_bienfaits_du_yoga/audit_data.json
    """
    import re
    # Slugifier l'URL comme le fait le projet
    slug = re.sub(r'[^a-z0-9]', '_', url.lower())
    slug = re.sub(r'_+', '_', slug).strip('_')
    candidate = context_dir / slug / "audit_data.json"
    if candidate.exists():
        return candidate
    # Recherche partielle si le slug exact ne correspond pas
    try:
        for d in context_dir.iterdir():
            if not d.is_dir():
                continue
            audit_file = d / "audit_data.json"
            if not audit_file.exists():
                continue
            # Vérifier l'URL dans le fichier
            try:
                with open(audit_file) as f:
                    data = json.load(f)
                if data.get("url", "") == url or data.get("blogpost_url", "") == url:
                    return audit_file
            except Exception:
                continue
    except Exception:
        pass
    return candidate  # Retourne le chemin calculé même s'il n'existe pas encore


def _save_ytg_to_audit(
    audit_file: Optional[Path],
    audit_data: dict,
    result,
    url: str,
    blog_id: str,
) -> None:
    """Écrit les données YTG dans audit_data.json (création si nécessaire)."""
    if not audit_file:
        return

    if not audit_data:
        audit_data = {"url": url, "blog_id": blog_id}

    audit_data["ytg_guide_id"] = result.guide_id
    audit_data["semantic_field_override"] = result.semantic_terms
    audit_data["ytg_competitor_targets"] = {
        "top3_soseo": result.top3_soseo,
        "top3_dseo": result.top3_dseo,
        "top10_soseo": result.top10_soseo,
        "top10_dseo": result.top10_dseo,
    }
    audit_data["ytg_term_colors"] = result.term_colors

    audit_file.parent.mkdir(parents=True, exist_ok=True)
    with open(audit_file, "w", encoding="utf-8") as f:
        json.dump(audit_data, f, ensure_ascii=False, indent=2)


@ytg.command(name='analyze')
@click.option('--guide-id', required=True, help='ID du guide YTG')
@click.option('--html-file', required=True, type=click.Path(exists=True),
              help='Fichier HTML à analyser')
def analyze(guide_id, html_file):
    """
    Analyse un fichier HTML contre un guide YTG existant.

    Affiche le SOSEO et DSEO obtenus pour notre contenu,
    comparés aux moyennes TOP 3/TOP 10.
    """
    click.echo(f"\n[YTG] Analyse contenu contre guide {guide_id}")
    click.echo(f"      Fichier: {html_file}\n")

    analyzer = YTGAnalyzer()
    if not analyzer.is_configured:
        click.echo("[ERREUR] YTG_API_KEY manquant.", err=True)
        sys.exit(1)

    # Lire le contenu HTML et en extraire le texte
    try:
        from bs4 import BeautifulSoup
        with open(html_file, encoding="utf-8") as f:
            html = f.read()
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(separator=" ", strip=True)
    except Exception as e:
        click.echo(f"[ERREUR] Lecture fichier: {e}", err=True)
        sys.exit(1)

    try:
        result = analyzer.analyze_content(guide_id, text)
        if not result:
            click.echo("[ERREUR] Analyse échouée.", err=True)
            sys.exit(1)

        click.echo(f"Notre contenu  — SOSEO: {result.get('our_soseo', 0):.1f}%  "
                   f"DSEO: {result.get('our_dseo', 0):.1f}%")

        colors = result.get("term_colors", {})
        if colors:
            blue = [t for t, c in colors.items() if c == "blue"]
            red = [t for t, c in colors.items() if c == "red"]
            orange = [t for t, c in colors.items() if c == "orange"]
            click.echo()
            if blue:
                click.echo(f"Sous-optimises (bleu)  : {', '.join(blue[:10])}")
            if orange:
                click.echo(f"Forte optim.  (orange) : {', '.join(orange[:10])}")
            if red:
                click.echo(f"En surdose    (rouge)  : {', '.join(red[:10])}")

    except YTGAPIError as e:
        click.echo(f"[ERREUR API] {e}", err=True)
        sys.exit(1)
