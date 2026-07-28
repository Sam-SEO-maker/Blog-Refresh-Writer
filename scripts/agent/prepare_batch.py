"""Prépare un lot hebdomadaire d'URLs pour la génération (Phase 1).

Pour chaque URL d'une liste fournie :
1. Récupère main_keyword / secondary_keyword / status depuis l'onglet ciblé.
   Si absents, les découvre via GSC (12 mois) et les réinjecte dans le sheet (colonnes B/C).
2. Récupère le post_content via l'API WordPress REST (PAS de scraping)
3. Audit GSC (30j + 12 mois + top 3 queries) → écrit impressions_12m/clicks_12m
   directement dans l'onglet (colonnes D/E) — pas de passage par `GSC_Perfs`.
4. Écrit le bundle de contexte `_shared/context/{slug}/` prêt pour la Phase 2 (génération)

Les URLs dont le statut est terminal (Publié, Redirection 301, Cannibalisation de
KW) sont ignorées ; un statut vide est traité.

L'onglet est ciblable comme dans `/batch` : le layout (col_url, col_keyword,
col_status, header_row) est lu depuis `sheets.tabs` du site.json, jamais supposé
— les onglets n'ont ni la même colonne de statut (NGL = F, Medium Potential = I)
ni le même nombre de lignes d'en-tête.

Usage:
    python -m scripts.agent.prepare_batch <fichier_urls.txt> [--site <slug>] [--tab "<onglet>"]
"""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from _shared.core.constants import canonical_site_slug
from _shared.core.models.sheets_models import RefreshAuditRow
from scripts.agent.orchestrator import RefreshOrchestrator

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("prepare_batch")
for noisy in ("googleapiclient", "google", "urllib3", "scripts.scraping.content_extractor"):
    logging.getLogger(noisy).setLevel(logging.WARNING)

from _shared.core.sheets_config import (
    get_primary_tab_name,
    get_sheets_config,
    get_spreadsheet_id,
)

DEFAULT_BLOG_ID = "superprof.fr-ressources"
# Même plafond par défaut que `cw batch refresh` : chaque URL coûte un fetch WP
# + un audit GSC + un appel SERP + un guide YTG, payés d'avance.
DEFAULT_LIMIT = 50
# Statuts terminaux : la ligne est déjà traitée ou hors périmètre éditorial.
# Aligné sur RefreshOrchestrator._TAB_SKIP_STATUSES (`/batch --tab`).
SKIP_STATUSES = {"publié", "redirection 301", "cannibalisation de kw"}


def resolve_tab_layout(site_slug: str, tab: str | None) -> dict:
    """Layout de l'onglet ciblé, lu depuis `sheets.tabs` du site.json.

    Sans `tab`, retombe sur le premier onglet déclaré (comportement historique
    single-tab). Un onglet inconnu échoue en listant les onglets déclarés,
    plutôt que de renvoyer silencieusement 0 ligne.
    """
    cfg = get_sheets_config(site_slug)
    tabs = cfg.get("tabs") or []
    name = tab or get_primary_tab_name(site_slug, default="New Growing List")
    tab_cfg = next((t for t in tabs if t.get("name") == name), None)
    if tab_cfg is None:
        declared = ", ".join(t.get("name", "?") for t in tabs) or "(aucun)"
        raise ValueError(f"Onglet '{name}' non déclaré pour {site_slug}. Déclarés : {declared}")
    return {
        "name": name,
        "col_url": tab_cfg.get("col_url", 0),
        "col_keyword": tab_cfg.get("col_keyword", 1),
        "col_secondary": tab_cfg.get("col_secondary_keyword", 2),
        "col_status": tab_cfg.get("col_status"),
        "header_row": tab_cfg.get("header_row", 1),
    }


def _gsc_property(site_slug: str) -> str:
    """Propriété GSC du site (racine du site.json)."""
    import json
    from _shared.core.site_paths import SitePaths
    cfg_path = SitePaths().site_config(site_slug)
    if cfg_path.exists():
        prop = json.loads(cfg_path.read_text(encoding="utf-8")).get("gsc_property")
        if prop:
            return prop
    raise ValueError(f"gsc_property absent de la config de {site_slug}")


def _norm(u: str) -> str:
    return (u or "").strip().rstrip("/").lower()


def load_url_list(path: Path) -> list[str]:
    return [l.strip() for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def read_tab_metadata(sheets_client, layout: dict, wanted: set[str]) -> dict[str, dict]:
    """Retourne {url_norm: {url, main_kw, secondary_kw, status, row_index}} pour les URLs voulues."""
    def cell(row, idx):
        if idx is None or idx >= len(row):
            return ""
        return (row[idx] or "").strip()

    data = sheets_client._read_sheet(layout["name"])
    header_row = layout["header_row"]
    out: dict[str, dict] = {}
    for i, row in enumerate(data, start=1):
        if i <= header_row or not row:
            continue
        u = _norm(cell(row, layout["col_url"]))
        if u not in wanted:
            continue
        out[u] = {
            "url": cell(row, layout["col_url"]),
            "main_keyword": cell(row, layout["col_keyword"]),
            "secondary_keyword": cell(row, layout["col_secondary"]),
            "status": cell(row, layout["col_status"]),
            "row_index": i,
        }
    return out


def discover_and_write_keywords(gsc_analyzer, sheets_api, url: str, row_index: int, info: dict) -> None:
    """Découvre main_keyword/secondary_keyword via GSC (12m) si absents et les écrit dans le sheet."""
    from scripts.utils.keyword_discovery_growing_list import (
        write_keyword,
        write_secondary_keyword,
        select_secondary_keyword,
    )

    if not info["main_keyword"]:
        main_kw = gsc_analyzer.fetch_top_keyword_12m(url)
        if main_kw:
            write_keyword(sheets_api, row_index, main_kw)
            info["main_keyword"] = main_kw
            logger.info("        + main_keyword découvert et écrit: '%s'", main_kw)

    if info["main_keyword"] and not info["secondary_keyword"]:
        candidates = gsc_analyzer.fetch_top_keywords_12m(url, limit=20)
        candidates = [c for c in candidates if c["query"].lower() != info["main_keyword"].lower()]
        secondary_kw = select_secondary_keyword(url, info["main_keyword"], candidates)
        if secondary_kw:
            write_secondary_keyword(sheets_api, row_index, secondary_kw)
            info["secondary_keyword"] = secondary_kw
            logger.info("        + secondary_keyword découvert et écrit: '%s'", secondary_kw)


def write_gsc_12m_metrics(sheets_api, spreadsheet_id: str, tab_name: str, row_index: int,
                          impressions_12m: int, clicks_12m: int) -> None:
    """Écrit impressions_12m (col D) et clicks_12m (col E) dans l'onglet ciblé."""
    sheets_api.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f"'{tab_name}'!D{row_index}:E{row_index}",
        valueInputOption="USER_ENTERED",
        body={"values": [[impressions_12m, clicks_12m]]},
    ).execute()



def main() -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(
        prog="python -m scripts.agent.prepare_batch",
        description="Prépare un lot d'URLs pour la génération (Phase 1).",
    )
    parser.add_argument("url_file", type=Path, help="Fichier texte, une URL par ligne")
    parser.add_argument("--site", "--blog", dest="site", default=DEFAULT_BLOG_ID,
                        help=f"Site slug (défaut: {DEFAULT_BLOG_ID})")
    parser.add_argument("--tab", default=None,
                        help='Onglet déclaré dans sheets.tabs, ex: "Medium Potential". '
                             "Défaut: premier onglet déclaré du site.")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT,
                        help=f"Nombre max d'URLs à préparer (défaut: {DEFAULT_LIMIT}, 0 = sans plafond)")
    args = parser.parse_args()

    site_slug = canonical_site_slug(args.site)
    try:
        layout = resolve_tab_layout(site_slug, args.tab)
    except ValueError as e:
        logger.error(str(e))
        return 2

    urls = load_url_list(args.url_file)
    if args.limit and args.limit > 0 and len(urls) > args.limit:
        logger.info("Lot plafonné à %d URLs (sur %d) — --limit 0 pour tout préparer",
                    args.limit, len(urls))
        urls = urls[:args.limit]
    logger.info("Lot: %d URLs depuis %s", len(urls), args.url_file)
    logger.info("Site: %s | Onglet: '%s' (statut col=%s, header_row=%s)",
                site_slug, layout["name"],
                layout["col_status"], layout["header_row"])

    spreadsheet_id = get_spreadsheet_id(site_slug) or os.environ["SPREADSHEET_ID_SUPERPROF"]
    orchestrator = RefreshOrchestrator(base_path=Path.cwd(), spreadsheet_id=spreadsheet_id)

    meta = read_tab_metadata(orchestrator.sheets_client, layout, {_norm(u) for u in urls})

    # GSC clients
    from scripts.audit.superprof_gsc_audit import _build_clients, audit_url
    from scripts.audit.gsc_analyzer import GSCAnalyzer

    sheets_api, gsc_api = _build_clients()
    gsc_analyzer = GSCAnalyzer(gsc_property=_gsc_property(site_slug))

    prepared, skipped, failed = [], [], []

    for i, url in enumerate(urls, start=1):
        n = _norm(url)
        info = meta.get(n)
        if info is None:
            logger.warning("[%2d/%d] ABSENT de '%s' — ignoré: %s", i, len(urls), layout["name"], url)
            skipped.append((url, "not_in_sheet"))
            continue
        if info["status"].lower() in SKIP_STATUSES:
            logger.info("[%2d/%d] SKIP (status=%s): %s", i, len(urls), info["status"], url)
            skipped.append((url, info["status"]))
            continue

        logger.info("[%2d/%d] %s", i, len(urls), url)
        try:
            # 0. Découverte + écriture auto des mots-clés manquants (GSC 12m)
            try:
                discover_and_write_keywords(gsc_analyzer, sheets_api, url, info["row_index"], info)
            except Exception as kw_err:  # noqa: BLE001
                logger.warning("        ⚠ découverte mots-clés échouée: %s", str(kw_err)[:120])

            # 1. post_content via WP REST API
            extraction = orchestrator._fetch_html(url, site_slug)
            html = extraction.get("clean_body") or ""
            method = extraction["extraction_metadata"].get("method_used", "?")
            if not html:
                logger.warning("        ✗ contenu vide (method=%s)", method)
                failed.append((url, f"empty_content_{method}"))
                continue
            if not method.startswith("wp_api"):
                logger.warning("        ⚠ méthode=%s (WP API attendue)", method)

            # 2. GSC audit (30j + 12m) → écriture directe dans New Growing List (D/E)
            try:
                audit = audit_url(gsc_api, info["row_index"], url, info["main_keyword"])
                metrics = {
                    "impressions_30d": audit.impressions_30d,
                    "clicks_30d": audit.clicks_30d,
                    "ctr_30d": audit.ctr_30d,
                }
                paa = " | ".join(q for q in [audit.top_query_1, audit.top_query_2, audit.top_query_3] if q)
                try:
                    write_gsc_12m_metrics(sheets_api, spreadsheet_id, layout["name"],
                                          info["row_index"], audit.impressions_12m, audit.clicks_12m)
                    logger.info(
                        "        + 12m écrit (D/E): impressions=%s clicks=%s",
                        audit.impressions_12m, audit.clicks_12m,
                    )
                except Exception as write_err:  # noqa: BLE001
                    logger.warning("        ⚠ écriture 12m (D/E) échouée: %s", str(write_err)[:120])
            except Exception as gsc_err:  # noqa: BLE001
                logger.warning("        ⚠ GSC/upsert échoué: %s", str(gsc_err)[:120])
                metrics = {"impressions_30d": 0, "clicks_30d": 0, "ctr_30d": 0.0}
                paa = ""

            # 3. Context bundle pour la Phase 2
            row = RefreshAuditRow(
                site_slug=site_slug,
                blogpost_url=url,
                main_keyword=info["main_keyword"],
                title="",
                post_type="",
                secondary_keywords=info["secondary_keyword"],
                people_also_ask=paa,
                impressions_30d=metrics["impressions_30d"],
                clicks_30d=metrics["clicks_30d"],
                ctr_30d=metrics["ctr_30d"],
            )
            ctx_dir = orchestrator._prepare_context_for_claude_code(
                original_html=html,
                action="FULL_REFRESH",
                row=row,
                extraction_result=extraction,
            )
            wc = extraction["extraction_metadata"].get("word_count", 0)
            logger.info(
                "        ✓ %s | %sw | imp30=%s | ctx=%s",
                method, wc, metrics["impressions_30d"], ctx_dir,
            )
            prepared.append(url)
        except Exception as exc:  # noqa: BLE001
            logger.exception("        ✗ échec: %s", str(exc)[:160])
            failed.append((url, str(exc)[:160]))

    logger.info("\n=== RÉSUMÉ ===")
    logger.info("Préparés : %d", len(prepared))
    logger.info("Ignorés  : %d  %s", len(skipped), [s[1] for s in skipped])
    logger.info("Échecs   : %d", len(failed))
    for u, e in failed:
        logger.info("  - %s :: %s", u, e)
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
