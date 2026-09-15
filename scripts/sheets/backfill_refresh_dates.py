"""Remplit la colonne « Date de refresh » des articles déjà republiés.

**Pourquoi ce script existe.** `push_to_wp` ne trace que ses propres
publications. Quand `cw push` échoue et que la republication se fait à la main
depuis WordPress — après relecture — l'article part en ligne sans laisser de
trace locale, et la colonne de suivi reste vide. Sur superprof.fr-ressources en
septembre 2026, 104 lignes publiées n'avaient aucune date.

La conséquence dépassait le confort de saisie : le rapport d'impact date ses
cohortes sur ces traces, donc 43 % du travail du mois en sortait sans que rien
ne le signale.

**La source de dates.** Le champ `modified` de WordPress, via le cache écrit par
`impact_cohort._pushed_dates_from_sheet_wp`. C'est une source de second rang —
une retouche ultérieure l'écrase — mais pour ces articles-là il n'en existe pas
d'autre, et la substitution a été validée contre les 20 lignes qui portaient
déjà une date saisie à la main : 10 identiques, 10 à +1 jour, aucun écart
erratique.

**Ce que le script ne fait pas** : écraser une date existante. Une saisie
humaine est une information, pas un doublon à corriger ; seules les cellules
vides sont remplies.

Usage :
    python3 -m scripts.sheets.backfill_refresh_dates --site <slug> [--apply]

Sans `--apply`, le script montre ce qu'il écrirait et ne touche à rien.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from _shared.core.site_paths import SitePaths
from scripts.audit.ahrefs_state import REPO_ROOT
from scripts.audit.impact_cohort import (
    _pushed_dates_from_backups,
    _pushed_dates_from_journal,
    _slug_from_url,
)

# Statuts éditoriaux qui signifient « l'article est en ligne ».
PUBLISHED_STATUSES = {"prêt pour relecture", "publié", "publie"}

# Colonne de date par onglet : elle porte un intitulé différent d'un onglet à
# l'autre (« Date de refresh », « Date de publication ») et n'existe pas
# partout. Un onglet absent de cette table est simplement ignoré.
DATE_COLUMNS = {
    "Medium Potential": 9,
    "New Growing List": 11,
}


def _col_letter(idx: int) -> str:
    out = ""
    idx += 1
    while idx:
        idx, rem = divmod(idx - 1, 26)
        out = chr(65 + rem) + out
    return out


def _load_dates(site: str) -> dict:
    """Toutes les dates connues, par ordre de fiabilité décroissante."""
    dates = {}
    cache_path = (SitePaths(base_path=REPO_ROOT).output_dir(site)
                  / "wp_backups" / "_modified_cache.json")
    if cache_path.is_file():
        try:
            dates.update({
                k: v for k, v in
                json.loads(cache_path.read_text(encoding="utf-8")).items() if v
            })
        except (OSError, json.JSONDecodeError):
            pass
    # Les traces de publication priment sur `modified` : elles datent un acte.
    dates.update(_pushed_dates_from_backups(site))
    dates.update(_pushed_dates_from_journal(site))
    return dates


def backfill(site: str, apply: bool = False) -> dict:
    cfg_path = SitePaths(base_path=REPO_ROOT).site_dir(site) / "config" / "site.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    sheets_cfg = cfg.get("sheets") or {}
    spreadsheet_id = sheets_cfg["spreadsheet_id"]

    from scripts.sheets.sheets_client import SheetsClient
    client = SheetsClient(spreadsheet_id)

    dates = _load_dates(site)
    updates, skipped_no_date, already = [], [], 0

    for tab in sheets_cfg.get("tabs") or []:
        name = tab.get("name")
        col_status = tab.get("col_status")
        col_date = tab.get("col_date", DATE_COLUMNS.get(name))
        if col_status is None or col_date is None:
            continue

        rows = client._read_sheet(name)
        for i, row in enumerate(rows[1:], start=2):
            url = (row[0] if row else "").strip()
            status = (row[col_status] if len(row) > col_status else "").strip()
            if not url.startswith("http") or status.lower() not in PUBLISHED_STATUSES:
                continue
            if (row[col_date] if len(row) > col_date else "").strip():
                already += 1
                continue

            slug = _slug_from_url(url)
            iso = dates.get(slug)
            if not iso:
                skipped_no_date.append((name, i, slug))
                continue

            updates.append({
                "sheet": name,
                "cell": f"{_col_letter(col_date)}{i}",
                # Format de la colonne, tel que saisi à la main : JJ/MM/AAAA.
                "value": datetime.strptime(iso, "%Y-%m-%d").strftime("%d/%m/%Y"),
                "_slug": slug,
            })

    ok = False
    if apply and updates:
        ok = client._batch_update_cells(
            [{k: v for k, v in u.items() if not k.startswith("_")} for u in updates]
        )

    return {
        "updates": updates,
        "applied": ok,
        "already_filled": already,
        "no_date_found": skipped_no_date,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--site", required=True)
    ap.add_argument("--apply", action="store_true",
                    help="écrit réellement dans la Sheet (sinon simulation)")
    args = ap.parse_args()

    res = backfill(args.site, apply=args.apply)
    print(f"À remplir       : {len(res['updates'])}")
    print(f"Déjà renseignés : {res['already_filled']}")
    print(f"Sans date connue: {len(res['no_date_found'])}")
    for u in res["updates"][:10]:
        print(f"  {u['sheet']}!{u['cell']:<6} {u['value']}  {u['_slug']}")
    if len(res["updates"]) > 10:
        print(f"  … et {len(res['updates']) - 10} autres")
    if args.apply:
        print("\nÉcriture :", "OK" if res["applied"] else "ÉCHEC")
    else:
        print("\nSimulation. Relancer avec --apply pour écrire.")


if __name__ == "__main__":
    main()
