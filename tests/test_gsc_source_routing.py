"""Routage source GSC : MCP `gsc-remote` (superprof.*) vs service account (Phase 6c).

Garantie critique verrouillée ici : une propriété NON couverte par le MCP
(enseigna.fr, tout client hors superprof) est TOUJOURS routée vers le service
account — jamais vers le MCP. Voir scripts/audit/GSC_MCP_POC_FINDINGS.md.
"""

import pytest

from scripts.audit.gsc_analyzer import (
    GSCAnalyzer,
    gsc_source_for_property,
    SOURCE_MCP,
    SOURCE_SERVICE_ACCOUNT,
)


@pytest.mark.parametrize("prop,expected", [
    ("https://www.superprof.fr/ressources/", SOURCE_MCP),
    ("https://www.superprof.fr/blog/", SOURCE_MCP),
    ("https://www.superprof.es/apuntes/", SOURCE_MCP),
    ("https://www.superprof.co.uk/resources/", SOURCE_MCP),
    ("https://www.super-prof.nl/", SOURCE_MCP),
    # Non couverts par le MCP → service account
    ("https://enseigna.fr/", SOURCE_SERVICE_ACCOUNT),
    ("https://someclient.com/", SOURCE_SERVICE_ACCOUNT),
    ("", SOURCE_SERVICE_ACCOUNT),
])
def test_source_routing(prop, expected):
    assert gsc_source_for_property(prop) == expected


def test_enseigna_always_service_account():
    """Garantie dure : enseigna ne doit JAMAIS être routé vers le MCP."""
    analyzer = GSCAnalyzer(gsc_property="https://enseigna.fr/")
    assert analyzer.data_source == SOURCE_SERVICE_ACCOUNT
    assert analyzer.uses_mcp is False


def test_superprof_routed_to_mcp():
    analyzer = GSCAnalyzer(gsc_property="https://www.superprof.fr/ressources/")
    assert analyzer.data_source == SOURCE_MCP
    assert analyzer.uses_mcp is True


def test_unknown_property_falls_back_to_service_account():
    """Fail-safe : propriété inconnue/vide → SA, jamais MCP."""
    for prop in ("", None, "https://random-domain.example/"):
        assert gsc_source_for_property(prop) == SOURCE_SERVICE_ACCOUNT


# --- Bascule fetch 12m : routage MCP + fallback SA (Phase 6c) ----------------

from unittest import mock

from scripts.audit import gsc_mcp_client


_FAKE_ROWS = [
    {"query": "kw a", "clicks": 100, "impressions": 1000, "ctr": 10.0, "position": 2.0},
    {"query": "kw b", "clicks": 50, "impressions": 800, "ctr": 6.2, "position": 3.1},
]


def _analyzer_no_sa(prop):
    """GSCAnalyzer sans service account initialisé (isole le routage MCP/SA)."""
    a = GSCAnalyzer(gsc_property=prop)
    a._gsc_service = None  # neutralise la voie SA pour observer le routage
    return a


def test_superprof_12m_uses_mcp():
    a = _analyzer_no_sa("https://www.superprof.fr/ressources/")
    with mock.patch.object(gsc_mcp_client.GSCMCPClient, "search_by_page_query",
                           return_value=list(_FAKE_ROWS)) as m:
        rows = a.fetch_top_keywords_12m("https://www.superprof.fr/ressources/x/", limit=20)
    m.assert_called_once()
    assert [r["query"] for r in rows] == ["kw a", "kw b"]


def test_mcp_error_falls_back_to_sa():
    a = _analyzer_no_sa("https://www.superprof.fr/ressources/")
    with mock.patch.object(gsc_mcp_client.GSCMCPClient, "search_by_page_query",
                           side_effect=gsc_mcp_client.GSCMCPError("down")), \
         mock.patch.object(GSCAnalyzer, "_fetch_top_keywords_12m_via_sa",
                           return_value=[{"query": "sa", "clicks": 1, "impressions": 2}]) as sa:
        rows = a.fetch_top_keywords_12m("https://www.superprof.fr/ressources/x/", limit=20)
    sa.assert_called_once()
    assert rows == [{"query": "sa", "clicks": 1, "impressions": 2}]


def test_limit_over_20_bypasses_mcp():
    """Garde row-limit : limit>20 ne doit jamais passer par le MCP (troncature)."""
    a = _analyzer_no_sa("https://www.superprof.fr/ressources/")
    with mock.patch.object(GSCAnalyzer, "_fetch_top_keywords_12m_via_mcp",
                           side_effect=AssertionError("MCP interdit pour limit>20")), \
         mock.patch.object(GSCAnalyzer, "_fetch_top_keywords_12m_via_sa",
                           return_value=[]) as sa:
        a.fetch_top_keywords_12m("https://www.superprof.fr/ressources/x/", limit=50)
    sa.assert_called_once()


def test_enseigna_12m_never_calls_mcp():
    a = _analyzer_no_sa("https://enseigna.fr/")
    with mock.patch.object(GSCAnalyzer, "_fetch_top_keywords_12m_via_mcp",
                           side_effect=AssertionError("enseigna ne doit jamais toucher le MCP")), \
         mock.patch.object(GSCAnalyzer, "_fetch_top_keywords_12m_via_sa",
                           return_value=[]) as sa:
        a.fetch_top_keywords_12m("https://enseigna.fr/page/", limit=20)
    sa.assert_called_once()


def test_main_keyword_uses_mcp_for_superprof():
    a = _analyzer_no_sa("https://www.superprof.fr/ressources/")
    rows = [
        {"query": "petit", "clicks": 5, "impressions": 10, "ctr": 50.0, "position": 1.0},
        {"query": "gros", "clicks": 3, "impressions": 999, "ctr": 0.3, "position": 5.0},
    ]
    with mock.patch("scripts.audit.gsc_mcp_client.GSCMCPClient.search_by_page_query",
                    return_value=rows) as m:
        kw = a.fetch_main_keyword("https://www.superprof.fr/ressources/x/")
    m.assert_called_once()
    assert kw == "gros"  # max impressions


def test_main_keyword_falls_back_to_sa():
    a = _analyzer_no_sa("https://www.superprof.fr/ressources/")
    with mock.patch("scripts.audit.gsc_mcp_client.GSCMCPClient.search_by_page_query",
                    side_effect=gsc_mcp_client.GSCMCPError("down")), \
         mock.patch.object(GSCAnalyzer, "_fetch_current_period_rows_via_sa",
                           return_value=[{"query": "sa-kw", "clicks": 1, "impressions": 9,
                                          "ctr": 1.0, "position": 2.0}]):
        kw = a.fetch_main_keyword("https://www.superprof.fr/ressources/x/")
    assert kw == "sa-kw"


def test_main_keyword_enseigna_never_mcp():
    a = _analyzer_no_sa("https://enseigna.fr/")
    with mock.patch("scripts.audit.gsc_mcp_client.GSCMCPClient.search_by_page_query",
                    side_effect=AssertionError("enseigna interdit MCP")), \
         mock.patch.object(GSCAnalyzer, "_fetch_current_period_rows_via_sa",
                           return_value=[{"query": "e", "clicks": 1, "impressions": 2,
                                          "ctr": 1.0, "position": 1.0}]) as sa:
        kw = a.fetch_main_keyword("https://enseigna.fr/p/")
    sa.assert_called_once()
    assert kw == "e"


def test_perf_current_period_stays_on_sa():
    """Perf 30j (sommes → décision) NON basculée MCP : row-limit tronquerait.

    `_fetch_current_period_rows` doit passer par le SA même pour superprof, car
    la somme sur toutes les requêtes est faussée par le plafond ~20 du MCP.
    """
    a = _analyzer_no_sa("https://www.superprof.fr/ressources/")
    with mock.patch("scripts.audit.gsc_mcp_client.GSCMCPClient.search_by_page_query",
                    side_effect=AssertionError("perf ne doit PAS passer par le MCP")), \
         mock.patch.object(GSCAnalyzer, "_fetch_current_period_rows_via_sa",
                           return_value=[]) as sa:
        a._fetch_current_period_rows("https://www.superprof.fr/ressources/x/")
    sa.assert_called_once()


def test_perf_aggregation_from_rows():
    """Agrégation période courante : totaux, ctr, position pondérée, main_keyword."""
    a = _analyzer_no_sa("https://enseigna.fr/")  # SA path, mais on stub les rows
    rows = [
        {"query": "a", "clicks": 100, "impressions": 1000, "ctr": 10.0, "position": 2.0},
        {"query": "b", "clicks": 50, "impressions": 3000, "ctr": 1.67, "position": 8.0},
    ]
    with mock.patch.object(GSCAnalyzer, "_fetch_current_period_rows", return_value=rows), \
         mock.patch.object(GSCAnalyzer, "_calculate_trends_direct", return_value=(0.0, 0.0, 0.0)):
        perf = a._fetch_performance_direct("https://enseigna.fr/x/")
    assert perf.clicks_30d == 150
    assert perf.impressions_30d == 4000
    # main keyword = plus d'impressions
    assert perf.main_keyword == "b"
    # position pondérée par impressions : (2*1000 + 8*3000)/4000 = 6.5
    assert round(perf.avg_position_30d, 2) == 6.5


def test_perf_returns_empty_when_no_source():
    a = _analyzer_no_sa("https://enseigna.fr/")
    with mock.patch.object(GSCAnalyzer, "_fetch_current_period_rows", return_value=None):
        perf = a._fetch_performance_direct("https://enseigna.fr/x/")
    assert perf.clicks_30d == 0 and perf.impressions_30d == 0


def test_parse_query_table_ignores_total_and_headers():
    text = (
        "Search queries for page X (last 30 days):\n"
        "--------------------------------------------------------\n"
        "Query | Clicks | Impressions | CTR | Position\n"
        "--------------------------------------------------------\n"
        "roi de france | 967 | 4343 | 22.27% | 2.9\n"
        "chronologie 2024 | 12 | 117 | 10.26% | 3.2\n"
        "--------------------------------------------------------\n"
        "TOTAL | 979 | 4460 | 21.95% | -\n"
    )
    rows = gsc_mcp_client.parse_query_table(text)
    assert [r["query"] for r in rows] == ["roi de france", "chronologie 2024"]
    assert rows[0] == {"query": "roi de france", "clicks": 967,
                       "impressions": 4343, "ctr": 22.27, "position": 2.9}
    # requête contenant un chiffre correctement parsée
    assert rows[1]["query"] == "chronologie 2024" and rows[1]["clicks"] == 12


def test_parse_query_table_preserves_accents():
    """Les accents FR doivent être préservés (cf. bug latin-1 du stream SSE)."""
    text = (
        "Query | Clicks | Impressions | CTR | Position\n"
        "formule maths 3ème | 12 | 100 | 12.00% | 3.0\n"
        "mathématiques élémentaires | 5 | 50 | 10.00% | 4.0\n"
    )
    rows = gsc_mcp_client.parse_query_table(text)
    assert rows[0]["query"] == "formule maths 3ème"
    assert rows[1]["query"] == "mathématiques élémentaires"
