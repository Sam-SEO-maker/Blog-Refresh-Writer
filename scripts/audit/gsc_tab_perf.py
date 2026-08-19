"""Monitoring GSC d'un onglet Sheet : pertes et progressions liées aux refreshs.

Compare deux fenêtres GSC de même durée (courante vs précédente) pour toutes
les URLs d'un onglet déclaré (bloc `sheets.tabs` du site.json, config-driven
comme tab_status.py), et croise avec le statut éditorial de la Sheet
(« Publié » = refresh en ligne). Sort les deltas par URL (progressions /
régressions) et les agrégats par statut — c'est la vue de suivi d'impact des
refreshs, pas un snapshot de perfs brutes.

Deux requêtes GSC service account (dimension `page`, une par fenêtre), pas un
appel par URL — un onglet peut porter des centaines de lignes. Le SA a accès à
toutes les propriétés superprof.* comme aux clients.

Usage :
    python content_writer.py audit gsc-tab --site superprof.fr-ressources \
        --tab "New Growing List" --days 28
    python content_writer.py audit gsc-tab --site superprof.fr-ressources \
        --tab "New Growing List" --start 2026-06-01 --end 2026-07-27
"""

import json
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from scripts.audit.ahrefs_state import REPO_ROOT
from scripts.audit.gsc_analyzer import GSCAnalyzer
from scripts.audit.gsc_state import _site_gsc_property
from _shared.core.sheets_config import get_sheets_config


def _norm(url: str) -> str:
    """Normalise une URL pour la jointure Sheet ↔ GSC (slash final, casse)."""
    return url.strip().rstrip("/").lower()


def _read_tab_rows(site: str, tab: str) -> list[dict]:
    """Lit l'onglet et retourne [{row, url, keyword, status}] (lignes à URL http)."""
    cfg = get_sheets_config(site)
    spreadsheet_id = cfg.get("spreadsheet_id")
    if not spreadsheet_id:
        raise ValueError(f"Pas de sheets.spreadsheet_id dans la config de {site}")
    tabs = cfg.get("tabs") or []
    tab_cfg = next((t for t in tabs if t.get("name") == tab), None)
    if tab_cfg is None:
        declared = ", ".join(t.get("name", "?") for t in tabs) or "(aucun)"
        raise ValueError(f"Onglet '{tab}' non déclaré pour {site}. Déclarés : {declared}")

    from scripts.sheets import SheetsClient
    values = SheetsClient(spreadsheet_id)._read_sheet(tab)

    col_url = tab_cfg.get("col_url", 0)
    col_kw = tab_cfg.get("col_keyword")
    col_status = tab_cfg.get("col_status")
    header_row = tab_cfg.get("header_row", 1)

    def cell(row: list, idx: Optional[int]) -> str:
        return (row[idx].strip() if idx is not None and idx < len(row) else "")

    rows = []
    for i, row in enumerate(values, start=1):
        if i <= header_row or not row:
            continue
        url = cell(row, col_url)
        if not url.startswith("http"):
            continue
        rows.append({
            "row": i,
            "url": url,
            "keyword": cell(row, col_kw),
            "status": cell(row, col_status) or "(sans statut)",
        })
    return rows


def _fetch_pages_metrics(gsc_property: str, start: str, end: str) -> dict:
    """Une requête GSC dimension=page sur la fenêtre → {url_normalisée: métriques}."""
    analyzer = GSCAnalyzer(gsc_property)
    if not analyzer._gsc_service:
        raise RuntimeError("API GSC service account indisponible (credentials manquants ?)")

    by_page: dict = {}
    start_row = 0
    while True:
        body = {
            "startDate": start,
            "endDate": end,
            "dimensions": ["page"],
            "rowLimit": 25000,
            "startRow": start_row,
        }
        response = analyzer._gsc_service.searchanalytics().query(
            siteUrl=gsc_property, body=body
        ).execute()
        batch = response.get("rows", [])
        for r in batch:
            by_page[_norm(r["keys"][0])] = {
                "clicks": r.get("clicks", 0),
                "impressions": r.get("impressions", 0),
                "position": round(r.get("position", 0), 1),
            }
        if len(batch) < 25000:
            return by_page
        start_row += len(batch)


def _windows(
    days: int,
    start: Optional[str],
    end: Optional[str],
    compare_start: Optional[str] = None,
    compare_end: Optional[str] = None,
) -> tuple:
    """Retourne ((start, end) courante, (start, end) de référence).

    Par défaut la période de référence est celle de même durée juste avant la
    fenêtre courante (lecture « depuis la dernière fois »). Avec compare_start /
    compare_end elle est explicite : c'est ce qui permet un year-over-year sur
    le même mois calendaire (juillet 2026 vs juillet 2025), où la période
    précédente glissante comparerait juillet à juin — deux mois dont la
    saisonnalité scolaire n'a rien de comparable.
    """
    if bool(start) != bool(end):
        raise ValueError("--start et --end vont ensemble (ou ni l'un ni l'autre)")
    if bool(compare_start) != bool(compare_end):
        raise ValueError("--compare-start et --compare-end vont ensemble")
    if start:
        d_start = datetime.strptime(start, "%Y-%m-%d")
        d_end = datetime.strptime(end, "%Y-%m-%d")
        if d_end < d_start:
            raise ValueError("--end doit être ≥ --start")
        length = (d_end - d_start).days + 1
    else:
        d_end = datetime.now(timezone.utc).replace(tzinfo=None)
        d_start = d_end - timedelta(days=days)
        length = days

    fmt = "%Y-%m-%d"
    if compare_start:
        p_start = datetime.strptime(compare_start, "%Y-%m-%d")
        p_end = datetime.strptime(compare_end, "%Y-%m-%d")
        if p_end < p_start:
            raise ValueError("--compare-end doit être ≥ --compare-start")
        if p_start >= d_start:
            raise ValueError(
                "La période de comparaison doit précéder la période courante "
                f"({compare_start} ≥ {d_start.strftime(fmt)})"
            )
    else:
        p_end = d_start - timedelta(days=1)
        p_start = p_end - timedelta(days=length - 1)

    return (
        (d_start.strftime(fmt), d_end.strftime(fmt)),
        (p_start.strftime(fmt), p_end.strftime(fmt)),
    )


def _pct(before: float, after: float) -> Optional[float]:
    """Variation en % (None si pas de base de comparaison)."""
    if not before:
        return None
    return round((after - before) / before * 100, 1)


def _slug(text: str) -> str:
    """« Formations Diplômantes » → « formations-diplomantes ».

    Normalise pour la comparaison : accents, casse et séparateurs varient entre
    ce qu'on tape en ligne de commande et ce qui est saisi dans Notion.
    """
    import unicodedata
    folded = unicodedata.normalize("NFKD", text.strip().lower())
    folded = "".join(c for c in folded if not unicodedata.combining(c))
    return "-".join(p for p in re.split(r"[^a-z0-9]+", folded) if p)


def _ctr(clicks: float, impressions: float) -> Optional[float]:
    """CTR en % (None si aucune impression : pas de taux définissable)."""
    if not impressions:
        return None
    return round(clicks / impressions * 100, 2)


def _publication_year(row: dict) -> str:
    """Tranche d'ancienneté éditoriale d'une ligne (axe d'agrégat Notion)."""
    published = (row.get("published") or "")[:4]
    return published if published.isdigit() else "(sans date)"


def run_gsc_tab(
    site: str,
    tab: str,
    days: int = 28,
    start: Optional[str] = None,
    end: Optional[str] = None,
    dry_run: bool = False,
    source: str = "sheet",
    compare_start: Optional[str] = None,
    compare_end: Optional[str] = None,
    categories: Optional[list] = None,
) -> dict:
    """Deltas GSC (fenêtre courante vs précédente) des URLs suivies.

    Args:
        site: site slug (résolu en gsc_property via sites.json).
        tab: nom d'onglet déclaré dans sheets.tabs du site (source « sheet »).
        days: fenêtre en jours, ignorée si start/end fournis.
        start / end: bornes YYYY-MM-DD de la fenêtre courante ; la fenêtre de
            comparaison est toujours la période de même durée juste avant.
        dry_run: si True, n'écrit pas le dump local.
        source: « sheet » (onglet Google Sheets) ou « notion » (base de suivi
            des publications déclarée en notion.publications du site.json).
        compare_start / compare_end: bornes explicites de la période de
            référence (year-over-year). Par défaut, période de même durée
            juste avant la fenêtre courante.
        categories: restreint le périmètre à ces catégories éditoriales
            (comparaison insensible aux accents/casse). Source notion
            uniquement : un onglet Sheet ne porte pas la catégorie.
    """
    if source == "notion":
        from scripts.audit.notion_pub_source import read_publication_rows
        urls = read_publication_rows(site)
        tab = tab or "Publications Notion"
    else:
        urls = _read_tab_rows(site, tab)

    if categories:
        wanted = {_slug(c) for c in categories}
        known = {_slug(u.get("category", "")) for u in urls if u.get("category")}
        unknown = wanted - known
        if unknown:
            raise ValueError(
                "Catégorie inconnue : "
                + ", ".join(sorted(unknown))
                + ". Déclarées : "
                + ", ".join(sorted({u["category"] for u in urls if u.get("category")}))
            )
        urls = [u for u in urls if _slug(u.get("category", "")) in wanted]
        if not urls:
            raise ValueError("Aucune URL ne correspond aux catégories demandées")
    gsc_property = _site_gsc_property(site)
    (cur_start, cur_end), (prev_start, prev_end) = _windows(
        days, start, end, compare_start, compare_end
    )

    # Deux fenêtres de durées différentes ne sont pas comparables en volume :
    # on le signale dans le rapport plutôt que de laisser lire un delta faussé.
    _len = lambda a, b: (datetime.strptime(b, "%Y-%m-%d")
                         - datetime.strptime(a, "%Y-%m-%d")).days + 1
    cur_days, prev_days = _len(cur_start, cur_end), _len(prev_start, prev_end)

    cur = _fetch_pages_metrics(gsc_property, cur_start, cur_end)
    prev = _fetch_pages_metrics(gsc_property, prev_start, prev_end)

    pages = []
    for u in urls:
        key = _norm(u["url"])
        c = cur.get(key, {"clicks": 0, "impressions": 0, "position": None})
        p = prev.get(key, {"clicks": 0, "impressions": 0, "position": None})
        # Delta position : négatif = on remonte (meilleure position). None si
        # l'URL n'a d'impressions que sur une seule des deux fenêtres.
        pos_delta = (
            round(c["position"] - p["position"], 1)
            if c["position"] is not None and p["position"] is not None else None
        )
        pages.append({
            **u,
            "clicks_before": p["clicks"], "clicks_after": c["clicks"],
            "clicks_delta": c["clicks"] - p["clicks"],
            "clicks_delta_pct": _pct(p["clicks"], c["clicks"]),
            "impressions_before": p["impressions"], "impressions_after": c["impressions"],
            "impressions_delta": c["impressions"] - p["impressions"],
            "impressions_delta_pct": _pct(p["impressions"], c["impressions"]),
            # CTR : sépare « on est moins vu » de « on est vu mais moins cliqué »
            # (AI Overview, SERP feature) — deux causes, deux remèdes.
            "ctr_before": _ctr(p["clicks"], p["impressions"]),
            "ctr_after": _ctr(c["clicks"], c["impressions"]),
            "position_before": p["position"], "position_after": c["position"],
            "position_delta": pos_delta,
        })

    # Agrégats par statut éditorial (« Publié » = refresh en ligne : c'est la
    # ligne à lire pour juger l'impact des refreshs vs le reste de l'onglet).
    def _group_by(key_fn) -> dict:
        groups: dict = {}
        for page in pages:
            g = groups.setdefault(key_fn(page), {
                "urls": 0, "clicks_before": 0, "clicks_after": 0,
                "impressions_before": 0, "impressions_after": 0,
            })
            g["urls"] += 1
            for k in ("clicks_before", "clicks_after",
                      "impressions_before", "impressions_after"):
                g[k] += page[k]
        for g in groups.values():
            g["clicks_delta"] = g["clicks_after"] - g["clicks_before"]
            g["clicks_delta_pct"] = _pct(g["clicks_before"], g["clicks_after"])
            g["impressions_delta"] = g["impressions_after"] - g["impressions_before"]
            g["impressions_delta_pct"] = _pct(
                g["impressions_before"], g["impressions_after"])
            g["ctr_before"] = _ctr(g["clicks_before"], g["impressions_before"])
            g["ctr_after"] = _ctr(g["clicks_after"], g["impressions_after"])
        return groups

    by_status = _group_by(lambda p: p["status"])
    # Axes portés par la seule source Notion (catégorie, date de publication) :
    # absents d'un onglet Sheet, donc calculés uniquement quand ils existent.
    by_category = _group_by(lambda p: p["category"]) if any(
        "category" in p for p in pages) else {}
    by_year = _group_by(_publication_year) if any(
        "published" in p for p in pages) else {}

    total_before = sum(p["clicks_before"] for p in pages)
    total_after = sum(p["clicks_after"] for p in pages)
    impr_before = sum(p["impressions_before"] for p in pages)
    impr_after = sum(p["impressions_after"] for p in pages)

    # Une URL sans aucune impression sur la fenêtre de référence n'existait pas
    # (ou n'était pas indexée) : son trafic actuel est une création, pas une
    # progression. Mélangée aux autres, elle gonfle un pourcentage censé mesurer
    # l'évolution d'un stock — d'où la vue « à périmètre constant » en regard.
    existing = [p for p in pages if p["impressions_before"] > 0]
    fresh = [p for p in pages if p["impressions_before"] == 0]
    ex_cb = sum(p["clicks_before"] for p in existing)
    ex_ca = sum(p["clicks_after"] for p in existing)
    ex_ib = sum(p["impressions_before"] for p in existing)
    ex_ia = sum(p["impressions_after"] for p in existing)
    like_for_like = {
        "urls": len(existing),
        "clicks_before": ex_cb, "clicks_after": ex_ca,
        "clicks_delta": ex_ca - ex_cb, "clicks_delta_pct": _pct(ex_cb, ex_ca),
        "impressions_before": ex_ib, "impressions_after": ex_ia,
        "impressions_delta": ex_ia - ex_ib,
        "impressions_delta_pct": _pct(ex_ib, ex_ia),
        "ctr_before": _ctr(ex_cb, ex_ib), "ctr_after": _ctr(ex_ca, ex_ia),
    }
    new_urls = {
        "urls": len(fresh),
        "clicks_after": sum(p["clicks_after"] for p in fresh),
        "impressions_after": sum(p["impressions_after"] for p in fresh),
    }
    result = {
        "site_id": site,
        "tab": tab,
        "snapshot_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "period": {"start": cur_start, "end": cur_end, "days": cur_days},
        "previous_period": {"start": prev_start, "end": prev_end, "days": prev_days},
        "comparison_mode": "explicite" if compare_start else "période précédente",
        # Seulement en comparaison explicite : le mode glissant dérive ses deux
        # bornes du même calcul, il est cohérent avec lui-même par construction.
        "length_mismatch": bool(compare_start) and cur_days != prev_days,
        "totals": {
            "urls": len(pages),
            "clicks_before": total_before,
            "clicks_after": total_after,
            "clicks_delta": total_after - total_before,
            "clicks_delta_pct": _pct(total_before, total_after),
            "impressions_before": impr_before,
            "impressions_after": impr_after,
            "impressions_delta": impr_after - impr_before,
            "impressions_delta_pct": _pct(impr_before, impr_after),
            "ctr_before": _ctr(total_before, impr_before),
            "ctr_after": _ctr(total_after, impr_after),
        },
        "like_for_like": like_for_like,
        "new_urls": new_urls,
        "source": source,
        "categories": list(categories) if categories else [],
        "by_status": by_status,
        "by_category": by_category,
        "by_year": by_year,
        "progressions": sorted(
            (p for p in pages if p["clicks_delta"] > 0),
            key=lambda p: p["clicks_delta"], reverse=True,
        ),
        "regressions": sorted(
            (p for p in pages if p["clicks_delta"] < 0),
            key=lambda p: p["clicks_delta"],
        ),
        "stable": [p for p in pages if p["clicks_delta"] == 0],
    }

    if not dry_run:
        safe_tab = tab.lower().replace(" ", "_")
        # La période de référence entre dans le nom : deux rapports sur la même
        # fenêtre courante mais des comparaisons différentes (glissante vs
        # year-over-year) sont deux lectures distinctes, pas un écrasement.
        stem = f"gsc_tab_delta_{safe_tab}_{cur_start}_{cur_end}"
        if compare_start:
            stem += f"_vs_{prev_start}_{prev_end}"
        if categories:
            stem += "_" + "-".join(sorted(_slug(c) for c in categories))
        result["output_path"] = _dump(site, stem, result)
        result["report_path"] = _dump_html(site, stem, result)
    return result


# -- rapport HTML lisible (non-dev) ------------------------------------------
# Charte Superprof : corail #FE5C5D en accent de marque (bandeau), jamais comme
# couleur de donnée. Polarité gains/pertes : #0E8A6D / #C63032 (paire validée
# CVD via le validateur dataviz, signes +/− en encodage secondaire).

_POS = "#0E8A6D"
_NEG = "#C63032"
_BRAND = "#FE5C5D"

_MONTHS_FR = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
              "août", "septembre", "octobre", "novembre", "décembre"]


def _fr_date(iso: str) -> str:
    d = datetime.strptime(iso, "%Y-%m-%d")
    return f"{d.day} {_MONTHS_FR[d.month - 1]} {d.year}"


def _fr_num(n) -> str:
    """1234 → « 1 234 » (espace insécable fine)."""
    return f"{n:,}".replace(",", " ")


def _delta_html(delta: int, pct) -> str:
    if delta > 0:
        label = f"▲ +{_fr_num(delta)}"
        color = _POS
    elif delta < 0:
        label = f"▼ −{_fr_num(abs(delta))}"
        color = _NEG
    else:
        label = "= 0"
        color = "#6b7280"
    pct_txt = "" if pct is None else f" ({'+' if pct > 0 else ''}{str(pct).replace('.', ',')} %)"
    return f'<span style="color:{color};font-weight:600;white-space:nowrap">{label}{pct_txt}</span>'


def _signed_pct(pct: Optional[float]) -> str:
    """« +312,2 % » / « n/a » — pourcentage signé en notation française."""
    if pct is None:
        return "n/a"
    return f"{'+' if pct > 0 else ''}{str(pct).replace('.', ',')} %"


def _ctr_html(before: Optional[float], after: Optional[float]) -> str:
    """« 2,1 % → 2,8 % ▲ » — la flèche suit le sens du CTR (haut = mieux)."""
    if before is None or after is None:
        return '<span style="color:#9ca3af">–</span>'
    fb = f"{before:.2f}".replace(".", ",")
    fa = f"{after:.2f}".replace(".", ",")
    if after > before:
        return f'{fb} % → {fa} % <span style="color:{_POS}">▲</span>'
    if after < before:
        return f'{fb} % → {fa} % <span style="color:{_NEG}">▼</span>'
    return f"{fb} % → {fa} % ="


def _bar_html(delta: int, max_abs: int) -> str:
    """Micro-barre divergente : gauche = perte, droite = gain, base au centre."""
    if not max_abs:
        return ""
    width = max(2, round(abs(delta) / max_abs * 70))
    color = _POS if delta > 0 else _NEG
    if delta == 0:
        return '<div style="width:144px"></div>'
    side = "margin-left:72px" if delta > 0 else f"margin-left:{72 - width}px"
    return (f'<div style="width:144px;background:'
            f'linear-gradient(#e5e7eb,#e5e7eb) 72px 0/1px 100% no-repeat">'
            f'<div style="height:10px;width:{width}px;{side};background:{color};'
            f'border-radius:3px"></div></div>')


def _pos_html(pg: dict) -> str:
    b, a = pg["position_before"], pg["position_after"]
    if b is None or a is None:
        return '<span style="color:#9ca3af">–</span>'
    fb, fa = str(b).replace(".", ","), str(a).replace(".", ",")
    if a < b:
        return f'{fb} → {fa} <span style="color:{_POS}">▲</span>'
    if a > b:
        return f'{fb} → {fa} <span style="color:{_NEG}">▼</span>'
    return f"{fb} → {fa} ="


def _movers_table(rows: list[dict], max_abs: int) -> str:
    tr = []
    for pg in rows:
        slug = pg["url"].rstrip("/").rsplit("/", 1)[-1]
        tr.append(
            "<tr>"
            f'<td><a href="{pg["url"]}" style="color:#111827">{slug}</a></td>'
            f'<td class="num">{_fr_num(pg["clicks_before"])} → {_fr_num(pg["clicks_after"])}</td>'
            f'<td class="num">{_delta_html(pg["clicks_delta"], pg["clicks_delta_pct"])}</td>'
            f"<td>{_bar_html(pg['clicks_delta'], max_abs)}</td>"
            f'<td class="num">{_fr_num(pg["impressions_before"])} → '
            f'{_fr_num(pg["impressions_after"])}</td>'
            f'<td class="num">{_ctr_html(pg.get("ctr_before"), pg.get("ctr_after"))}</td>'
            f'<td class="num">{_pos_html(pg)}</td>'
            f"<td>{pg['status']}</td>"
            "</tr>"
        )
    return (
        '<div class="scroll"><table><thead><tr><th>Article</th><th>Clics avant → après</th>'
        '<th>Évolution</th><th></th><th>Impressions avant → après</th>'
        '<th>CTR</th><th>Position moyenne</th><th>Statut</th>'
        "</tr></thead><tbody>" + "".join(tr) + "</tbody></table></div>"
    )


def _render_html(r: dict) -> str:
    t = r["totals"]
    p, pp = r["period"], r["previous_period"]
    top = 20
    all_moves = r["progressions"] + r["regressions"]
    max_abs = max((abs(pg["clicks_delta"]) for pg in all_moves), default=0)

    kind = "Base Notion" if r.get("source") == "notion" else "Onglet"
    source_label = f"{kind} « {r['tab']} »"
    if r.get("categories"):
        source_label += " — " + ", ".join(r["categories"])

    # Year-over-year : les deux périodes sont choisies, « précédente » serait faux.
    same_month = (r.get("comparison_mode") == "explicite"
                  and p["start"][5:] == pp["start"][5:])
    if same_month:
        comparison_label = "la même période un an plus tôt"
    elif r.get("comparison_mode") == "explicite":
        comparison_label = "la période de référence"
    else:
        comparison_label = "la période précédente"

    # Les URLs nées après la période de référence créent du trafic au lieu d'en
    # faire progresser : sans cette mise au point, le % global se lit comme une
    # multiplication du stock existant, ce qu'il n'est pas.
    lfl, nu = r.get("like_for_like") or {}, r.get("new_urls") or {}
    lfl_block = ""
    if nu.get("urls"):
        lfl_block = (
            '<div class="note"><strong>Lecture : {n} des {tot} URLs suivies '
            "n'avaient aucune impression sur la période de référence</strong> "
            "(publiées depuis, ou pas encore indexées). Elles créent du trafic "
            "plutôt qu'elles n'en font progresser, et apportent {nc} clics / "
            "{ni} impressions.<br>À périmètre constant — les {lu} URLs déjà en "
            "ligne — l'évolution réelle est de <strong>{lc}</strong> clics et "
            "<strong>{li}</strong> impressions, contre {gc} et {gi} en incluant "
            "les nouvelles.</div>"
        ).format(
            n=nu["urls"], tot=t["urls"],
            nc=_fr_num(nu["clicks_after"]), ni=_fr_num(nu["impressions_after"]),
            lu=lfl.get("urls", 0),
            lc=_signed_pct(lfl.get("clicks_delta_pct")),
            li=_signed_pct(lfl.get("impressions_delta_pct")),
            gc=_signed_pct(t.get("clicks_delta_pct")),
            gi=_signed_pct(t.get("impressions_delta_pct")),
        )

    mismatch_note = ""
    if r.get("length_mismatch"):
        mismatch_note = (
            '<div class="alert"><strong>⚠️ Périodes de durées inégales</strong> — '
            f"{p.get('days')} jours contre {pp.get('days')} jours : les volumes de "
            "clics ne sont pas directement comparables, lire en priorité les "
            "positions moyennes.</div>"
        )

    pub_losses = [pg for pg in r["regressions"] if pg["status"] == "Publié"]

    def _group_table(groups: dict, label: str, sort_key=None) -> str:
        """Table d'agrégats (statut / catégorie / année) — même gabarit."""
        if not groups:
            return ""
        scale = max((abs(x["clicks_delta"]) for x in groups.values()), default=0) or 1
        items = sorted(groups.items(), key=sort_key) if sort_key else sorted(
            groups.items(), key=lambda kv: kv[1]["clicks_after"], reverse=True)
        body = "".join(
            "<tr>"
            f"<td>{name}</td>"
            f'<td class="num">{g["urls"]}</td>'
            f'<td class="num">{_fr_num(g["clicks_before"])} → {_fr_num(g["clicks_after"])}</td>'
            f'<td class="num">{_delta_html(g["clicks_delta"], g["clicks_delta_pct"])}</td>'
            f"<td>{_bar_html(g['clicks_delta'], scale)}</td>"
            f'<td class="num">{_fr_num(g["impressions_before"])} → '
            f'{_fr_num(g["impressions_after"])}</td>'
            f'<td class="num">{_delta_html(g["impressions_delta"], g["impressions_delta_pct"])}</td>'
            f'<td class="num">{_ctr_html(g["ctr_before"], g["ctr_after"])}</td>'
            "</tr>"
            for name, g in items
        )
        return (
            '<div class="scroll">'
            f"<table><thead><tr><th>{label}</th><th>Articles</th>"
            "<th>Clics avant → après</th><th>Évolution</th><th></th>"
            "<th>Impressions avant → après</th><th>Évol. impressions</th>"
            "<th>CTR</th></tr></thead>"
            f"<tbody>{body}</tbody></table></div>"
        )

    status_table = _group_table(r["by_status"], "Statut")
    category_block = ""
    if r.get("by_category"):
        category_block = (
            "<h2>Vue par catégorie</h2>"
            '<p class="hint">Quelle verticale éditoriale porte la croissance.</p>'
            + _group_table(r["by_category"], "Catégorie")
        )
    year_block = ""
    if r.get("by_year"):
        year_block = (
            "<h2>Vue par année de publication</h2>"
            '<p class="hint">Les articles anciens (2023) sont les candidats naturels '
            "au refresh ; les récents mesurent ce que la production actuelle rapporte.</p>"
            + _group_table(r["by_year"], "Année", sort_key=lambda kv: kv[0])
        )

    def tile(label: str, value: str, sub: str = "") -> str:
        return (f'<div class="tile"><div class="tl">{label}</div>'
                f'<div class="tv">{value}</div>'
                f'<div class="ts">{sub}</div></div>')

    tiles = [
        tile("Clics sur la période",
             f"{_fr_num(t['clicks_before'])} → {_fr_num(t['clicks_after'])}",
             _delta_html(t["clicks_delta"], t["clicks_delta_pct"])),
        tile("Impressions",
             f"{_fr_num(t['impressions_before'])} → {_fr_num(t['impressions_after'])}",
             _delta_html(t["impressions_delta"], t["impressions_delta_pct"])),
        tile("CTR moyen", _ctr_html(t["ctr_before"], t["ctr_after"]),
             "part des affichages qui deviennent des clics"),
        tile("Articles suivis", _fr_num(t["urls"]), source_label),
        tile("En progression", f'<span style="color:{_POS}">{len(r["progressions"])}</span>',
             "articles qui gagnent des clics"),
        tile("En régression", f'<span style="color:{_NEG}">{len(r["regressions"])}</span>',
             "articles qui perdent des clics"),
    ]

    alert = ""
    if pub_losses:
        items = "".join(
            f'<li><a href="{pg["url"]}">{pg["url"].rstrip("/").rsplit("/", 1)[-1]}</a> : '
            f'{_delta_html(pg["clicks_delta"], pg["clicks_delta_pct"])} clics, '
            f"position {_pos_html(pg)}</li>"
            for pg in pub_losses[:10]
        )
        alert = (
            f'<div class="alert"><strong>⚠️ {len(pub_losses)} article(s) déjà refreshé(s) '
            "(statut « Publié ») perdent des clics</strong> — premiers candidats à une "
            f"passe de suivi.<ul>{items}</ul></div>"
        )

    return f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Suivi refreshs — {r['tab']} — {r['site_id']}</title>
<style>
  body {{ font-family: -apple-system, "Segoe UI", Roboto, sans-serif; margin: 0;
         color: #111827; background: #fcfcfb; }}
  header {{ background: {_BRAND}; color: #fff; padding: 24px 32px; }}
  header h1 {{ margin: 0 0 6px; font-size: 22px; }}
  header p {{ margin: 0; opacity: .95; }}
  main {{ padding: 24px 32px; max-width: 1100px; }}
  .tiles {{ display: flex; gap: 16px; flex-wrap: wrap; margin: 8px 0 24px; }}
  .tile {{ background: #fff; border: 1px solid #e5e7eb; border-radius: 10px;
           padding: 14px 18px; min-width: 190px; flex: 1; }}
  .tl {{ font-size: 12px; text-transform: uppercase; letter-spacing: .04em;
         color: #6b7280; }}
  .tv {{ font-size: 26px; font-weight: 700; margin: 4px 0; }}
  .ts {{ font-size: 13px; color: #6b7280; }}
  h2 {{ font-size: 16px; margin: 28px 0 4px; }}
  .hint {{ color: #6b7280; font-size: 13px; margin: 0 0 10px; }}
  .scroll {{ overflow-x: auto; }}
  table {{ border-collapse: collapse; width: 100%; background: #fff;
           border: 1px solid #e5e7eb; border-radius: 10px; overflow: hidden;
           font-size: 14px; }}
  th, td {{ text-align: left; padding: 8px 12px; border-top: 1px solid #f0f0ef; }}
  thead th {{ background: #f9fafb; font-size: 12px; text-transform: uppercase;
              letter-spacing: .03em; color: #6b7280; border-top: none; }}
  td.num {{ font-variant-numeric: tabular-nums; white-space: nowrap; }}
  td a {{ text-decoration: none; }}
  td a:hover {{ text-decoration: underline; }}
  .alert {{ background: #fdf2f2; border: 1px solid #f5c6c6; border-left: 4px solid {_NEG};
            border-radius: 8px; padding: 12px 16px; margin: 20px 0; font-size: 14px; }}
  .note {{ background: #f4f7fb; border: 1px solid #d9e2ec; border-left: 4px solid #5b7fa6;
           border-radius: 8px; padding: 12px 16px; margin: 20px 0; font-size: 14px;
           line-height: 1.5; }}
  .alert ul {{ margin: 8px 0 0 18px; padding: 0; }}
  .alert li {{ margin: 3px 0; }}
  details {{ margin: 12px 0 24px; }}
  summary {{ cursor: pointer; color: #6b7280; font-size: 13px; }}
  footer {{ color: #9ca3af; font-size: 12px; margin: 32px 0 8px; }}
</style></head><body>
<header>
  <h1>Suivi des refreshs — {r['site_id']}</h1>
  <p>{source_label} · du {_fr_date(p['start'])} au {_fr_date(p['end'])},
     comparé à {comparison_label} ({_fr_date(pp['start'])} → {_fr_date(pp['end'])}) ·
     données Google Search Console</p>
</header>
<main>
  <div class="tiles">{''.join(tiles)}</div>
  {mismatch_note}
  {lfl_block}
  {alert}
  <h2>Vue par statut éditorial</h2>
  <p class="hint">« Publié » = refresh en ligne : c'est la ligne qui mesure l'impact
     réel des refreshs. Les autres statuts servent de point de comparaison.</p>
  {status_table}
  {category_block}
  {year_block}

  <h2>Plus fortes progressions</h2>
  <p class="hint">Position moyenne : plus le chiffre est petit, mieux l'article est classé
     (▲ = il remonte dans Google).</p>
  {_movers_table(r['progressions'][:top], max_abs)}
  <details><summary>Voir les {len(r['progressions'])} progressions</summary>
  {_movers_table(r['progressions'], max_abs)}</details>

  <h2>Plus fortes pertes</h2>
  {_movers_table(r['regressions'][:top], max_abs)}
  <details><summary>Voir les {len(r['regressions'])} régressions</summary>
  {_movers_table(r['regressions'], max_abs)}</details>

  <footer>Rapport généré le {_fr_date(r['snapshot_date'])} ·
  {len(r['stable'])} articles stables non listés ·
  les 2-3 derniers jours de la fenêtre sont sous-comptés par Google (latence des données).</footer>
</main></body></html>"""


def _dump_html(site: str, stem: str, payload: dict) -> str:
    """Écrit le rapport HTML à côté du dump JSON. Retourne le chemin."""
    from _shared.core.site_paths import SitePaths
    out_dir = SitePaths(base_path=REPO_ROOT).output_dir(site) / "audit"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{stem}.html"
    out_path.write_text(_render_html(payload), encoding="utf-8")
    return str(out_path)


def _dump(site: str, stem: str, payload: dict) -> str:
    """Écrit un dump JSON dans outputs/{site}/audit/. Retourne le chemin."""
    from _shared.core.site_paths import SitePaths
    out_dir = SitePaths(base_path=REPO_ROOT).output_dir(site) / "audit"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{stem}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return str(out_path)
