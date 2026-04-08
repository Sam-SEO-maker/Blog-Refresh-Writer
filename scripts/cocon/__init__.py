"""
Cocon Module

Module for semantic silo (cocon) management and H2 cannibalization detection.
"""

from .cocon_registry import CoconRegistry
from .cannibalization_detector import CannibalizationDetector
from .similarity_engine import SimilarityEngine
from .sibling_fetcher import SiblingFetcher

__all__ = [
    "CoconRegistry",
    "CannibalizationDetector",
    "SimilarityEngine",
    "SiblingFetcher",
]
