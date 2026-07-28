"""Découpage des listes PAA / secondary_keywords sérialisées.

Bug couvert (constaté en production le 2026-07-28) : `_split_terms` ne gérait
que le séparateur historique ` | `, alors que l'orchestrateur sérialise les PAA
avec `", ".join(paa[:5])`. Les 4 questions d'une PAA comptaient donc pour **une
seule** : `plan init` affichait « 1 PAA injected », et surtout `plan check`
validait la couverture éditoriale contre une chaîne unique — le contrôle ne
vérifiait rien.
"""

import pytest

from scripts.audit.plan_validator import _split_terms


class TestSplitTerms:

    def test_pipe_format_still_works(self):
        """Le format historique ne doit pas régresser."""
        assert _split_terms("a | b | c") == ["a", "b", "c"]

    def test_comma_format_is_split(self):
        """Le format réellement écrit par l'orchestrateur."""
        raw = (
            "C'est quoi le design d'objet ?, "
            "Quels sont les 3 types de design ?, "
            "Qu'est-ce qu'un designer d'objet ?, "
            "Quels sont les 4 domaines de design ?"
        )
        terms = _split_terms(raw)
        assert len(terms) == 4
        assert terms[0] == "C'est quoi le design d'objet ?"
        assert terms[-1] == "Quels sont les 4 domaines de design ?"

    def test_pipe_wins_over_comma(self):
        """Une PAA peut contenir une virgule interne : le pipe reste prioritaire."""
        raw = "Combien ça coûte, vraiment ? | Quel diplôme ?"
        assert _split_terms(raw) == ["Combien ça coûte, vraiment ?", "Quel diplôme ?"]

    @pytest.mark.parametrize("raw", ["", "   ", None])
    def test_empty_inputs(self, raw):
        assert _split_terms(raw or "") == []

    def test_single_term_without_separator(self):
        assert _split_terms("une seule question ?") == ["une seule question ?"]

    def test_blank_fragments_are_dropped(self):
        assert _split_terms("a,, b,") == ["a", "b"]
