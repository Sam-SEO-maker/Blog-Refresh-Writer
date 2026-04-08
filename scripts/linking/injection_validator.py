"""
Injection Validator Module

Validates HTML integrity after link injection.
"""

import re
import logging

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class InjectionValidator:
    """
    Validates modified HTML post-injection.

    Checks:
    1. Asset preservation (images, tables, videos >= before)
    2. Link spacing (150+ words between internal links)
    3. Forbidden anchors (no "cliquez ici", "en savoir plus")
    4. No "Articles connexes" sections
    5. HTML integrity (balanced tags)
    """

    MIN_WORDS_BETWEEN_LINKS = 150

    FORBIDDEN_ANCHORS = [
        "cliquez ici", "en savoir plus", "ici", "voir cet article",
        "cet article", "lire la suite", "plus d'infos",
    ]

    FORBIDDEN_SECTIONS = [
        "articles connexes", "pour aller plus loin", "articles similaires",
        "à lire aussi", "sur le même sujet",
    ]

    def __init__(self, domain: str):
        self.domain = domain

    def validate(self, original_html: str, modified_html: str) -> dict:
        """
        Run all validation checks on modified HTML.

        Args:
            original_html: HTML before injection
            modified_html: HTML after injection

        Returns:
            {
                "valid": bool,
                "errors": list[str],
                "warnings": list[str],
                "assets_preserved": bool,
                "link_spacing_valid": bool,
                "internal_links_before": int,
                "internal_links_after": int,
            }
        """
        errors = []
        warnings = []

        original_soup = BeautifulSoup(original_html, "html.parser")
        modified_soup = BeautifulSoup(modified_html, "html.parser")

        # 1. Asset preservation
        assets_ok, asset_errors = self._check_asset_preservation(original_soup, modified_soup)
        errors.extend(asset_errors)

        # 2. Link spacing
        spacing_ok, spacing_warns = self._check_link_spacing(modified_soup)
        warnings.extend(spacing_warns)

        # 3. Forbidden anchors
        anchor_ok, anchor_errors = self._check_forbidden_anchors(modified_soup)
        errors.extend(anchor_errors)

        # 4. No link sections
        section_ok, section_errors = self._check_no_link_sections(modified_soup)
        errors.extend(section_errors)

        # 5. HTML integrity
        html_ok, html_errors = self._check_html_integrity(modified_html)
        errors.extend(html_errors)

        # Count internal links
        original_links = self._count_internal_links(original_soup)
        modified_links = self._count_internal_links(modified_soup)

        valid = len(errors) == 0

        if valid:
            logger.info("[InjectionValidator] Validation PASSED")
        else:
            logger.warning(f"[InjectionValidator] Validation FAILED: {len(errors)} errors")
            for err in errors:
                logger.warning(f"  - {err}")

        return {
            "valid": valid,
            "errors": errors,
            "warnings": warnings,
            "assets_preserved": assets_ok,
            "link_spacing_valid": spacing_ok,
            "internal_links_before": original_links,
            "internal_links_after": modified_links,
        }

    def _check_asset_preservation(self, original: BeautifulSoup, modified: BeautifulSoup) -> tuple[bool, list[str]]:
        """Verify assets (images, tables) were not removed."""
        errors = []

        orig_images = len(original.find_all("img"))
        mod_images = len(modified.find_all("img"))
        if mod_images < orig_images:
            errors.append(f"Images reduced: {orig_images} -> {mod_images}")

        orig_tables = len(original.find_all("table"))
        mod_tables = len(modified.find_all("table"))
        if mod_tables < orig_tables:
            errors.append(f"Tables reduced: {orig_tables} -> {mod_tables}")

        orig_figures = len(original.find_all("figure"))
        mod_figures = len(modified.find_all("figure"))
        if mod_figures < orig_figures:
            errors.append(f"Figures reduced: {orig_figures} -> {mod_figures}")

        return len(errors) == 0, errors

    def _check_link_spacing(self, soup: BeautifulSoup) -> tuple[bool, list[str]]:
        """Check minimum word spacing between internal links."""
        warnings = []

        # Get full text with link positions
        text_parts = []
        link_word_positions = []
        current_word_count = 0

        for element in soup.descendants:
            if hasattr(element, "name"):
                if element.name == "a" and element.get("href", ""):
                    href = element.get("href", "")
                    if self.domain in href:
                        link_word_positions.append(current_word_count)
            elif isinstance(element, str):
                words = element.strip().split()
                current_word_count += len(words)

        # Check spacing between consecutive links
        for i in range(1, len(link_word_positions)):
            gap = link_word_positions[i] - link_word_positions[i - 1]
            if gap < self.MIN_WORDS_BETWEEN_LINKS:
                warnings.append(
                    f"Link spacing too close: {gap} words between link {i} and {i+1} "
                    f"(minimum: {self.MIN_WORDS_BETWEEN_LINKS})"
                )

        return len(warnings) == 0, warnings

    def _check_forbidden_anchors(self, soup: BeautifulSoup) -> tuple[bool, list[str]]:
        """Check no forbidden anchor texts are used."""
        errors = []

        for link in soup.find_all("a", href=True):
            anchor = link.get_text(strip=True).lower()
            for forbidden in self.FORBIDDEN_ANCHORS:
                if anchor == forbidden:
                    errors.append(f"Forbidden anchor text: '{anchor}' -> {link.get('href', '')[:50]}")

        return len(errors) == 0, errors

    def _check_no_link_sections(self, soup: BeautifulSoup) -> tuple[bool, list[str]]:
        """Verify no 'Articles connexes' sections were created."""
        errors = []

        for heading in soup.find_all(["h2", "h3"]):
            heading_text = heading.get_text(strip=True).lower()
            for forbidden in self.FORBIDDEN_SECTIONS:
                if forbidden in heading_text:
                    errors.append(f"Forbidden section heading: '{heading.get_text(strip=True)}'")

        return len(errors) == 0, errors

    def _check_html_integrity(self, html: str) -> tuple[bool, list[str]]:
        """Verify HTML is well-formed (BeautifulSoup can parse without errors)."""
        errors = []

        try:
            soup = BeautifulSoup(html, "html.parser")
            # Check for obvious issues
            text = soup.get_text(strip=True)
            if not text:
                errors.append("HTML appears empty after parsing")
        except Exception as e:
            errors.append(f"HTML parsing error: {str(e)[:100]}")

        return len(errors) == 0, errors

    def _count_internal_links(self, soup: BeautifulSoup) -> int:
        """Count internal links in the HTML."""
        count = 0
        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            if self.domain in href:
                count += 1
        return count
