"""Source de lignes « publications » lue depuis une base Notion.

Pendant Notion de `gsc_tab_perf._read_tab_rows` : même contrat de sortie
([{row, url, keyword, status, ...}]), de sorte que tout le moteur de monitoring
(fenêtres GSC, deltas, agrégats, rapport HTML) est réutilisé tel quel — seule la
provenance des URLs change.

La base de suivi porte les colonnes de publication (URL, statut de refresh,
catégorie, date de publication) ; le monitoring ne lit que les lignes **en
ligne**, c'est-à-dire celles qui portent une URL http : une ligne sans URL est
un article à produire, pas un article dont on peut mesurer les performances.

Config : bloc `notion.publications` du site.json ::

    "notion": {
      "publications": {
        "database_id": "28cd6418-695a-8071-990e-dd3824d477d9",
        "col_url": "URL",
        "col_keyword": "Mot-clé cible",
        "col_status": "Statut de refresh",
        "col_category": "Catégorie",
        "col_published": "Date de publication"
      }
    }
"""

import json
from typing import Optional


def _plain(prop: Optional[dict]) -> str:
    """Aplati une propriété Notion en texte (chaîne vide si absente/vide).

    Ne couvre que les types portés par la base de suivi : les colonnes de
    publication sont des title/rich_text/select/multi_select/date/url.
    """
    if not prop:
        return ""
    kind = prop.get("type", "")
    value = prop.get(kind)
    if value in (None, [], {}):
        return ""
    if kind in ("title", "rich_text"):
        return "".join(x.get("plain_text", "") for x in value).strip()
    if kind == "select":
        return (value.get("name") or "").strip()
    if kind == "multi_select":
        return ", ".join((x.get("name") or "").strip() for x in value)
    if kind == "date":
        return (value.get("start") or "").strip()
    if kind == "url":
        return (value or "").strip()
    if kind == "formula":
        return _plain({"type": value.get("type"), value.get("type"): value.get(value.get("type"))})
    return ""


def get_notion_pub_config(site: str) -> dict:
    """Retourne le bloc notion.publications du site, ou lève si absent."""
    from _shared.core.site_paths import SitePaths
    cfg_path = SitePaths().site_config(site)
    cfg = {}
    if cfg_path.exists():
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    pub = ((cfg.get("notion") or {}).get("publications")) or {}
    if not pub.get("database_id"):
        raise ValueError(
            f"Pas de notion.publications.database_id dans la config de {site}. "
            "Déclare le bloc notion.publications dans sites/<site>/config/site.json."
        )
    return pub


def read_publication_rows(site: str) -> list[dict]:
    """Lit la base Notion de suivi → [{row, url, keyword, status, ...}].

    Seules les lignes portant une URL http sont retournées (les autres sont des
    articles pas encore publiés : rien à mesurer côté GSC).
    """
    pub = get_notion_pub_config(site)

    from scripts.notion import NotionClient
    client = NotionClient()
    if not client.is_configured:
        raise RuntimeError(
            "NOTION_TOKEN manquant (.env ou ~/.credentials/notion/credentials.json)"
        )

    pages = client.query_database(pub["database_id"])
    if not pages:
        raise RuntimeError(
            f"Base Notion {pub['database_id']} vide ou inaccessible — "
            "vérifier que l'intégration a bien été partagée sur la page."
        )

    col_url = pub.get("col_url", "URL")
    col_kw = pub.get("col_keyword", "Mot-clé cible")
    col_status = pub.get("col_status", "Statut de refresh")
    col_cat = pub.get("col_category", "Catégorie")
    col_pub = pub.get("col_published", "Date de publication")

    rows = []
    for i, page in enumerate(pages, start=1):
        props = page.get("properties", {})
        url = _plain(props.get(col_url))
        if not url.startswith("http"):
            continue
        rows.append({
            "row": i,
            "url": url,
            "keyword": _plain(props.get(col_kw)),
            "status": _plain(props.get(col_status)) or "(sans statut)",
            "category": _plain(props.get(col_cat)) or "(sans catégorie)",
            "published": _plain(props.get(col_pub)),
            "notion_page_id": page.get("id", ""),
        })
    return rows
