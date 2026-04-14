"""
Cocon Models Module

Data models for semantic silo (cocon) management and cannibalization detection.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SiblingArticle:
    """
    Metadata for a sibling article in the semantic cocon.

    Attributes:
        url: Full URL of the sibling article
        h1: Main title (H1) of the sibling
        main_keyword: Main keyword targeted by the sibling
        context_h2_from_parent: H2 from parent article that links to this child (optional)
    """
    url: str
    h1: str
    main_keyword: str
    context_h2_from_parent: Optional[str] = None


@dataclass
class CoconRegistryData:
    """
    Complete structure of a semantic cocon for an article.

    Attributes:
        parent_url: URL of the parent article (if exists)
        parent_h1: H1 title of the parent article
        current_url: URL of the current article being processed
        current_h1: H1 title of the current article
        siblings: List of sibling articles (other children in the same cocon)
    """
    parent_url: Optional[str] = None
    parent_h1: Optional[str] = None
    current_url: str = ""
    current_h1: str = ""
    siblings: list[SiblingArticle] = field(default_factory=list)


@dataclass
class CannibalizationMatch:
    """
    Detected H2 cannibalization with a sibling article.

    Attributes:
        current_h2: H2 heading in the current article
        sibling_h1: H1 heading of the sibling article
        sibling_url: URL of the cannibalizing sibling
        similarity_score: Similarity score (0.0-1.0)
        match_type: Type of match ('exact', 'semantic', 'keyword')
    """
    current_h2: str
    sibling_h1: str
    sibling_url: str
    similarity_score: float
    match_type: str  # 'exact', 'semantic', 'keyword'


@dataclass
class CannibalizationReport:
    """
    Complete cannibalization analysis report for an article.

    Attributes:
        current_url: URL of the analyzed article
        h2_analyzed_count: Number of H2 headings analyzed
        matches: List of detected cannibalization matches
        blacklist_h2_topics: List of H2 topics to blacklist in the prompt
    """
    current_url: str
    h2_analyzed_count: int
    matches: list[CannibalizationMatch] = field(default_factory=list)
    blacklist_h2_topics: list[str] = field(default_factory=list)
