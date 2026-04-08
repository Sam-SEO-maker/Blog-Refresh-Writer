"""
Cannibalization Detector Module

Détection de la cannibalisation SEO entre les pages du même site.
"""

from typing import Optional

from _shared.core.models import (
    CannibalizationSeverity,
    ResolutionStrategy,
    CannibalizingURL,
    CannibalizationIssue,
    CannibalizationResult,
)
from _shared.core.constants import (
    OVERLAP_VERY_LOW,
    OVERLAP_LOW,
    OVERLAP_MEDIUM,
    OVERLAP_HIGH,
)


class CannibalizationDetector:
    """
    Détecteur de cannibalisation SEO.

    Identifie quand plusieurs pages du même site se concurrencent
    pour les mêmes mots-clés.
    """

    # Seuils pour décision
    POSITION_DIFF_STRONG = 10  # Positions d'écart pour considérer une URL "plus forte"
    TRAFFIC_RATIO_STRONG = 3  # Ratio de trafic pour considérer une URL dominante

    def __init__(self, domain: str):
        """
        Initialise le détecteur.

        Args:
            domain: Domaine du site à analyser
        """
        self.domain = domain

    def detect(
        self,
        target_url: str,
        keywords_data: list[dict],
        sitemap_urls: list[str],
    ) -> CannibalizationResult:
        """
        Détecte les problèmes de cannibalisation pour une URL.

        Args:
            target_url: URL à analyser
            keywords_data: Données de mots-clés GSC pour cette URL
            sitemap_urls: Liste des URLs du sitemap (cache)

        Returns:
            CannibalizationResult avec les issues détectées
        """
        issues = []

        for kw_data in keywords_data:
            keyword = kw_data.get("query", "")
            target_position = kw_data.get("position", 0)
            target_clicks = kw_data.get("clicks", 0)
            target_impressions = kw_data.get("impressions", 0)

            # Ignorer les mots-clés avec peu d'impressions
            if target_impressions < 50:
                continue

            # Chercher d'autres URLs rankant pour ce mot-clé
            competing_urls = self._find_competing_urls(
                keyword=keyword,
                target_url=target_url,
                sitemap_urls=sitemap_urls,
            )

            if competing_urls:
                # Calculer la sévérité
                max_overlap = max(cu.overlap_score for cu in competing_urls)
                severity = self._calculate_severity(max_overlap)

                # Déterminer la stratégie de résolution
                strategy, action_message = self._determine_strategy(
                    target_url=target_url,
                    target_position=target_position,
                    target_clicks=target_clicks,
                    competing_urls=competing_urls,
                )

                issues.append(CannibalizationIssue(
                    keyword=keyword,
                    primary_url=target_url,
                    competing_urls=competing_urls,
                    severity=severity,
                    max_overlap=max_overlap,
                    recommended_strategy=strategy,
                    action_message=action_message,
                ))

        # Déterminer si une action est requise
        has_cannibalization = len(issues) > 0
        most_severe = max(issues, key=lambda i: i.max_overlap) if issues else None

        requires_action = most_severe and most_severe.severity in [
            CannibalizationSeverity.HIGH,
            CannibalizationSeverity.MEDIUM
        ]

        suggested_action = ""
        if requires_action and most_severe:
            suggested_action = most_severe.action_message

        return CannibalizationResult(
            url=target_url,
            has_cannibalization=has_cannibalization,
            issues=issues,
            total_competing_urls=sum(len(i.competing_urls) for i in issues),
            most_severe_issue=most_severe,
            requires_action=requires_action,
            suggested_action=suggested_action,
        )

    def _find_competing_urls(
        self,
        keyword: str,
        target_url: str,
        sitemap_urls: list[str],
    ) -> list[CannibalizingURL]:
        """Trouve les URLs du même site qui rankent pour le même mot-clé via API directe GSC."""
        competing = []

        # Requires direct GSC API - import and use if available
        try:
            from .gsc_analyzer import GSCAnalyzer, GOOGLE_API_AVAILABLE, SERVICE_ACCOUNT_PATH
            if not GOOGLE_API_AVAILABLE or not SERVICE_ACCOUNT_PATH.exists():
                return competing

            from google.oauth2 import service_account as sa
            from googleapiclient.discovery import build as gapi_build

            credentials = sa.Credentials.from_service_account_file(
                str(SERVICE_ACCOUNT_PATH),
                scopes=['https://www.googleapis.com/auth/webmasters.readonly']
            )
            gsc_service = gapi_build('searchconsole', 'v1', credentials=credentials)

            data = gsc_service.searchanalytics().query(
                siteUrl=f"https://{self.domain}/",
                body={
                    "startDate": self._get_date_30_days_ago(),
                    "endDate": self._get_today(),
                    "dimensions": ["page", "query"],
                    "dimensionFilterGroups": [{
                        "filters": [{
                            "dimension": "query",
                            "expression": keyword
                        }]
                    }],
                    "rowLimit": 20
                }
            ).execute()

            for row in data.get("rows", []):
                page_url = row["keys"][0]
                query = row["keys"][1]

                # Ignorer l'URL cible elle-même
                if page_url == target_url:
                    continue

                # Vérifier que c'est une URL du sitemap
                if page_url not in sitemap_urls:
                    continue

                # Calculer le score de chevauchement
                overlap_score = self._calculate_overlap_score(keyword, query)

                competing.append(CannibalizingURL(
                    url=page_url,
                    position=row.get("position", 0),
                    clicks=row.get("clicks", 0),
                    impressions=row.get("impressions", 0),
                    ctr=row.get("ctr", 0) * 100,
                    overlap_score=overlap_score,
                ))

        except Exception as e:
            print(f"Erreur recherche cannibalisation pour '{keyword}': {e}")

        return competing

    def _calculate_overlap_score(self, keyword1: str, keyword2: str) -> float:
        """
        Calcule un score de chevauchement entre deux mots-clés.

        Utilise la similarité de Jaccard sur les tokens.
        """
        tokens1 = set(keyword1.lower().split())
        tokens2 = set(keyword2.lower().split())

        if not tokens1 or not tokens2:
            return 0.0

        intersection = len(tokens1 & tokens2)
        union = len(tokens1 | tokens2)

        return (intersection / union) * 100 if union > 0 else 0.0

    def _calculate_severity(self, overlap: float) -> CannibalizationSeverity:
        """Détermine la sévérité basée sur le score de chevauchement."""
        if overlap >= OVERLAP_HIGH:
            return CannibalizationSeverity.HIGH
        elif overlap >= OVERLAP_MEDIUM:
            return CannibalizationSeverity.MEDIUM
        elif overlap >= OVERLAP_LOW:
            return CannibalizationSeverity.LOW
        else:
            return CannibalizationSeverity.VERY_LOW

    def _determine_strategy(
        self,
        target_url: str,
        target_position: float,
        target_clicks: int,
        competing_urls: list[CannibalizingURL]
    ) -> tuple[ResolutionStrategy, str]:
        """Détermine la meilleure stratégie de résolution."""

        # Trouver l'URL concurrente la plus forte
        strongest_competitor = max(competing_urls, key=lambda c: c.clicks)

        # Si une URL concurrente est significativement plus forte
        if (strongest_competitor.clicks > target_clicks * self.TRAFFIC_RATIO_STRONG and
            strongest_competitor.position < target_position - self.POSITION_DIFF_STRONG):
            return (
                ResolutionStrategy.REDIRECT_301,
                f"Redirect 301 vers {strongest_competitor.url} (plus performante)"
            )

        # Si les URLs ont des performances similaires
        if abs(strongest_competitor.position - target_position) < 5:
            return (
                ResolutionStrategy.DIFFERENTIATE,
                f"Différencier avec longue traîne vs {strongest_competitor.url}"
            )

        # Si notre URL est plus forte, suggérer de merger
        if target_clicks > strongest_competitor.clicks:
            return (
                ResolutionStrategy.MERGE,
                f"Enrichir {target_url} avec le contenu de {strongest_competitor.url}"
            )

        # Par défaut, différencier
        return (
            ResolutionStrategy.DIFFERENTIATE,
            f"Spécialiser sur une variante longue traîne"
        )

    def _get_today(self) -> str:
        """Retourne la date d'aujourd'hui au format YYYY-MM-DD."""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d")

    def _get_date_30_days_ago(self) -> str:
        """Retourne la date d'il y a 30 jours au format YYYY-MM-DD."""
        from datetime import datetime, timedelta
        return (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    def to_dict(self, result: CannibalizationResult) -> dict:
        """Convertit le résultat en dictionnaire pour export."""
        return {
            "url": result.url,
            "has_cannibalization": result.has_cannibalization,
            "requires_action": result.requires_action,
            "suggested_action": result.suggested_action,
            "total_competing_urls": result.total_competing_urls,
            "issues": [
                {
                    "keyword": issue.keyword,
                    "severity": issue.severity.value,
                    "max_overlap": issue.max_overlap,
                    "strategy": issue.recommended_strategy.value,
                    "action": issue.action_message,
                    "competing_urls": [
                        {
                            "url": cu.url,
                            "position": cu.position,
                            "clicks": cu.clicks,
                            "overlap": cu.overlap_score,
                        }
                        for cu in issue.competing_urls
                    ]
                }
                for issue in result.issues
            ],
        }
