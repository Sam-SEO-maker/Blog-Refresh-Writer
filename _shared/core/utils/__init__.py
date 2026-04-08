"""
Utils Package

Fonctions utilitaires partagées du projet.
"""

# HTML Utils
from .html_utils import (
    extract_images,
    extract_links,
    extract_cta_blocks,
    classify_link,
    find_context_h2,
    clean_html_text,
    identify_featured_image
)

# Text Utils
from .text_utils import (
    clean_text,
    calculate_word_count,
    calculate_reading_time
)

# Scoring Utils
from .scoring_utils import (
    calculate_similarity,
    calculate_trends,
    calculate_overlap_score
)

__all__ = [
    # HTML Utils
    "extract_images",
    "extract_links",
    "extract_cta_blocks",
    "classify_link",
    "find_context_h2",
    "clean_html_text",
    "identify_featured_image",
    # Text Utils
    "clean_text",
    "calculate_word_count",
    "calculate_reading_time",
    # Scoring Utils
    "calculate_similarity",
    "calculate_trends",
    "calculate_overlap_score",
]
