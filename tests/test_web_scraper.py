"""Tests for WebScraper module"""

import pytest
from datetime import datetime, timedelta
from scripts.scraping.web_scraper import RateLimiter, WebScraper


class TestRateLimiter:
    """Test RateLimiter class"""

    def test_init(self):
        """Test RateLimiter initialization"""
        limiter = RateLimiter(requests_per_minute=30)
        assert limiter.rpm == 30
        assert len(limiter.requests) == 0

    def test_wait_if_needed_no_wait(self):
        """Test that no wait occurs when under limit"""
        limiter = RateLimiter(requests_per_minute=20)

        # First request should not wait
        import time
        start = time.time()
        limiter.wait_if_needed("https://example.com/page1")
        duration = time.time() - start

        # Should be immediate (< 0.1s)
        assert duration < 0.1

    def test_wait_if_needed_same_domain(self):
        """Test that rate limit applies per domain"""
        limiter = RateLimiter(requests_per_minute=2)  # Very low limit for testing

        # Make 2 requests to same domain (under limit)
        limiter.wait_if_needed("https://example.com/page1")
        limiter.wait_if_needed("https://example.com/page2")

        # Check that 2 requests were recorded
        assert len(limiter.requests["example.com"]) == 2

    def test_wait_if_needed_different_domains(self):
        """Test that different domains have separate limits"""
        limiter = RateLimiter(requests_per_minute=2)

        limiter.wait_if_needed("https://example.com/page1")
        limiter.wait_if_needed("https://other.com/page1")

        # Different domains should have separate counters
        assert len(limiter.requests["example.com"]) == 1
        assert len(limiter.requests["other.com"]) == 1


class TestWebScraper:
    """Test WebScraper class"""

    def test_init(self):
        """Test WebScraper initialization"""
        scraper = WebScraper(rate_limit_rpm=30, timeout=60, use_playwright=False)

        assert scraper.rate_limiter.rpm == 30
        assert scraper.timeout == 60
        assert scraper.use_playwright is False
        assert scraper.stats["requests_total"] == 0

    def test_get_user_agent_rotation(self):
        """Test user agent rotation"""
        scraper = WebScraper()

        ua1 = scraper._get_user_agent()
        ua2 = scraper._get_user_agent()
        ua3 = scraper._get_user_agent()
        ua4 = scraper._get_user_agent()

        # Should rotate through 3 user agents
        assert ua1 != ua2
        assert ua2 != ua3
        # Fourth should be same as first (rotation)
        assert ua4 == ua1

    def test_needs_js_rendering_react(self):
        """Test JS rendering detection for React app"""
        scraper = WebScraper()

        html_react = """
        <html>
        <head><script src="react.js"></script></head>
        <body><div id="root"></div></body>
        </html>
        """

        assert scraper._needs_js_rendering(html_react) is True

    def test_needs_js_rendering_vue(self):
        """Test JS rendering detection for Vue app"""
        scraper = WebScraper()

        html_vue = """
        <html>
        <body><div v-app>Content</div></body>
        </html>
        """

        assert scraper._needs_js_rendering(html_vue) is True

    def test_needs_js_rendering_sparse_content(self):
        """Test JS rendering detection for sparse body"""
        scraper = WebScraper()

        html_sparse = """
        <html>
        <body><p>Short</p></body>
        </html>
        """

        assert scraper._needs_js_rendering(html_sparse) is True

    def test_needs_js_rendering_normal_html(self):
        """Test that normal HTML is not flagged for JS rendering"""
        scraper = WebScraper()

        html_normal = """
        <html>
        <body>
        <p>This is a normal HTML page with plenty of content.</p>
        <p>It has multiple paragraphs with substantial text content.</p>
        <p>This should not require JavaScript rendering.</p>
        <p>The body has enough content to be considered substantial.</p>
        <p>Therefore JS rendering detection should return False.</p>
        </body>
        </html>
        """

        assert scraper._needs_js_rendering(html_normal) is False

    def test_fetch_html_invalid_url(self):
        """Test fetch_html with invalid URL"""
        scraper = WebScraper(timeout=5)

        # Invalid URL should return None
        result = scraper.fetch_html("http://this-domain-does-not-exist-12345.com")
        assert result is None

    def test_fetch_html_404(self):
        """Test fetch_html with 404 response"""
        scraper = WebScraper(timeout=5)

        # HTTPBin 404 endpoint
        result = scraper.fetch_html("https://httpbin.org/status/404")
        assert result is None

    @pytest.mark.slow
    def test_fetch_html_success(self):
        """Test successful HTML fetch from real website"""
        scraper = WebScraper(timeout=10)

        # HTTPBin is a reliable test endpoint
        result = scraper.fetch_html("https://httpbin.org/html")

        assert result is not None
        assert "<html>" in result.lower()
        assert scraper.stats["requests_success"] >= 1

    def test_get_stats(self):
        """Test stats collection"""
        scraper = WebScraper()

        # Mock some stats
        scraper.stats["requests_total"] = 10
        scraper.stats["requests_success"] = 8
        scraper.stats["requests_failed"] = 2
        scraper.stats["total_duration_ms"] = 4000

        stats = scraper.get_stats()

        assert stats["requests_total"] == 10
        assert stats["requests_success"] == 8
        assert stats["requests_failed"] == 2
        assert stats["success_rate"] == 0.8
        assert stats["avg_duration_ms"] == 500  # 4000 / 8

    def test_get_stats_empty(self):
        """Test stats with no requests"""
        scraper = WebScraper()

        stats = scraper.get_stats()

        assert stats["requests_total"] == 0
        assert stats["success_rate"] == 0.0
        assert stats["avg_duration_ms"] == 0

    @pytest.mark.slow
    def test_fetch_batch(self):
        """Test batch fetching with parallel requests"""
        scraper = WebScraper(timeout=10)

        urls = [
            "https://httpbin.org/html",
            "https://httpbin.org/status/200",
            "https://httpbin.org/status/404",
        ]

        results = scraper.fetch_batch(urls, parallel=2)

        assert len(results) == 3
        assert results["https://httpbin.org/html"]["success"] is True
        assert results["https://httpbin.org/status/200"]["success"] is True
        assert results["https://httpbin.org/status/404"]["success"] is False

    def test_fallback_playwright_disabled(self):
        """Test Playwright fallback when disabled"""
        scraper = WebScraper(use_playwright=False)

        result = scraper._fallback_playwright("https://example.com")

        # Should return None with warning
        assert result is None
        assert scraper.stats["playwright_fallbacks"] == 1


# Run with: pytest tests/test_web_scraper.py -v
# Run slow tests: pytest tests/test_web_scraper.py -v -m slow
