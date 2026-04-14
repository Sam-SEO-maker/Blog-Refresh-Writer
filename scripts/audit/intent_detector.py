"""
Intent Detector Module

Détection des shifts d'intention de recherche.
"""

from typing import Optional

from _shared.core.models import (
    SearchIntent,
    ContentFormat,
    IntentSignal,
    IntentShift,
    IntentAnalysisResult,
)


class IntentDetector:
    """
    Détecteur de shifts d'intention de recherche.

    Analyse:
    - L'intention dominante sur la SERP
    - Les changements de format attendu
    - Les variantes de mots-clés en progression/déclin
    """

    # Patterns pour détecter l'intention dans les mots-clés
    INTENT_PATTERNS = {
        SearchIntent.TRANSACTIONAL: [
            r"acheter", r"prix", r"tarif", r"pas cher", r"promo",
            r"commander", r"réserver", r"inscription",
        ],
        SearchIntent.COMMERCIAL: [
            r"meilleur", r"comparatif", r"avis", r"test", r"vs",
            r"alternative", r"top \d+", r"classement",
        ],
        SearchIntent.NAVIGATIONAL: [
            r"^[\w]+\.(?:fr|com|org)$",  # Noms de domaine
            r"connexion", r"login", r"espace client",
        ],
        SearchIntent.INFORMATIONAL: [
            r"comment", r"qu'est-ce", r"pourquoi", r"quand",
            r"définition", r"guide", r"tutoriel", r"apprendre",
        ],
    }

    # Seuils
    INTENT_SHIFT_THRESHOLD = 30  # % de différence pour considérer un shift
    VARIANT_TREND_THRESHOLD = 20  # % de variation pour considérer une tendance

    def __init__(self):
        """Initialise le détecteur d'intention."""
        pass

    def analyze(
        self,
        keyword: str,
        current_content_format: ContentFormat,
        gsc_keywords: list[dict],
        serp_results: list[dict],
        serp_features: list[dict]
    ) -> IntentAnalysisResult:
        """
        Analyse complète de l'intention de recherche.

        Args:
            keyword: Mot-clé principal
            current_content_format: Format actuel de notre contenu
            gsc_keywords: Données de mots-clés GSC
            serp_results: Résultats SERP
            serp_features: Features SERP

        Returns:
            IntentAnalysisResult avec l'analyse complète
        """
        # Détecter l'intention de notre contenu actuel
        current_intent = self._detect_intent_from_keyword(keyword)

        # Détecter l'intention dominante sur la SERP
        serp_intent = self._detect_serp_intent(serp_results, serp_features)

        # Détecter le format dominant sur la SERP
        serp_format = self._detect_serp_format(serp_results)

        # Identifier les variantes en progression/déclin
        rising_variants, declining_variants = self._analyze_keyword_variants(gsc_keywords)

        # Détecter les shifts
        shifts = []
        intent_shift_detected = False
        format_shift_detected = False

        # Shift d'intention
        if current_intent != serp_intent:
            intent_shift = self._create_intent_shift(
                current_intent, serp_intent, serp_results, serp_features
            )
            if intent_shift.confidence >= self.INTENT_SHIFT_THRESHOLD:
                shifts.append(intent_shift)
                intent_shift_detected = True

        # Shift de format
        if current_content_format.value != serp_format.value:
            format_shift_detected = True

        # Générer les recommandations
        recommendations = self._generate_recommendations(
            intent_shift_detected,
            format_shift_detected,
            current_intent,
            serp_intent,
            current_content_format,
            serp_format,
            rising_variants,
        )

        return IntentAnalysisResult(
            keyword=keyword,
            current_content_intent=current_intent,
            current_content_format=current_content_format,
            detected_serp_intent=serp_intent,
            detected_serp_format=serp_format,
            intent_shift_detected=intent_shift_detected,
            format_shift_detected=format_shift_detected,
            shifts=shifts,
            rising_variants=rising_variants,
            declining_variants=declining_variants,
            recommendations=recommendations,
        )

    def _detect_intent_from_keyword(self, keyword: str) -> SearchIntent:
        """Détecte l'intention à partir d'un mot-clé."""
        import re

        keyword_lower = keyword.lower()

        for intent, patterns in self.INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, keyword_lower, re.I):
                    return intent

        # Par défaut, informationnel
        return SearchIntent.INFORMATIONAL

    def _detect_serp_intent(
        self,
        serp_results: list[dict],
        serp_features: list[dict]
    ) -> SearchIntent:
        """Détecte l'intention dominante sur la SERP."""
        intent_scores = {intent: 0.0 for intent in SearchIntent}

        # Analyser les features SERP
        for feature in serp_features:
            feature_type = feature.get("type", "")

            if feature_type == "shopping":
                intent_scores[SearchIntent.TRANSACTIONAL] += 2
            elif feature_type == "local_pack":
                intent_scores[SearchIntent.TRANSACTIONAL] += 1
            elif feature_type == "featured_snippet":
                intent_scores[SearchIntent.INFORMATIONAL] += 2
            elif feature_type == "paa":
                intent_scores[SearchIntent.INFORMATIONAL] += 1
            elif feature_type == "knowledge_panel":
                intent_scores[SearchIntent.NAVIGATIONAL] += 2

        # Analyser les titres des résultats
        for result in serp_results[:10]:
            title = result.get("title", "").lower()

            for intent, patterns in self.INTENT_PATTERNS.items():
                for pattern in patterns:
                    import re
                    if re.search(pattern, title, re.I):
                        intent_scores[intent] += 0.5

        # Retourner l'intention avec le score le plus élevé
        return max(intent_scores, key=intent_scores.get)

    def _detect_serp_format(self, serp_results: list[dict]) -> ContentFormat:
        """Détecte le format dominant sur la SERP."""
        format_counts = {fmt: 0 for fmt in ContentFormat}

        for result in serp_results[:10]:
            format_type = result.get("format_type", "other")

            try:
                fmt = ContentFormat(format_type)
            except ValueError:
                fmt = ContentFormat.OTHER

            format_counts[fmt] += 1

        # Retourner le format le plus fréquent
        return max(format_counts, key=format_counts.get)

    def _analyze_keyword_variants(
        self,
        gsc_keywords: list[dict]
    ) -> tuple[list[dict], list[dict]]:
        """Identifie les variantes de mots-clés en progression/déclin."""
        rising = []
        declining = []

        for kw in gsc_keywords:
            trend = kw.get("trend_clicks") or 0

            if trend > self.VARIANT_TREND_THRESHOLD:
                rising.append({
                    "query": kw.get("query", ""),
                    "trend": trend,
                    "impressions": kw.get("impressions", 0),
                    "position": kw.get("position", 0),
                })
            elif trend < -self.VARIANT_TREND_THRESHOLD:
                declining.append({
                    "query": kw.get("query", ""),
                    "trend": trend,
                    "impressions": kw.get("impressions", 0),
                    "position": kw.get("position", 0),
                })

        # Trier par importance
        rising.sort(key=lambda x: x["impressions"], reverse=True)
        declining.sort(key=lambda x: x["impressions"], reverse=True)

        return rising[:5], declining[:5]

    def _create_intent_shift(
        self,
        from_intent: SearchIntent,
        to_intent: SearchIntent,
        serp_results: list[dict],
        serp_features: list[dict]
    ) -> IntentShift:
        """Crée un objet IntentShift avec les signaux détectés."""
        signals = []

        # Signaux des features SERP
        for feature in serp_features:
            feature_type = feature.get("type", "")
            signals.append(IntentSignal(
                signal_type="serp_feature",
                source=feature_type,
                description=f"Présence de {feature_type} sur la SERP",
                weight=0.3,
            ))

        # Signaux des résultats concurrents
        intent_match_count = 0
        for result in serp_results[:5]:
            title = result.get("title", "").lower()
            if any(p in title for p in self.INTENT_PATTERNS.get(to_intent, [])):
                intent_match_count += 1

        if intent_match_count >= 3:
            signals.append(IntentSignal(
                signal_type="competitor_content",
                source="top_5_results",
                description=f"{intent_match_count}/5 résultats top correspondent à l'intention {to_intent.value}",
                weight=0.5,
            ))

        # Calculer la confiance
        confidence = min(100, sum(s.weight * 100 for s in signals))

        # Générer la recommandation
        recommendation = self._get_shift_recommendation(from_intent, to_intent)

        return IntentShift(
            from_intent=from_intent,
            to_intent=to_intent,
            confidence=confidence,
            signals=signals,
            recommendation=recommendation,
        )

    def _get_shift_recommendation(
        self,
        from_intent: SearchIntent,
        to_intent: SearchIntent
    ) -> str:
        """Génère une recommandation pour le shift d'intention."""
        recommendations = {
            (SearchIntent.INFORMATIONAL, SearchIntent.COMMERCIAL):
                "Ajouter des éléments comparatifs et des avis. L'intention a évolué vers la comparaison.",
            (SearchIntent.INFORMATIONAL, SearchIntent.TRANSACTIONAL):
                "Ajouter des CTAs et des éléments de conversion. L'utilisateur est prêt à agir.",
            (SearchIntent.COMMERCIAL, SearchIntent.TRANSACTIONAL):
                "Simplifier le parcours vers l'action. L'utilisateur a fait son choix.",
            (SearchIntent.COMMERCIAL, SearchIntent.INFORMATIONAL):
                "Enrichir le contenu éducatif. L'utilisateur recherche plus d'informations avant de comparer.",
        }

        key = (from_intent, to_intent)
        return recommendations.get(
            key,
            f"Adapter le contenu de l'intention {from_intent.value} vers {to_intent.value}"
        )

    def _generate_recommendations(
        self,
        intent_shift: bool,
        format_shift: bool,
        current_intent: SearchIntent,
        serp_intent: SearchIntent,
        current_format: ContentFormat,
        serp_format: ContentFormat,
        rising_variants: list[dict]
    ) -> list[str]:
        """Génère les recommandations basées sur l'analyse."""
        recommendations = []

        if intent_shift:
            recommendations.append(
                f"Shift d'intention détecté: {current_intent.value} → {serp_intent.value}. "
                "Adapter le contenu à la nouvelle intention dominante."
            )

        if format_shift:
            recommendations.append(
                f"Format SERP dominant: {serp_format.value}. "
                f"Votre format actuel ({current_format.value}) ne correspond pas. "
                "Envisager une restructuration."
            )

        if rising_variants:
            top_variant = rising_variants[0]
            recommendations.append(
                f"Variante en progression: '{top_variant['query']}' (+{top_variant['trend']:.0f}%). "
                "Considérer une réorientation sémantique vers cette variante."
            )

        if not recommendations:
            recommendations.append(
                "Aucun shift d'intention majeur détecté. "
                "Continuer à optimiser pour l'intention actuelle."
            )

        return recommendations

    def to_dict(self, result: IntentAnalysisResult) -> dict:
        """Convertit le résultat en dictionnaire pour export."""
        return {
            "keyword": result.keyword,
            "current_content_intent": result.current_content_intent.value,
            "current_content_format": result.current_content_format.value,
            "detected_serp_intent": result.detected_serp_intent.value,
            "detected_serp_format": result.detected_serp_format.value,
            "intent_shift_detected": result.intent_shift_detected,
            "format_shift_detected": result.format_shift_detected,
            "shifts": [
                {
                    "from": s.from_intent.value,
                    "to": s.to_intent.value,
                    "confidence": s.confidence,
                    "recommendation": s.recommendation,
                }
                for s in result.shifts
            ],
            "rising_variants": result.rising_variants,
            "declining_variants": result.declining_variants,
            "recommendations": result.recommendations,
        }
