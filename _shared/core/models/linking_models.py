"""
Linking Models Module

Data models for automated internal linking injection in semantic cocoons.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LinkMapping:
    """
    A single link injection instruction from the CSV mapping.

    Attributes:
        url_source: Article to modify (where the link will be inserted)
        url_cible: Target article to link to
        mot_cle_principal: Main keyword for anchor text generation
        type_relation: Relationship type: "Parent", "Enfant", or "Soeur"
        h1_cible: H1 title of the target article (auto-fetched if empty)
    """
    url_source: str
    url_cible: str
    mot_cle_principal: str
    type_relation: str  # "Parent" | "Enfant" | "Soeur"
    h1_cible: str = ""


@dataclass
class InjectionPoint:
    """
    Where in the HTML a link should be injected.

    Attributes:
        paragraph_index: 0-based index of the target <p> tag
        context_h2: H2 section containing this point (None if in intro)
        insertion_type: "intro", "after_h2", or "body"
    """
    paragraph_index: int
    context_h2: Optional[str] = None
    insertion_type: str = "body"


@dataclass
class InjectionResult:
    """
    Result of a single link injection attempt.

    Attributes:
        url_cible: Target URL that was linked to
        success: Whether injection succeeded
        anchor_text: The anchor text used
        placement: Description of where the link was placed
        was_duplicate: True if link already existed and was skipped
        error: Error message if injection failed
    """
    url_cible: str
    success: bool
    anchor_text: str
    placement: str  # "Intro" | "H2: [titre]" | "Body"
    was_duplicate: bool = False
    error: Optional[str] = None


@dataclass
class InjectionReport:
    """
    Summary report for all injections on one source article.

    Attributes:
        url_source: URL of the modified article
        site_id: Blog identifier (e.g., "moments-yoga.fr")
        links_injected: Number of links successfully injected
        links_skipped_duplicate: Number of links skipped (already existed)
        links_failed: Number of links that failed to inject
        internal_links_before: Internal link count before injection
        internal_links_after: Internal link count after injection
        results: Detailed results for each link
        validation_passed: Whether post-injection validation passed
    """
    url_source: str
    site_id: str
    links_injected: int = 0
    links_skipped_duplicate: int = 0
    links_failed: int = 0
    internal_links_before: int = 0
    internal_links_after: int = 0
    results: list[InjectionResult] = field(default_factory=list)
    validation_passed: bool = False
