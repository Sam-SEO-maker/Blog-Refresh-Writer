"""
Output Manager Module

Centralized handler for all file outputs in the autonomous "Scrape & Refresh" workflow.

Architecture:
- Scrape cache: sites/{site_slug}/outputs/_scrape_cache/ (scraped HTML for comparison)
- Permanent outputs:
  - sites/{site_slug}/outputs/html/ (refreshed HTML files)
  - sites/{site_slug}/outputs/metadata/ (metadata and audit JSON files)
  - sites/{site_slug}/outputs/editorial_audits/ (editorial audit markdown files)

Multi-site support : dossiers indexés par `site_slug` (clé de sites.json),
p.ex. `enseigna`, `superprof-ressources`. Registre ouvert (tout site présent
dans sites.json est valide) — plus de whitelist de domaines codée en dur.
"""

from pathlib import Path
from typing import Optional, Dict, List, Tuple
import json
import re
import shutil
import unicodedata
from datetime import datetime
import locale
import logging


def title_to_slug(title: str) -> str:
    """Convert an article title to a clean URL/filename slug."""
    s = unicodedata.normalize('NFD', title)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = s.lower()
    s = re.sub(r'[^a-z0-9\s]', '', s)
    s = re.sub(r'\s+', '-', s.strip())
    s = re.sub(r'-+', '-', s)
    return s[:150] or "unknown"


def dated_batch_folder_name(dt: Optional[datetime] = None) -> str:
    """Nom de sous-dossier de lot daté, ex. 'articles_7_juillet_2026'.

    Utilisé pour ranger html/, csv_zips/ et json/ par date de génération plutôt
    que de tout accumuler à plat dans un seul dossier (cf. réorganisation
    manuelle du 2026-07-07 en articles_juin_2026 / articles_7_juillet_2026).
    """
    dt = dt or datetime.now()
    try:
        locale.setlocale(locale.LC_TIME, "fr_FR.UTF-8")
    except locale.Error:
        pass
    mois_fr = [
        "janvier", "fevrier", "mars", "avril", "mai", "juin",
        "juillet", "aout", "septembre", "octobre", "novembre", "decembre",
    ]
    return f"articles_{dt.day}_{mois_fr[dt.month - 1]}_{dt.year}"

logger = logging.getLogger(__name__)


class OutputManager:
    """
    Manages all file outputs for the autonomous workflow.

    Ensures:
    - Single output location per site (sites/{id}/outputs/)
    - Temporary cache for scraped HTML (sites/{id}/outputs/_scrape_cache/)
    - Consistent directory structure
    - Validation before writes
    - Atomic file operations
    - Multi-site isolation
    """

    def __init__(self, base_path: Optional[Path] = None):
        """
        Initialize output manager.

        Args:
            base_path: Project root (defaults to auto-detect)
        """
        self.base_path = base_path or Path(__file__).parent.parent.parent
        # Racines résolues via le point unique SitePaths (Phase 4.0) : un futur
        # déplacement vers sites/{id}/ ne changera que SitePaths, pas ici.
        from _shared.core.site_paths import SitePaths
        self._site_paths = SitePaths(base_path=self.base_path)

        # Ensure base directories exist (outputs sont désormais par site)
        self._site_paths.sites_root.mkdir(parents=True, exist_ok=True)

    def init_workspace(self, purge_temp: bool = True) -> Dict[str, int]:
        """
        Initialize workspace: purge temp cache and ensure outputs structure.

        Cette fonction garantit:
        1. le _scrape_cache de chaque site est purgé (si purge_temp=True)
        2. sites/{id}/outputs/ existe pour chaque site
        3. sites/{id}/outputs/editorial_audits/ existe

        Args:
            purge_temp: Si True, supprime le _scrape_cache de chaque site

        Returns:
            {
                "temp_files_removed": int,
                "output_dirs_created": int,
                "editorial_audit_dirs_created": int
            }
        """
        stats = {
            "temp_files_removed": 0,
            "output_dirs_created": 0,
            "subdirs_created": 0
        }

        # Purge scrape cache — le _scrape_cache de chaque site.
        if purge_temp:
            for _site_slug, output_dir in self._site_paths.output_dirs():
                cache_dir = output_dir / "_scrape_cache"
                if not cache_dir.exists():
                    continue
                stats["temp_files_removed"] += sum(1 for _ in cache_dir.rglob("*") if _.is_file())
                shutil.rmtree(cache_dir)
            logger.info(f"Purged scrape cache: {stats['temp_files_removed']} files removed")

        # Ensure outputs structure for all sites
        for site_id in self._known_site_slugs():
            # Create site output directory (sites/{id}/outputs/)
            site_dir = self._site_paths.output_dir(site_id)
            if not site_dir.exists():
                site_dir.mkdir(parents=True, exist_ok=True)
                stats["output_dirs_created"] += 1

            # Create html/, metadata/, editorial_audits/ subdirectories
            for subdir in ["html", "metadata", "editorial_audits"]:
                sub_path = site_dir / subdir
                if not sub_path.exists():
                    sub_path.mkdir(parents=True, exist_ok=True)
                    stats["subdirs_created"] += 1

        logger.info(
            f"Workspace initialized: "
            f"{stats['output_dirs_created']} output dirs, "
            f"{stats['subdirs_created']} subdirs created"
        )

        return stats

    # Domaines historiques tolérés en ENTRÉE (rétrocompat appelants), remappés
    # vers le site_slug canonique. Les sorties sont toujours écrites par id.
    _DOMAIN_TO_SITE_SLUG = {
        "enseigna.fr": "enseigna",
        "superprof.fr": "superprof-ressources",
    }

    def _known_site_slugs(self) -> set:
        """IDs de sites connus, lus directement depuis sites.json (registre plat).

        Lecture JSON brute plutôt que via SiteConfig(**data) : les entrées de
        sites.json portent des champs métier (subject_category, ymyl_level…) que
        le dataclass strict SiteConfig ne déclare pas et qui le font planter.
        """
        try:
            sites_path = self.base_path / "_shared" / "config" / "sites.json"
            data = json.loads(sites_path.read_text(encoding="utf-8"))
            return {(s.get("site_slug") or s.get("id")) for s in data.get("sites", []) if ("site_slug" in s or "id" in s)}
        except Exception:
            return set()

    def _normalize_site_id(self, site_id: str) -> str:
        """Normalise vers le site_slug canonique (remappe un domaine hérité)."""
        return self._DOMAIN_TO_SITE_SLUG.get(site_id, site_id)

    def _validate_site_id(self, site_id: str) -> str:
        """Valide et retourne le site_slug canonique (id-based, ouvert au registre)."""
        normalized = self._normalize_site_id(site_id)
        known = self._known_site_slugs()
        # Si le registre est lisible, on valide contre lui ; sinon on laisse passer
        # (un site factice sans entrée registre ne doit pas être bloqué par un
        # whitelist codé en dur — cf. objectif « site sans modif code »).
        if known and normalized not in known:
            raise ValueError(
                f"Invalid site_id '{site_id}'. "
                f"Must be a site registered in sites.json: {', '.join(sorted(known))}"
            )
        return normalized

    @staticmethod
    def _validate_article_type(article_type: str) -> str:
        """Valide un sous-type d'article servant de nom de sous-dossier `html/`.

        Restreint à [a-z0-9_-] (après strip/lowercase) pour interdire toute
        traversée de chemin (`..`, `/`) : le sous-type provient d'une option CLI.
        """
        norm = article_type.strip().lower()
        if not norm or not re.fullmatch(r"[a-z0-9_-]+", norm):
            raise ValueError(
                f"Invalid article_type '{article_type}'. "
                "Attendu : identifiant simple [a-z0-9_-] (ex. 'avis', 'versus')."
            )
        return norm

    def _url_to_slug(self, url: str) -> str:
        """
        Convert URL to safe filename slug.

        Examples:
            https://enseigna.fr/avis-acadomia/ → avis-acadomia
            https://www.superprof.fr/ressources/maths/calcul/ → calcul
        """
        from urllib.parse import urlparse
        import re

        parsed = urlparse(url) if url.startswith("http") else None
        if parsed:
            slug = parsed.path.strip('/').replace('/', '-')
        else:
            slug = url

        # Sanitize: keep only alphanumeric, dash, underscore
        slug = re.sub(r'[^\w\-]', '', slug)

        # Limit length
        slug = slug[:150]

        return slug or "unknown"

    @staticmethod
    def _title_to_slug(title: str) -> str:
        return title_to_slug(title)

    # =========================================================================
    # TEMP CACHE METHODS (for scraped HTML)
    # =========================================================================

    def _temp_dir(self, site_id: str) -> Path:
        """Dossier de cache scrapé du site (site_id normalisé)."""
        return self._site_paths.scrape_cache_dir(self._validate_site_id(site_id))

    def save_temp_html(self, site_id: str, url_slug: str, html_content: str) -> Path:
        """
        Save scraped HTML to temp cache for editorial audit comparison.

        Args:
            site_id: Blog identifier (e.g., "enseigna.fr")
            url_slug: URL slug for filename
            html_content: Scraped HTML content

        Returns:
            Path to saved temp file
        """
        # Create site scrape-cache directory (_temp_dir valide site_id)
        temp_dir = self._temp_dir(site_id)
        temp_dir.mkdir(parents=True, exist_ok=True)

        # Save HTML
        temp_file = temp_dir / f"{url_slug}.html"
        temp_file.write_text(html_content, encoding="utf-8")

        logger.debug(f"Saved temp HTML: {temp_file}")
        return temp_file

    def get_temp_html(self, site_id: str, url_slug: str) -> Optional[str]:
        """
        Retrieve scraped HTML from temp cache.

        Args:
            site_id: Blog identifier
            url_slug: URL slug

        Returns:
            HTML content if exists, None otherwise
        """
        temp_file = self._temp_dir(site_id) / f"{url_slug}.html"
        if temp_file.exists():
            return temp_file.read_text(encoding="utf-8")
        return None

    def _cleanup_temp(self, site_id: str, url_slug: str):
        """Remove temp file for a delivered article."""
        temp_file = self._temp_dir(site_id) / f"{url_slug}.html"
        if temp_file.exists():
            temp_file.unlink()
            logger.debug(f"Cleaned up temp file: {temp_file}")

    def clear_temp_cache(self, site_id: Optional[str] = None) -> int:
        """
        Clear temp cache for a specific site or all sites.

        Args:
            site_id: If provided, clear only this site's cache. If None, clear all.

        Returns:
            Number of files removed
        """
        if site_id:
            temp_dir = self._temp_dir(site_id)
            if temp_dir.exists():
                file_count = sum(1 for _ in temp_dir.rglob("*.html"))
                shutil.rmtree(temp_dir)
                temp_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"Cleared scrape cache for {temp_dir.parent.parent.name}: {file_count} files")
                return file_count
            return 0
        else:
            # Clear all sites : itère le _scrape_cache de chaque site présent
            # sur disque (via output_dirs) — robuste à un site retiré du registre.
            total = 0
            for _site_slug, output_dir in self._site_paths.output_dirs():
                temp_dir = output_dir / "_scrape_cache"
                if temp_dir.is_dir():
                    file_count = sum(1 for _ in temp_dir.rglob("*.html"))
                    shutil.rmtree(temp_dir)
                    temp_dir.mkdir(parents=True, exist_ok=True)
                    total += file_count
            return total

    # =========================================================================
    # OUTPUT METHODS (for permanent results)
    # =========================================================================

    def get_site_output_dir(self, site_id: str) -> Path:
        """
        Get output directory for a site.

        Args:
            site_id: Blog identifier

        Returns:
            Path to site output directory
        """
        site_id = self._validate_site_id(site_id)

        site_dir = self._site_paths.output_dir(site_id)
        site_dir.mkdir(parents=True, exist_ok=True)

        # Ensure html/, metadata/, editorial_audits/ subdirectories exist
        for subdir in ["html", "metadata", "editorial_audits"]:
            (site_dir / subdir).mkdir(parents=True, exist_ok=True)

        return site_dir

    def save_refreshed_html(
        self,
        site_id: str,
        url_slug: str,
        html_content: str,
        title: Optional[str] = None,
        post_type: Optional[str] = None,  # kept for backwards compat, ignored
        article_type: Optional[str] = None,
    ) -> Path:
        """
        Save refreshed HTML content (WordPress-ready).

        Args:
            site_id: Blog identifier
            url_slug: URL slug for filename (fallback if no title)
            html_content: Refreshed HTML content
            title: Article title (column E) — used for filename if provided
            article_type: sous-type d'article routant la sortie HTML dans un
                sous-dossier `html/{article_type}/` (ex. enseigna : "avis" |
                "versus"). None → écriture à la racine `html/` (comportement
                historique, sites sans sous-typage).

        Returns:
            Path to saved file
        """
        site_id = self._validate_site_id(site_id)
        html_dir = self.get_site_output_dir(site_id) / "html"
        if article_type:
            html_dir = html_dir / self._validate_article_type(article_type)
        html_dir.mkdir(parents=True, exist_ok=True)

        file_slug = self._title_to_slug(title) if title else url_slug
        output_file = html_dir / f"{file_slug}_refreshed.html"

        output_file.write_text(html_content, encoding="utf-8")
        logger.info(f"Saved refreshed HTML: {output_file}")

        from scripts.utils.gutenberg_formatter import to_gutenberg
        gutenberg_file = html_dir / f"{file_slug}_refreshed.gutenberg.html"
        gutenberg_file.write_text(to_gutenberg(html_content), encoding="utf-8")
        logger.info(f"Saved Gutenberg HTML: {gutenberg_file}")

        from scripts.utils.table_csv_extractor import extract_tables_to_csv
        csv_dir = self.get_site_output_dir(site_id) / "csv"
        csv_files = extract_tables_to_csv(html_content, csv_dir, file_slug)
        if csv_files:
            logger.info(f"[CSV] {len(csv_files)} tableau(x) extrait(s) → {csv_dir}")
            import zipfile
            zip_dir = self.get_site_output_dir(site_id) / "csv_zips"
            zip_dir.mkdir(parents=True, exist_ok=True)
            zip_path = zip_dir / f"{file_slug}_tableaux.zip"
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for p in csv_files:
                    zf.write(p, p.name)
            logger.info(f"[ZIP] {zip_path.name}")

        from scripts.utils.acf_extractor import save_acf_if_literary
        acf_path = save_acf_if_literary(
            site_id, file_slug, html_content,
            site_output_dir=self._site_paths.output_dir(site_id),
        )
        if acf_path:
            logger.info(f"[ACF] fiche de lecture détectée → {acf_path}")

        # Clean up temp file for this article after successful delivery
        self._cleanup_temp(site_id, url_slug)

        return output_file

    def save_metadata(
        self,
        site_id: str,
        url_slug: str,
        metadata: dict
    ) -> Path:
        """
        Save metadata JSON (title, meta_description, keywords, etc.).

        Args:
            site_id: Blog identifier
            url_slug: URL slug for filename
            metadata: Metadata dictionary

        Returns:
            Path to saved file
        """
        site_id = self._validate_site_id(site_id)

        metadata_dir = self.get_site_output_dir(site_id) / "metadata"
        metadata_dir.mkdir(parents=True, exist_ok=True)
        output_file = metadata_dir / f"{url_slug}_metadata.json"

        with output_file.open("w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved metadata: {output_file}")
        return output_file

    def save_audit_report(
        self,
        site_id: str,
        url_slug: str,
        audit_data: dict,
        report_type: str = "audit"
    ) -> Path:
        """
        Save audit report JSON.

        Args:
            site_id: Blog identifier
            url_slug: URL slug for filename
            audit_data: Audit data dictionary
            report_type: Type of report (audit, serp, gsc)

        Returns:
            Path to saved file
        """
        site_id = self._validate_site_id(site_id)

        metadata_dir = self.get_site_output_dir(site_id) / "metadata"
        metadata_dir.mkdir(parents=True, exist_ok=True)
        output_file = metadata_dir / f"{url_slug}_{report_type}.json"

        with output_file.open("w", encoding="utf-8") as f:
            json.dump(audit_data, f, indent=2, ensure_ascii=False)

        logger.debug(f"Saved {report_type} report: {output_file}")
        return output_file

    def save_editorial_audit(
        self,
        site_id: str,
        url_slug: str,
        markdown_content: str
    ) -> Path:
        """
        Save editorial audit markdown report.

        Stocké dans: sites/{site_id}/outputs/editorial_audits/{url_slug}_editorial_audit.md

        Args:
            site_id: Blog identifier
            url_slug: URL slug for filename
            markdown_content: Markdown content of editorial audit

        Returns:
            Path to saved file
        """
        site_id = self._validate_site_id(site_id)

        output_dir = self.get_site_output_dir(site_id)
        editorial_dir = output_dir / "editorial_audits"
        editorial_dir.mkdir(parents=True, exist_ok=True)

        output_file = editorial_dir / f"{url_slug}_editorial_audit.md"
        output_file.write_text(markdown_content, encoding="utf-8")

        logger.info(f"Saved editorial audit: {output_file}")
        return output_file

    # =========================================================================
    # VALIDATION & UTILITY METHODS
    # =========================================================================

    def get_output_files(
        self,
        site_id: str,
        url_slug: str,
        title: Optional[str] = None,
        post_type: Optional[str] = None
    ) -> Dict[str, Path]:
        """
        Get paths to expected output files.

        Args:
            site_id: Blog identifier
            url_slug: URL slug
            title: Article title — used for HTML filename if provided
        Returns:
            Dictionary of output file paths
        """
        site_id = self._validate_site_id(site_id)

        output_dir = self.get_site_output_dir(site_id)
        html_dir = output_dir / "html"
        metadata_dir = output_dir / "metadata"
        editorial_dir = output_dir / "editorial_audits"

        return {
            "refreshed_html": html_dir / f"{self._title_to_slug(title) if title else url_slug}_refreshed.html",
            "metadata": metadata_dir / f"{url_slug}_metadata.json",
            "audit": metadata_dir / f"{url_slug}_audit.json",
            "serp": metadata_dir / f"{url_slug}_serp.json",
            "gsc": metadata_dir / f"{url_slug}_gsc.json",
            "editorial_audit": editorial_dir / f"{url_slug}_editorial_audit.md",
            "temp_html": self._temp_dir(site_id) / f"{url_slug}.html"
        }

    def validate_outputs_exist(
        self,
        site_id: str,
        url_slug: str,
        required: List[str] = None
    ) -> Tuple[bool, List[str]]:
        """
        Validate that required output files exist.

        Args:
            site_id: Blog identifier
            url_slug: URL slug
            required: List of required file types (default: ["refreshed_html", "metadata"])

        Returns:
            Tuple of (all_exist: bool, missing_files: list)
        """
        if required is None:
            required = ["refreshed_html", "metadata"]

        site_id = self._validate_site_id(site_id)

        outputs = self.get_output_files(site_id, url_slug)
        missing = [
            file_type
            for file_type in required
            if not outputs[file_type].exists()
        ]

        return (len(missing) == 0, missing)

    def get_workspace_stats(self) -> Dict[str, any]:
        """
        Get statistics about workspace usage.

        Returns:
            {
                "temp_cache": {site_id: file_count},
                "outputs": {site_id: file_count},
                "total_temp_size_mb": float,
                "total_output_size_mb": float
            }
        """
        stats = {
            "temp_cache": {},
            "outputs": {},
            "total_temp_size_mb": 0.0,
            "total_output_size_mb": 0.0
        }

        # Temp cache stats — le _scrape_cache de chaque site
        for site_slug, output_dir in self._site_paths.output_dirs():
            cache_dir = output_dir / "_scrape_cache"
            if cache_dir.is_dir():
                files = list(cache_dir.rglob("*.html"))
                stats["temp_cache"][site_slug] = len(files)
                stats["total_temp_size_mb"] += sum(f.stat().st_size for f in files) / (1024 * 1024)

        # Output stats — un dossier outputs/ par site (sites/{id}/outputs/)
        for site_slug, output_dir in self._site_paths.output_dirs():
            files = [f for f in output_dir.rglob("*") if f.is_file()]
            stats["outputs"][site_slug] = len(files)
            stats["total_output_size_mb"] += sum(f.stat().st_size for f in files) / (1024 * 1024)

        return stats
