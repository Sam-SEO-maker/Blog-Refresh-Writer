"""
Fact Checker Module

3-tier fact-checking system for editorial audit:
- Tier 1: Manual rules (topic-specific dates, entities)
- Tier 2: LLM verification (Claude + optional web search)
- Tier 3: Statistical validation (outdated years, obsolete stats)
"""

from pathlib import Path
from typing import Optional, List, Dict
import json
import re
from datetime import datetime
import logging

from _shared.core.models.audit_models import FactCheckResult

logger = logging.getLogger(__name__)


class FactChecker:
    """
    3-tier fact-checking system for content validation.

    Approach:
    1. Manual rules: Check dates, entities from editorial_rules.json
    2. LLM verification: Use Claude to validate claims (optional)
    3. Statistical validation: Detect outdated years, obsolete stats
    """

    def __init__(self, rules_path: Optional[Path] = None, llm_client=None):
        """
        Initialize fact checker.

        Args:
            rules_path: Path to editorial_rules.json (default: auto-detect)
            llm_client: Optional LLM client for Tier 2 verification
        """
        self.rules_path = rules_path or (
            Path(__file__).parent.parent.parent / "_shared" / "config" / "editorial_rules.json"
        )
        self.llm_client = llm_client
        self.rules = self._load_rules()

    def _load_rules(self) -> dict:
        """Load editorial rules from JSON."""
        if not self.rules_path.exists():
            logger.warning(f"Editorial rules not found: {self.rules_path}")
            return {"topics": {}, "global_rules": {}}

        with self.rules_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def check_content(
        self,
        html_content: str,
        topic: Optional[str] = None,
        use_llm: bool = False
    ) -> List[FactCheckResult]:
        """
        Check content factually across all 3 tiers.

        Args:
            html_content: HTML content to check
            topic: Detected topic (e.g., "parcoursup_2026")
            use_llm: Enable LLM verification (Tier 2)

        Returns:
            List of fact check results
        """
        results = []

        # Tier 1: Manual rules
        if topic and topic in self.rules.get("topics", {}):
            results.extend(self._tier1_manual_rules(html_content, topic))

        # Tier 3: Statistical validation (always run)
        results.extend(self._tier3_statistical_validation(html_content))

        # Tier 2: LLM verification (optional, expensive)
        if use_llm and self.llm_client:
            results.extend(self._tier2_llm_verification(html_content, topic))

        return results

    def _tier1_manual_rules(self, html_content: str, topic: str) -> List[FactCheckResult]:
        """
        Tier 1: Check manual rules (dates, entities) from editorial_rules.json.

        Args:
            html_content: HTML content
            topic: Topic identifier

        Returns:
            List of fact check results
        """
        results = []
        topic_rules = self.rules["topics"].get(topic, {})

        # Check required dates
        for date_rule in topic_rules.get("required_dates", []):
            result = self._check_date(html_content, date_rule)
            if result:
                results.append(result)

        # Check required entities
        for entity in topic_rules.get("required_entities", []):
            result = self._check_entity(html_content, entity)
            if result:
                results.append(result)

        # Check obsolete patterns
        for pattern_rule in topic_rules.get("obsolete_patterns", []):
            result = self._check_obsolete_pattern(html_content, pattern_rule)
            if result:
                results.append(result)

        return results

    def _check_date(self, html_content: str, date_rule: dict) -> Optional[FactCheckResult]:
        """
        Check if required date is present and correct.

        Args:
            html_content: HTML content
            date_rule: {"label": str, "date": "YYYY-MM-DD", "description": str}

        Returns:
            FactCheckResult if issue found, None otherwise
        """
        from bs4 import BeautifulSoup

        expected_date = date_rule["date"]
        label = date_rule["label"]

        # Extract text content
        soup = BeautifulSoup(html_content, "lxml")
        text = soup.get_text(separator=" ", strip=True).lower()

        # Pattern variations for date
        # e.g., "2026-03-12" → "12 mars 2026", "12/03/2026", "mars 2026"
        year, month, day = expected_date.split("-")
        month_names = ["janvier", "février", "mars", "avril", "mai", "juin",
                       "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
        month_name = month_names[int(month) - 1]

        # Check if correct date is present
        patterns = [
            f"{day} {month_name} {year}",
            f"{month_name} {year}",
            f"{day}/{month}/{year}",
            expected_date
        ]

        found = any(pattern.lower() in text for pattern in patterns)

        if not found:
            # Check if wrong year is present (common error)
            wrong_year_pattern = f"{day} {month_name} 202[0-9]"
            if re.search(wrong_year_pattern, text):
                match = re.search(wrong_year_pattern, text)
                return FactCheckResult(
                    checked=True,
                    is_valid=False,
                    error_type="date_mismatch",
                    expected_value=f"{day} {month_name} {year}",
                    found_value=match.group(0) if match else "unknown",
                    context=f"Date pour {label}",
                    severity="critical"
                )

            # Date missing entirely
            return FactCheckResult(
                checked=True,
                is_valid=False,
                error_type="missing_date",
                expected_value=f"{day} {month_name} {year}",
                found_value=None,
                context=f"Date manquante pour {label}",
                severity="high"
            )

        return None  # Date OK

    def _check_entity(self, html_content: str, entity: str) -> Optional[FactCheckResult]:
        """
        Check if required entity is mentioned.

        Args:
            html_content: HTML content
            entity: Required entity (e.g., "CAES")

        Returns:
            FactCheckResult if entity missing, None otherwise
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html_content, "lxml")
        text = soup.get_text(separator=" ", strip=True).lower()

        if entity.lower() not in text:
            return FactCheckResult(
                checked=True,
                is_valid=False,
                error_type="missing_entity",
                expected_value=entity,
                found_value=None,
                context="Entité requise manquante",
                severity="medium"
            )

        return None  # Entity present

    def _check_obsolete_pattern(self, html_content: str, pattern_rule: dict) -> Optional[FactCheckResult]:
        """
        Check for obsolete patterns (e.g., "2025" when it should be "2026").

        Args:
            html_content: HTML content
            pattern_rule: {"pattern": str, "context": str, "replacement": str}

        Returns:
            FactCheckResult if obsolete pattern found, None otherwise
        """
        from bs4 import BeautifulSoup

        pattern = pattern_rule["pattern"]
        context = pattern_rule.get("context", "")
        replacement = pattern_rule.get("replacement", "")

        soup = BeautifulSoup(html_content, "lxml")
        text = soup.get_text(separator=" ", strip=True)

        # Search for pattern
        matches = re.findall(pattern, text)

        if matches and context == "dates":
            # Obsolete year found
            return FactCheckResult(
                checked=True,
                is_valid=False,
                error_type="obsolete_stat",
                expected_value=replacement,
                found_value=pattern,
                context=f"Année obsolète dans contexte {context}",
                severity="high"
            )

        return None

    def _tier3_statistical_validation(self, html_content: str) -> List[FactCheckResult]:
        """
        Tier 3: Statistical validation (outdated years, old stats).

        Args:
            html_content: HTML content

        Returns:
            List of fact check results
        """
        results = []
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html_content, "lxml")
        text = soup.get_text(separator=" ", strip=True)

        current_year = datetime.now().year

        # Find all years mentioned
        year_pattern = r'\b(20[0-2][0-9])\b'
        years_found = re.findall(year_pattern, text)

        for year_str in set(years_found):
            year = int(year_str)
            age = current_year - year

            # Flag stats older than 24 months (configurable)
            max_age_months = self.rules.get("global_rules", {}).get("stat_freshness_months", 24)
            max_age_years = max_age_months // 12

            if age > max_age_years:
                results.append(FactCheckResult(
                    checked=True,
                    is_valid=False,
                    error_type="obsolete_stat",
                    expected_value=f"{current_year} ou {current_year - 1}",
                    found_value=year_str,
                    context=f"Statistique datant de {age} ans",
                    severity="medium" if age <= 3 else "high"
                ))

        return results

    def _tier2_llm_verification(self, html_content: str, topic: Optional[str]) -> List[FactCheckResult]:
        """
        Tier 2: LLM-based fact verification (Claude + web search).

        TODO: Implement LLM verification with Claude API
        Requires: MCP client for web search, Claude API for claim verification

        Args:
            html_content: HTML content
            topic: Topic identifier

        Returns:
            List of fact check results
        """
        results = []

        if not self.llm_client:
            logger.debug("LLM verification skipped (no client)")
            return results

        # TODO: Implement LLM-based verification
        # 1. Extract key claims from content
        # 2. Use Claude to verify each claim
        # 3. Optionally use web search for verification
        # 4. Return fact check results

        logger.warning("Tier 2 LLM verification not implemented yet")
        return results
