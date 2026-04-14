"""
Sibling Fetcher Module

Fetches metadata (H1, keyword, URL) for sibling articles.
"""

import logging
import re
from typing import Optional
from _shared.core.models.cocon_models import SiblingArticle

logger = logging.getLogger(__name__)


class SiblingFetcher:
    """
    Fetches sibling article metadata efficiently.

    Strategy:
    1. Query spreadsheet for all sibling URLs in batch (1 API call)
    2. For URLs not in spreadsheet: fetch via STSEO API to extract H1
    3. Return list of SiblingArticle
    """

    def __init__(self, sheets_client, stseo_client=None):
        """
        Initialize the fetcher.

        Args:
            sheets_client: SheetsClient instance for spreadsheet queries
            stseo_client: STSEOClient instance for content fetching fallback
        """
        self.sheets_client = sheets_client
        self.stseo_client = stseo_client

    def fetch_batch(self, sibling_urls: list[str]) -> list[SiblingArticle]:
        """
        Fetch metadata for multiple sibling URLs efficiently.

        Strategy:
        1. Query spreadsheet for all URLs (batch read)
        2. For URLs not found: fetch via STSEO API

        Args:
            sibling_urls: List of sibling URLs to fetch

        Returns:
            List of SiblingArticle with metadata
        """
        if not sibling_urls:
            return []

        siblings = []

        # Step 1: Try to fetch from spreadsheet (fast path)
        spreadsheet_data = self._fetch_from_spreadsheet(sibling_urls)

        # Step 2: For URLs not in spreadsheet, fetch via STSEO API (fallback)
        found_urls = {data['url'] for data in spreadsheet_data}
        missing_urls = [url for url in sibling_urls if url not in found_urls]

        for url in missing_urls:
            fetched_data = self._fetch_sibling_via_api(url)
            if fetched_data:
                spreadsheet_data.append(fetched_data)

        # Convert to SiblingArticle objects
        for data in spreadsheet_data:
            siblings.append(SiblingArticle(
                url=data['url'],
                h1=data['title'],
                main_keyword=data.get('keyword', ''),
                context_h2_from_parent=data.get('context_h2')
            ))

        return siblings

    def fetch_single(self, url: str) -> Optional[SiblingArticle]:
        """
        Fetch metadata for a single sibling URL.

        Args:
            url: Sibling URL to fetch

        Returns:
            SiblingArticle or None if fetch failed
        """
        siblings = self.fetch_batch([url])
        return siblings[0] if siblings else None

    def _fetch_from_spreadsheet(self, urls: list[str]) -> list[dict]:
        """
        Fetch sibling metadata from spreadsheet.

        Queries columns C (url), D (keyword), E (title), P (new_h1_title).
        Priority: new_h1_title (col P) > title (col E) for refreshed articles.

        Args:
            urls: List of URLs to query

        Returns:
            List of dicts with url, title, keyword
        """
        if not self.sheets_client:
            logger.warning("No sheets_client available, skipping spreadsheet fetch")
            return []

        try:
            # Read all rows from Refreshs_Audit sheet
            data = self.sheets_client._read_sheet(self.sheets_client.SHEET_REFRESHS_AUDIT)

            results = []
            for row in data[1:]:  # Skip header
                if len(row) < 5:
                    continue

                # Column C (index 2) = blogpost_url
                # Column D (index 3) = main_keyword
                # Column E (index 4) = title (original)
                # Column P (index 15) = new_h1_title (refreshed, if available)
                row_url = row[2] if len(row) > 2 else ""

                if row_url in urls:
                    # Priority: use refreshed H1 (col P) if available, else original title (col E)
                    new_h1 = row[15].strip() if len(row) > 15 and row[15].strip() else ""
                    original_title = row[4] if len(row) > 4 else ""
                    title = new_h1 or original_title

                    if new_h1:
                        logger.info(f"[SiblingFetcher] Using refreshed H1 for {row_url[:50]}: {new_h1[:60]}")

                    results.append({
                        'url': row_url,
                        'keyword': row[3] if len(row) > 3 else "",
                        'title': title,
                    })

            logger.info(f"[SiblingFetcher] Found {len(results)}/{len(urls)} siblings in spreadsheet")
            return results

        except Exception as e:
            logger.error(f"[SiblingFetcher] Error fetching from spreadsheet: {e}")
            return []

    def _fetch_sibling_via_api(self, url: str) -> Optional[dict]:
        """
        Fetch sibling article content via STSEO API to extract H1.

        Fallback when URL not in spreadsheet.

        Args:
            url: URL to fetch

        Returns:
            Dict with url, title, keyword or None if fetch failed
        """
        if not self.stseo_client:
            logger.warning("No stseo_client available, skipping API fetch")
            return None

        try:
            logger.info(f"[SiblingFetcher] Fetching sibling via STSEO API (not in sheet): {url[:60]}")

            result = self.stseo_client.get_post_content_by_link(url)

            if not result or result.get("error") or not result.get("post_content"):
                logger.warning(f"[SiblingFetcher] STSEO API returned no content for {url[:60]}")
                return None

            html = result["post_content"]

            # Extract H1
            h1_match = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.I | re.S)

            if not h1_match:
                logger.warning(f"[SiblingFetcher] No H1 found in {url[:60]}")
                return None

            # Clean H1 (remove HTML tags)
            h1 = re.sub(r'<[^>]+>', '', h1_match.group(1))
            h1 = re.sub(r'\s+', ' ', h1).strip()

            logger.info(f"[SiblingFetcher] Fetched H1: {h1[:60]}")

            return {
                'url': url,
                'title': h1,
                'keyword': '',
            }

        except Exception as e:
            logger.error(f"[SiblingFetcher] Error fetching {url[:60]}: {e}")
            return None
