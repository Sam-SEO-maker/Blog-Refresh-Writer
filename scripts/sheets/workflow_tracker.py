"""
Workflow Tracker Module

Suivi en temps réel du workflow de refresh dans Google Sheets.
"""

from datetime import datetime
from typing import Optional

from _shared.core.models import (
    WorkflowProgress,
    TaskStatus,
    AuditResultRow,
    RefreshResultRow,
)
from .sheets_client import SheetsClient


class WorkflowTracker:
    """
    Tracker de workflow pour le suivi en temps réel.

    Gère:
    - La progression étape par étape
    - Les mises à jour de statut
    - La conversion des résultats d'audit en lignes Sheets
    """

    WORKFLOW_STEPS = [
        "selection",
        "ingest",
        "audit",
        "decision",
        "writing",
        "linking",
        "validation",
        "sync"
    ]

    def __init__(self, sheets_client: SheetsClient):
        """
        Initialise le tracker.

        Args:
            sheets_client: Client Sheets pour les mises à jour
        """
        self.sheets_client = sheets_client
        self._active_workflows: dict[str, WorkflowProgress] = {}

    def start_workflow(self, url: str) -> WorkflowProgress:
        """
        Démarre le suivi d'un workflow pour une URL.

        Args:
            url: URL à traiter

        Returns:
            WorkflowProgress initial
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        progress = WorkflowProgress(
            url=url,
            current_step="selection",
            steps_completed=[],
            steps_remaining=self.WORKFLOW_STEPS.copy(),
            progress_percent=0,
            started_at=now,
            last_update=now,
            errors=[],
        )

        self._active_workflows[url] = progress

        # Mettre à jour le statut dans Sheets

        return progress

    def advance_step(self, url: str, completed_step: str) -> Optional[WorkflowProgress]:
        """
        Avance au step suivant du workflow.

        Args:
            url: URL concernée
            completed_step: Étape qui vient d'être complétée

        Returns:
            WorkflowProgress mis à jour
        """
        if url not in self._active_workflows:
            return None

        progress = self._active_workflows[url]
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Marquer l'étape comme complétée
        if completed_step in progress.steps_remaining:
            progress.steps_remaining.remove(completed_step)
            progress.steps_completed.append(completed_step)

        # Déterminer l'étape courante
        if progress.steps_remaining:
            progress.current_step = progress.steps_remaining[0]
        else:
            progress.current_step = "completed"

        # Calculer le pourcentage
        total_steps = len(self.WORKFLOW_STEPS)
        completed = len(progress.steps_completed)
        progress.progress_percent = int((completed / total_steps) * 100)

        progress.last_update = now

        # Mettre à jour le statut Sheets selon l'étape
        status_mapping = {
            "audit": TaskStatus.AUDITING,
            "decision": TaskStatus.DECIDING,
            "writing": TaskStatus.WRITING,
            "validation": TaskStatus.VALIDATING,
            "completed": TaskStatus.COMPLETED,
        }

        # (écriture Sheet retirée : l'onglet URLs_Input n'existe pas — suivi en mémoire)
        return progress

    def record_error(self, url: str, error: str) -> None:
        """
        Enregistre une erreur dans le workflow.

        Args:
            url: URL concernée
            error: Message d'erreur
        """
        if url in self._active_workflows:
            self._active_workflows[url].errors.append(error)
            self._active_workflows[url].last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


    def complete_workflow(self, url: str, success: bool = True) -> None:
        """
        Termine un workflow.

        Args:
            url: URL concernée
            success: True si succès, False si échec
        """
        # (écritures Sheet COMPLETED/FAILED retirées — suivi en mémoire uniquement)
        # Nettoyer le workflow actif
        if url in self._active_workflows:
            del self._active_workflows[url]

    def get_progress(self, url: str) -> Optional[WorkflowProgress]:
        """
        Récupère la progression d'un workflow.

        Args:
            url: URL concernée

        Returns:
            WorkflowProgress ou None
        """
        return self._active_workflows.get(url)

    # =========================================================================
    # Conversion helpers pour les résultats
    # =========================================================================

    def audit_report_to_row(self, report: dict) -> AuditResultRow:
        """
        Convertit un rapport d'audit en ligne Sheets.

        Args:
            report: Dictionnaire du rapport d'audit (de AuditEngine.to_dict())

        Returns:
            AuditResultRow prête pour insertion
        """
        content = report.get("content", {})
        performance = report.get("performance", {})
        cannibalization = report.get("cannibalization", {})
        intent = report.get("intent", {})

        # Déterminer la tendance du keyword
        keyword_trend = "stable"
        if performance.get("is_declining"):
            keyword_trend = "declining"

        # Déterminer la sévérité de cannibalisation
        cann_severity = ""
        if cannibalization.get("has_issue"):
            cann_severity = "high" if cannibalization.get("requires_action") else "medium"

        # Formater les alertes et recommandations
        alerts = ", ".join(report.get("alerts", [])) if report.get("alerts") else ""
        recommendations = ", ".join(report.get("recommendations", [])[:3]) if report.get("recommendations") else ""

        return AuditResultRow(
            to_do="",
            url=report.get("url", ""),
            overall_score=report.get("overall_score", 0),
            impressions_30d=performance.get("impressions_30d", 0),
            clicks_30d=performance.get("clicks_30d", 0),
            ctr_30d=performance.get("ctr_30d", 0.0),
            avg_position=performance.get("avg_position", 0.0),
            main_keyword=performance.get("main_keyword", ""),
            keyword_trend=keyword_trend,
            word_count=content.get("word_count", 0),
            images_count=content.get("image_count", 0),
            internal_links_count=content.get("internal_links", 0),
            has_faq=content.get("has_faq", False),
            cannibalization_flag=cannibalization.get("has_issue", False),
            cannibalization_severity=cann_severity,
            cannibalization_urls=cannibalization.get("suggested_action", ""),
            intent_shift_detected=intent.get("shift_detected", False) if intent else False,
            serp_format_expected=intent.get("serp_format", "") if intent else "",
            alerts=alerts,
            recommendations=recommendations,
            audit_date=report.get("audit_date", ""),
            recommended_actions="",
        )

    def refresh_result_to_row(
        self,
        url: str,
        rewrite_type: str,
        new_title: str,
        new_meta: str,
        sections_modified: int,
        before_stats: dict,
        after_stats: dict,
        validation_passed: bool,
        validation_errors: str,
        content_preview: str,
        tokens_used: int
    ) -> RefreshResultRow:
        """
        Crée une ligne de résultat de refresh.

        Args:
            url: URL concernée
            rewrite_type: Type de réécriture (PARTIAL, FULL, TITLE_ONLY)
            new_title: Nouveau titre
            new_meta: Nouvelle meta description
            sections_modified: Nombre de sections modifiées
            before_stats: Statistiques avant (word_count, images, links)
            after_stats: Statistiques après
            validation_passed: Validation réussie
            validation_errors: Erreurs de validation
            content_preview: Aperçu du contenu
            tokens_used: Tokens utilisés

        Returns:
            RefreshResultRow prête pour insertion
        """
        return RefreshResultRow(
            url=url,
            refresh_date=datetime.now().strftime("%Y-%m-%d %H:%M"),
            rewrite_type=rewrite_type,
            new_title=new_title,
            new_meta=new_meta,
            sections_modified=sections_modified,
            word_count_before=before_stats.get("word_count", 0),
            word_count_after=after_stats.get("word_count", 0),
            images_before=before_stats.get("images", 0),
            images_after=after_stats.get("images", 0),
            links_before=before_stats.get("links", 0),
            links_after=after_stats.get("links", 0),
            validation_passed=validation_passed,
            validation_errors=validation_errors,
            content_preview=content_preview,
            full_content_link="",  # À remplir si stockage externe
            publish_queue=validation_passed,
            published_date="",
            tokens_used=tokens_used,
        )
