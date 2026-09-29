"""Joint le ZIP des tableaux d'un article à sa ligne de commande Notion.

Chaque ligne de refresh de « Resources - Main Database » doit porter, dans le
corps de sa page, le ZIP des CSV de tableaux : `csv_zips/{slug}_tableaux.zip`.
Le geste manuel est d'ouvrir la ligne depuis `Title (Main KW)` et de taper
`/fichiers`. Ce module fait la même chose depuis la livraison.

**Le fichier est un bloc, pas une propriété.** `Title (Main KW)` est la propriété
*titre* de la base (`"type": "title"`) : l'API rejette un payload `files` dessus,
et la base ne comporte aucune propriété de type `files`. La pièce jointe vit donc
comme un bloc `file` enfant de la page — ce que produit `/fichiers`.

Trois appels : créer le file upload, POSTer le fichier, ajouter le bloc.

Le déclenchement est la **publication**, pas la commande : quand `/sheets-update`
crée la ligne, l'article n'est pas écrit et le ZIP n'existe pas encore. À la
publication, l'URL est connue et le ZIP vient d'être produit.

Détail complet, pièges et réparation : `_shared/docs/NOTION_ZIP_TABLEAUX.md`.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Optional

import requests

logger = logging.getLogger(__name__)

# Le POST multipart ne passe pas par _headers() : il ne porte PAS de
# Content-Type json, c'est requests qui pose la frontière multipart.
_UPLOAD_TIMEOUT = 60


def slug_from_url(url: str) -> str:
    """Dernier segment de l'URL, sans extension — la clé des noms de ZIP."""
    last = (url or "").rstrip("/").rsplit("/", 1)[-1]
    return re.sub(r"\.html?$", "", last)


def find_zip(site_output_dir: Path, slug: str) -> Optional[Path]:
    """Localise le ZIP de tableaux d'un article, racine d'abord.

    Les ZIP ne sont pas tous à la racine de `csv_zips/` : les fournées passées
    en ont laissé dans des sous-dossiers datés (`articles_260909/`) et dans
    `_archive/`, parfois préfixés du nom de lot
    (`articles_260903__{slug}_tableaux.zip`). Ne chercher qu'à la racine
    sous-estime la couverture — mesuré une fois à 47 lignes sur 100 là où le
    balayage complet en trouvait 92.

    Un même slug peut exister en plusieurs exemplaires ; les contenus vérifiés
    (noms + CRC des CSV) étaient identiques sur les 25 cas rencontrés, donc
    l'ordre de préférence est une commodité, pas un arbitrage.
    """
    zips = site_output_dir / "csv_zips"
    if not zips.is_dir():
        return None

    direct = zips / f"{slug}_tableaux.zip"
    if direct.is_file():
        return direct

    # Sous-dossiers et archives, nom nu ou préfixé du lot.
    candidates = [
        p for p in zips.rglob(f"*{slug}_tableaux.zip")
        if p.is_file() and p.name.split("__")[-1] == f"{slug}_tableaux.zip"
    ]
    if candidates:
        # Le plus récent : à contenu égal, c'est celui de la dernière passe.
        return max(candidates, key=lambda p: p.stat().st_mtime)
    return None


def _page_file_names(client, page_id: str) -> Optional[list[str]]:
    """Noms des fichiers déjà attachés à la page, ou None si la lecture échoue.

    Distinguer « aucune pièce jointe » de « je n'ai pas pu lire » est ce qui
    empêche d'attacher un doublon sur une erreur réseau : None fait renoncer,
    [] fait attacher.
    """
    url = f"{client.API_BASE_URL}/blocks/{page_id}/children?page_size=100"
    names: list[str] = []
    try:
        while True:
            resp = requests.get(url, headers=client._headers(), timeout=30)
            if resp.status_code != 200:
                logger.warning("[Notion] lecture blocs %s: HTTP %s", page_id, resp.status_code)
                return None
            data = resp.json()
            for block in data.get("results", []):
                if block.get("type") != "file":
                    continue
                f = block.get("file", {})
                name = f.get("name") or ""
                if not name:
                    # Un upload interne n'expose pas toujours `name` ; l'URL
                    # signée porte le nom de fichier dans son chemin.
                    src = (f.get("file") or {}).get("url") or (f.get("external") or {}).get("url") or ""
                    name = src.split("?")[0].rsplit("/", 1)[-1]
                names.append(name)
            if not data.get("has_more"):
                return names
            url = (
                f"{client.API_BASE_URL}/blocks/{page_id}/children"
                f"?page_size=100&start_cursor={data['next_cursor']}"
            )
    except requests.exceptions.RequestException as exc:
        logger.warning("[Notion] lecture blocs %s: %s", page_id, exc)
        return None


def _upload_file(client, zip_path: Path) -> Optional[str]:
    """Crée le file upload et y envoie le fichier. Retourne son id."""
    try:
        create = requests.post(
            f"{client.API_BASE_URL}/file_uploads",
            headers=client._headers(),
            json={"filename": zip_path.name, "content_type": "application/zip"},
            timeout=30,
        )
        if create.status_code != 200:
            logger.warning(
                "[Notion] création upload %s: HTTP %s %s",
                zip_path.name, create.status_code, create.text[:200],
            )
            return None
        payload = create.json()
        upload_id = payload.get("id")
        send_url = payload.get("upload_url")
        if not upload_id or not send_url:
            return None

        # Multipart : surtout pas le Content-Type json de _headers().
        auth = {
            "Authorization": f"Bearer {client._token}",
            "Notion-Version": client.API_VERSION,
        }
        with zip_path.open("rb") as fh:
            send = requests.post(
                send_url,
                headers=auth,
                files={"file": (zip_path.name, fh, "application/zip")},
                timeout=_UPLOAD_TIMEOUT,
            )
        if send.status_code != 200 or send.json().get("status") != "uploaded":
            logger.warning(
                "[Notion] envoi %s: HTTP %s %s",
                zip_path.name, send.status_code, send.text[:200],
            )
            return None
        return upload_id
    except (requests.exceptions.RequestException, ValueError, OSError) as exc:
        logger.warning("[Notion] upload %s: %s", zip_path.name, exc)
        return None


def _append_file_block(client, page_id: str, upload_id: str, name: str) -> bool:
    """Ajoute le bloc `file` à la page. Le bloc est ce que rend `/fichiers`."""
    try:
        resp = requests.patch(
            f"{client.API_BASE_URL}/blocks/{page_id}/children",
            headers=client._headers(),
            json={"children": [{
                "object": "block",
                "type": "file",
                "file": {
                    "type": "file_upload",
                    "file_upload": {"id": upload_id},
                    "name": name,
                },
            }]},
            timeout=30,
        )
        if resp.status_code != 200:
            logger.warning(
                "[Notion] ajout bloc %s: HTTP %s %s",
                page_id, resp.status_code, resp.text[:200],
            )
            return False
        return True
    except requests.exceptions.RequestException as exc:
        logger.warning("[Notion] ajout bloc %s: %s", page_id, exc)
        return False


def attach_tables_zip(
    site: str,
    url: str,
    base_path: Optional[Path] = None,
    slug: Optional[str] = None,
) -> dict:
    """Joint le ZIP de tableaux de `url` à sa ligne Notion, si tout s'y prête.

    Best-effort et non bloquant par contrat : appelé après une publication
    réussie, l'article est déjà en ligne quand cette fonction s'exécute. Aucun
    échec ici ne doit remettre en cause une publication faite. Les raisons de
    ne rien faire sont donc rendues telles quelles, jamais levées.

    Returns:
        {"ok": bool, "reason": str, "zip": str|None, "page_id": str|None}
        `reason` vaut "attached" en cas de succès, sinon dit pourquoi :
        no_config / no_token / no_zip / no_access / no_row / already /
        upload_failed / block_failed / unreadable.
    """
    from _shared.core.site_paths import SitePaths

    out = {"ok": False, "reason": "", "zip": None, "page_id": None}
    slug = slug or slug_from_url(url)

    tp = SitePaths(base_path=base_path) if base_path else SitePaths()

    # 1. Le site déclare-t-il une base de commandes ?
    try:
        cfg = json.loads(tp.site_config(site).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        out["reason"] = "no_config"
        return out
    orders = ((cfg.get("notion") or {}).get("orders")) or {}
    database_id = orders.get("database_id")
    if not database_id:
        out["reason"] = "no_config"
        return out

    # 2. Le ZIP existe-t-il ? Un article sans tableau n'en a pas, et c'est normal.
    zip_path = find_zip(tp.output_dir(site), slug)
    if zip_path is None:
        out["reason"] = "no_zip"
        return out
    out["zip"] = str(zip_path)

    from scripts.notion import NotionClient

    client = NotionClient()
    if not client.is_configured:
        out["reason"] = "no_token"
        return out

    # 3. Retrouver la ligne par URL normalisée, comme le fait orders_sync.
    from scripts.notion.orders_sync import normalize_url

    key = normalize_url(url)
    col_url = orders.get("col_url", "Local resource URL")
    rows = client.query_database(database_id)
    if not rows:
        # `query_database` avale le 404 et rend []. Une base vide et une base
        # inaccessible se ressemblent, mais pas pour qui lit le message : dire
        # « URL absente des commandes » enverrait chercher une ligne manquante
        # alors que l'intégration n'a tout simplement pas accès à la base.
        out["reason"] = "no_access"
        return out
    page_id = None
    for page in rows:
        prop = (page.get("properties") or {}).get(col_url) or {}
        value = prop.get(prop.get("type", ""), "")
        if isinstance(value, list):
            value = "".join(x.get("plain_text", "") for x in value)
        if value and normalize_url(value) == key:
            page_id = page.get("id")
            break
    if not page_id:
        out["reason"] = "no_row"
        return out
    out["page_id"] = page_id

    # 4. Ne jamais poser un second exemplaire : l'API ne déduplique pas, et une
    #    lecture impossible se traite comme un doute, donc comme un renoncement.
    existing = _page_file_names(client, page_id)
    if existing is None:
        out["reason"] = "unreadable"
        return out
    if any(n.endswith(f"{slug}_tableaux.zip") for n in existing):
        out["reason"] = "already"
        out["ok"] = True
        return out

    upload_id = _upload_file(client, zip_path)
    if not upload_id:
        out["reason"] = "upload_failed"
        return out

    if not _append_file_block(client, page_id, upload_id, zip_path.name):
        out["reason"] = "block_failed"
        return out

    out["ok"] = True
    out["reason"] = "attached"
    return out


# Messages rendus à l'utilisateur, un par raison. Les cas où il n'y avait
# simplement rien à faire (pas de tableau, site sans base Notion) sont muets :
# les signaler à chaque publication ferait du bruit sur la ligne qui compte.
_SILENT = {"no_config", "no_zip"}

_MESSAGES = {
    "attached": "Notion: tables ZIP attached ({zip})",
    "already": "Notion: tables ZIP already attached",
    "no_token": "Notion ZIP not attached (NOTION_TOKEN missing)",
    "no_access": ("Notion ZIP not attached (orders database unreachable - share it "
                  "with the integration holding NOTION_TOKEN)"),
    "no_row": "Notion ZIP not attached (URL in no order row)",
    "unreadable": "Notion ZIP not attached (page unreadable - check integration access)",
    "upload_failed": "Notion ZIP not attached (upload failed)",
    "block_failed": "Notion ZIP not attached (file block rejected)",
}


def attach_tables_zip_message(
    site: str,
    url: str,
    base_path: Optional[Path] = None,
    slug: Optional[str] = None,
) -> Optional[str]:
    """`attach_tables_zip` en version affichable. Ne lève JAMAIS.

    Même contrat que `mark_published` : appelée juste après un push WP réussi,
    l'article est déjà en ligne. Une base Notion injoignable, un token absent ou
    une ligne manquante ne doivent pas transformer une publication réussie en
    échec — d'où un message rendu à l'appelant plutôt qu'une exception.

    Returns:
        Le message à afficher, ou None quand il n'y avait rien à faire.
    """
    try:
        res = attach_tables_zip(site, url, base_path=base_path, slug=slug)
    except Exception as exc:  # réseau, config illisible, API inattendue…
        return f"Notion ZIP not attached ({type(exc).__name__}: {exc})"

    reason = res.get("reason", "")
    if reason in _SILENT:
        return None
    template = _MESSAGES.get(reason, "Notion ZIP not attached ({reason})")
    zip_name = Path(res["zip"]).name if res.get("zip") else ""
    return template.format(zip=zip_name, reason=reason or "unknown")
