"""Refresh list enseigna : pull GSC, filtre Avis / Versus, push 2 onglets."""

import json
from collections import defaultdict
from datetime import datetime, timezone
from urllib.parse import urlparse

from scripts.audit.ahrefs_state import REPO_ROOT, _write_tab
from scripts.audit.gsc_state import fetch_gsc_keywords, _site_gsc_property
from scripts.sheets.sheets_client import SheetsClient

SPREADSHEET_ID = "1rNRU2WzlqfsAvFDjJHDN3ChCZ3u0NIfRaPoM4s1MzEM"
HEADERS = [
    "url", "priority", "impressions", "clicks", "ctr", "avg_position",
    "nb_kw", "top_keyword", "top_kw_impressions", "snapshot_date",
]


def _slug(url: str) -> str:
    path = urlparse(url).path.strip("/")
    return path.rsplit("/", 1)[-1] if path else ""


def _bucket(slug: str) -> str | None:
    if slug.startswith("superprof-vs-"):
        return "Versus"
    if "avis" in slug:
        return "Avis"
    return None


def _priority(impressions: int, clicks: int) -> str:
    if impressions >= 1000 or clicks >= 50:
        return "HIGH"
    if impressions >= 200 or clicks >= 10:
        return "MEDIUM"
    return "LOW"


def _aggregate(raw: list[dict], snapshot: str) -> dict[str, list[list]]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in raw:
        groups[r["url"]].append(r)

    buckets: dict[str, list[list]] = {"Avis": [], "Versus": []}
    for url, items in groups.items():
        bucket = _bucket(_slug(url))
        if not bucket:
            continue
        sum_clicks = sum(i["clicks"] for i in items)
        sum_impr = sum(i["impressions"] for i in items)
        weighted_pos = (
            sum(i["position"] * i["impressions"] for i in items) / sum_impr
            if sum_impr else 0
        )
        ctr = round((sum_clicks / sum_impr * 100), 2) if sum_impr else 0
        top = max(items, key=lambda x: x["impressions"])
        priority = _priority(sum_impr, sum_clicks)
        buckets[bucket].append([
            url, priority, sum_impr, sum_clicks, ctr, round(weighted_pos, 2),
            len(items), top["keyword"], top["impressions"], snapshot,
        ])

    _prio_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    for b in buckets:
        buckets[b].sort(key=lambda row: (_prio_order[row[1]], -row[2]))
    return buckets


def _print_summary(buckets: dict[str, list[list]]) -> None:
    for name, rows in buckets.items():
        highs = [r for r in rows if r[1] == "HIGH"]
        meds = [r for r in rows if r[1] == "MEDIUM"]
        lows = [r for r in rows if r[1] == "LOW"]
        print(f"\n[{name}] total={len(rows)} | HIGH={len(highs)} MEDIUM={len(meds)} LOW={len(lows)}")
        print(f"  Top 5 by priority:")
        for r in rows[:5]:
            print(f"    [{r[1]}] impr={r[2]} clicks={r[3]} pos={r[5]} — {r[0]}")


def run(months: int = 6, dry_run: bool = False) -> dict:
    gsc_property = _site_gsc_property("enseigna")
    print(f"[enseigna-refresh-list] pull GSC ({gsc_property}, {months}m)")
    raw = fetch_gsc_keywords(gsc_property, months=months)
    print(f"[enseigna-refresh-list] {len(raw)} rows brutes")

    snapshot = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    buckets = _aggregate(raw, snapshot)
    _print_summary(buckets)

    if dry_run:
        out_dir = REPO_ROOT / "_shared" / "outputs" / "enseigna" / "audit"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"refresh_list_{snapshot}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump({"snapshot_date": snapshot, "buckets": buckets}, f, ensure_ascii=False, indent=2)
        print(f"\n[enseigna-refresh-list] DRY-RUN dump: {out_path}")
        return {"avis": len(buckets["Avis"]), "versus": len(buckets["Versus"]), "output_path": str(out_path)}

    print(f"\n[enseigna-refresh-list] push → {SPREADSHEET_ID}")
    sheets = SheetsClient(SPREADSHEET_ID)
    if not sheets._sheets_service:
        raise RuntimeError("SheetsClient: API directe indisponible")
    svc = sheets._sheets_service
    _write_tab(svc, SPREADSHEET_ID, "Avis", HEADERS, buckets["Avis"])
    _write_tab(svc, SPREADSHEET_ID, "Versus", HEADERS, buckets["Versus"])
    print("[enseigna-refresh-list] ✓ 2 onglets mis à jour")

    return {
        "avis": len(buckets["Avis"]),
        "versus": len(buckets["Versus"]),
        "spreadsheet_id": SPREADSHEET_ID,
    }
