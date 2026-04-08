"""
Tests pour le module decision_engine.
"""

import pytest
import json
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.decision.decision_engine import DecisionEngine, DecisionResult


class TestDecisionEngine:
    """Tests pour DecisionEngine."""

    def setup_method(self):
        """Setup avec règles temporaires."""
        self.rules = {
            "version": "1.0",
            "rules": [
                {
                    "rule_id": "low_ctr",
                    "name": "CTR faible",
                    "conditions": {
                        "performance.ctr_30d": {"operator": "<", "value": 0.02},
                        "performance.impressions_30d": {"operator": ">", "value": 500},
                    },
                    "action": "TITLE_OPTIMIZATION",
                    "priority": 1,
                    "rewrite_scope": "title_meta",
                    "estimated_tokens": 500,
                },
                {
                    "rule_id": "cannibalization",
                    "name": "Cannibalisation",
                    "conditions": {
                        "cannibalization.has_cannibalization": {"operator": "==", "value": True},
                        "cannibalization.severity": {"operator": "==", "value": "high"},
                    },
                    "action": "REDIRECT_301",
                    "priority": 1,
                },
                {
                    "rule_id": "stale_content",
                    "name": "Contenu obsolète",
                    "conditions": {
                        "content.age_months": {"operator": ">", "value": 12},
                    },
                    "action": "PARTIAL_REFRESH",
                    "priority": 3,
                    "rewrite_scope": "diff_based",
                    "estimated_tokens": 2000,
                },
                {
                    "rule_id": "intent_shift",
                    "name": "Shift d'intention",
                    "conditions": {
                        "intent.has_intent_shift": {"operator": "==", "value": True},
                    },
                    "action": "SEMANTIC_REORIENTATION",
                    "priority": 2,
                    "rewrite_scope": "full_content",
                    "estimated_tokens": 4000,
                },
            ],
        }

        # Créer fichier temporaire
        self.temp_file = NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        json.dump(self.rules, self.temp_file)
        self.temp_file.close()

        self.engine = DecisionEngine(Path(self.temp_file.name))

    def teardown_method(self):
        """Cleanup."""
        Path(self.temp_file.name).unlink(missing_ok=True)

    def test_evaluate_low_ctr(self, sample_audit_data):
        """Test règle CTR faible."""
        result = self.engine.evaluate(sample_audit_data)

        assert isinstance(result, DecisionResult)
        assert result.primary_action == "TITLE_OPTIMIZATION"
        assert any(r.rule_id == "low_ctr" for r in result.rules_triggered)

    def test_evaluate_cannibalization(self, sample_audit_data_cannibalization):
        """Test règle cannibalisation."""
        result = self.engine.evaluate(sample_audit_data_cannibalization)

        assert result.primary_action == "REDIRECT_301"
        assert any(r.rule_id == "cannibalization" for r in result.rules_triggered)

    def test_evaluate_intent_shift(self, sample_audit_data_intent_shift):
        """Test règle shift d'intention."""
        result = self.engine.evaluate(sample_audit_data_intent_shift)

        assert result.primary_action == "SEMANTIC_REORIENTATION"
        assert any(r.rule_id == "intent_shift" for r in result.rules_triggered)

    def test_priority_ordering(self):
        """Test que les règles sont ordonnées par priorité."""
        # Données qui déclenchent plusieurs règles
        audit_data = {
            "performance": {
                "ctr_30d": 0.01,
                "impressions_30d": 1000,
            },
            "content": {
                "age_months": 18,
            },
            "cannibalization": {
                "has_cannibalization": False,
            },
            "intent": {
                "has_intent_shift": False,
            },
        }

        result = self.engine.evaluate(audit_data)

        # Low CTR (priorité 1) doit primer sur stale content (priorité 3)
        assert result.primary_action == "TITLE_OPTIMIZATION"

    def test_no_action_when_no_rules_match(self):
        """Test NO_ACTION quand aucune règle ne match."""
        audit_data = {
            "performance": {
                "ctr_30d": 0.05,  # CTR OK
                "impressions_30d": 100,  # Impressions faibles
            },
            "content": {
                "age_months": 3,  # Contenu récent
            },
            "cannibalization": {
                "has_cannibalization": False,
            },
            "intent": {
                "has_intent_shift": False,
            },
        }

        result = self.engine.evaluate(audit_data)
        assert result.primary_action == "NO_ACTION"
        assert len(result.rules_triggered) == 0

    def test_estimated_tokens(self, sample_audit_data):
        """Test estimation des tokens."""
        result = self.engine.evaluate(sample_audit_data)

        # TITLE_OPTIMIZATION = 500 tokens
        assert result.estimated_tokens == 500

    def test_rewrite_scope(self, sample_audit_data):
        """Test scope de réécriture."""
        result = self.engine.evaluate(sample_audit_data)

        # TITLE_OPTIMIZATION → title_meta
        assert result.rewrite_scope == "title_meta"


class TestConditionEvaluation:
    """Tests pour l'évaluation des conditions."""

    def setup_method(self):
        rules = {"version": "1.0", "rules": []}
        self.temp_file = NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        json.dump(rules, self.temp_file)
        self.temp_file.close()
        self.engine = DecisionEngine(Path(self.temp_file.name))

    def teardown_method(self):
        Path(self.temp_file.name).unlink(missing_ok=True)

    def test_operator_less_than(self):
        """Test opérateur <."""
        condition = {"operator": "<", "value": 10}
        assert self.engine._evaluate_condition(5, condition) is True
        assert self.engine._evaluate_condition(10, condition) is False
        assert self.engine._evaluate_condition(15, condition) is False

    def test_operator_greater_than(self):
        """Test opérateur >."""
        condition = {"operator": ">", "value": 10}
        assert self.engine._evaluate_condition(15, condition) is True
        assert self.engine._evaluate_condition(10, condition) is False
        assert self.engine._evaluate_condition(5, condition) is False

    def test_operator_equals(self):
        """Test opérateur ==."""
        condition = {"operator": "==", "value": "high"}
        assert self.engine._evaluate_condition("high", condition) is True
        assert self.engine._evaluate_condition("low", condition) is False

    def test_operator_not_equals(self):
        """Test opérateur !=."""
        condition = {"operator": "!=", "value": "none"}
        assert self.engine._evaluate_condition("high", condition) is True
        assert self.engine._evaluate_condition("none", condition) is False

    def test_operator_in(self):
        """Test opérateur in."""
        condition = {"operator": "in", "value": ["high", "critical"]}
        assert self.engine._evaluate_condition("high", condition) is True
        assert self.engine._evaluate_condition("low", condition) is False

    def test_nested_path_access(self):
        """Test accès chemin imbriqué."""
        data = {
            "performance": {
                "metrics": {
                    "ctr": 0.015,
                },
            },
        }

        value = self.engine._get_nested_value(data, "performance.metrics.ctr")
        assert value == 0.015

    def test_missing_nested_path(self):
        """Test chemin manquant."""
        data = {"performance": {}}

        value = self.engine._get_nested_value(data, "performance.metrics.ctr")
        assert value is None
