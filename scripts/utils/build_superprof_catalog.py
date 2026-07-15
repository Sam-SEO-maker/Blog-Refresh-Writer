"""Génère le catalogue des blogs Superprof depuis les propriétés GSC.

Le **catalogue** (`_shared/config/superprof_blogs_catalog.json`) liste TOUS les
blogs Superprof actifs (éditoriaux `/blog/` + sites Ressources), qu'ils soient
onboardés ou non comme tenants Content Writer. C'est le « menu » qu'un responsable
pays consulte pour découvrir ce qu'il peut onboarder (`cw tenant init <id>`).

À NE PAS confondre avec le **registre** `sites.json` (tenants réellement onboardés,
chargés par le moteur au runtime). Catalogue = carte ; registre = commande.

Source = propriétés GSC (`mcp gsc-remote list_properties`), la liste vivante des
sites. Comme les tools MCP sont appelés côté Claude Code (pas depuis ce process),
la liste est passée en entrée :

    # Claude appelle mcp__gsc-remote__list_properties, colle la sortie dans un
    # fichier, puis :
    python -m scripts.utils.build_superprof_catalog --from-file props.txt

Filtrage : on ne garde que les propriétés `/blog/` (type=blog) et les 6 sites
Ressources connus (type=ressources). On écarte le bruit (homepages nues,
diccionario, laromedel, resources hors des 6 marchés…).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CATALOG_PATH = _PROJECT_ROOT / "_shared" / "config" / "superprof_blogs_catalog.json"

# Les 6 sites Ressources confirmés (cf. RECENSEMENT_BLOGS_SUPERPROF.md).
# gsc_property → (tenant_id conventionnel, country, language, url_base)
RESSOURCES_SITES = {
    "https://www.superprof.fr/ressources/":   ("superprof-ressources", "FR", "fr", "/ressources/"),
    "https://www.superprof.es/apuntes/":      ("es-es-ressources", "ES", "es", "/apuntes/"),
    "https://www.superprof.de/lernplattform/": ("de-de-ressources", "DE", "de", "/lernplattform/"),
    "https://www.superprof.co.uk/resources/": ("en-uk-ressources", "UK", "en", "/resources/"),
    "https://www.superprof.com/resources/":   ("en-us-ressources", "US", "en", "/resources/"),
    "https://www.superprof.com.br/recursos/": ("pt-br-ressources", "BR", "pt", "/recursos/"),
}

# Mapping TLD → (country, language) pour les blogs éditoriaux.
# Basé sur les domaines Superprof réels ; élargir si besoin.
_TLD_META = {
    "fr": ("FR", "fr"), "es": ("ES", "es"), "de": ("DE", "de"), "co.uk": ("UK", "en"),
    "com": ("US", "en"), "com.br": ("BR", "pt"), "it": ("IT", "it"), "ca": ("CA", "en"),
    "mx": ("MX", "es"), "com.ar": ("AR", "es"), "cl": ("CL", "es"), "co": ("CO", "es"),
    "pe": ("PE", "es"), "be": ("BE", "fr"), "ch": ("CH", "de"), "at": ("AT", "de"),
    "pt": ("PT", "pt"), "nl": ("NL", "nl"), "pl": ("PL", "pl"), "se": ("SE", "sv"),
}

_DOMAIN_RE = re.compile(r"https?://(?:www\.)?superprof\.([a-z.]+?)/")


def _tld_of(url: str) -> str:
    m = _DOMAIN_RE.search(url.lower())
    return m.group(1) if m else ""


def _country_lang(tld: str) -> tuple[str, str]:
    return _TLD_META.get(tld, (tld.upper(), ""))


def _slug_tld(tld: str) -> str:
    """`co.uk` → `uk`, `com.br` → `br`, `com` → `us` (pour l'id blog)."""
    if tld == "com":
        return "us"
    return tld.split(".")[-1]


def parse_properties(text: str) -> list[str]:
    """Extrait les URLs de la sortie de list_properties (lignes `- <url> (...)`)."""
    urls = []
    for line in text.splitlines():
        m = re.search(r"(https?://\S+/)", line)
        if m:
            urls.append(m.group(1).strip())
    return urls


def build_catalog(urls: list[str]) -> dict:
    """Construit le catalogue {ressources[], blogs[]} filtré depuis les URLs GSC."""
    ressources = []
    blogs = []
    seen = set()

    for url in urls:
        u = url.rstrip("/") + "/"
        if u in seen:
            continue
        seen.add(u)

        # Sites Ressources connus (liste blanche stricte).
        if u in RESSOURCES_SITES:
            tid, country, lang, url_base = RESSOURCES_SITES[u]
            ressources.append({
                "tenant_id": tid, "type": "ressources", "country": country,
                "language": lang, "gsc_property": u, "url_base": url_base,
                "onboardable": True,
            })
            continue

        # Blogs éditoriaux : /blog/ uniquement.
        if u.endswith("/blog/"):
            tld = _tld_of(u)
            if not tld:
                continue
            country, lang = _country_lang(tld)
            blogs.append({
                "tenant_id": f"{lang or 'xx'}-{_slug_tld(tld)}-blog",
                "type": "blog", "country": country, "language": lang,
                "gsc_property": u, "url_base": "/blog/", "onboardable": True,
            })

    ressources.sort(key=lambda x: x["tenant_id"])
    blogs.sort(key=lambda x: x["tenant_id"])
    return {
        "_comment": (
            "Catalogue des blogs Superprof (généré depuis GSC list_properties). "
            "NE PAS confondre avec sites.json (tenants onboardés, lu au runtime). "
            "Régénérer : python -m scripts.utils.build_superprof_catalog --from-file <props>."
        ),
        "ressources_sites": ressources,
        "blogs": blogs,
        "counts": {"ressources": len(ressources), "blogs": len(blogs)},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Génère superprof_blogs_catalog.json depuis GSC")
    ap.add_argument("--from-file", required=True,
                    help="Fichier contenant la sortie de mcp gsc-remote list_properties.")
    ap.add_argument("--apply", action="store_true", help="Écrit le catalogue (sinon stdout).")
    args = ap.parse_args()

    text = Path(args.from_file).read_text(encoding="utf-8")
    urls = parse_properties(text)
    catalog = build_catalog(urls)

    if not args.apply:
        print(json.dumps(catalog, ensure_ascii=False, indent=2))
        print(f"\n[CATALOG] {catalog['counts']} — dry-run (--apply pour écrire).", file=sys.stderr)
        return 0

    CATALOG_PATH.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[CATALOG] ✓ {CATALOG_PATH} — {catalog['counts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
