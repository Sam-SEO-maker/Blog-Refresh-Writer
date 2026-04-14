"""
Ghostwriter Models Module

Tous les modèles de données pour le ghostwriting et la réécriture différentielle.
"""

from dataclasses import dataclass, field
from typing import Optional


# =========================================================================
# Modèles Diff Engine
# =========================================================================

@dataclass
class SectionDiff:
    """Différence pour une section."""
    section_id: str  # H2 ou identifiant
    section_title: str
    original_content: str
    modified_content: Optional[str]
    modification_type: str  # 'unchanged', 'modified', 'added', 'removed'
    justification: str
    similarity_ratio: float  # 0-1, 1 = identique


@dataclass
class ContentDiff:
    """Résultat complet du diff."""
    title_diff: Optional[SectionDiff]
    meta_diff: Optional[SectionDiff]
    sections: list[SectionDiff]
    total_sections: int
    modified_sections: int
    unchanged_sections: int
    overall_similarity: float


# =========================================================================
# Modèles Ghostwriter
# =========================================================================

@dataclass
class RewriteResult:
    """Résultat d'une réécriture."""
    url: str
    rewrite_type: str  # 'partial', 'full', 'title_only'
    original_html: str
    new_content: str
    diff: Optional[ContentDiff]

    # Nouveau titre et meta
    new_title: str
    new_meta_description: str

    # Statistiques
    sections_modified: int
    tokens_used: int

    # Validation
    assets_preserved: bool
    validation_errors: list[str] = field(default_factory=list)
