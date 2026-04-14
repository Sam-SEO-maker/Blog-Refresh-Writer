"""
SuperTeamSEO WordPress API Client.

Récupère le contenu HTML des articles via l'API REST SuperTeamSEO.
"""

import logging
import os
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

BASE_URL = "https://www.superteamseo.com/wp-json/sp/v1"


class STSEOClient:
    """Client pour l'API SuperTeamSEO (WordPress REST)."""

    def __init__(self, email: Optional[str] = None, password: Optional[str] = None):
        self.email = email or os.environ.get("STSEO_EMAIL", "")
        self.password = password or os.environ.get("STSEO_PASSWORD", "")
        self.session = requests.Session()
        self.session.auth = (self.email, self.password)
        self.session.headers.update({
            "Accept": "application/json",
        })

        if not self.email or not self.password:
            logger.warning("[STSEO] Credentials manquants (STSEO_EMAIL / STSEO_PASSWORD)")

    def get_post_content_by_link(self, link: str, timeout: int = 30) -> Optional[dict]:
        """
        Récupère le contenu d'un article à partir de son URL.

        Args:
            link: URL de l'article (ex: https://mymusicteacher.fr/accessoire-guitare-cable-jack/)
            timeout: Timeout en secondes

        Returns:
            dict avec le contenu de l'article, ou None en cas d'erreur
        """
        url = f"{BASE_URL}/get_pbn_post_content_by_link"
        params = {"link": link}

        try:
            resp = self.session.get(url, params=params, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            logger.info(f"[STSEO] Contenu récupéré pour {link}")
            return data
        except requests.exceptions.HTTPError as e:
            logger.error(f"[STSEO] HTTP {resp.status_code} pour {link}: {e}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"[STSEO] Erreur réseau pour {link}: {e}")
            return None

    def get_website_mindmaps(self, pbn_website_id: int, timeout: int = 30) -> Optional[dict]:
        """
        Récupère les mindmaps d'un PBN Website.

        Args:
            pbn_website_id: ID du PBN Website (ex: 910)
            timeout: Timeout en secondes

        Returns:
            dict avec website, mindmaps[], ou None en cas d'erreur
        """
        url = f"{BASE_URL}/get_pbn_website_mindmaps"
        params = {"pbn_website_id": pbn_website_id}

        try:
            resp = self.session.get(url, params=params, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            count = len(data.get("mindmaps", []))
            logger.info(f"[STSEO] {count} mindmaps pour website_id={pbn_website_id}")
            return data
        except requests.exceptions.HTTPError as e:
            logger.error(f"[STSEO] HTTP {resp.status_code} pour website_id={pbn_website_id}: {e}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"[STSEO] Erreur réseau pour website_id={pbn_website_id}: {e}")
            return None
