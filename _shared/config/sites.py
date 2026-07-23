"""
Sites registry access.

Loads _shared/config/sites.json (runtime registry of onboarded sites, gitignored)
and exposes SITE_CONFIGS / ACTIVE_SITES. The file does not exist on a fresh clone
(it is created by `site init` / `notion sync-sites`): fall back to an empty
registry so the CLI can still start (--help, site list, site init...).
"""

import json
from pathlib import Path

_config_path = Path(__file__).parent / "sites.json"

try:
    _sites_data = json.loads(_config_path.read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError):
    _sites_data = {"sites": []}

# "id" = legacy key of sites.json files written before the site_slug rename
SITE_CONFIGS = {
    (site.get('site_slug') or site['id']): site
    for site in _sites_data.get('sites', [])
}

ACTIVE_SITES = [slug for slug, site in SITE_CONFIGS.items() if site.get('active', True)]

__all__ = ['SITE_CONFIGS', 'ACTIVE_SITES']
