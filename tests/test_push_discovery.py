"""Tests de la découverte de fichiers de `cw push`.

Publier le mauvais fichier est indétectable une fois l'article en ligne : les
dossiers de sortie accumulent les passes successives, et un appariement trop
permissif rapproche des articles distincts. Ces tests verrouillent le refus
d'ambiguïté, qui est le comportement voulu — pas un défaut d'ergonomie.
"""

import json

import pytest

from cli.commands.push import _discover_gutenberg, _discover_metadata, _read_qc_verdict


@pytest.fixture
def site_outputs(tmp_path):
    """Layout monorepo minimal : sites/<slug>/outputs/{html,metadata}/."""
    out = tmp_path / "sites" / "test.fr" / "outputs"
    (out / "html").mkdir(parents=True)
    (out / "metadata").mkdir(parents=True)
    return tmp_path, out


def _write(path, name, content="<!-- wp:paragraph --><p>x</p>"):
    f = path / name
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(content, encoding="utf-8")
    return f


class TestDiscoverGutenberg:
    def test_finds_unique_match(self, site_outputs):
        base, out = site_outputs
        expected = _write(out / "html", "mon-article_refreshed.gutenberg.html")
        found = _discover_gutenberg(base, "test.fr",
                                    "https://test.fr/mon-article/", None)
        assert found == expected

    def test_matches_superprof_html_suffix(self, site_outputs):
        """Permaliens Superprof en .html : le suffixe ne doit pas gêner."""
        base, out = site_outputs
        expected = _write(out / "html", "cours-python.html_refreshed.gutenberg.html")
        found = _discover_gutenberg(base, "test.fr",
                                    "https://test.fr/res/cours-python.html", None)
        assert found == expected

    def test_narrows_by_article_type(self, site_outputs):
        base, out = site_outputs
        _write(out / "html", "avis-x_refreshed.gutenberg.html")
        expected = _write(out / "html" / "avis", "avis-x_refreshed.gutenberg.html")
        found = _discover_gutenberg(base, "test.fr",
                                    "https://test.fr/avis-x/", "avis")
        assert found == expected

    def test_refuses_substring_match(self, site_outputs):
        """`conjugaison` ne doit JAMAIS ramener `modes-de-conjugaison`.

        Cas réel : deux articles distincts, dont l'un aurait été écrasé par le
        contenu de l'autre sans le moindre signal.
        """
        base, out = site_outputs
        _write(out / "html", "modes-de-conjugaison.html_refreshed.gutenberg.html")
        found = _discover_gutenberg(base, "test.fr",
                                    "https://test.fr/x/conjugaison.html", None)
        assert found is None

    def test_refuses_ambiguous_prefix(self, site_outputs):
        """Plusieurs passes du même article : on s'arrête, --html-file tranche."""
        base, out = site_outputs
        _write(out / "html", "mon-article_refreshed.gutenberg.html")
        _write(out / "html" / "articles_260812",
               "mon-article_refreshed.gutenberg.html")
        found = _discover_gutenberg(base, "test.fr",
                                    "https://test.fr/mon-article/", None)
        assert found is None

    def test_returns_none_when_no_output_dir(self, tmp_path):
        found = _discover_gutenberg(tmp_path, "absent.fr",
                                    "https://absent.fr/x/", None)
        assert found is None


class TestDiscoverMetadata:
    def test_matches_context_slug(self, site_outputs):
        """Convention des chemins batch : URL entière translittérée.

        Elle ne partage aucun préfixe avec le slug d'URL ; sans elle, un
        article préparé en batch publiait sans titre ni meta SEOPress.
        """
        base, out = site_outputs
        gut = _write(out / "html", "avis-gostudent_refreshed.gutenberg.html")
        expected = _write(out / "metadata",
                          "https_test_fr_avis_gostudent_metadata.json", "{}")
        found = _discover_metadata(gut, "avis-gostudent",
                                   "https://test.fr/avis-gostudent/")
        assert found == expected

    def test_matches_url_slug(self, site_outputs):
        base, out = site_outputs
        gut = _write(out / "html", "mon-article_refreshed.gutenberg.html")
        expected = _write(out / "metadata", "mon-article_metadata.json", "{}")
        found = _discover_metadata(gut, "mon-article", "https://test.fr/mon-article/")
        assert found == expected

    def test_climbs_out_of_type_subfolder(self, site_outputs):
        """html/avis/x.html → outputs/metadata/, pas html/avis/metadata/."""
        base, out = site_outputs
        gut = _write(out / "html" / "avis", "avis-x_refreshed.gutenberg.html")
        expected = _write(out / "metadata", "avis-x_metadata.json", "{}")
        found = _discover_metadata(gut, "avis-x", "https://test.fr/avis-x/")
        assert found == expected

    def test_returns_none_when_absent(self, site_outputs):
        base, out = site_outputs
        gut = _write(out / "html", "orphelin_refreshed.gutenberg.html")
        found = _discover_metadata(gut, "orphelin", "https://test.fr/orphelin/")
        assert found is None


class TestReadQcVerdict:
    """`push` reste soumis à la validation : il relit le verdict de `finalize`."""

    def _write_qc(self, tmp_path, url, qc):
        from scripts.audit.ytg_qc import url_to_context_slug

        ctx = tmp_path / "_shared" / "context" / url_to_context_slug(url)
        ctx.mkdir(parents=True)
        payload = {"url": url}
        if qc is not None:
            payload["ytg_qc"] = qc
        (ctx / "audit_data.json").write_text(json.dumps(payload), encoding="utf-8")

    def test_reads_verdict_and_path(self, tmp_path):
        url = "https://test.fr/article/"
        self._write_qc(tmp_path, url,
                       {"verdict": "OPTIMAL", "html_path": "/out/a.gutenberg.html"})
        assert _read_qc_verdict(tmp_path, url) == ("OPTIMAL", "/out/a.gutenberg.html")

    def test_never_validated_returns_none(self, tmp_path):
        """Sans QC enregistrée, l'article n'a jamais été validé : pas de push."""
        url = "https://test.fr/article/"
        self._write_qc(tmp_path, url, None)
        assert _read_qc_verdict(tmp_path, url) == (None, None)

    def test_no_context_returns_none(self, tmp_path):
        assert _read_qc_verdict(tmp_path, "https://test.fr/jamais-vu/") == (None, None)

    def test_verdict_without_html_path(self, tmp_path):
        url = "https://test.fr/article/"
        self._write_qc(tmp_path, url, {"verdict": "NEEDS_FIX"})
        assert _read_qc_verdict(tmp_path, url) == ("NEEDS_FIX", None)
