"""
Decision Models Module

Modèles pour le moteur de décision et la sélection de stratégies.
"""

from dataclasses import dataclass
from typing import Any, Optional

from .enums import RefreshStrategy


@dataclass
class RuleMatch:
    """Une règle qui a été déclenchée."""
    rule_id: str
    rule_name: str
    priority: int
    action: str
    description: str
    conditions_matched: dict[str, Any]


@dataclass
class DecisionResult:
    """Résultat de l'évaluation des règles."""
    url: str
    rules_triggered: list[RuleMatch]
    primary_action: str
    secondary_actions: list[str]
    rewrite_scope: str
    estimated_tokens: int
    prompt_template: str
    subject_prompt: Optional[str]
    requires_approval: bool
    alert_level: str  # 'none', 'low', 'medium', 'high'
    explanation: str


@dataclass
class StrategyConfig:
    """Configuration complète d'une stratégie."""
    strategy: RefreshStrategy
    rewrite_scope: str  # 'none', 'title_meta_only', 'diff_based', 'targeted_sections', 'full_content'
    estimated_tokens: int
    prompt_template: str
    subject_prompt: Optional[str]
    blog_overrides: dict
    preserve_assets: bool
    requires_eeat_enrichment: bool
    guidelines: list[str]
