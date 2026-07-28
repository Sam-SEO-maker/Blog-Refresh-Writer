"""Idempotence de la conversion Gutenberg.

Bug couvert (constaté en production le 2026-07-28, article « design d'objet ») :
`to_gutenberg()` appliqué à un HTML **déjà converti** détruisait ses blocs. Les
délimiteurs `<!-- wp: -->` sont des commentaires HTML, exposés par BeautifulSoup
en nœuds `Comment` — une sous-classe de `NavigableString`. La branche « texte
nu » les capturait donc et réemballait chaque délimiteur en paragraphe visible.

Un simple paragraphe ressortait en trois blocs, dont deux affichant
littéralement « wp:paragraph » sur la page publiée. Sur l'article réel, cela
produisait 137 paragraphes parasites et faisait gonfler le fichier de 59 Ko à
94 Ko à chaque relance de `cw finalize` — la cause racine de sa non-idempotence.
"""

import pytest

from scripts.utils.gutenberg_formatter import is_already_gutenberg, to_gutenberg


PARASITE_MARKERS = ("<p>wp:", "<p>/wp:")


def count_parasites(html: str) -> int:
    return sum(html.count(m) for m in PARASITE_MARKERS)


class TestIsAlreadyGutenberg:

    def test_detects_block_delimiters(self):
        assert is_already_gutenberg("<!-- wp:paragraph -->\n<p>x</p>\n<!-- /wp:paragraph -->")

    def test_detects_namespaced_blocks(self):
        assert is_already_gutenberg('<!-- wp:advgb/infobox {"id":"x"} -->')

    def test_plain_html_is_not_gutenberg(self):
        assert not is_already_gutenberg("<h2>Titre</h2><p>Texte</p>")

    @pytest.mark.parametrize("html", ["", None])
    def test_empty_inputs(self, html):
        assert not is_already_gutenberg(html)


class TestToGutenbergIdempotency:

    def test_already_converted_is_returned_unchanged(self):
        src = "<!-- wp:paragraph -->\n<p>Bonjour</p>\n<!-- /wp:paragraph -->"
        assert to_gutenberg(src) == src

    def test_no_parasitic_paragraphs_on_reconversion(self):
        """Le symptôme visible du bug : « wp:paragraph » affiché en clair."""
        src = "<!-- wp:paragraph -->\n<p>Bonjour</p>\n<!-- /wp:paragraph -->"
        assert count_parasites(to_gutenberg(src)) == 0

    def test_conversion_is_stable_across_repeated_calls(self):
        raw = "<h2>Titre</h2><p>Texte simple</p>"
        once = to_gutenberg(raw)
        assert to_gutenberg(once) == once
        assert to_gutenberg(to_gutenberg(once)) == once

    def test_file_does_not_grow_on_reconversion(self):
        """Sur l'article réel, le fichier passait de 59 Ko à 94 Ko."""
        raw = "<h2>Titre</h2><p>Un paragraphe.</p><h3>Sous-titre</h3><p>Un autre.</p>"
        once = to_gutenberg(raw)
        assert len(to_gutenberg(once)) == len(once)

    def test_plain_html_still_converts(self):
        """La garde ne doit pas empêcher la conversion normale."""
        out = to_gutenberg("<h2>Titre</h2><p>Texte</p>")
        assert "<!-- wp:" in out
        assert count_parasites(out) == 0

    def test_block_count_preserved(self):
        raw = "<p>Un</p><p>Deux</p><p>Trois</p>"
        once = to_gutenberg(raw)
        assert once.count("<!-- wp:paragraph -->") == 3
        assert to_gutenberg(once).count("<!-- wp:paragraph -->") == 3
