"""
Sites Registry Module

Registry centralisé pour gérer tous les sites clients.
"""

from dataclasses import asdict
from pathlib import Path
from typing import Optional
import json

from _shared.core.models import SiteConfig


class SitesRegistry:
    """
    Registry centralisé des sites clients.

    Gère le chargement, l'ajout, la suppression et la liste des sites.
    Tous les sites sont stockés dans un seul fichier JSON.

    Usage:
        registry = SitesRegistry()

        # Lister tous les sites actifs
        sites = registry.list_active_sites()

        # Récupérer un site spécifique
        site = registry.get_site("enseigna")

        # Ajouter un nouveau site
        registry.add_site(SiteConfig(
            id="nouveau-site",
            name="Nouveau Site",
            domain="nouveau-site.fr",
            gsc_property="https://nouveau-site.fr/",
            sheet_id="1abc...",
            credentials="nouveau-site-sa.json"
        ))
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialise le registry.

        Args:
            config_path: Chemin vers sites.json (par défaut: _shared/config/sites.json)
        """
        if config_path is None:
            # Détecter le chemin racine du projet
            current_file = Path(__file__).resolve()
            project_root = current_file.parent.parent.parent
            config_path = project_root / "_shared" / "config" / "sites.json"

        self.config_path = config_path
        self.sites: dict[str, SiteConfig] = {}
        self._load_sites()

    def _load_sites(self):
        """Charge tous les sites depuis sites.json."""
        if not self.config_path.exists():
            self.sites = {}
            return

        with open(self.config_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for site_data in data.get("sites", []):
            site = SiteConfig(**site_data)
            self.sites[site.id] = site

    def get_site(self, site_id: str) -> Optional[SiteConfig]:
        """
        Récupère la configuration d'un site.

        Args:
            site_id: ID du site (ex: "enseigna")

        Returns:
            SiteConfig ou None si non trouvé
        """
        return self.sites.get(site_id)

    def list_active_sites(self) -> list[SiteConfig]:
        """Liste tous les sites actifs."""
        return [s for s in self.sites.values() if s.active]

    def list_all_sites(self) -> list[SiteConfig]:
        """Liste tous les sites (actifs et inactifs)."""
        return list(self.sites.values())

    def add_site(self, site: SiteConfig) -> bool:
        """
        Ajoute un nouveau site au registry.

        Args:
            site: Configuration du site à ajouter

        Returns:
            True si succès
        """
        self.sites[site.id] = site
        self._save_sites()
        return True

    def remove_site(self, site_id: str) -> bool:
        """
        Supprime un site du registry.

        Args:
            site_id: ID du site à supprimer

        Returns:
            True si succès, False si site non trouvé
        """
        if site_id not in self.sites:
            return False

        del self.sites[site_id]
        self._save_sites()
        return True

    def deactivate_site(self, site_id: str) -> bool:
        """
        Désactive un site (sans le supprimer).

        Args:
            site_id: ID du site à désactiver

        Returns:
            True si succès
        """
        site = self.get_site(site_id)
        if not site:
            return False

        site.active = False
        self._save_sites()
        return True

    def _save_sites(self):
        """Sauvegarde tous les sites dans sites.json."""
        data = {
            "sites": [asdict(site) for site in self.sites.values()]
        }

        # Créer le dossier parent si nécessaire
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
