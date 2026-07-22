"""
Options CLI partagées (click).

`--site` est l'option canonique multi-site. `--blog` reste accepté comme alias
de rétro-compatibilité : les deux pointent vers le même paramètre. Un
collaborateur n'a qu'un seul identifiant à connaître (le site slug, ex:
`enseigna`, `superprof.fr-ressources`), qui résout vers l'entrée `sites.json`
correspondante.

Usage :

    from cli.options import site_option

    @click.command()
    @click.argument('url')
    @site_option(required=True)
    def refresh(url, blog, ...):
        ...

Le nom du paramètre reçu par la fonction reste `blog` (dest inchangé), donc
aucune signature de commande n'a besoin d'être modifiée.
"""

import click

from _shared.core.constants import canonical_site_slug


def _canonicalize(ctx, param, value):
    return canonical_site_slug(value)


def site_option(required=False, help=None, dest="blog"):
    """Décorateur ajoutant `--site` (alias legacy : `--blog`) sur une commande click.

    Args:
        required: passe l'option en obligatoire.
        help: texte d'aide ; défaut adapté au caractère requis/optionnel.
        dest: nom du paramètre reçu par la fonction (`blog` ou `site_slug` selon
            la convention du call site — on préserve l'existant).
    """
    if help is None:
        help = (
            "Site slug (e.g. enseigna, superprof.fr-ressources). Alias: --blog."
            if required
            else "Filter by site slug. Alias: --blog."
        )
    return click.option(
        "--site",
        "--blog",
        dest,
        required=required,
        help=help,
        callback=_canonicalize,
    )


# Alias legacy pour les imports existants.
blog_option = site_option
