"""
Sheets Models Module

Modèles pour l'intégration avec Google Sheets.
"""

from dataclasses import dataclass

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
    Modèle unifié pour la feuille Refreshs_Audit (29 colonnes A-AC).

    Remplace URLTask + AuditResultRow + RefreshResultRow dans l'architecture single-sheet.
    """

    # A-B: Core identification
    blog_id: str                                   # A
    cocon_branch: int = 0                          # B (numéro de branche cocon, 0 = pas de cocon)

    # C-F: Article identification
    blogpost_url: str = ""                         # C
    main_keyword: str = ""                         # D
    title: str = ""                                # E
    post_type: PostType = PostType.STANDALONE       # F (PARENT/CHILD/STANDALONE)

    # G-H: Action tracking
    action_blogpost: str = ""                     # G (NO ACTION, PARTIAL REFRESH, REFRESH TITLES, FULL REFRESH)
    status: str = ""                              # H (TODO, AUDITING, DONE, BLOCKED)

    # I-J: Audit status flags
    audit_gsc: str = ""                           # I (AUDITING, DONE, FAILED)
    audit_serp: str = ""                          # J (AUDITING, DONE, FAILED)

    # K-M: Performance metrics (GSC)
    impressions_30d: int = 0                      # K
    clicks_30d: int = 0                           # L
    ctr_30d: float = 0.0                          # M

    # N-O: SERP insights
    people_also_ask: str = ""                     # N (comma-separated PAA questions)
    secondary_keywords: str = ""                  # O (comma-separated keywords)

    # P-Q: Optimization targets
    new_h1_title: str = ""                        # P
    new_h2_titles: str = ""                       # Q (JSON list of H2 titles)

    # R-T: Content metrics
    word_count_before: int = 0                    # R
    images_count: int = 0                         # S
    internal_links_count: int = 0                 # T

    # U-V: Cannibalization
    cannibalization_flag: bool = False            # U (YES/NO)
    cannibalization_urls: str = ""                # V (comma-separated competing URLs)

    # W: Error tracking
    error_message: str = ""                       # W (short error message for audit/refresh failures)

    # X: Index diagnostic
    index_diagnostic: str = ""                    # X (JSON: diagnostic détaillé d'indexation)

    # Y-AC: Editorial Audit
    editorial_audit_score: float = 0.0            # Y (score 1-10)
    editorial_audit_date: str = ""                # Z (timestamp)
    editorial_verdict: str = ""                   # AA (PASSED, BLOCKED, REVIEW_REQUIRED)
    blocking_issues_count: int = 0                # AB (count of blocking issues)
    editorial_audit_report_url: str = ""          # AC (path to report markdown)

    # Metadata (non-sheet)
    row_index: int = 0                            # Row number in sheet (for updates)

    def to_list(self) -> list:
        """Convertit en liste pour écriture Google Sheets (29 colonnes A-AC)."""
        return [
            self.blog_id,                                                       # A
            str(self.cocon_branch) if self.cocon_branch else "",                 # B
            self.blogpost_url,                                                   # C
            self.main_keyword,                                                   # D
            self.title,                                                          # E
            self.post_type.value,                                                # F
            self.action_blogpost,                                                # G
            self.status,                                                         # H
            self.audit_gsc,                                                      # I
            self.audit_serp,                                                     # J
            self.impressions_30d,                                                # K
            self.clicks_30d,                                                     # L
            self.ctr_30d,                                                        # M
            self.people_also_ask,                                                # N
            self.secondary_keywords,                                             # O
            self.new_h1_title,                                                   # P
            self.new_h2_titles,                                                  # Q
            self.word_count_before,                                              # R
            self.images_count,                                                   # S
            self.internal_links_count,                                           # T
            "YES" if self.cannibalization_flag else "NO",                         # U
            self.cannibalization_urls,                                            # V
            self.error_message,                                                  # W
            self.index_diagnostic,                                               # X
            str(self.editorial_audit_score) if self.editorial_audit_score else "", # Y
            self.editorial_audit_date,                                           # Z
            self.editorial_verdict,                                              # AA
            str(self.blocking_issues_count) if self.blocking_issues_count else "", # AB
            self.editorial_audit_report_url,                                     # AC
        ]

    @staticmethod
    def from_list(row: list, row_index: int = 0) -> "RefreshAuditRow":
        """Crée une instance à partir d'une liste (29 colonnes A-AC du sheet)."""
        # Helper function to safely convert to float
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
            cocon_branch=safe_int(row[1]) if len(row) > 1 else 0,               # B
            blogpost_url=row[2] if len(row) > 2 else "",                         # C
            main_keyword=row[3] if len(row) > 3 else "",                         # D
            title=row[4] if len(row) > 4 else "",                                # E
            post_type=PostType(row[5]) if len(row) > 5 else PostType.STANDALONE, # F
            action_blogpost=row[6] if len(row) > 6 else "",                      # G
            status=row[7] if len(row) > 7 else "",                               # H
            audit_gsc=row[8] if len(row) > 8 else "",                            # I
            audit_serp=row[9] if len(row) > 9 else "",                           # J
            impressions_30d=safe_int(row[10]) if len(row) > 10 else 0,           # K
            clicks_30d=safe_int(row[11]) if len(row) > 11 else 0,                # L
            ctr_30d=safe_float(row[12]) if len(row) > 12 else 0.0,              # M
            people_also_ask=row[13] if len(row) > 13 else "",                    # N
            secondary_keywords=row[14] if len(row) > 14 else "",                 # O
            new_h1_title=row[15] if len(row) > 15 else "",                       # P
            new_h2_titles=row[16] if len(row) > 16 else "",                      # Q
            word_count_before=safe_int(row[17]) if len(row) > 17 else 0,         # R
            images_count=safe_int(row[18]) if len(row) > 18 else 0,              # S
            internal_links_count=safe_int(row[19]) if len(row) > 19 else 0,      # T
            cannibalization_flag=(row[20] == "YES") if len(row) > 20 else False,  # U
            cannibalization_urls=row[21] if len(row) > 21 else "",               # V
            error_message=row[22] if len(row) > 22 else "",                      # W
            index_diagnostic=row[23] if len(row) > 23 else "",                   # X
            editorial_audit_score=safe_float(row[24]) if len(row) > 24 else 0.0, # Y
            editorial_audit_date=row[25] if len(row) > 25 else "",               # Z
            editorial_verdict=row[26] if len(row) > 26 else "",                  # AA
            blocking_issues_count=safe_int(row[27]) if len(row) > 27 else 0,     # AB
            editorial_audit_report_url=row[28] if len(row) > 28 else "",         # AC
            row_index=row_index,
        )
