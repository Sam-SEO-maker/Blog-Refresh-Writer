"""
Sitemap Models Module

Data models for sitemap fetching and analysis.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum


class SitemapType(str, Enum):
    """Type of sitemap file."""
    STANDARD = "standard"      # Regular sitemap.xml
    INDEX = "index"            # Sitemap index file
    UNKNOWN = "unknown"


@dataclass
class SitemapURL:
    """
    Represents a single URL entry from a sitemap.

    Attributes:
        loc: The URL location (required)
        lastmod: Last modification date in ISO format (optional)
        changefreq: Change frequency hint (optional)
        priority: Priority value 0.0-1.0 (optional)
        slug: URL slug extracted from loc (auto-generated)
    """
    loc: str
    lastmod: Optional[str] = None
    changefreq: Optional[str] = None
    priority: Optional[float] = None
    slug: str = field(default="", init=False)

    def __post_init__(self):
        """Extract slug from URL."""
        # Remove domain and get the path
        from urllib.parse import urlparse
        parsed = urlparse(self.loc)
        path = parsed.path.strip('/')
        self.slug = path.split('/')[-1] if path else ""

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "loc": self.loc,
            "lastmod": self.lastmod,
            "changefreq": self.changefreq,
            "priority": self.priority,
            "slug": self.slug
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SitemapURL":
        """Create from dictionary."""
        return cls(
            loc=data["loc"],
            lastmod=data.get("lastmod"),
            changefreq=data.get("changefreq"),
            priority=data.get("priority")
        )


@dataclass
class SitemapCache:
    """
    Cached sitemap data with metadata.

    Attributes:
        urls: List of SitemapURL objects
        fetch_timestamp: When the sitemap was fetched
        sitemap_url: Source sitemap URL
        sitemap_type: Type of sitemap (standard/index)
        total_urls: Total count of URLs
        error: Error message if fetch failed (optional)
    """
    urls: list[SitemapURL]
    fetch_timestamp: str  # ISO format
    sitemap_url: str
    sitemap_type: SitemapType = SitemapType.STANDARD
    total_urls: int = field(default=0, init=False)
    error: Optional[str] = None

    def __post_init__(self):
        """Calculate total URLs."""
        self.total_urls = len(self.urls)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "urls": [url.to_dict() for url in self.urls],
            "fetch_timestamp": self.fetch_timestamp,
            "sitemap_url": self.sitemap_url,
            "sitemap_type": self.sitemap_type.value,
            "total_urls": self.total_urls,
            "error": self.error
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SitemapCache":
        """Create from dictionary."""
        urls = [SitemapURL.from_dict(u) for u in data.get("urls", [])]
        return cls(
            urls=urls,
            fetch_timestamp=data["fetch_timestamp"],
            sitemap_url=data["sitemap_url"],
            sitemap_type=SitemapType(data.get("sitemap_type", "standard")),
            error=data.get("error")
        )


@dataclass
class FetchResult:
    """
    Result of a sitemap fetch operation with change detection.

    Attributes:
        new_urls: URLs that weren't in previous cache
        removed_urls: URLs that were in previous cache but not current
        total_previous: Count of URLs in previous cache
        total_current: Count of URLs in current cache
        has_changes: Whether any changes were detected
    """
    new_urls: list[SitemapURL]
    removed_urls: list[str]  # Just the loc strings
    total_previous: int
    total_current: int
    has_changes: bool = field(default=False, init=False)

    def __post_init__(self):
        """Determine if changes exist."""
        self.has_changes = len(self.new_urls) > 0 or len(self.removed_urls) > 0


@dataclass
class StaleContent:
    """
    Represents content that may need refreshing.

    Attributes:
        url: The content URL
        lastmod: Last modification date (optional)
        days_since_update: Days since last update (-1 if no lastmod)
        slug: URL slug
        refresh_priority: Priority score 1-5 (5 = highest)
    """
    url: str
    lastmod: Optional[str]
    days_since_update: int
    slug: str
    refresh_priority: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "url": self.url,
            "lastmod": self.lastmod,
            "days_since_update": self.days_since_update,
            "slug": self.slug,
            "refresh_priority": self.refresh_priority
        }
