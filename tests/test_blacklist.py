"""
Tests du module _shared/core/blacklist.py — liste canonique markdown + matching host.
"""

import pytest

from _shared.core import blacklist
from _shared.core.blacklist import (
    is_blacklisted_host,
    is_blacklisted_url,
    load_blacklist_domains,
    url_host,
    _normalize_entry,
)


class TestLoadBlacklist:
    def test_parses_canonical_markdown(self):
        """La liste canonique (~750 domaines) est bien parsée depuis le markdown."""
        domains = load_blacklist_domains()
        assert len(domains) > 700
        assert "acadomia.fr" in domains
        assert "preply.com" in domains
        assert "wikipedia.org" in domains  # famille toujours incluse

    def test_fallback_when_markdown_missing(self, monkeypatch, tmp_path):
        """Markdown introuvable → fallback legacy + famille Wikipédia."""
        monkeypatch.setattr(blacklist, "_project_root", lambda: tmp_path)
        load_blacklist_domains.cache_clear()
        try:
            domains = load_blacklist_domains()
            assert "acadomia.fr" in domains       # legacy
            assert "wikipedia.org" in domains     # famille wiki
            assert len(domains) < 50
        finally:
            load_blacklist_domains.cache_clear()


class TestNormalizeEntry:
    def test_path_entry_gives_parent_domain(self):
        assert "quipper.com" in _normalize_entry("Quipper.com/id")

    def test_subdomain_entry_adds_parent(self):
        got = _normalize_entry("en.duolingo.com")
        assert {"en.duolingo.com", "duolingo.com"} <= got

    def test_generic_sld_not_promoted(self):
        """121tutors.co.nz ne doit JAMAIS blacklister co.nz entier."""
        got = _normalize_entry("121tutors.co.nz")
        assert "121tutors.co.nz" in got
        assert "co.nz" not in got

    def test_garbage_lines_ignored(self):
        assert _normalize_entry("") == set()
        assert _normalize_entry("# commentaire") == set()
        assert _normalize_entry("pas un domaine !") == set()


class TestMatching:
    @pytest.mark.parametrize("url,expected", [
        ("https://fr.wikipedia.org/wiki/Japon", True),      # toutes langues wiki
        ("https://www.acadomia.fr/offre", True),
        ("https://blog.acadomia.fr/article", True),         # sous-domaine
        ("https://www.preply.com/fr/blog", True),
        ("https://www.insee.fr/fr/statistiques", False),    # autorité légitime
        ("https://chef.com/page", False),                   # pas de faux positif substring
        ("/ressources/interne", False),                     # lien relatif
        ("#ancre", False),
        ("", False),
    ])
    def test_is_blacklisted_url(self, url, expected):
        assert is_blacklisted_url(url) is expected

    def test_no_substring_false_positive_on_host(self):
        """Un host qui CONTIENT un domaine blacklisté sans en être un sous-domaine
        n'est pas matché (l'ancien `domain in netloc` l'aurait flagué)."""
        assert is_blacklisted_host("notacadomia.fr") is False
        assert is_blacklisted_host("acadomia.fr.example.com") is False

    def test_url_host_normalization(self):
        assert url_host("https://WWW.Acadomia.FR:443/x") == "acadomia.fr"
        assert url_host("acadomia.fr/page") == "acadomia.fr"
        assert url_host("/relatif") == ""
