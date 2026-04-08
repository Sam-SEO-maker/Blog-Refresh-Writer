"""
Action Formatter Module

Génère les descriptions d'actions pour le spreadsheet :
- "To Do" : Action claire et actionnable pour l'utilisateur
- "recommended_actions" : Détails techniques des changements automatiques
"""

from datetime import datetime
from typing import List, Dict, Optional


def map_action_to_blogpost(primary_action: str) -> str:
    """
    Map DecisionEngine primary_action → action_blogpost (4 values for single-sheet).

    Règles de mapping :
    - NO ACTION : article performe bien, user intent OK, positionné SERP
    - PARTIAL REFRESH : mise à jour données statistiques et dates uniquement
    - REFRESH TITLES : optimiser titre (pas de KW, cannibalisation, date antérieure 2025)
    - FULL REFRESH : réécriture complète (performance faible, user intent changé)

    Args:
        primary_action: Action from DecisionEngine

    Returns:
        Simplifié action_blogpost value (4 options)
    """
    mapping = {
        # No action
        "NO_ACTION": "NO ACTION",
        "DATA_COLLECTION_REQUIRED": "NO ACTION",

        # Partial refresh (update stats/dates only)
        "PARTIAL_REFRESH": "PARTIAL REFRESH",

        # Refresh titles (H1/H2 optimization)
        "TITLE_OPTIMIZATION": "REFRESH TITLES",

        # Full refresh (complete rewrite)
        "SEMANTIC_REORIENTATION": "FULL REFRESH",
        "FORMAT_ADAPTATION": "FULL REFRESH",
        "EEAT_REWRITE": "FULL REFRESH",
        "FULL_REFRESH": "FULL REFRESH",
        "CONTENT_GAP_ANALYSIS": "FULL REFRESH",
        "LONG_TAIL_SPECIALIZATION": "FULL REFRESH",

        # Special actions (manual intervention)
        "REDIRECT_301": "NO ACTION",  # Requires manual intervention
        "SUGGEST_301": "NO ACTION",
    }
    return mapping.get(primary_action, "NO ACTION")


def generate_to_do_action(decision_result) -> str:
    """
    LEGACY: Génère l'action à mener depuis le DecisionResult (ancienne API).

    DEPRECATED: Use map_action_to_blogpost() instead for v2.0 single-sheet architecture.

    Cette colonne était destinée à l'utilisateur dans l'ancienne architecture multi-sheet.
    Dans la v2.0, seule la colonne action_blogpost (4 valeurs) est utilisée.

    Args:
        decision_result: Objet DecisionResult avec primary_action et autres données

    Returns:
        Texte clair et actionnable (ancien format)
    """
    # Mapping des actions vers les catégories de dropdown
    action_map = {
        "NO_ACTION": "Aucune action nécessaire",
        "TITLE_OPTIMIZATION": "Optimiser titres",

        # Tous les types de réécriture partielle
        "PARTIAL_REFRESH": "Réécriture partielle",
        "SEMANTIC_REORIENTATION": "Réécriture partielle",
        "FORMAT_ADAPTATION": "Réécriture partielle",
        "EEAT_REWRITE": "Réécriture partielle",
        "LONG_TAIL_SPECIALIZATION": "Réécriture partielle",
        "CONTENT_GAP_ANALYSIS": "Réécriture totale",
        "DATA_COLLECTION_REQUIRED": "En attente de données",

        # Réécriture totale
        "FULL_REFRESH": "Réécriture totale",

        # Redirections
        "REDIRECT_301": "Redirection 301",
        "SUGGEST_301": "Redirection 301",
    }

    # Support pour à la fois dict et objet
    if isinstance(decision_result, dict):
        primary_action = decision_result.get('primary_action', 'NO_ACTION')
    else:
        primary_action = getattr(decision_result, 'primary_action', 'NO_ACTION')

    return action_map.get(primary_action, "Réécriture partielle")


def generate_recommended_actions(
    year_changes: Optional[List[Dict]] = None,
    decision_result=None,
    audit_data: Optional[Dict] = None
) -> str:
    """
    LEGACY: Génère les détails techniques des actions (ancienne colonne recommended_actions).

    DEPRECATED: This function is not used in v2.0 single-sheet architecture.
    The new architecture uses only action_blogpost (4 values) instead of to_do + recommended_actions.

    Conservé pour backwards compatibility pendant la transition migration.

    Args:
        year_changes: Liste des changements d'années effectués
        decision_result: Objet DecisionResult avec primary_action
        audit_data: Dictionnaire des données d'audit

    Returns:
        Détails techniques formatés (ancien format)
    """
    if not any([year_changes, decision_result, audit_data]):
        return "Aucune action automatique effectuée"

    actions = []
    current_year = datetime.now().year

    # 1. Actions automatiques effectuées (mises à jour d'années)
    if year_changes:
        count = len(year_changes)
        actions.append(f"✓ {count} date(s) mise à jour automatiquement (→{current_year})")

    # 2. Stratégie recommandée
    if decision_result:
        # Support pour à la fois dict et objet
        if isinstance(decision_result, dict):
            primary_action = decision_result.get('primary_action')
        else:
            primary_action = getattr(decision_result, 'primary_action', None)

        if primary_action and primary_action != "NO_ACTION":
            actions.append(f"→ Stratégie: {primary_action}")

    # 3. Alertes critiques
    if audit_data:
        # Alerte cannibalisation
        canib_severity = audit_data.get("cannibalization_severity")
        if canib_severity and canib_severity.lower() == "high":
            actions.append("⚠️ ALERTE: Cannibalisation sévère")

        # Alerte CTR faible
        ctr = audit_data.get("ctr_30d", 0)
        impressions = audit_data.get("impressions_30d", 0)
        if ctr and impressions and ctr < 2.0 and impressions > 500:
            actions.append("⚠️ CTR faible malgré visibilité")

        # Alerte position dégradée
        position = audit_data.get("avg_position")
        if position and position > 30:
            actions.append("⚠️ Position faible (> pos 30)")

        # Alerte trafic en baisse
        kw_trend = audit_data.get("keyword_trend", "")
        if "baisse" in str(kw_trend).lower():
            actions.append("⚠️ Tendance mots-clés en baisse")

    # Retourner le résumé formaté
    if actions:
        return " | ".join(actions)
    else:
        return "Aucune action automatique effectuée"


def format_actions_for_spreadsheet(
    year_changes: Optional[List[Dict]] = None,
    decision_result=None,
    audit_data: Optional[Dict] = None
) -> Dict[str, str]:
    """
    LEGACY: Génère les deux colonnes d'actions pour le spreadsheet (ancien format multi-sheet).

    DEPRECATED: This function is not used in v2.0 single-sheet architecture.
    Use map_action_to_blogpost() instead.

    Conservé pour backwards compatibility.

    Args:
        year_changes: Liste des changements d'années
        decision_result: Objet DecisionResult
        audit_data: Dictionnaire d'audit

    Returns:
        Dictionnaire avec les deux colonnes (ancien format)
    """
    return {
        'to_do': generate_to_do_action(decision_result),
        'recommended_actions': generate_recommended_actions(
            year_changes,
            decision_result,
            audit_data
        )
    }


# Utilisation simple
if __name__ == "__main__":
    from collections import namedtuple

    # Simuler un DecisionResult pour test
    DecisionResult = namedtuple('DecisionResult', ['primary_action'])
    decision = DecisionResult(primary_action="PARTIAL_REFRESH")

    # Simuler des changements d'années
    year_changes = [
        {'original': '2025', 'replacement': '2026'},
        {'original': '2025', 'replacement': '2026'},
        {'original': '2025', 'replacement': '2026'},
    ]

    # Simuler des données d'audit
    audit_data = {
        'ctr_30d': 1.5,
        'impressions_30d': 750,
        'cannibalization_severity': 'low'
    }

    # Générer les actions
    to_do = generate_to_do_action(decision)
    recommended = generate_recommended_actions(year_changes, decision, audit_data)

    print(f"To Do: {to_do}")
    print(f"Recommended Actions: {recommended}")
