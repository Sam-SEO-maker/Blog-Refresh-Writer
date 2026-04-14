"""
Cocon Registry Module

Loads and caches semantic cocon structures for articles.
"""

import logging
from typing import Optional
from _shared.core.models.cocon_models import CoconRegistryData, SiblingArticle
from .sibling_fetcher import SiblingFetcher

logger = logging.getLogger(__name__)


class CoconRegistry:
    """
    Registry for loading and caching semantic cocon structures.

    Workflow:
    1. Extract internal links from article HTML (via HTMLAnalyzer.cocon_structure)
    2. Identify parent URL (first link in intro) and sibling URLs
    3. Fetch metadata (H1, keyword) for all siblings via SiblingFetcher
    4. Return complete CoconRegistryData

    Caching:
    - In-memory cache during workflow run (keyed by URL)
    - Invalidated after refresh completion
    """

    def __init__(self, sheets_client, stseo_client=None):
        """
        Initialize the registry.

        Args:
            sheets_client: SheetsClient for spreadsheet queries
            stseo_client: STSEOClient for content fetching fallback
        """
        self.sheets_client = sheets_client
        self.stseo_client = stseo_client
        self.sibling_fetcher = SiblingFetcher(sheets_client, stseo_client)
        self._cache: dict[str, CoconRegistryData] = {}

    def load_cocon(
        self,
        url: str,
        blog_id: str,
        cocon_structure: Optional[dict] = None
    ) -> CoconRegistryData:
        """
        Load complete cocon structure for an article.

        Args:
            url: URL of the current article
            blog_id: Blog ID (e.g., 'enseigna', 'cours-particuliers')
            cocon_structure: Pre-extracted cocon structure from HTMLAnalyzer
                            (contains parent_url, parent_title, sibling_urls)

        Returns:
            CoconRegistryData with complete cocon structure
        """
        # Check cache first
        if url in self._cache:
            logger.info(f"[CoconRegistry] Cache hit for {url[:60]}")
            return self._cache[url]

        logger.info(f"[CoconRegistry] Loading cocon for {url[:60]}")

        # Initialize cocon data
        cocon_data = CoconRegistryData(current_url=url)

        # If no cocon_structure provided, article is STANDALONE
        if not cocon_structure:
            logger.info(f"[CoconRegistry] No cocon structure (STANDALONE article)")
            self._cache[url] = cocon_data
            return cocon_data

        # Extract parent info
        cocon_data.parent_url = cocon_structure.get('parent_url')
        cocon_data.parent_h1 = cocon_structure.get('parent_title')

        # Extract sibling URLs
        sibling_urls_data = cocon_structure.get('sibling_urls', [])

        # Convert sibling_urls from list of dicts to list of URLs
        sibling_urls = []
        for sibling_info in sibling_urls_data:
            if isinstance(sibling_info, dict):
                sibling_url = sibling_info.get('url', '')
                if sibling_url:
                    sibling_urls.append(sibling_url)
            elif isinstance(sibling_info, str):
                sibling_urls.append(sibling_info)

        if not sibling_urls:
            logger.info(f"[CoconRegistry] No siblings detected")
            self._cache[url] = cocon_data
            return cocon_data

        # Limit to 10 siblings max (performance optimization)
        if len(sibling_urls) > 10:
            logger.warning(f"[CoconRegistry] Truncating {len(sibling_urls)} siblings to 10")
            sibling_urls = sibling_urls[:10]

        # Fetch sibling metadata
        logger.info(f"[CoconRegistry] Fetching metadata for {len(sibling_urls)} siblings")
        siblings = self.sibling_fetcher.fetch_batch(sibling_urls)

        cocon_data.siblings = siblings

        # Cache the result
        self._cache[url] = cocon_data

        logger.info(
            f"[CoconRegistry] Loaded cocon: "
            f"{len(siblings)} siblings, "
            f"parent: {cocon_data.parent_url and 'YES' or 'NO'}"
        )

        return cocon_data

    def clear_cache(self):
        """Clear the in-memory cache."""
        self._cache.clear()
        logger.info("[CoconRegistry] Cache cleared")

    def get_from_cache(self, url: str) -> Optional[CoconRegistryData]:
        """
        Get cocon data from cache without loading.

        Args:
            url: URL to lookup

        Returns:
            CoconRegistryData if cached, None otherwise
        """
        return self._cache.get(url)
