"""
Site Models Module

Modèles pour la gestion multi-tenant des sites.
"""

from dataclasses import dataclass


@dataclass
class SiteConfig:
    """Configuration d'un site client."""
    id: str                    # Ex: "enseigna"
    name: str                  # Ex: "Enseigna"
    domain: str                # Ex: "enseigna.fr"
    gsc_property: str          # Ex: "https://enseigna.fr/"
    sheet_id: str              # Google Sheet ID
    credentials: str           # Nom du fichier credentials
    active: bool = True        # Site actif ou non
    sitemap_url: str = ""      # URL du sitemap (vide = auto-découverte)
