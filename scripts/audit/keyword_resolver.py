"""
Résolveur du mot-clé principal (main_keyword) multi-source.

Le guide YourTextGuru (YTG) doit être créé/résolu avec le mot-clé principal de
la requête. Ce mot-clé peut provenir de plusieurs sources, cloisonnées par blog
dans l'état actuel du projet. Ce module unifie la résolution en une seule
fonction, avec un ordre de priorité configurable par blog.

Sources supportées (dans l'ordre de priorité par défaut) :
    1. notion  — propriété "Requête YTG" de la base "📕 Commandes"
                 (source de vérité pour les NOUVEAUX articles ; enseigna surtout).
    2. sheet   — mot-clé lu dans l'onglet réel du blog (service account) :
                   * enseigna              → onglets "Avis"/"Versus" (col B top_keyword)
                                             + "A ajouter" (col D main_keyword)
                   * superprof.fr-ressources  → onglet "New Growing List" (col B main_keyword)
    3. gsc     — top query par impressions/clicks sur 12 mois (API GSC directe).
    4. slug    — slug de l'URL normalisé (dernier recours, jamais None).

⚠️ IMPORTANT — onglets réels : l'ancien onglet "Refreshs_Audit" n'existe plus
dans les Google Sheets réels (il provoque un HTTP 400). Ce module lit donc
directement les onglets réels par blog, il ne dépend PAS de RefreshAuditRow.

Utilisation :
    resolver = KeywordResolver()
    kw, source = resolver.resolve("enseigna", url="https://enseigna.fr/acadomia-avis/")
    # kw = "acadomia avis", source = "sheet" (ou "notion"/"gsc"/"slug")
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


# Ordre de priorité par défaut si la config blog ne le précise pas.
DEFAULT_KEYWORD_SOURCES = ["notion", "sheet", "gsc", "slug"]

# Sources DÉCLARATIVES : un humain a saisi le mot-clé (Notion, Sheet). Elles sont
# faillibles — une colonne "Main Keyword" peut contenir un fragment récupéré à
# l'arrachée ("un exemple", "des signaux") qui n'est la requête de personne.
# Ces sources sont donc CONFRONTÉES à GSC avant usage (cf. _validate_against_gsc).
# `gsc` et `slug` ne le sont pas : la première EST la mesure, la seconde est un
# dernier recours qui n'a de toute façon rien à valider.
_DECLARATIVE_SOURCES = ("notion", "sheet")

# Dernier verdict de validation GSC, pour journalisation par l'appelant
# (persisté dans audit_data.json). Réinitialisé à chaque resolve().
KEYWORD_VALIDATION_KEY = "keyword_validation"

# Mapping site_slug → (env var du spreadsheet, onglets à scanner, index colonne du mot-clé)
# Les onglets et index sont ceux VÉRIFIÉS EN LIVE (juillet 2026).
_SHEET_LAYOUT = {
    "enseigna": {
        "spreadsheet_env": "SPREADSHEET_ID_ENSEIGNA",
        # (onglet, index_url, index_keyword)
        "tabs": [
            ("Avis", 0, 1),        # A=url, B=top_keyword
            ("Versus", 0, 1),      # A=url, B=top_keyword (pas de kw dédié → fallback col B si présent)
            ("A ajouter", 0, 3),   # A=url, D=main_keyword (nouveaux articles)
        ],
    },
    "superprof.fr-ressources": {
        "spreadsheet_env": "SPREADSHEET_ID_SUPERPROF",
        "tabs": [
            ("New Growing List", 0, 1),  # A=url, B=main_keyword
        ],
    },
}


def _resolve_sheet_layout(site_slug: str) -> dict | None:
    """Layout des onglets Sheet d'un site.

    Source de vérité : le bloc `sheets` de sites/{id}/config/site.json
    (externalisé en Phase 4bis-A). Repli sur la constante _SHEET_LAYOUT si la
    config est absente/incomplète, pour ne pas casser un site non encore migré.
    """
    try:
        from _shared.core.site_paths import SitePaths
        import json
        cfg_path = SitePaths().site_config(site_slug)
        if cfg_path.exists():
            sheets = json.loads(cfg_path.read_text(encoding="utf-8")).get("sheets", {})
            tabs = sheets.get("tabs")
            env = sheets.get("spreadsheet_env")
            if tabs and env:
                return {
                    "spreadsheet_env": env,
                    "tabs": [
                        (t["name"], t.get("col_url", 0), t.get("col_keyword", 1))
                        for t in tabs
                    ],
                }
    except Exception as e:
        logger.warning(f"[KeywordResolver] lecture sheets config '{site_slug}' échouée: {e}")
    return _SHEET_LAYOUT.get(site_slug)


def _norm_kw(kw: str) -> str:
    """Normalise un mot-clé pour comparaison avec les requêtes GSC."""
    return re.sub(r"\s+", " ", (kw or "").strip().lower())


def _norm_url(url: str) -> str:
    """Normalise une URL pour comparaison (minuscules, sans slash final)."""
    return (url or "").strip().rstrip("/").lower()


def slug_to_keyword(url_or_slug: str) -> str:
    """
    Dérive un mot-clé lisible depuis un slug d'URL (dernier recours).

    Ex: "https://enseigna.fr/acadomia-avis/" → "acadomia avis"
    """
    if not url_or_slug:
        return ""
    slug = url_or_slug.strip().rstrip("/").split("/")[-1]
    slug = re.sub(r"\.(html?|php)$", "", slug)
    return slug.replace("-", " ").replace("_", " ").strip()


# Un clic isolé n'est pas un signal : sur une page à faible trafic, une requête
# parasite peut capter 1 clic accidentel et supplanter une requête à 16, 39 ou 270
# impressions qui, elle, décrit vraiment le sujet de la page. En dessous de ce
# seuil, les clics sont considérés comme absents et les impressions tranchent.
MIN_SIGNIFICANT_CLICKS = 3

# Nombre de requêtes GSC lues par URL pour l'arbitrage. > 20 pour sortir du
# plafond MCP (cf. _validate_against_gsc).
_GSC_QUERY_ROWS = 200


def _best_gsc_candidate(top: list[dict]) -> Optional[dict]:
    """Meilleure requête GSC : le plus de clics, sinon le plus d'impressions.

    « Sinon » couvre l'absence de clics SIGNIFICATIFS, pas seulement le zéro
    absolu (cf. MIN_SIGNIFICANT_CLICKS).
    """
    if not top:
        return None
    clicked = [k for k in top if (k.get("clicks") or 0) >= MIN_SIGNIFICANT_CLICKS]
    if clicked:
        return max(clicked, key=lambda k: (k.get("clicks") or 0, k.get("impressions") or 0))
    return max(top, key=lambda k: (k.get("impressions") or 0, k.get("clicks") or 0))


class KeywordResolver:
    """
    Résout le mot-clé principal d'une URL en interrogeant plusieurs sources.

    Les clients (Notion, Sheets, GSC) sont lazy-init et graceful : si une source
    n'est pas configurée, elle est silencieusement sautée et on passe à la suivante.
    """

    def __init__(
        self,
        notion_client=None,
        sheets_client_factory=None,
        gsc_analyzer=None,
        notion_db_resolver=None,
    ):
        """
        Args:
            notion_client: instance NotionClient (optionnel, lazy sinon).
            sheets_client_factory: callable(spreadsheet_id) -> SheetsClient (lazy sinon).
            gsc_analyzer: instance GSCAnalyzer (optionnel, lazy sinon).
            notion_db_resolver: callable(site_slug) -> notion_commandes_db_id | None.
        """
        self._notion = notion_client
        self._sheets_factory = sheets_client_factory
        self._gsc = gsc_analyzer
        self._notion_db_resolver = notion_db_resolver
        # Cache par blog pour éviter de relire un onglet à chaque URL.
        self._sheet_index_cache: dict[str, dict] = {}
        self._notion_cache: dict[str, dict] = {}
        # Verdict de la dernière validation GSC (cf. _validate_against_gsc).
        # Toujours présent : l'appelant le persiste sans avoir à tester l'attribut.
        self.last_validation: dict = {}

    # ------------------------------------------------------------------
    # Point d'entrée
    # ------------------------------------------------------------------

    def resolve(
        self,
        site_slug: str,
        url: str = "",
        slug: str = "",
        sources: Optional[list[str]] = None,
    ) -> tuple[str, str]:
        """
        Retourne (main_keyword, source) pour cette URL/blog.

        source ∈ {"notion", "sheet", "gsc", "slug", "none"}.
        Le mot-clé n'est jamais None : au pire slug, au pire-pire "".
        """
        order = sources or DEFAULT_KEYWORD_SOURCES

        for src in order:
            try:
                if src == "notion":
                    kw = self._from_notion(site_slug, url)
                elif src == "sheet":
                    kw = self._from_sheet(site_slug, url)
                elif src == "gsc":
                    kw = self._from_gsc(site_slug, url)
                elif src == "slug":
                    kw = slug_to_keyword(url or slug)
                else:
                    logger.warning(f"[KeywordResolver] Source inconnue ignorée: {src}")
                    continue
            except Exception as e:
                logger.warning(f"[KeywordResolver] Source '{src}' en erreur (ignorée): {e}")
                continue

            if kw:
                logger.info(f"[KeywordResolver] {site_slug} '{url}' → '{kw}' (source={src})")
                if src in _DECLARATIVE_SOURCES:
                    kw, src = self._validate_against_gsc(site_slug, url, kw, src)
                return kw, src

        # Aucun résultat même via slug
        return "", "none"

    # ------------------------------------------------------------------
    # Sources
    # ------------------------------------------------------------------

    def _from_notion(self, site_slug: str, url: str) -> str:
        """Cherche la 'Requête YTG' d'une commande Notion matchant l'URL."""
        db_id = self._resolve_notion_db(site_slug)
        if not db_id:
            return ""

        index = self._notion_cache.get(site_slug)
        if index is None:
            notion = self._get_notion()
            if notion is None:
                return ""
            commandes = notion.get_commandes(db_id, site_slug=site_slug)
            index = {}
            for c in commandes:
                if c.ytg_keyword:
                    if c.url:
                        index[_norm_url(c.url)] = c.ytg_keyword.strip()
            self._notion_cache[site_slug] = index

        return index.get(_norm_url(url), "")

    def _from_sheet(self, site_slug: str, url: str) -> str:
        """Cherche le mot-clé dans l'onglet réel du blog (service account)."""
        layout = _resolve_sheet_layout(site_slug)
        if not layout:
            return ""

        index = self._sheet_index_cache.get(site_slug)
        if index is None:
            index = self._build_sheet_index(site_slug, layout)
            self._sheet_index_cache[site_slug] = index

        return index.get(_norm_url(url), "")

    def _validate_against_gsc(
        self, site_slug: str, url: str, declared: str, src: str
    ) -> tuple[str, str]:
        """Confronte un mot-clé DÉCLARÉ (Notion/Sheet) aux requêtes réelles GSC.

        Pourquoi : les sources déclaratives sont faillibles et leur erreur est
        invisible en aval — toute la chaîne (SERP, guide YTG, sources, rédaction)
        répond alors à une requête que personne ne tape, silencieusement, une fois
        par URL. GSC est la seule source qui observe le comportement réel.

        Règle d'arbitrage (arbitrage métier, SEO Manager) : le mot-clé retenu est
        celui qui a le PLUS DE CLICS ; si les clics sont absents (page à zéro clic
        sur la fenêtre), celui qui a le PLUS D'IMPRESSIONS. C'est exactement le tri
        de `fetch_top_keywords_12m` — on lui délègue plutôt que de le redériver.

        Trois issues :
          * déclaré présent dans les requêtes GSC → validé (source `<src>+gsc`) ;
          * déclaré absent et GSC a du signal    → CORRIGÉ vers le top GSC ;
          * GSC muet (page neuve, 0 impression)  → déclaré conservé, non vérifié.

        Ne lève jamais : GSC indisponible ne doit pas bloquer un refresh.
        """
        self.last_validation = {
            "declared": declared,
            "declared_source": src,
            "status": "unverified",
            "final": declared,
        }

        try:
            gsc = self._get_gsc(site_slug)
            if gsc is None:
                return declared, src
            # NB fenêtre : le MCP plafonne à 20 lignes ET les renvoie triées par
            # clics. Sur une page à faible trafic, les requêtes fortes en
            # IMPRESSIONS tombent alors hors fenêtre : « ensemble de définition
            # exercice corrigé » (39 impressions) était invisible, et l'arbitrage
            # se faisait sur un reliquat à 6 impressions. On demande donc un
            # volume large, ce qui route la lecture vers le service account
            # (paginé) au lieu du MCP tronqué.
            top = gsc.fetch_top_keywords_12m(url, limit=_GSC_QUERY_ROWS)
        except Exception as e:
            logger.warning(f"[KeywordResolver] validation GSC impossible ({e}) — mot-clé déclaré conservé.")
            return declared, src

        if not top:
            logger.info(
                f"[KeywordResolver] GSC muet pour '{url}' — '{declared}' conservé (non vérifié)."
            )
            return declared, src

        best = _best_gsc_candidate(top)
        if best is None:
            return declared, src
        if _norm_kw(declared) == _norm_kw(best.get("query") or ""):
            self.last_validation.update(status="confirmed")
            logger.info(f"[KeywordResolver] '{declared}' confirmé par GSC (top requête).")
            return declared, f"{src}+gsc"

        candidate = (best.get("query") or "").strip()
        if not candidate:
            return declared, src

        self.last_validation.update(
            status="corrected",
            final=candidate,
            gsc_clicks=best.get("clicks", 0),
            gsc_impressions=best.get("impressions", 0),
            basis="clics" if (best.get("clicks") or 0) >= MIN_SIGNIFICANT_CLICKS else "impressions",
            top_queries=[
                {"query": k.get("query"), "clicks": k.get("clicks"), "impressions": k.get("impressions")}
                for k in top[:5]
            ],
        )
        by_clicks = (best.get("clicks") or 0) >= MIN_SIGNIFICANT_CLICKS
        basis = "clics" if by_clicks else "impressions"
        value = best.get("clicks") if by_clicks else best.get("impressions")
        logger.warning(
            f"[KeywordResolver] CONFLIT mot-clé sur '{url}' : déclaré '{declared}' "
            f"n'est pas la requête dominante → corrigé en '{candidate}' "
            f"({basis}={value})."
        )
        return candidate, f"gsc_corrected(from_{src})"

    def _from_gsc(self, site_slug: str, url: str) -> str:
        """Top query GSC 12 mois pour cette URL."""
        if not url:
            return ""
        gsc = self._get_gsc(site_slug)
        if gsc is None:
            return ""
        kw = gsc.fetch_top_keyword_12m(url)
        return (kw or "").strip()

    # ------------------------------------------------------------------
    # Construction d'index (avec cache)
    # ------------------------------------------------------------------

    def _build_sheet_index(self, site_slug: str, layout: dict) -> dict:
        """Construit {url_norm: keyword} depuis les onglets réels du blog."""
        import os

        sid = os.environ.get(layout["spreadsheet_env"], "")
        if not sid:
            logger.warning(
                f"[KeywordResolver] {layout['spreadsheet_env']} absent — source sheet sautée pour {site_slug}"
            )
            return {}

        sheets = self._get_sheets(sid)
        if sheets is None:
            return {}

        index: dict[str, str] = {}
        for tab, url_idx, kw_idx in layout["tabs"]:
            try:
                data = sheets._read_sheet(tab)
            except Exception as e:
                logger.warning(f"[KeywordResolver] lecture onglet '{tab}' échouée: {e}")
                continue
            if not data:
                continue
            for row in data[1:]:  # skip header
                if len(row) <= url_idx:
                    continue
                u = _norm_url(row[url_idx])
                if not u:
                    continue
                kw = row[kw_idx].strip() if len(row) > kw_idx and row[kw_idx] else ""
                # Ne pas écraser un mot-clé déjà trouvé dans un onglet prioritaire
                if kw and u not in index:
                    index[u] = kw
        logger.info(f"[KeywordResolver] index sheet {site_slug}: {len(index)} URLs")
        return index

    def _resolve_notion_db(self, site_slug: str) -> Optional[str]:
        if self._notion_db_resolver is not None:
            try:
                return self._notion_db_resolver(site_slug)
            except Exception:
                return None
        # Fallback : lire sites.json
        return self._notion_db_from_sites_json(site_slug)

    @staticmethod
    def _notion_db_from_sites_json(site_slug: str) -> Optional[str]:
        import json
        from pathlib import Path

        try:
            base = Path(__file__).resolve().parent.parent.parent
            sites_path = base / "_shared" / "config" / "sites.json"
            if not sites_path.exists():
                return None
            with open(sites_path) as f:
                data = json.load(f)
            for site in data.get("sites", []):
                if (site.get("site_slug") or site.get("id")) == site_slug:
                    return site.get("notion_commandes_db_id") or None
        except Exception:
            return None
        return None

    # ------------------------------------------------------------------
    # Lazy getters
    # ------------------------------------------------------------------

    def _get_notion(self):
        if self._notion is None:
            try:
                from scripts.notion.notion_client import NotionClient
                self._notion = NotionClient()
            except Exception as e:
                logger.warning(f"[KeywordResolver] NotionClient indisponible: {e}")
                self._notion = None
        return self._notion

    def _get_sheets(self, spreadsheet_id: str):
        try:
            if self._sheets_factory is not None:
                return self._sheets_factory(spreadsheet_id)
            from scripts.sheets.sheets_client import SheetsClient
            return SheetsClient(spreadsheet_id=spreadsheet_id)
        except Exception as e:
            logger.warning(f"[KeywordResolver] SheetsClient indisponible: {e}")
            return None

    # GSC analyzers sont par-blog (une gsc_property chacun) → cache par site_slug.
    def _get_gsc(self, site_slug: str):
        if self._gsc is not None:
            return self._gsc  # instance injectée explicitement
        cached = getattr(self, "_gsc_by_blog", None)
        if cached is None:
            cached = {}
            self._gsc_by_blog = cached
        if site_slug not in cached:
            prop = self._gsc_property_for_blog(site_slug)
            if not prop:
                cached[site_slug] = None
            else:
                try:
                    from scripts.audit.gsc_analyzer import GSCAnalyzer
                    cached[site_slug] = GSCAnalyzer(prop)
                except Exception as e:
                    logger.warning(f"[KeywordResolver] GSCAnalyzer indisponible: {e}")
                    cached[site_slug] = None
        return cached[site_slug]

    @staticmethod
    def _gsc_property_for_blog(site_slug: str) -> str:
        """Lit gsc_property depuis _shared/config/blogs/{site_slug}.json."""
        import json
        from pathlib import Path

        try:
            base = Path(__file__).resolve().parent.parent.parent
            from _shared.core.site_paths import SitePaths
            cfg_path = SitePaths(base_path=base).site_config(site_slug)
            if not cfg_path.exists():
                return ""
            with open(cfg_path) as f:
                return json.load(f).get("gsc_property", "") or ""
        except Exception:
            return ""
