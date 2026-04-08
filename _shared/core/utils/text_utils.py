"""
Text Utils Module

Fonctions utilitaires pour le traitement de texte.
"""

import re
from ..constants import WORDS_PER_MINUTE


def clean_text(text: str) -> str:
    """
    Nettoie le texte (supprime balises HTML, normalise les espaces).

    Args:
        text: Texte à nettoyer

    Returns:
        Texte nettoyé
    """
    # Supprimer les balises HTML
    text = re.sub(r'<[^>]+>', '', text)
    # Normaliser les espaces multiples
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def calculate_word_count(text: str) -> int:
    """
    Calcule le nombre de mots dans un texte.

    Args:
        text: Texte à analyser

    Returns:
        Nombre de mots
    """
    # Nettoyer d'abord le texte
    clean = clean_text(text)
    # Compter les mots (séparés par des espaces)
    words = clean.split()
    return len(words)


def calculate_reading_time(word_count: int, wpm: int = WORDS_PER_MINUTE) -> int:
    """
    Calcule le temps de lecture estimé.

    Args:
        word_count: Nombre de mots
        wpm: Mots par minute (par défaut: WORDS_PER_MINUTE constant)

    Returns:
        Temps de lecture en minutes
    """
    # Minimum 1 minute
    return max(1, word_count // wpm)
