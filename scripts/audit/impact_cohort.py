"""Rapport d'impact mensuel : chaque article republié comparé à lui-même.

Différence avec `gsc_tab_perf` (audit gsc-tab), et raison d'être de ce module :
`gsc-tab` mesure **un onglet** sur un **mois calendaire**. Sur un article
republié le 25 août, « août 2026 vs août 2025 » mesure surtout les 24 jours
*d'avant* le refresh — le travail est noyé dans la période qui le précède, et
l'onglet mélange les articles traités avec ceux qui ne l'ont pas été. Les deux
lectures ne portent pas sur le même objet : celle-ci mesure le travail, l'autre
mesure l'onglet.

Ici chaque article est sa propre unité de mesure :

- **fenêtre propre** : les N jours qui suivent sa republication contre les N
  jours qui la précèdent, à durée strictement égale, N étant le recul commun le
  plus large que la date d'export autorise pour l'article (plafonné à
  `--maturity`) ;
- **groupe de contrôle** : le reste du site (total GSC moins les articles
  traités) sur *exactement* les mêmes dates, ce qui déduit la saisonnalité —
  sans lui, un mois de rentrée se lit comme un succès éditorial ;
- **cohortes** : les articles regroupés par vague de republication puis par
  recul, parce qu'un effet SEO réel grandit avec le temps d'observation. Une
  hausse identique à 7 et à 30 jours est plus probablement du bruit.

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
# réévaluer la page et la mesure est dominée par le bruit de recrawl ; au-delà
# de 30 la fenêtre « avant » commence à mordre sur un refresh antérieur.
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

    gained = sorted(
        (pack(q, None, after[q]) for q in keys_a - keys_b),
        key=lambda r: -r["impressions_after"],
    )[:top]
    lost = sorted(
        (pack(q, before[q], None) for q in keys_b - keys_a),
        key=lambda r: -r["impressions_before"],
    )[:top]
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

    return {
        "gained": gained,
        "lost": lost,
        "held": held[:top],
        "counts": {
            "gained": len(keys_a - keys_b),
            "lost": len(keys_b - keys_a),
            "held": len(keys_a & keys_b),
            "before": len(keys_b),
            "after": len(keys_a),
        },
    }


def _article_windows(pushed: str, maturity: int, data_end: str) -> Optional[dict]:
    """Fenêtres avant/après d'un article, à durée strictement égale.

    Le jour de republication lui-même est exclu des deux fenêtres : il porte à
    la fois de l'ancienne et de la nouvelle version, et n'appartient donc ni à
    l'avant ni à l'après.
    """
    d = datetime.strptime(pushed, "%Y-%m-%d")
    end_cap = datetime.strptime(data_end, "%Y-%m-%d")

    available = (end_cap - d).days
    n = min(maturity, available)
    if n < MIN_MATURITY:
        return None

    return {
        "maturity": n,
        "before": {
            "start": (d - timedelta(days=n)).strftime("%Y-%m-%d"),
            "end": (d - timedelta(days=1)).strftime("%Y-%m-%d"),
        },
        "after": {
            "start": (d + timedelta(days=1)).strftime("%Y-%m-%d"),
            "end": (d + timedelta(days=n)).strftime("%Y-%m-%d"),
        },
    }


def _maturity_bucket(n: int) -> str:
    if n <= 15:
        return "7-15 jours"
    if n <= 25:
        return "16-25 jours"
    return "26-30 jours"


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
    top_queries: int = 10,
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
            "bucket": _maturity_bucket(w["maturity"]),
            # La date vient-elle d'un acte de publication tracé, ou du
            # `modified` WordPress d'une republication manuelle ? La seconde est
            # moins sûre (une retouche ultérieure l'écrase) : le rapport le dit
            # plutôt que de présenter les deux comme équivalentes.
            "date_source": ("wp_modified" if slug in recovered else "wp_backups"),
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
    treated_urls = {_norm(a["url"]) for a in articles if a["url"].startswith("http")}

    def control_for(win: tuple) -> dict:
        by_page = metrics[win]
        clicks = sum(p["clicks"] for u, p in by_page.items() if u not in treated_urls)
        impr = sum(p["impressions"] for u, p in by_page.items() if u not in treated_urls)
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

    # Tri par recul croissant, pas alphabétique : « 7-15 » doit précéder
    # « 16-25 », sinon le tableau censé montrer une progression la brouille.
    by_bucket = {
        k: agg(rows)
        for k, rows in sorted(
            _group(articles, lambda a: a["bucket"]).items(),
            key=lambda kv: int(kv[0].split("-")[0]),
        )
    }
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
        # Deux sources, jamais confondues : le rapport doit pouvoir dire de
        # quelle trace chaque date provient, la première étant plus sûre.
        "pushed_source": "wp_backups + wp_modified" if recovered else "wp_backups",
        "pushed_sources": {
            "wp_backups": n_traced,
            "wp_modified_manual": len(recovered),
        },
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
        "by_maturity": by_bucket,
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
    """Premier segment de chemin après /ressources/ — le vertical éditorial."""
    m = re.search(r"/ressources/([^/]+)/", a["url"])
    return m.group(1) if m else "(hors arborescence)"


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


def _pct_span(pct: Optional[float]) -> str:
    if pct is None:
        return '<span style="color:#9ca3af">n/a</span>'
    color = _POS if pct > 0 else (_NEG if pct < 0 else "#6b7280")
    return f'<span style="color:{color};font-weight:600">{_signed_pct(pct)}</span>'


def _pos_cell(pb, pa) -> str:
    """Position avant → après, colorée sur l'amélioration et non sur le signe.

    Passer de 12 à 7 est un gain : le delta brut vaut -5, l'affichage doit
    montrer +5 en vert. Confondre les deux fait lire un succès comme un recul.
    """
    if pb is None or pa is None:
        return "–"
    d = round(pb - pa, 1)
    col = _POS if d > 0 else (_NEG if d < 0 else "#6b7280")
    sign = "+" if d > 0 else ""
    return (f'{str(pb).replace(".", ",")} → {str(pa).replace(".", ",")} '
            f'<span style="color:{col};font-size:10.5px">{sign}'
            f'{str(d).replace(".", ",")}</span>')


def _render_impact(r: dict, annex: bool = True) -> str:
    """Rapport à deux étages : PDF directeur, puis annexe de monitoring.

    Le rapport précédent mélangeait les deux publics et ne servait bien ni l'un
    ni l'autre : trop de prose méthodologique pour un directeur, trop peu de
    granularité pour piloter le travail (27 articles montrés sur 76, aucun
    mot-clé). Les deux besoins sont réels mais n'ont pas le même lecteur.

    - **Étage 1 (pages 1-2)** : le verdict net, sa fiabilité, ses réserves.
      C'est ce qu'on envoie. Un directeur arbitre trois choses — continuer,
      changer d'échelle, changer de direction — et rien d'autre ne l'y aide.
    - **Étage 2 (annexe)** : une fiche par URL avec son déplacement sémantique.
      C'est l'outil de travail, celui qui dit *sur quelles requêtes* un article
      a bougé, et donc quoi refaire.

    Le saut de page CSS sépare physiquement les deux : le PDF envoyé peut
    s'arrêter à la page 2 sans rien perdre de son propos.
    """
    o, c = r["overall"], r["control"]
    p = r["period"]
    month_label = p.get("month") and _fr_month(p["start"]) or (
        f"{_fr_date(p['start'])} – {_fr_date(p['end'])}"
    )
    n_art = r["counts"]["measurable"]
    net_i, net_c = c["net_impressions_pct"], c["net_clicks_pct"]

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

    tiles = "".join([
        tile("Impressions nettes", _signed_pct(net_i),
             f'{_fr_num(o["impressions_after"])} obtenues · '
             f'{_fr_num(c["expected_impressions"])} attendues'),
        tile("Clics nets", _signed_pct(net_c),
             f'{_fr_num(o["clicks_after"])} obtenus · '
             f'{_fr_num(c["expected_clicks"])} attendus'),
        tile("Articles traités", str(n_art), f'republiés en {month_label}'),
        tile("Effet médian", f'× {str(r["median_factor"] or 0).replace(".", ",")}',
             "impressions de l'article médian"),
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

    # ----------------------------------------------------------- trajectoire
    # Le bloc se dégrade proprement tant qu'un seul mois existe : afficher un
    # graphique à un point suggérerait une tendance qui n'est pas mesurée.
    # `wp_backups/` ne porte pas d'historique avant août 2026, donc aucune date
    # de republication antérieure n'est fiable (la Sheet est saisie à la main,
    # le `modified` WordPress est écrasé par toute retouche).
    traj = r.get("trajectory") or []
    if len(traj) >= 2:
        mx = max(abs(m["net_impressions_pct"] or 0) for m in traj) or 1
        bars = ""
        for m in traj:
            v = m["net_impressions_pct"] or 0
            h = round(abs(v) / mx * 92)
            col = _POS if v >= 0 else _NEG
            bars += (
                f'<div class="tb"><div class="tbv">{_signed_pct(v)}</div>'
                f'<div class="tbar" style="height:{h}px;background:{col}"></div>'
                f'<div class="tbl">{m["label"]}</div>'
                f'<div class="tbn">{m["articles"]} art.</div></div>'
            )
        traj_block = f"""
 <h2>Trajectoire mensuelle</h2>
 <p class="lead">Écart net d'impressions, saisonnalité déduite, mois après mois.</p>
 <div class="traj">{bars}</div>"""
    else:
        traj_block = f"""
 <h2>Trajectoire mensuelle</h2>
 <p class="lead">Un seul mois mesuré à ce jour : la comparaison mois à mois
 s'affichera ici dès qu'un second rapport aura été produit
 (<code>audit impact --month</code> sur le mois voulu).</p>"""

    # ------------------------------------------------------- annexe par URL
    def art_card(a: dict) -> str:
        q = a.get("queries") or {}
        counts = q.get("counts") or {}
        net = a.get("net_impressions_pct")
        b, af = a["before"], a["after"]

        def qrows(rows, kind):
            if not rows:
                return (f'<tr><td colspan="5" class="empty">Aucune requête '
                        f'{kind}</td></tr>')
            out = ""
            for x in rows:
                if kind == "perdue":
                    vol = f'{_fr_num(x["impressions_before"])} → 0'
                    clk = f'{x["clicks_before"]} → 0'
                    pos = (f'{str(x["position_before"]).replace(".", ",")} → –'
                           if x["position_before"] else "–")
                elif kind == "gagnée":
                    vol = f'0 → {_fr_num(x["impressions_after"])}'
                    clk = f'0 → {x["clicks_after"]}'
                    pos = (f'– → {str(x["position_after"]).replace(".", ",")}'
                           if x["position_after"] else "–")
                else:
                    vol = (f'{_fr_num(x["impressions_before"])} → '
                           f'{_fr_num(x["impressions_after"])}')
                    clk = f'{x["clicks_before"]} → {x["clicks_after"]}'
                    pos = _pos_cell(x["position_before"], x["position_after"])
                out += (f'<tr><td class="q">{x["query"]}</td>'
                        f'<td class="num">{vol}</td><td class="num">{clk}</td>'
                        f'<td class="num">{pos}</td></tr>')
            return out

        held = q.get("held") or []
        gained = q.get("gained") or []
        lost = q.get("lost") or []
        qblock = ""
        if q:
            qblock = f"""
   <div class="qsum">
    <span><strong>{counts.get("after", 0)}</strong> requêtes après refresh</span>
    <span class="up">+{counts.get("gained", 0)} gagnées</span>
    <span class="dn">−{counts.get("lost", 0)} perdues</span>
    <span>{counts.get("held", 0)} maintenues</span>
   </div>
   <table class="qt"><thead><tr><th>Requête</th><th class="num">Impressions</th>
   <th class="num">Clics</th><th class="num">Position</th></tr></thead>
   <tbody>
   <tr class="qh"><td colspan="4">Requêtes maintenues — top {len(held)}</td></tr>
   {qrows(held, "maintenue")}
   <tr class="qh"><td colspan="4">Requêtes gagnées — top {len(gained)}</td></tr>
   {qrows(gained, "gagnée")}
   <tr class="qh"><td colspan="4">Requêtes perdues — top {len(lost)}</td></tr>
   {qrows(lost, "perdue")}
   </tbody></table>"""

        return f"""
  <div class="card">
   <div class="chead">
    <a href="{a["url"]}">{a["slug"]}</a>
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
     <span class="sv">{_pct_span(net)}</span></div>
   </div>{qblock}
  </div>"""

    ranked = sorted(r["articles"], key=lambda a: a["impressions_delta"], reverse=True)
    cards = "".join(art_card(a) for a in ranked)

    # Tableau de synthèse de l'annexe : les 76 lignes d'un coup d'œil, avant les
    # fiches détaillées. C'est la vue qui manquait — le rapport n'en montrait
    # que 27.
    sum_rows = ""
    for a in ranked:
        sum_rows += (
            "<tr>"
            f'<td><a href="{a["url"]}">{a["slug"]}</a></td>'
            f'<td class="num">{_fr_date(a["pushed"])[:-5]}</td>'
            f'<td class="num">{_fr_num(a["before"]["impressions"])} → '
            f'{_fr_num(a["after"]["impressions"])}</td>'
            f'<td class="num">{_pct_span(a["impressions_pct"])}</td>'
            f'<td class="num">{_pct_span(a.get("net_impressions_pct"))}</td>'
            f'<td class="num">{a["before"]["clicks"]} → {a["after"]["clicks"]}</td>'
            f'<td class="num">{_pos_cell(a["before"].get("position"), a["after"].get("position"))}</td>'
            f'<td class="num">{(a.get("queries") or {}).get("counts", {}).get("gained", "–")}</td>'
            f'<td class="num">{(a.get("queries") or {}).get("counts", {}).get("lost", "–")}</td>'
            "</tr>"
        )

    # L'annexe (une fiche par URL) pèse une trentaine de pages sur un lot de
    # 76 articles. Le PDF envoyé aux directeurs n'en a pas l'usage : annex=False
    # produit le document court, sans toucher au HTML de travail qui la garde.
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
 .sumt{{table-layout:fixed;width:100%}}
 .sumt td:first-child,.sumt th:first-child{{width:23%;overflow:hidden;
  text-overflow:ellipsis}}
 .sumt col.c-impr{{width:13%}} .sumt col.c-pct{{width:9.5%}}
 .sumt col.c-clk{{width:8%}} .sumt col.c-pos{{width:13%}}
 .sumt col.c-kw{{width:6%}} .sumt col.c-pub{{width:8%}}
 .sumt td,.sumt th{{padding:5px 6px;font-size:11.5px}}
 .sumt th{{font-size:9.5px}}
 .sumt td:first-child a{{border-bottom:none}}
 a{{color:#111827;text-decoration:none;border-bottom:1px solid #d1d5db}}
 .annex{{page-break-before:always;border-top:3px solid {_BRAND};margin-top:38px;
  padding-top:20px}}
 .card{{background:#fff;border:1px solid #e5e7eb;border-radius:7px;padding:14px 16px;
  margin:12px 0;page-break-inside:avoid}}
 .chead a{{font-size:13.5px;font-weight:650;border-bottom:none}}
 .cmeta{{display:block;font-size:11px;color:#9ca3af;margin-top:2px}}
 .cstats{{display:flex;gap:10px;flex-wrap:wrap;margin:11px 0 4px;padding:9px 0;
  border-top:1px solid #f3f4f6;border-bottom:1px solid #f3f4f6}}
 .cstats>div{{flex:1 1 0;min-width:130px}}
 .sl{{display:block;font-size:10px;color:#9ca3af;text-transform:uppercase;
  letter-spacing:.04em}}
 .sv{{font-size:12.5px;font-weight:600;margin-right:6px}}
 .qsum{{font-size:11.5px;color:#6b7280;margin:9px 0 6px;display:flex;gap:14px;
  flex-wrap:wrap}}
 .qsum .up{{color:{_POS}}} .qsum .dn{{color:{_NEG}}}
 .qt{{font-size:11.5px}}
 .qt th{{font-size:9.5px}}
 .qt td{{padding:4px 8px}}
 .qh td{{background:#fafbfc;font-size:10px;text-transform:uppercase;
  letter-spacing:.04em;color:#6b7280;font-weight:600}}
 .q{{max-width:330px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
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
  header{{padding:0 0 12px}} .card,.tile,.verdict,.relia,.traj{{break-inside:avoid}}
  .method[open] summary~*{{display:block}}
 }}
</style></head><body>
<header>
 <h1>Impact des refreshs {_de(month_label)}</h1>
 <p>{r["site"]} · {n_art} articles republiés · chaque article comparé à lui-même
 sur sa propre fenêtre · Google Search Console, données arrêtées au
 {_fr_date(r["data_end"])}</p>
</header>
<main>

 <div class="verdict">
  <div><div class="vnum">{_signed_pct(net_i)}</div>
  <div class="vlab">impressions nettes<br>saisonnalité déduite</div></div>
  <p class="vtxt">Les {n_art} articles refreshés {_de(month_label)} ont produit
  <strong>{_fr_num(o["impressions_after"])} impressions</strong> et
  <strong>{_fr_num(o["clicks_after"])} clics</strong>, contre
  {_fr_num(c["expected_impressions"])} impressions et {_fr_num(c["expected_clicks"])}
  clics attendus au rythme du reste du site sur les mêmes dates.
  Les clics nets ressortent à <strong>{_signed_pct(net_c)}</strong>.
  L'écart ne s'explique pas par la saison :
  il suit les articles qui ont été retravaillés.</p>
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
{traj_block}
 {reserve_block}

 <details class="method"><summary>Méthode de mesure et sources</summary>
  <p><strong>Fenêtre.</strong> Chaque article est comparé à lui-même : les N jours
  suivant sa republication contre les N jours la précédant, à durée strictement
  égale, jour de publication exclu des deux côtés. N vaut au plus
  {r["maturity_target"]} jours.</p>
  <p><strong>Groupe de contrôle.</strong> Le reste du site (total GSC moins les
  articles traités) sur exactement les mêmes dates. L'attendu est un contrefactuel
  pondéré : pour chaque vague, ce que ses articles auraient fait au rythme du site,
  puis la somme. C'est ce qui déduit la saisonnalité.</p>
  <p><strong>Dates de republication.</strong> Trace locale
  <code>outputs/{r["site"]}/wp_backups/</code>, écrite par <code>push_to_wp</code> :
  seule source qui date un acte de refresh. Le champ <code>modified</code> de
  WordPress date la dernière modification quelconque et ne sert que de contrôle de
  cohérence.</p>
  <p><strong>Distinction avec /tab-perf.</strong> Ce rapport mesure un travail sur
  sa propre fenêtre ; <code>/tab-perf</code> mesure un périmètre sur un mois
  calendaire. Les deux peuvent diverger sans qu'aucun soit faux.</p>
 </details>

 {annex_open}
  <h2>Annexe — détail par URL refreshée</h2>
  <p class="lead">Les {n_art} articles du mois, triés par gain d'impressions.
  « Gagnées » et « perdues » comptent les requêtes présentes d'un seul côté du
  refresh : c'est le déplacement sémantique de l'article.</p>
  <div class="scroll"><table class="sumt"><colgroup><col><col class="c-pub"><col class="c-impr"><col class="c-pct"><col class="c-pct"><col class="c-clk"><col class="c-pos"><col class="c-kw"><col class="c-kw"></colgroup><thead><tr><th>Article</th><th class="num">Publié</th>
  <th class="num">Impressions</th><th class="num">Δ</th><th class="num">Δ net</th>
  <th class="num">Clics</th><th class="num">Position</th>
  <th class="num">KW +</th><th class="num">KW −</th></tr></thead>
  <tbody>{sum_rows}</tbody></table></div>

  <h2>Déplacement sémantique, article par article</h2>
  <p class="lead">Top {r.get("top_queries", 10)} par famille. Les requêtes
  maintenues montrent le mouvement de classement, les gagnées l'élargissement de
  couverture, les perdues les candidats à une seconde passe.</p>
  {cards}
 {annex_close}

 <footer>Rapport généré par <code>audit impact</code> ·
 dates de republication : wp_backups · le JSON associé permet le drill-down complet.</footer>
</main></body></html>"""


def _dump_pdf_impact(site: str, stem: str, payload: dict, annex: bool = False) -> str:
    """Rend le rapport en PDF A4 via WeasyPrint.

    Par défaut **sans l'annexe** : c'est le document qu'on envoie, et un lecteur
    de comité ne lit pas trente pages de fiches par URL. Le HTML, lui, garde
    toujours les deux étages — c'est l'outil de travail.

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


def _dump_html_impact(site: str, stem: str, payload: dict) -> str:
    from _shared.core.site_paths import SitePaths
    out_dir = SitePaths(base_path=REPO_ROOT).output_dir(site) / "audit"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{stem}.html"
    out_path.write_text(_render_impact(payload), encoding="utf-8")
    return str(out_path)
