"""
Client Ahrefs API v3.

Usage:
    client = AhrefsClient()
    volume = client.get_keyword_volume("apprendre le piano", country="fr")
    results = client.get_matching_terms("piano", country="fr", min_volume=10, limit=10)

Configuration:
    Ajouter AHREFS_API_TOKEN dans .env ou ~/.credentials/ahrefs/credentials.json
    Format JSON: {"token": "votre_token"}
"""

import json
import os
from pathlib import Path
from typing import Optional

import requests


AHREFS_CREDENTIALS_PATH = Path(
    os.environ.get("AHREFS_CREDENTIALS_PATH", "~/.credentials/ahrefs/credentials.json")
).expanduser()


class AhrefsClient:
    """
    Client Ahrefs API v3.

    Utilisé pour la validation de volume et la découverte de keywords
    (plus fiable que DataForSEO sur les marchés de niche francophones).
    """

    API_BASE = "https://api.ahrefs.com/v3"

    def __init__(self):
        self._token = self._load_token()

    def _load_token(self) -> Optional[str]:
        """Charge le token Ahrefs depuis .env ou credentials.json."""
        # Priorité 1 : variable d'environnement
        token = os.environ.get("AHREFS_API_TOKEN", "").strip()
        if token:
            return token

        # Priorité 2 : fichier credentials
        if AHREFS_CREDENTIALS_PATH.exists():
            try:
                with open(AHREFS_CREDENTIALS_PATH) as f:
                    data = json.load(f)
                    token = data.get("token", "").strip()
                    if token:
                        return token
            except Exception as e:
                print(f"[Ahrefs] Erreur chargement credentials: {e}")

        return None

    @property
    def available(self) -> bool:
        """True si le client est configuré avec un token valide."""
        return bool(self._token)

    def _get(self, endpoint: str, params: dict) -> Optional[dict]:
        """Effectue une requête GET sur l'API Ahrefs."""
        if not self._token:
            return None

        url = f"{self.API_BASE}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/json",
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 401:
                print("[Ahrefs] Token invalide ou expiré")
            elif e.response is not None and e.response.status_code == 429:
                print("[Ahrefs] Rate limit atteint")
            else:
                print(f"[Ahrefs] HTTP {e.response.status_code if e.response else '?'}: {e}")
            return None
        except Exception as e:
            print(f"[Ahrefs] Erreur API: {e}")
            return None

    def get_keyword_volume(self, keyword: str, country: str = "fr") -> int:
        """
        Retourne le volume mensuel d'un keyword via Ahrefs Keywords Explorer.

        Args:
            keyword: Le mot-clé à vérifier
            country: Code pays (ex: "fr", "us")

        Returns:
            Volume mensuel, 0 si non trouvé ou erreur
        """
        if not self._token or not keyword:
            return 0

        data = self._get("/keywords-explorer/overview", {
            "country": country,
            "select": "volume,keyword",
            "keywords[]": keyword,
        })

        if not data:
            return 0

        keywords_list = data.get("keywords", [])
        if not keywords_list:
            return 0

        return keywords_list[0].get("volume", 0) or 0

    def get_matching_terms(
        self,
        seed: str,
        country: str = "fr",
        min_volume: int = 10,
        limit: int = 10,
    ) -> list[dict]:
        """
        Retourne les keywords correspondant à un seed, triés par volume décroissant.

        Args:
            seed: Mot-clé seed (ex: "capodastre guitare")
            country: Code pays
            min_volume: Volume minimum accepté
            limit: Nombre max de résultats

        Returns:
            Liste de dicts [{keyword, volume}, ...]
        """
        if not self._token or not seed:
            return []

        data = self._get("/keywords-explorer/matching-terms", {
            "country": country,
            "term": seed,
            "select": "volume,keyword",
            "limit": limit,
            "order_by": "volume:desc",
            "volume_min": min_volume,
        })

        if not data:
            return []

        keywords_list = data.get("keywords", [])
        results = []
        for item in keywords_list:
            kw = item.get("keyword", "")
            vol = item.get("volume", 0) or 0
            if kw and vol >= min_volume:
                results.append({"keyword": kw, "volume": vol})

        return results
