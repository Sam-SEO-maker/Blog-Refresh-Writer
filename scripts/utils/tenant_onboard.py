"""Onboarding d'un tenant depuis le catalogue Superprof (Phase 6d).

`cw tenant init <id>` matérialise un tenant :
  1. crée le squelette `tenants/{id}/` (config/tenant.json pré-rempli + prompts/,
     linking_maps/, outputs/) ;
  2. ajoute une entrée dans `_shared/config/sites.json` (registre runtime).

Le pré-remplissage vient du catalogue `superprof_blogs_catalog.json` (gsc_property,
url_base, langue, pays). Les champs éditoriaux (ton, blacklist, guides) restent des
TODO explicites à compléter par le responsable pays — c'est là qu'il « charge ses
fichiers » (prompts/site.md, guides).

Idempotent et sûr : refuse d'écraser un tenant existant sans --force.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CATALOG_PATH = _PROJECT_ROOT / "_shared" / "config" / "superprof_blogs_catalog.json"
SITES_JSON = _PROJECT_ROOT / "_shared" / "config" / "sites.json"


def load_catalog_entry(tenant_id: str) -> Optional[dict]:
    """Cherche `tenant_id` dans le catalogue (ressources + blogs)."""
    if not CATALOG_PATH.exists():
        return None
    cat = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    for entry in cat.get("ressources_sites", []) + cat.get("blogs", []):
        if entry.get("tenant_id") == tenant_id:
            return entry
    return None


def _domain_from_gsc(gsc_property: str) -> str:
    # https://www.superprof.es/apuntes/ → superprof.es
    core = gsc_property.split("//", 1)[-1].split("/", 1)[0]
    return core[4:] if core.startswith("www.") else core


def build_tenant_config(entry: dict) -> dict:
    """Squelette tenant.json pré-rempli depuis le catalogue. Éditorial = TODO."""
    tid = entry["tenant_id"]
    gsc = entry["gsc_property"]
    return {
        "blog_id": tid,
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
        "_TODO": (
            "Compléter par le responsable pays : tone_profile, seo_settings, "
            "editorial_guides (déposer prompts/site.md + guides dans ce dossier), "
            "sheets, wp_api_config, brand_rules. Voir tenants/superprof-ressources "
            "comme modèle Ressources."
        ),
    }


def onboard_tenant(tenant_id: str, base_path: Optional[Path] = None,
                   force: bool = False) -> dict:
    """Crée le dossier tenant + l'entrée sites.json. Retourne un rapport.

    Lève ValueError si le tenant n'est pas au catalogue, ou existe déjà sans force.
    """
    root = base_path or _PROJECT_ROOT
    entry = load_catalog_entry(tenant_id)
    if not entry:
        raise ValueError(
            f"'{tenant_id}' absent du catalogue superprof_blogs_catalog.json. "
            f"Vérifier l'id (ex: es-es-ressources, fr-fr-blog)."
        )

    tenant_dir = root / "tenants" / tenant_id
    cfg_path = tenant_dir / "config" / "tenant.json"
    if cfg_path.exists() and not force:
        raise ValueError(f"Tenant '{tenant_id}' existe déjà ({cfg_path}). --force pour écraser.")

    # 1. Squelette de dossiers
    created = []
    for sub in ("config", "prompts", "linking_maps", "outputs"):
        d = tenant_dir / sub
        d.mkdir(parents=True, exist_ok=True)
        created.append(str(d.relative_to(root)))

    # 2. tenant.json pré-rempli
    cfg = build_tenant_config(entry)
    cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # 3. prompts/site.md placeholder
    site_md = tenant_dir / "prompts" / "site.md"
    if not site_md.exists():
        site_md.write_text(
            f"# {tenant_id} — prompt site (à compléter)\n\n"
            f"Ton, blacklist, format WP spécifiques à ce tenant.\n"
            f"Déposer ici les guides éditoriaux du pays "
            f"({entry.get('language','')}, {entry.get('country','')}).\n",
            encoding="utf-8",
        )

    # 4. Entrée sites.json (merge additif, ne touche pas aux autres tenants)
    added_to_registry = _add_to_sites_json(root, tenant_id, entry)

    return {
        "tenant_id": tenant_id,
        "tenant_dir": str(tenant_dir.relative_to(root)),
        "dirs_created": created,
        "config": str(cfg_path.relative_to(root)),
        "registry_updated": added_to_registry,
        "catalog_entry": entry,
    }


def _add_to_sites_json(root: Path, tenant_id: str, entry: dict) -> bool:
    """Ajoute (ou laisse) l'entrée dans sites.json. True si ajouté, False si déjà là."""
    sites_path = root / "_shared" / "config" / "sites.json"
    data = json.loads(sites_path.read_text(encoding="utf-8")) if sites_path.exists() else {"sites": []}
    if any(s.get("id") == tenant_id for s in data.get("sites", [])):
        return False
    data.setdefault("sites", []).append({
        "id": tenant_id,
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
