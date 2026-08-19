"""Appariement d'un article à ses fichiers de sortie.

Trois conventions de nommage coexistent dans `outputs/metadata/` selon le
chemin qui a écrit le fichier : le slug de contexte (URL entière
translittérée), le slug d'URL, et le slug dérivé du titre. Les trois sont
tentées, du plus spécifique au plus large.

Partagé par `finalize` et `push` : les deux publient le même article et
doivent apparier la même metadata, sinon l'un pousse un titre que l'autre
ignore.
"""
from pathlib import Path
from typing import Optional

_HTML_SUFFIXES = (".gutenberg.html", ".html_refreshed", "_refreshed", ".html")


def strip_output_suffixes(filename: str) -> str:
    """`mon-article.html_refreshed.gutenberg.html` → `mon-article`.

    Les noms réels cumulent les suffixes ; `Path.stem` n'en retire qu'un.
    """
    changed = True
    while changed:
        changed = False
        for suffix in _HTML_SUFFIXES:
            if filename.endswith(suffix):
                filename = filename[: -len(suffix)]
                changed = True
    return filename


def context_slug_for(url: str) -> str:
    """Slug de contexte de l'URL, ou "" si indisponible."""
    try:
        from scripts.audit.ytg_qc import url_to_context_slug
        return url_to_context_slug(url)
    except Exception:
        return ""


def find_metadata(meta_dir: Path, url: str = "", url_slug: str = "",
                  file_slug: str = "") -> Optional[Path]:
    """Trouve le JSON de metadata d'un article. None si aucun ou ambigu.

    Un appariement ambigu vaut mieux abandonné que joué au hasard : publier le
    titre et la meta description d'un autre article ne se voit pas au push.
    """
    if not meta_dir.exists():
        return None

    slugs = [s for s in (context_slug_for(url), url_slug, file_slug) if s]

    for slug in slugs:
        cand = meta_dir / f"{slug}_metadata.json"
        if cand.exists():
            return cand

    for slug in slugs:
        matches = [p for p in meta_dir.glob("*_metadata.json")
                   if p.name.startswith(slug)]
        if len(matches) == 1:
            return matches[0]
    return None


def metadata_dir_for(gutenberg_path: Path) -> Path:
    """`outputs/html/[type/]article.html` → `outputs/metadata/`."""
    d = gutenberg_path.parent
    while d.name and d.name != "html":
        d = d.parent
    return d.parent / "metadata"
