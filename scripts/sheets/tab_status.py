"""
Mise à jour de statut éditorial, générique par onglet (config-driven).

Remplace les chemins codés en dur par onglet (`New Growing List`, `⬆️ Growing`) :
les onglets de travail d'un site sont déclarés dans son `site.json`, bloc
`sheets.tabs`, chaque entrée portant :

    {"name": "...", "col_url": 0, "col_status": 5, "header_row": 2}

- `col_url`     : index 0-based de la colonne contenant l'URL ;
- `col_status`  : index 0-based de la colonne statut. ABSENT = l'onglet n'a pas
                  (encore) de colonne statut : l'écriture y est refusée avec un
                  message clair (ajouter la colonne dans la Sheet + déclarer
                  `col_status` pour l'activer) ;
- `header_row`  : nombre de lignes d'en-tête à sauter (défaut 1 ; ex. 2 pour un
                  onglet avec une ligne-bannière au-dessus des en-têtes).

L'URL est cherchée dans TOUS les onglets déclarés (ou un seul via `tab=`).
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from _shared.core.constants import canonical_site_slug
from _shared.core.sheets_config import get_sheets_config


@dataclass
class StatusUpdate:
    tab: str
    row: int          # 1-indexed
    written: bool     # False si l'onglet n'a pas de col_status
    reason: str = ""


def _norm(url: str) -> str:
    return (url or "").strip().rstrip("/").lower()


def _col_letter(idx: int) -> str:
    letters = ""
    idx += 1
    while idx:
        idx, rem = divmod(idx - 1, 26)
        letters = chr(ord("A") + rem) + letters
    return letters


def _sheets_service():
    from googleapiclient.discovery import build
    from _shared.core.google_auth import get_credentials
    creds = get_credentials(["https://www.googleapis.com/auth/spreadsheets"])
    if creds is None:
        raise RuntimeError("Google credentials unavailable (see GOOGLE_SA_PATH / .env)")
    return build("sheets", "v4", credentials=creds)


def _spreadsheet_id(site_slug: str) -> str:
    cfg = get_sheets_config(site_slug)
    sid = cfg.get("spreadsheet_id")
    if not sid and cfg.get("spreadsheet_env"):
        sid = os.environ.get(cfg["spreadsheet_env"], "")
    if not sid:
        raise RuntimeError(f"No spreadsheet_id configured for site '{site_slug}'")
    return sid


def update_status(site_slug: str, url: str, value: str,
                  tab: Optional[str] = None) -> Optional[StatusUpdate]:
    """Cherche `url` dans les onglets déclarés du site et écrit `value` en
    colonne statut. Retourne un StatusUpdate (written=False si l'onglet trouvé
    n'a pas de colonne statut), ou None si l'URL n'est dans aucun onglet."""
    site_slug = canonical_site_slug(site_slug)
    tabs = get_sheets_config(site_slug).get("tabs") or []
    if tab:
        tabs = [t for t in tabs if t.get("name") == tab]
        if not tabs:
            raise ValueError(f"Tab '{tab}' not declared in sheets.tabs of {site_slug}")

    svc = _sheets_service()
    sid = _spreadsheet_id(site_slug)
    target = _norm(url)

    for t in tabs:
        name = t["name"]
        col_url = t.get("col_url", 0)
        header_row = t.get("header_row", 1)
        letter = _col_letter(col_url)
        data = svc.spreadsheets().values().get(
            spreadsheetId=sid, range=f"'{name}'!{letter}:{letter}",
        ).execute().get("values", [])
        for i, row in enumerate(data, start=1):
            if i <= header_row or not row:
                continue
            if _norm(row[0]) == target:
                if "col_status" not in t:
                    return StatusUpdate(tab=name, row=i, written=False,
                                        reason=f"tab '{name}' has no status column "
                                               f"(add one in the Sheet, then declare col_status in site.json)")
                status_letter = _col_letter(t["col_status"])
                svc.spreadsheets().values().update(
                    spreadsheetId=sid,
                    range=f"'{name}'!{status_letter}{i}",
                    valueInputOption="RAW",
                    body={"values": [[value]]},
                ).execute()
                return StatusUpdate(tab=name, row=i, written=True)
    return None
