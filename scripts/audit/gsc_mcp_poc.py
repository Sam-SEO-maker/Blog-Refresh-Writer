"""PoC comparatif GSC : API directe (service account) vs MCP `gsc-remote`.

Phase 6c — première étape de la migration GSC SA → MCP (bascule progressive,
jamais big-bang). Ce module fournit UNIQUEMENT l'outillage de comparaison :
il exécute la même requête « 30 jours par requête pour une URL » via l'API
directe et affiche le résultat sous une forme normalisée, comparable à la sortie
du tool MCP `gsc-remote get_search_by_page_query`.

Le côté MCP n'est pas appelé depuis Python (les tools MCP sont invoqués par
Claude Code, pas par le process CLI). Le workflow PoC est donc :

  1. Claude appelle `mcp__gsc-remote__get_search_by_page_query(site, page, 30)`.
  2. Claude lance `python -m scripts.audit.gsc_mcp_poc <property> <page_url>` pour
     l'équivalent API directe.
  3. `compare_rows()` (ou l'œil humain) confronte les deux jeux de lignes.

Aucune modification du pipeline de décision : cet outil est hors chemin critique.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from typing import Optional

from dotenv import load_dotenv

from scripts.audit.gsc_analyzer import GSCAnalyzer


def fetch_direct_by_query(gsc_property: str, page_url: str, days: int = 30) -> list[dict]:
    """Requête API directe : lignes {query, clicks, impressions, ctr, position}.

    Réplique exactement le corps de requête utilisé par `GSCAnalyzer`
    (`_fetch_performance_direct`) pour que la comparaison porte sur la donnée,
    pas sur une divergence de paramétrage.
    """
    analyzer = GSCAnalyzer(gsc_property=gsc_property)
    if analyzer._gsc_service is None:
        raise RuntimeError("Service GSC non initialisé (credentials SA absents ?).")

    today = datetime.now()
    body = {
        "startDate": (today - timedelta(days=days)).strftime("%Y-%m-%d"),
        "endDate": today.strftime("%Y-%m-%d"),
        "dimensions": ["query"],
        "dimensionFilterGroups": [{
            "filters": [{"dimension": "page", "expression": page_url}]
        }],
        "rowLimit": 50,
    }
    resp = analyzer._gsc_service.searchanalytics().query(
        siteUrl=gsc_property, body=body
    ).execute()

    rows = []
    for r in resp.get("rows", []):
        rows.append({
            "query": r["keys"][0],
            "clicks": int(r.get("clicks", 0)),
            "impressions": int(r.get("impressions", 0)),
            "ctr": round(r.get("ctr", 0) * 100, 2),
            "position": round(r.get("position", 0), 1),
        })
    rows.sort(key=lambda x: (-x["clicks"], -x["impressions"]))
    return rows


def compare_rows(direct: list[dict], mcp: list[dict], top: int = 20) -> dict:
    """Compare deux jeux de lignes (direct vs MCP) sur les métriques clés.

    Retourne un dict de synthèse : totaux, top keyword de part et d'autre,
    et écarts par requête (clics/impressions) pour les `top` premières.
    """
    def _totals(rows):
        return {
            "clicks": sum(r["clicks"] for r in rows),
            "impressions": sum(r["impressions"] for r in rows),
            "n_queries": len(rows),
        }

    d_by_q = {r["query"]: r for r in direct}
    m_by_q = {r["query"]: r for r in mcp}
    all_q = list(dict.fromkeys([r["query"] for r in direct] + [r["query"] for r in mcp]))

    deltas = []
    for q in all_q[:top]:
        d = d_by_q.get(q)
        m = m_by_q.get(q)
        deltas.append({
            "query": q,
            "in_direct": d is not None,
            "in_mcp": m is not None,
            "clicks_direct": d["clicks"] if d else None,
            "clicks_mcp": m["clicks"] if m else None,
            "impr_direct": d["impressions"] if d else None,
            "impr_mcp": m["impressions"] if m else None,
        })

    return {
        "totals_direct": _totals(direct),
        "totals_mcp": _totals(mcp),
        "top_kw_direct": direct[0]["query"] if direct else None,
        "top_kw_mcp": mcp[0]["query"] if mcp else None,
        "deltas": deltas,
    }


def main() -> int:
    load_dotenv()
    if len(sys.argv) < 3:
        print("Usage: python -m scripts.audit.gsc_mcp_poc <gsc_property> <page_url> [days]")
        return 2
    gsc_property = sys.argv[1]
    page_url = sys.argv[2]
    days = int(sys.argv[3]) if len(sys.argv) > 3 else 30

    rows = fetch_direct_by_query(gsc_property, page_url, days)
    out = {
        "source": "api_direct",
        "gsc_property": gsc_property,
        "page_url": page_url,
        "days": days,
        "totals": {
            "clicks": sum(r["clicks"] for r in rows),
            "impressions": sum(r["impressions"] for r in rows),
            "n_queries": len(rows),
        },
        "top_keyword": rows[0]["query"] if rows else None,
        "rows": rows,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
