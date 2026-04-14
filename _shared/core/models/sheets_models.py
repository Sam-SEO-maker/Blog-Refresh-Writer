"""
Sheets Models Module

Modèles pour l'intégration avec Google Sheets.

Architecture :
- `RefreshAuditRow`     — modèle générique legacy (à terme : à supprimer)
- `SuperprofAuditRow`   — onglet "⬆️ Growing" de la spreadsheet "Articles Ressources"
- `EnseignaAvisRow`     — onglet "Avis" de la spreadsheet Enseigna (à venir)
- `EnseignaVersusRow`   — onglet "Versus" de la spreadsheet Enseigna (à venir)
"""

from dataclasses import dataclass, field

from .enums import TaskStatus, TriggerType, PostType


@dataclass
class URLTask:
    """Représente une tâche de refresh d'URL."""
    url: str
    title: str  # Titre de l'article (nouvelle colonne)
    blog_id: str
    row_index: int
    post_type: PostType = PostType.STANDALONE
    status: TaskStatus = TaskStatus.PENDING
    triggered_by: TriggerType = TriggerType.MANUAL
    added_date: str = ""
    processing_started: str = ""
    processing_completed: str = ""
    error_message: str = ""
    notes: str = ""
    main_keyword: str = ""  # Mot-clé principal fourni (colonne C)
    # URLs des articles enfants (jusqu'à 6) pour les articles PARENT
    child_urls: list[str] = None  # Liste des URLs enfants

    def __post_init__(self):
        if self.child_urls is None:
            self.child_urls = []


@dataclass
class AuditResultRow:
    """Ligne de résultat d'audit pour le Sheet."""
    to_do: str = ""
    url: str = ""
    overall_score: int = 0
    impressions_30d: int = 0
    clicks_30d: int = 0
    ctr_30d: float = 0.0
    avg_position: float = 0.0
    main_keyword: str = ""
    keyword_trend: str = ""
    word_count: int = 0
    images_count: int = 0
    internal_links_count: int = 0
    has_faq: bool = False
    cannibalization_flag: bool = False
    cannibalization_severity: str = ""
    cannibalization_urls: str = ""
    intent_shift_detected: bool = False
    serp_format_expected: str = ""
    alerts: str = ""
    recommendations: str = ""
    audit_date: str = ""
    recommended_actions: str = ""


@dataclass
class RefreshResultRow:
    """Ligne de résultat de refresh pour le Sheet."""
    url: str
    refresh_date: str
    rewrite_type: str
    new_title: str
    new_meta: str
    sections_modified: int
    word_count_before: int
    word_count_after: int
    images_before: int
    images_after: int
    links_before: int
    links_after: int
    validation_passed: bool
    validation_errors: str
    content_preview: str
    full_content_link: str
    publish_queue: bool
    published_date: str
    tokens_used: int


@dataclass
class RefreshAuditRow:
    """
    Modèle unifié pour la feuille Refreshs_Audit (28 colonnes A-AB).

    Remplace URLTask + AuditResultRow + RefreshResultRow dans l'architecture single-sheet.
    NOTE: cocon_branch a été retiré du schéma — toutes les colonnes B+ ont été shiftées de -1.
    """

    # A: Core identification
    blog_id: str                                   # A

    # B-E: Article identification
    blogpost_url: str = ""                         # B
    main_keyword: str = ""                         # C
    title: str = ""                                # D
    post_type: PostType = PostType.STANDALONE       # E (PARENT/CHILD/STANDALONE)

    # F-G: Action tracking
    action_blogpost: str = ""                     # F (NO ACTION, PARTIAL REFRESH, REFRESH TITLES, FULL REFRESH)
    status: str = ""                              # G (TODO, AUDITING, DONE, BLOCKED)

    # H-I: Audit status flags
    audit_gsc: str = ""                           # H (AUDITING, DONE, FAILED)
    audit_serp: str = ""                          # I (AUDITING, DONE, FAILED)

    # J-L: Performance metrics (GSC)
    impressions_30d: int = 0                      # J
    clicks_30d: int = 0                           # K
    ctr_30d: float = 0.0                          # L

    # M-N: SERP insights
    people_also_ask: str = ""                     # M (comma-separated PAA questions)
    secondary_keywords: str = ""                  # N (comma-separated keywords)

    # O-P: Optimization targets
    new_h1_title: str = ""                        # O
    new_h2_titles: str = ""                       # P (JSON list of H2 titles)

    # Q-S: Content metrics
    word_count_before: int = 0                    # Q
    images_count: int = 0                         # R
    internal_links_count: int = 0                 # S

    # T-U: Cannibalization
    cannibalization_flag: bool = False            # T (YES/NO)
    cannibalization_urls: str = ""                # U (comma-separated competing URLs)

    # V: Error tracking
    error_message: str = ""                       # V (short error message for audit/refresh failures)

    # W: Index diagnostic
    index_diagnostic: str = ""                    # W (JSON: diagnostic détaillé d'indexation)

    # X-AB: Editorial Audit
    editorial_audit_score: float = 0.0            # X (score 1-10)
    editorial_audit_date: str = ""                # Y (timestamp)
    editorial_verdict: str = ""                   # Z (PASSED, BLOCKED, REVIEW_REQUIRED)
    blocking_issues_count: int = 0                # AA (count of blocking issues)
    editorial_audit_report_url: str = ""          # AB (path to report markdown)

    # Metadata (non-sheet)
    row_index: int = 0                            # Row number in sheet (for updates)

    def to_list(self) -> list:
        """Convertit en liste pour écriture Google Sheets (28 colonnes A-AB)."""
        return [
            self.blog_id,                                                       # A
            self.blogpost_url,                                                   # B
            self.main_keyword,                                                   # C
            self.title,                                                          # D
            self.post_type.value,                                                # E
            self.action_blogpost,                                                # F
            self.status,                                                         # G
            self.audit_gsc,                                                      # H
            self.audit_serp,                                                     # I
            self.impressions_30d,                                                # J
            self.clicks_30d,                                                     # K
            self.ctr_30d,                                                        # L
            self.people_also_ask,                                                # M
            self.secondary_keywords,                                             # N
            self.new_h1_title,                                                   # O
            self.new_h2_titles,                                                  # P
            self.word_count_before,                                              # Q
            self.images_count,                                                   # R
            self.internal_links_count,                                           # S
            "YES" if self.cannibalization_flag else "NO",                         # T
            self.cannibalization_urls,                                            # U
            self.error_message,                                                  # V
            self.index_diagnostic,                                               # W
            str(self.editorial_audit_score) if self.editorial_audit_score else "", # X
            self.editorial_audit_date,                                           # Y
            self.editorial_verdict,                                              # Z
            str(self.blocking_issues_count) if self.blocking_issues_count else "", # AA
            self.editorial_audit_report_url,                                     # AB
        ]

    @staticmethod
    def from_list(row: list, row_index: int = 0) -> "RefreshAuditRow":
        """Crée une instance à partir d'une liste (28 colonnes A-AB du sheet)."""
        def safe_float(val, default=0.0):
            if not val:
                return default
            try:
                return float(str(val).replace(",", "."))
            except (ValueError, TypeError):
                return default

        def safe_int(val, default=0):
            if not val:
                return default
            try:
                return int(float(str(val).replace(",", ".")))
            except (ValueError, TypeError):
                return default

        return RefreshAuditRow(
            blog_id=row[0] if len(row) > 0 else "",                             # A
            blogpost_url=row[1] if len(row) > 1 else "",                         # B
            main_keyword=row[2] if len(row) > 2 else "",                         # C
            title=row[3] if len(row) > 3 else "",                                # D
            post_type=PostType(row[4]) if len(row) > 4 else PostType.STANDALONE, # E
            action_blogpost=row[5] if len(row) > 5 else "",                      # F
            status=row[6] if len(row) > 6 else "",                               # G
            audit_gsc=row[7] if len(row) > 7 else "",                            # H
            audit_serp=row[8] if len(row) > 8 else "",                           # I
            impressions_30d=safe_int(row[9]) if len(row) > 9 else 0,             # J
            clicks_30d=safe_int(row[10]) if len(row) > 10 else 0,                # K
            ctr_30d=safe_float(row[11]) if len(row) > 11 else 0.0,               # L
            people_also_ask=row[12] if len(row) > 12 else "",                    # M
            secondary_keywords=row[13] if len(row) > 13 else "",                 # N
            new_h1_title=row[14] if len(row) > 14 else "",                       # O
            new_h2_titles=row[15] if len(row) > 15 else "",                      # P
            word_count_before=safe_int(row[16]) if len(row) > 16 else 0,         # Q
            images_count=safe_int(row[17]) if len(row) > 17 else 0,              # R
            internal_links_count=safe_int(row[18]) if len(row) > 18 else 0,      # S
            cannibalization_flag=(row[19] == "YES") if len(row) > 19 else False, # T
            cannibalization_urls=row[20] if len(row) > 20 else "",               # U
            error_message=row[21] if len(row) > 21 else "",                      # V
            index_diagnostic=row[22] if len(row) > 22 else "",                   # W
            editorial_audit_score=safe_float(row[23]) if len(row) > 23 else 0.0, # X
            editorial_audit_date=row[24] if len(row) > 24 else "",               # Y
            editorial_verdict=row[25] if len(row) > 25 else "",                  # Z
            blocking_issues_count=safe_int(row[26]) if len(row) > 26 else 0,     # AA
            editorial_audit_report_url=row[27] if len(row) > 27 else "",         # AB
            row_index=row_index,
        )


# =============================================================================
# Superprof Ressources — modèle d'audit en mémoire
# =============================================================================
# NOTE: Pas de mapping vers les colonnes A-E de l'onglet "⬆️ Growing".
# `Growing` est lu en read-only (URLs uniquement). Les perfs GSC sont écrites
# dans un onglet séparé `GSC_Perfs` géré indépendamment.

@dataclass
class SuperprofAuditRow:
    """
    Audit en mémoire d'une URL Superprof Ressources.

    Cette dataclass sert :
    - de structure de travail pour le pipeline (audit GSC, decision tree, refresh)
    - de schéma pour les fichiers JSON dans `_shared/outputs/superprof-ressources/audit/`

    Elle n'est PAS mappée sur les colonnes de l'onglet `Growing` (lecture seule).
    Elle alimente l'onglet séparé `GSC_Perfs` via `to_gsc_perfs_row()`.
    """

    # URL source (extraite de Growing)
    url: str = ""
    main_keyword: str = ""           # depuis Growing col B (à titre indicatif)

    # GSC metrics — fenêtre 30 jours
    impressions_30d: int = 0
    clicks_30d: int = 0
    ctr_30d: float = 0.0
    position_30d: float = 0.0

    # GSC metrics — fenêtre 12 mois
    impressions_12m: int = 0
    clicks_12m: int = 0
    position_12m: float = 0.0

    # Top queries (récupérées via dimension=query)
    top_query_1: str = ""
    top_query_2: str = ""
    top_query_3: str = ""

    # Métadonnées
    last_gsc_refresh: str = ""       # ISO timestamp ou "NO_DATA"
    error_message: str = ""

    # Source row (1-indexed dans Growing) — utile pour traçabilité
    growing_row_index: int = 0

    def to_gsc_perfs_row(self) -> list:
        """
        Convertit en liste pour écriture dans l'onglet GSC_Perfs.

        Schéma 12 colonnes (validé) :
        A: URL
        B: Main Keyword
        C: Impressions 30d
        D: Clicks 30d
        E: CTR 30d (%)
        F: Position Avg 30d
        G: Impressions 12m
        H: Clicks 12m
        I: Position 12m
        J: Top Query 1
        K: Top Query 2
        L: Top Query 3
        M: Last GSC Refresh
        """
        return [
            self.url,
            self.main_keyword,
            self.impressions_30d,
            self.clicks_30d,
            round(self.ctr_30d * 100, 2) if self.ctr_30d else 0,  # affichage en %
            round(self.position_30d, 1) if self.position_30d else 0,
            self.impressions_12m,
            self.clicks_12m,
            round(self.position_12m, 1) if self.position_12m else 0,
            self.top_query_1,
            self.top_query_2,
            self.top_query_3,
            self.last_gsc_refresh,
        ]

    @staticmethod
    def gsc_perfs_headers() -> list:
        """En-têtes (Title Case) de l'onglet GSC_Perfs — single source of truth."""
        return [
            "URL",
            "Main Keyword",
            "Impressions 30d",
            "Clicks 30d",
            "CTR 30d (%)",
            "Position Avg 30d",
            "Impressions 12m",
            "Clicks 12m",
            "Position 12m",
            "Top Query 1",
            "Top Query 2",
            "Top Query 3",
            "Last GSC Refresh",
        ]

    def to_dict(self) -> dict:
        """Sérialise pour dump JSON local."""
        return {
            "url": self.url,
            "main_keyword": self.main_keyword,
            "growing_row_index": self.growing_row_index,
            "gsc_30d": {
                "impressions": self.impressions_30d,
                "clicks": self.clicks_30d,
                "ctr": self.ctr_30d,
                "position": self.position_30d,
            },
            "gsc_12m": {
                "impressions": self.impressions_12m,
                "clicks": self.clicks_12m,
                "position": self.position_12m,
            },
            "top_queries": [self.top_query_1, self.top_query_2, self.top_query_3],
            "last_gsc_refresh": self.last_gsc_refresh,
            "error_message": self.error_message,
        }
