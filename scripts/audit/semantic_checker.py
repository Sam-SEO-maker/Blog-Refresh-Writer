"""
Semantic Checker Module — v2.0

Two-axis semantic analysis inspired by YourTextGuru's SOSEO/DSEO model:

1. COVERAGE (SOSEO proxy): How many terms from the semantic field are present?
   - Measures breadth of vocabulary coverage
   - Higher = better (target: 60-80%)

2. DANGER (DSEO proxy): Are any terms repeated excessively?
   - Measures keyword stuffing risk
   - Lower = better (target: < 20%)

Combined verdict:
  - HIGH coverage + LOW danger  → OPTIMAL
  - LOW coverage  + LOW danger  → UNDER_OPTIMIZED
  - HIGH coverage + HIGH danger → OVER_OPTIMIZED
  - LOW coverage  + HIGH danger → POORLY_WRITTEN

Calibrated against YourTextGuru data (March 2026):
  - TOP 3 average (across keywords): SOSEO 60-75%, DSEO 12-20%
  - TOP 10 average: SOSEO 55-70%, DSEO 12-18%
  - Target zone: SOSEO 55-75%, DSEO < 20%
  - Danger zone: SOSEO > 80% or DSEO > 25%
"""

import math
import re
import logging
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


# =========================================================================
# Data Models
# =========================================================================

@dataclass
class TermAlert:
    """A single alert about a problematic term usage."""
    term: str
    alert_type: str  # "high_frequency", "consecutive", "clustering", "phrase_stuffing", "missing_term"
    severity: str  # "info", "warning", "critical"
    count: int = 0
    details: str = ""


@dataclass
class SemanticCheckResult:
    """Result of the two-axis semantic check."""
    coverage_score: float  # 0-100 (SOSEO proxy) — higher = better
    danger_score: float  # 0-100 (DSEO proxy) — lower = better
    verdict: str  # "OPTIMAL", "UNDER_OPTIMIZED", "OVER_OPTIMIZED", "POORLY_WRITTEN"
    alerts: list[TermAlert] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)

    # Backwards-compatible score property (used by orchestrator)
    @property
    def score(self) -> float:
        """Combined score: high = good quality. Kept for backwards compatibility."""
        return round(max(0, self.coverage_score - self.danger_score * 0.5), 1)

    @property
    def is_optimal(self) -> bool:
        return self.verdict == "OPTIMAL"

    @property
    def critical_alerts(self) -> list[TermAlert]:
        return [a for a in self.alerts if a.severity == "critical"]


# =========================================================================
# Semantic Checker v2
# =========================================================================

class SemanticChecker:
    """
    Two-axis semantic checker: Coverage (SOSEO) + Danger (DSEO).

    Usage:
        checker = SemanticChecker()
        result = checker.check(html_content, primary_keyword="cv stage seconde",
                               category="career", subject="orientation")
        print(f"Coverage: {result.coverage_score}%  Danger: {result.danger_score}%")
    """

    # Frequency ceilings per term type (for a ~1800 word article)
    # Calibrated against YTG TOP 3 average across multiple keywords — March 2026
    # Typical TOP 3: SOSEO 60-75%, DSEO 12-20%. Ceilings must prevent > 80% SOSEO.
    CEILING_TOPIC_WORD = 10  # Primary KW components: moderate, use synonyms beyond this
    CEILING_IMPORTANT_TERM = 5  # Top 10 most-used terms: 2-5x is the safe zone
    CEILING_SUPPORTING_TERM = 4  # Other terms: 1-3x is natural, 4 is the ceiling
    REFERENCE_WORD_COUNT = 1800

    # Coverage thresholds
    COVERAGE_OPTIMAL_MIN = 40  # Weighted coverage % for OPTIMAL
    COVERAGE_LOW = 25  # Below this = UNDER_OPTIMIZED

    # Danger thresholds (calibrated: TOP 3 DSEO typically 12-20%)
    DANGER_SAFE_MAX = 18  # Below this = safe (aligns with TOP 3 DSEO ~16%)
    DANGER_HIGH = 30  # Above this = definitely OVER_OPTIMIZED (was 40, too permissive)

    # Phrase stuffing
    MAX_TERMS_PER_SENTENCE = 3

    # French stopwords
    STOPWORDS = frozenset([
        # Determiners / pronouns
        "le", "la", "les", "de", "des", "du", "un", "une", "et", "en", "à",
        "au", "aux", "ce", "ces", "se", "qui", "que", "qu", "ou", "ne", "pas",
        "par", "pour", "sur", "avec", "dans", "est", "sont", "ont", "été",
        "être", "avoir", "fait", "faire", "plus", "tout", "tous", "très",
        "peut", "cette", "son", "ses", "sa", "nous", "vous", "ils", "elles",
        "leur", "leurs", "il", "elle", "on", "même", "aussi", "bien", "si",
        "mais", "car", "donc", "dont", "comme", "entre", "autre", "autres",
        "après", "avant", "chez", "vers", "sans", "sous", "lors", "votre",
        "vos", "nos", "mon", "ma", "mes", "ton", "ta", "tes",
        # Common verbs / adverbs
        "avez", "êtes", "sera", "serait", "peut", "pouvez", "devez",
        "faut", "doit", "dois", "font", "vont", "allez", "aller",
        "permet", "permettre", "donne", "donner", "prendre",
        "mettre", "reste", "partir", "voir", "savoir", "dire",
        "encore", "déjà", "toujours", "jamais", "souvent", "parfois",
        "assez", "plutôt", "surtout", "notamment", "également",
        "vraiment", "simplement", "seulement", "quand", "alors",
        "ainsi", "voici", "voilà", "ici", "cela", "ceci",
        # Common structural words
        "exemple", "point", "partie", "premier", "première", "dernier",
        "dernière", "chaque", "plusieurs", "certains", "certaines",
        "quelques", "beaucoup", "nombre", "temps", "moment", "façon",
        "manière", "type", "forme", "niveau", "chose", "page",
        "titre", "simple", "simples", "éléments", "important",
        "différents", "différentes", "principal", "générale",
        "possible", "nécessaire", "utile", "bonne", "meilleur",
        "grande", "petit", "petite", "nouveau", "nouvelle",
        # Numbers, temporal and spatial words
        "deux", "trois", "quatre", "cinq", "depuis", "pendant",
        "jusqu", "année", "années", "mois", "jours", "semaines",
        "fois", "lieu", "place", "côté", "base", "cadre",
        "sens", "suite", "sein", "terme", "absence",
        "long", "court", "courte", "haut", "haute",
    ])

    def __init__(self, categories_path: Optional[Path] = None):
        if categories_path is None:
            current_file = Path(__file__).resolve()
            project_root = current_file.parent.parent.parent
            categories_path = project_root / "_shared" / "prompts" / "categories"
        self.categories_path = categories_path

    # =================================================================
    # Main Entry Point
    # =================================================================

    def check(
        self,
        html_content: str,
        primary_keyword: Optional[str] = None,
        category: Optional[str] = None,
        subject: Optional[str] = None,
        semantic_field_override: Optional[list[str]] = None,
        competitor_metrics: Optional[dict] = None,
        ytg_targets: Optional[dict] = None,
    ) -> SemanticCheckResult:
        """
        Run two-axis semantic check on generated HTML.

        Args:
            html_content: Generated HTML content
            primary_keyword: Main target keyword (e.g. "cv stage seconde")
            category: Category group for loading semantic field
            subject: Specific subject for filtering semantic field
            semantic_field_override: Explicit term list (e.g. from YTG)
            competitor_metrics: Optional dict for threshold calibration
            ytg_targets: Optional YTG competitor targets dict with keys:
                - top3_soseo (float): SOSEO moyen TOP 3 — cible COVERAGE > cette valeur
                - top3_dseo (float): DSEO moyen TOP 3 — cible DANGER < cette valeur
                Calibre les seuils localement sans muter l'état de l'instance.

        Returns:
            SemanticCheckResult with coverage_score, danger_score, verdict
        """
        text, paragraphs, sections = self._extract_structure(html_content)

        if not text or len(text.split()) < 100:
            return SemanticCheckResult(
                coverage_score=0, danger_score=0,
                verdict="UNDER_OPTIMIZED",
                alerts=[TermAlert("", "content_too_short", "critical",
                                  details="Content too short for analysis")],
                metrics={"word_count": len(text.split()) if text else 0},
            )

        word_count = len(text.split())
        text_lower = text.lower()

        # Build semantic field
        if semantic_field_override:
            semantic_field = [t.lower() for t in semantic_field_override]
        elif category:
            semantic_field = self._load_semantic_field(category, subject)
        else:
            semantic_field = []

        # Identify topic words (components of primary keyword)
        topic_words = set()
        if primary_keyword:
            for w in primary_keyword.lower().split():
                if len(w) > 2 and w not in self.STOPWORDS:
                    topic_words.add(w)

        # Auto-detect high-frequency terms not in semantic field
        auto_terms = self._auto_detect_terms(text_lower, topic_words)

        # All terms to analyze
        all_terms = list(set(semantic_field + auto_terms))
        if primary_keyword:
            kw_lower = primary_keyword.lower()
            if kw_lower not in all_terms:
                all_terms.append(kw_lower)

        # Count occurrences for all terms
        term_counts = {}
        for term in all_terms:
            count = len(re.findall(r"\b" + re.escape(term) + r"\b", text_lower))
            if count > 0:
                term_counts[term] = count

        # Calibrate ceilings to article length
        length_ratio = word_count / self.REFERENCE_WORD_COUNT
        ceiling_topic = max(6, round(self.CEILING_TOPIC_WORD * length_ratio))
        ceiling_important = max(3, round(self.CEILING_IMPORTANT_TERM * length_ratio))
        ceiling_supporting = max(2, round(self.CEILING_SUPPORTING_TERM * length_ratio))

        if competitor_metrics:
            self._apply_competitor_calibration(competitor_metrics)

        # Calibration YTG : seuils locaux (ne mute PAS self — instance partagée)
        coverage_min = self.COVERAGE_OPTIMAL_MIN
        danger_max = self.DANGER_SAFE_MAX
        if ytg_targets:
            top3_soseo = ytg_targets.get("top3_soseo")
            top3_dseo = ytg_targets.get("top3_dseo")
            if top3_soseo:
                # Cibler un SOSEO légèrement supérieur au TOP 3 (-5 pts de marge)
                coverage_min = max(coverage_min, float(top3_soseo) - 5)
            if top3_dseo:
                # Rester en-dessous du DSEO TOP 3
                danger_max = min(danger_max, float(top3_dseo))

        # ---- AXIS 1: COVERAGE (SOSEO proxy) ----
        coverage_score, coverage_details = self._calculate_coverage(
            semantic_field, term_counts, word_count
        )

        # ---- AXIS 2: DANGER (DSEO proxy) ----
        danger_score, danger_alerts = self._calculate_danger(
            term_counts, topic_words, primary_keyword,
            ceiling_topic, ceiling_important, ceiling_supporting
        )

        # Additional danger checks
        stuffing_alerts = self._check_phrase_stuffing(text, list(term_counts.keys()))
        if stuffing_alerts:
            danger_alerts.extend(stuffing_alerts)
            # Add to danger score
            for alert in stuffing_alerts:
                danger_score += min(alert.count * 1.5, 10)

        clustering_alerts = self._check_clustering(sections, list(term_counts.keys()))
        danger_alerts.extend(clustering_alerts)

        danger_score = min(100, danger_score)

        # ---- VERDICT (avec seuils calibrés YTG si fournis) ----
        verdict = self._determine_verdict(
            coverage_score, danger_score,
            coverage_min=coverage_min,
            danger_max=danger_max,
        )

        # ---- ALERTS ----
        all_alerts = coverage_details["missing_alerts"] + danger_alerts

        # ---- METRICS ----
        metrics = {
            "word_count": word_count,
            "semantic_field_size": len(semantic_field),
            "terms_present": coverage_details["terms_present"],
            "terms_missing": coverage_details["terms_missing"],
            "coverage_pct": coverage_details["coverage_pct"],
            "term_counts": dict(sorted(term_counts.items(), key=lambda x: -x[1])[:20]),
            "over_ceiling_terms": coverage_details.get("over_ceiling", 0),
        }

        return SemanticCheckResult(
            coverage_score=round(coverage_score, 1),
            danger_score=round(danger_score, 1),
            verdict=verdict,
            alerts=all_alerts,
            metrics=metrics,
        )

    # =================================================================
    # AXIS 1: Coverage (SOSEO proxy)
    # =================================================================

    def _calculate_coverage(
        self,
        semantic_field: list[str],
        term_counts: dict[str, int],
        word_count: int,
    ) -> tuple[float, dict]:
        """
        Calculate coverage score: how well does the article cover the semantic field?

        Scoring per term (calibrated against YTG SOSEO — March 2026):
          - 0    if absent
          - 0.15 if present 1x (barely counts — YTG penalizes sparse presence)
          - 0.40 if present 2x
          - 0.65 if present 3x
          - 0.85 if present 4x
          - 1.0  if present 5+x (fully optimized for that term)

        Coverage = average of all term scores * 100

        Calibration check: V2 has 34/50 terms, most at 1-2x
          → avg weight ≈ 0.25 → coverage = (34 * 0.25 / 50) * 100 = 17%
          → YTG SOSEO was 24% — close enough for a proxy.
        """
        if not semantic_field:
            unique_terms = len(term_counts)
            expected = max(20, word_count // 60)
            diversity_score = min(100, (unique_terms / expected) * 100)
            return diversity_score, {
                "terms_present": unique_terms,
                "terms_missing": 0,
                "coverage_pct": round(diversity_score, 1),
                "missing_alerts": [],
            }

        term_scores = []
        missing_terms = []
        present_count = 0

        for term in semantic_field:
            count = term_counts.get(term, 0)
            if count == 0:
                term_scores.append(0)
                missing_terms.append(term)
            else:
                present_count += 1
                if count >= 5:
                    term_scores.append(1.0)
                elif count == 4:
                    term_scores.append(0.85)
                elif count == 3:
                    term_scores.append(0.65)
                elif count == 2:
                    term_scores.append(0.40)
                else:
                    term_scores.append(0.15)

        raw_coverage = (sum(term_scores) / len(term_scores) * 100) if term_scores else 0

        # Build missing term alerts (info level, not blocking)
        missing_alerts = []
        if missing_terms and len(missing_terms) <= 15:
            missing_alerts.append(TermAlert(
                term="",
                alert_type="missing_terms",
                severity="info",
                count=len(missing_terms),
                details=f"{len(missing_terms)} semantic field terms absent: {', '.join(missing_terms[:10])}{'...' if len(missing_terms) > 10 else ''}",
            ))

        coverage_pct = (present_count / len(semantic_field) * 100) if semantic_field else 0

        return raw_coverage, {
            "terms_present": present_count,
            "terms_missing": len(missing_terms),
            "coverage_pct": round(coverage_pct, 1),
            "missing_alerts": missing_alerts,
        }

    # =================================================================
    # AXIS 2: Danger (DSEO proxy)
    # =================================================================

    def _calculate_danger(
        self,
        term_counts: dict[str, int],
        topic_words: set[str],
        primary_keyword: Optional[str],
        ceiling_topic: int,
        ceiling_important: int,
        ceiling_supporting: int,
    ) -> tuple[float, list[TermAlert]]:
        """
        Calculate danger score: are any terms repeated excessively?

        A term is "dangerous" if its count exceeds its ceiling.
        Danger score = weighted sum of excess ratios.

        Topic words (part of primary KW) get the highest ceiling.
        Other terms get lower ceilings depending on their frequency rank.
        """
        alerts = []
        danger_points = 0.0
        over_ceiling_count = 0

        # Sort terms by count (highest first) for importance ranking
        sorted_terms = sorted(term_counts.items(), key=lambda x: -x[1])

        for rank, (term, count) in enumerate(sorted_terms):
            # Determine ceiling based on term type
            if primary_keyword and term == primary_keyword.lower():
                ceiling = ceiling_topic
            elif term in topic_words:
                ceiling = ceiling_topic
            elif rank < 10:  # Top 10 most frequent = "important" terms
                ceiling = ceiling_important
            else:
                ceiling = ceiling_supporting

            if count > ceiling:
                over_ceiling_count += 1
                excess_ratio = count / ceiling  # 1.5 = 50% over ceiling
                danger_contribution = (excess_ratio - 1) * 10  # 0.5 excess → 5 points

                severity = "critical" if excess_ratio > 2.0 else "warning"
                alerts.append(TermAlert(
                    term=term,
                    alert_type="high_frequency",
                    severity=severity,
                    count=count,
                    details=f'"{term}" {count}x (ceiling: {ceiling})',
                ))

                danger_points += danger_contribution

        # Normalize: scale so that 3-4 moderately over-ceiling terms ≈ 20 points
        danger_score = min(100, danger_points)

        return danger_score, alerts

    # =================================================================
    # Supplementary Checks (contribute to DSEO)
    # =================================================================

    def _check_phrase_stuffing(
        self, text: str, terms: list[str]
    ) -> list[TermAlert]:
        """Check for sentences overloaded with semantic terms."""
        sentences = re.split(r"[.!?]+", text)
        stuffed = 0

        for sentence in sentences:
            if len(sentence.split()) < 5:
                continue
            sentence_lower = sentence.lower()
            found = sum(
                1 for t in terms
                if re.search(r"\b" + re.escape(t) + r"\b", sentence_lower)
            )
            if found > self.MAX_TERMS_PER_SENTENCE:
                stuffed += 1

        alerts = []
        if stuffed >= 3:
            alerts.append(TermAlert(
                term="",
                alert_type="phrase_stuffing",
                severity="critical" if stuffed >= 8 else "warning",
                count=stuffed,
                details=f"{stuffed} sentences with {self.MAX_TERMS_PER_SENTENCE + 1}+ terms each",
            ))
        return alerts

    def _check_clustering(
        self, sections: list[dict], terms: list[str]
    ) -> list[TermAlert]:
        """Check if terms are concentrated in one section instead of distributed."""
        if len(sections) < 2:
            return []

        alerts = []
        for term in terms:
            section_counts = []
            for section in sections:
                count = len(re.findall(
                    r"\b" + re.escape(term) + r"\b",
                    section["text"].lower(),
                ))
                section_counts.append(count)

            total = sum(section_counts)
            if total < 4:
                continue

            max_in_section = max(section_counts)
            concentration = max_in_section / total if total > 0 else 0

            if concentration > 0.75 and total >= 5:
                idx = section_counts.index(max_in_section)
                alerts.append(TermAlert(
                    term=term,
                    alert_type="clustering",
                    severity="warning",
                    count=max_in_section,
                    details=(
                        f'"{term}" concentrated in '
                        f'"{sections[idx]["heading"][:40]}" '
                        f"({max_in_section}/{total} = {concentration:.0%})"
                    ),
                ))
        return alerts

    # =================================================================
    # Verdict
    # =================================================================

    def _determine_verdict(
        self,
        coverage: float,
        danger: float,
        coverage_min: Optional[float] = None,
        danger_max: Optional[float] = None,
    ) -> str:
        """
        Two-axis verdict:
                        COVERAGE
                    LOW         HIGH
               ┌──────────┬──────────┐
          LOW  │  UNDER   │ OPTIMAL  │
        DANGER │          │          │
               ├──────────┼──────────┤
          HIGH │  POOR    │  OVER    │
               │          │          │
               └──────────┴──────────┘

        Args:
            coverage_min: Seuil de couverture (défaut: COVERAGE_OPTIMAL_MIN).
                Passer une valeur calibrée depuis YTG sans muter l'instance.
            danger_max: Seuil de danger (défaut: DANGER_SAFE_MAX).
                Passer une valeur calibrée depuis YTG sans muter l'instance.
        """
        eff_coverage_min = coverage_min if coverage_min is not None else self.COVERAGE_OPTIMAL_MIN
        eff_danger_max = danger_max if danger_max is not None else self.DANGER_SAFE_MAX

        high_coverage = coverage >= eff_coverage_min
        low_danger = danger <= eff_danger_max

        if high_coverage and low_danger:
            return "OPTIMAL"
        elif high_coverage and not low_danger:
            if danger > self.DANGER_HIGH:
                return "OVER_OPTIMIZED"
            return "SLIGHTLY_OVER"  # Acceptable but watch out
        elif not high_coverage and low_danger:
            return "UNDER_OPTIMIZED"
        else:
            return "POORLY_WRITTEN"

    # =================================================================
    # Text Extraction
    # =================================================================

    def _extract_structure(self, html: str) -> tuple[str, list[str], list[dict]]:
        """Extract text, paragraphs, and sections from HTML."""
        soup = BeautifulSoup(html, "html.parser")

        for tag in soup(["script", "style"]):
            tag.decompose()

        paragraphs = []
        for p in soup.find_all(["p", "li"]):
            t = p.get_text(strip=True)
            if t and len(t) > 20:
                paragraphs.append(t)

        sections = []
        current = {"heading": "introduction", "text": ""}

        for element in soup.descendants:
            if element.name in ("h2", "h3"):
                if current["text"].strip():
                    sections.append(current)
                current = {"heading": element.get_text(strip=True), "text": ""}
            elif element.name in ("p", "li") and element.string:
                current["text"] += " " + element.get_text(strip=True)

        if current["text"].strip():
            sections.append(current)

        full_text = soup.get_text(separator=" ", strip=True)
        return full_text, paragraphs, sections

    # =================================================================
    # Semantic Field Loading
    # =================================================================

    def _load_semantic_field(
        self, category: str, subject: Optional[str] = None
    ) -> list[str]:
        """Load semantic terms from category .md files."""
        terms = []

        category_map = {
            "sport": "sport/sport.md",
            "wellness": "wellness/bien-etre.md",
            "education": "education/sciences-scolaire.md",
            "langues": "education/langues.md",
            "music": "music/musique.md",
            "career": "career/carriere.md",
        }

        filepath = self.categories_path / category_map.get(category, "")
        if not filepath.exists():
            return terms

        try:
            content = filepath.read_text(encoding="utf-8")
            in_vocab = False
            in_semantic_field = False

            for line in content.split("\n"):
                stripped = line.strip()

                if "### Vocabulaire spécifique" in stripped:
                    in_vocab = True
                    in_semantic_field = False
                    continue
                elif "## Champs sémantiques" in stripped:
                    in_semantic_field = True
                    in_vocab = False
                    continue
                elif stripped.startswith("##"):
                    if subject and in_semantic_field:
                        if self._normalize(subject) in self._normalize(stripped):
                            in_semantic_field = True
                        else:
                            in_semantic_field = False
                    elif stripped.startswith("### ") and in_semantic_field:
                        if subject and self._normalize(subject) in self._normalize(stripped):
                            in_semantic_field = True
                        elif not subject:
                            in_semantic_field = True
                    else:
                        in_vocab = False
                        in_semantic_field = False
                    continue

                if (in_vocab or in_semantic_field) and stripped and not stripped.startswith("*"):
                    # Split on comma, then clean sub-terms separated by periods or colons
                    for raw_term in stripped.split(","):
                        # Further split on ". " or " : " to catch multi-concept items
                        sub_parts = re.split(r"\.\s+|\s*:\s+", raw_term)
                        for term in sub_parts:
                            term = term.strip().rstrip(".")
                            term = re.sub(r"\s*\(.*?\)", "", term).strip()
                            # Skip separators, too-short, too-long, and stopwords
                            if (term and len(term) > 2 and len(term) <= 35
                                    and term != "---"
                                    and term.lower() not in self.STOPWORDS):
                                terms.append(term.lower())

        except Exception as e:
            logger.warning(f"Failed to load semantic field for {category}: {e}")

        return list(set(terms))

    # =================================================================
    # Auto-detect terms
    # =================================================================

    def _auto_detect_terms(self, text_lower: str, topic_words: set[str]) -> list[str]:
        """Auto-detect high-frequency non-stopword terms in the text."""
        words = re.findall(r"\b[a-zàâäéèêëïîôùûüç]{4,}\b", text_lower)
        word_counts = Counter(words)

        auto = []
        for word, count in word_counts.most_common(50):
            if count >= 3 and word not in self.STOPWORDS and word not in topic_words:
                auto.append(word)

        return auto

    # =================================================================
    # Calibration
    # =================================================================

    def _apply_competitor_calibration(self, competitor_metrics: dict):
        """Adjust ceilings based on competitor data."""
        avg_density = competitor_metrics.get("avg_density_per_1000")
        if avg_density:
            ratio = avg_density / 50
            self.CEILING_IMPORTANT_TERM = max(3, round(6 * ratio))
            self.CEILING_TOPIC_WORD = max(6, round(12 * ratio))

    # =================================================================
    # Report Generation
    # =================================================================

    def generate_report(self, result: SemanticCheckResult) -> str:
        """Generate a markdown report with both axes."""
        lines = [
            "# Semantic Check Report (v2)",
            "",
            f"**Coverage (SOSEO proxy)**: {result.coverage_score}/100",
            f"**Danger (DSEO proxy)**: {result.danger_score}/100",
            f"**Verdict**: {result.verdict}",
            f"**Word count**: {result.metrics.get('word_count', 'N/A')}",
            f"**Semantic field**: {result.metrics.get('terms_present', '?')}/{result.metrics.get('semantic_field_size', '?')} terms covered ({result.metrics.get('coverage_pct', '?')}%)",
            "",
        ]

        verdict_map = {
            "OPTIMAL": "Coverage and danger are both in the target zone.",
            "UNDER_OPTIMIZED": "Too few semantic terms. Enrich vocabulary breadth.",
            "OVER_OPTIMIZED": "Good coverage but too much repetition. Reduce stuffing.",
            "SLIGHTLY_OVER": "Good coverage, slightly high repetition. Minor adjustments needed.",
            "POORLY_WRITTEN": "Low coverage AND high stuffing. Rewrite recommended.",
        }
        lines.append(f"> {verdict_map.get(result.verdict, '')}")
        lines.append("")

        # Top terms
        tc = result.metrics.get("term_counts", {})
        if tc:
            lines.append("## Top Terms")
            lines.append("")
            lines.append("| Term | Count |")
            lines.append("|------|-------|")
            for term, count in list(tc.items())[:15]:
                lines.append(f"| {term} | {count} |")
            lines.append("")

        # Alerts by type
        if result.alerts:
            danger_alerts = [a for a in result.alerts if a.alert_type != "missing_terms"]
            coverage_alerts = [a for a in result.alerts if a.alert_type == "missing_terms"]

            if danger_alerts:
                lines.append("## Danger Alerts")
                lines.append("")
                for a in sorted(danger_alerts, key=lambda x: (x.severity != "critical",)):
                    icon = "!!" if a.severity == "critical" else "!"
                    lines.append(f"- [{icon}] **{a.alert_type}**: {a.details}")
                lines.append("")

            if coverage_alerts:
                lines.append("## Coverage Gaps")
                lines.append("")
                for a in coverage_alerts:
                    lines.append(f"- {a.details}")
                lines.append("")

        # Recommendations
        lines.append("## Recommendations")
        lines.append("")
        if result.verdict == "UNDER_OPTIMIZED":
            lines.append("- Add more terms from the semantic field (aim for 60%+ coverage)")
            lines.append("- Use each important term 2-4x distributed across sections")
            lines.append("- Check the missing terms list above for quick wins")
        elif result.verdict in ("OVER_OPTIMIZED", "SLIGHTLY_OVER"):
            lines.append("- Reduce most-repeated terms by using synonyms or periphrases")
            lines.append("- Spread term occurrences more evenly across sections")
            lines.append("- Keep coverage high — don't remove terms, reduce repetitions")
        elif result.verdict == "OPTIMAL":
            lines.append("- No action needed. Both coverage and danger are in target range.")
        else:
            lines.append("- Rewrite needed: increase vocabulary breadth while reducing repetition")

        return "\n".join(lines)

    # =================================================================
    # Utilities
    # =================================================================

    @staticmethod
    def _normalize(text: str) -> str:
        """Normalize text for comparison (lowercase, no accents)."""
        text = text.lower()
        nfkd = unicodedata.normalize("NFKD", text)
        return "".join(c for c in nfkd if not unicodedata.combining(c))
