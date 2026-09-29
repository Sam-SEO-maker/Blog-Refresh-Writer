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

`database_id` doit être celui de la base **source**, pas celui qu'affiche l'URL
Notion : la section « Ressources section » de la page de commandes est une *base
liée*, et l'API refuse explicitement les bases liées (« Database retrievals do
not support linked databases »). L'ID source se lit sur la data source elle-même
(`data_source_id` ci-dessous) ; l'ID lié est conservé sous `linked_database_id`
pour que personne ne le remette par erreur en croyant corriger la config.

Config : bloc `notion.orders` du site.json ::

    "notion": {
      "orders": {
        "database_id": "6dc43079-14bb-430b-bd32-4db038eb1086",
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
import time
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


# ---------------------------------------------------------------------------
# Création de commandes (Sheet → Notion)
# ---------------------------------------------------------------------------
#
# Le pont ci-dessus corrige des lignes Notion qui existent déjà. Commander un
# lot, c'est l'étape d'avant : la Sheet porte les URLs retenues et leur mot-clé,
# la PO attend une ligne par article dans « Resources - Main Database ».
#
# Trois colonnes seulement sont écrites, exactement celles que portent les
# lignes récentes de la base : l'URL, le mot-clé, et le type « Refresh ». La
# relation Country vient de la config (`country_page_id`) : sans elle la ligne
# n'apparaît dans aucune vue pays, donc invisible pour la PO. Tout le reste
# (Writer, Deadline, Price, Status, Month) reste sa main.
#
# `Title (Main KW)` est laissé vide à dessein : les lignes de refresh créées
# jusqu'ici n'en portent pas, et c'est l'URL qui identifie l'article.

KIND_CREATE = "create"
KIND_EXISTS = "exists"


def build_create_plan(
    sheet_rows: list[dict],
    notion_rows: list[dict],
) -> list[dict]:
    """Classe les lignes Sheet en « à créer » / « déjà commandée ».

    L'appariement se fait sur l'URL normalisée, comme `build_plan` : une URL
    déjà présente dans la base ne redonne jamais lieu à une commande, même si
    son mot-clé diverge (c'est le travail de `push_keywords`, pas celui-ci).

    Une ligne déjà présente porte son `keyword` Notion et son `page_id`, pour
    que l'appelant puisse dire *pourquoi* elle est écartée et proposer une
    correction de mot-clé plutôt qu'un doublon.

    Le plan sort **dans l'ordre des lignes de la Sheet**, et non dans celui où
    l'onglet a été lu. C'est la garantie qui manque au copier-coller manuel :
    coller dix URLs d'un bloc les fait arriver dans un ordre arbitraire côté
    Notion, alors que la Sheet porte un ordre de travail (la plage `--rows`
    qu'on a décidé de commander). `apply_create_plan` crée ensuite une ligne
    à la fois dans cet ordre, si bien que le tri par date de création de la
    base reproduit le lot tel qu'il a été demandé.
    """
    known = {normalize_url(r["url"]): r for r in notion_rows if r.get("url")}

    # Le tri est explicite plutôt que dépendant de l'ordre de lecture : une URL
    # commandée hors de son rang se retrouve noyée dans la base, et c'est
    # exactement ce qu'on cherche à supprimer.
    ordered = sorted(sheet_rows, key=lambda r: r.get("row") or 0)

    plan = []
    seen: set[str] = set()
    for s_row in ordered:
        url = (s_row.get("url") or "").strip()
        if not url:
            continue
        key = normalize_url(url)

        # Une URL en double dans la Sheet ne doit produire qu'une commande.
        if key in seen:
            continue
        seen.add(key)

        n_row = known.get(key)
        if n_row is not None:
            plan.append({
                **s_row,
                "kind": KIND_EXISTS,
                "notion_keyword": n_row.get("keyword", ""),
                "page_id": n_row.get("page_id", ""),
            })
        else:
            plan.append({**s_row, "kind": KIND_CREATE})
    return plan


def build_order_properties(orders: dict, url: str, keyword: str) -> dict:
    """Construit le payload Notion d'une commande de refresh.

    Isolé de l'appel réseau pour rester testable : c'est ici que se joue la
    conformité au schéma de la base (« Type of article » est un multi_select,
    pas un select — une valeur scalaire y est rejetée par l'API).
    """
    col_url = orders.get("col_url", "Local resource URL")
    col_kw = orders.get("col_keyword", "Main KW")
    col_type = orders.get("col_type", "Type of article")
    type_value = orders.get("type_value", "Refresh")

    props: dict = {
        col_url: {"url": url},
        col_type: {"multi_select": [{"name": type_value}]},
    }
    if keyword:
        props[col_kw] = {"rich_text": [{"text": {"content": keyword}}]}

    # Sans la relation pays, la ligne n'entre dans aucune vue marché : elle est
    # créée mais personne ne la voit. On ne l'omet que si la config n'en donne pas.
    country_page_id = orders.get("country_page_id")
    col_country = orders.get("col_country", "Country")
    if country_page_id:
        props[col_country] = {"relation": [{"id": country_page_id}]}

    return props


# Notion date les pages à la seconde : deux créations dans la même seconde ne
# sont plus départageables. Une seconde pleine est le plus petit espacement qui
# garantit un `createdTime` strictement croissant.
ORDER_SPACING_SECONDS = 1.1


def apply_create_plan(
    site: str,
    plan: list[dict],
    order_spacing_seconds: float = ORDER_SPACING_SECONDS,
) -> tuple[int, int, list[dict]]:
    """Crée dans Notion les lignes du plan marquées `create`.

    Les créations partent **séquentiellement, dans l'ordre du plan**, espacées
    d'au moins une seconde. Les deux conditions sont nécessaires et ont été
    vérifiées contre la vraie base : trois lignes créées d'un bloc y portent la
    même `createdTime` à la seconde près (Notion ne stocke pas les
    sous-secondes) et ressortent dans un ordre arbitraire — 2, 3, 1 lors du
    test. La vue de commande ne déclare aucun tri, donc rien en aval ne
    rattrape un ordre perdu à l'écriture. C'est précisément le défaut du
    copier-coller manuel que cette commande remplace : dix URLs collées d'un
    bloc arrivent mélangées.

    Le coût est d'une seconde par ligne, sur des lots de quelques dizaines :
    négligeable face à un lot qu'il faut ensuite réordonner à la main.

    Retourne (créées, échecs, échecs détaillés). Un échec n'interrompt pas le
    lot : une commande ratée se rejoue, et laisser passer les suivantes évite
    de redemander à l'appelant un lot déjà à moitié écrit.
    """
    orders = get_orders_config(site)
    database_id = orders["database_id"]

    from scripts.notion import NotionClient

    client = NotionClient()
    created = 0
    failures: list[dict] = []
    to_create = [item for item in plan if item["kind"] == KIND_CREATE]
    for n, item in enumerate(to_create):
        # Espacement : voir la docstring. Jamais avant la première ligne, pour
        # qu'une commande unitaire reste instantanée.
        if n:
            time.sleep(order_spacing_seconds)
        props = build_order_properties(
            orders, item["url"], (item.get("keyword") or "").strip()
        )
        if client.create_page(database_id, props):
            created += 1
        else:
            failures.append(item)
    return created, len(failures), failures
