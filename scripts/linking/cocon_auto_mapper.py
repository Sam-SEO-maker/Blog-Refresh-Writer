"""
Cocon Auto Mapper Module

Auto-generates LinkMapping objects from the Refreshs_Audit spreadsheet,
replacing manual CSV creation for internal link injection.

Reads cocon structure (blog_id + cocon_branch) and determines:
- PARENT → CHILD links (after corresponding H2)
- CHILD → PARENT links (in introduction)
- CHILD ↔ CHILD sibling links (body, 150+ word spacing)
"""

import json
import logging
from typing import Optional

from _shared.core.models.linking_models import LinkMapping
from _shared.core.models.enums import PostType
from scripts.cocon.similarity_engine import SimilarityEngine

logger = logging.getLogger(__name__)

# Maximum sibling links per article to avoid link stuffing
MAX_SIBLINGS_PER_ARTICLE = 2

# Minimum similarity score to match a PARENT H2 with a CHILD H1
H2_H1_MATCH_THRESHOLD = 0.5


class CoconAutoMapper:
    """
    Auto-generates LinkMapping objects from spreadsheet data.

    Replaces manual CSV creation by reading Refreshs_Audit rows
    filtered by blog_id + cocon_branch, then generating link mappings
    based on PARENT/CHILD/SOEUR relationships.
    """

    def __init__(self, sheets_client, stseo_client=None):
        """
        Args:
            sheets_client: SheetsClient instance for spreadsheet access
            stseo_client: Optional STSEOClient for fallback content fetching
        """
        self.sheets_client = sheets_client
        self.stseo_client = stseo_client
        self.similarity_engine = SimilarityEngine()

    def generate_mappings(self, blog_id: str, cocon_branch: int) -> list[LinkMapping]:
        """
        Generate all LinkMapping objects for a cocon branch.

        Steps:
        1. Read all rows from Refreshs_Audit matching blog_id + cocon_branch
        2. Separate into PARENT / CHILD articles
        3. Generate PARENT→CHILD, CHILD→PARENT, CHILD↔CHILD mappings

        Args:
            blog_id: Blog identifier (e.g., "coachsportlyon.fr")
            cocon_branch: Cocon branch number (e.g., 1, 2, 3)

        Returns:
            List of LinkMapping objects ready for LinkInjector
        """
        # 1. Read rows from spreadsheet
        rows = self.sheets_client.read_cocon_branch(blog_id, cocon_branch)

        if not rows:
            logger.warning(f"No rows found for blog_id={blog_id}, cocon_branch={cocon_branch}")
            return []

        logger.info(f"Found {len(rows)} articles in cocon branch {cocon_branch} for {blog_id}")

        # 2. Separate PARENT and CHILD articles
        parent_rows = [r for r in rows if r.post_type == PostType.PARENT]
        child_rows = [r for r in rows if r.post_type == PostType.CHILD]

        if not parent_rows:
            logger.warning("No PARENT article found in this cocon branch")
            # Still generate sibling links between children
            return self._generate_sibling_mappings(child_rows)

        if len(parent_rows) > 1:
            logger.warning(f"Multiple PARENT articles found ({len(parent_rows)}), using first one")

        parent = parent_rows[0]
        mappings = []

        # 3. Generate PARENT → CHILD mappings
        parent_to_child = self._generate_parent_to_child_mappings(parent, child_rows)
        mappings.extend(parent_to_child)

        # 4. Generate CHILD → PARENT mappings
        child_to_parent = self._generate_child_to_parent_mappings(parent, child_rows)
        mappings.extend(child_to_parent)

        # 5. Generate CHILD ↔ CHILD sibling mappings
        sibling_mappings = self._generate_sibling_mappings(child_rows)
        mappings.extend(sibling_mappings)

        logger.info(
            f"Generated {len(mappings)} link mappings: "
            f"{len(parent_to_child)} parent→child, "
            f"{len(child_to_parent)} child→parent, "
            f"{len(sibling_mappings)} siblings"
        )

        return mappings

    def _generate_parent_to_child_mappings(self, parent, child_rows) -> list[LinkMapping]:
        """
        Generate PARENT → CHILD mappings.

        For each child, create a mapping from parent to child with
        type_relation="Parent". The link will be placed after the
        corresponding H2 section in the parent article.

        Uses SimilarityEngine to match child H1 with parent H2s.
        """
        mappings = []
        parent_h2s = self._get_h2_titles(parent)

        for child in child_rows:
            child_h1 = child.new_h1_title or child.title

            if not child_h1:
                logger.warning(f"Child {child.blogpost_url} has no H1/title, skipping")
                continue

            # Try to match child H1 with a parent H2 for optimal placement
            best_h2 = None
            if parent_h2s:
                best_h2 = self._find_best_h2_match(child_h1, parent_h2s)

            mapping = LinkMapping(
                url_source=parent.blogpost_url,
                url_cible=child.blogpost_url,
                mot_cle_principal=child.main_keyword or child_h1,
                type_relation="Parent",
                h1_cible=child_h1,
            )
            mappings.append(mapping)

            if best_h2:
                logger.debug(f"Matched child H1 '{child_h1}' → parent H2 '{best_h2}'")
            else:
                logger.debug(f"No H2 match for child H1 '{child_h1}', will use default placement")

        return mappings

    def _generate_child_to_parent_mappings(self, parent, child_rows) -> list[LinkMapping]:
        """
        Generate CHILD → PARENT mappings.

        For each child, create a mapping from child to parent with
        type_relation="Enfant". The link will be placed in the introduction.
        """
        parent_h1 = parent.new_h1_title or parent.title

        if not parent_h1:
            logger.warning("Parent has no H1/title, using URL as keyword")
            parent_h1 = parent.blogpost_url

        mappings = []
        for child in child_rows:
            mapping = LinkMapping(
                url_source=child.blogpost_url,
                url_cible=parent.blogpost_url,
                mot_cle_principal=parent.main_keyword or parent_h1,
                type_relation="Enfant",
                h1_cible=parent_h1,
            )
            mappings.append(mapping)

        return mappings

    def _generate_sibling_mappings(self, child_rows) -> list[LinkMapping]:
        """
        Generate CHILD ↔ CHILD (sibling) mappings.

        For each child, create 1-2 bidirectional sibling links to
        other children in the same cocon. Cap at MAX_SIBLINGS_PER_ARTICLE.
        """
        if len(child_rows) < 2:
            return []

        mappings = []
        # Track how many sibling links each article already has
        sibling_count: dict[str, int] = {r.blogpost_url: 0 for r in child_rows}
        # Track created pairs to avoid duplicates
        created_pairs: set[tuple[str, str]] = set()

        for i, child_a in enumerate(child_rows):
            if sibling_count[child_a.blogpost_url] >= MAX_SIBLINGS_PER_ARTICLE:
                continue

            for j, child_b in enumerate(child_rows):
                if i == j:
                    continue

                # Skip if this pair was already created (in either direction)
                pair_key = (child_a.blogpost_url, child_b.blogpost_url)
                if pair_key in created_pairs:
                    continue

                # Check caps for both sides
                if sibling_count[child_a.blogpost_url] >= MAX_SIBLINGS_PER_ARTICLE:
                    break
                if sibling_count[child_b.blogpost_url] >= MAX_SIBLINGS_PER_ARTICLE:
                    continue

                child_b_h1 = child_b.new_h1_title or child_b.title

                # A → B
                mappings.append(LinkMapping(
                    url_source=child_a.blogpost_url,
                    url_cible=child_b.blogpost_url,
                    mot_cle_principal=child_b.main_keyword or child_b_h1,
                    type_relation="Soeur",
                    h1_cible=child_b_h1,
                ))
                sibling_count[child_a.blogpost_url] += 1
                created_pairs.add(pair_key)

                # B → A (bidirectional)
                reverse_key = (child_b.blogpost_url, child_a.blogpost_url)
                child_a_h1 = child_a.new_h1_title or child_a.title
                mappings.append(LinkMapping(
                    url_source=child_b.blogpost_url,
                    url_cible=child_a.blogpost_url,
                    mot_cle_principal=child_a.main_keyword or child_a_h1,
                    type_relation="Soeur",
                    h1_cible=child_a_h1,
                ))
                sibling_count[child_b.blogpost_url] += 1
                created_pairs.add(reverse_key)

        return mappings

    def _get_h2_titles(self, row) -> list[str]:
        """
        Extract H2 titles from a RefreshAuditRow.

        Tries column Q (new_h2_titles, JSON list) first.
        Falls back to scraping the article HTML if needed.
        """
        # Try from spreadsheet (JSON list in new_h2_titles column)
        if row.new_h2_titles:
            try:
                h2s = json.loads(row.new_h2_titles)
                if isinstance(h2s, list) and h2s:
                    return h2s
            except (json.JSONDecodeError, TypeError):
                # Not valid JSON, try comma-separated
                if "," in row.new_h2_titles:
                    return [h.strip() for h in row.new_h2_titles.split(",") if h.strip()]

        # Fallback: fetch via STSEO API to extract H2s
        if self.stseo_client and row.blogpost_url:
            return self._fetch_h2_titles(row.blogpost_url)

        return []

    def _fetch_h2_titles(self, url: str) -> list[str]:
        """Fetch H2 titles from an article via STSEO API."""
        try:
            result = self.stseo_client.get_post_content_by_link(url)
            if not result or result.get("error") or not result.get("post_content"):
                return []

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(result["post_content"], 'html.parser')
            h2_tags = soup.find_all('h2')
            return [h2.get_text(strip=True) for h2 in h2_tags if h2.get_text(strip=True)]

        except Exception as e:
            logger.warning(f"Failed to fetch H2s from {url}: {e}")
            return []

    def _find_best_h2_match(self, child_h1: str, parent_h2s: list[str]) -> Optional[str]:
        """
        Find the parent H2 that best matches a child H1 title.

        Uses SimilarityEngine for matching with threshold.

        Returns:
            Best matching H2 title, or None if no match above threshold.
        """
        best_score = 0.0
        best_h2 = None

        for h2 in parent_h2s:
            score, match_type = self.similarity_engine.compute_similarity(child_h1, h2)
            if score > best_score and score >= H2_H1_MATCH_THRESHOLD:
                best_score = score
                best_h2 = h2

        return best_h2
