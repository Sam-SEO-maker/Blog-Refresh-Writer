"""
Multi-Tenant Orchestrator Module

Orchestrateur multi-tenant pour gérer plusieurs sites clients.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional

from _shared.core.sites_registry import SitesRegistry
from _shared.core.models import SiteConfig, RefreshWorkflowResult
from _shared.core.prompt_composer import PromptComposer

from .orchestrator import RefreshOrchestrator


class MultiTenantOrchestrator:
    """
    Orchestrateur multi-tenant pour gérer plusieurs sites.

    Simplifie le traitement d'URLs pour différents sites sans
    avoir à gérer chaque site comme un projet unique.

    Usage:
        orchestrator = MultiTenantOrchestrator()

        # Traiter une URL pour un site spécifique
        result = orchestrator.process_url(
            site_id="enseigna",
            url="https://enseigna.fr/avis-acadomia",
            html_content=html,
            subject="education_reviews",
            content_type="review"
        )

        # Traiter un batch multi-sites
        results = orchestrator.process_batch([
            {"site_id": "enseigna", "url": "...", "subject": "education_reviews", "content_type": "review"},
            {"site_id": "mymusicteacher", "url": "...", "subject": "music_lessons", "content_type": "guide"},
        ])
    """

    def __init__(self, base_path: Optional[Path] = None):
        """
        Initialise l'orchestrateur multi-tenant.

        Args:
            base_path: Chemin racine du projet (auto-détecté si None)
        """
        self.base_path = base_path or Path(__file__).parent.parent.parent

        # Registry des sites
        self.sites_registry = SitesRegistry()

        # Composer de prompts
        self.prompt_composer = PromptComposer()

        # Cache des orchestrateurs par site
        self._orchestrators: dict[str, RefreshOrchestrator] = {}

    def process_url(
        self,
        site_id: str,
        url: str,
        html_content: str,
        subject: Optional[str] = None,
        strategy: str = "refresh_full",
        content_type: Optional[str] = None,
        force_action: Optional[str] = None
    ) -> RefreshWorkflowResult:
        """
        Traite une URL pour un site spécifique.

        Args:
            site_id: ID du site (ex: "enseigna")
            url: URL à traiter
            html_content: Contenu HTML de la page
            subject: Sujet optionnel (ex: "education_reviews", "music_lessons")
            strategy: Stratégie de refresh (default: "refresh_full")
            content_type: Type de contenu optionnel (ex: "review", "guide") pour template
            force_action: Action forcée (bypass decision engine)

        Returns:
            RefreshWorkflowResult avec les détails

        Raises:
            ValueError: Si le site n'existe pas ou est inactif
        """
        # Récupérer la config du site
        site_config = self.sites_registry.get_site(site_id)
        if not site_config:
            raise ValueError(f"Site inconnu: {site_id}")

        if not site_config.active:
            raise ValueError(f"Site inactif: {site_id}")

        # Auto-detect subject and content_type if not provided
        if not subject and hasattr(site_config, 'subject_category'):
            subject = site_config.subject_category
        if not content_type and hasattr(site_config, 'content_type'):
            content_type = site_config.content_type

        # Composer le prompt final avec 4 niveaux (Base → Category → Strategy → Site → Template)
        custom_prompt = self.prompt_composer.compose(
            strategy=strategy,
            subject=subject,
            site_id=site_id,
            content_type=content_type
        )

        # Récupérer ou créer l'orchestrateur pour ce site
        orchestrator = self._get_orchestrator(site_config)

        # Traiter avec le prompt composé (4 niveaux: Base + Category + Strategy + Site + Template)
        return orchestrator.process_url(
            url=url,
            blog_id=site_id,
            html_content=html_content,
            force_action=force_action,
            custom_prompt=custom_prompt
        )

    def _get_orchestrator(self, site_config: SiteConfig) -> RefreshOrchestrator:
        """
        Récupère ou crée un orchestrateur pour un site.

        Args:
            site_config: Configuration du site

        Returns:
            RefreshOrchestrator configuré pour ce site
        """
        if site_config.id not in self._orchestrators:
            # Chemin des credentials
            credentials_path = self.base_path / ".credentials" / "google" / site_config.credentials

            self._orchestrators[site_config.id] = RefreshOrchestrator(
                base_path=self.base_path,
                spreadsheet_id=site_config.sheet_id
            )

        return self._orchestrators[site_config.id]

    def process_batch(self, batch: list[dict]) -> list[RefreshWorkflowResult]:
        """
        Traite un batch d'URLs multi-sites.

        Args:
            batch: Liste de dicts avec {site_id, url, html_content, subject, content_type, strategy}

        Returns:
            Liste de RefreshWorkflowResult
        """
        results = []
        for item in batch:
            try:
                result = self.process_url(
                    site_id=item["site_id"],
                    url=item["url"],
                    html_content=item["html_content"],
                    subject=item.get("subject"),
                    strategy=item.get("strategy", "refresh_full"),
                    content_type=item.get("content_type")
                )
                results.append(result)
            except Exception as e:
                print(f"Erreur traitement {item['url']}: {e}")
                # Créer un résultat d'erreur
                results.append(RefreshWorkflowResult(
                    url=item["url"],
                    blog_id=item["site_id"],
                    success=False,
                    action_taken="ERROR",
                    audit_score=0,
                    rewrite_type=None,
                    new_title=None,
                    new_meta=None,
                    assets_valid=False,
                    errors=[str(e)],
                    execution_time_seconds=0.0
                ))

        return results

    def list_sites(self) -> list[SiteConfig]:
        """Liste tous les sites actifs."""
        return self.sites_registry.list_active_sites()
