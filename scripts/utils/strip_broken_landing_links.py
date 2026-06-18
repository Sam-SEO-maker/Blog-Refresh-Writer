#!/usr/bin/env python3
"""
Nettoyage : retire les liens landings cassés (404) vers
https://www.superprof.fr/cours/superprof/france/

- HTML (.html / .gutenberg.html) : déballe le lien (garde le texte d'ancre en clair).
- JSON metadata : retire le champ `superprof_cta` s'il pointe vers l'URL cassée.

Usage : python3 scripts/utils/strip_broken_landing_links.py [--apply]
Sans --apply : dry-run (compte seulement).
"""

import json
import re
import sys
from pathlib import Path

OUTPUTS = Path(__file__).resolve().parents[2] / "_shared" / "outputs"
BROKEN_URL = "https://www.superprof.fr/cours/superprof/france/"

# <a ...href="<BROKEN_URL>"...>TEXTE</a>  ->  TEXTE
LINK_RE = re.compile(
    r'<a\b[^>]*?href=(["\'])'
    + re.escape(BROKEN_URL)
    + r'\1[^>]*>(.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)


def clean_html(path: Path, apply: bool) -> int:
    text = path.read_text(encoding="utf-8")
    new_text, n = LINK_RE.subn(lambda m: m.group(2), text)
    if n and apply:
        path.write_text(new_text, encoding="utf-8")
    return n


BROKEN_PATH = "/cours/superprof/france/"


def clean_json(path: Path, apply: bool) -> int:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return 0

    # Champs métadonnées CTA Superprof — noms incohérents selon les batchs :
    # superprof_cta / superprof_link / cta_superprof (dicts), superprof_cta_url (str).
    to_remove: set[str] = set()
    for key, value in data.items():
        if isinstance(value, dict) and BROKEN_PATH in str(value.get("url", "")):
            to_remove.add(key)
        elif isinstance(value, str) and BROKEN_PATH in value:
            to_remove.add(key)
            # Retirer aussi le champ ancre compagnon (..._url -> ..._anchor).
            if key.endswith("_url"):
                to_remove.add(key[:-4] + "_anchor")

    to_remove &= set(data.keys())
    if not to_remove:
        return 0
    if apply:
        for key in to_remove:
            data.pop(key, None)
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return len(to_remove)


def main() -> None:
    apply = "--apply" in sys.argv
    html_links = html_files = json_fields = json_files = 0

    for path in sorted(OUTPUTS.rglob("*.html")):
        n = clean_html(path, apply)
        if n:
            html_files += 1
            html_links += n
            print(f"[HTML]  {n:2d} lien(s)  {path.relative_to(OUTPUTS)}")

    for path in sorted(OUTPUTS.rglob("*.json")):
        try:
            n = clean_json(path, apply)
        except json.JSONDecodeError:
            continue
        if n:
            json_files += 1
            json_fields += n
            print(f"[JSON]  superprof_cta retiré  {path.relative_to(OUTPUTS)}")

    mode = "APPLIQUÉ" if apply else "DRY-RUN (relancer avec --apply)"
    print(f"\n=== {mode} ===")
    print(f"HTML : {html_links} lien(s) déballé(s) dans {html_files} fichier(s)")
    print(f"JSON : {json_fields} champ(s) superprof_cta retiré(s) dans {json_files} fichier(s)")


if __name__ == "__main__":
    main()
