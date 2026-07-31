"""La baseline de la Règle d'Or doit compter TOUTES les images du HTML.

Bug couvert (constaté en production le 2026-07-30, lot « Medium Potential ») :
`RefreshOrchestrator._extract_original_metrics()` dérivait `images_count` de
`HTMLAnalyzer.analyze(...).images`, une liste dont la featured image est
retirée (elle sert l'analyse éditoriale, pas la préservation des assets).

Sur ce corpus WordPress, les formules mathématiques sont rendues en images —
fichiers nommés par un hash SHA, dépourvus d'attribut `alt`. Un article de
22 images était annoncé à 10 au rédacteur, qui transcrivait les formules en
`<code>` et supprimait les images de bonne foi, en croyant respecter une
baseline qui était fausse. L'article « magnétostatique » a réellement perdu
12 images de cette façon.

Écarts mesurés sur le lot (audit → réel) : 10 → 22, 4 → 13, 6 → 10, 4 → 7.
"""

from scripts.agent.orchestrator import RefreshOrchestrator


def _img(src: str, alt: str | None = None) -> str:
    alt_attr = f' alt="{alt}"' if alt is not None else ""
    return f'<img src="{src}"{alt_attr}>'


# Formule rendue en image par l'éditeur : hash SHA, aucun `alt`.
FORMULA = _img("b5e2e02deeb051289c073e91d78681fb1bc1ddb4.png")
PHOTO = _img("champ-magnetique-boussole.jpg", "Une boussole")


class TestBaselineCountsEveryImage:

    def test_formula_images_are_counted(self):
        """Une formule en image compte autant qu'une photo : c'est un asset."""
        html = PHOTO + FORMULA
        assert RefreshOrchestrator._count_unique_images(html) == 2

    def test_image_without_alt_is_counted(self):
        """L'absence d'`alt` ne retire pas l'image du décompte."""
        assert RefreshOrchestrator._count_unique_images(_img("x.png")) == 1

    def test_featured_image_is_counted(self):
        """La featured image entre dans la baseline (contrairement à
        `HTMLAnalyzer.images`, qui l'exclut pour l'analyse éditoriale)."""
        html = (
            '<figure class="wp-post-image"><img src="une.jpg" alt="A la une"></figure>'
            + PHOTO
        )
        assert RefreshOrchestrator._count_unique_images(html) == 2

    def test_duplicate_src_counted_once(self):
        """Déduplication par `src` : sans elle, un doublon dans l'original
        rendrait `assets_after >= assets_before` impossible à satisfaire sans
        dupliquer aussi à la sortie."""
        html = PHOTO + FORMULA + FORMULA
        assert RefreshOrchestrator._count_unique_images(html) == 2

    def test_empty_html_is_zero(self):
        assert RefreshOrchestrator._count_unique_images("") == 0
        assert RefreshOrchestrator._count_unique_images(None) == 0

    def test_img_without_src_is_ignored(self):
        """Une balise sans `src` n'est pas un asset récupérable."""
        assert RefreshOrchestrator._count_unique_images('<img alt="vide">') == 0

    def test_regression_magnetostatique(self):
        """Le cas réel : 10 annoncées, 22 présentes.

        2 photos nommées + 20 formules en hash. L'ancien compteur en voyait 10,
        ce qui a coûté 12 images à l'article avant restauration manuelle.
        """
        html = "".join(
            [_img(f"photo-{i}.jpg", f"photo {i}") for i in range(2)]
            + [_img(f"{i:040x}.png") for i in range(20)]
        )
        assert RefreshOrchestrator._count_unique_images(html) == 22
