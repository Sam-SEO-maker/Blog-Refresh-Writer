"""Comparaison d'images : les deux membres doivent être mesurés à la même aune.

Bug couvert (constaté en production le 2026-07-28, article « design d'objet ») :
`AssetManager.validate()` comparait un baseline produit par
`ContentExtractor._extract_assets_baseline()` — qui compte **toutes** les images
WordPress, image à la Une comprise — à un décompte obtenu via
`extract_assets(exclude_featured_image=True)`, qui l'exclut.

L'écart d'une unité était systématique dès qu'un article avait une image à la
Une, donc en pratique sur tous : `cw finalize` affichait « ⚠ missing assets NOT
restorable » à chaque refresh alors qu'aucune image n'avait été perdue. Une
alerte qui se déclenche toujours finit ignorée — et c'est précisément celle qui
garde la Règle d'Or (`assets_after >= assets_before`).
"""

from scripts.assets.asset_manager import AssetManager


def _figure(n: int) -> str:
    return (
        f'<figure class="wp-block-image">'
        f'<img class="wp-image-{n}" src="img{n}.jpg" alt="img {n}">'
        f"</figure>"
    )


SUPERPROF_LINK = '<p><a href="https://www.superprof.fr/cours-dessin.html">un prof</a></p>'


class TestFeaturedImageAsymmetry:

    def test_identical_content_is_valid(self):
        """Le cas qui remontait un faux positif à chaque refresh."""
        html = _figure(1) + _figure(2) + _figure(3) + SUPERPROF_LINK
        result = AssetManager().validate(
            original_assets={"counts": {}},
            new_content=html,
            original_content=html,
        )
        assert result.is_valid, f"faux positif : {result.errors}"

    def test_stale_baseline_count_does_not_trigger_false_positive(self):
        """Un baseline « toutes images » ne doit plus contredire l'original réel.

        C'est exactement la forme du bug : counts.images=3 (featured incluse)
        contre 2 images contextuelles réellement présentes de part et d'autre.
        """
        html = _figure(1) + _figure(2) + _figure(3) + SUPERPROF_LINK
        result = AssetManager().validate(
            original_assets={"counts": {"images": 3}},
            new_content=html,
            original_content=html,
        )
        assert result.is_valid, f"faux positif : {result.errors}"

    def test_real_image_loss_is_still_detected(self):
        """Le correctif ne doit pas rendre le garde-fou aveugle."""
        original = _figure(1) + _figure(2) + _figure(3) + SUPERPROF_LINK
        degraded = _figure(1) + _figure(2) + SUPERPROF_LINK
        result = AssetManager().validate(
            original_assets={"counts": {}},
            new_content=degraded,
            original_content=original,
        )
        assert not result.is_valid
        assert any("mages" in e for e in result.errors)

    def test_added_images_are_valid(self):
        """assets_after >= assets_before : ajouter est permis."""
        original = _figure(1) + _figure(2) + SUPERPROF_LINK
        enriched = _figure(1) + _figure(2) + _figure(3) + SUPERPROF_LINK
        result = AssetManager().validate(
            original_assets={"counts": {}},
            new_content=enriched,
            original_content=original,
        )
        assert result.is_valid, result.errors

    def test_falls_back_to_baseline_without_original(self):
        """Sans original_content, le compteur transmis reste la seule référence."""
        result = AssetManager().validate(
            original_assets={"counts": {"images": 99}},
            new_content=_figure(1) + SUPERPROF_LINK,
            original_content=None,
        )
        assert not result.is_valid
