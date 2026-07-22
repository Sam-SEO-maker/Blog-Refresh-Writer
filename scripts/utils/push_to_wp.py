"""Pousse les articles refreshés (Gutenberg) sur WordPress via l'API REST.

Pour chaque URL fournie :
1. Résout le post WP (par slug)
2. Sauvegarde la version live actuelle dans wp_backups/{id}_before.json (si absente)
3. POST title + content (gutenberg) + meta SEOPress (titre + description), status=publish

Deux usages :
- CLI batch (rétro-compat) : `python -m scripts.utils.push_to_wp <fichier_urls.txt>`
  (site historique `superprof.fr-ressources`).
- Programmatique, multi-site (Phase 6b, appelé par `cw finalize --publish`) :
  `build_client(site)` + `publish_article(client, site, url, gutenberg_path, metadata_path)`.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from scripts.scraping.wordpress_api_client import WordPressAPIClient

from _shared.core.site_paths import SitePaths

_DEFAULT_SITE = "superprof.fr-ressources"


def _slug(url: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", url.lower()).strip("_")


def build_client(site: str = _DEFAULT_SITE, base_path: Optional[Path] = None) -> WordPressAPIClient:
    """Construit le client WP REST à partir du bloc `wp_api_config` du site."""
    tp = SitePaths(base_path=base_path) if base_path else SitePaths()
    cfg_path = tp.site_config(site)
    cfg_full = json.loads(cfg_path.read_text(encoding="utf-8"))
    cfg = cfg_full.get("wp_api_config")
    if not cfg:
        raise ValueError(f"Site '{site}' n'a pas de bloc 'wp_api_config' — publication impossible.")
    return WordPressAPIClient(
        api_base_url=cfg["api_base_url"],
        user_env_var=cfg["user_env_var"],
        password_env_var=cfg["password_env_var"],
        timeout=cfg.get("timeout", 30),
    )


def publish_article(
    client: WordPressAPIClient,
    site: str,
    url: str,
    gutenberg_path: Path,
    metadata_path: Optional[Path] = None,
    base_path: Optional[Path] = None,
    status: str = "publish",
) -> dict:
    """Publie un article déjà généré sur WP (paths explicites, multi-site).

    Args:
        client: client WP REST du site.
        site: id du site (pour localiser wp_backups/).
        url: URL de l'article live (résolution du post par slug).
        gutenberg_path: fichier `.gutenberg.html` à pousser (contenu).
        metadata_path: JSON {title, meta_description} pour title + meta SEOPress.
            Si absent/illisible, on pousse le contenu sans toucher au titre/meta.
        status: statut WP cible (défaut `publish`).

    Returns:
        {"url", "id", "ok", "error"}
    """
    gutenberg_path = Path(gutenberg_path)
    if not gutenberg_path.exists():
        return {"url": url, "ok": False, "error": f"no_gutenberg_file:{gutenberg_path.name}"}

    content = gutenberg_path.read_text(encoding="utf-8")

    meta = {}
    if metadata_path is not None:
        metadata_path = Path(metadata_path)
        if metadata_path.exists():
            try:
                meta = json.loads(metadata_path.read_text(encoding="utf-8"))
            except Exception:
                meta = {}

    post = client.get_post_by_url(url)
    if not post:
        return {"url": url, "ok": False, "error": "post_not_found"}
    pid = post["id"]

    # Backup once (par site)
    tp = SitePaths(base_path=base_path) if base_path else SitePaths()
    backups = tp.output_dir(site) / "wp_backups"
    backups.mkdir(parents=True, exist_ok=True)
    bkp = backups / f"{pid}_before.json"
    if not bkp.exists():
        bkp.write_text(json.dumps({
            "id": pid, "slug": post.get("slug"),
            "title": post.get("title"), "raw": post.get("raw"),
        }, ensure_ascii=False, indent=2), encoding="utf-8")

    wp_meta = {}
    if meta.get("title"):
        wp_meta["_seopress_titles_title"] = meta.get("title", "")
    if meta.get("meta_description"):
        wp_meta["_seopress_titles_desc"] = meta.get("meta_description", "")

    res = client.update_post(
        post_id=pid,
        title=meta.get("title") or None,
        content=content,
        meta=wp_meta or None,
        status=status,
    )
    return {"url": url, "id": pid, "ok": res["ok"], "error": res["error"]}


def push_url(client: WordPressAPIClient, url: str, site: str = _DEFAULT_SITE) -> dict:
    """Chemin batch historique : résout gutenberg/metadata par slug d'URL dans le site."""
    tp = SitePaths()
    out = tp.output_dir(site)
    slug = _slug(url)
    gut = out / "html" / f"{slug}_refreshed.gutenberg.html"
    meta_p = out / "metadata" / f"{slug}_metadata.json"
    if not meta_p.exists():
        return {"url": url, "ok": False, "error": "no_metadata_file"}
    return publish_article(client, site, url, gut, meta_p)


def main() -> int:
    load_dotenv()
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.utils.push_to_wp <urls_file.txt>")
        return 2
    urls = [l.strip() for l in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines() if l.strip()]
    client = build_client()
    ok = fail = 0
    for i, url in enumerate(urls, 1):
        r = push_url(client, url)
        if r["ok"]:
            ok += 1
            print(f"[{i:>2}/{len(urls)}] ✓ id={r.get('id')} {url.split('/ressources/')[1]}")
        else:
            fail += 1
            print(f"[{i:>2}/{len(urls)}] ✗ {r.get('error')} :: {url}")
    print(f"\nPushed OK: {ok} | Failed: {fail}")
    return 0 if not fail else 1


if __name__ == "__main__":
    raise SystemExit(main())
