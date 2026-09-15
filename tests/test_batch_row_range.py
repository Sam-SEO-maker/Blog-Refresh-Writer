"""Tests de `--rows` : restreindre un lot à une plage de lignes Sheet.

Enjeu couvert ici : la plage porte les numéros de ligne AFFICHÉS par Google
Sheets (en-têtes comprises), qui sont le seul repère que l'opérateur a sous les
yeux. Une conversion en index de liste, ou un filtre posé après `--limit`,
sélectionnerait d'autres URLs que celles demandées — et rien dans le rapport de
lot ne permettrait de s'en apercevoir.
"""

from dataclasses import dataclass

import pytest

from scripts.agent import RefreshOrchestrator


@dataclass
class _Row:
    row_index: int = 0
    post_type: str = ""
    blogpost_url: str = ""


class _FakeOrchestrator:
    """Expose `_rows_for_batch` sur un jeu de lignes fixe (pas de Sheet, pas de GSC)."""

    parse_row_range = staticmethod(RefreshOrchestrator.parse_row_range)
    _rows_for_batch = RefreshOrchestrator._rows_for_batch

    def __init__(self, rows):
        self._rows = rows

    def _tab_rows_for_refresh(self, site_slug, tab):
        return list(self._rows)

    def _validate_keywords_for_rows(self, rows):
        # La validation GSC est hors sujet ici : elle coûte un appel par ligne.
        return rows


class _Logger:
    def info(self, *a, **k):
        pass

    def error(self, *a, **k):
        pass


def _select(rows, rows_spec=None, limit=None):
    o = _FakeOrchestrator(rows)
    return o._rows_for_batch("FULL_REFRESH", "superprof.fr-ressources", "Medium Potential",
                             None, limit, _Logger(), rows_spec)


class TestParseRowRange:
    @pytest.mark.parametrize("spec,expected", [
        ("140-180", (140, 180)),
        ("140:180", (140, 180)),
        ("140", (140, 140)),
        ("  140 - 180  ", (140, 180)),
    ])
    def test_accepted_forms(self, spec, expected):
        assert RefreshOrchestrator.parse_row_range(spec) == expected

    @pytest.mark.parametrize("spec", ["", "   ", "abc", "140-", "1-2-3-x", "0-10", "180-140"])
    def test_rejected_forms_raise(self, spec):
        """Une plage inexploitable lève, jamais un silence qui traiterait autre chose."""
        with pytest.raises(ValueError):
            RefreshOrchestrator.parse_row_range(spec)


class TestRowRangeSelection:
    def test_bounds_are_sheet_row_numbers_and_inclusive(self):
        rows = [_Row(row_index=i) for i in range(1, 21)]
        got = [r.row_index for r in _select(rows, "5-8")]
        assert got == [5, 6, 7, 8]

    def test_range_keeps_only_rows_present_in_the_tab(self):
        """La plage sélectionne, elle ne ressuscite pas une ligne écartée par le statut."""
        rows = [_Row(row_index=i) for i in (5, 7, 9)]  # 6 et 8 non « à faire »
        assert [r.row_index for r in _select(rows, "5-9")] == [5, 7, 9]

    def test_single_row(self):
        rows = [_Row(row_index=i) for i in range(1, 11)]
        assert [r.row_index for r in _select(rows, "7")] == [7]

    def test_empty_range_is_not_an_error(self):
        rows = [_Row(row_index=i) for i in range(1, 11)]
        assert _select(rows, "50-60") == []

    def test_limit_counts_within_the_range_not_before_it(self):
        """`--rows` filtre AVANT `--limit`.

        Dans l'ordre inverse, `--limit 3` aurait d'abord retenu les lignes 1-3
        puis la plage 10-20 n'en aurait gardé aucune : un lot vide indiscernable
        d'une plage réellement vide.
        """
        rows = [_Row(row_index=i) for i in range(1, 31)]
        got = [r.row_index for r in _select(rows, "10-20", limit=3)]
        assert got == [10, 11, 12]

    def test_no_range_leaves_selection_untouched(self):
        rows = [_Row(row_index=i) for i in range(1, 6)]
        assert [r.row_index for r in _select(rows)] == [1, 2, 3, 4, 5]

    def test_rows_without_row_index_are_refused(self):
        """Le flux enseigna ne porte pas de row_index : filtrer y renverrait 0 en silence."""
        rows = [_Row(row_index=0), _Row(row_index=0)]
        with pytest.raises(ValueError, match="--rows requiert --tab"):
            _select(rows, "1-10")
