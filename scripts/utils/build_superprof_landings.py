#!/usr/bin/env python3
"""
Génère _shared/config/superprof_landings.json à partir de l'export brut
_shared/config/landings-superprof-fr.csv (base interne des landings Superprof).

Stratégie (cf. CLAUDE.md / rotator) :
- Colonne vertébrale : les pages nationales /cours/{matiere}/france/.
- Variété géo : pour chaque matière, les variantes des TOP villes FR réelles
  (arrondissements exclus), uniquement si la landing a des profs (Annonces > 0).
- Aucune ancre nue "professeur particulier" : toutes les ancres contiennent la
  matière (corrige l'anti-pattern "même ancre partout").
- target_keywords laissé vide : le CSV n'a pas de volume/position fiable
  (à enrichir via Ahrefs/DataForSEO ultérieurement).

Usage : python3 scripts/utils/build_superprof_landings.py [--cities N] [--site SITE_ID]
"""

import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# Export brut gardé en local (70 Mo, hors git — voir .gitignore : _local/).
CSV_PATH = ROOT / "_local" / "landings-superprof-fr.csv"
OUT_PATH = ROOT / "_shared" / "config" / "superprof_landings.json"

# Matières du blog superprof.fr-ressources sans page nationale exacte -> équivalent Superprof
SUBJECT_ALIASES = {
    "informatique": "initiation-informatique",
    "arts-appliques": "arts-plastiques",
    "management": "economie",
}

# Affichage correct (accents / minuscules internes) pour les villes "piège".
CITY_DISPLAY_OVERRIDES = {
    "saint-etienne": "Saint-Étienne",
    "aix-en-provence": "Aix-en-Provence",
    "clermont-ferrand": "Clermont-Ferrand",
    "boulogne-billancourt": "Boulogne-Billancourt",
    "le-havre": "Le Havre",
    "le-mans": "Le Mans",
    "orleans": "Orléans",
    "nimes": "Nîmes",
    "besancon": "Besançon",
}

ARRONDISSEMENT_RE = re.compile(r"-\d+$")  # paris-12, lyon-2, ...


def slug_after(url: str, marker: str) -> str:
    parts = [p for p in url.split("/") if p]
    if marker in parts:
        i = parts.index(marker)
        if i + 1 < len(parts):
            return parts[i + 1]
    return ""


def city_of(url: str) -> str:
    parts = [p for p in url.split("/") if p]
    return parts[-1] if parts else ""


def to_int(value: str) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def city_display(slug: str) -> str:
    if slug in CITY_DISPLAY_OVERRIDES:
        return CITY_DISPLAY_OVERRIDES[slug]
    small = {"en", "sur", "le", "la", "les", "sous", "lez", "du", "de"}
    parts = slug.split("-")
    return "-".join(p if (p in small and i > 0) else p.capitalize()
                     for i, p in enumerate(parts))


def city_locution(slug: str) -> str:
    """Locution grammaticale : 'à Lyon', 'au Havre', 'à La Rochelle'."""
    if slug.startswith("le-"):
        return "au " + city_display(slug[3:])
    if slug.startswith("les-"):
        return "aux " + city_display(slug[4:])
    return "à " + city_display(slug)


def matiere_name(subject: str) -> str:
    """Nom matière pour les ancres : minuscule, sans parenthèses ni espaces parasites."""
    name = re.sub(r"\([^)]*\)", "", subject).strip().lower()
    return re.sub(r"\s+", " ", name)


def subject_match_tokens(slug: str, name: str) -> list[str]:
    tokens = {slug, slug.replace("-", " "), name}
    # alias inverse : si ce slug est la cible d'un alias blog, ajouter le terme blog
    for blog_term, csv_slug in SUBJECT_ALIASES.items():
        if csv_slug == slug:
            tokens.add(blog_term)
            tokens.add(blog_term.replace("-", " "))
    return sorted(t for t in tokens if t)


def de_name(name: str) -> str:
    """Élision : 'de' -> "d'" devant voyelle ou h muet."""
    if name and name[0].lower() in "aeiouéèêàâîôûy" or name[:1].lower() == "h":
        return f"d'{name}"
    return f"de {name}"


def national_anchors(name: str) -> list[str]:
    dn = de_name(name)
    return [
        f"cours {dn}",
        f"prof {dn}",
        f"professeur {dn}",
        f"cours particuliers {dn}",
        f"professeur particulier {dn}",
    ]


def city_anchors(name: str, slug: str) -> list[str]:
    loc = city_locution(slug)
    dn = de_name(name)
    return [
        f"cours {dn} {loc}",
        f"prof {dn} {loc}",
        f"professeur {dn} {loc}",
        f"cours particuliers {dn} {loc}",
    ]


def weight_from_ads(ads: int, *, national: bool) -> int:
    base = 5 if national else 0
    return max(1, base + min(15, ads // 3000))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cities", type=int, default=30, help="nb de top villes FR à inclure")
    ap.add_argument("--site", default="superprof.fr-ressources", help="site_id cible")
    args = ap.parse_args()

    if not CSV_PATH.exists():
        raise SystemExit(
            f"CSV source introuvable : {CSV_PATH}\n"
            "Place l'export Superprof (landings-superprof-fr.csv) dans _local/ "
            "(dossier local, hors git) avant de régénérer."
        )

    # Passe 1 : matières nationales + comptage villes + index (matiere, ville)
    national: dict[str, dict] = {}            # slug -> row
    city_counts: dict[str, int] = defaultdict(int)
    city_rows: dict[tuple, dict] = {}         # (matiere_slug, city) -> row

    with open(CSV_PATH, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            ltype = row["Landing Type"]
            url = row["Landing URL"]
            if ltype == "matiere":
                national[slug_after(url, "cours")] = row
            elif ltype == "matiere_ville":
                city = city_of(url)
                if ARRONDISSEMENT_RE.search(city) or city == "france":
                    continue
                city_counts[city] += 1
                city_rows[(slug_after(url, "cours"), city)] = row

    top_cities = [c for c, _ in sorted(
        city_counts.items(), key=lambda kv: kv[1], reverse=True)][: args.cities]

    # Passe 2 : construire les landings
    landings = []
    for slug, row in sorted(national.items()):
        if to_int(row["Annonces"]) <= 0:
            continue
        name = matiere_name(row["Subject"])
        match = subject_match_tokens(slug, name)
        landings.append({
            "slug": f"/cours/{slug}/france/",
            "subject_match": match,
            "weight": weight_from_ads(to_int(row["Annonces"]), national=True),
            "anchor_pool": national_anchors(name),
            "target_keywords": [],
        })
        for city in top_cities:
            crow = city_rows.get((slug, city))
            if not crow or to_int(crow["Annonces"]) <= 0:
                continue
            landings.append({
                "slug": f"/cours/{slug}/{city}/",
                "subject_match": match,
                "weight": weight_from_ads(to_int(crow["Annonces"]), national=False),
                "anchor_pool": city_anchors(name, city),
                "target_keywords": [],
                "city_display": city_display(city),
            })

    config = {
        "_doc": ("Registre des landings Superprof par site. Généré depuis "
                 "landings-superprof-fr.csv par scripts/utils/build_superprof_landings.py. "
                 "Ne pas éditer à la main : régénérer."),
        "_updated": "2026-06-17",
        "_source": "landings-superprof-fr.csv",
        args.site: {
            "default_subject": "soutien-scolaire",
            "landings": landings,
        },
    }

    OUT_PATH.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")

    n_nat = sum(1 for x in landings if x["slug"].endswith("/france/"))
    print(f"Top villes ({len(top_cities)}) : {', '.join(top_cities)}")
    print(f"Landings écrites : {len(landings)} "
          f"({n_nat} nationales + {len(landings) - n_nat} villes)")
    print(f"→ {OUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
