"""
Sitemap Analyzer Module

Analyzes sitemap data to identify stale content that needs refreshing.
"""

from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path

from _shared.core.models import SitemapURL, StaleContent
from .fetcher import SitemapFetcher, load_fetcher_from_config


class SitemapAnalyzer:
    """
    Analyzes sitemap URLs to find content needing refresh.

    Features:
    - Find content older than N months based on lastmod
    - Calculate refresh priority based on age
    - Handle missing lastmod dates gracefully

    Usage:
        analyzer = SitemapAnalyzer(sitemap_fetcher)
        stale = analyzer.find_stale_content(months=6)

        for item in stale:
            print(f"{item.url} - Priority: {item.refresh_priority}")
    """

    def __init__(self, sitemap_fetcher: SitemapFetcher):
        """
        Initialize the analyzer.

        Args:
            sitemap_fetcher: Configured SitemapFetcher instance
        """
        self.fetcher = sitemap_fetcher

    def find_stale_content(
        self,
        months: int = 6,
        min_priority: int = 1,
        force_refresh: bool = False
    ) -> list[StaleContent]:
        """
        Find content older than specified months.

        Args:
            months: Number of months to consider content stale
            min_priority: Minimum priority to include (1-5)
            force_refresh: Whether to fetch fresh sitemap data

        Returns:
            List of StaleContent objects, sorted by priority (highest first)
        """
        # Fetch URLs
        urls = self.fetcher.fetch(force_refresh=force_refresh)

        # Calculate cutoff date
        cutoff_date = datetime.now() - timedelta(days=months * 30)

        stale = []

        for url in urls:
            if not url.lastmod:
                # No lastmod = potentially stale, medium priority
                stale.append(StaleContent(
                    url=url.loc,
                    lastmod=None,
                    days_since_update=-1,
                    slug=url.slug,
                    refresh_priority=3
                ))
                continue

            try:
                # Parse lastmod date (handle different formats)
                lastmod_str = url.lastmod.split("T")[0]  # Take just date part
                lastmod_date = datetime.fromisoformat(lastmod_str)

                if lastmod_date < cutoff_date:
                    days_old = (datetime.now() - lastmod_date).days

                    # Calculate priority based on age
                    priority = self._calculate_priority(days_old)

                    if priority >= min_priority:
                        stale.append(StaleContent(
                            url=url.loc,
                            lastmod=url.lastmod,
                            days_since_update=days_old,
                            slug=url.slug,
                            refresh_priority=priority
                        ))

            except (ValueError, AttributeError) as e:
                # Invalid date format - treat as unknown
                stale.append(StaleContent(
                    url=url.loc,
                    lastmod=url.lastmod,
                    days_since_update=-1,
                    slug=url.slug,
                    refresh_priority=2
                ))

        # Sort by priority (highest first), then by days old
        stale.sort(key=lambda x: (x.refresh_priority, x.days_since_update), reverse=True)

        return stale

    def _calculate_priority(self, days_old: int) -> int:
        """
        Calculate refresh priority based on content age.

        Priority scale:
        - 5: Very high (>365 days / 1 year)
        - 4: High (>270 days / 9 months)
        - 3: Medium (>180 days / 6 months)
        - 2: Low (>120 days / 4 months)
        - 1: Very low (>90 days / 3 months)

        Args:
            days_old: Number of days since last update

        Returns:
            Priority score 1-5
        """
        if days_old > 365:
            return 5
        elif days_old > 270:
            return 4
        elif days_old > 180:
            return 3
        elif days_old > 120:
            return 2
        else:
            return 1

    def get_all_urls(self, force_refresh: bool = False) -> list[str]:
        """
        Get all URLs from sitemap as plain strings.

        Useful for integration with other systems (e.g., cannibalization detection).

        Args:
            force_refresh: Whether to fetch fresh sitemap data

        Returns:
            List of URL strings
        """
        urls = self.fetcher.fetch(force_refresh=force_refresh)
        return [url.loc for url in urls]

    def get_url_count(self, force_refresh: bool = False) -> int:
        """
        Get total count of URLs in sitemap.

        Args:
            force_refresh: Whether to fetch fresh sitemap data

        Returns:
            Total URL count
        """
        urls = self.fetcher.fetch(force_refresh=force_refresh)
        return len(urls)

    def filter_by_pattern(
        self,
        pattern: str,
        force_refresh: bool = False
    ) -> list[SitemapURL]:
        """
        Filter URLs matching a pattern (e.g., "/blog/").

        Args:
            pattern: String pattern to match in URL
            force_refresh: Whether to fetch fresh sitemap data

        Returns:
            List of matching SitemapURL objects
        """
        urls = self.fetcher.fetch(force_refresh=force_refresh)
        return [url for url in urls if pattern in url.loc]


def load_analyzer_from_config(
    site_id: str,
    config_path: Optional[Path] = None
) -> SitemapAnalyzer:
    """
    Load a SitemapAnalyzer from site configuration.

    Args:
        site_id: Site identifier (e.g., "enseigna")
        config_path: Path to sites.json (auto-detected if None)

    Returns:
        Configured SitemapAnalyzer instance

    Raises:
        ValueError: If site not found or inactive

    Usage:
        analyzer = load_analyzer_from_config("enseigna")
        stale = analyzer.find_stale_content(months=6)
    """
    fetcher = load_fetcher_from_config(site_id, config_path)
    return SitemapAnalyzer(fetcher)
