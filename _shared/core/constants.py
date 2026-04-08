"""
Constants Module

Toutes les constantes globales du projet centralisées ici.
"""

# =========================================================================
# Domaines et URLs
# =========================================================================

BLACKLIST_DOMAINS = [
    "acadomia.fr",
    "kelprof.com",
    "apprentus.fr",
    "voscours.fr",
    "completchude.com",
]

SUPERPROF_DOMAIN = "superprof.fr"


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
# Thresholds Intent Detection
# =========================================================================

INTENT_SHIFT_THRESHOLD = 0.7
VARIANT_TREND_THRESHOLD = 0.3


# =========================================================================
# Thresholds Content Similarity
# =========================================================================

SIMILARITY_THRESHOLD = 0.8


# =========================================================================
# Reading Time
# =========================================================================

WORDS_PER_MINUTE = 200
