"""Tests du mode création (/new-blogpost) : `cw refresh --new` et `cw batch new-list`."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from cli.commands.batch import pending_new_rows
from cli.commands.refresh import MinimalRow, refresh


# --- batch new-list : lecture par en-tête, pas par index ------------------

HEADER = ["url", "company_name", "blog_category", "main_keyword", "volume",
          "blogpost_title", "blogpost_h1", "publish_date"]


def test_pending_new_rows_skips_published_and_urlless():
    rows = [
        HEADER,
        ["https://enseigna.fr/a-avis/", "A", "Soutien", "a avis", "200", "T-A", "H1-A", ""],
        ["https://enseigna.fr/b-avis/", "B", "Soutien", "b avis", "90", "T-B", "H1-B", "2026-05-21"],
        ["", "C", "Soutien", "c avis", "10", "T-C", "H1-C", ""],
        ["https://enseigna.fr/d-avis/", "D", "Langues", "d avis"],  # ligne courte
    ]
    out = pending_new_rows(rows)
    assert [r["url"] for r in out] == ["https://enseigna.fr/a-avis/", "https://enseigna.fr/d-avis/"]
    assert out[0] == {"row": 2, "url": "https://enseigna.fr/a-avis/", "main_keyword": "a avis",
                      "title": "T-A", "h1": "H1-A", "category": "Soutien", "company": "A",
                      "volume": "200"}
    assert out[1]["title"] == "" and out[1]["row"] == 5


def test_pending_new_rows_header_order_independent():
    rows = [
        ["publish_date", "blogpost_h1", "URL", "Main_Keyword"],
        ["", "H1", "https://x.fr/p/", "kw"],
    ]
    out = pending_new_rows(rows)
    assert out == [{"row": 2, "url": "https://x.fr/p/", "main_keyword": "kw", "title": "",
                    "h1": "H1", "category": "", "company": "", "volume": ""}]


def test_pending_new_rows_empty():
    assert pending_new_rows([]) == []
    assert pending_new_rows([HEADER]) == []


# --- refresh --new : garde-fous et contexte ------------------------------

def test_refresh_new_requires_keyword():
    res = CliRunner().invoke(refresh, ["https://enseigna.fr/x-avis/", "--site", "enseigna.fr", "--new"])
    assert res.exit_code != 0
    assert "--new requires --main-keyword" in res.output


def test_refresh_new_skips_fetch_and_forces_full_refresh(tmp_path: Path):
    """--new : aucun _fetch_html, FULL_REFRESH forcé, row.new_article propagé."""
    captured = {}

    class FakeResult:
        action_taken = "FULL_REFRESH"
        audit_score = 0
        errors = []
        main_keyword = "x avis"
        people_also_ask = ""
        secondary_keywords = ""
        serp = {}
        ytg_guide_id = ""
        ytg_semantic_field = []
        ytg_competitor_targets = {}
        ytg_term_colors = {}
        execution_time_seconds = 0.1

    class FakeOrchestrator:
        def __init__(self, **kw):
            self.ghostwriter = self

        def _fetch_html(self, *a, **k):
            raise AssertionError("--new must never fetch")

        def process_url(self, **kw):
            captured["process"] = kw
            return FakeResult()

        def _prepare_context_for_claude_code(self, original_html, action, row, extraction_result=None, ytg_data=None):
            captured["row"] = row
            captured["original_html"] = original_html
            captured["baseline"] = extraction_result["assets_baseline"]["counts"]
            d = tmp_path / "ctx"
            d.mkdir()
            return d

        def generate_from_context(self, **kw):
            return {"status": "error", "error": "stop here"}

    with patch("cli.commands.refresh.RefreshOrchestrator", FakeOrchestrator):
        res = CliRunner().invoke(refresh, [
            "https://enseigna.fr/x-avis/", "--site", "enseigna.fr",
            "--main-keyword", "x avis", "--title", "X avis : test", "--new",
            "--strategy", "TITLE_OPTIMIZATION",
        ])
    assert "NEW ARTICLE" in res.output
    assert captured["process"]["force_action"] == "FULL_REFRESH"
    assert captured["process"]["html_content"] == ""
    assert captured["process"]["provided_keyword"] == "x avis"
    row: MinimalRow = captured["row"]
    assert row.new_article is True
    assert row.title == "X avis : test"
    assert captured["original_html"] == ""
    assert captured["baseline"] == {"images": 0, "tables": 0, "videos": 0, "internal_links": 0}


def test_generation_prompt_header_new_article():
    from scripts.ghostwriter.ghostwriter import Ghostwriter

    gw = Ghostwriter.__new__(Ghostwriter)
    ctx = {
        "assets_to_preserve": {"counts": {}, "images": [], "internal_links": []},
        "instruction": "i",
        "original_content": {"title": ""},
        "audit_insights": {"main_keyword": "kw", "current_position": 0, "ctr": 0,
                           "recommendations": []},
        "semantic_field_terms": [],
    }
    prompt = Ghostwriter._build_generation_prompt(
        gw, composed_prompt="", rewrite_context=ctx, original_html="",
        audit_data={"new_article": True, "site_config": {}}, guidelines="", site_slug="enseigna.fr",
    )
    assert prompt.startswith("# TÂCHE: Création d'un nouvel article SEO")
    assert "aucun contenu original" in prompt
