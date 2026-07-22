"""Résolution du bloc `sheets` d'un site (§4bis-A).

Point d'accès unique au layout Sheet externalisé (`sites/{id}/config/site.json`
→ clé `sheets`). Évite de dupliquer des constantes single-site (ENSEIGNA_TABS,
NGL_SHEET, SPREADSHEET_ID hardcodés) dans les scripts.

Retourne toujours un dict (vide si absent) → l'appelant décide de son repli.
"""
from __future__ import annotations

import json
from typing import Optional


def get_sheets_config(site_slug: str) -> dict:
    """Bloc `sheets` de la config du site, ou {} si absent/illisible."""
    try:
        from _shared.core.site_paths import SitePaths
        cfg_path = SitePaths().site_config(site_slug)
        if cfg_path.exists():
            return json.loads(cfg_path.read_text(encoding="utf-8")).get("sheets", {}) or {}
    except Exception:
        pass
    return {}


def get_tab_names(site_slug: str, default: Optional[list[str]] = None) -> list[str]:
    """Noms des onglets Sheet du site (col `name` du bloc `tabs`)."""
    tabs = get_sheets_config(site_slug).get("tabs") or []
    names = [t["name"] for t in tabs if t.get("name")]
    return names or (default or [])


def get_spreadsheet_id(site_slug: str, default: Optional[str] = None) -> Optional[str]:
    """spreadsheet_id du site (bloc `sheets`), avec repli optionnel."""
    return get_sheets_config(site_slug).get("spreadsheet_id") or default


def get_status_col(site_slug: str, default: str = "F") -> str:
    """Colonne de statut du site (bloc `sheets`)."""
    return get_sheets_config(site_slug).get("status_col") or default


def get_primary_tab_name(site_slug: str, default: Optional[str] = None) -> Optional[str]:
    """Premier onglet déclaré (usage single-tab type NGL Superprof)."""
    names = get_tab_names(site_slug)
    return names[0] if names else default
