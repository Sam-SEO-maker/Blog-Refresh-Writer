"""
SERP Analyzer Module

Analyse de la SERP via DataforSEO API (MCP ou API directe).
"""

import base64
import json
from pathlib import Path
from typing import Optional

import requests

from _shared.core.models import (
    SERPResult,
    SERPFeature,
    SERPAnalysisResult,
)
from scripts.seo.ahrefs_client import AhrefsClient

# Chemin des credentials DataforSEO (via .env ou fallback)
import os
DATAFORSEO_CREDENTIALS_PATH = Path(os.environ.get("DATAFORSEO_CREDENTIALS_PATH", "~/.credentials/dataforseo/credentials.json")).expanduser()


class SERPAnalyzer:
    """
    Analyseur de SERP via DataforSEO API directe.
    """

    # Patterns pour détecter le format d'un article
    FORMAT_PATTERNS = {
        "listicle": [
            r"^\d+\s+",  # Commence par un nombre
            r"top\s+\d+",
            r"best\s+\d+",
            r"meilleur",
            r"\d+\s+conseils?",
            r"\d+\s+astuces?",
            r"\d+\s+façons?",
        ],
        "guide": [
            r"guide\s+complet",
            r"guide\s+ultime",
            r"comment\s+",
            r"tutoriel",
            r"apprendre\s+à",
        ],
        "comparison": [
            r"vs\.?\s+",
            r"versus",
            r"comparatif",
            r"comparaison",
            r"avis\s+sur",
            r"test\s+",
        ],
        "faq": [
            r"faq",
            r"questions?\s+fréquentes?",
            r"tout\s+savoir",
        ],
        "tool": [
            r"outil",
            r"calculat",
            r"simulat",
            r"générateur",
        ],
    }

    # API DataforSEO endpoints
    API_BASE_URL = "https://api.dataforseo.com/v3"
    SERP_ENDPOINT = "/serp/google/organic/live/advanced"

    def __init__(self, location: str = "France", language: str = "fr"):
        """
        Initialise l'analyseur SERP.

        Args:
            location: Pays pour la recherche
            language: Langue de la recherche
        """
        self.location = location
        self.language = language
        self._api_credentials = None
        self._init_direct_api()
        self._ahrefs = AhrefsClient()

    def _init_direct_api(self):
        """Initialise les credentials pour l'API directe DataforSEO."""
        # 1) Variables d'environnement (.env) — parcours onboarding standard.
        login = os.environ.get("DATAFORSEO_LOGIN", "")
        password = os.environ.get("DATAFORSEO_PASSWORD", "")
        if login and password and login != "your_login_here":
            credentials = f"{login}:{password}"
            self._api_credentials = base64.b64encode(credentials.encode()).decode()
            return
        # 2) Fallback : fichier de credentials JSON.
        if DATAFORSEO_CREDENTIALS_PATH.exists():
            try:
                with open(DATAFORSEO_CREDENTIALS_PATH) as f:
                    creds = json.load(f)
                    # Support structure imbriquée {"dataforseo": {"login": ..., "password": ...}}
                    if "dataforseo" in creds:
                        creds = creds["dataforseo"]
                    login = creds.get("login", "")
                    password = creds.get("password", "")
                    if login and password and login != "VOTRE_LOGIN_DATAFORSEO":
                        # Encoder en Base64 pour Basic Auth
                        credentials = f"{login}:{password}"
                        self._api_credentials = base64.b64encode(credentials.encode()).decode()
            except Exception as e:
                print(f"Erreur chargement credentials DataforSEO: {e}")

    def _fetch_serp_direct(self, keyword: str) -> dict:
        """Récupère les données SERP via API directe DataforSEO."""
        url = f"{self.API_BASE_URL}{self.SERP_ENDPOINT}"

        headers = {
            "Authorization": f"Basic {self._api_credentials}",
            "Content-Type": "application/json"
        }

        # Payload pour l'API DataforSEO
        payload = [{
            "keyword": keyword,
            "location_name": self.location,
            "language_code": self.language,
            "depth": 20,
            "se_domain": "google.fr"
        }]

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            # Validate response structure
            items = data.get("tasks", [{}])[0].get("result", [{}])[0].get("items", [])
            if not items:
                print(f"[SERP] ⚠ DataforSEO returned 0 items for keyword (API OK but empty SERP)")
            return data
        except requests.exceptions.RequestException as e:
            print(f"[SERP] ✗ ERREUR API DataforSEO: {e}")
            raise  # Propager l'erreur au lieu de la masquer

    # DataForSEO Labs endpoints
    RANKED_KEYWORDS_ENDPOINT = "/dataforseo_labs/google/ranked_keywords/live"
    KEYWORD_SUGGESTIONS_ENDPOINT = "/dataforseo_labs/google/keyword_suggestions/live"
    KEYWORD_OVERVIEW_ENDPOINT = "/dataforseo_labs/google/keyword_overview/live"
    RELATED_KEYWORDS_ENDPOINT = "/dataforseo_labs/google/related_keywords/live"

    def discover_main_keyword(self, target_url: str) -> Optional[dict]:
        """
        Découvre le main_keyword pour une URL via DataForSEO ranked_keywords.

        Retourne le keyword avec le plus haut volume de recherche pour lequel
        l'URL se positionne en organique.

        Args:
            target_url: URL complète de la page (ex: https://example.com/page/)

        Returns:
            Dict avec keyword, search_volume, position, ou None si aucun résultat
        """
        if self._api_credentials is None:
            return None

        url = f"{self.API_BASE_URL}{self.RANKED_KEYWORDS_ENDPOINT}"

        headers = {
            "Authorization": f"Basic {self._api_credentials}",
            "Content-Type": "application/json"
        }

        payload = [{
            "target": target_url,
            "location_name": self.location,
            "language_code": self.language,
            "limit": 10,
            "item_types": ["organic"],
            "order_by": ["keyword_data.keyword_info.search_volume,desc"],
            "filters": [["keyword_data.keyword_info.search_volume", ">", 10]]
        }]

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()

            items = data.get("tasks", [{}])[0].get("result", [{}])[0].get("items", [])
            if not items:
                return None

            top = items[0]
            kw_data = top.get("keyword_data", {})
            kw_info = kw_data.get("keyword_info", {})
            serp_item = top.get("ranked_serp_element", {}).get("serp_item", {})

            return {
                "keyword": kw_data.get("keyword", ""),
                "search_volume": kw_info.get("search_volume", 0),
                "position": serp_item.get("rank_group", 0),
                "source": "dataforseo_ranked_keywords"
            }

        except Exception as e:
            print(f"[KW Discovery] DataForSEO ranked_keywords error for {target_url[:60]}: {e}")
            return None

    def suggest_keyword_from_seed(self, seed: str) -> Optional[dict]:
        """
        Trouve le meilleur keyword réel via DataForSEO keyword_suggestions.

        Prend un seed (slug nettoyé ou titre) et retourne la suggestion
        avec le plus haut volume de recherche.

        Args:
            seed: Mot-clé seed (ex: "accessoires guitare", "muscles du dos")

        Returns:
            Dict avec keyword, search_volume, ou None si aucun résultat
        """
        if self._api_credentials is None or not seed:
            return None

        url = f"{self.API_BASE_URL}{self.KEYWORD_SUGGESTIONS_ENDPOINT}"

        headers = {
            "Authorization": f"Basic {self._api_credentials}",
            "Content-Type": "application/json"
        }

        payload = [{
            "keyword": seed,
            "location_name": self.location,
            "language_code": self.language,
            "limit": 10,
            "order_by": ["keyword_info.search_volume,desc"]
        }]

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()

            items = data.get("tasks", [{}])[0].get("result", [{}])[0].get("items", [])
            if not items:
                return None

            top = items[0]
            kw_info = top.get("keyword_info", {})
            volume = kw_info.get("search_volume", 0)

            # Ne retourner que si le keyword a du volume suffisant
            if not volume or volume < 10:
                return None

            return {
                "keyword": top.get("keyword", ""),
                "search_volume": volume,
                "source": "dataforseo_keyword_suggestions"
            }

        except Exception as e:
            print(f"[KW Suggest] DataForSEO keyword_suggestions error for seed '{seed[:40]}': {e}")
            return None

    def check_keyword_volume(self, keyword: str) -> int:
        """
        Vérifie le volume de recherche d'un keyword.

        Priorité : Ahrefs (plus fiable sur les niches FR) → DataForSEO fallback.

        Args:
            keyword: Mot-clé à vérifier

        Returns:
            Volume mensuel (0 si non trouvé ou erreur API)
        """
        if not keyword:
            return 0

        # Priorité 1 : Ahrefs (clickstream panel, volumes FR plus précis)
        if self._ahrefs.available:
            country = "fr" if self.language == "fr" else self.language
            volume = self._ahrefs.get_keyword_volume(keyword, country=country)
            if volume > 0:
                return volume
            # Ahrefs retourne 0 = pas de volume → on fait confiance (pas de fallback)
            return 0

        # Priorité 2 : DataForSEO fallback si Ahrefs non configuré
        if self._api_credentials is None:
            return 0

        url = f"{self.API_BASE_URL}{self.KEYWORD_OVERVIEW_ENDPOINT}"
        headers = {
            "Authorization": f"Basic {self._api_credentials}",
            "Content-Type": "application/json"
        }
        payload = [{
            "keywords": [keyword],
            "location_name": self.location,
            "language_code": self.language,
        }]

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            items = data.get("tasks", [{}])[0].get("result", [{}])[0].get("items", [])
            if not items:
                return 0
            kw_info = items[0].get("keyword_info", {})
            return kw_info.get("search_volume", 0) or 0
        except Exception as e:
            print(f"[KW Volume] DataForSEO keyword_overview error for '{keyword[:40]}': {e}")
            return 0

    def find_broader_keyword(self, seed: str, min_volume: int = 10) -> Optional[dict]:
        """
        Trouve un keyword plus large avec volume suffisant.

        Priorité : Ahrefs matching-terms → DataForSEO related_keywords fallback.

        Utilisé quand ranked_keywords et keyword_suggestions ne trouvent rien
        avec volume suffisant.

        Args:
            seed: Mot-clé seed (slug nettoyé ou keyword trop spécifique)
            min_volume: Volume minimum accepté

        Returns:
            Dict avec keyword, search_volume, source, ou None si aucun résultat
        """
        if not seed:
            return None

        # Priorité 1 : Ahrefs matching-terms (volumes FR plus précis)
        if self._ahrefs.available:
            country = "fr" if self.language == "fr" else self.language
            results = self._ahrefs.get_matching_terms(
                seed, country=country, min_volume=min_volume, limit=10
            )
            if results:
                top = results[0]
                return {
                    "keyword": top["keyword"],
                    "search_volume": top["volume"],
                    "source": "ahrefs_matching_terms"
                }
            return None

        # Priorité 2 : DataForSEO related_keywords fallback si Ahrefs non configuré
        if self._api_credentials is None:
            return None

        url = f"{self.API_BASE_URL}{self.RELATED_KEYWORDS_ENDPOINT}"
        headers = {
            "Authorization": f"Basic {self._api_credentials}",
            "Content-Type": "application/json"
        }
        payload = [{
            "keyword": seed,
            "location_name": self.location,
            "language_code": self.language,
            "limit": 20,
            "order_by": ["keyword_info.search_volume,desc"],
            "filters": [["keyword_info.search_volume", ">=", min_volume]]
        }]

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            items = data.get("tasks", [{}])[0].get("result", [{}])[0].get("items", [])
            if not items:
                return None

            top = items[0]
            kw_data = top.get("keyword_data", {})
            kw_info = kw_data.get("keyword_info", {})
            volume = kw_info.get("search_volume", 0) or 0

            if volume < min_volume:
                return None

            return {
                "keyword": kw_data.get("keyword", ""),
                "search_volume": volume,
                "source": "dataforseo_related_keywords"
            }

        except Exception as e:
            print(f"[KW Broader] DataForSEO related_keywords error for seed '{seed[:40]}': {e}")
            return None

    def analyze(self, keyword: str, our_domain: str) -> SERPAnalysisResult:
        """
        Analyse complète de la SERP pour un mot-clé.

        Args:
            keyword: Mot-clé à analyser
            our_domain: Notre domaine pour détecter notre position

        Returns:
            SERPAnalysisResult avec toutes les données
        """
        # Si pas d'API directe, retourner résultat vide
        if self._api_credentials is None:
            return self._empty_result(keyword)

        try:
            serp_data = self._fetch_serp_direct(keyword)

            # Parser les résultats organiques
            organic_results = self._parse_organic_results(serp_data)

            # Extraire les features SERP
            features = self._parse_serp_features(serp_data)

            # Extraire les PAA
            paa_questions = self._extract_paa(features)

            # Analyser la distribution des formats
            format_distribution = self._analyze_format_distribution(organic_results)
            dominant_format = max(format_distribution, key=format_distribution.get) if format_distribution else "other"

            # Trouver notre position
            our_position = None
            our_url_found = False
            for result in organic_results:
                if our_domain in result.domain:
                    our_position = result.position
                    our_url_found = True
                    break

            return SERPAnalysisResult(
                keyword=keyword,
                organic_results=organic_results,
                features=features,
                dominant_format=dominant_format,
                format_distribution=format_distribution,
                paa_questions=paa_questions,
                our_position=our_position,
                our_url_found=our_url_found,
            )

        except Exception as e:
            print(f"[SERP] ✗ ERREUR SERP pour '{keyword}': {e}")
            import traceback
            traceback.print_exc()
            raise  # Propager pour que l'orchestrator écrive FAILED dans la spreadsheet

    def _parse_organic_results(self, serp_data: dict) -> list[SERPResult]:
        """Parse les résultats organiques de la réponse DataforSEO."""
        results = []

        items = serp_data.get("tasks", [{}])[0].get("result", [{}])[0].get("items", [])

        for item in items:
            if item.get("type") != "organic":
                continue

            title = item.get("title") or ""
            description = item.get("description") or ""

            # Détecter le format
            format_type = self._detect_format(title, description)

            # Extraire les keywords depuis le titre et description
            keywords = self._extract_keywords_from_text(title, description)

            results.append(SERPResult(
                position=item.get("rank_group", 0),
                url=item.get("url", ""),
                title=title,
                description=description,
                domain=item.get("domain", ""),
                format_type=format_type,
                keywords=keywords,
            ))

        return results

    def _parse_serp_features(self, serp_data: dict) -> list[SERPFeature]:
        """Parse les features SERP (PAA, Featured Snippet, etc.)."""
        features = []

        items = serp_data.get("tasks", [{}])[0].get("result", [{}])[0].get("items", [])

        for item in items:
            item_type = item.get("type", "")

            if item_type == "featured_snippet":
                features.append(SERPFeature(
                    feature_type="featured_snippet",
                    content=item.get("description", ""),
                ))
            elif item_type == "people_also_ask":
                questions = []
                for paa_item in item.get("items", []):
                    question = paa_item.get("title", "")
                    if question:
                        questions.append(question)
                features.append(SERPFeature(
                    feature_type="paa",
                    questions=questions,
                ))
            elif item_type == "local_pack":
                features.append(SERPFeature(
                    feature_type="local_pack",
                ))
            elif item_type == "video":
                features.append(SERPFeature(
                    feature_type="video",
                ))

        return features

    def _extract_paa(self, features: list[SERPFeature]) -> list[str]:
        """Extrait les questions PAA."""
        paa_questions = []
        for feature in features:
            if feature.feature_type == "paa":
                paa_questions.extend(feature.questions)
        return paa_questions

    def _detect_format(self, title: str, description: str) -> str:
        """Détecte le format d'un résultat SERP."""
        import re

        combined = f"{title.lower()} {description.lower()}"

        for format_type, patterns in self.FORMAT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, combined, re.I):
                    return format_type

        return "other"

    def _extract_keywords_from_text(self, title: str, description: str) -> list[str]:
        """
        Extrait les mots-clés pertinents depuis le titre et la description.

        Utilise une stratégie simple :
        1. Tokenise le texte
        2. Filtre les stop words français
        3. Priorise les mots du titre
        4. Retourne les N premiers mots uniques
        """
        import re

        # Stop words français courants
        STOP_WORDS_FR = {
            "le", "la", "les", "un", "une", "des", "et", "ou", "mais", "donc",
            "car", "si", "que", "ce", "cet", "cette", "ces", "mon", "ma", "mes",
            "ton", "ta", "tes", "son", "sa", "ses", "notre", "nos", "votre", "vos",
            "leur", "leurs", "je", "tu", "il", "elle", "nous", "vous", "ils",
            "elles", "moi", "toi", "lui", "nous", "vous", "leur", "de", "du",
            "d", "à", "au", "en", "par", "pour", "sur", "avec", "sans", "sous",
            "entre", "vers", "dans", "hors", "devant", "derrière", "dessus",
            "dessous", "dedans", "dehors", "ici", "là", "où", "quand", "comme",
            "combien", "quel", "qui", "comment", "pourquoi", "est", "sont",
            "était", "étaient", "être", "avoir", "a", "as", "ai", "avez", "ont",
            "pas", "plus", "moins", "très", "aussi", "bien", "mal", "bon", "mauvais"
        }

        # Tokeniser titre et description séparément
        title_words = re.findall(r'\b[a-zàâäéèêëïîôöùûüœæ]+\b', title.lower())
        desc_words = re.findall(r'\b[a-zàâäéèêëïîôöùûüœæ]+\b', description.lower())

        # Filtrer les stop words et créer une liste avec priorité au titre
        keywords = []
        seen = set()

        # Ajouter les mots du titre en priorité (exclure les mots courts < 4 caractères)
        for word in title_words:
            if word not in STOP_WORDS_FR and len(word) >= 4 and word not in seen:
                keywords.append(word)
                seen.add(word)
                if len(keywords) >= 10:  # Limiter à 10 keywords
                    break

        # Ajouter les mots de la description
        for word in desc_words:
            if word not in STOP_WORDS_FR and len(word) >= 4 and word not in seen:
                keywords.append(word)
                seen.add(word)
                if len(keywords) >= 10:  # Limiter à 10 keywords
                    break

        return keywords[:10]

    def _analyze_format_distribution(self, results: list[SERPResult]) -> dict[str, int]:
        """Analyse la distribution des formats dans les résultats."""
        distribution = {}

        # Ne considérer que le top 10
        for result in results[:10]:
            format_type = result.format_type
            distribution[format_type] = distribution.get(format_type, 0) + 1

        return distribution

    def check_format_mismatch(
        self,
        current_format: str,
        serp_result: SERPAnalysisResult,
        threshold: float = 0.5
    ) -> tuple[bool, Optional[str]]:
        """
        Vérifie si le format actuel correspond au format dominant de la SERP.

        Args:
            current_format: Format actuel de notre article
            serp_result: Résultat de l'analyse SERP
            threshold: Seuil de dominance (0.5 = 50% des résultats)

        Returns:
            (is_mismatch, recommended_format)
        """
        total = sum(serp_result.format_distribution.values())
        if total == 0:
            return False, None

        dominant_count = serp_result.format_distribution.get(serp_result.dominant_format, 0)
        dominance_ratio = dominant_count / total

        if dominance_ratio >= threshold and current_format != serp_result.dominant_format:
            return True, serp_result.dominant_format

        return False, None

    def _empty_result(self, keyword: str) -> SERPAnalysisResult:
        """Retourne un résultat vide pour les tests."""
        return SERPAnalysisResult(
            keyword=keyword,
            organic_results=[],
            features=[],
            dominant_format="other",
            format_distribution={},
            paa_questions=[],
        )

    def to_dict(self, result: SERPAnalysisResult) -> dict:
        """Convertit le résultat en dictionnaire pour export."""
        return {
            "keyword": result.keyword,
            "our_position": result.our_position,
            "our_url_found": result.our_url_found,
            "dominant_format": result.dominant_format,
            "format_distribution": result.format_distribution,
            "format_mismatch": result.format_mismatch,
            "recommended_format": result.recommended_format,
            "paa_questions": result.paa_questions,
            "top_10_results": [
                {
                    "position": r.position,
                    "url": r.url,
                    "title": r.title,
                    "domain": r.domain,
                    "format_type": r.format_type,
                }
                for r in result.organic_results[:10]
            ],
            "serp_features": [
                {
                    "type": f.feature_type,
                    "questions": f.questions if f.feature_type == "paa" else None,
                }
                for f in result.features
            ],
        }
