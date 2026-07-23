"""
Sitemap Module

Sitemap fetching and analysis for SEO workflows.
Entry point: config_adapter (loads SiteConfig from sites/<site-slug>/config/site.json).
"""

from .fetcher import SitemapFetcher
from .analyzer import SitemapAnalyzer

__all__ = [
    "SitemapFetcher",
    "SitemapAnalyzer",
]
