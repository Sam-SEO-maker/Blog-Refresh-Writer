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


# ---------------------------------------------------------------------------
# Création de commandes (Sheet → Notion)
# ---------------------------------------------------------------------------
#
# Le copier-coller manuel de dix URLs les fait arriver dans un ordre arbitraire
# côté Notion, et rien ne dit à la PO lesquelles étaient déjà commandées. Les
# tests fixent donc les deux propriétés qui rendent la commande utile : l'ordre
# de la Sheet est celui du lot, et une URL déjà présente ne redonne jamais lieu
# à une création.

from scripts.notion.orders_sync import (  # noqa: E402
    KIND_CREATE,
    KIND_EXISTS,
    build_create_plan,
    build_order_properties,
)


ORDERS_CFG = {
    "col_url": "Local resource URL",
    "col_keyword": "Main KW",
    "col_type": "Type of article",
    "type_value": "Refresh",
    "country_page_id": "4d06ca37-4111-4b09-81d9-b6d55697bef8",
}


class TestBuildCreatePlan:
    def test_orders_the_urls_absent_from_notion(self):
        plan = build_create_plan(
            _sheet(("https://www.superprof.fr/a.html", "kw a")),
            _notion(),
        )
        assert [p["kind"] for p in plan] == [KIND_CREATE]
        assert plan[0]["keyword"] == "kw a"

    def test_an_already_ordered_url_is_never_recreated(self):
        plan = build_create_plan(
            _sheet(("https://www.superprof.fr/a.html", "kw a")),
            _notion(("http://superprof.fr/a.html/", "kw notion")),
        )
        assert [p["kind"] for p in plan] == [KIND_EXISTS]
        # L'écart de mot-clé est rapporté, pas corrigé en douce : c'est le
        # travail de push-keywords, et un doublon serait pire que l'écart.
        assert plan[0]["notion_keyword"] == "kw notion"
        assert plan[0]["page_id"] == "pg1"

    def test_the_plan_follows_the_sheet_row_order(self):
        # Le défaut central du copier-coller : dix URLs collées d'un bloc
        # arrivent en désordre. Le plan doit restituer l'ordre de la Sheet,
        # quel que soit l'ordre de lecture de l'onglet.
        shuffled = [
            {"url": "https://www.superprof.fr/c.html", "keyword": "kw c", "row": 30},
            {"url": "https://www.superprof.fr/a.html", "keyword": "kw a", "row": 10},
            {"url": "https://www.superprof.fr/b.html", "keyword": "kw b", "row": 20},
        ]
        plan = build_create_plan(shuffled, _notion())
        assert [p["row"] for p in plan] == [10, 20, 30]

    def test_a_url_repeated_in_the_sheet_is_ordered_once(self):
        plan = build_create_plan(
            _sheet(
                ("https://www.superprof.fr/a.html", "kw a"),
                ("https://www.superprof.fr/a.html/", "kw a bis"),
            ),
            _notion(),
        )
        assert len(plan) == 1
        assert plan[0]["keyword"] == "kw a"

    def test_a_row_without_url_is_skipped(self):
        plan = build_create_plan([{"url": "", "keyword": "kw", "row": 2}], _notion())
        assert plan == []


class TestBuildOrderProperties:
    def test_type_of_article_is_a_multi_select(self):
        # Le schéma de la base déclare « Type of article » en multi_select :
        # une valeur scalaire y est rejetée par l'API, et la ligne créée
        # n'apparaîtrait dans aucune vue filtrée sur Refresh.
        props = build_order_properties(ORDERS_CFG, "https://x.fr/a.html", "kw")
        assert props["Type of article"] == {"multi_select": [{"name": "Refresh"}]}

    def test_the_country_relation_is_set(self):
        props = build_order_properties(ORDERS_CFG, "https://x.fr/a.html", "kw")
        assert props["Country"] == {
            "relation": [{"id": "4d06ca37-4111-4b09-81d9-b6d55697bef8"}]
        }

    def test_url_and_keyword_land_in_their_own_column_types(self):
        props = build_order_properties(ORDERS_CFG, "https://x.fr/a.html", "kw")
        assert props["Local resource URL"] == {"url": "https://x.fr/a.html"}
        assert props["Main KW"]["rich_text"][0]["text"]["content"] == "kw"

    def test_an_empty_keyword_writes_no_keyword_column(self):
        props = build_order_properties(ORDERS_CFG, "https://x.fr/a.html", "")
        assert "Main KW" not in props

    def test_no_other_column_is_ever_written(self):
        # Writer, Deadline, Price, Status et Month sont la main de la PO.
        props = build_order_properties(ORDERS_CFG, "https://x.fr/a.html", "kw")
        assert set(props) == {
            "Local resource URL", "Main KW", "Type of article", "Country",
        }


class TestApplyCreatePlan:
    """L'écriture elle-même : ordre, espacement, tolérance aux échecs."""

    def _run(self, monkeypatch, plan, results=None, spacing=0.0):
        import scripts.notion as notion_pkg
        import scripts.notion.orders_sync as mod

        calls: list[dict] = []
        outcomes = list(results or [])

        class FakeClient:
            def create_page(self, database_id, properties):
                calls.append(properties)
                return outcomes.pop(0) if outcomes else {"id": "new"}

        # `apply_create_plan` importe NotionClient depuis le package.
        monkeypatch.setattr(notion_pkg, "NotionClient", FakeClient)
        monkeypatch.setattr(
            mod, "get_orders_config", lambda site: dict(ORDERS_CFG,
                                                        database_id="db")
        )
        created, failed, failures = mod.apply_create_plan(
            "site", plan, order_spacing_seconds=spacing
        )
        return calls, created, failed, failures

    def _plan(self, *urls):
        return [
            {"url": u, "keyword": f"kw{i}", "row": i, "kind": KIND_CREATE}
            for i, u in enumerate(urls, start=1)
        ]

    def test_creates_in_plan_order(self, monkeypatch):
        calls, created, failed, _ = self._run(
            monkeypatch, self._plan("https://x.fr/a", "https://x.fr/b", "https://x.fr/c")
        )
        assert [c["Local resource URL"]["url"] for c in calls] == [
            "https://x.fr/a", "https://x.fr/b", "https://x.fr/c"
        ]
        assert (created, failed) == (3, 0)

    def test_rows_already_ordered_are_not_created(self, monkeypatch):
        plan = self._plan("https://x.fr/a")
        plan.append({"url": "https://x.fr/b", "keyword": "kw", "row": 2,
                     "kind": KIND_EXISTS})
        calls, created, _, _ = self._run(monkeypatch, plan)
        assert len(calls) == 1
        assert created == 1

    def test_a_failure_does_not_stop_the_batch(self, monkeypatch):
        # Un lot à moitié écrit qu'il faut relancer en entier est pire qu'un
        # échec isolé rapporté : les lignes déjà créées seraient dédoublées.
        calls, created, failed, failures = self._run(
            monkeypatch,
            self._plan("https://x.fr/a", "https://x.fr/b", "https://x.fr/c"),
            results=[{"id": "1"}, None, {"id": "3"}],
        )
        assert len(calls) == 3
        assert (created, failed) == (2, 1)
        assert failures[0]["url"] == "https://x.fr/b"

    def test_creations_are_spaced_so_created_time_can_order_them(self, monkeypatch):
        # Vérifié contre la vraie base : trois lignes créées dans la même
        # seconde portent la même createdTime et ressortent en 2, 3, 1.
        import scripts.notion.orders_sync as mod

        slept: list[float] = []
        monkeypatch.setattr(mod.time, "sleep", lambda s: slept.append(s))
        self._run(
            monkeypatch,
            self._plan("https://x.fr/a", "https://x.fr/b", "https://x.fr/c"),
            spacing=1.1,
        )
        # Un espacement entre chaque ligne, aucun avant la première.
        assert slept == [1.1, 1.1]
        assert mod.ORDER_SPACING_SECONDS >= 1.0

    def test_a_single_order_is_never_delayed(self, monkeypatch):
        import scripts.notion.orders_sync as mod

        slept: list[float] = []
        monkeypatch.setattr(mod.time, "sleep", lambda s: slept.append(s))
        self._run(monkeypatch, self._plan("https://x.fr/a"), spacing=1.1)
        assert slept == []
