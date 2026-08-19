"""Tests de la publication WordPress : retry, résolution du post, vérification.

Couvre les garde-fous ajoutés autour du push :
- `update_post` ne retente que le transitoire (429/5xx/réseau), jamais un 403
  (WAF ou application password révoqué) ni un payload rejeté ;
- la publication cible l'ID mémorisé au fetch avant de retomber sur le slug ;
- le contenu publié est relu pour détecter un `core/freeform` (WP a rangé
  l'article en bloc « HTML classique » et répond quand même 200).
"""

import json
from unittest.mock import Mock, patch

import pytest

from scripts.scraping.wordpress_api_client import WordPressAPIClient
from scripts.utils.push_to_wp import _verify_blocks, resolve_wp_post_id


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("T_WP_USER", "user")
    monkeypatch.setenv("T_WP_PASS", "pass")
    return WordPressAPIClient(
        api_base_url="https://example.test/wp-json/wp/v2",
        user_env_var="T_WP_USER",
        password_env_var="T_WP_PASS",
    )


def _resp(status, text="", headers=None):
    return Mock(status_code=status, text=text, headers=headers or {})


class TestUpdatePostRetry:
    """Le retry ne doit couvrir que les échecs qui ont une chance d'aboutir."""

    def test_retries_429_then_succeeds(self, client):
        with patch("scripts.scraping.wordpress_api_client.requests.post") as post, \
             patch("time.sleep"):
            post.side_effect = [_resp(429, "rate limited", {"Retry-After": "1"}),
                                _resp(200, "ok")]
            res = client.update_post(1, content="<!-- wp:paragraph -->")

        assert res["ok"] is True
        assert res["attempts"] == 2
        assert post.call_count == 2

    def test_retries_5xx_until_max_attempts(self, client):
        with patch("scripts.scraping.wordpress_api_client.requests.post") as post, \
             patch("time.sleep"):
            post.return_value = _resp(503, "unavailable")
            res = client.update_post(1, content="x", max_attempts=3)

        assert res["ok"] is False
        assert res["attempts"] == 3
        assert post.call_count == 3

    def test_does_not_retry_403(self, client):
        """403 = WAF ou password révoqué : réessayer fait bannir l'IP."""
        with patch("scripts.scraping.wordpress_api_client.requests.post") as post, \
             patch("time.sleep"):
            post.return_value = _resp(403, "forbidden")
            res = client.update_post(1, content="x")

        assert res["ok"] is False
        assert post.call_count == 1

    def test_does_not_retry_400(self, client):
        """Payload rejeté : le rejouer produit exactement la même erreur."""
        with patch("scripts.scraping.wordpress_api_client.requests.post") as post, \
             patch("time.sleep"):
            post.return_value = _resp(400, "bad request")
            res = client.update_post(1, content="x")

        assert res["ok"] is False
        assert post.call_count == 1

    def test_retries_network_error(self, client):
        import requests

        with patch("scripts.scraping.wordpress_api_client.requests.post") as post, \
             patch("time.sleep"):
            post.side_effect = [requests.Timeout("timed out"), _resp(200, "ok")]
            res = client.update_post(1, content="x")

        assert res["ok"] is True
        assert res["attempts"] == 2


class TestRetryDelay:
    def test_honours_retry_after_seconds(self, client):
        assert client._retry_delay(1, "5") == 5.0

    def test_caps_retry_after(self, client):
        assert client._retry_delay(1, "99999") == 60.0

    def test_falls_back_on_http_date(self, client):
        """Retry-After en date HTTP : non parsé, on retombe sur l'exponentiel."""
        assert client._retry_delay(2, "Wed, 21 Oct 2026 07:28:00 GMT") == 4.0

    def test_exponential_without_header(self, client):
        assert client._retry_delay(1, None) == 2.0
        assert client._retry_delay(3, None) == 8.0

    def test_delay_is_bounded(self, client):
        assert client._retry_delay(10, None) == 30.0


class TestVerifyBlocks:
    """Un 200 ne prouve pas que WP a parsé les blocs."""

    def _client_returning(self, raw):
        c = Mock()
        c.get_post_by_id.return_value = {"raw": raw}
        return c

    def test_clean_gutenberg_has_no_warning(self):
        raw = "<!-- wp:paragraph -->\n<p>Bonjour</p>\n<!-- /wp:paragraph -->"
        assert _verify_blocks(self._client_returning(raw), 1) is None

    def test_detects_freeform(self):
        raw = "<!-- wp:freeform -->du html classique<!-- /wp:freeform -->"
        warning = _verify_blocks(self._client_returning(raw), 1)
        assert warning and "freeform" in warning

    def test_detects_missing_delimiters(self):
        warning = _verify_blocks(self._client_returning("<p>nu</p>"), 1)
        assert warning and "without any block delimiter" in warning

    def test_refetch_failure_is_reported_not_raised(self):
        c = Mock()
        c.get_post_by_id.return_value = None
        warning = _verify_blocks(c, 1)
        assert warning and "not verified" in warning


class TestResolveWpPostId:
    """L'ID mémorisé au fetch évite un `post_not_found` sur slug modifié."""

    def _write_audit(self, tmp_path, url, payload):
        from scripts.audit.ytg_qc import url_to_context_slug

        ctx = tmp_path / "_shared" / "context" / url_to_context_slug(url)
        ctx.mkdir(parents=True)
        (ctx / "audit_data.json").write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )

    def test_reads_persisted_id(self, tmp_path):
        url = "https://example.test/article/"
        self._write_audit(tmp_path, url, {"url": url, "wp_post_id": 4242})
        assert resolve_wp_post_id(url, tmp_path) == 4242

    def test_returns_none_when_absent(self, tmp_path):
        """Contenu récupéré par scraping : pas d'ID, publication par slug."""
        url = "https://example.test/article/"
        self._write_audit(tmp_path, url, {"url": url})
        assert resolve_wp_post_id(url, tmp_path) is None

    def test_returns_none_without_context(self, tmp_path):
        assert resolve_wp_post_id("https://example.test/nope/", tmp_path) is None
