"""
Cannibalization Detector Module

Detects H2 cannibalization with sibling articles in semantic cocons.
"""

import logging
from typing import Optional
from _shared.core.models.cocon_models import (
    CannibalizationMatch,
    CannibalizationReport,
    CoconRegistryData
)
from .cocon_registry import CoconRegistry
from .similarity_engine import SimilarityEngine

logger = logging.getLogger(__name__)


class CannibalizationDetector:
    """
    Detects H2 headings that cannibalize sibling article H1s.

    Workflow:
    1. Load cocon structure via CoconRegistry
    2. For each H2 in current article:
       - Compare with each sibling H1
       - If similarity ≥ 0.75 → add to matches
    3. Generate blacklist of sibling topics
    4. Return CannibalizationReport
    """

    # Cannibalization threshold (similarity score ≥ 0.75 = HIGH cannibalization)
    CANNIBALIZATION_THRESHOLD = 0.75

    def __init__(self, sheets_client, stseo_client=None):
        """
        Initialize the detector.

        Args:
            sheets_client: SheetsClient for spreadsheet queries
            stseo_client: STSEOClient for content fetching fallback
        """
        self.cocon_registry = CoconRegistry(sheets_client, stseo_client)
        self.similarity_engine = SimilarityEngine()

    def detect(
        self,
        url: str,
        blog_id: str,
        current_h2_list: list[str],
        cocon_structure: Optional[dict] = None
    ) -> CannibalizationReport:
        """
        Detect H2 cannibalization with siblings.

        Args:
            url: URL of the current article
            blog_id: Blog ID (e.g., 'enseigna')
            current_h2_list: List of H2 headings in current article
            cocon_structure: Pre-extracted cocon structure from HTMLAnalyzer (optional)

        Returns:
            CannibalizationReport with detected matches and blacklist
        """
        logger.info(f"[CannibalizationDetector] Analyzing {len(current_h2_list)} H2s for {url[:60]}")

        # Load cocon structure
        try:
            cocon_data = self.cocon_registry.load_cocon(url, blog_id, cocon_structure)
        except Exception as e:
            logger.error(f"[CannibalizationDetector] Failed to load cocon: {e}")
            # Return empty report on failure
            return CannibalizationReport(
                current_url=url,
                h2_analyzed_count=len(current_h2_list)
            )

        # If no siblings, no cannibalization possible
        if not cocon_data.siblings:
            logger.info(f"[CannibalizationDetector] No siblings, skipping detection")
            return CannibalizationReport(
                current_url=url,
                h2_analyzed_count=len(current_h2_list)
            )

        # Detect matches
        matches = []

        for h2 in current_h2_list:
            for sibling in cocon_data.siblings:
                try:
                    # Compute similarity
                    score, match_type = self.similarity_engine.compute_similarity(
                        h2,
                        sibling.h1
                    )

                    # If score ≥ threshold, it's cannibalization
                    if score >= self.CANNIBALIZATION_THRESHOLD:
                        match = CannibalizationMatch(
                            current_h2=h2,
                            sibling_h1=sibling.h1,
                            sibling_url=sibling.url,
                            similarity_score=score,
                            match_type=match_type
                        )
                        matches.append(match)

                        logger.warning(
                            f"[CannibalizationDetector] MATCH: H2 '{h2[:40]}' ↔ "
                            f"Sibling '{sibling.h1[:40]}' (score={score:.2f}, type={match_type})"
                        )

                except Exception as e:
                    logger.debug(
                        f"[CannibalizationDetector] Similarity check failed for "
                        f"'{h2[:30]}' vs '{sibling.h1[:30]}': {e}"
                    )
                    continue

        # Generate blacklist
        blacklist = self.generate_blacklist(matches, cocon_data)

        # Create report
        report = CannibalizationReport(
            current_url=url,
            h2_analyzed_count=len(current_h2_list),
            matches=matches,
            blacklist_h2_topics=blacklist
        )

        logger.info(
            f"[CannibalizationDetector] Detection complete: "
            f"{len(matches)} cannibalization matches, "
            f"{len(blacklist)} blacklisted topics"
        )

        return report

    def generate_blacklist(
        self,
        matches: list[CannibalizationMatch],
        cocon_data: CoconRegistryData
    ) -> list[str]:
        """
        Generate list of topics to blacklist in the prompt.

        Format:
        - "Où aller en Angleterre pour apprendre l'anglais" (sibling: /meilleures-villes/)
        - "Budget et prix des cours d'anglais" (sibling: /budget-cours/)

        Args:
            matches: List of detected cannibalization matches
            cocon_data: Complete cocon structure

        Returns:
            List of blacklist entries (formatted strings)
        """
        if not matches:
            return []

        blacklist = []

        for match in matches:
            # Extract slug from sibling URL for display
            slug = match.sibling_url.split('/')[-2] if match.sibling_url.endswith('/') else match.sibling_url.split('/')[-1]

            entry = f'"{match.current_h2}" (sibling: /{slug}/)'
            blacklist.append(entry)

        return blacklist
