"""Classification du sous-type d'article (avis / versus) à partir de l'URL.

Point unique de vérité pour router un article vers son sous-dossier de sortie
(`html/{type}/`) et son prompt (`site.md` vs `vs_concurrent.md`). La règle est
celle déjà appliquée en prod pour peupler les onglets Sheet "Avis"/"Versus"
(cf. scripts/audit/enseigna_refresh_list.py, `_bucket`).

Aujourd'hui seul le site `enseigna` distingue avis/versus ; les autres sites
n'ont pas de sous-typage → `classify_article_type` renvoie None (sortie à plat).
"""

from __future__ import annotations

from typing import Optional
from urllib.parse import urlparse


def _slug(url: str) -> str:
    """Dernier segment de chemin de l'URL (le slug de l'article)."""
    path = urlparse(url).path.strip("/")
    return path.rsplit("/", 1)[-1] if path else ""


def classify_article_type(url: str, site_slug: Optional[str] = None) -> Optional[str]:
    """Retourne "avis", "versus" ou None selon le slug de l'URL.

    Règle (enseigna) — identique à enseigna_refresh_list._bucket :
      - slug commençant par `superprof-vs-`  → "versus"
      - slug contenant `avis`                → "avis"
      - sinon                                → None (pas de sous-typage)

    site_slug est accepté pour une future divergence par site ; ignoré tant que
    seul enseigna sous-type.
    """
    slug = _slug(url).lower()
    if slug.startswith("superprof-vs-"):
        return "versus"
    if "avis" in slug:
        return "avis"
    return None
