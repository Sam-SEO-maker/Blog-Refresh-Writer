"""Pont Sheet → Notion pour les commandes éditoriales (base « orders »).

Le mot-clé principal d'un article naît d'un signal GSC et vit dans la Google
Sheet ; il est ensuite recopié à la main dans la base Notion où la Product Owner
commande les articles aux rédacteurs. Ce recopiage apparie les lignes **par
position**, ce qui a produit un décalage d'un cran sur une plage entière de
l'onglet « Medium Potential » : chaque ligne Notion portait le mot-clé de la
ligne précédente, si bien qu'un article de maths s'est retrouvé commandé sur
« corrosion ».

Ce module apparie **par URL normalisée**. Un décalage de lignes devient
impossible par construction, et non plus par vigilance.

Trois colonnes seulement sont écrites (`Local resource URL`, `Main KW`,
`Type of article`) : tout le reste de la base — Writer, Deadline, Price, Status,
Keywords — est la main de la PO et n'est jamais touché.

Config : bloc `notion.orders` du site.json ::

    "notion": {
      "orders": {
        "database_id": "1ebd6418-695a-80ff-8cc9-db41a02d7f27",
        "col_url": "Local resource URL",
        "col_keyword": "Main KW",
        "col_type": "Type of article",
        "type_value": "Refresh",
        "country_page_id": "4d06ca37-4111-4b09-81d9-b6d55697bef8"
      }
    }
"""

import json
import re
from typing import Optional

# Une ligne Notion dont le mot-clé est celui d'une AUTRE ligne de la Sheet est la
# signature d'un copier-coller décalé : la preuve est dans la donnée elle-même.
# Une simple reformulation ("adn" là où la Sheet dit "cellule svt") n'a pas cette
# signature et peut être un arbitrage éditorial délibéré de la PO.
KIND_SHIFTED = "shifted"
KIND_REWORDED = "reworded"
KIND_MISSING = "missing"
KIND_ABSENT = "absent"


def normalize_url(url: str) -> str:
    """Clé d'appariement : sans protocole, sans www, sans slash final."""
    u = (url or "").strip().lower()
    u = re.sub(r"^https?://", "", u)
    u = re.sub(r"^www\.", "", u)
    return u.rstrip("/")


def _norm_kw(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def get_orders_config(site: str) -> dict:
    """Retourne le bloc notion.orders du site, ou lève si absent."""
    from _shared.core.site_paths import SitePaths

    cfg_path = SitePaths().site_config(site)
    cfg = {}
    if cfg_path.exists():
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    orders = ((cfg.get("notion") or {}).get("orders")) or {}
    if not orders.get("database_id"):
        raise ValueError(
            f"Pas de notion.orders.database_id dans la config de {site}. "
            "Déclare le bloc notion.orders dans sites/<site>/config/site.json."
        )
    return orders


def _plain(prop: Optional[dict]) -> str:
    """Aplatit une propriété Notion en texte (chaîne vide si absente/vide)."""
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
    if kind == "url":
        return (value or "").strip()
    return ""


def read_order_rows(site: str) -> list[dict]:
    """Lit la base de commandes Notion → [{url, keyword, type, page_id}].

    Ne retient que les lignes portant une URL http du site : la base est
    multi-pays (colonne Country) et les lignes des autres marchés ne doivent
    jamais être touchées par un pont FR.
    """
    orders = get_orders_config(site)

    from scripts.notion import NotionClient

    client = NotionClient()
    if not client.is_configured:
        raise RuntimeError(
            "NOTION_TOKEN manquant (.env ou ~/.credentials/notion/credentials.json)"
        )

    pages = client.query_database(orders["database_id"])
    if not pages:
        raise RuntimeError(
            f"Base Notion {orders['database_id']} vide ou inaccessible — "
            "vérifier que l'intégration a bien été partagée sur la page."
        )

    col_url = orders.get("col_url", "Local resource URL")
    col_kw = orders.get("col_keyword", "Main KW")
    col_type = orders.get("col_type", "Type of article")
    domain = orders.get("url_filter", "")

    rows = []
    for page in pages:
        props = page.get("properties", {})
        url = _plain(props.get(col_url))
        if not url.startswith("http"):
            continue
        if domain and domain not in url:
            continue
        rows.append({
            "url": url,
            "keyword": _plain(props.get(col_kw)),
            "type": _plain(props.get(col_type)),
            "page_id": page.get("id", ""),
        })
    return rows


def build_plan(sheet_rows: list[dict], notion_rows: list[dict]) -> list[dict]:
    """Compare Sheet et Notion sur la clé URL → liste d'écarts qualifiés.

    `sheet_rows` et `notion_rows` suivent le contrat {url, keyword, ...}.
    Chaque écart porte un `kind` qui dit *pourquoi* il diverge, car la réponse
    n'est pas la même selon les cas : un décalage se corrige les yeux fermés,
    une reformulation demande un arbitrage humain.
    """
    by_url = {normalize_url(r["url"]): r for r in sheet_rows if r.get("url")}
    # Index inverse : quel mot-clé appartient à quelle URL de la Sheet ?
    kw_owner: dict[str, str] = {}
    for key, row in by_url.items():
        kw = _norm_kw(row.get("keyword"))
        if kw:
            kw_owner.setdefault(kw, key)

    plan = []
    for n_row in notion_rows:
        key = normalize_url(n_row["url"])
        s_row = by_url.get(key)
        if s_row is None:
            plan.append({**n_row, "kind": KIND_ABSENT, "sheet_keyword": ""})
            continue

        target = (s_row.get("keyword") or "").strip()
        current = (n_row.get("keyword") or "").strip()
        if not target or _norm_kw(current) == _norm_kw(target):
            continue

        if not current:
            kind = KIND_MISSING
        else:
            owner = kw_owner.get(_norm_kw(current))
            kind = KIND_SHIFTED if owner and owner != key else KIND_REWORDED

        plan.append({
            **n_row,
            "kind": kind,
            "sheet_keyword": target,
            "sheet_tab": s_row.get("tab", ""),
            "sheet_row": s_row.get("row", ""),
        })
    return plan


def apply_plan(site: str, plan: list[dict], kinds: set[str]) -> tuple[int, int]:
    """Écrit `Main KW` sur les lignes du plan dont le `kind` est retenu.

    N'écrit que la colonne mot-clé : l'URL sert de clé (elle est déjà juste) et
    le type est constant sur les lignes existantes. Retourne (écrites, échecs).
    """
    orders = get_orders_config(site)
    col_kw = orders.get("col_keyword", "Main KW")

    from scripts.notion import NotionClient

    client = NotionClient()
    written = failed = 0
    for item in plan:
        if item["kind"] not in kinds:
            continue
        props = {
            col_kw: {"rich_text": [{"text": {"content": item["sheet_keyword"]}}]}
        }
        if client.update_page(item["page_id"], props):
            written += 1
        else:
            failed += 1
    return written, failed
