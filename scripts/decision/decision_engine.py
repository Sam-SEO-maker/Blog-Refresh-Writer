"""
Decision Engine Module

Évalue les règles de décision et détermine la stratégie de refresh.
"""

import json
import logging
from pathlib import Path
from typing import Any, Optional

from _shared.core.models import RuleMatch, DecisionResult


class DecisionEngine:
    """
    Moteur de décision basé sur les règles.

    Évalue les conditions de chaque règle contre les données d'audit
    et retourne la stratégie optimale.
    """

    def __init__(self, rules_config_path: Optional[Path] = None):
        """
        Initialise le moteur de décision.

        Args:
            rules_config_path: Chemin vers decision_rules.json
        """
        self.logger = logging.getLogger("DecisionEngine")
        self.rules = []
        self.action_strategies = {}
        self.thresholds = {}
        self.evaluation_order = []  # Initialize default empty list

        if rules_config_path and rules_config_path.exists():
            self._load_rules(rules_config_path)

    def _load_rules(self, path: Path):
        """Charge les règles depuis le fichier JSON."""
        with open(path, "r", encoding="utf-8") as f:
            config = json.load(f)

        self.rules = config.get("rules", [])
        self.action_strategies = config.get("action_strategies", {})
        self.thresholds = config.get("thresholds", {})
        self.evaluation_order = config.get("evaluation_order", [])

    def evaluate(self, audit_data: dict) -> DecisionResult:
        """
        Évalue toutes les règles contre les données d'audit.

        Args:
            audit_data: Dictionnaire des données d'audit (de AuditEngine.to_dict())

        Returns:
            DecisionResult avec la stratégie recommandée
        """
        url = audit_data.get("url", "")
        main_keyword = audit_data.get("main_keyword", "")
        self.logger.debug(f"[evaluate] START: url={url}, main_keyword='{main_keyword}'")
        triggered_rules: list[RuleMatch] = []

        # Vérifier la fraîcheur du titre (Règle de Fraîcheur - Date)
        title = audit_data.get("title", "")
        if self._has_stale_year(title):
            self.logger.debug(f"[evaluate] Freshness check: OLD YEAR detected in title '{title}'")
            # Ajouter la règle de TITLE_OPTIMIZATION avec priorité haute
            freshness_rule = RuleMatch(
                rule_id="freshness_date",
                rule_name="Freshness Check - Stale Year",
                priority=1,  # Haute priorité
                action="TITLE_OPTIMIZATION",
                description="Title contains year < 2026",
                conditions_matched={"title_contains_old_year": True}
            )
            triggered_rules.append(freshness_rule)

        # Évaluer chaque règle dans l'ordre de priorité
        rules_to_check = self._get_ordered_rules()
        self.logger.debug(f"[evaluate] Total rules to check: {len(rules_to_check)}, evaluation_order: {self.evaluation_order}")

        for rule in rules_to_check:
            rule_id = rule.get("id", "unknown")
            self.logger.debug(f"[evaluate] Checking rule: {rule_id}")
            if self._evaluate_rule(rule, audit_data):
                match = RuleMatch(
                    rule_id=rule.get("id", ""),
                    rule_name=rule.get("name", ""),
                    priority=rule.get("priority", 5),
                    action=rule.get("action", "NO_ACTION"),
                    description=rule.get("description", ""),
                    conditions_matched=rule.get("conditions", {}),
                )
                triggered_rules.append(match)

        # Déterminer l'action principale (règle de plus haute priorité)
        if triggered_rules:
            # Trier par priorité (1 = haute)
            triggered_rules.sort(key=lambda r: r.priority)
            primary_rule = triggered_rules[0]
            primary_action = primary_rule.action
        else:
            primary_action = "NO_ACTION"

        # Récupérer les détails de la stratégie
        strategy = self.action_strategies.get(primary_action, {})

        # Déterminer les actions secondaires
        secondary_actions = [
            r.action for r in triggered_rules[1:3]
            if r.action != primary_action
        ]

        # Déterminer si approbation requise
        requires_approval = strategy.get("requires_manual_approval", False)
        if any(r.action in ["REDIRECT_301", "EEAT_REWRITE"] for r in triggered_rules):
            requires_approval = True

        # Déterminer le niveau d'alerte
        alert_level = self._determine_alert_level(triggered_rules, audit_data)

        # Générer l'explication
        explanation = self._generate_explanation(triggered_rules, audit_data)

        return DecisionResult(
            url=url,
            rules_triggered=triggered_rules,
            primary_action=primary_action,
            secondary_actions=secondary_actions,
            rewrite_scope=strategy.get("rewrite_scope", "none"),
            estimated_tokens=strategy.get("estimated_tokens", 0),
            prompt_template=strategy.get("prompt", ""),
            subject_prompt=None,  # À déterminer par le dispatcher
            requires_approval=requires_approval,
            alert_level=alert_level,
            explanation=explanation,
        )

    def _has_stale_year(self, title: str) -> bool:
        """
        Détecte si le titre contient une année antérieure à 2026.

        Args:
            title: Titre de l'article

        Returns:
            True si une année < 2026 est détectée
        """
        import re
        if not title:
            return False

        # Chercher les années dans le titre (ex: 2024, 2025, 2023, etc)
        year_pattern = r'\b(20\d{2})\b'
        matches = re.findall(year_pattern, title)

        for year_str in matches:
            year = int(year_str)
            if year < 2026:
                self.logger.debug(f"[_has_stale_year] Found old year '{year}' in title")
                return True

        return False

    def _get_ordered_rules(self) -> list[dict]:
        """Retourne les règles dans l'ordre d'évaluation."""
        if self.evaluation_order:
            ordered = []
            rule_map = {r["id"]: r for r in self.rules}
            for rule_id in self.evaluation_order:
                if rule_id in rule_map:
                    ordered.append(rule_map[rule_id])
            return ordered
        return self.rules

    def _evaluate_rule(self, rule: dict, audit_data: dict) -> bool:
        """
        Évalue si une règle est déclenchée.

        Args:
            rule: Définition de la règle
            audit_data: Données d'audit

        Returns:
            True si toutes les conditions sont remplies
        """
        rule_id = rule.get("id", "unknown")
        conditions = rule.get("conditions", {})

        for condition_key, condition_def in conditions.items():
            value = self._get_audit_value(condition_key, audit_data)

            if not self._check_condition(value, condition_def):
                self.logger.debug(f"[_evaluate_rule] {rule_id}: condition '{condition_key}' FAILED (value='{value}')")
                return False

        self.logger.debug(f"[_evaluate_rule] {rule_id}: ALL CONDITIONS PASSED → TRIGGER")
        return True

    def _get_audit_value(self, key: str, audit_data: dict) -> Any:
        """Récupère une valeur des données d'audit."""
        # Gestion des champs spéciaux
        if key == "has_provided_keyword":
            # Vérifier si un keyword a été fourni (main_keyword non vide)
            main_keyword = audit_data.get("main_keyword", "")
            result = bool(main_keyword and len(main_keyword.strip()) > 0)
            self.logger.debug(f"[_get_audit_value] has_provided_keyword: main_keyword='{main_keyword}' → {result}")
            return result

        # NEW: Handler pour index_diagnostic_scenario
        if key == "index_diagnostic_scenario":
            index_diagnostic_json = audit_data.get("index_diagnostic", "{}")
            try:
                import json
                diagnostic = json.loads(index_diagnostic_json) if isinstance(index_diagnostic_json, str) else index_diagnostic_json
                scenario = diagnostic.get("scenario", "UNKNOWN")
                self.logger.debug(f"[_get_audit_value] index_diagnostic_scenario: {scenario}")
                return scenario
            except Exception as e:
                self.logger.warning(f"[_get_audit_value] Failed to parse index_diagnostic: {e}")
                return "UNKNOWN"

        # Mapping des clés de condition vers les chemins dans audit_data
        value_mappings = {
            "ctr": ("performance", "ctr_30d"),
            "impressions_30d": ("performance", "impressions_30d"),
            "clicks_30d": ("performance", "clicks_30d"),
            "main_keyword_trend": ("performance", "clicks_trend"),
            "variant_keywords_trend": ("performance", "impressions_trend"),
            "position_change_30d": ("performance", "position_trend"),
            "previous_position": ("performance", "avg_position"),
            "traffic_change_90d": ("performance", "clicks_trend"),
            "indexation_status": ("performance", "indexation_status"),
            "cannibalization_severity": ("cannibalization", "severity"),
            "months_since_update": ("freshness_score",),  # Calculé
            "performance_stable": ("performance", "is_declining"),
        }

        # Essayer d'abord le mapping imbriqué (pour full_audit)
        if key in value_mappings:
            path = value_mappings[key]
            value = audit_data
            found = True
            for p in path:
                if isinstance(value, dict):
                    value = value.get(p)
                    if value is None:
                        found = False
                        break
                else:
                    found = False
                    break

            if found and value is not None:
                return value

        # Fallback: chercher directement (pour quick_audit)
        return audit_data.get(key)

    def _check_condition(self, value: Any, condition: dict) -> bool:
        """
        Vérifie si une valeur satisfait une condition.

        Args:
            value: Valeur à vérifier
            condition: Définition de la condition (operator, value)

        Returns:
            True si la condition est satisfaite
        """
        if value is None:
            return False

        operator = condition.get("operator", "==")
        threshold = condition.get("value")

        # Gérer les valeurs spéciales
        if threshold == "serp_dominant_format":
            # Comparaison de format - nécessite contexte supplémentaire
            return True  # Simplifié

        try:
            if operator == "<":
                return float(value) < float(threshold)
            elif operator == "<=":
                return float(value) <= float(threshold)
            elif operator == ">":
                return float(value) > float(threshold)
            elif operator == ">=":
                if isinstance(threshold, str):
                    # Comparaison de sévérité
                    severity_order = ["very_low", "low", "medium", "high"]
                    if value in severity_order and threshold.lower() in severity_order:
                        return severity_order.index(value.lower()) >= severity_order.index(threshold.lower())
                return float(value) >= float(threshold)
            elif operator == "==":
                return str(value).lower() == str(threshold).lower()
            elif operator == "!=":
                return str(value).lower() != str(threshold).lower()
        except (ValueError, TypeError):
            return False

        return False

    def _determine_alert_level(self, rules: list[RuleMatch], audit_data: dict) -> str:
        """Détermine le niveau d'alerte global."""
        if any(r.action in ["EEAT_REWRITE", "REDIRECT_301"] for r in rules):
            return "high"

        if any(r.priority == 1 for r in rules):
            return "high"

        if any(r.priority == 2 for r in rules):
            return "medium"

        if rules:
            return "low"

        return "none"

    def _generate_explanation(self, rules: list[RuleMatch], audit_data: dict) -> str:
        """Génère une explication de la décision."""
        if not rules:
            return "Aucune action nécessaire. L'article performe bien et est à jour."

        explanations = []
        for rule in rules[:3]:  # Top 3 règles
            explanations.append(f"- {rule.rule_name}: {rule.description}")

        performance = audit_data.get("performance", {})

        summary = f"CTR: {performance.get('ctr_30d', 0):.1f}%, "
        summary += f"Position: {performance.get('avg_position', 0):.1f}, "
        summary += f"Impressions: {performance.get('impressions_30d', 0)}"

        return f"Règles déclenchées:\n" + "\n".join(explanations) + f"\n\nMétriques: {summary}"

    def get_strategy_details(self, action: str) -> dict:
        """
        Récupère les détails d'une stratégie.

        Args:
            action: Nom de l'action

        Returns:
            Dictionnaire des détails de la stratégie
        """
        return self.action_strategies.get(action, {})
