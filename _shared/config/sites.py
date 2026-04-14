"""
Sites Configuration Module

Charge la configuration des sites depuis sites.json et expose SITE_CONFIGS dict.
"""

import json
from pathlib import Path

# Charger sites.json
_config_path = Path(__file__).parent / "sites.json"

with open(_config_path, 'r', encoding='utf-8') as f:
    _sites_data = json.load(f)

# Créer le dict SITE_CONFIGS (indexé par site ID)
SITE_CONFIGS = {
    site['id']: site
    for site in _sites_data['sites']
}

# Exporter également la liste des sites actifs
ACTIVE_SITES = [site['id'] for site in _sites_data['sites'] if site.get('active', True)]

__all__ = ['SITE_CONFIGS', 'ACTIVE_SITES']
