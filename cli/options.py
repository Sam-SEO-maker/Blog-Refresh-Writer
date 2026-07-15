"""
Options CLI partagées (click).

`--market` est l'alias canonique multi-tenant de `--blog` (Phase 6a). Les deux
pointent vers le même paramètre `blog_id` : un collaborateur n'a qu'un seul
identifiant marché à connaître (`fr-enseigna`, `es-apuntes`, `br-blog`…), qui
résout vers l'entrée `sites.json` correspondante. `--blog` reste accepté pour
rétro-compatibilité.

Usage :

    from cli.options import blog_option

    @click.command()
    @click.argument('url')
    @blog_option(required=True)
    def refresh(url, blog, ...):
        ...

Le nom du paramètre reçu par la fonction reste `blog` (dest inchangé), donc
aucune signature de commande n'a besoin d'être modifiée.
"""

import click


def blog_option(required=False, help=None, dest="blog"):
    """Décorateur ajoutant `--blog`/`--market` (alias) sur une commande click.

    Args:
        required: passe l'option en obligatoire.
        help: texte d'aide ; défaut adapté au caractère requis/optionnel.
        dest: nom du paramètre reçu par la fonction (`blog` ou `blog_id` selon
            la convention du call site — on préserve l'existant).
    """
    if help is None:
        help = (
            "ID marché / blog (ex: enseigna, es-apuntes). Alias : --market."
            if required
            else "Filtrer par ID marché / blog. Alias : --market."
        )
    return click.option(
        "--blog",
        "--market",
        dest,
        required=required,
        help=help,
    )
