"""
Scoring Utils Module

Fonctions utilitaires pour les calculs de scores, tendances et similarité.
"""

from difflib import SequenceMatcher


def calculate_similarity(text1: str, text2: str) -> float:
    """
    Calcule la similarité entre deux textes (ratio de SequenceMatcher).

    Args:
        text1: Premier texte
        text2: Deuxième texte

    Returns:
        Score de similarité entre 0.0 et 1.0
    """
    return SequenceMatcher(None, text1, text2).ratio()


def calculate_trends(data_30d: dict, data_90d: dict) -> dict:
    """
    Calcule les tendances entre deux périodes.

    Args:
        data_30d: Données sur 30 jours (dict avec keys: clicks, impressions, position)
        data_90d: Données sur 90 jours

    Returns:
        Dict avec les variations en % (clicks_trend, impressions_trend, position_trend)
    """
    trends = {}

    # Variation des clics
    if data_90d.get("clicks", 0) > 0:
        trends["clicks_trend"] = ((data_30d.get("clicks", 0) - data_90d.get("clicks", 0)) / data_90d["clicks"]) * 100
    else:
        trends["clicks_trend"] = 0.0

    # Variation des impressions
    if data_90d.get("impressions", 0) > 0:
        trends["impressions_trend"] = ((data_30d.get("impressions", 0) - data_90d.get("impressions", 0)) / data_90d["impressions"]) * 100
    else:
        trends["impressions_trend"] = 0.0

    # Variation de la position (inversée : une baisse de position est positive)
    trends["position_trend"] = data_90d.get("position", 0) - data_30d.get("position", 0)

    return trends


def calculate_overlap_score(keyword1: str, keyword2: str) -> float:
    """
    Calcule le score de chevauchement entre deux mots-clés.

    Args:
        keyword1: Premier mot-clé
        keyword2: Deuxième mot-clé

    Returns:
        Score de chevauchement entre 0.0 et 100.0
    """
    # Normaliser les mots-clés
    k1 = keyword1.lower().strip()
    k2 = keyword2.lower().strip()

    # Calculer la similarité
    similarity = calculate_similarity(k1, k2)

    # Convertir en score de 0 à 100
    return similarity * 100
