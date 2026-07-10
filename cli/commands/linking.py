"""
Commandes de maillage interne automatisé (enseigna).

Pose sur les articles avis enseigna :
  - un lien Superprof (superprof.fr) en rotation home/landing ville,
  - un à deux liens internes avis <-> avis,
sans lien concurrent et sans jamais dupliquer une URL enseigna dans la page.

Usage :
    cw linking avis            # dry-run (aucune écriture) sur tous les articles
    cw linking avis --apply    # applique (backup .backup.html + rapport JSON)
    cw linking avis --url https://enseigna.fr/busuu-avis-apprentissage-litalien/
"""

import logging

import click


@click.group()
def linking():
    """Maillage interne automatisé."""
    pass


def _print_results(results, linker):
    added = upg = sib = 0
    for r in results:
        if not r.file:
            continue
        fam = linker.family_of(r.url)
        status = "OK" if r.validation_passed else "FAIL"
        click.echo(
            f"\n{r.url}  [{fam}]  liens {r.internal_before}->{r.internal_after}  {status}"
        )
        if r.error:
            click.echo(f"    ERREUR: {r.error}")
        for a in r.links_added:
            kind = {
                "superprof": "SP-new",
                "superprof_upgrade": "SP-upgrade",
                "sibling": "avis<->avis",
            }.get(a["kind"], a["kind"])
            click.echo(f"    + [{kind:11}] {a['anchor']!r} -> {a['url']}")
            added += a["kind"] == "superprof"
            upg += a["kind"] == "superprof_upgrade"
            sib += a["kind"] == "sibling"
        for s in r.links_skipped:
            click.echo(f"    ~ SKIP [{s['kind']}] {s['url']} ({s['reason']})")

    resolved = sum(1 for r in results if r.file)
    click.echo("\n" + "=" * 70)
    click.echo(
        f"Articles traités : {resolved}/{len(results)} | "
        f"Superprof : {added + upg} ({upg} upgrades) | avis<->avis : {sib}"
    )


@linking.command()
@click.option("--apply", "apply_", is_flag=True, help="Écrit les fichiers (sinon dry-run).")
@click.option("--url", "urls", multiple=True, help="Limiter à une/des URL(s) précise(s).")
@click.option("-v", "--verbose", is_flag=True, help="Logs détaillés.")
def avis(apply_, urls, verbose):
    """Maillage des articles avis enseigna (Superprof rotator + avis<->avis)."""
    from scripts.linking.enseigna_avis_linker import EnseignaAvisLinker

    logging.basicConfig(
        level=logging.INFO if verbose else logging.WARNING,
        format="%(message)s",
    )
    if not verbose:
        # Le validator logue chaque succès en INFO ; on le tait hors --verbose.
        logging.getLogger("scripts.linking.injection_validator").setLevel(
            logging.ERROR
        )

    linker = EnseignaAvisLinker()
    mode = "APPLY (écriture)" if apply_ else "DRY-RUN (aucune écriture)"
    click.echo(f"Mode : {mode}")

    results = linker.process(urls=list(urls) or None, dry_run=not apply_)
    _print_results(results, linker)

    if apply_:
        click.echo(
            "\nRapport : _shared/outputs/enseigna/json/avis_linking_report.json"
        )
        click.echo("Backups : {slug}_refreshed.gutenberg.backup.html")
    else:
        click.echo("\n(dry-run — relancer avec --apply pour écrire)")
