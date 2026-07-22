"""
Commandes de plan éditorial (content_plan.md).

Usage:
    cw plan check <url> --site superprof.fr-ressources

`plan check` valide *mécaniquement* le plan produit à l'étape 2bis de /refresh
(skill seo-outline) : hiérarchie des titres, couverture PAA, preuves. 100%
déterministe — aucun appel LLM/API. La rédaction du plan reste au subagent Max ;
cette commande ne fait que le noter (patron identique à `ytg qc` / `finalize`).
"""

import json
import re
import sys
from pathlib import Path
from typing import Optional

import click
from cli.options import blog_option

from scripts.audit.plan_validator import validate_plan


CONTEXT_DIR = Path.cwd() / "_shared" / "context"


def _slugify_url(url: str) -> str:
    slug = re.sub(r"[^a-z0-9]", "_", url.lower())
    return re.sub(r"_+", "_", slug).strip("_")


def _find_context_dir(url: str) -> Optional[Path]:
    """Résout le context_dir d'une URL (même stratégie que ytg._find_audit_file)."""
    candidate = CONTEXT_DIR / _slugify_url(url)
    if (candidate / "audit_data.json").exists():
        return candidate
    if not CONTEXT_DIR.exists():
        return None
    for d in CONTEXT_DIR.iterdir():
        if not d.is_dir():
            continue
        audit_file = d / "audit_data.json"
        if not audit_file.exists():
            continue
        try:
            data = json.loads(audit_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if data.get("url") == url:
            return d
    return None


@click.group()
def plan():
    """Plan éditorial (content_plan.md) : scaffold + validation SEO déterministe."""
    pass


_PLAN_TEMPLATE = """\
<!-- PLAN ÉDITORIAL — page : {url}

     Outline rédigé par l'agent via la skill `seo-outline`, puis validé par
     `cw plan check`. Le CLI a posé la structure + injecté les signaux ci-dessous ;
     il ne rédige AUCUNE phrase. Remplis les H2/H3, place les PAA et les preuves,
     supprime les commentaires au fur et à mesure.

     SIGNAUX (extraits de audit_data.json — à couvrir, pas à recopier tels quels) :
       Mot-clé principal : {main_keyword}
       Intention / action : {action}
       PAA à couvrir ({paa_count}) :
{paa_block}
       Secondary keywords : {secondary}
       Assets à préserver (Règle d'Or) : {assets}

     INVARIANTS (vérifiés par `cw plan check`) :
       - >= 3 H2, aucun H2 ni H3 orphelin
       - sous un H2 : 0 H3, ou >= 2 H3 (jamais un seul)
       - subdiviser en 2-4 H3 dès que le H2 dépasse ~150 mots ; max 4 H3/H2
       - `?` sur tout titre interrogatif
       - >= 3 liens sources institutionnels + >= 2 statistiques chiffrées, par H2
       - chaque PAA ci-dessus couverte par au moins une section

     STRUCTURE À RÉDIGER (≥ 3 H2). Écris chaque titre sur une ligne `## Titre`,
     puis son contenu dessous ; ajoute des `### Sous-titre` si le H2 dépasse
     ~150 mots. N'émets JAMAIS de `##` sans texte (heading vide = invalide). -->
"""


def _format_paa_block(paa_raw: str) -> tuple[str, int]:
    from scripts.audit.plan_validator import _split_terms
    terms = _split_terms(paa_raw)
    if not terms:
        return "    (aucune PAA collectée)", 0
    return "\n".join(f"    - {t}" for t in terms), len(terms)


@plan.command(name="init")
@click.argument("url")
@blog_option(required=True)
@click.option("--force", is_flag=True, help="Écrase un content_plan.md existant.")
def init(url: str, blog: str, force: bool):
    """
    Scaffold déterministe de content_plan.md au bon chemin.

    Crée le fichier dans le context_dir de l'URL, pré-rempli d'un template + des
    signaux (PAA, mot-clé, intent, assets) extraits de audit_data.json. Le CLI
    pose la STRUCTURE ; l'agent RÉDIGE ensuite l'outline via la skill seo-outline,
    puis `cw plan check` valide. Aucune phrase rédigée par le CLI (règle : la
    génération passe par le subagent Max, jamais l'API).
    """
    context_dir = _find_context_dir(url)
    if context_dir is None:
        click.echo(
            f"❌ Aucun context_dir pour {url}. Lance d'abord "
            f"`cw refresh {url} --site {blog}`.",
            err=True,
        )
        sys.exit(2)

    plan_file = context_dir / "content_plan.md"
    if plan_file.exists() and not force:
        click.echo(
            f"⚠️  {plan_file} existe déjà. --force pour l'écraser.", err=True)
        sys.exit(2)

    try:
        audit = json.loads((context_dir / "audit_data.json").read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        audit = {}

    paa_block, paa_count = _format_paa_block(audit.get("people_also_ask", "") or "")
    content = _PLAN_TEMPLATE.format(
        url=url,
        main_keyword=audit.get("main_keyword", "(inconnu)") or "(inconnu)",
        action=audit.get("action", "(inconnue)") or "(inconnue)",
        paa_count=paa_count,
        paa_block=paa_block,
        secondary=audit.get("secondary_keywords", "") or "(aucun)",
        assets=json.dumps(audit.get("assets_counts", {}), ensure_ascii=False),
    )
    plan_file.write_text(content, encoding="utf-8")

    click.echo(f"✅ Squelette créé : {plan_file}")
    click.echo(f"   {paa_count} PAA injectée(s) à couvrir.")
    click.echo(
        "   → Remplis l'outline via la skill `seo-outline`, puis "
        f"`cw plan check {url} --site {blog}`.")


@plan.command(name="check")
@click.argument("url")
@blog_option(required=True)
@click.option(
    "--plan-file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Chemin explicite du content_plan.md (sinon résolu depuis l'URL).",
)
@click.option("--json", "as_json", is_flag=True, help="Sortie JSON (scriptable).")
def check(url: str, blog: str, plan_file: Optional[Path], as_json: bool):
    """
    Valide un content_plan.md contre les invariants SEO (seo-outline).

    Verdict OK → passer à la génération. A_CORRIGER → corriger le plan (bon
    marché) avant de rédiger l'article. Code de sortie 1 si A_CORRIGER.
    """
    context_dir = _find_context_dir(url)
    paa_raw = ""

    if plan_file is None:
        if context_dir is None:
            click.echo(
                f"❌ Aucun context_dir trouvé pour {url}. "
                f"Lance d'abord `cw refresh {url} --site {blog}`.",
                err=True,
            )
            sys.exit(2)
        plan_file = context_dir / "content_plan.md"
        if not plan_file.exists():
            click.echo(
                f"❌ Pas de content_plan.md dans {context_dir}. "
                f"L'étape 2bis (skill seo-outline) ne l'a pas encore produit.",
                err=True,
            )
            sys.exit(2)

    # PAA : depuis l'audit résolu (si trouvé), sinon plan sans check de couverture.
    if context_dir is not None:
        try:
            audit = json.loads((context_dir / "audit_data.json").read_text(encoding="utf-8"))
            paa_raw = audit.get("people_also_ask", "") or ""
        except (json.JSONDecodeError, OSError):
            pass

    markdown = plan_file.read_text(encoding="utf-8")
    report = validate_plan(markdown, paa_raw=paa_raw)

    if as_json:
        click.echo(json.dumps({
            "verdict": report.verdict,
            "h2_count": report.h2_count,
            "paa_covered": report.paa_covered,
            "paa_total": report.paa_total,
            "source_links": report.source_links,
            "stats_found": report.stats_found,
            "violations": [
                {"rule": v.rule, "heading": v.heading, "message": v.message}
                for v in report.violations
            ],
        }, ensure_ascii=False, indent=2))
    else:
        _echo_human(report, plan_file)

    sys.exit(0 if report.ok else 1)


def _echo_human(report, plan_file: Path):
    icon = "✅" if report.ok else "⚠️"
    click.echo(f"{icon} Plan : {report.verdict}   ({plan_file})")
    click.echo(
        f"  H2: {report.h2_count}  |  PAA couvertes: "
        f"{report.paa_covered}/{report.paa_total}  |  "
        f"sources: {report.source_links}  |  stats: {report.stats_found}"
    )
    if report.violations:
        click.echo(f"\n  {len(report.violations)} manquement(s) à corriger :")
        for v in report.violations:
            where = f" [{v.heading}]" if v.heading else ""
            click.echo(f"  • ({v.rule}){where} {v.message}")
    else:
        click.echo("  Aucun manquement — prêt pour la génération.")
