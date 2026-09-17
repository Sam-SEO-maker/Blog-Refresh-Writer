"""Commande `seo-tags` — génère title / H1 / meta description pour tout un onglet.

Automatise le parcours manuel du backoffice WP (copier le KW depuis la Sheet,
coller dans l'outil, generate, choisir, enregistrer), répété trois fois par
article. Le générateur est celui du backoffice lui-même, pas une IA tierce :
la sortie reste comparable à ce que produit l'écran d'admin.

La cascade imposée par le plugin est reproduite à l'identique :
title (mot-clé principal, colonne B) → H1 (mot-clé secondaire, colonne C) →
meta description (exige les deux précédents).

Rien n'est écrit sans le demander. Par défaut la commande génère et affiche ;
`--write-sheet` remplit les colonnes de l'onglet, `--push-wp` pousse title et
meta description dans SEOPress. Le H1 n'est jamais poussé en meta : côté
Superprof c'est le premier bloc Gutenberg du corps, que seul un refresh
réécrit.

Usage :
    cw seo-tags --site superprof.fr-ressources --tab "Medium Potential" --limit 5
    cw seo-tags --site superprof.fr-ressources --tab "Medium Potential" --limit 50 --write-sheet
    cw seo-tags --site superprof.fr-ressources --tab "Medium Potential" --rows 12-40 --write-sheet --push-wp
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

import click
from dotenv import load_dotenv

from cli.options import site_option
from scripts.seo.seo_tags import (
    STEP_H1,
    STEP_META,
    STEP_TITLE,
    STEPS,
    SeoTagGenerator,
    acronym_casing,
    generate_row,
    push_to_seopress,
    read_rows,
    resolve_tab,
    write_sheet,
)

_LABEL = {STEP_TITLE: "Title", STEP_H1: "H1", STEP_META: "Meta description"}


def _parse_rows(spec: str) -> tuple[int, int]:
    m = re.match(r"^(\d+)\s*-\s*(\d+)$", spec.strip())
    if not m:
        raise click.BadParameter("format attendu : --rows 140-180 (numéros affichés par Sheets)")
    a, b = int(m.group(1)), int(m.group(2))
    if a > b:
        raise click.BadParameter("borne de début supérieure à la borne de fin")
    return a, b


@click.command(name="seo-tags")
@site_option(required=True, dest="site_slug")
@click.option("--tab", "tab_name", required=True,
              help="Onglet de la Sheet, nom EXACT tel que déclaré dans sheets.tabs "
                   "(le layout des colonnes diffère d'un onglet à l'autre).")
@click.option("--limit", type=int, default=10, show_default=True,
              help="Nombre d'articles traités (0 = tout l'onglet). Chaque article "
                   "coûte 3 appels au générateur.")
@click.option("--rows", "rows_spec", default=None,
              help="Restreindre à une plage de lignes, numéros affichés par Sheets "
                   "(en-têtes comprises), ex. 140-180. Filtre avant --limit.")
@click.option("--status", "statuses", default="a faire,à faire", show_default=True,
              help="Statuts éligibles, séparés par des virgules. Vide = ignorer le statut.")
@click.option("--all-rows", "all_rows", is_flag=True, default=False,
              help="Traiter aussi les lignes dont les balises sont déjà renseignées "
                   "(par défaut elles sont laissées intactes : un choix humain ne "
                   "s'écrase pas).")
@click.option("--write-sheet", "write_sheet_flag", is_flag=True, default=False,
              help="Écrire les balises retenues dans les colonnes de l'onglet.")
@click.option("--push-wp", "push_wp", is_flag=True, default=False,
              help="Pousser title + meta description dans SEOPress (meta SEO uniquement).")
@click.option("--push-h1", "push_h1", is_flag=True, default=False,
              help="Pousser aussi le H1, qui vit dans le CORPS de l'article : "
                   "seul le texte entre <h1> et </h1> est remplacé, le reste "
                   "est intact, et le corps d'origine est sauvegardé dans "
                   "wp_backups/. Refusé sur un article déjà passé par le "
                   "pipeline (H1 en bloc Gutenberg). Implique --push-wp.")
@click.option("--json-out", "json_out", default=None,
              help="Écrire le détail (5 propositions par étape, rejets, erreurs) en JSON.")
def seo_tags(site_slug, tab_name, limit, rows_spec, statuses, all_rows,
             write_sheet_flag, push_wp, push_h1, json_out):
    """Génère les balises SEO d'un onglet via l'outil IA du backoffice WP."""
    load_dotenv()
    base = Path.cwd()

    status_set = {s.strip().lower() for s in statuses.split(",") if s.strip()}
    if push_h1:
        push_wp = True  # le H1 ne se pousse pas sans les autres balises

    click.echo(f"\n{'=' * 70}")
    click.echo("GENERATION DES BALISES SEO (outil backoffice WP)")
    click.echo(f"{'=' * 70}")
    click.echo(f"Site   : {site_slug}")
    click.echo(f"Onglet : {tab_name}")

    # 1. Layout de l'onglet — refus tôt si les colonnes de sortie manquent.
    try:
        tab = resolve_tab(site_slug, tab_name, base_path=base)
    except ValueError as e:
        click.echo(f"\n[ERREUR] {e}")
        raise SystemExit(1)

    if write_sheet_flag and any(tab.get(k) is None for k in ("col_title", "col_h1", "col_metadesc")):
        click.echo(
            f"\n[ERREUR] L'onglet {tab_name!r} ne déclare pas col_title / col_h1 / "
            f"col_metadesc dans sheets.tabs : impossible de savoir où écrire.\n"
            f"         Ajoute-les au site.json avant d'utiliser --write-sheet."
        )
        raise SystemExit(1)

    # 2. Lecture des lignes éligibles.
    from _shared.core.sheets_config import get_spreadsheet_id
    from scripts.sheets.sheets_client import SheetsClient

    spreadsheet_id = get_spreadsheet_id(site_slug)
    client = SheetsClient(spreadsheet_id)

    rows = read_rows(client, tab, tab_name, status_set, only_missing=not all_rows)

    if rows_spec:
        lo, hi = _parse_rows(rows_spec)
        rows = [r for r in rows if lo <= r.row <= hi]
        click.echo(f"Plage  : lignes {lo}-{hi}")

    eligible = [r for r in rows if not r.skipped]
    if limit:
        eligible = eligible[:limit]

    click.echo(f"Lignes : {len(eligible)} à traiter"
               + (f" (statuts : {', '.join(sorted(status_set))})" if status_set else ""))
    if not eligible:
        click.echo("\nRien à faire.")
        return

    click.echo(f"Appels : {len(eligible) * 3} générations (3 par article)")
    click.echo(f"Écriture : Sheet={'oui' if write_sheet_flag else 'non'} · "
               f"WP={'oui' if push_wp else 'non'}"
               + (" (+ H1 dans le corps)" if push_h1 else ""))

    # 3. La cascade, article par article.
    gen = _build_generator(site_slug, base)
    wp = _build_wp_client(site_slug, base)

    click.echo(f"\n{'-' * 70}")
    done = []
    for i, r in enumerate(eligible, 1):
        slug = r.url.rstrip("/").rsplit("/", 1)[-1]
        click.echo(f"\n[{i}/{len(eligible)}] ligne {r.row} · {slug[:52]}")
        click.echo(f"   KW principal : {r.main_keyword or '(absent)'}")
        click.echo(f"   KW secondaire: {r.secondary_keyword or '(absent)'}")

        # La casse des sigles vient de l'article, pas de la Sheet : « ali » y
        # est saisi en minuscules alors que le corps écrit « ALI » 29 fois.
        casing = {}
        if wp:
            post = wp.get_post_by_url(r.url)
            if post:
                body = post.get("raw") or ""
                casing = acronym_casing(body, f"{r.main_keyword} {r.secondary_keyword}")
                if casing:
                    click.echo("   Casse article : "
                               + ", ".join(f"{k} → {v}" for k, v in casing.items()))

        r.steps = generate_row(gen, r.main_keyword, r.secondary_keyword, casing=casing)
        for step in STEPS:
            s = r.steps.get(step)
            if not s:
                click.echo(f"   {_LABEL[step]:<17}: — (étape non atteinte)")
                continue
            if s.chosen:
                click.echo(f"   {_LABEL[step]:<17}: {s.chosen}")
                if s.fallback_from:
                    click.echo(f"   {'':<17}  (rejoué sur le KW principal : "
                               f"« {s.fallback_from} » donnait un titre fautif)")
                for opt, why in s.rejected:
                    click.echo(f"   {'':<17}  écarté ({why}) : {opt[:60]}")
            else:
                click.echo(f"   {_LABEL[step]:<17}: ECHEC — {s.error or 'aucune proposition conforme'}")
                for opt, why in s.rejected:
                    click.echo(f"   {'':<17}  écarté ({why}) : {opt[:60]}")
        done.append(r)

    # 4. Bilan.
    full = [r for r in done if r.ok]
    click.echo(f"\n{'=' * 70}")
    click.echo(f"BILAN : {len(full)}/{len(done)} articles avec les 3 balises")
    partial = [r for r in done if not r.ok]
    if partial:
        click.echo(f"        {len(partial)} incomplet(s) :")
        for r in partial:
            missing = [_LABEL[s] for s in STEPS if not r.value(s)]
            first_err = next((r.steps[s].error for s in STEPS
                              if r.steps.get(s) and r.steps[s].error), None)
            click.echo(f"          ligne {r.row} — manque {', '.join(missing)}"
                       + (f" ({first_err})" if first_err else ""))

    # 5. Écritures, seulement si demandées.
    if write_sheet_flag:
        # On écrit aussi les lignes partielles : une balise juste vaut mieux
        # qu'une cellule vide, et la relecture verra ce qui manque.
        n = write_sheet(client, tab, tab_name, done)
        click.echo(f"\nSheet : {n} cellules écrites dans {tab_name!r}")

    if push_wp:
        if not full:
            click.echo("\nWP : rien à pousser (aucun article complet).")
        else:
            res = push_to_seopress(site_slug, full, base_path=base, with_h1=push_h1)
            ok = sum(1 for x in res if x["ok"])
            what = "title + meta description" + (" + H1" if push_h1 else "")
            click.echo(f"\nWP : {ok}/{len(res)} articles mis à jour ({what})")
            for x in res:
                if not x["ok"]:
                    click.echo(f"      ECHEC {x['url'][:60]} — {x.get('error')}")
                elif push_h1 and x.get("h1") and not x["h1"].startswith("ok"):
                    # Les meta sont passées, le H1 non : il reste à poser à la
                    # main, et la raison dit laquelle des structures a bloqué.
                    click.echo(f"      H1 NON poussé ({x['h1']}) : {x['url'][:56]}")
            if not push_h1:
                click.echo("      H1 non poussé (il vit dans le corps) : --push-h1 pour l'inclure.")

    if json_out:
        out = Path(json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "site": site_slug,
            "tab": tab_name,
            "articles": [
                {
                    "url": r.url, "row": r.row,
                    "main_keyword": r.main_keyword,
                    "secondary_keyword": r.secondary_keyword,
                    "complete": r.ok,
                    "steps": {
                        s: {
                            "keyword": r.steps[s].keyword,
                            "chosen": r.steps[s].chosen,
                            "options": r.steps[s].options,
                            "rejected": [{"text": t, "why": w} for t, w in r.steps[s].rejected],
                            "error": r.steps[s].error,
                            "fallback_from": r.steps[s].fallback_from,
                        }
                        for s in STEPS if r.steps.get(s)
                    },
                }
                for r in done
            ],
        }
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        click.echo(f"\nJSON : {out}")

    if not write_sheet_flag and not push_wp:
        click.echo("\n(dry-run : rien n'a été écrit. --write-sheet / --push-wp pour enregistrer)")


def _build_wp_client(site_slug: str, base: Path):
    """Client WP REST pour lire le corps des articles (casse des sigles).

    Optionnel : sans lui on génère quand même, les balises reprennent
    simplement la casse de la Sheet.
    """
    try:
        from scripts.utils.push_to_wp import build_client

        return build_client(site_slug, base_path=base)
    except Exception as e:
        click.echo(f"\n[AVERTISSEMENT] Lecture WP indisponible ({type(e).__name__}) : "
                   f"la casse des sigles ne sera pas corrigée.")
        return None


def _build_generator(site_slug: str, base: Path) -> SeoTagGenerator:
    """Client du générateur, construit sur le bloc `wp_api_config` du site."""
    from _shared.core.site_paths import SitePaths

    tp = SitePaths(base_path=base)
    cfg = json.loads(tp.site_config(site_slug).read_text(encoding="utf-8"))
    wp = cfg.get("wp_api_config")
    if not wp:
        click.echo(f"\n[ERREUR] Le site {site_slug} n'a pas de bloc 'wp_api_config'.")
        raise SystemExit(1)
    try:
        return SeoTagGenerator(
            api_base_url=wp["api_base_url"],
            user_env_var=wp["user_env_var"],
            password_env_var=wp["password_env_var"],
            timeout=wp.get("timeout", 30) * 4,  # la génération IA est lente
        )
    except ValueError as e:
        click.echo(f"\n[ERREUR] {e}")
        raise SystemExit(1)
