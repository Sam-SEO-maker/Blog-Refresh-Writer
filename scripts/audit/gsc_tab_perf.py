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


def _windows(days: int, start: Optional[str], end: Optional[str]) -> tuple:
    """Retourne ((start, end) courante, (start, end) précédente de même durée)."""
    if bool(start) != bool(end):
        raise ValueError("--start et --end vont ensemble (ou ni l'un ni l'autre)")
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
    prev_end = d_start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=length - 1)
    fmt = "%Y-%m-%d"
    return (
        (d_start.strftime(fmt), d_end.strftime(fmt)),
        (prev_start.strftime(fmt), prev_end.strftime(fmt)),
    )


def _pct(before: float, after: float) -> Optional[float]:
    """Variation en % (None si pas de base de comparaison)."""
    if not before:
        return None
    return round((after - before) / before * 100, 1)


def run_gsc_tab(
    site: str,
    tab: str,
    days: int = 28,
    start: Optional[str] = None,
    end: Optional[str] = None,
    dry_run: bool = False,
) -> dict:
    """Deltas GSC (fenêtre courante vs précédente) des URLs d'un onglet.

    Args:
        site: site slug (résolu en gsc_property via sites.json).
        tab: nom d'onglet déclaré dans sheets.tabs du site.
        days: fenêtre en jours, ignorée si start/end fournis.
        start / end: bornes YYYY-MM-DD de la fenêtre courante ; la fenêtre de
            comparaison est toujours la période de même durée juste avant.
        dry_run: si True, n'écrit pas le dump local.
    """
    urls = _read_tab_rows(site, tab)
    gsc_property = _site_gsc_property(site)
    (cur_start, cur_end), (prev_start, prev_end) = _windows(days, start, end)

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
            "position_before": p["position"], "position_after": c["position"],
            "position_delta": pos_delta,
        })

    # Agrégats par statut éditorial (« Publié » = refresh en ligne : c'est la
    # ligne à lire pour juger l'impact des refreshs vs le reste de l'onglet).
    by_status: dict = {}
    for pg in pages:
        g = by_status.setdefault(pg["status"], {"urls": 0, "clicks_before": 0, "clicks_after": 0})
        g["urls"] += 1
        g["clicks_before"] += pg["clicks_before"]
        g["clicks_after"] += pg["clicks_after"]
    for g in by_status.values():
        g["clicks_delta"] = g["clicks_after"] - g["clicks_before"]
        g["clicks_delta_pct"] = _pct(g["clicks_before"], g["clicks_after"])

    total_before = sum(p["clicks_before"] for p in pages)
    total_after = sum(p["clicks_after"] for p in pages)
    result = {
        "site_id": site,
        "tab": tab,
        "snapshot_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "period": {"start": cur_start, "end": cur_end},
        "previous_period": {"start": prev_start, "end": prev_end},
        "totals": {
            "urls": len(pages),
            "clicks_before": total_before,
            "clicks_after": total_after,
            "clicks_delta": total_after - total_before,
            "clicks_delta_pct": _pct(total_before, total_after),
        },
        "by_status": by_status,
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
        stem = f"gsc_tab_delta_{safe_tab}_{cur_start}_{cur_end}"
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
            f'<td class="num">{_pos_html(pg)}</td>'
            f"<td>{pg['status']}</td>"
            "</tr>"
        )
    return (
        '<table><thead><tr><th>Article</th><th>Clics avant → après</th>'
        '<th>Évolution</th><th></th><th>Position moyenne</th><th>Statut</th>'
        "</tr></thead><tbody>" + "".join(tr) + "</tbody></table>"
    )


def _render_html(r: dict) -> str:
    t = r["totals"]
    p, pp = r["period"], r["previous_period"]
    top = 20
    all_moves = r["progressions"] + r["regressions"]
    max_abs = max((abs(pg["clicks_delta"]) for pg in all_moves), default=0)

    pub_losses = [pg for pg in r["regressions"] if pg["status"] == "Publié"]

    status_rows = []
    for status, g in sorted(r["by_status"].items(),
                            key=lambda kv: kv[1]["clicks_after"], reverse=True):
        status_rows.append(
            "<tr>"
            f"<td>{status}</td>"
            f'<td class="num">{g["urls"]}</td>'
            f'<td class="num">{_fr_num(g["clicks_before"])} → {_fr_num(g["clicks_after"])}</td>'
            f'<td class="num">{_delta_html(g["clicks_delta"], g["clicks_delta_pct"])}</td>'
            f"<td>{_bar_html(g['clicks_delta'], max(abs(x['clicks_delta']) for x in r['by_status'].values()) or 1)}</td>"
            "</tr>"
        )

    def tile(label: str, value: str, sub: str = "") -> str:
        return (f'<div class="tile"><div class="tl">{label}</div>'
                f'<div class="tv">{value}</div>'
                f'<div class="ts">{sub}</div></div>')

    tiles = [
        tile("Clics sur la période",
             f"{_fr_num(t['clicks_before'])} → {_fr_num(t['clicks_after'])}",
             _delta_html(t["clicks_delta"], t["clicks_delta_pct"])),
        tile("Articles suivis", _fr_num(t["urls"]), f"onglet « {r['tab']} »"),
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
  .alert ul {{ margin: 8px 0 0 18px; padding: 0; }}
  .alert li {{ margin: 3px 0; }}
  details {{ margin: 12px 0 24px; }}
  summary {{ cursor: pointer; color: #6b7280; font-size: 13px; }}
  footer {{ color: #9ca3af; font-size: 12px; margin: 32px 0 8px; }}
</style></head><body>
<header>
  <h1>Suivi des refreshs — {r['site_id']}</h1>
  <p>Onglet « {r['tab']} » · du {_fr_date(p['start'])} au {_fr_date(p['end'])},
     comparé à la période précédente ({_fr_date(pp['start'])} → {_fr_date(pp['end'])}) ·
     données Google Search Console</p>
</header>
<main>
  <div class="tiles">{''.join(tiles)}</div>
  {alert}
  <h2>Vue par statut éditorial</h2>
  <p class="hint">« Publié » = refresh en ligne : c'est la ligne qui mesure l'impact
     réel des refreshs. Les autres statuts servent de point de comparaison.</p>
  <table><thead><tr><th>Statut</th><th>Articles</th><th>Clics avant → après</th>
  <th>Évolution</th><th></th></tr></thead>
  <tbody>{''.join(status_rows)}</tbody></table>

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
