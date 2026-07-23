"""
Constants Module

Toutes les constantes globales du projet centralisées ici.
"""

# =========================================================================
# Domaines et URLs
# =========================================================================

# Liste LEGACY (fallback uniquement). La liste canonique (~750 domaines) vit dans
# `.claude/skills/source-research/references/blacklisted-domains.md`, chargée par
# `_shared/core/blacklist.py` (load_blacklist_domains / is_blacklisted_url).
BLACKLIST_DOMAINS = [
    "acadomia.fr",
    "kelprof.com",
    "apprentus.fr",
    "voscours.fr",
    "completude.com",
]

SUPERPROF_DOMAIN = "superprof.fr"

# =========================================================================
# Site slugs — alias legacy
# =========================================================================

# Anciens identifiants (pré-convention domaine, 2026-07) encore présents dans
# les Sheets, les vieux artefacts et les habitudes CLI. Toujours normaliser via
# canonical_site_slug() avant de comparer ou de résoudre un chemin.
LEGACY_SITE_SLUGS = {
    "enseigna": "enseigna.fr",
    "superprof-ressources": "superprof.fr-ressources",
    "superprof.fr": "superprof.fr-ressources",  # domaine hérité (bug output_manager)
    # NB : n'ajouter un alias ici que pour un site réellement matérialisé sous
    # sites/ — les mappings vers des sites fantômes (es-es-ressources →
    # superprof.es-apuntes, etc.) ont été retirés le 2026-07-23 ; les recréer
    # au fil des onboardings si le besoin réapparaît.
}


def canonical_site_slug(slug):
    """Normalise un site slug vers sa forme canonique (convention domaine)."""
    if not slug:
        return slug
    return LEGACY_SITE_SLUGS.get(slug, slug)


# =========================================================================
# Thresholds GSC (Google Search Console)
# =========================================================================

CTR_LOW_THRESHOLD = 2.0  # %
CTR_GOOD_THRESHOLD = 3.5  # %
IMPRESSIONS_SIGNIFICANT = 500
POSITION_DECLINE_ALERT = 5
TRAFFIC_DECLINE_MODERATE = -30  # %
TRAFFIC_DECLINE_SEVERE = -50  # %


# =========================================================================
# Thresholds Cannibalization
# =========================================================================

OVERLAP_VERY_LOW = 20
OVERLAP_LOW = 40
OVERLAP_MEDIUM = 60
OVERLAP_HIGH = 80


# =========================================================================
# Thresholds Content Similarity
# =========================================================================

SIMILARITY_THRESHOLD = 0.8

