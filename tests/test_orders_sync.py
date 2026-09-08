"""Tests du pont Sheet → Notion des commandes (scripts/notion/orders_sync.py).

Le pont existe pour supprimer une classe d'erreur précise : le copier-coller
manuel appariait les lignes par position, ce qui a décalé d'un cran une plage
entière de l'onglet « Medium Potential ». Les tests fixent donc surtout ce qui
distingue un décalage démontrable d'une reformulation à arbitrer.
"""

from scripts.notion.orders_sync import (
    KIND_ABSENT,
    KIND_MISSING,
    KIND_REWORDED,
    KIND_SHIFTED,
    build_plan,
    normalize_url,
)


def _sheet(*pairs):
    return [
        {"url": u, "keyword": k, "tab": "Medium Potential", "row": i}
        for i, (u, k) in enumerate(pairs, start=1)
    ]


def _notion(*pairs):
    return [
        {"url": u, "keyword": k, "type": "Refresh", "page_id": f"pg{i}"}
        for i, (u, k) in enumerate(pairs, start=1)
    ]


class TestNormalizeUrl:
    def test_strips_scheme_www_and_trailing_slash(self):
        assert normalize_url("https://www.superprof.fr/ressources/a.html") == \
            "superprof.fr/ressources/a.html"
        assert normalize_url("http://superprof.fr/x/") == "superprof.fr/x"

    def test_matching_is_case_insensitive(self):
        assert normalize_url("HTTPS://WWW.Superprof.FR/A") == normalize_url(
            "https://www.superprof.fr/a"
        )


class TestBuildPlan:
    def test_identical_keyword_produces_no_change(self):
        plan = build_plan(
            _sheet(("https://www.superprof.fr/a.html", "corrosion")),
            _notion(("https://www.superprof.fr/a.html", "corrosion")),
        )
        assert plan == []

    def test_whitespace_and_case_are_not_a_divergence(self):
        plan = build_plan(
            _sheet(("https://www.superprof.fr/a.html", "Main  Keyword")),
            _notion(("https://www.superprof.fr/a.html", "main keyword")),
        )
        assert plan == []

    def test_one_row_shift_is_flagged_as_shifted(self):
        """Le cas réel : chaque ligne Notion porte le mot-clé de la précédente."""
        sheet = _sheet(
            ("https://www.superprof.fr/thales.html", "théorème de thalès formule"),
            ("https://www.superprof.fr/corrosion.html", "corrosion"),
            ("https://www.superprof.fr/nombres.html", "diviseur de 84"),
        )
        notion = _notion(
            ("https://www.superprof.fr/corrosion.html", "théorème de thalès formule"),
            ("https://www.superprof.fr/nombres.html", "corrosion"),
        )
        plan = build_plan(sheet, notion)
        assert [p["kind"] for p in plan] == [KIND_SHIFTED, KIND_SHIFTED]
        assert plan[0]["sheet_keyword"] == "corrosion"
        assert plan[1]["sheet_keyword"] == "diviseur de 84"

    def test_reworded_keyword_is_not_confused_with_a_shift(self):
        """« adn » n'appartient à aucune autre ligne : arbitrage humain."""
        plan = build_plan(
            _sheet(("https://www.superprof.fr/cellule.html", "cellule svt")),
            _notion(("https://www.superprof.fr/cellule.html", "adn")),
        )
        assert [p["kind"] for p in plan] == [KIND_REWORDED]

    def test_empty_notion_keyword_is_missing_not_reworded(self):
        plan = build_plan(
            _sheet(("https://www.superprof.fr/a.html", "corrosion")),
            _notion(("https://www.superprof.fr/a.html", "")),
        )
        assert [p["kind"] for p in plan] == [KIND_MISSING]

    def test_url_absent_from_sheet_is_reported_not_silently_dropped(self):
        plan = build_plan(
            _sheet(("https://www.superprof.fr/a.html", "corrosion")),
            _notion(("https://www.superprof.fr/autre.html", "x")),
        )
        assert [p["kind"] for p in plan] == [KIND_ABSENT]

    def test_empty_sheet_keyword_never_overwrites_notion(self):
        """Une case vide côté Sheet ne doit pas effacer une valeur Notion."""
        plan = build_plan(
            _sheet(("https://www.superprof.fr/a.html", "")),
            _notion(("https://www.superprof.fr/a.html", "biomécanique")),
        )
        assert plan == []

    def test_matching_ignores_scheme_and_www_differences(self):
        plan = build_plan(
            _sheet(("https://www.superprof.fr/a.html", "corrosion")),
            _notion(("http://superprof.fr/a.html/", "corrosion")),
        )
        assert plan == []
