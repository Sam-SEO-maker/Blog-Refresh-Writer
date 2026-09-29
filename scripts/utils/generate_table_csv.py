"""Génère les CSV de tableaux (+ zip par article) pour Superprof Ressources.

KEEP (audit 2026-07-23) : pas d'importeur Python — outil batch MANUEL assumé
(lancé en python -m après une fournée d'articles ; les csv_zips/ des outputs
superprof en attestent). Complémentaire de table_csv_extractor (par-article,
appelé par output_manager à la génération).

Pour chaque article, extrait les <table> du fichier `{slug}.gutenberg.html`
et écrit un CSV par tableau, nommé `{slug-à-tirets}_tableau_{descriptif-sujet}.csv`
(descripteur = sujet déduit du heading le plus proche, PAS les en-têtes — voir
mémoire feedback-csv-naming-tablepress). Puis zippe par article dans csv_zips/.

Usage:
    python -m scripts.utils.generate_table_csv [fichier_urls.txt]
    (sans argument : tous les {slug}.gutenberg.html du dossier html/)
"""
from __future__ import annotations

import csv
import re
import sys
import unicodedata
import zipfile
from pathlib import Path

from bs4 import BeautifulSoup

from scripts.utils.table_csv_extractor import _parse_table, extract_tables_to_csv
from scripts.utils.output_manager import dated_batch_folder_name
from scripts.utils.output_lookup import strip_output_suffixes

from _shared.core.site_paths import SitePaths
OUT = SitePaths().output_dir("superprof.fr-ressources")
HTML = OUT / "html"
CSVDIR = OUT / "csv"
ZIPDIR = OUT / "csv_zips"
EMO = re.compile("[\U0001F000-\U0001FAFF←-➿⬀-⯿☀-⛿️⃣‍]")
STOP = re.compile(r"\b(les?|la|des?|du|un|une|au|aux|et|d|l|en|pour|sur|ce|cette)\b", re.I)


def subj_slug(s: str) -> str:
    s = EMO.sub("", s)
    s = unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode("ascii")
    s = STOP.sub(" ", s)
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return "-".join(s.split("-")[:5])[:60] or "tableau"


def hyphen_slug(url: str) -> str:
    return url.rstrip("/").split("/")[-1].replace(".html", "")


def gutenberg_for(url: str) -> Path:
    return HTML / f"{hyphen_slug(url)}.gutenberg.html"


# La chaîne de refresh écrit `{slug}_refreshed.gutenberg.html` (le suffixe vient
# de `cw refresh`), pas `{slug}.gutenberg.html`. Chercher le nom nu ne trouvait
# donc AUCUN fichier produit par le pipeline : `main()` affichait « ABSENT » sur
# des articles pourtant présents, et il fallait reconstruire les zip à la main.
# Les deux formes sont désormais acceptées, de la plus spécifique à la plus large.
_GUTENBERG_PATTERNS = ("{slug}_refreshed.gutenberg.html", "{slug}.gutenberg.html")


def find_gutenberg(slug: str, batch_folder: str) -> Path | None:
    """Le `.gutenberg.html` de `slug` : sous-dossier daté d'abord, sinon scan."""
    for pattern in _GUTENBERG_PATTERNS:
        dated = HTML / batch_folder / pattern.format(slug=slug)
        if dated.exists():
            return dated
    for pattern in _GUTENBERG_PATTERNS:
        matches = sorted(HTML.rglob(pattern.format(slug=slug)))
        if matches:
            return matches[0]
    return None


def gen_for(art: str, html: str, batch_folder: str | None = None) -> list[Path]:
    """Écrit les CSV de `art` dans `csv/` (plat) et le zip dans `csv_zips/`.

    Délègue le nommage et l'indexation à `extract_tables_to_csv`, le même
    extracteur que celui appelé par la chaîne à la génération : deux
    implémentations donnaient deux noms pour le même tableau, et seul celui de
    la chaîne était inscrit dans `_index.csv`. Le lot 201-249 s'est retrouvé
    avec six doublons byte-identiques sous des noms concurrents.

    `batch_folder` est ignoré (gardé pour compatibilité d'appel) : les CSV vont
    dans le dossier plat que `_index.csv` référence, pas dans un sous-dossier
    daté qui échappait à l'index.
    """
    # Purge des CSV/zip devenus obsolètes pour cet article, sinon un tableau
    # renommé (titre modifié au refresh) laisserait son ancien fichier derrière.
    for p in CSVDIR.glob(f"{art}_tableau_*.csv"):
        p.unlink()
    (ZIPDIR / f"{art}_tableaux.zip").unlink(missing_ok=True)

    made = extract_tables_to_csv(
        html_content=html,
        csv_dir=CSVDIR,
        file_slug=art,
    )
    if made:
        ZIPDIR.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(ZIPDIR / f"{art}_tableaux.zip", "w", zipfile.ZIP_DEFLATED) as z:
            for p in made:
                z.write(p, p.name)
    return made


def main() -> int:
    batch_folder = dated_batch_folder_name()
    if len(sys.argv) > 1:
        urls = [l.strip() for l in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines() if l.strip()]
        # Cherche le .gutenberg.html dans le sous-dossier daté du jour, sinon
        # scan récursif (au cas où il a été généré un autre jour).
        targets = []
        for u in urls:
            slug = hyphen_slug(u)
            found = find_gutenberg(slug, batch_folder)
            # Pas trouvé : on garde le chemin nu attendu, pour que le message
            # d'erreur dise quel fichier manque plutôt que de sauter la ligne.
            targets.append((slug, found or HTML / batch_folder / f"{slug}.gutenberg.html"))
    else:
        # `strip_output_suffixes` retire `_refreshed` en plus de `.gutenberg.html` :
        # sans lui, le CSV s'appelait `{slug}_refreshed_tableau_...`.
        targets = [(strip_output_suffixes(p.name), p)
                   for p in sorted(HTML.rglob("*.gutenberg.html"))]
    total = 0
    for art, path in targets:
        if not path.exists():
            print(f"  ✗ ABSENT {path.name}")
            continue
        made = gen_for(art, path.read_text(encoding="utf-8"), batch_folder=batch_folder)
        if made:
            total += len(made)
            flag = "  ⚠ >3 (ok si lexique/grammaire)" if len(made) > 3 else ""
            print(f"  {art}: {len(made)} CSV{flag}")
    print(f"\nTotal CSV générés: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
