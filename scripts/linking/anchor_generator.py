"""
Anchor Generator Module

Generates contextual, varied anchor text for internal link injection.
"""

import logging
import random
from typing import Optional

from _shared.core.models.linking_models import LinkMapping

logger = logging.getLogger(__name__)


class AnchorGenerator:
    """
    Generates contextual anchor text for internal links.

    Strategies:
    - Exact keyword anchor
    - Partial keyword (2-3 significant words)
    - H1-based anchor
    - Contextual phrases by relation type

    Rules:
    - Never use "cliquez ici", "en savoir plus", etc.
    - Vary anchors within the same article
    """

    FORBIDDEN_PATTERNS = [
        "cliquez ici",
        "en savoir plus",
        "voir cet article",
        "cet article",
        "lire la suite",
        "plus d'infos",
        "ici",
    ]

    # Contextual sentence templates per relation type
    TEMPLATES = {
        "Enfant": [
            'Pour une vision d\'ensemble, retrouvez {anchor}.',
            'Consultez {anchor} pour un panorama complet du sujet.',
        ],
        "Parent": [
            'Pour approfondir ce point, consultez {anchor}.',
            'Notre article dédié à {anchor} détaille cette question.',
        ],
        "Soeur": [
            'Découvrez également {anchor} pour compléter cette approche.',
            'Vous pourriez aussi vous intéresser à {anchor}.',
            'Dans une perspective complémentaire, explorez {anchor}.',
        ],
    }

    def __init__(self):
        self._used_anchors: set[str] = set()

    def reset(self):
        """Reset used anchors tracking (call between source articles)."""
        self._used_anchors.clear()

    def generate_anchor(self, mapping: LinkMapping) -> str:
        """
        Generate appropriate anchor text for a link.

        Args:
            mapping: LinkMapping with keyword, relation type, and optional H1

        Returns:
            Anchor text string
        """
        candidates = self._build_candidates(mapping)

        # Filter out already-used anchors for diversity
        available = [a for a in candidates if a.lower() not in self._used_anchors]
        if not available:
            available = candidates  # Fall back to all candidates if all used

        anchor = available[0]
        self._used_anchors.add(anchor.lower())

        logger.debug(f"[AnchorGenerator] Generated anchor: '{anchor}' for {mapping.url_cible[:50]}")
        return anchor

    def generate_sentence(self, mapping: LinkMapping, anchor: str) -> str:
        """
        Generate a complete injection sentence with anchor link.

        Args:
            mapping: LinkMapping with relation type
            anchor: Pre-generated anchor text

        Returns:
            Complete sentence with <a> tag
        """
        link_tag = f'<a href="{mapping.url_cible}" title="{anchor}">{anchor}</a>'

        templates = self.TEMPLATES.get(mapping.type_relation, self.TEMPLATES["Soeur"])
        template = random.choice(templates)

        sentence = template.format(anchor=link_tag)
        return sentence

    def _build_candidates(self, mapping: LinkMapping) -> list[str]:
        """
        Build a ranked list of anchor text candidates.

        Order: exact keyword > H1 title > partial keyword
        """
        candidates = []
        keyword = mapping.mot_cle_principal.strip()
        h1 = mapping.h1_cible.strip()

        # Strategy 1: Exact keyword
        if keyword:
            candidates.append(keyword)

        # Strategy 2: H1 title (if available and different from keyword)
        if h1 and h1.lower() != keyword.lower():
            candidates.append(h1)

        # Strategy 3: Partial keyword (first 2-3 significant words)
        if keyword:
            partial = self._extract_partial(keyword)
            if partial and partial.lower() != keyword.lower():
                candidates.append(partial)

        # Strategy 4: Contextual prefix + keyword
        if keyword and mapping.type_relation == "Enfant":
            candidates.append(f"notre guide sur {keyword}")
        elif keyword and mapping.type_relation == "Soeur":
            candidates.append(f"les {keyword}")

        # Filter forbidden anchors
        candidates = [c for c in candidates if not self._is_forbidden(c)]

        if not candidates:
            candidates = [keyword or h1 or "cet article"]

        return candidates

    def _extract_partial(self, keyword: str) -> str:
        """
        Extract 2-3 significant words from a keyword phrase.

        Removes common French stopwords and keeps substantive terms.
        """
        stopwords = {
            "le", "la", "les", "un", "une", "des", "de", "du", "à", "au", "aux",
            "pour", "par", "sur", "dans", "avec", "en", "et", "ou", "que", "qui",
            "est", "sont", "son", "sa", "ses", "ce", "cette", "ces",
        }

        words = keyword.lower().split()
        significant = [w for w in words if w not in stopwords and len(w) > 2]

        if len(significant) >= 2:
            return " ".join(significant[:3])
        return ""

    def _is_forbidden(self, anchor: str) -> bool:
        """Check if anchor matches forbidden patterns."""
        anchor_lower = anchor.lower().strip()
        return any(forbidden in anchor_lower for forbidden in self.FORBIDDEN_PATTERNS)
