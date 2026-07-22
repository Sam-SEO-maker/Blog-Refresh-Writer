"""Onboarding d'un site depuis le catalogue Superprof (Phase 6d).

`cw site init <id>` matérialise un site :
  1. crée le squelette `sites/{id}/` (config/site.json pré-rempli + prompts/,
     linking_maps/, outputs/) ;
  2. ajoute une entrée dans `_shared/config/sites.json` (registre runtime) ;
  3. matérialise le dossier dans le sparse-checkout (`git sparse-checkout add`) si
     le worktree est sparse — un SEO Manager voit alors son site sans exposer
     les autres. Sur un worktree plein (mainteneur), l'étape est ignorée sans risque.

Le pré-remplissage vient du catalogue `superprof_sites_catalog.json` (gsc_property,
url_base, langue, pays). Les champs éditoriaux (ton, blacklist, guides) restent des
TODO explicites à compléter par le responsable pays — c'est là qu'il « charge ses
fichiers » (prompts/site.md, guides).

Idempotent et sûr : refuse d'écraser un site existant sans --force.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Optional

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CATALOG_PATH = _PROJECT_ROOT / "_shared" / "config" / "superprof_sites_catalog.json"
SITES_JSON = _PROJECT_ROOT / "_shared" / "config" / "sites.json"
LOCATIONS_PATH = _PROJECT_ROOT / "_shared" / "config" / "dataforseo_locations.json"


def load_catalog_entry(site_slug: str) -> Optional[dict]:
    """Cherche `site_slug` dans le catalogue (ressources + blogs)."""
    if not CATALOG_PATH.exists():
        return None
    cat = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    for entry in cat.get("sites", []):
        if entry.get("site_slug") == site_slug:
            return entry
    return None


def resolve_serp_location(country: str) -> str:
    """`location_name` DataForSEO pour un code pays du catalogue, "" si inconnu.

    La table est générée/validée par `build_dataforseo_locations.py` : un
    `location_name` inventé ferait échouer l'appel SERP. Un pays absent laisse le
    champ vide plutôt que de deviner — le moteur retombe alors sur France/fr.
    """
    if not country or not LOCATIONS_PATH.exists():
        return ""
    table = json.loads(LOCATIONS_PATH.read_text(encoding="utf-8"))
    return table.get("locations", {}).get(country, "")


def _domain_from_gsc(gsc_property: str) -> str:
    # https://www.superprof.es/apuntes/ → superprof.es
    core = gsc_property.split("//", 1)[-1].split("/", 1)[0]
    return core[4:] if core.startswith("www.") else core


def build_site_config(entry: dict) -> dict:
    """Squelette site.json pré-rempli depuis le catalogue. Éditorial = TODO."""
    tid = entry["site_slug"]
    gsc = entry["gsc_property"]
    return {
        "site_slug": tid,
        "display_name": f"Superprof {entry.get('country','')} ({entry.get('type','')})".strip(),
        "domain": _domain_from_gsc(gsc),
        "url_base": gsc,
        "gsc_property": gsc,
        # Superprof.* → MCP gsc-remote (Phase 6c) ; service_account reste le défaut
        # sûr. Un responsage sur propriété MCP peut laisser tel quel.
        "auth_mode": "service_account",
        "content_type": "blog_article",
        "subject_category": "education_general",
        "language": entry.get("language", ""),
        # Locale SERP : lus par l'orchestrateur (_get_serp_analyzer). Absents ou
        # vides → France/fr, le défaut des marchés historiques.
        "serp_location": resolve_serp_location(entry.get("country", "")),
        "_TODO": (
            "Compléter par le responsable pays : tone_profile, seo_settings, "
            "editorial_guides (déposer prompts/site.md + guides dans ce dossier), "
            "sheets, wp_api_config, brand_rules. Copier depuis "
            "onboarding/site-model/ (livré sur ta machine) ; le site de référence "
            "superprof-ressources n'est pas sur ton disque (sparse-checkout)."
        ),
    }


def _worktree_is_sparse(root: Path) -> bool:
    """True si le worktree git est en sparse-checkout (sinon plein / pas un repo)."""
    try:
        res = subprocess.run(
            ["git", "sparse-checkout", "list"],
            cwd=str(root), capture_output=True, text=True,
        )
    except (OSError, FileNotFoundError):
        return False
    # `git sparse-checkout list` renvoie 0 + des lignes en sparse ;
    # sur un worktree plein il échoue ("this worktree is not sparse").
    return res.returncode == 0 and bool(res.stdout.strip())


def _sparse_add_site(root: Path, site_slug: str) -> bool:
    """Ajoute `sites/{id}` au sparse-checkout si le worktree est sparse.

    Retourne True si la matérialisation a été demandée, False si sautée (worktree
    plein, hors repo git, ou git absent). Ne convertit jamais un worktree plein
    en sparse — sûr pour le mainteneur.
    """
    if not _worktree_is_sparse(root):
        return False
    subprocess.run(
        ["git", "sparse-checkout", "add", f"sites/{site_slug}"],
        cwd=str(root), capture_output=True, text=True, check=False,
    )
    return True


def onboard_site(site_slug: str, base_path: Optional[Path] = None,
                   force: bool = False, no_sparse: bool = False) -> dict:
    """Crée le dossier site + l'entrée sites.json. Retourne un rapport.

    Lève ValueError si le site n'est pas au catalogue, ou existe déjà sans force.
    """
    root = base_path or _PROJECT_ROOT
    entry = load_catalog_entry(site_slug)
    if not entry:
        raise ValueError(
            f"'{site_slug}' absent du catalogue superprof_sites_catalog.json. "
            f"Vérifier l'id (ex: es-es-ressources, fr-fr-blog)."
        )

    site_dir = root / "sites" / site_slug
    cfg_path = site_dir / "config" / "site.json"
    if cfg_path.exists() and not force:
        raise ValueError(f"Site '{site_slug}' existe déjà ({cfg_path}). --force pour écraser.")

    # 1. Squelette de dossiers
    created = []
    for sub in ("config", "prompts", "linking_maps", "outputs"):
        d = site_dir / sub
        d.mkdir(parents=True, exist_ok=True)
        created.append(str(d.relative_to(root)))

    # 2. site.json pré-rempli
    cfg = build_site_config(entry)
    cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # 3. prompts/site.md placeholder
    site_md = site_dir / "prompts" / "site.md"
    if not site_md.exists():
        site_md.write_text(
            f"# {site_slug} — prompt site (à compléter)\n\n"
            f"Ton, blacklist, format WP spécifiques à ce site.\n"
            f"Déposer ici les guides éditoriaux du pays "
            f"({entry.get('language','')}, {entry.get('country','')}).\n",
            encoding="utf-8",
        )

    # 4. Entrée sites.json (merge additif, ne touche pas aux autres sites)
    added_to_registry = _add_to_sites_json(root, site_slug, entry)

    # 5. Sparse-checkout : matérialise le dossier du site sans exposer les autres.
    #    Sauté si --no-sparse, ou si le worktree n'est pas sparse (mainteneur).
    sparse_added = False if no_sparse else _sparse_add_site(root, site_slug)

    return {
        "site_slug": site_slug,
        "site_dir": str(site_dir.relative_to(root)),
        "dirs_created": created,
        "config": str(cfg_path.relative_to(root)),
        "registry_updated": added_to_registry,
        "sparse_added": sparse_added,
        "catalog_entry": entry,
    }


def _add_to_sites_json(root: Path, site_slug: str, entry: dict) -> bool:
    """Ajoute (ou laisse) l'entrée dans sites.json. True si ajouté, False si déjà là."""
    sites_path = root / "_shared" / "config" / "sites.json"
    data = json.loads(sites_path.read_text(encoding="utf-8")) if sites_path.exists() else {"sites": []}
    # "id" = clé legacy des sites.json écrits avant le renommage site_slug
    if any((s.get("site_slug") or s.get("id")) == site_slug for s in data.get("sites", [])):
        return False
    data.setdefault("sites", []).append({
        "site_slug": site_slug,
        "name": f"Superprof {entry.get('country','')} ({entry.get('type','')})".strip(),
        "domain": _domain_from_gsc(entry["gsc_property"]),
        "url_base": entry["gsc_property"],
        "gsc_property": entry["gsc_property"],
        "language": entry.get("language", ""),
        "active": True,
        "content_type": "blog_article",
        "subject_category": "education_general",
    })
    sites_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return True
