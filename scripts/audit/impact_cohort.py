"""Rapport d'impact mensuel : chaque article republié comparé à lui-même,
un an plus tôt, à date fixe.

Différence avec `gsc_tab_perf` (audit gsc-tab), et raison d'être de ce module :
`gsc-tab` mesure **un périmètre** (onglet entier, articles traités ou non) sur
**un mois calendaire**, ancré sur le calendrier plutôt que sur les
republications. Ce module-ci mesure **le lot des articles effectivement
retravaillés**, chacun sur sa propre fenêtre année-sur-année ancrée sur SA
date de republication. Les deux peuvent diverger fortement sans qu'aucune ne
soit fausse : elles ne répondent pas à la même question (voir la skill
`impact-report` pour l'exemple chiffré).

Ici chaque article est sa propre unité de mesure :

- **fenêtre année-sur-année propre à l'article** : les N jours qui suivent sa
  republication contre les N jours qui suivent la même date un an plus tôt
  (`pushed - 365 j`), à durée strictement égale, N étant le recul que la date
  d'export autorise côté « après » (plafonné à `--maturity`). Comparer les
  mêmes dates calendaires à un an d'écart élimine la saisonnalité par
  construction, plutôt que de la déduire après coup ;
- **groupe de contrôle** : le reste du site (total GSC moins les articles
  traités), comparé lui aussi à J-365 sur exactement les mêmes paires de
  dates que chaque vague. La saisonnalité étant déjà éliminée par la
  construction YoY, ce contrôle capte surtout une dérive de marché
  résiduelle (le reste du site progresse ou régresse structurellement d'une
  année sur l'autre) plutôt qu'un effet de saison ;
- **cohortes** : les articles regroupés par vague de republication, pour que
  le contrôle se calcule sur les mêmes paires de dates que les articles
  qu'il sert de référence.

Source des republications : la trace locale `outputs/<site>/wp_backups/`, un
fichier écrit à chaque première publication — elle date l'**acte de refresh**.
Ni la colonne « Date de refresh » de la Sheet (saisie manuelle, incomplète,
parfois datée du futur), ni le champ `modified` de WordPress : celui-ci
enregistre la *dernière modification quelconque* du post, si bien qu'une
correction manuelle ou une passe de QC ultérieure l'écrase. Mesuré sur août
2026, 69 des 78 articles avaient un `modified` postérieur à leur refresh — les
dater ainsi les aurait tous déplacés en septembre.

`modified` sert donc de **contrôle de cohérence** et non de source : il
signale les articles retouchés après leur refresh, dont la fenêtre « après »
mélange deux interventions. Le rapport les compte et les liste.

Usage :
    python content_writer.py audit impact --site superprof.fr-ressources \
        --month 2026-08
    python content_writer.py audit impact --site superprof.fr-ressources \
        --start 2026-08-01 --end 2026-08-31 --maturity 30
"""

import json
import math
import re
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

from scripts.audit.ahrefs_state import REPO_ROOT
from scripts.audit.gsc_analyzer import GSCAnalyzer
from scripts.audit.gsc_state import _site_gsc_property
from scripts.audit.gsc_tab_perf import (
    _ctr,
    _fetch_pages_metrics,
    _fr_num,
    _norm,
    _pct,
    _signed_pct,
    _dump,
    _BRAND,
    _NEG,
    _POS,
    _MONTHS_FR,
)

# Recul par défaut : 30 jours. En deçà de ~7 jours Google n'a pas fini de
# réévaluer la page et la mesure est dominée par le bruit de recrawl.
#
# Le plafond de 30 ne tient plus, depuis le passage au YoY, à la fenêtre
# « avant » qui mordrait sur un refresh antérieur (elle est maintenant ancrée
# à J-365, largement hors de portée d'un refresh du mois précédent) : il reste
# la seule contrainte qui varie encore avec la date de republication dans le
# mois, côté « après », et sert surtout à garder les rapports comparables d'un
# mois sur l'autre (voir la skill `impact-report`).
DEFAULT_MATURITY = 30
MIN_MATURITY = 7

# En deçà de ce taux de couverture, le rapport tairait une part trop large du
# mois pour être honnête : il refuse de se produire (voir `--partial`).
MIN_COVERAGE_PCT = 90

# Latence de consolidation GSC : les tout derniers jours sont sous-comptés, les
# inclure ferait passer une incomplétude de données pour une baisse de trafic.
GSC_LAG_DAYS = 3


# ---------------------------------------------------------------------------
# Sources de republication
# ---------------------------------------------------------------------------

def _pushed_dates_from_backups(site: str) -> dict:
    """{slug: date ISO} depuis les mtimes de outputs/<site>/wp_backups/.

    Source primaire : ce fichier n'est écrit que par `push_to_wp`, donc sa
    date est celle d'un **acte de refresh**, pas d'une modification
    quelconque. C'est ce qui la rend supérieure au `modified` de WordPress
    pour cette mesure.

    Sa limite : `push_to_wp` n'écrit le backup que s'il est absent
    (`if not bkp.exists()`), donc le mtime date la PREMIÈRE publication.
    Un article repassé une seconde fois reste daté de sa passe initiale.
    Le contrôle `modified` ne lève pas cette limite mais la signale, en
    listant les articles retouchés depuis.

    Ces fichiers sont la seule trace durable de l'historique de publication :
    les purger (ou purger `outputs/html/`) rendrait tout rapport d'impact
    rétrospectif impossible. À conserver, ou à archiver avant purge.
    """
    from _shared.core.site_paths import SitePaths

    backups = SitePaths(base_path=REPO_ROOT).output_dir(site) / "wp_backups"
    if not backups.is_dir():
        return {}

    out = {}
    for path in backups.glob("*_before.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        slug = data.get("slug")
        if not slug:
            continue
        stamp = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d")
        # Un même slug peut porter deux post_id (doublon WordPress) : deux
        # fichiers, un seul article en ligne et une seule URL dans GSC. On
        # garde la republication la plus récente, celle dont l'effet est mesuré.
        out[slug] = max(stamp, out[slug]) if slug in out else stamp
    return out


def _wp_modified(site: str, slugs: list[str]) -> dict:
    """{slug: date ISO de `modified`} — contrôle de cohérence, PAS une source.

    `modified` est la date de la *dernière modification quelconque* du post :
    une correction manuelle, une passe de QC ou un plugin l'écrasent. Elle ne
    dit donc pas quand l'article a été refreshé. Sur août 2026, 69 des 78
    articles avaient un `modified` postérieur à leur republication.

    Ce qu'elle apporte : un `modified` postérieur au refresh signale que la
    fenêtre « après » de l'article contient une seconde intervention, et que
    l'effet mesuré n'est plus imputable au seul refresh.
    """
    try:
        from scripts.utils.push_to_wp import build_client
        client = build_client(site, base_path=REPO_ROOT)
    except Exception:
        # Pas de bloc wp_api_config, credentials absents, WAF : le contrôle
        # est optionnel, le rapport se calcule sans lui.
        return {}

    out = {}
    for slug in slugs:
        try:
            post = client.get_post_by_slug(slug)
        except Exception:
            continue
        modified = (post or {}).get("modified") or (post or {}).get("modified_gmt")
        if modified:
            out[slug] = str(modified)[:10]
    return out


def _trajectory(site: str, current_month: Optional[str], current: dict) -> list:
    """Écart net mois après mois, lu dans les rapports déjà produits.

    La question directoriale qu'aucune autre section ne traite : l'effet se
    cumule-t-il ou plafonne-t-il ? Un mois isolé n'y répond pas.

    On relit les JSON voisins plutôt que de recalculer : chacun a coûté ses
    appels GSC, et leur écart net est déjà déduit de la saisonnalité de *leur*
    propre fenêtre — la seule comparaison qui ait un sens d'un mois à l'autre.
    Un mois non encore calculé n'apparaît simplement pas.
    """
    if not current_month:
        return []

    from _shared.core.site_paths import SitePaths

    audit_dir = SitePaths(base_path=REPO_ROOT).output_dir(site) / "audit"
    if not audit_dir.is_dir():
        return []

    rows = []
    for path in sorted(audit_dir.glob("impact_refresh_*.json")):
        m = re.search(r"impact_refresh_(\d{4}-\d{2})_", path.name)
        if not m:
            continue
        month = m.group(1)
        if month == current_month:
            payload = current
        else:
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
        ctrl = payload.get("control") or {}
        if ctrl.get("net_impressions_pct") is None:
            continue
        rows.append({
            "month": month,
            "label": _fr_month(f"{month}-01")[:-5].capitalize(),
            "articles": (payload.get("counts") or {}).get("measurable", 0),
            "net_impressions_pct": ctrl["net_impressions_pct"],
            "net_clicks_pct": ctrl.get("net_clicks_pct"),
        })

    rows.sort(key=lambda r: r["month"])
    return rows


def _pushed_dates_from_journal(site: str) -> dict:
    """{slug: date ISO} depuis `wp_backups/_publications.jsonl`.

    Écrit par `push_to_wp` à **chaque** publication réussie, là où le backup
    `{id}_before.json` n'est écrit qu'à la première. C'est donc la source la
    plus juste quand elle existe : elle date l'acte de publication et survit
    aux passes multiples.

    Le journal n'existe que depuis sa mise en place : les publications
    antérieures restent datées par les mtimes des backups, et les
    republications manuelles par `modified` (voir
    `_pushed_dates_from_sheet_wp`). On garde la date la plus récente par slug,
    qui est celle dont l'effet est mesuré.
    """
    from _shared.core.site_paths import SitePaths

    path = (SitePaths(base_path=REPO_ROOT).output_dir(site)
            / "wp_backups" / "_publications.jsonl")
    if not path.is_file():
        return {}

    out: dict = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}

    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        slug, ts = entry.get("slug"), entry.get("ts")
        if not slug or not ts:
            continue
        stamp = str(ts)[:10]
        out[slug] = max(stamp, out[slug]) if slug in out else stamp
    return out


def _pushed_dates_from_sheet_column(site: str, tab_name: str) -> dict:
    """{slug: date ISO} depuis la colonne « Date de refresh » d'un onglet.

    **Source de rang 1 quand elle existe, et la seule qui date un acte
    éditorial.** Les trois autres sources datent un événement *technique* :
    `wp_backups` une publication par `push_to_wp`, le journal la même chose,
    `modified` n'importe quelle écriture sur le post. Cette colonne-ci est
    remplie par la personne qui a fait le refresh : elle dit quand le travail a
    eu lieu, pas quand un octet a bougé.

    Ce qui a rendu cette source nécessaire. Le rapport d'août 2026 comptait 166
    articles là où l'onglet n'en déclare que 86. L'écart venait du repli sur
    `modified` : `clovis-premier-dynastie-germaine`, refreshé en **juin**,
    portait un `modified` d'août (une retouche ultérieure) et ressortait comme
    la plus forte progression du mois — alors qu'il n'appartient même pas à
    l'onglet suivi. Mesuré sur l'échantillon : sur 10 articles datés par
    `modified`, 3 servaient en ligne une version rédigée en juin.

    Le périmètre suit l'onglet : une ligne sans date n'est pas datée ailleurs,
    elle est simplement hors du lot.
    """
    from _shared.core.site_paths import SitePaths

    cfg_path = SitePaths(base_path=REPO_ROOT).site_dir(site) / "config" / "site.json"
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    sheets_cfg = cfg.get("sheets") or {}
    spreadsheet_id = sheets_cfg.get("spreadsheet_id")
    tab = next((t for t in (sheets_cfg.get("tabs") or [])
                if t.get("name") == tab_name), None)
    if not spreadsheet_id or not tab:
        raise ValueError(
            f"Onglet « {tab_name} » introuvable dans la config de {site}. "
            f"Onglets déclarés : "
            f"{[t.get('name') for t in (sheets_cfg.get('tabs') or [])]}"
        )
    col_date = tab.get("col_date")
    if col_date is None:
        raise ValueError(
            f"L'onglet « {tab_name} » ne déclare pas de colonne de date "
            f"(`col_date` dans sheets.tabs) : impossible d'en dater les refreshs."
        )

    try:
        from scripts.sheets.sheets_client import SheetsClient
        rows = SheetsClient(spreadsheet_id)._read_sheet(tab_name)
    except Exception:
        return {}

    col_url = tab.get("col_url", 0)
    out = {}
    for row in rows[1:]:
        url = (row[col_url] if len(row) > col_url else "").strip()
        raw = (row[col_date] if len(row) > col_date else "").strip()
        if not url.startswith("http") or not raw:
            continue
        iso = _parse_fr_date(raw)
        if iso:
            out[_slug_from_url(url)] = iso
    return out


# Colonne Notion qui date le refresh éditorial. « Date de publication » date
# la *création* de l'article (2023 pour la quasi-totalité du catalogue
# enseigna.fr) : la prendre pour une date de refresh mettrait tout le lot hors
# de n'importe quel mois mesuré.
NOTION_REFRESH_COL = "Planing de refresh"


def _pushed_dates_from_notion(site: str) -> dict:
    """{slug: date ISO} depuis la colonne de refresh de la base Notion.

    **Le pendant de `_pushed_dates_from_sheet_column` pour les sites suivis
    dans Notion**, et pour la même raison : elle date un *acte éditorial*,
    saisi par la personne qui a fait le refresh, là où les autres sources
    datent un événement technique.

    Elle existe parce que `wp_backups/` est vide sur enseigna.fr : le site
    publie à la main depuis WordPress, `push_to_wp` n'y écrit jamais, et la
    cascade habituelle (journal → mtimes → `modified`) n'a donc aucun rang
    disponible. Sans cette source, le rapport d'impact n'est pas produisible
    sur ce site.

    Deux colonnes de date cohabitent dans la base, et prendre la mauvaise vide
    le rapport : « Date de publication » date la création (2023 pour 30 des 42
    articles en ligne), « Planing de refresh » date la republication. Seule la
    seconde est lue ici.

    Le périmètre suit la base : une ligne sans date de refresh n'est pas datée
    ailleurs, elle est simplement hors du lot.
    """
    try:
        from scripts.audit.notion_pub_source import (
            get_notion_pub_config,
            read_publication_rows,
        )
    except ImportError:
        return {}

    pub = get_notion_pub_config(site)
    col = pub.get("col_refreshed", NOTION_REFRESH_COL)

    from scripts.audit.notion_pub_source import _plain
    from scripts.notion import NotionClient

    client = NotionClient()
    if not client.is_configured:
        raise RuntimeError(
            "NOTION_TOKEN manquant (.env ou ~/.credentials/notion/credentials.json) : "
            "impossible de lire les dates de refresh de la base Notion."
        )

    out = {}
    for page in client.query_database(pub["database_id"]):
        props = page.get("properties", {})
        url = _plain(props.get(pub.get("col_url", "URL")))
        raw = _plain(props.get(col))[:10]
        if not url.startswith("http") or not raw:
            continue
        iso = _parse_fr_date(raw)
        if iso:
            out[_slug_from_url(url)] = iso
    return out


def _notion_online_slugs(site: str) -> set:
    """Slugs que la base Notion déclare en ligne (ligne portant une URL http).

    Sert de **borne au périmètre** quand le sitemap complète les dates : un
    `lastmod` ne doit jamais faire entrer dans le lot une page que la base ne
    suit pas. C'est exactement le mécanisme qui avait gonflé le rapport d'août
    2026 de 86 à 166 articles sur l'autre site, par un repli de dernier rang
    qui élargissait le périmètre au lieu de combler un trou dedans.
    """
    try:
        from scripts.audit.notion_pub_source import read_publication_rows
        return {_slug_from_url(r["url"]) for r in read_publication_rows(site)}
    except Exception:
        return set()


def _notion_categories(site: str) -> dict:
    """{slug: catégorie} depuis la base Notion.

    enseigna.fr n'a pas de vertical dans ses URLs (elles sont à plat) : sans
    cette colonne, toutes les fiches s'affichent « hors arborescence » et
    l'agrégat par catégorie est vide.
    """
    try:
        from scripts.audit.notion_pub_source import read_publication_rows
        return {_slug_from_url(r["url"]): r["category"]
                for r in read_publication_rows(site) if r.get("category")}
    except Exception:
        return {}


def _pushed_dates_from_sitemap(site: str) -> dict:
    """{slug: date ISO} depuis le `lastmod` du sitemap des articles.

    **Complément de la base Notion, jamais source unique.** Le `lastmod` a le
    même défaut que le `modified` WordPress — il date la dernière écriture
    quelconque, pas un acte éditorial — mais il a deux qualités que rien
    d'autre n'offre sur un site à publication manuelle : il est exhaustif (il
    voit les republications que personne n'a saisies dans Notion) et il est
    public (aucune API WordPress, dont l'accès REST d'enseigna.fr est
    désactivé).

    Vérifié sur enseigna.fr en septembre 2026 : sur les 19 refreshs que Notion
    date, **18 portent un `lastmod` identique au jour près**, le dernier à 5
    jours. Cette concordance est ce qui autorise le sitemap en second rang ;
    elle ne le promeut pas au premier, car il ne distingue pas un refresh
    d'une correction de coquille.

    Ne lit que les sitemaps d'articles (`post-sitemap*`) : les sitemaps de
    catégories, villes et écoles contiennent des pages générées qui ne sont
    pas des articles et n'ont jamais été refreshées.
    """
    import gzip
    import urllib.request

    domain = _site_domain(site)
    if not domain:
        return {}

    def fetch(url: str) -> str:
        req = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0 (compatible; content-writer/1.0)"}
        )
        raw = urllib.request.urlopen(req, timeout=30).read()
        if raw[:2] == b"\x1f\x8b":
            raw = gzip.decompress(raw)
        return raw.decode("utf-8", "replace")

    try:
        index = fetch(f"https://{domain}/sitemap_index.xml")
    except Exception:
        return {}

    maps = [u for u in re.findall(r"<loc>(.*?)</loc>", index) if "post-sitemap" in u]
    if not maps:
        maps = [f"https://{domain}/sitemap.xml"]

    out = {}
    for sm in maps:
        try:
            xml = fetch(sm)
        except Exception:
            continue
        for block in re.findall(r"<url>(.*?)</url>", xml, re.S):
            loc = re.search(r"<loc>(.*?)</loc>", block)
            mod = re.search(r"<lastmod>(.*?)</lastmod>", block)
            if not loc or not mod:
                continue
            url = loc.group(1).strip()
            iso = _parse_fr_date(mod.group(1).strip()[:10])
            if iso and url.rstrip("/") != f"https://{domain}":
                out[_slug_from_url(url)] = iso
    return out


def _site_domain(site: str) -> str:
    from _shared.core.site_paths import SitePaths

    cfg_path = SitePaths(base_path=REPO_ROOT).site_dir(site) / "config" / "site.json"
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    return (cfg.get("domain") or "").strip()


def _parse_fr_date(raw: str) -> Optional[str]:
    """« 04/08/2026 » ou « 2026-08-04 » → « 2026-08-04 ».

    La saisie est humaine : les deux formats coexistent dans la même colonne.
    Une valeur non reconnue est ignorée plutôt que devinée — une date fausse
    déplacerait l'article de vague et fausserait sa fenêtre de mesure.
    """
    raw = raw.strip()
    m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", raw)
    if m:
        y, mo, d = m.groups()
    else:
        m = re.match(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$", raw)
        if not m:
            return None
        d, mo, y = m.groups()
    try:
        return datetime(int(y), int(mo), int(d)).strftime("%Y-%m-%d")
    except ValueError:
        return None


def _pushed_dates_from_sheet_wp(site: str, known: dict) -> dict:
    """Dates de republication des articles publiés HORS `push_to_wp`.

    **Pourquoi cette source existe.** `push_to_wp` n'écrit son backup que
    lorsqu'il publie lui-même. Quand `cw push` échoue et que la republication se
    fait à la main depuis WordPress — après relecture, cas courant — l'article
    part en ligne sans laisser la moindre trace locale. Mesuré sur
    superprof.fr-ressources en septembre 2026 : 58 articles republiés
    manuellement sur ~134, soit 43 % du travail du mois absent du rapport, sans
    que rien ne le signale (la couverture affichait « 100 % » parce qu'elle
    comptait les articles *tracés*, pas les articles *republiés*).

    **La méthode.** L'onglet de suivi connaît les articles traités ; leur statut
    éditorial dit lesquels sont partis en ligne. Pour ceux-là, et pour eux seuls,
    le champ `modified` de WordPress sert de date de republication.

    **Pourquoi `modified` est acceptable ICI alors qu'il est proscrit ailleurs.**
    La règle générale tient toujours : `modified` date la dernière modification
    quelconque et une retouche ultérieure l'écrase, ce qui en fait une mauvaise
    source *quand une meilleure existe*. Pour ces articles-là il n'en existe
    aucune autre — le choix n'est pas entre `modified` et mieux, mais entre
    `modified` et ne pas mesurer 43 % du mois. La substitution a été validée sur
    les 20 lignes qui portaient aussi une date saisie à la main : 10 dates
    identiques, 10 à +1 jour exactement, aucun écart erratique.

    L'ordre de priorité reste : `wp_backups` d'abord (il date un acte de
    publication), cette source ensuite, et jamais l'inverse.
    """
    from _shared.core.site_paths import SitePaths

    cfg_path = SitePaths(base_path=REPO_ROOT).site_dir(site) / "config" / "site.json"
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    sheets_cfg = cfg.get("sheets") or {}
    spreadsheet_id = sheets_cfg.get("spreadsheet_id")
    tabs = sheets_cfg.get("tabs") or []
    published = {st.lower() for st in (
        sheets_cfg.get("published_statuses")
        or ["prêt pour relecture", "publié", "publie"]
    )}
    if not spreadsheet_id or not tabs:
        return {}

    try:
        from scripts.sheets.sheets_client import SheetsClient
        client = SheetsClient(spreadsheet_id)
    except Exception:
        return {}

    candidates = {}
    for tab in tabs:
        col_status = tab.get("col_status")
        if col_status is None:
            continue
        try:
            rows = client._read_sheet(tab["name"])
        except Exception:
            continue
        for row in rows[1:]:
            url = (row[0] if row else "").strip()
            status = (row[col_status] if len(row) > col_status else "").strip()
            if not url.startswith("http") or status.lower() not in published:
                continue
            slug = _slug_from_url(url)
            if slug in known:
                continue
            candidates[slug] = url

    if not candidates:
        return {}

    # Cache disque : un appel WP par slug, ~250 sur ce site, soit plusieurs
    # minutes et autant d'occasions de se faire refuser par le WAF. Ces dates
    # ne bougent plus une fois l'article publié : les relire à chaque rapport
    # serait payer le même prix pour la même réponse.
    cache_path = (SitePaths(base_path=REPO_ROOT).output_dir(site)
                  / "wp_backups" / "_modified_cache.json")
    cache = {}
    if cache_path.is_file():
        try:
            cache = json.loads(cache_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            cache = {}

    todo = sorted(set(candidates) - set(cache))
    if todo:
        fresh = _wp_modified(site, todo)
        cache.update(fresh)
        # On mémorise aussi les échecs (valeur vide) : sans cela, un slug que
        # le WAF refuse serait retenté à chaque exécution, indéfiniment.
        for slug in todo:
            cache.setdefault(slug, "")
        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(
                json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8"
            )
        except OSError:
            pass

    return {slug: cache[slug] for slug in candidates if cache.get(slug)}


def _slug_from_url(url: str) -> str:
    last = url.rstrip("/").rsplit("/", 1)[-1]
    return re.sub(r"\.html?$", "", last)


# ---------------------------------------------------------------------------
# Fenêtres
# ---------------------------------------------------------------------------

def _month_bounds(month: str) -> tuple:
    """« 2026-08 » → (2026-08-01, 2026-08-31)."""
    d = datetime.strptime(month, "%Y-%m")
    start = d.replace(day=1)
    nxt = (start + timedelta(days=32)).replace(day=1)
    return start.strftime("%Y-%m-%d"), (nxt - timedelta(days=1)).strftime("%Y-%m-%d")


def _fetch_page_query_metrics(gsc_property: str, start: str, end: str) -> dict:
    """Une requête GSC dimension=page+query sur la fenêtre.

    Retourne {url_normalisée: {requête: métriques}}.

    **Un seul appel paginé par fenêtre, pas un par URL.** GSC renvoie toutes les
    paires page+requête de la propriété ; on filtre localement sur les articles
    traités. Interroger chaque URL séparément coûterait 76 appels par fenêtre là
    où un seul suffit, pour exactement la même donnée.

    C'est ce qui rend lisible le *déplacement sémantique* d'un refresh : quelles
    requêtes l'article a gagnées, lesquelles il a perdues. Les métriques par page
    seules disent qu'il monte, jamais sur quoi.
    """
    analyzer = GSCAnalyzer(gsc_property)
    if not analyzer._gsc_service:
        raise RuntimeError("API GSC service account indisponible (credentials manquants ?)")

    by_page: dict = defaultdict(dict)
    start_row = 0
    while True:
        body = {
            "startDate": start,
            "endDate": end,
            "dimensions": ["page", "query"],
            "rowLimit": 25000,
            "startRow": start_row,
        }
        # Une coupure réseau en fin de parcours perdrait toutes les fenêtres
        # déjà collectées (plusieurs minutes d'appels) : un rapport de 91
        # articles s'est ainsi arrêté sur un « Connection reset by peer ».
        # Trois tentatives espacées suffisent pour un incident transitoire.
        for attempt in range(3):
            try:
                response = analyzer._gsc_service.searchanalytics().query(
                    siteUrl=gsc_property, body=body
                ).execute()
                break
            except (OSError, ConnectionError) as exc:
                if attempt == 2:
                    raise
                time.sleep(2 ** attempt)
        batch = response.get("rows", [])
        for r in batch:
            url, query = r["keys"][0], r["keys"][1]
            by_page[_norm(url)][query] = {
                "clicks": r.get("clicks", 0),
                "impressions": r.get("impressions", 0),
                "position": round(r.get("position", 0), 1),
            }
        if len(batch) < 25000:
            return dict(by_page)
        start_row += len(batch)


def _query_movement(before: dict, after: dict, top: int) -> dict:
    """Déplacement sémantique d'un article : requêtes gagnées, perdues, tenues.

    Trois familles, parce qu'un refresh réussi peut se lire de deux façons très
    différentes et que les confondre fait passer un élargissement de couverture
    pour une remontée de classement :

    - **gagnées** : absentes avant, présentes après — l'article ressort sur des
      requêtes qu'il ne captait pas ;
    - **perdues** : l'inverse, le seul signal d'alerte éditorial du lot ;
    - **tenues** : présentes des deux côtés, avec le delta de position.

    Le classement se fait sur les impressions *après* pour les deux premières
    familles et *avant* pour les perdues : une requête perdue n'a plus de volume
    après, la trier là-dessus les mettrait toutes à zéro.
    """
    keys_b, keys_a = set(before), set(after)

    def pack(q: str, b: Optional[dict], a: Optional[dict]) -> dict:
        return {
            "query": q,
            "impressions_before": (b or {}).get("impressions", 0),
            "impressions_after": (a or {}).get("impressions", 0),
            "clicks_before": (b or {}).get("clicks", 0),
            "clicks_after": (a or {}).get("clicks", 0),
            "position_before": (b or {}).get("position"),
            "position_after": (a or {}).get("position"),
        }

    gained_all = sorted(
        (pack(q, None, after[q]) for q in keys_a - keys_b),
        key=lambda r: -r["impressions_after"],
    )
    lost_all = sorted(
        (pack(q, before[q], None) for q in keys_b - keys_a),
        key=lambda r: -r["impressions_before"],
    )
    gained, lost = gained_all[:top], lost_all[:top]
    held = []
    for q in keys_a & keys_b:
        row = pack(q, before[q], after[q])
        pb, pa = row["position_before"], row["position_after"]
        # Le gain de position se lit à l'envers : passer de 12 à 7 est un gain
        # de 5, pas de -5. On stocke le signe déjà retourné pour que le rendu
        # n'ait pas à le refaire (et à se tromper).
        row["position_delta"] = (
            None if pb is None or pa is None else round(pb - pa, 1)
        )
        held.append(row)
    held.sort(key=lambda r: -r["impressions_after"])

    # Les `top` requêtes qui pèsent le plus, toutes familles confondues,
    # classées sur max(avant, après). C'est la liste que la fiche affiche : une
    # requête perdue à 414 impressions l'an dernier pèse plus dans la lecture
    # d'un recul qu'une requête gagnée à 2 impressions, et une requête
    # maintenue qui s'effondre (368 → 5) n'entrerait jamais dans un classement
    # sur le seul « après ». Les trois familles restent à côté pour le
    # drill-down et pour le diagnostic.
    merged = (
        [{**x, "kind": "maintenue"} for x in held]
        + [{**x, "kind": "gagnée"} for x in gained_all]
        + [{**x, "kind": "perdue"} for x in lost_all]
    )
    merged.sort(key=lambda x: (-max(x["impressions_before"], x["impressions_after"]),
                               -x["impressions_after"]))

    return {
        "gained": gained,
        "lost": lost,
        "held": held[:top],
        "top": merged[:top],
        "counts": {
            "gained": len(keys_a - keys_b),
            "lost": len(keys_b - keys_a),
            "held": len(keys_a & keys_b),
            "before": len(keys_b),
            "after": len(keys_a),
        },
    }


# Nombre d'articles détaillés en fiche de chaque côté (gagnants, reculs). Le
# reste du lot tient en tableau : 165 fiches font 45 pages qu'on ne parcourt
# pas, et le ventre mou n'ouvre sur aucune décision.
DETAIL_ARTICLES = 20

# Libellés auto-explicatifs : un lecteur qui ne connaît pas le jargon du
# rapport doit pouvoir deviner ce que chaque étiquette signifie sans ouvrir la
# méthode. « Couverture élargie » et « Audience resserrée » ne remplissaient
# pas ce critère (question posée telle quelle en relecture : « Audience
# resserrée : c'est-à-dire ? »).
DIAGS = {
    "coverage": "Nouveaux mots-clés",
    "ranking": "Classement amélioré",
    "query_loss": "Perte de requêtes",
    "narrowed": "Recul sur mêmes requêtes",
    "flat": "Sans mouvement net",
}


def _diagnose(a: dict) -> Optional[str]:
    """Diagnostic mécanique d'un article, dérivé du mouvement de ses requêtes.

    Ce n'est pas une cause — la mesure n'établit aucune causalité — mais la
    description de *ce qui a bougé*, que les métriques par page ne peuvent pas
    donner. Sans elle on lit `polariser-lumiere-physique` (+310 % net, position
    9,9 → 10,6) comme un échec de classement, alors que l'article a gagné 83
    requêtes : le volume vient de l'élargissement, pas du rang.

    Le test de recul insuffisant (« immature ») a disparu avec le passage à la
    fenêtre année-sur-année : l'ancien diagnostic reposait sur `maturity`, qui
    ne bornait alors que le recul « avant » (les jours précédant la
    republication) et servait à repérer les mesures trop jeunes côté avant.
    Depuis que « avant » est ancré à J-365 avec le même recul que « après »,
    ce recul est presque toujours disponible côté GSC (16 mois d'historique) ;
    seul le recul côté « après » varie encore selon la date de republication
    dans le mois, et il est déjà reflété dans `maturity` sans qu'un diagnostic
    séparé soit nécessaire — un article à 7 jours de recul produit simplement
    des volumes plus petits, pas un statut à part.

    **Un article qui baisse ne porte jamais une étiquette positive.** Le test
    `gained > held` est vrai trivialement quand l'article tient peu de requêtes
    (`forces-et-effets` : +1 gagnée, 0 maintenue, et pourtant -28 % net) ; sans
    ce garde-fou il ressortirait « nouveaux mots-clés » alors qu'il recule.
    """
    q = (a.get("queries") or {}).get("counts")
    net = a.get("net_impressions_pct")
    if not q:
        return None

    gained, lost, held = q.get("gained", 0), q.get("lost", 0), q.get("held", 0)
    declining = net is not None and net < -5

    if lost > 2 * gained and lost > 5:
        return DIAGS["query_loss"]
    if declining:
        return DIAGS["narrowed"]
    if gained > held:
        return DIAGS["coverage"]
    if net is not None and net > 5:
        return DIAGS["ranking"]
    return DIAGS["flat"]


# Décalage année sur année : la fenêtre « avant » n'est plus les N jours qui
# précèdent la republication, mais les N jours qui suivent la MÊME date un an
# plus tôt. Ça élimine mécaniquement la saisonnalité (même mois calendaire des
# deux côtés) au lieu de la déduire après coup via le groupe de contrôle, et ça
# répond à la question qu'un lecteur pose spontanément : « et par rapport à
# l'an dernier, à date fixe ? ».
YOY_OFFSET_DAYS = 365


def _article_windows(pushed: str, maturity: int, data_end: str) -> Optional[dict]:
    """Fenêtres année-sur-année d'un article, à durée strictement égale.

    « Après » : les N jours qui suivent la republication, comme avant ce
    changement. « Avant » : les N jours qui suivent la même date un an plus
    tôt (`pushed - 365 j`), et non plus les N jours qui la précèdent. Les deux
    fenêtres sont donc symétriques (même décalage en jours depuis leur date
    ancre respective) plutôt que contiguës.

    Le jour de republication lui-même reste exclu de la fenêtre « après » :
    il porte à la fois l'ancienne et la nouvelle version. Son homologue un an
    plus tôt n'a pas cette raison d'être exclu (aucun refresh n'y a eu lieu),
    mais on l'exclut par symétrie : la fenêtre « avant » commence donc le
    lendemain de `pushed - 365 j`, exactement comme « après » commence le
    lendemain de `pushed`.

    N reste plafonné par le recul disponible côté « après » (`--maturity`,
    borné à `data_end`) : c'est la seule contrainte qui varie encore avec la
    date de republication dans le mois. Côté « avant », le recul est
    quasiment toujours disponible (GSC conserve environ 16 mois d'historique),
    donc ce n'est plus lui qui limite N.
    """
    d = datetime.strptime(pushed, "%Y-%m-%d")
    end_cap = datetime.strptime(data_end, "%Y-%m-%d")

    available = (end_cap - d).days
    n = min(maturity, available)
    if n < MIN_MATURITY:
        return None

    d_prior = d - timedelta(days=YOY_OFFSET_DAYS)

    return {
        "maturity": n,
        "before": {
            "start": (d_prior + timedelta(days=1)).strftime("%Y-%m-%d"),
            "end": (d_prior + timedelta(days=n)).strftime("%Y-%m-%d"),
        },
        "after": {
            "start": (d + timedelta(days=1)).strftime("%Y-%m-%d"),
            "end": (d + timedelta(days=n)).strftime("%Y-%m-%d"),
        },
    }


# ---------------------------------------------------------------------------
# Calcul
# ---------------------------------------------------------------------------

def run_impact(
    site: str,
    month: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    maturity: int = DEFAULT_MATURITY,
    top: int = 15,
    top_queries: int = 5,
    tab: Optional[str] = None,
    source: str = "auto",
    with_queries: bool = True,
    with_manual: bool = True,
    pdf: bool = False,
    pdf_annex: bool = False,
    check_wp: bool = True,
    partial: bool = False,
    dry_run: bool = False,
) -> dict:
    """Mesure l'impact des republications d'une période, article par article."""
    if month:
        start, end = _month_bounds(month)
    if not (start and end):
        raise ValueError("Passer --month YYYY-MM, ou --start et --end.")

    data_end = (datetime.now() - timedelta(days=GSC_LAG_DAYS)).strftime("%Y-%m-%d")
    gsc_property = _site_gsc_property(site)

    # 1. Republications de la période (trace locale = acte de refresh), puis
    #    rattrapage des articles publiés à la main (voir
    #    `_pushed_dates_from_sheet_wp` : `push_to_wp` ne trace que ses propres
    #    publications, et une republication manuelle est invisible du rapport).
    # `--tab` : le périmètre ET les dates viennent de la colonne « Date de
    # refresh » de l'onglet, et de rien d'autre. C'est un mode volontairement
    # étanche : mélanger une date saisie avec un `modified` WordPress avait
    # gonflé le rapport d'août 2026 de 86 articles déclarés à 166 mesurés, en y
    # faisant entrer des refreshs de juin dont le post avait simplement été
    # retouché depuis.
    # `--source notion` : le pendant de `--tab` pour les sites à publication
    # manuelle, où `wp_backups/` est vide et où aucun rang de la cascade
    # habituelle n'existe. La base Notion donne le périmètre et les dates
    # éditoriales ; le sitemap comble les refreshs que personne n'y a saisis
    # (1 sur 9 en août 2026 sur enseigna.fr), sans jamais élargir le périmètre
    # au-delà des URLs que la base déclare en ligne — c'est la leçon du faux
    # d'août 2026, où un repli de dernier rang avait fait passer le lot de 86
    # à 166 articles.
    categories = {}
    if source == "notion":
        categories = _notion_categories(site)
        pushed_by_slug = _pushed_dates_from_notion(site)
        n_traced = len(pushed_by_slug)
        recovered = {}
        known = set(_notion_online_slugs(site))
        for slug, date in _pushed_dates_from_sitemap(site).items():
            if slug in known and slug not in pushed_by_slug:
                recovered[slug] = date
        pushed_by_slug.update(recovered)
        if not pushed_by_slug:
            raise ValueError(
                f"Aucune date de refresh lisible dans la base Notion de {site} "
                f"(colonne « {NOTION_REFRESH_COL} »)."
            )
    elif tab:
        pushed_by_slug = _pushed_dates_from_sheet_column(site, tab)
        if not pushed_by_slug:
            raise ValueError(
                f"Aucune date de refresh lisible dans l'onglet « {tab} » "
                f"pour {site}."
            )
        n_traced = len(pushed_by_slug)
        recovered = {}
    else:
        pushed_by_slug = _pushed_dates_from_backups(site)
        # Le journal prime sur les mtimes : il date chaque publication, quand le
        # backup ne retient que la première.
        pushed_by_slug.update(_pushed_dates_from_journal(site))
        n_traced = len(pushed_by_slug)
        recovered = {}
        if with_manual:
            recovered = _pushed_dates_from_sheet_wp(site, pushed_by_slug)
            pushed_by_slug.update(recovered)

    in_period = {
        slug: date for slug, date in pushed_by_slug.items()
        if start <= date <= end
    }
    if not in_period:
        raise ValueError(
            f"Aucune republication trouvée entre {start} et {end} pour {site}."
        )

    # 2. Une requête GSC par fenêtre distincte (les articles d'une même vague
    #    les partagent, donc le nombre d'appels suit les vagues, pas les URLs).
    windows = {}
    for slug, pushed in in_period.items():
        w = _article_windows(pushed, maturity, data_end)
        if w:
            windows[slug] = w

    skipped = sorted(set(in_period) - set(windows))

    # Couverture : lancer le rapport trop tôt après la fin de la période écarte
    # les articles les plus récents, faute du recul minimal. Le biais est
    # systématique (ce sont toujours les derniers publiés) et invisible dans un
    # total : lancé le 1er septembre, le rapport d'août 2026 ne couvrait que 44
    # des 78 articles. On refuse de produire un rapport qui tairait la moitié
    # du travail du mois ; `--partial` lève le refus en connaissance de cause.
    coverage = round(len(windows) / len(in_period) * 100)
    ready_on = (
        datetime.strptime(end, "%Y-%m-%d")
        + timedelta(days=MIN_MATURITY + GSC_LAG_DAYS)
    ).strftime("%Y-%m-%d")
    if coverage < MIN_COVERAGE_PCT and not partial:
        raise ValueError(
            f"Recul insuffisant : {len(windows)}/{len(in_period)} articles "
            f"mesurables ({coverage} %), les {len(skipped)} plus récents sont "
            f"écartés faute de {MIN_MATURITY} jours de recul.\n"
            f"Le lot sera complet à partir du {ready_on}. "
            f"Relancer à cette date, ou forcer avec --partial "
            f"(le rapport ne portera alors que sur une partie du mois)."
        )

    needed = set()
    for w in windows.values():
        needed.add((w["before"]["start"], w["before"]["end"]))
        needed.add((w["after"]["start"], w["after"]["end"]))

    metrics = {}
    totals = {}
    queries = {}
    for win in sorted(needed):
        by_page = _fetch_pages_metrics(gsc_property, win[0], win[1])
        metrics[win] = by_page
        totals[win] = {
            "clicks": sum(p["clicks"] for p in by_page.values()),
            "impressions": sum(p["impressions"] for p in by_page.values()),
        }
        # Requêtes par page sur la même fenêtre : un appel supplémentaire par
        # fenêtre (pas par URL), ce qui garde le coût aligné sur le nombre de
        # vagues. Sans elles, le rapport dit qu'un article progresse sans jamais
        # dire sur quoi — c'est la granularité qui manquait au monitoring.
        if with_queries:
            queries[win] = _fetch_page_query_metrics(gsc_property, win[0], win[1])

    # 3. Par article
    slug_to_url = {}
    for by_page in metrics.values():
        for url in by_page:
            slug_to_url.setdefault(_slug_from_url(url), url)

    articles = []
    for slug, w in sorted(windows.items()):
        url = slug_to_url.get(slug)
        wb = (w["before"]["start"], w["before"]["end"])
        wa = (w["after"]["start"], w["after"]["end"])
        mb = metrics[wb].get(_norm(url), {}) if url else {}
        ma = metrics[wa].get(_norm(url), {}) if url else {}

        cb, ca = mb.get("clicks", 0), ma.get("clicks", 0)
        ib, ia = mb.get("impressions", 0), ma.get("impressions", 0)

        # Un article sans aucune impression des deux côtés est invisible de GSC
        # (désindexé, ou sous le seuil de remontée) : le compter donnerait une
        # ligne vide et un dénominateur trompeur.
        if not ib and not ia:
            skipped.append(slug)
            continue

        articles.append({
            "slug": slug,
            "url": url or slug,
            "pushed": in_period[slug],
            "maturity": w["maturity"],
            # La date vient-elle d'un acte de publication tracé, ou du
            # `modified` WordPress d'une republication manuelle ? La seconde est
            # moins sûre (une retouche ultérieure l'écrase) : le rapport le dit
            # plutôt que de présenter les deux comme équivalentes.
            "category": categories.get(slug, ""),
            "date_source": (
                ("notion_sitemap" if slug in recovered else "notion_column")
                if source == "notion" else
                "sheet_column" if tab else
                "wp_modified" if slug in recovered else "wp_backups"),
            "before": {**w["before"], "clicks": cb, "impressions": ib,
                       "position": mb.get("position")},
            "after": {**w["after"], "clicks": ca, "impressions": ia,
                      "position": ma.get("position")},
            "clicks_delta": ca - cb,
            "impressions_delta": ia - ib,
            "clicks_pct": _pct(cb, ca),
            "impressions_pct": _pct(ib, ia),
            "ctr_before": _ctr(cb, ib),
            "ctr_after": _ctr(ca, ia),
        })

        if with_queries and url:
            qb = queries.get(wb, {}).get(_norm(url), {})
            qa = queries.get(wa, {}).get(_norm(url), {})
            articles[-1]["queries"] = _query_movement(qb, qa, top_queries)

    if not articles:
        raise ValueError("Aucun article mesurable (recul insuffisant ou hors GSC).")

    # 4. Groupe de contrôle : le reste du site sur les mêmes dates. On retire
    #    les articles traités du total, sinon le contrôle contiendrait ce qu'il
    #    est censé servir de référence et l'écart serait mécaniquement réduit.
    #
    #    **On exclut tout ce qui a été retravaillé, pas seulement ce qu'on
    #    mesure.** En mode `--tab`, le lot mesuré est un sous-ensemble : les
    #    autres refreshs du mois existent, ils ont bougé, et les laisser dans le
    #    contrôle ferait passer leur progression pour de la saisonnalité. Le
    #    contrôle surestimerait alors le rythme « naturel » du site et l'écart
    #    net du lot serait sous-estimé. Sur août 2026, ce sont ~80 articles à
    #    forte progression qui rentreraient dans la référence.
    treated_urls = {_norm(a["url"]) for a in articles if a["url"].startswith("http")}
    excluded_urls = set(treated_urls)
    if source == "notion":
        # Toute page dont le sitemap dit qu'elle a bougé pendant la période a
        # été retouchée : la laisser dans la référence prêterait sa variation
        # au « rythme naturel » du site.
        for slug, date in _pushed_dates_from_sitemap(site).items():
            if start <= date <= end:
                url = slug_to_url.get(slug)
                if url:
                    excluded_urls.add(_norm(url))
    elif tab:
        others = _pushed_dates_from_backups(site)
        others.update(_pushed_dates_from_journal(site))
        others.update(_pushed_dates_from_sheet_wp(site, {}))
        for slug, date in others.items():
            if start <= date <= end:
                url = slug_to_url.get(slug)
                if url:
                    excluded_urls.add(_norm(url))
    n_control_excluded = len(excluded_urls)

    def control_for(win: tuple) -> dict:
        by_page = metrics[win]
        clicks = sum(p["clicks"] for u, p in by_page.items() if u not in excluded_urls)
        impr = sum(p["impressions"] for u, p in by_page.items() if u not in excluded_urls)
        return {"clicks": clicks, "impressions": impr}

    # 5. Agrégats
    def agg(rows: list[dict]) -> dict:
        cb = sum(a["before"]["clicks"] for a in rows)
        ca = sum(a["after"]["clicks"] for a in rows)
        ib = sum(a["before"]["impressions"] for a in rows)
        ia = sum(a["after"]["impressions"] for a in rows)
        return {
            "articles": len(rows),
            "clicks_before": cb, "clicks_after": ca,
            "impressions_before": ib, "impressions_after": ia,
            "clicks_delta": ca - cb, "impressions_delta": ia - ib,
            "clicks_pct": _pct(cb, ca), "impressions_pct": _pct(ib, ia),
            "ctr_before": _ctr(cb, ib), "ctr_after": _ctr(ca, ia),
        }

    by_wave = {}
    for pushed, rows in sorted(_group(articles, lambda a: a["pushed"]).items()):
        wb = (rows[0]["before"]["start"], rows[0]["before"]["end"])
        wa = (rows[0]["after"]["start"], rows[0]["after"]["end"])
        ctrl_b, ctrl_a = control_for(wb), control_for(wa)
        ctrl_i_pct = _pct(ctrl_b["impressions"], ctrl_a["impressions"])
        ctrl_c_pct = _pct(ctrl_b["clicks"], ctrl_a["clicks"])
        block = agg(rows)
        block.update({
            "maturity": rows[0]["maturity"],
            "control_impressions_pct": ctrl_i_pct,
            "control_clicks_pct": ctrl_c_pct,
            # L'écart net est la performance imputable au refresh : ce que la
            # vague fait de plus que le site aurait fait sans elle.
            "net_impressions_pct": (
                None if block["impressions_pct"] is None or ctrl_i_pct is None
                else round(block["impressions_pct"] - ctrl_i_pct, 1)
            ),
            "net_clicks_pct": (
                None if block["clicks_pct"] is None or ctrl_c_pct is None
                else round(block["clicks_pct"] - ctrl_c_pct, 1)
            ),
        })
        by_wave[pushed] = block

        # Écart net par article : sa variation moins celle du reste du site sur
        # sa propre fenêtre. Sans cette colonne, aucune ligne du tableau détaillé
        # ne se juge hors saison — un +30 % en septembre et un +30 % en juillet
        # ne valent pas la même chose, et seul l'agrégat le disait jusqu'ici.
        for a in rows:
            a["control_impressions_pct"] = ctrl_i_pct
            a["net_impressions_pct"] = (
                None if a["impressions_pct"] is None or ctrl_i_pct is None
                else round(a["impressions_pct"] - ctrl_i_pct, 1)
            )
            # Le diagnostic se lit sur l'écart net, donc il se pose ici et pas
            # dans la boucle de collecte : au moment où l'article est construit,
            # sa vague n'a pas encore son contrôle.
            a["diagnosis"] = _diagnose(a)

    # Le gradient de recul par tranche de maturité (7-15 / 16-25 / 26-30 j) a
    # disparu avec le passage au YoY : il comparait des articles ayant un recul
    # « avant » différent, ce qui n'existe plus (« avant » est désormais ancré
    # à J-365 avec le même recul que « après », quasi toujours disponible côté
    # GSC). Seul le recul côté « après » varie encore selon la date de
    # republication dans le mois — `hindsight_days` ci-dessous en donne la
    # distribution simple, sans reconstituer une tranche par tranche qui
    # n'apporterait plus rien : ce n'est plus le recul qui explique une
    # baisse, la comparaison YoY élimine cette explication par construction.
    hindsight_days = sorted(a["maturity"] for a in articles)

    by_category = {
        k: agg(rows)
        for k, rows in sorted(_group(articles, _category).items())
    }

    overall = agg(articles)
    winners = [a for a in articles if a["impressions_delta"] > 0]
    medians = sorted(
        a["after"]["impressions"] / a["before"]["impressions"]
        for a in articles if a["before"]["impressions"]
    )
    median_factor = round(medians[len(medians) // 2], 2) if medians else None

    # Contrôle global sur la fenêtre dominante (la vague la plus fournie) :
    # c'est la seule qui porte assez d'articles pour que la comparaison
    # saisonnière ait un sens à l'échelle du rapport.
    main_wave = max(by_wave, key=lambda k: by_wave[k]["articles"])

    # Contrôle global : contrefactuel pondéré, et non le contrôle d'une seule
    # vague. Chaque vague a sa propre fenêtre, donc sa propre saisonnalité ;
    # prendre celle de la vague dominante appliquerait à tout le lot un
    # contexte que les autres vagues n'ont pas connu. On projette plutôt, pour
    # chaque vague, ce que ses articles auraient fait au rythme du reste du
    # site, puis on somme : « attendu » vs « obtenu » sur le lot entier.
    expected_i = expected_c = 0.0
    for k, v in by_wave.items():
        gi = (v["control_impressions_pct"] or 0) / 100
        gc = (v["control_clicks_pct"] or 0) / 100
        expected_i += v["impressions_before"] * (1 + gi)
        expected_c += v["clicks_before"] * (1 + gc)

    control = {
        # Variation qu'aurait connue le lot à la seule dynamique du site.
        "impressions_pct": _pct(overall["impressions_before"], expected_i),
        "clicks_pct": _pct(overall["clicks_before"], expected_c),
        "expected_impressions": round(expected_i),
        "expected_clicks": round(expected_c),
        # Sur-performance : ce que le travail ajoute au-dessus de l'attendu.
        "net_impressions_pct": _pct(expected_i, overall["impressions_after"]),
        "net_clicks_pct": _pct(expected_c, overall["clicks_after"]),
        "reference_wave": main_wave,
        # Combien d'URLs le contrôle écarte : le lot mesuré, plus — en mode
        # `--tab` — les refreshs du mois hors périmètre, qui ne sont pas de la
        # saisonnalité et n'ont donc rien à faire dans la référence.
        "excluded_urls": n_control_excluded,
        "measured_urls": len(treated_urls),
    }

    ranked = sorted(articles, key=lambda a: a["impressions_delta"], reverse=True)

    # 6. Courbe de maturation de la vague la plus fournie : impressions par
    #    jour par tranche de 7 jours après republication, rapportées au
    #    régime d'avant refresh. C'est elle qui dit si la fenêtre de mesure
    #    capte l'effet complet ou seulement sa montée — sur août 2026 la
    #    cohorte du 6 passait de ×1,5 (J+7) à ×4,0 (J+34), donc une lecture à
    #    30 jours sous-estimait de moitié le régime atteint.
    ramp = _maturation_ramp(metrics, gsc_property, articles, main_wave)

    # 7. Contrôle de cohérence WordPress : un article modifié après son
    #    refresh a une fenêtre « après » qui mélange deux interventions.
    touched = []
    if check_wp:
        modified = _wp_modified(site, [a["slug"] for a in articles])
        for a in articles:
            m = modified.get(a["slug"])
            a["wp_modified"] = m
            if m and m > a["pushed"] and m <= a["after"]["end"]:
                touched.append({"slug": a["slug"], "pushed": a["pushed"],
                                "modified": m})

    payload = {
        "site": site,
        "period": {"start": start, "end": end, "month": month},
        "data_end": data_end,
        "maturity_target": maturity,
        # Les sources ne sont jamais confondues : le rapport doit pouvoir dire
        # de quelle trace chaque date provient, et laquelle est la plus sûre.
        "scope_tab": tab,
        "source_mode": source,
        "pushed_source": (
            (f"colonne « {NOTION_REFRESH_COL} » de la base Notion"
             + (" + lastmod du sitemap" if recovered else ""))
            if source == "notion"
            else f"colonne « Date de refresh » de l'onglet {tab}" if tab
            else "wp_backups + wp_modified" if recovered
            else "wp_backups"
        ),
        "pushed_sources": (
            {"notion_column": n_traced, "sitemap_lastmod": len(recovered)}
            if source == "notion"
            else {"sheet_column": n_traced} if tab else {
                "wp_backups": n_traced,
                "wp_modified_manual": len(recovered),
            }
        ),
        "with_queries": bool(with_queries),
        "top_queries": top_queries,
        "counts": {
            "republished": len(in_period),
            "measurable": len(articles),
            "skipped": len(skipped),
        },
        "coverage": {
            "pct": coverage,
            "ready_on": ready_on,
            "partial": bool(partial),
            # Reculs effectivement obtenus : quand ils sont très inégaux, le
            # total agrège des effets à des stades de maturation différents.
            "maturity_min": min(a["maturity"] for a in articles),
            "maturity_max": max(a["maturity"] for a in articles),
        },
        "skipped_slugs": sorted(set(skipped)),
        "overall": overall,
        "control": control,
        "winners": len(winners),
        "median_factor": median_factor,
        "by_wave": by_wave,
        "hindsight_days": hindsight_days,
        "by_category": by_category,
        "ramp": ramp,
        "touched_after_refresh": touched,
        "trajectory": [],
        "top_progressions": ranked[:top],
        "top_regressions": [a for a in ranked[::-1] if a["impressions_delta"] < 0][:top],
        "articles": articles,
    }

    # La trajectoire se lit après coup : elle inclut le mois courant, qui doit
    # donc être complet avant d'être comparé aux précédents.
    payload["trajectory"] = _trajectory(site, month, payload)

    if not dry_run:
        stem = f"impact_refresh_{month or start}_{site}".replace(".", "-")
        payload["json_path"] = _dump(site, stem, payload)
        payload["html_path"] = _dump_html_impact(site, stem, payload)
        if pdf:
            payload["pdf_path"] = _dump_pdf_impact(site, stem, payload,
                                                   annex=pdf_annex)
    return payload


def _maturation_ramp(
    metrics: dict, gsc_property: str, articles: list[dict], wave: str
) -> list[dict]:
    """Impressions/jour par tranche de 7 j après refresh, pour une vague.

    Répond à « quelle fenêtre choisir ? » par la mesure plutôt que par une
    convention : elle montre où en est la montée en charge. Sur la cohorte du
    6 août 2026 (39 articles), le régime passait de ×1,5 la première semaine à
    ×4,0 à J+34, sans plateau — autrement dit une lecture à 30 jours ne capte
    pas l'effet complet, elle en capte la pente.

    Normalisation en impressions **par jour** : la dernière tranche est
    tronquée par la latence GSC, un total brut la ferait paraître en chute.
    """
    slugs = {a["slug"] for a in articles if a["pushed"] == wave}
    if not slugs:
        return []

    d = datetime.strptime(wave, "%Y-%m-%d")
    data_end = datetime.strptime(
        (datetime.now() - timedelta(days=GSC_LAG_DAYS)).strftime("%Y-%m-%d"),
        "%Y-%m-%d",
    )

    def impressions(a: datetime, b: datetime) -> tuple:
        days = (b - a).days + 1
        if days < 1:
            return None, 0
        by_page = _fetch_pages_metrics(
            gsc_property, a.strftime("%Y-%m-%d"), b.strftime("%Y-%m-%d")
        )
        total = sum(
            v["impressions"] for u, v in by_page.items()
            if _slug_from_url(u) in slugs
        )
        return total / days, days

    base, base_days = impressions(d - timedelta(days=28), d - timedelta(days=1))
    if not base:
        return []

    out = [{
        "label": "Avant refresh",
        "days": base_days,
        "per_day": round(base, 1),
        "factor": 1.0,
    }]
    for i in range(5):
        a = d + timedelta(days=1 + i * 7)
        b = min(a + timedelta(days=6), data_end)
        if b < a:
            break
        per_day, days = impressions(a, b)
        if per_day is None:
            break
        out.append({
            "label": f"J+{1 + i * 7} → J+{1 + i * 7 + days - 1}",
            "days": days,
            "per_day": round(per_day, 1),
            "factor": round(per_day / base, 2),
            "partial": days < 7,
        })
    return out


def _group(rows: list[dict], key_fn) -> dict:
    out = defaultdict(list)
    for r in rows:
        out[key_fn(r)].append(r)
    return dict(out)


def _category(a: dict) -> str:
    """Le vertical éditorial de l'article.

    Deux sites, deux façons de le porter : superprof.fr-ressources l'inscrit
    dans l'URL (`/ressources/<vertical>/…`), enseigna.fr le tient dans une
    colonne de sa base Notion (les URLs y sont à plat, sans segment de
    rubrique). Sans ce second cas, toutes les fiches d'enseigna.fr
    s'affichaient « (hors arborescence) ».
    """
    m = re.search(r"/ressources/([^/]+)/", a["url"])
    if m:
        return m.group(1)
    return a.get("category") or "(sans catégorie)"


# ---------------------------------------------------------------------------
# Rendu HTML
# ---------------------------------------------------------------------------

def _fr_date(iso: str) -> str:
    d = datetime.strptime(iso, "%Y-%m-%d")
    return f"{d.day} {_MONTHS_FR[d.month - 1]} {d.year}"


def _de(label: str) -> str:
    """« août 2026 » → « d'août 2026 » ; « mai 2026 » → « de mai 2026 »."""
    return f"d'{label}" if label[:1].lower() in "aeiouâéêîôû" else f"de {label}"


def _fr_month(start: str) -> str:
    d = datetime.strptime(start, "%Y-%m-%d")
    return f"{_MONTHS_FR[d.month - 1]} {d.year}"


def _fr_dec(v) -> str:
    """0.81 → « 0,81 ». Le séparateur décimal français, que `_fr_num` (qui ne
    traite que les milliers) laisse passer en notation anglaise."""
    return "–" if v is None else str(v).replace(".", ",")


def _pct_span(pct: Optional[float]) -> str:
    """Au-delà de +1 000 %, un multiplicateur se lit mieux : « × 175 » plutôt
    que « +17 420,0 % » (volume-fraction-resolution, 5 → 876 impressions). Le
    JSON garde le pourcentage ; seul l'affichage change."""
    if pct is None:
        return '<span style="color:#9ca3af">n/a</span>'
    color = _POS if pct > 0 else (_NEG if pct < 0 else "#6b7280")
    label = f"× {_fr_num(round(1 + pct / 100))}" if pct >= 1000 else _signed_pct(pct)
    return f'<span style="color:{color};font-weight:600">{label}</span>'


def _pos(p) -> str:
    """Position en entier. Le JSON garde la décimale, l'affichage l'arrondit.

    Une position GSC est une moyenne pondérée : sa décimale n'a pas de sens
    opérationnel (on n'est pas « 8,4e »), et elle encombre une lecture rapide.
    """
    return "–" if p is None else str(int(round(p)))


def _pos_cell(pb, pa) -> str:
    """Position avant → après, colorée sur l'amélioration et non sur le signe.

    Passer de 12 à 7 est un gain : le delta brut vaut -5, l'affichage doit
    montrer +5 en vert. Confondre les deux fait lire un succès comme un recul.

    Le delta se calcule sur les valeurs **non arrondies**, puis s'arrondit. En
    arrondissant d'abord, un gain réel de 8,4 → 7,5 (0,9 place) s'afficherait
    « 8 → 8, +0 » : l'arrondi effacerait le mouvement qu'on cherche à montrer.
    """
    if pb is None or pa is None:
        return "–"
    d = round(pb - pa)
    col = _POS if d > 0 else (_NEG if d < 0 else "#6b7280")
    sign = "+" if d > 0 else ""
    return (f'{_pos(pb)} → {_pos(pa)} '
            f'<span style="color:{col};font-size:10.5px">{sign}{d}</span>')


def _net_cell(a: dict) -> str:
    """Écart net, ou le volume créé quand l'article partait de zéro.

    Une page invisible avant refresh n'a pas de pourcentage de progression :
    la division est impossible. Afficher « n/a » effaçait pourtant de vraies
    réussites — sur août 2026, quatre articles créaient 968 impressions à eux
    seuls et ressortaient tous comme non mesurables. Le volume, lui, se dit.
    """
    net = a.get("net_impressions_pct")
    if net is not None:
        return _pct_span(net)
    created = a["after"]["impressions"]
    if not a["before"]["impressions"] and created:
        return (f'<span style="color:{_POS};font-weight:600">nouveau</span>'
                f'<br><span style="font-size:10px;color:#6b7280">'
                f'{_fr_num(created)} impr.</span>')
    return _pct_span(None)


def _net_cell_with_expected(a: dict) -> str:
    """Écart net d'un article, avec le repère « attendu → obtenu » en volume.

    `_net_cell` seule affiche un pourcentage sans rien pour l'ancrer, alors
    que la ligne Impressions juste au-dessus montre « 374 → 2 761 » : le
    lecteur voit un nombre concret pour tout sauf l'écart net, précisément le
    chiffre le moins intuitif de la fiche (relecture : « c'est abstrait »).
    Ici, « attendu » est le volume que l'article aurait fait au rythme du
    contrôle sur sa propre fenêtre (`before × (1 + control_pct)`), le même
    calcul que la tuile globale du verdict, juste reporté par article.
    """
    pct_span = _net_cell(a)
    ctrl_pct = a.get("control_impressions_pct")
    ib = a["before"]["impressions"]
    if ctrl_pct is None or not ib:
        return pct_span
    expected = round(ib * (1 + ctrl_pct / 100))
    return (
        f'{pct_span}<br><span style="font-size:10px;color:#6b7280">'
        f'{_fr_num(expected)} attendues → {_fr_num(a["after"]["impressions"])} '
        f'obtenues</span>'
    )


def _top_query(a: dict) -> str:
    """Requête la plus porteuse après refresh, maintenue ou gagnée.

    Sert à identifier un article dans le tableau sans déplier sa fiche : un slug
    seul ne dit pas sur quoi la page travaille.
    """
    q = a.get("queries") or {}
    pool = (q.get("held") or []) + (q.get("gained") or [])
    if not pool:
        return "–"
    best = max(pool, key=lambda x: x.get("impressions_after", 0))
    return best["query"]


def _ord(p) -> str:
    """Position en ordinal français : 1 → « 1re », 7 → « 7e »."""
    if p is None:
        return "–"
    n = int(round(p))
    return "1re" if n == 1 else f"{n}e"


def _pl(n: int, word: str) -> str:
    """« 5 requête perdues » n'est pas du français : chaque mot prend le pluriel."""
    if n <= 1:
        return f"{n} {word}"
    return f"{n} " + " ".join(w if w.endswith("s") else w + "s" for w in word.split())


def _top_queries_merged(a: dict, n: int) -> list[dict]:
    """Les n requêtes qui pèsent le plus sur l'article, avant ou après.

    Lit `queries.top` quand le JSON le porte (calculé sur toutes les requêtes
    de l'article). Un JSON produit avant ce champ n'a que les trois familles
    tronquées à n : on les fusionne, ce qui couvre le vrai top n par volume
    « après » (maintenues et gagnées sont classées dessus) mais peut manquer
    une requête maintenue qui s'est effondrée. Relancer la collecte comble ce
    trou ; le rendu ne doit pas échouer en attendant.
    """
    q = a.get("queries") or {}
    if q.get("top"):
        return q["top"][:n]
    rows = []
    for kind, key in (("maintenue", "held"), ("gagnée", "gained"), ("perdue", "lost")):
        for x in q.get(key) or []:
            rows.append({**x, "kind": kind})
    rows.sort(key=lambda x: (-max(x["impressions_before"], x["impressions_after"]),
                             -x["impressions_after"]))
    return rows[:n]


def _kind_tag(kind: str) -> str:
    cls = {"gagnée": "k-g", "maintenue": "k-m", "perdue": "k-p"}.get(kind, "k-m")
    return f'<span class="k {cls}">{kind}</span>'


def _query_reading(a: dict) -> str:
    """Deux à quatre phrases par article : d'où vient le volume, ce que font
    les requêtes déjà captées, ce qui a disparu.

    Chaque nombre est lu dans le dict de l'article, jamais déduit ; le texte
    décrit un déplacement de requêtes, il n'en affirme pas la cause (skill
    `impact-report`, « Ce qui se joue dans la troisième phrase »).

    **La part non attribuée.** GSC ne rattache pas toutes les impressions
    d'une page à une requête : les requêtes rares sont anonymisées. Sur
    `theorie-calculs-travail` (août 2026), la page fait 309 impressions et
    ses 5 requêtes visibles en totalisent 6 : écrire que « le volume vient de
    ces requêtes » serait faux. Les familles étant tronquées à n, on ne
    connaît pas la somme exacte, mais une borne haute suffit (chaque requête
    manquante pèse au plus la plus petite affichée) : sous 50 % du volume de
    la page, la lecture commence par le dire et le reste est présenté comme
    « la part visible ».

    **Une position ne se cite que sur du volume.** Gagner 58 places sur une
    requête à 2 impressions est du bruit de mesure : un mouvement de
    classement n'est nommé que si la requête a au moins 3 impressions de
    chaque côté et 5 d'un côté.
    """
    q = a.get("queries") or {}
    counts = q.get("counts") or {}
    if not q or not (counts.get("after") or counts.get("before")):
        return ""
    gained, lost = counts.get("gained", 0), counts.get("lost", 0)
    held = counts.get("held", 0)
    g_rows = sorted(q.get("gained") or [], key=lambda x: -x["impressions_after"])
    l_rows = sorted(q.get("lost") or [], key=lambda x: -x["impressions_before"])
    h_rows = list(q.get("held") or [])
    ib, ia = a["before"]["impressions"], a["after"]["impressions"]
    delta = ia - ib

    def imp(n):
        return _pl(n, "impression")

    def ex_after(x):
        pos = f", {_ord(x['position_after'])} place" if x.get("position_after") else ""
        return f"« {x['query']} » ({imp(x['impressions_after'])}{pos})"

    def ex_lost(x):
        return f"« {x['query']} » ({imp(x['impressions_before'])} l'an dernier)"

    def ex_held(x):
        pb, pa = x.get("position_before"), x.get("position_after")
        pos = f" ({_ord(pb)} → {_ord(pa)})" if pb is not None and pa is not None else ""
        return (f"« {x['query']} » passe de {_fr_num(x['impressions_before'])} à "
                f"{imp(x['impressions_after'])}{pos}")

    def move(x):
        d = round(x.get("position_delta") or 0)
        verb = "gagne" if d > 0 else "perd"
        return (f"« {x['query']} » {verb} {_pl(abs(d), 'place')} "
                f"({_ord(x['position_before'])} → {_ord(x['position_after'])})")

    def solid(x):
        lo = min(x["impressions_before"], x["impressions_after"])
        hi = max(x["impressions_before"], x["impressions_after"])
        return lo >= 3 and hi >= 5

    def bound(rows, key, total):
        """Borne haute du volume attribué à une famille tronquée à n."""
        if not rows:
            return 0
        s = sum(x[key] for x in rows)
        return s + max(0, total - len(rows)) * min(x[key] for x in rows)

    def cap(s):
        return s[:1].upper() + s[1:]

    parts, cited, hedge = [], set(), ""
    after_max = (bound(h_rows, "impressions_after", held)
                 + bound(g_rows, "impressions_after", gained))
    if delta > 0 and ia >= 20 and after_max < ia * 0.5:
        # En incise et non en phrase séparée : la moitié des fiches d'août
        # 2026 sont dans ce cas, et une phrase de deux lignes répétée 44 fois
        # noyait la lecture. Le principe est expliqué une fois, dans le
        # chapeau de la section.
        hedge = (f"sur la part visible (GSC n'attribue à des requêtes "
                 f"identifiables qu'au plus {_fr_num(after_max)} des "
                 f"{_fr_num(ia)} impressions), ")

    g_sum = sum(x["impressions_after"] for x in g_rows)
    h_gain = sum(max(0, x["impressions_after"] - x["impressions_before"]) for x in h_rows)
    l_sum = sum(x["impressions_before"] for x in l_rows)

    if delta > 0:
        if g_rows and g_sum >= h_gain:
            ex = " et ".join(ex_after(x) for x in g_rows[:2])
            parts.append(cap(f"{hedge}le volume supplémentaire vient d'abord de "
                             f"{_pl(gained, 'requête nouvelle')}, comme {ex}."))
            cited.update(x["query"] for x in g_rows[:2])
        elif h_gain > 0:
            best = max(h_rows, key=lambda x: x["impressions_after"] - x["impressions_before"])
            parts.append(cap(f"{hedge}le volume supplémentaire vient d'abord de "
                             f"requêtes déjà captées : {ex_held(best)}."))
            cited.add(best["query"])
        elif h_rows:
            worst = min(h_rows, key=lambda x: x["impressions_after"] - x["impressions_before"])
            parts.append(cap(f"{hedge}les requêtes identifiables reculent "
                             f"({ex_held(worst)}) : le volume supplémentaire vient "
                             f"de requêtes non détaillées."))
            cited.add(worst["query"])
        movers = [x for x in h_rows if solid(x) and x["query"] not in cited
                  and abs(round(x.get("position_delta") or 0)) >= 2]
        if movers:
            best = max(movers, key=lambda x: x["position_delta"])
            worst = min(movers, key=lambda x: x["position_delta"])
            if best["position_delta"] > 0:
                s = f"Sur les requêtes historiques, {move(best)}"
                if worst is not best and worst["position_delta"] < 0:
                    s += f" tandis que {move(worst)}"
                parts.append(s + ".")
            else:
                parts.append(f"Sur les requêtes historiques, {move(worst)}.")
        if l_rows:
            big = l_rows[0]
            # « À surveiller » seulement sur du volume : une requête à 10
            # impressions ou plus, ou un cumul perdu d'au moins 10 % de la
            # page ET 10 impressions (7 impressions perdues sur une page à 207
            # n'appellent aucune action).
            if big["impressions_before"] >= 10 or (l_sum >= ib * 0.1 and l_sum >= 10):
                s = f"À surveiller : {ex_lost(big)} ne ressort plus"
                if len(l_rows) > 1 and l_rows[1]["impressions_before"] >= 5:
                    s += f", ni {ex_lost(l_rows[1])}"
                parts.append(s + ".")
            else:
                parts.append(f"{cap(_pl(lost, 'requête perdue'))}, "
                             f"marginale{'s' if lost > 1 else ''} : {ex_lost(big)}.")
    elif delta < 0:
        drops = [x for x in h_rows if x["impressions_before"] > x["impressions_after"]]
        big_drop = (max(drops, key=lambda x: x["impressions_before"] - x["impressions_after"])
                    if drops else None)
        drop_vol = (big_drop["impressions_before"] - big_drop["impressions_after"]) if big_drop else 0
        if l_rows and (not big_drop or l_sum >= drop_vol):
            ex = " et ".join(ex_lost(x) for x in l_rows[:2])
            parts.append(f"La page ne ressort plus sur {_pl(lost, 'requête')}, dont {ex}.")
            if big_drop and drop_vol >= 5:
                parts.append(f"Sur les requêtes conservées, {ex_held(big_drop)}.")
        elif big_drop:
            parts.append(f"Le recul tient aux requêtes déjà captées : {ex_held(big_drop)}.")
            if l_rows:
                parts.append(f"{cap(_pl(lost, 'requête perdue'))} par ailleurs, "
                             f"dont {ex_lost(l_rows[0])}.")
        ups = [x for x in h_rows if solid(x) and round(x.get("position_delta") or 0) >= 2]
        if ups:
            parts.append(f"La position s'améliore pourtant : "
                         f"{move(max(ups, key=lambda x: x['position_delta']))}.")
        if g_rows:
            if g_sum < abs(delta) * 0.2:
                parts.append(f"En face, {_pl(gained, 'requête nouvelle')} pour peu "
                             f"de volume : {ex_after(g_rows[0])}.")
            else:
                parts.append(f"En face, {_pl(gained, 'requête nouvelle')}, dont "
                             f"{ex_after(g_rows[0])}.")
    else:
        parts.append(f"Volume inchangé sur un an : {_pl(gained, 'requête gagnée')}, "
                     f"{_pl(lost, 'perdue')}, {_pl(held, 'maintenue')}.")
    return " ".join(parts[:4])


def _diag_badge(diag: Optional[str]) -> str:
    """Étiquette de diagnostic, colorée par famille.

    Neutre (gris) pour « sans mouvement net » : ni un succès ni un échec, donc
    ni vert ni rouge.
    """
    if not diag:
        return ""
    color = {
        DIAGS["coverage"]: _POS,
        DIAGS["ranking"]: _POS,
        DIAGS["query_loss"]: _NEG,
        DIAGS["narrowed"]: _NEG,
    }.get(diag, "#6b7280")
    return f'<span class="diag" style="color:{color};border-color:{color}">{diag}</span>'


# Nombre de cas notables commentés sous le tableau « Le reste du lot ». Assez
# pour couvrir les contradictions réelles d'un mois type sans transformer le
# ventre mou en une troisième section de fiches détaillées — c'est justement
# ce que « le reste du lot » n'est pas censé devenir.
REST_NOTABLE_MIN = 3
REST_NOTABLE_MAX = 6


def _notable_rest_cases(rest: list[dict]) -> list[dict]:
    """Sélectionne les cas les plus « racontables » du ventre mou.

    Le reste du lot (ni dans les plus fortes progressions, ni dans les plus
    fortes baisses) est un tableau sec : aucune ligne n'ouvre sur une
    décision individuelle. Mais certaines lignes contiennent une contradiction
    entre métriques qui mérite une phrase — typiquement un trafic qui monte
    alors que la position recule (l'inverse existe aussi, plus rare) : c'est
    le cas qui a motivé cette section (`theorie-calculs-travail` : +291
    impressions, position 7,4 → 13,6).

    Deux familles de sélection, sans doublon :

    - **divergence de signe** entre le delta d'impressions et le delta de
      position (l'un monte, l'autre descend) : c'est la contradiction qui
      appelle une explication, une hausse de trafic ET de position n'en a pas
      besoin ;
    - **plus gros mouvements bruts** parmi le reste, pour ne pas ignorer un
      article qui pèse lourd simplement parce qu'il ne contredit rien.

    Retourne au plus `REST_NOTABLE_MAX` articles, en s'arrêtant sous
    `REST_NOTABLE_MIN` si le lot n'en contient pas assez (un mois calme ne
    doit pas être forcé à produire des paragraphes qui n'ont rien à dire).
    """
    def position_delta(a: dict) -> Optional[float]:
        pb = a["before"].get("position")
        pa = a["after"].get("position")
        if pb is None or pa is None:
            return None
        return pb - pa  # positif = amélioration (comme _pos_cell)

    divergent = []
    for a in rest:
        pd = position_delta(a)
        idlt = a.get("impressions_delta", 0)
        if pd is None or idlt == 0:
            continue
        # Trafic en hausse et position qui recule, ou l'inverse : les deux
        # signes désaccordés. `pd` positif = position améliorée.
        if (idlt > 0 and pd < 0) or (idlt < 0 and pd > 0):
            divergent.append(a)
    divergent.sort(key=lambda a: -abs(a.get("impressions_delta", 0)))

    picked = divergent[:REST_NOTABLE_MAX]
    if len(picked) < REST_NOTABLE_MIN:
        picked_ids = {id(a) for a in picked}
        biggest = sorted(
            (a for a in rest if id(a) not in picked_ids),
            key=lambda a: -abs(a.get("impressions_delta", 0)),
        )
        picked += biggest[:REST_NOTABLE_MAX - len(picked)]
    return picked[:REST_NOTABLE_MAX]


def _rest_case_paragraph(a: dict) -> str:
    """Paragraphe explicatif d'un cas notable du reste du lot.

    Sur le modèle validé en relecture : les chiffres réels de l'article
    d'abord (jamais inventés, lus dans son propre dict), puis une hypothèse
    SEO/GEO explicitement présentée comme une hypothèse — jamais une cause
    établie, cohérent avec le refus de fausse causalité du reste du rapport
    (skill `impact-report`, section « Ce qui se joue dans la troisième
    phrase »).

    L'hypothèse varie selon ce que montre le déplacement de requêtes de
    l'article (`queries.counts`), plutôt qu'un texte fixe répété à
    l'identique d'un cas à l'autre : six paragraphes qui se terminent tous par
    la même phrase-catalogue (« cannibalisation... dilution... concurrence »)
    ne se lisent plus comme six analyses mais comme un gabarit rempli, ce qui
    a été corrigé après une première génération qui faisait exactement ça.
    """
    b, af = a["before"], a["after"]
    ib, ia = b["impressions"], af["impressions"]
    cb, ca = b["clicks"], af["clicks"]
    pb, pa = b.get("position"), af.get("position")
    idlt = a.get("impressions_delta", 0)
    counts = (a.get("queries") or {}).get("counts") or {}
    gained, lost, held = counts.get("gained", 0), counts.get("lost", 0), counts.get("held", 0)

    traffic_verb = "on passe de" if idlt >= 0 else "on retombe de"
    sentence = (
        f'sur <a href="{a["url"]}">{a["slug"]}</a>, {traffic_verb} '
        f'{_fr_num(ib)} à {_fr_num(ia)} impressions et de {cb} à {ca} clics'
    )

    if pb is not None and pa is not None:
        moved = round(pb - pa)  # positif = amélioration
        if moved < 0:
            sentence += (
                f', ce qui traduit {"un refresh efficace" if idlt > 0 else "une érosion"}'
                f'. Mais paradoxalement, la page recule en position de '
                f'{_pos(pb)} à {_pos(pa)} (perd {abs(moved)} place'
                f'{"s" if abs(moved) > 1 else ""})'
                f'{_rest_hypothesis(gained, lost, held, worsening=True)}'
            )
        elif moved > 0:
            sentence += (
                f', portée par une amélioration de position de {_pos(pb)} à '
                f'{_pos(pa)} (gagne {moved} place{"s" if moved > 1 else ""})'
            )
            if idlt < 0:
                sentence += _rest_hypothesis(gained, lost, held, worsening=False)
            else:
                sentence += "."
        else:
            sentence += "."
    else:
        sentence += "."

    diag = a.get("diagnosis")
    diag_txt = f' Diagnostic : {diag.lower()}.' if diag else ""

    return f"<p>{sentence}{diag_txt}</p>"


def _rest_hypothesis(gained: int, lost: int, held: int, worsening: bool) -> str:
    """Hypothèse SEO/GEO pour un cas où trafic et position divergent.

    Choisie à partir de ce que le mouvement de requêtes de l'article donne à
    voir (pas au hasard) : `lost`/`gained`/`held` disent si le périmètre de
    mots-clés a bougé, ce qui oriente vers une hypothèse plutôt qu'une autre.
    Reste une hypothèse déclarée comme telle dans chaque branche : la mesure
    n'établit aucune causalité (skill `impact-report`, section 3).
    """
    if worsening:
        # Trafic en hausse, position en recul : le volume vient d'ailleurs
        # que du classement. Le mouvement de requêtes dit d'où. Le ratio
        # gagnées/maintenues varie d'un article à l'autre : le dire en
        # chiffres réels évite que deux articles dans la même branche
        # produisent un texte identique au mot près.
        if gained > held:
            ratio = round(gained / held) if held else None
            scale = (
                f'{gained} requêtes gagnées contre {held} maintenue'
                f'{"s" if held > 1 else ""}'
                + (f' (environ {ratio}× plus de nouvelles requêtes que '
                   f'd\'historiques)' if ratio and ratio >= 2 else '')
            )
            return (
                f'. {scale} : le volume vient surtout de mots-clés nouveaux, '
                'pas du classement sur les requêtes déjà captées avant '
                'refresh. Une couverture élargie à ce point peut diluer la '
                "pertinence perçue sur la requête d'origine, ou simplement "
                'traduire un contenu qui répond désormais à plus de '
                'variantes. Hypothèse à vérifier plutôt qu\'à tenir pour '
                'acquise.'
            )
        if lost > 0:
            return (
                f'. {lost} requête{"s" if lost > 1 else ""} déjà captée'
                f'{"s" if lost > 1 else ""} ont disparu du classement, ce qui '
                'peut expliquer le recul de position sur le reste : une autre '
                'page du site, ou un concurrent, a pu progresser sur ces '
                'mêmes requêtes. Hypothèse à vérifier plutôt qu\'à tenir pour '
                'acquise.'
            )
        return (
            '. Le périmètre de requêtes est resté stable : le recul de '
            'position sur un volume qui progresse suggère une concurrence '
            'accrue sur ces mots-clés plutôt qu\'un problème du contenu '
            "lui-même. Hypothèse à vérifier plutôt qu'à tenir pour acquise."
        )
    # Position améliorée, trafic en recul : le classement s'améliore sur un
    # périmètre qui rapporte moins de volume qu'avant.
    if lost > gained:
        return (
            f'. Ce qui reste paradoxal : la page se classe mieux mais a perdu '
            f'{lost} requête{"s" if lost > 1 else ""} contre {gained} gagnée'
            f'{"s" if gained > 1 else ""}, signe possible d\'un resserrement '
            "du périmètre plutôt que d'un problème de classement. Hypothèse à "
            "vérifier."
        )
    return (
        '. Ce qui reste paradoxal : la page se classe mieux mais capte moins '
        "de volume, signe possible d'une baisse de la demande sur ses "
        "requêtes plutôt que d'un problème éditorial. Hypothèse à vérifier."
    )


def _rest_notable_block(rest: list[dict]) -> str:
    cases = _notable_rest_cases(rest)
    if not cases:
        return ""
    paras = "".join(_rest_case_paragraph(a) for a in cases)
    return f"""
 <div class="ctx">
  <p class="lead" style="margin-bottom:10px"><strong>Quelques cas du reste du
  lot valent une explication</strong>, choisis parce que leur trafic et leur
  position évoluent en sens contraires ou parce qu'ils pèsent le plus dans ce
  sous-ensemble.</p>
  {paras}
 </div>"""


def _render_impact(r: dict, annex: bool = True) -> str:
    """Rapport à trois étages : verdict, ce sur quoi on agit, le lot complet.

    Le rapport n'avait que deux volumes : 2 pages sans aucune URL, ou 85 pages
    détaillant les 165 articles. Le premier ne disait pas quoi faire, le second
    n'était pas parcouru. Le cran qui manquait est celui du milieu.

    - **Étage 1 (pages 1-2)** : le verdict net, sa fiabilité, le gradient de
      recul, ses réserves, et pourquoi il diffère d'un suivi d'onglet. Un
      directeur arbitre trois choses — continuer, changer d'échelle, changer de
      direction — et rien d'autre ne l'y aide.
    - **Étage 2** : les plus fortes progressions et les plus fortes baisses en
      fiche, avec leur diagnostic et leurs requêtes. C'est l'outil de travail,
      celui qui dit *sur quelles requêtes* un article a bougé, donc quoi refaire.
      Le reste du lot suit en tableau : il n'ouvre sur aucune décision.
    - **Étage 3 (`annex`)** : le tableau exhaustif, pour l'archivage.

    Les sauts de page CSS séparent physiquement les trois.
    """
    o, c = r["overall"], r["control"]
    p = r["period"]
    month_label = p.get("month") and _fr_month(p["start"]) or (
        f"{_fr_date(p['start'])} – {_fr_date(p['end'])}"
    )
    n_art = r["counts"]["measurable"]
    # Variation brute d'une année sur l'autre, et non plus l'écart au groupe de
    # contrôle. Le contrefactuel répondait à « ces articles ont-ils fait mieux
    # que le reste du site ? », une question qui ne se pose pas : on refresh
    # précisément les articles dont le trafic est atone, donc un écart avec le
    # reste du site est attendu par construction et n'apprend rien. Ce qui se
    # lit, c'est ce que les articles font aujourd'hui contre ce qu'ils
    # faisaient il y a un an. Le contrôle reste calculé dans le JSON pour qui
    # veut le drill-down.
    var_i, var_c = o["impressions_pct"], o["clicks_pct"]

    # ------------------------------------------------------------ fiabilité
    # Trois familles plutôt que « gagnants / perdants » : un article à +2 % n'a
    # pas bougé, le compter comme une victoire gonfle le taux de réussite et
    # rend le chiffre attaquable. Le seuil de 5 % est le bruit de mesure GSC.
    up = [a for a in r["articles"] if (a["impressions_pct"] or 0) > 5]
    flat = [a for a in r["articles"] if -5 <= (a["impressions_pct"] or 0) <= 5]
    down = [a for a in r["articles"] if (a["impressions_pct"] or 0) < -5]
    seg = [
        ("En progression", len(up), _POS),
        ("Stables", len(flat), "#9ca3af"),
        ("En recul", len(down), _NEG),
    ]
    hit = round(len(up) / n_art * 100) if n_art else 0

    # Camembert : part-of-whole à 3 segments, sous la limite de 6 au-delà de
    # laquelle un secteur cesse d'être lisible. Les 12 catégories éditoriales
    # auraient violé cette règle — elles restent en table, pas en secteurs.
    total_seg = sum(v for _, v, _ in seg) or 1
    cx = cy = 88
    rad = 76
    angle = -90.0
    slices = ""
    for label, val, col in seg:
        if not val:
            continue
        sweep = val / total_seg * 360
        a0, a1 = math.radians(angle), math.radians(angle + sweep)
        x0, y0 = cx + rad * math.cos(a0), cy + rad * math.sin(a0)
        x1, y1 = cx + rad * math.cos(a1), cy + rad * math.sin(a1)
        large = 1 if sweep > 180 else 0
        if sweep >= 359.99:
            slices += (f'<circle cx="{cx}" cy="{cy}" r="{rad}" fill="{col}"/>')
        else:
            slices += (
                f'<path d="M{cx},{cy} L{x0:.2f},{y0:.2f} '
                f'A{rad},{rad} 0 {large},1 {x1:.2f},{y1:.2f} Z" '
                f'fill="{col}" stroke="#fff" stroke-width="2"/>'
            )
        angle += sweep
    # Trou central : le donut porte le taux de réussite, qui est le chiffre que
    # le lecteur cherche dans ce graphique. Le laisser hors du dessin oblige à
    # faire la division de tête.
    slices += f'<circle cx="{cx}" cy="{cy}" r="44" fill="#fff"/>'

    # Le chiffre central est posé en HTML par-dessus le SVG, pas en <text> :
    # WeasyPrint (moteur du PDF) ne rend pas le texte SVG inline, et le donut
    # partait sans le seul nombre que le lecteur y cherche.
    donut = (
        f'<div class="donut">'
        f'<svg width="176" height="176" viewBox="0 0 176 176" role="img" '
        f'aria-label="Répartition des {n_art} articles : {len(up)} en progression, '
        f'{len(flat)} stables, {len(down)} en recul">{slices}</svg>'
        f'<div class="dctr"><div class="dpct">{hit} %</div>'
        f'<div class="dlab">en hausse</div></div></div>'
    )
    legend = "".join(
        f'<div class="lg"><span class="dot" style="background:{col}"></span>'
        f'<strong>{val}</strong> {label}'
        f'<span class="lgp">{round(val / total_seg * 100)} %</span></div>'
        for label, val, col in seg
    )

    def tile(label, value, sub=""):
        return (
            f'<div class="tile"><div class="tl">{label}</div>'
            f'<div class="tv">{value}</div><div class="ts">{sub}</div></div>'
        )

    # Position moyenne du lot, sur les seuls articles classés des deux côtés :
    # moyenner « avant » sur 83 articles et « après » sur 86 comparerait deux
    # populations différentes, et l'entrée de trois pages jusque-là non
    # classées suffirait à faire bouger la moyenne sans qu'aucune page n'ait
    # gagné une place.
    paired = [a for a in r["articles"]
              if a["before"].get("position") is not None
              and a["after"].get("position") is not None]
    pos_before = pos_after = None
    if paired:
        pos_before = round(sum(a["before"]["position"] for a in paired) / len(paired), 1)
        pos_after = round(sum(a["after"]["position"] for a in paired) / len(paired), 1)

    # Les trois métriques clés en volumes, pas en écart au contrôle : « avant →
    # après » se lit sans connaître la méthode, là où un pourcentage net
    # supposait d'avoir compris le contrefactuel.
    tiles = "".join([
        tile("Impressions", f'{_fr_num(o["impressions_before"])} → '
                            f'{_fr_num(o["impressions_after"])}',
             f'{_signed_pct(var_i)} en un an'),
        tile("Clics", f'{_fr_num(o["clicks_before"])} → {_fr_num(o["clicks_after"])}',
             f'{_signed_pct(var_c)} en un an · CTR {_fr_dec(o["ctr_before"])} % → '
             f'{_fr_dec(o["ctr_after"])} %'),
        tile("Position moyenne",
             "–" if pos_before is None
             else f'{_pos(pos_before)} → {_pos(pos_after)}',
             "non classé l'an dernier" if pos_before is None
             else f'{len(paired)} articles classés les deux années'),
    ])

    # -------------------------------------------------------------- réserves
    cov = r.get("coverage") or {}
    spread = cov.get("maturity_max", 0) - cov.get("maturity_min", 0)
    reserves = []
    if cov.get("pct", 100) < 100:
        reserves.append(
            f"Couverture {cov['pct']} % — {r['counts']['skipped']} articles écartés "
            f"faute de recul suffisant ; lot complet le {_fr_date(cov['ready_on'])}."
        )
    if spread >= 14:
        reserves.append(
            f"Reculs de {cov['maturity_min']} à {cov['maturity_max']} jours selon "
            f"l'article : l'effet croissant avec le temps, les republications de fin "
            f"de mois sont sous-évaluées dans le total."
        )
    if r.get("touched_after_refresh"):
        reserves.append(
            f"{len(r['touched_after_refresh'])} articles retouchés après leur refresh : "
            f"leur évolution mélange deux interventions."
        )
    # Les articles republiés à la main n'ont pas de trace de publication : leur
    # date vient du `modified` WordPress, qu'une retouche ultérieure décale. Le
    # dire, sans quoi le rapport présente deux qualités de date comme une seule.
    n_manual = sum(1 for a in r["articles"] if a.get("date_source") == "wp_modified")
    if n_manual:
        reserves.append(
            f"{n_manual} des {n_art} articles ont été republiés manuellement depuis "
            f"WordPress : leur date de refresh est déduite du champ « modifié le », "
            f"à un jour près."
        )
    # Un lot de quelques articles produit des pourcentages spectaculaires qui ne
    # disent presque rien : un seul mouvement fait tout basculer. On le dit en
    # tête des réserves, avant que le lecteur ne cite le chiffre.
    if n_art < 5:
        reserves.insert(0, (
            f"<strong>Effectif trop faible pour conclure</strong> : {n_art} article"
            f"{'s' if n_art > 1 else ''} seulement. Les pourcentages ci-dessus "
            f"basculent sur un seul mouvement et ne sont pas citables comme un "
            f"résultat de mois."
        ))

    low_volume_block = ""
    if n_art < 5:
        low_volume_block = (
            '<div class="reserve" style="margin:14px 0 4px">'
            + reserves.pop(0) + "</div>"
        )

    reserve_block = ""
    if reserves:
        reserve_block = (
            '<div class="reserve"><strong>Réserves de lecture</strong><ul>'
            + "".join(f"<li>{x}</li>" for x in reserves) + "</ul></div>"
        )

    # ------------------------------------------------- mois mesuré (ex-trajectoire)
    # La comparaison mois après mois affichait le mois précédent à côté du mois
    # courant, ce qui a été jugé trompeur ici : ce rapport ne mesure QUE le mois
    # demandé (`--month`), et une barre de juillet dans un rapport d'août laisse
    # croire à une trajectoire alors qu'aucun des deux mois n'est comparé sur la
    # même base après le passage au YoY (chacun compare sa propre vague à sa
    # propre année précédente, pas l'un à l'autre). Le bloc n'affiche donc plus
    # que le mois courant, sans barre ni comparaison visuelle : un seul chiffre
    # ne trace pas de trajectoire, il ne fait que rappeler le verdict déjà
    # donné plus haut.
    #
    # `payload["trajectory"]` reste calculé et écrit dans le JSON (voir
    # `_trajectory`) : il continue d'accumuler l'historique mois par mois sur
    # disque, utile en dehors de ce rendu pour qui veut suivre la série dans le
    # temps (drill-down JSON, ou une future vue dédiée). Seul l'affichage HTML
    # du mois courant a changé.
    # Le bloc porte le même chiffre que le verdict (variation brute sur un an),
    # pas l'écart net au contrôle : afficher +101,7 % ici sous un verdict à
    # +31,9 % faisait lire deux résultats pour le même mois. L'historique
    # (écart net, mois par mois) reste écrit dans le JSON.
    if p.get("month"):
        traj_block = f"""
 <h2>Mois mesuré</h2>
 <p class="lead">Variation d'impressions sur un an pour {month_label} seul, le
 chiffre du verdict. L'historique mois par mois est écrit dans le JSON associé
 (<code>trajectory</code>) à mesure que les rapports s'accumulent.</p>
 <div class="tiles"><div class="tile">
  <div class="tl">{month_label}</div>
  <div class="tv">{_signed_pct(var_i)}</div>
  <div class="ts">{n_art} articles mesurés</div>
 </div></div>"""
    else:
        traj_block = ""

    # ------------------------------------------- distribution du recul (page 1)
    # Le gradient de recul par tranche de maturité (7-15 / 16-25 / 26-30 j) a
    # été retiré avec le passage au YoY : il comparait des articles à des
    # stades de maturation différents côté « avant », ce qui n'existe plus
    # (« avant » est ancré à J-365 avec le même recul que « après », quasi
    # toujours disponible côté GSC). Il n'expliquait donc plus rien : dans la
    # nouvelle méthode, un article en recul l'est vraiment, pas parce que sa
    # mesure est jeune.
    #
    # Ce qui reste vrai : le recul côté « après » varie encore selon la date
    # de republication dans le mois (7 à ~30 j). Ce court bloc en donne la
    # distribution, pour que le lecteur voie d'un coup d'œil si le lot est
    # homogène ou étalé, sans reconstituer un gradient qui n'a plus de sens.
    hindsight = r.get("hindsight_days") or []
    grad_block = ""
    if hindsight:
        lo, hi = min(hindsight), max(hindsight)
        med = hindsight[len(hindsight) // 2]
        grad_block = f"""
 <h2>Recul disponible après refresh</h2>
 <p class="lead">Nombre de jours mesurés après la republication, article par
 article (le recul « avant », lui, est fixe : environ un an). Plus ce recul
 est court, plus les volumes de l'article pèsent peu dans le total.</p>
 <div class="grad"><div><div class="gl">Recul après refresh</div>
 <div class="gv">{lo}-{hi} j</div>
 <div class="gs">médiane {med} j · {len(hindsight)} articles</div></div></div>"""

    # -------------------------------------------------------- fiche par URL
    n_q = r.get("top_queries", 5)

    def art_card(a: dict) -> str:
        """Une fiche = métriques de la page, puis UNE table des requêtes qui
        pèsent le plus (avant ou après), puis sa lecture en deux ou trois
        phrases. Les trois familles côte à côte laissaient ~75 px à la
        requête, coupée en « vitesse de l... », et la colonne position
        débordait sur la voisine : le document envoyé était illisible."""
        q = a.get("queries") or {}
        counts = q.get("counts") or {}
        b, af = a["before"], a["after"]

        qblock = qsum = ""
        if q:
            rows = ""
            for x in _top_queries_merged(a, n_q):
                pb, pa = x.get("position_before"), x.get("position_after")
                if x["kind"] == "maintenue":
                    pos = _pos_cell(pb, pa)
                elif x["kind"] == "gagnée":
                    pos = f"– → {_pos(pa)}"
                else:
                    pos = f"{_pos(pb)} → –"
                rows += (
                    f'<tr><td class="q">{x["query"]}</td>'
                    f'<td>{_kind_tag(x["kind"])}</td>'
                    f'<td class="num">{_fr_num(x["impressions_before"])} → '
                    f'{_fr_num(x["impressions_after"])}</td>'
                    f'<td class="num">{x["clicks_before"]} → {x["clicks_after"]}</td>'
                    f'<td class="num">{pos}</td></tr>'
                )
            if not rows:
                rows = ('<tr><td colspan="5" class="empty">Aucune requête remontée '
                        'par GSC sur les deux fenêtres</td></tr>')
            reading = _query_reading(a)
            qsum = f"""
   <div class="qsum">
    <span><strong>{counts.get("after", 0)}</strong> requêtes après refresh</span>
    <span class="up">+{counts.get("gained", 0)} gagnées</span>
    <span class="dn">−{counts.get("lost", 0)} perdues</span>
    <span>{counts.get("held", 0)} maintenues</span>
   </div>"""
            qblock = f"""
   <table class="qt5"><colgroup><col class="c-q"><col class="c-k"><col class="c-i">
   <col class="c-c"><col class="c-p"></colgroup>
   <thead><tr><th>Top {n_q} requêtes (avant ou après)</th><th>Statut</th>
   <th class="num">Impressions</th><th class="num">Clics</th>
   <th class="num">Position</th></tr></thead>
   <tbody>{rows}</tbody></table>
   {f'<p class="reading">{reading}</p>' if reading else ''}"""

        return f"""
  <div class="card"><div class="ctop">
   <div class="chead">
    <a href="{a["url"]}">{a["slug"]}</a>{_diag_badge(a.get("diagnosis"))}
    <span class="cmeta">{_category(a)} · republié le {_fr_date(a["pushed"])[:-5]}{
     ' (date déduite)' if a.get("date_source") == "wp_modified" else ''} ·
    {a["maturity"]} j de recul</span>
   </div>
   <div class="cstats">
    <div><span class="sl">Impressions</span>
     <span class="sv">{_fr_num(b["impressions"])} → {_fr_num(af["impressions"])}</span>
     {_pct_span(a["impressions_pct"])}</div>
    <div><span class="sl">Clics</span>
     <span class="sv">{b["clicks"]} → {af["clicks"]}</span>
     {_pct_span(a["clicks_pct"])}</div>
    <div><span class="sl">Position</span>
     <span class="sv">{_pos_cell(b.get("position"), af.get("position"))}</span></div>
    <div><span class="sl">Écart net</span>
     <span class="sv">{_net_cell_with_expected(a)}</span></div>
   </div>{qsum}</div>{qblock}
  </div>"""

    ranked = sorted(r["articles"], key=lambda a: a["impressions_delta"], reverse=True)

    # Découpage du lot en trois : ce sur quoi on agit, et le reste.
    #
    # Un rapport qui détaille les 165 articles fait 45 pages et n'est pas
    # parcouru ; un rapport qui n'en détaille aucun ne dit pas quoi faire. Les
    # articles qui ont le plus produit et ceux qui ont le plus reculé sont les
    # seuls dont la fiche ouvre sur une décision — le ventre mou n'appelle
    # aucune action et tient en une ligne de tableau.
    #
    # Les reculs se trient par écart net croissant et non par volume perdu :
    # un article qui perd 400 impressions sur 5 000 va bien, un qui en perd 120
    # sur 157 est en difficulté, et c'est le second qu'il faut regarder.
    detail_n = min(DETAIL_ARTICLES, len(ranked))
    winners = [a for a in ranked if (a.get("net_impressions_pct") or 0) > 5][:detail_n]
    losers = sorted(
        (a for a in r["articles"] if (a.get("net_impressions_pct") or 0) < -5),
        key=lambda a: a.get("net_impressions_pct") or 0,
    )[:detail_n]
    detailed = {id(a) for a in winners} | {id(a) for a in losers}
    rest = [a for a in ranked if id(a) not in detailed]

    win_cards = "".join(art_card(a) for a in winners)
    lose_cards = "".join(art_card(a) for a in losers)
    # Le reste du lot tenait en une ligne par article, avec une seule
    # « requête principale » : le lecteur qui voulait savoir sur quoi un
    # article du ventre mou avait bougé n'avait rien. Même fiche que les
    # extrêmes, du plus fort gain au plus fort recul ; l'index tabulaire du
    # lot reste en annexe.
    rest_cards = "".join(art_card(a) for a in rest)

    def sum_table(rows: list) -> str:
        out = ""
        for a in rows:
            q = (a.get("queries") or {}).get("counts", {})
            top_q = _top_query(a)
            out += (
                "<tr>"
                f'<td><a href="{a["url"]}">{a["slug"]}</a></td>'
                f'<td class="num">{_fr_date(a["pushed"])[:-5]}</td>'
                f'<td class="num">{_fr_num(a["before"]["impressions"])} → '
                f'{_fr_num(a["after"]["impressions"])}</td>'
                f'<td class="num">{_net_cell(a)}</td>'
                f'<td class="num">{a["before"]["clicks"]} → {a["after"]["clicks"]}</td>'
                f'<td class="num">{_pos_cell(a["before"].get("position"), a["after"].get("position"))}</td>'
                f'<td class="num">{q.get("gained", "–")} / {q.get("lost", "–")}</td>'
                f'<td class="dg">{a.get("diagnosis") or "–"}</td>'
                f'<td class="q">{top_q}</td>'
                "</tr>"
            )
        return out

    all_rows = sum_table(ranked)
    rest_notable_block = _rest_notable_block(rest)

    # Trois volumes de document, et non plus deux.
    #
    # Le rapport n'avait que deux crans : 2 pages sans aucune URL, ou 85 pages
    # détaillant les 165 articles. Le premier ne disait pas quoi faire, le
    # second n'était pas parcouru. Les sections « ont grimpé » / « n'ont pas
    # fonctionné » / « le reste » sont désormais toujours rendues (~10 pages,
    # le document qu'on envoie) ; `annex` ne commande plus que le tableau
    # exhaustif du lot, réservé à l'archivage.
    annex_open = '<div class="annex">' if annex else '<div class="annex" hidden>'
    annex_close = "</div>"

    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Impact des refreshs {_de(month_label)} — {r["site"]}</title>
<style>
 @page {{ size:A4; margin:14mm 12mm 16mm;
  @bottom-right {{ content:counter(page) " / " counter(pages);
   font:9pt -apple-system,sans-serif; color:#9ca3af }} }}
 *{{box-sizing:border-box}}
 body{{margin:0;font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
  color:#111827;background:#f4f5f7}}
 header{{background:{_BRAND};color:#fff;padding:20px 30px}}
 header h1{{margin:0 0 3px;font-size:21px;font-weight:650}}
 header p{{margin:0;opacity:.92;font-size:12.5px}}
 main{{max-width:1180px;margin:0 auto;padding:22px 30px 50px}}
 h2{{font-size:16px;margin:26px 0 4px;font-weight:650}}
 .lead{{color:#6b7280;margin:0 0 12px;font-size:12.5px}}
 .verdict{{background:#fff;border:1px solid #e5e7eb;border-radius:8px;
  padding:20px 24px;margin:16px 0 14px;display:flex;gap:24px;align-items:center;
  flex-wrap:wrap}}
 .vnum{{font-size:42px;font-weight:750;color:{_BRAND};line-height:1}}
 .vlab{{font-size:11px;color:#6b7280;text-transform:uppercase;letter-spacing:.05em;
  margin-top:5px;line-height:1.35}}
 .vtxt{{flex:1;min-width:300px;font-size:13.5px;color:#374151;margin:0}}
 .tiles{{display:flex;gap:10px;flex-wrap:wrap}}
 .tile{{background:#fff;border:1px solid #e5e7eb;border-radius:7px;padding:12px 14px;
  flex:1 1 0;min-width:150px}}
 .tl{{font-size:10.5px;color:#6b7280;text-transform:uppercase;letter-spacing:.045em}}
 .tv{{font-size:22px;font-weight:700;margin:4px 0 2px}}
 .ts{{font-size:11px;color:#6b7280;line-height:1.35}}
 .relia{{display:flex;gap:26px;align-items:center;background:#fff;
  border:1px solid #e5e7eb;border-radius:8px;padding:16px 22px;flex-wrap:wrap}}
 .donut{{position:relative;width:176px;height:176px;flex:0 0 176px}}
 .dctr{{position:absolute;top:60px;left:0;width:176px;text-align:center}}
 .dpct{{font-size:24px;font-weight:700;color:#111827;line-height:1.1}}
 .dlab{{font-size:10.5px;color:#6b7280}}
 .lg{{font-size:13px;margin:5px 0;color:#374151}}
 .dot{{display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:7px}}
 .lgp{{color:#9ca3af;font-size:11.5px;margin-left:6px}}
 .rtxt{{flex:1;min-width:260px;font-size:12.5px;color:#6b7280;margin:0}}
 .reserve{{background:#fffbeb;border:1px solid #fde68a;border-radius:7px;
  padding:11px 16px;margin:14px 0;font-size:12.5px;color:#78350f}}
 .reserve strong{{color:#92400e}}
 .reserve ul{{margin:5px 0 0;padding-left:17px}}
 .reserve li{{margin:2px 0}}
 .traj{{display:flex;gap:16px;align-items:flex-end;background:#fff;
  border:1px solid #e5e7eb;border-radius:8px;padding:18px 22px;min-height:150px}}
 .tb{{text-align:center;flex:1}}
 .tbv{{font-size:12px;font-weight:650;margin-bottom:5px}}
 .tbar{{border-radius:3px;margin:0 auto;width:38px}}
 .tbl{{font-size:11.5px;margin-top:6px;color:#374151}}
 .tbn{{font-size:10.5px;color:#9ca3af}}
 table{{border-collapse:collapse;width:100%;background:#fff;font-size:12.5px}}
 th,td{{padding:6px 9px;border-bottom:1px solid #eef0f2;text-align:left}}
 th{{background:#f3f4f6;font-size:10.5px;text-transform:uppercase;
  letter-spacing:.03em;color:#4b5563}}
 td.num,th.num{{text-align:right;white-space:nowrap}}
 .scroll{{overflow-x:auto;border:1px solid #e5e7eb;border-radius:7px}}
 /* Largeurs de colonnes : la somme doit tenir sous 100 %, sans quoi la
    dernière colonne (« Requête principale ») déborde du cadre du tableau au
    rendu WeasyPrint au lieu d'être contenue par table-layout:fixed. Colonnes
    posées via <colgroup>/<col> (obligatoire pour WeasyPrint, voir plus haut) :
    19 (article) + 8 (publié) + 12 (impr.) + 9,5 (Δ net) + 8 (clics) +
    11 (position) + 7 (KW +/-) + 11,5 (diagnostic) + 14 (requête) = 100 %.
    Le slug passe à la ligne au lieu d'être coupé en « energies-nuc... », et
    le diagnostic ne se casse plus au milieu d'un mot (« Nouveau / x »). */
 .sumt{{table-layout:fixed;width:100%}}
 .sumt col.c-art{{width:19%}} .sumt col.c-pub{{width:8%}}
 .sumt col.c-impr{{width:12%}} .sumt col.c-pct{{width:9.5%}}
 .sumt col.c-clk{{width:8%}} .sumt col.c-pos{{width:11%}}
 .sumt col.c-kw{{width:7%}} .sumt col.c-dg{{width:11.5%}} .sumt col.c-tq{{width:14%}}
 .sumt td:first-child,.sumt th:first-child{{white-space:normal;
  overflow-wrap:anywhere}}
 .sumt td.dg,.sumt td.q{{font-size:10.5px;color:#4b5563;white-space:normal;
  overflow-wrap:break-word;word-break:normal;hyphens:manual}}
 .sumt td,.sumt th{{padding:5px 6px;font-size:11.5px}}
 .sumt th{{font-size:9.5px}}
 .sumt td:first-child a{{border-bottom:none}}
 a{{color:#111827;text-decoration:none;border-bottom:1px solid #d1d5db}}
 .annex{{page-break-before:always;border-top:3px solid {_BRAND};margin-top:38px;
  padding-top:20px}}
 .detail,.rest{{page-break-before:always;margin-top:34px}}
 .diag{{display:inline-block;margin-left:8px;padding:1px 7px;font-size:9.5px;
  font-weight:600;border:1px solid;border-radius:10px;vertical-align:1px;
  text-transform:uppercase;letter-spacing:.03em}}
 .grad{{display:flex;gap:10px;flex-wrap:wrap;margin:10px 0 4px}}
 .grad>div{{flex:1 1 0;min-width:150px;background:#fff;border:1px solid #e5e7eb;
  border-radius:7px;padding:11px 13px}}
 .gl{{font-size:10.5px;color:#6b7280;text-transform:uppercase;letter-spacing:.04em}}
 .gv{{font-size:19px;font-weight:700;margin:3px 0 1px}}
 .gs{{font-size:11px;color:#6b7280;line-height:1.35}}
 .ctx{{background:#fff;border:1px solid #e5e7eb;border-radius:7px;padding:14px 16px;
  margin:12px 0}}
 .ctx p{{font-size:12.5px;color:#374151;margin:0 0 9px}}
 .ctx p:last-child{{margin-bottom:0}}
 /* Une fiche peut se couper entre deux pages (l'en-tête du tableau se
    répète), mais jamais entre son titre et ses chiffres ni au milieu d'une
    ligne : interdire toute coupure laissait un tiers de page blanc sous
    chaque paire de fiches et le document faisait 46 pages. */
 .card{{background:#fff;border:1px solid #e5e7eb;border-radius:7px;padding:9px 12px;
  margin:7px 0}}
 /* WeasyPrint n'honore pas toujours break-after:avoid : le titre restait
    seul en bas de page. Le haut de fiche (titre, chiffres, compte de
    requêtes) est un bloc insécable ; seuls la table et la lecture se coupent. */
 .ctop{{page-break-inside:avoid}}
 .reading{{orphans:2;widows:2}}
 .annex[hidden]{{display:none}}
 .chead a{{font-size:13.5px;font-weight:650;border-bottom:none}}
 .cmeta{{display:block;font-size:11px;color:#9ca3af;margin-top:2px}}
 .cstats{{display:flex;gap:0;flex-wrap:nowrap;margin:6px 0 2px;padding:5px 0;
  border-top:1px solid #f3f4f6;border-bottom:1px solid #f3f4f6}}
 /* Quatre blocs sur une seule ligne, aux largeurs de leur contenu le plus
    long (« 1 133 → 2 761 +638,2 % », « 248 attendues → 2 761 obtenues ») :
    en flex égal, « +638,2 % » passait à la ligne ou chevauchait le bloc
    voisin, et « attendues → obtenues » sortait de la fiche. */
 .cstats>div{{flex:0 0 auto;white-space:nowrap;padding-right:6px}}
 .cstats>div:nth-child(1){{width:30%}} .cstats>div:nth-child(2){{width:24%}}
 .cstats>div:nth-child(3){{width:16%}} .cstats>div:nth-child(4){{width:30%}}
 .qcap{{font-size:9.5px;text-transform:uppercase;letter-spacing:.04em;
  font-weight:600;color:#6b7280;margin-bottom:3px}}
 .sl{{display:block;font-size:10px;color:#9ca3af;text-transform:uppercase;
  letter-spacing:.04em}}
 .sv{{font-size:12px;font-weight:600;margin-right:5px}}
 .qsum{{font-size:11px;color:#6b7280;margin:6px 0 4px;display:flex;gap:14px;
  flex-wrap:wrap}}
 .qsum .up{{color:{_POS}}} .qsum .dn{{color:{_NEG}}}
 /* Aucune cellule du rapport n'est tronquée : le PDF est le document envoyé,
    une requête coupée en « vitesse de l... » ou un slug en « energies-nuc... »
    ne se lit pas. Les colonnes larges renvoient à la ligne, les colonnes de
    chiffres ont la place de leur contenu le plus long. */
 .q{{white-space:normal;overflow-wrap:anywhere}}
 .qt5{{font-size:11px;table-layout:fixed;width:100%;margin-top:4px}}
 .qt5 th{{font-size:9px;white-space:normal}}
 .qt5 td{{padding:2px 6px;vertical-align:top}}
 .qt5 col.c-q{{width:42%}} .qt5 col.c-k{{width:12%}} .qt5 col.c-i{{width:17%}}
 .qt5 col.c-c{{width:11%}} .qt5 col.c-p{{width:18%}}
 .k{{display:inline-block;padding:0 6px;border-radius:9px;font-size:8.5px;
  font-weight:600;text-transform:uppercase;letter-spacing:.03em;border:1px solid;
  vertical-align:1px}}
 .k-g{{color:{_POS};border-color:{_POS}}} .k-m{{color:#6b7280;border-color:#d1d5db}}
 .k-p{{color:{_NEG};border-color:{_NEG}}}
 .reading{{font-size:11px;color:#374151;margin:5px 0 0;line-height:1.42}}
 tr{{page-break-inside:avoid}} thead{{display:table-header-group}}
 .empty{{color:#9ca3af;font-style:italic}}
 footer{{margin-top:24px;font-size:11px;color:#9ca3af}}
 .method{{margin-top:26px;background:#fff;border:1px solid #e5e7eb;border-radius:7px;
  padding:0 16px}}
 .method summary{{cursor:pointer;padding:12px 0;font-size:12.5px;font-weight:600;
  color:#4b5563}}
 .method p{{font-size:12px;color:#4b5563;margin:0 0 10px}}
 code{{background:#f3f4f6;padding:1px 4px;border-radius:3px;font-size:11px}}
 @media print{{
  body{{background:#fff}} main{{padding:0;max-width:none}}
  header{{padding:0 0 12px}} .tile,.verdict,.relia,.traj{{break-inside:avoid}}
  .method[open] summary~*{{display:block}}
 }}
</style></head><body>
<header>
 <h1>Impact des refreshs {_de(month_label)}</h1>
 <p>{r["site"]}{f' · onglet {r["scope_tab"]}' if r.get("scope_tab") else ''} ·
 {n_art} articles refreshés · chaque article comparé à lui-même un an plus tôt,
 à date fixe · Google Search Console</p>
</header>
<main>

 <div class="verdict">
  <div><div class="vnum">{_signed_pct(var_i)}</div>
  <div class="vlab">impressions<br>contre l'an dernier</div></div>
  <p class="vtxt">Les {n_art} articles refreshés {_de(month_label)} ont produit
  <strong>{_fr_num(o["impressions_after"])} impressions</strong> et
  <strong>{_fr_num(o["clicks_after"])} clics</strong>. Un an plus tôt, ces mêmes
  articles faisaient <strong>{_fr_num(o["impressions_before"])} impressions</strong>
  et <strong>{_fr_num(o["clicks_before"])} clics</strong> sur les mêmes dates,
  soit {_signed_pct(var_i)} d'impressions et {_signed_pct(var_c)} de clics.
  Le CTR passe de {_fr_dec(o["ctr_before"])} % à {_fr_dec(o["ctr_after"])} %.</p>
 </div>

 {low_volume_block}
 <div class="tiles">{tiles}</div>

 <h2>Fiabilité du résultat</h2>
 <p class="lead">Répartition des {n_art} articles. Un résultat porté par une
 majorité d'articles ne tient pas à quelques cas isolés.</p>
 <div class="relia">
  {donut}
  <div>{legend}</div>
  <p class="rtxt">Seuil de ±5 % : en deçà, la variation n'est pas distinguable du
  bruit de mesure GSC et l'article est compté comme stable plutôt que comme une
  victoire.</p>
 </div>
{grad_block}
{traj_block}
 {reserve_block}

 <h2>Situer ce résultat</h2>
 <div class="ctx">
  <p><strong>Pourquoi ce chiffre diffère d'un suivi d'onglet.</strong> Ce rapport
  compare chaque article à lui-même un an plus tôt, à date fixe : les N jours qui
  suivent sa republication contre les N jours qui suivent la même date l'an
  dernier. Un suivi de périmètre (<code>/tab-perf</code>) compare lui aussi une
  période à son année précédente, mais sur un mois calendaire et sur tout un
  onglet (articles retravaillés ou non), sans ancrer la comparaison sur la date
  de republication de chacun. Les deux lectures sont désormais l'une et l'autre
  année-sur-année : ce qui les distingue n'est plus le principe de la comparaison
  mais son ancrage et son périmètre — cet article précis, à sa date à lui, contre
  un onglet entier, au mois calendaire.</p>
  <p><strong>Les deux peuvent être justes en même temps</strong>, et diverger :
  un article republié en fin de mois pèse peu dans une lecture calendaire alors
  qu'il porte tout son poids ici, et l'onglet mélange des articles retravaillés
  avec d'autres qui ne le sont pas. Quand les deux lectures circulent, dire
  laquelle on cite.</p>
 </div>

 <details class="method"><summary>Méthode de mesure et sources</summary>
  <p><strong>Fenêtre.</strong> Chaque article est comparé à lui-même, un an plus
  tôt : les N jours suivant sa republication contre les N jours suivant la même
  date un an auparavant, à durée strictement égale. Comparer les mêmes dates
  calendaires à un an d'écart élimine la saisonnalité par construction plutôt que
  de la déduire après coup. N vaut au plus {r["maturity_target"]} jours, plafonné
  par le recul disponible côté « après » (le recul côté « avant » ne limite plus
  N : GSC conserve assez d'historique pour couvrir J-365-N dans la quasi-totalité
  des cas).</p>
  <p><strong>Groupe de contrôle.</strong> Le reste du site (total GSC moins les
  articles traités), comparé lui aussi à J-365 sur exactement les mêmes dates que
  la vague mesurée. La saisonnalité étant déjà éliminée par la fenêtre
  année-sur-année, ce contrôle capte surtout une dérive de marché résiduelle (le
  reste du site progresse ou régresse structurellement d'une année sur l'autre)
  plutôt qu'un effet de saison. L'attendu est un contrefactuel pondéré : pour
  chaque vague, ce que ses articles auraient fait au rythme du site, puis la
  somme.{
   f' Le contrôle écarte {c["excluded_urls"]} URLs : les {c["measured_urls"]} '
   f'mesurées ici, et les autres articles refreshés le même mois hors de cet '
   f'onglet. Leur progression n\'est pas de la saisonnalité : les laisser dans '
   f'la référence sous-estimerait l\'écart net.'
   if c.get("excluded_urls", 0) > c.get("measured_urls", 0) else ''
  }</p>
  <p><strong>Périmètre et dates.</strong> {
   f'Colonne « {NOTION_REFRESH_COL} » de la base Notion de suivi : la date est '
   f'saisie par la personne qui a fait le refresh, et le périmètre est '
   f'exactement ce que la base déclare en ligne. Le <code>lastmod</code> du '
   f'sitemap complète les republications qui n\'y ont pas été saisies, sans '
   f'jamais faire entrer une page que la base ne suit pas.'
   if r.get("source_mode") == "notion" else
   f'Colonne « Date de refresh » de l\'onglet {r["scope_tab"]} : la date est '
   f'saisie par la personne qui a fait le refresh, et le périmètre est '
   f'exactement ce que l\'onglet déclare. Aucune date déduite de WordPress '
   f'n\'entre dans ce rapport.'
   if r.get("scope_tab") else
   f'Trace locale <code>outputs/{r["site"]}/wp_backups/</code>, écrite par '
   f'<code>push_to_wp</code> : seule source qui date un acte de refresh. Le '
   f'champ <code>modified</code> de WordPress date la dernière modification '
   f'quelconque et ne sert que de contrôle de cohérence.'
  }</p>
  <p><strong>Distinction avec /tab-perf.</strong> Ce rapport mesure, article par
  article, un an-sur-un-an ancré sur la date de republication de CHAQUE article,
  sur le lot effectivement retravaillé ; <code>/tab-perf</code> mesure un
  an-sur-un-an calendaire par mois, sur tout un périmètre (onglet ou base
  Notion). Les deux peuvent diverger sans qu'aucun soit faux.</p>
 </details>

 <div class="detail">
  <h2>Ont grimpé — les {len(winners)} plus fortes progressions</h2>
  <p class="lead">Écart net, saisonnalité déduite. Pour chaque article, les
  {n_q} requêtes qui pèsent le plus, avant ou après refresh, avec leur statut :
  <strong>gagnée</strong> (absente l'an dernier), <strong>maintenue</strong>
  (présente les deux années, avec le mouvement de classement),
  <strong>perdue</strong> (disparue). Puis deux à quatre phrases qui disent d'où
  vient le mouvement. GSC ne rattache pas toutes les impressions d'une page à
  une requête (les requêtes rares sont anonymisées) : quand la part attribuable
  à des requêtes identifiables tombe sous la moitié du volume de la page, la
  lecture le dit et ne commente que « la part visible ».</p>
  {win_cards}

  <h2>N'ont pas fonctionné — les {len(losers)} plus fortes baisses</h2>
  <p class="lead">Triés par écart net croissant : la comparaison est déjà
  année-sur-année à date fixe, donc ces baisses s'imputent au contenu ou à un
  mouvement de marché plutôt qu'à un manque de recul.</p>
  {lose_cards}
 </div>

 <div class="rest">
  <h2>Le reste du lot — {len(rest)} articles</h2>
  <p class="lead">Ni dans les plus fortes progressions ni dans les plus fortes
  baisses, du plus fort gain d'impressions au plus fort recul. Même fiche que
  ci-dessus : les {n_q} requêtes qui pèsent le plus sur chaque article, et leur
  lecture.</p>
  {rest_cards}
  {rest_notable_block}
 </div>

 {annex_open}
  <h2>Annexe — les {n_art} articles</h2>
  <p class="lead">Le lot complet en une ligne par article, trié par gain
  d'impressions. « KW +/− » compte les requêtes présentes d'un seul côté du
  refresh.</p>
  <div class="scroll"><table class="sumt"><colgroup><col class="c-art"><col class="c-pub"><col class="c-impr"><col class="c-pct"><col class="c-clk"><col class="c-pos"><col class="c-kw"><col class="c-dg"><col class="c-tq"></colgroup><thead><tr><th>Article</th><th class="num">Publié</th>
  <th class="num">Impressions</th><th class="num">Δ net</th>
  <th class="num">Clics</th><th class="num">Position</th>
  <th class="num">KW +/−</th><th>Diagnostic</th><th>Requête principale</th></tr></thead>
  <tbody>{all_rows}</tbody></table></div>
 {annex_close}

 <footer>Rapport généré par <code>audit impact</code> ·
 dates de republication : wp_backups · le JSON associé permet le drill-down complet.</footer>
</main></body></html>"""


def _dump_pdf_impact(site: str, stem: str, payload: dict, annex: bool = False) -> str:
    """Rend le rapport en PDF A4 via WeasyPrint.

    Par défaut **sans le tableau exhaustif** : le document envoyé porte déjà le
    verdict et les articles sur lesquels on agit (~25 pages), et le lot complet
    n'ouvre sur aucune décision de plus. Le HTML, lui, garde tout — c'est
    l'outil de travail.

    WeasyPrint est une dépendance optionnelle (elle tire Pango/Cairo) : son
    absence ne doit pas faire échouer la commande, qui a déjà écrit le HTML et
    le JSON à ce stade.
    """
    try:
        from weasyprint import HTML as _WeasyHTML
    except ImportError:
        return ""

    from _shared.core.site_paths import SitePaths
    out_dir = SitePaths(base_path=REPO_ROOT).output_dir(site) / "audit"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{stem}.pdf"
    _WeasyHTML(string=_render_impact(payload, annex=annex)).write_pdf(str(out_path))
    return str(out_path)


def render_from_json(site: str, month: Optional[str] = None,
                     start: Optional[str] = None, pdf: bool = False,
                     annex: bool = False) -> dict:
    """Re-rend HTML (et PDF) depuis le JSON déjà écrit, sans aucun appel GSC.

    Pour itérer sur la mise en forme : la collecte a coûté ses appels, le
    rendu n'a besoin que du payload. Lève FileNotFoundError si le mois n'a
    jamais été calculé.
    """
    from _shared.core.site_paths import SitePaths
    stem = f"impact_refresh_{month or start}_{site}".replace(".", "-")
    path = SitePaths(base_path=REPO_ROOT).output_dir(site) / "audit" / f"{stem}.json"
    if not path.is_file():
        raise FileNotFoundError(f"no report to re-render: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    out = {"json_path": str(path),
           "html_path": _dump_html_impact(site, stem, payload)}
    if pdf:
        out["pdf_path"] = _dump_pdf_impact(site, stem, payload, annex=annex)
    return out


def _dump_html_impact(site: str, stem: str, payload: dict) -> str:
    from _shared.core.site_paths import SitePaths
    out_dir = SitePaths(base_path=REPO_ROOT).output_dir(site) / "audit"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{stem}.html"
    out_path.write_text(_render_impact(payload), encoding="utf-8")
    return str(out_path)
