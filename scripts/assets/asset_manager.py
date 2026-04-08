"""
Asset Manager Module

Extraction, préservation et restauration des assets.
"""

import re
from typing import Optional

from _shared.core.models import AssetValidationResult
from _shared.core.constants import BLACKLIST_DOMAINS, SUPERPROF_DOMAIN
from _shared.core.utils.year_updater import YearUpdater


class AssetManager:
    """
    Gestionnaire d'assets pour la réécriture.

    Responsabilités:
    - Extraire les assets du contenu original
    - Valider que les assets sont préservés après réécriture
    - Restaurer les assets manquants si nécessaire
    - Détecter les liens vers des concurrents blacklistés
    """

    def __init__(self):
        """Initialise le gestionnaire d'assets."""
        pass

    def extract_assets(self, html_content: str, exclude_featured_image: bool = True) -> dict:
        """
        Extrait tous les assets d'un contenu HTML.

        Args:
            html_content: Contenu HTML
            exclude_featured_image: Si True, exclut la featured image du comptage

        Returns:
            Dictionnaire des assets extraits
        """
        all_images = self._extract_images(html_content)
        links = self._extract_links(html_content)
        cta_blocks = self._extract_cta_blocks(html_content)

        # Identifier et exclure la featured image si demandé
        featured_image = None
        images = all_images
        if exclude_featured_image and all_images:
            # La featured image est généralement la première grande image
            featured_image = self._identify_featured_image(all_images, html_content)
            if featured_image:
                images = [img for img in all_images if img.get("src") != featured_image.get("src")]

        # Séparer les types de liens
        internal_links = [l for l in links if l.get("type") == "internal"]
        external_links = [l for l in links if l.get("type") == "external"]
        superprof_links = [l for l in links if l.get("type") == "superprof"]

        return {
            "featured_image": featured_image,  # Image à la Une (séparée)
            "images": images,  # Images contextuelles uniquement
            "internal_links": internal_links,
            "external_links": external_links,
            "superprof_link": superprof_links[0] if superprof_links else None,
            "cta_blocks": cta_blocks,  # Blocs CTA stylés
            "counts": {
                "images": len(images),  # Sans featured image
                "internal_links": len(internal_links),
                "external_links": len(external_links),
                "superprof_links": len(superprof_links),
                "cta_blocks": len(cta_blocks),
            }
        }

    def _identify_featured_image(self, images: list[dict], html: str) -> Optional[dict]:
        """
        Identifie l'image à la Une parmi les images extraites.

        Args:
            images: Liste des images
            html: Contenu HTML pour analyse de position

        Returns:
            L'image featured ou None
        """
        if not images:
            return None

        first_img = images[0]

        # Heuristique: la première image avec width >= 800 est probablement la featured
        width_match = re.search(r'width=["\']?(\d+)', first_img.get("html", ""), re.I)
        if width_match and int(width_match.group(1)) >= 800:
            return first_img

        # Ou si c'est la première image juste après le H1
        h1_match = re.search(r'<h1[^>]*>', html, re.I)
        if h1_match:
            h1_pos = h1_match.end()
            first_img_match = re.search(re.escape(first_img.get("html", "")[:30]), html)
            if first_img_match and first_img_match.start() < h1_pos + 1000:
                return first_img

        return None

    def _extract_cta_blocks(self, html: str) -> list[dict]:
        """
        Extrait les blocs CTA stylés.

        Args:
            html: Contenu HTML

        Returns:
            Liste des blocs CTA
        """
        cta_blocks = []

        # Pattern 1: CTA bouton Superprof (paragraphe centré avec lien stylé)
        superprof_cta_pattern = r'(<p[^>]*style="[^"]*text-align:\s*center[^"]*"[^>]*>.*?<a[^>]*style="[^"]*background-color[^"]*"[^>]*>.*?</a>.*?</p>)'
        for match in re.finditer(superprof_cta_pattern, html, re.I | re.S):
            cta_blocks.append({
                "html": match.group(1),
                "type": "superprof_button",
                "required": True
            })

        # Pattern 2: Bloc définition (div avec border-left)
        definition_pattern = r'(<div[^>]*style="[^"]*border-left[^"]*"[^>]*>.*?</div>)'
        for match in re.finditer(definition_pattern, html, re.I | re.S):
            cta_blocks.append({
                "html": match.group(1),
                "type": "definition_box",
                "required": False
            })

        return cta_blocks

    def _extract_images(self, html: str) -> list[dict]:
        """Extrait toutes les images avec leurs captions (figure/figcaption, wp-caption)."""
        images = []

        # Pattern 1: <figure> wrapping <img> + <figcaption>
        figure_pattern = r'<figure[^>]*>(.*?)</figure>'
        figure_srcs = set()
        for match in re.finditer(figure_pattern, html, re.I | re.S):
            figure_html = match.group(0)
            inner = match.group(1)

            src_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', inner, re.I)
            if not src_match:
                continue
            src = src_match.group(1)
            figure_srcs.add(src)

            alt_match = re.search(r'alt=["\']([^"\']*)["\']', inner, re.I)
            alt = alt_match.group(1) if alt_match else ""

            caption = ""
            cap_match = re.search(r'<figcaption[^>]*>(.*?)</figcaption>', inner, re.I | re.S)
            if cap_match:
                caption = re.sub(r'<[^>]+>', '', cap_match.group(1)).strip()

            images.append({
                "html": figure_html,
                "src": src,
                "alt": alt,
                "caption": caption,
            })

        # Pattern 2: WordPress wp-caption div
        wp_pattern = r'<div[^>]*class="[^"]*wp-caption[^"]*"[^>]*>(.*?)</div>'
        for match in re.finditer(wp_pattern, html, re.I | re.S):
            wp_html = match.group(0)
            inner = match.group(1)

            src_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', inner, re.I)
            if not src_match:
                continue
            src = src_match.group(1)
            if src in figure_srcs:
                continue
            figure_srcs.add(src)

            alt_match = re.search(r'alt=["\']([^"\']*)["\']', inner, re.I)
            alt = alt_match.group(1) if alt_match else ""

            caption = ""
            cap_match = re.search(r'<p[^>]*class="[^"]*wp-caption-text[^"]*"[^>]*>(.*?)</p>', inner, re.I | re.S)
            if cap_match:
                caption = re.sub(r'<[^>]+>', '', cap_match.group(1)).strip()

            images.append({
                "html": wp_html,
                "src": src,
                "alt": alt,
                "caption": caption,
            })

        # Pattern 3: standalone <img> tags (not already captured in figure/wp-caption)
        img_pattern = r'<img[^>]+>'
        for match in re.finditer(img_pattern, html, re.I):
            img_tag = match.group(0)

            src_match = re.search(r'src=["\']([^"\']+)["\']', img_tag, re.I)
            src = src_match.group(1) if src_match else ""

            if not src or src in figure_srcs:
                continue

            alt_match = re.search(r'alt=["\']([^"\']*)["\']', img_tag, re.I)
            alt = alt_match.group(1) if alt_match else ""

            images.append({
                "html": img_tag,
                "src": src,
                "alt": alt,
                "caption": "",
            })

        return images

    def _extract_links(self, html: str) -> list[dict]:
        """Extrait tous les liens."""
        links = []
        pattern = r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>'

        for match in re.finditer(pattern, html, re.I | re.S):
            href = match.group(1)
            anchor = re.sub(r'<[^>]+>', '', match.group(2)).strip()
            full_tag = match.group(0)

            # Ignorer les ancres et javascript
            if href.startswith('#') or href.startswith('javascript:'):
                continue

            # Classifier le lien
            link_type = self._classify_link(href)

            links.append({
                "html": full_tag,
                "href": href,
                "anchor": anchor,
                "type": link_type,
            })

        return links

    def _classify_link(self, href: str) -> str:
        """Classifie un lien selon son URL."""
        href_lower = href.lower()

        if SUPERPROF_DOMAIN in href_lower:
            return "superprof"
        elif href.startswith('/') or href.startswith('#'):
            return "internal"
        elif any(domain in href_lower for domain in BLACKLIST_DOMAINS):
            return "blacklisted"
        elif href.startswith('http'):
            return "external"
        else:
            return "internal"

    def validate(
        self,
        original_assets: dict,
        new_content: str
    ) -> AssetValidationResult:
        """
        Valide que les assets sont préservés dans le nouveau contenu.

        Note: La featured image est EXCLUE du comptage car elle est gérée par WordPress.

        Args:
            original_assets: Assets extraits de l'original
            new_content: Nouveau contenu HTML

        Returns:
            AssetValidationResult avec les détails de validation
        """
        new_assets = self.extract_assets(new_content, exclude_featured_image=True)

        # Compter les assets (images contextuelles uniquement, sans featured image)
        images_original = original_assets.get("counts", {}).get("images", 0)
        images_new = new_assets.get("counts", {}).get("images", 0)

        links_original = (
            original_assets.get("counts", {}).get("internal_links", 0) +
            original_assets.get("counts", {}).get("external_links", 0)
        )
        links_new = (
            new_assets.get("counts", {}).get("internal_links", 0) +
            new_assets.get("counts", {}).get("external_links", 0)
        )

        superprof_count = new_assets.get("counts", {}).get("superprof_links", 0)

        # Vérifier les CTA
        cta_blocks_original = original_assets.get("cta_blocks", [])
        cta_blocks_new = new_assets.get("cta_blocks", [])
        cta_superprof_original = [c for c in cta_blocks_original if c.get("type") == "superprof_button"]
        cta_superprof_new = [c for c in cta_blocks_new if c.get("type") == "superprof_button"]

        # Vérifier les violations de blacklist
        blacklist_violations = self._check_blacklist(new_content)

        # Validations
        images_valid = images_new >= images_original
        links_valid = links_new >= links_original
        superprof_valid = superprof_count == 1
        # CTA Superprof valide si présent dans l'original et préservé
        cta_superprof_valid = len(cta_superprof_new) >= len(cta_superprof_original) if cta_superprof_original else True

        errors = []
        warnings = []

        if not images_valid:
            errors.append(
                f"Images contextuelles perdues: {images_original} original -> {images_new} nouveau"
            )

        if not links_valid:
            errors.append(
                f"Liens perdus: {links_original} original -> {links_new} nouveau"
            )

        if superprof_count == 0:
            errors.append("Lien Superprof manquant (exactement 1 requis)")
        elif superprof_count > 1:
            errors.append(f"Trop de liens Superprof: {superprof_count} (exactement 1 requis)")

        if blacklist_violations:
            errors.append(f"Liens blacklistés détectés: {', '.join(blacklist_violations)}")

        if not cta_superprof_valid:
            warnings.append("CTA Superprof stylé absent (était présent dans l'original)")

        # NOUVEAU: Validation des années obsolètes
        year_validator = YearUpdater()
        obsolete_years = year_validator.detect_obsolete_years(new_content)

        obsolete_count = 0
        if obsolete_years:
            # Filtrer les faux positifs (URLs, citations, références)
            real_issues = [
                y for y in obsolete_years
                if not year_validator.should_exclude(y['context'])
            ]

            if real_issues:
                obsolete_count = len(real_issues)
                warnings.append(
                    f"Années obsolètes: {obsolete_count} occurrence(s) détectées "
                    f"(ex: '{real_issues[0]['match']}' dans '{real_issues[0]['context'][:40]}...')"
                )

        # Warnings
        if images_new > images_original * 2:
            warnings.append(f"Beaucoup d'images ajoutées: {images_original} -> {images_new}")

        is_valid = len(errors) == 0 and not blacklist_violations

        return AssetValidationResult(
            is_valid=is_valid,
            images_original=images_original,
            images_new=images_new,
            images_valid=images_valid,
            links_original=links_original,
            links_new=links_new,
            links_valid=links_valid,
            superprof_count=superprof_count,
            superprof_valid=superprof_valid,
            blacklist_violations=blacklist_violations,
            errors=errors,
            warnings=warnings,
            cta_superprof_valid=cta_superprof_valid,
            cta_blocks_preserved=len(cta_blocks_new),
        )

    def _check_blacklist(self, content: str) -> list[str]:
        """Vérifie la présence de liens blacklistés."""
        violations = []

        for domain in BLACKLIST_DOMAINS:
            if domain in content.lower():
                violations.append(domain)

        return violations

    def restore_missing_assets(
        self,
        content: str,
        original_assets: dict,
        validation_result: AssetValidationResult
    ) -> str:
        """
        Tente de restaurer les assets manquants.

        Note: La featured image n'est PAS restaurée car elle est gérée par WordPress.

        Args:
            content: Contenu avec assets manquants
            original_assets: Assets originaux
            validation_result: Résultat de la validation

        Returns:
            Contenu avec assets restaurés
        """
        restored_content = content

        # Restaurer les images contextuelles manquantes (pas la featured image)
        if not validation_result.images_valid:
            restored_content = self._restore_images(
                restored_content,
                original_assets.get("images", [])  # N'inclut pas featured_image
            )

        # Restaurer le lien Superprof si manquant
        if validation_result.superprof_count == 0:
            superprof = original_assets.get("superprof_link")
            if superprof:
                restored_content = self._restore_superprof(
                    restored_content,
                    superprof
                )

        # Restaurer les CTA stylés manquants (seulement les obligatoires)
        if not validation_result.cta_superprof_valid:
            original_cta_blocks = original_assets.get("cta_blocks", [])
            for cta in original_cta_blocks:
                if cta.get("required", False) and cta.get("type") == "superprof_button":
                    restored_content = self._restore_cta_block(restored_content, cta)

        # Supprimer les liens blacklistés
        if validation_result.blacklist_violations:
            restored_content = self._remove_blacklisted_links(restored_content)

        return restored_content

    def _restore_cta_block(self, content: str, cta: dict) -> str:
        """
        Restaure un bloc CTA manquant.

        Args:
            content: Contenu HTML
            cta: Bloc CTA à restaurer

        Returns:
            Contenu avec CTA restauré
        """
        cta_html = cta.get("html", "")
        if not cta_html:
            return content

        # Vérifier si le CTA est déjà présent
        if cta_html in content:
            return content

        # Trouver un bon emplacement pour le CTA
        # Idéalement avant la FAQ ou avant la conclusion
        insert_patterns = [
            (r'(<h2[^>]*>\s*FAQ)', cta_html + '\n\n\\1'),
            (r'(<h2[^>]*>\s*Conclusion)', cta_html + '\n\n\\1'),
            (r'(</article>)', cta_html + '\n\n\\1'),
        ]

        for pattern, replacement in insert_patterns:
            if re.search(pattern, content, re.I):
                return re.sub(pattern, replacement, content, count=1, flags=re.I)

        # Fallback: ajouter avant le dernier paragraphe
        last_p = content.rfind('</p>')
        if last_p != -1:
            return content[:last_p] + '\n\n' + cta_html + '\n\n' + content[last_p:]

        return content + '\n\n' + cta_html

    def _restore_images(self, content: str, original_images: list[dict]) -> str:
        """
        Restaure les images manquantes avec placement contextuel.

        Stratégie: distribue les images après la première phrase de transition
        sous le premier H2 et le dernier H2, puis répartit les restantes
        après les premiers </p> des sections H2 intermédiaires.
        """
        current_images = self._extract_images(content)
        current_srcs = {img["src"] for img in current_images}

        missing_images = [
            img for img in original_images
            if img["src"] not in current_srcs
        ]

        if not missing_images:
            return content

        # Find all H2 section boundaries (positions after first </p> following each <h2>)
        h2_insert_points = self._find_h2_insert_points(content)

        if not h2_insert_points:
            # Fallback: find all </p> positions and distribute evenly
            h2_insert_points = self._find_paragraph_insert_points(content)

        if not h2_insert_points:
            # Last resort: append before end
            last_p = content.rfind('</p>')
            if last_p != -1:
                h2_insert_points = [last_p + len('</p>')]
            else:
                h2_insert_points = [len(content)]

        # Distribute missing images across insert points
        # Offset tracks how much we've inserted (shifts subsequent positions)
        offset = 0
        for i, img in enumerate(missing_images):
            # Round-robin across available insert points
            point_index = i % len(h2_insert_points)
            insert_pos = h2_insert_points[point_index] + offset

            img_tag = f"\n{img['html']}\n"
            content = content[:insert_pos] + img_tag + content[insert_pos:]
            offset += len(img_tag)

            # Shift subsequent insert points that come after this one
            for j in range(len(h2_insert_points)):
                if h2_insert_points[j] >= h2_insert_points[point_index]:
                    h2_insert_points[j] += len(img_tag)

        return content

    def _find_h2_insert_points(self, content: str) -> list[int]:
        """
        Find insert points: position after first </p> following each <h2>.

        Returns sorted list of positions where images can be inserted.
        """
        points = []
        h2_pattern = re.compile(r'<h2[^>]*>', re.I)

        for h2_match in h2_pattern.finditer(content):
            # Find the first </p> after this H2
            p_close = content.find('</p>', h2_match.end())
            if p_close != -1:
                points.append(p_close + len('</p>'))

        return points

    def _find_paragraph_insert_points(self, content: str) -> list[int]:
        """
        Fallback: find evenly-spaced </p> positions for image distribution.

        Picks every Nth paragraph to maintain ~200 word spacing.
        """
        points = []
        p_pattern = re.compile(r'</p>', re.I)
        all_p_positions = [m.end() for m in p_pattern.finditer(content)]

        if not all_p_positions:
            return points

        # Pick every 3rd paragraph close to approximate 150-200 word spacing
        step = max(1, len(all_p_positions) // 6)
        for i in range(0, len(all_p_positions), step):
            points.append(all_p_positions[i])

        return points

    def _restore_superprof(self, content: str, superprof_link: dict) -> str:
        """Restaure le lien Superprof."""
        # Trouver un bon emplacement (après l'introduction ou dans le CTA)
        insert_points = [
            (r'</p>\s*<h2', '</p>\n\n' + superprof_link["html"] + '\n\n<h2'),
            (r'</article>', superprof_link["html"] + '\n</article>'),
        ]

        for pattern, replacement in insert_points:
            if re.search(pattern, content, re.I):
                return re.sub(pattern, replacement, content, count=1, flags=re.I)

        # Fallback: ajouter à la fin
        return content + f"\n\n{superprof_link['html']}\n"

    def _remove_blacklisted_links(self, content: str) -> str:
        """Supprime les liens vers des domaines blacklistés."""
        for domain in BLACKLIST_DOMAINS:
            # Pattern pour supprimer le lien mais garder le texte
            pattern = rf'<a[^>]*href=["\'][^"\']*{re.escape(domain)}[^"\']*["\'][^>]*>(.*?)</a>'
            content = re.sub(pattern, r'\1', content, flags=re.I | re.S)

        return content

    def generate_assets_report(
        self,
        original_assets: dict,
        validation_result: AssetValidationResult
    ) -> str:
        """
        Génère un rapport sur les assets.

        Args:
            original_assets: Assets originaux
            validation_result: Résultat de la validation

        Returns:
            Rapport formaté
        """
        report = [
            "# Rapport des Assets\n",
            "## Validation\n",
            f"- Statut: {'✅ VALIDE' if validation_result.is_valid else '❌ INVALIDE'}\n",
            f"\n## Featured Image\n",
            f"- Présente dans original: {'✅' if original_assets.get('featured_image') else '❌'}",
            f"- Note: Gérée par WordPress, exclue du HTML généré\n",
            f"\n## Images Contextuelles\n",
            f"- Original: {validation_result.images_original}",
            f"- Nouveau: {validation_result.images_new}",
            f"- Valide: {'✅' if validation_result.images_valid else '❌'}\n",
            f"\n## Liens\n",
            f"- Original: {validation_result.links_original}",
            f"- Nouveau: {validation_result.links_new}",
            f"- Valide: {'✅' if validation_result.links_valid else '❌'}\n",
            f"\n## Superprof\n",
            f"- Nombre: {validation_result.superprof_count}",
            f"- Valide: {'✅' if validation_result.superprof_valid else '❌'}\n",
            f"\n## Blocs CTA\n",
            f"- Blocs préservés: {validation_result.cta_blocks_preserved}",
            f"- CTA Superprof valide: {'✅' if validation_result.cta_superprof_valid else '❌'}\n",
        ]

        if validation_result.blacklist_violations:
            report.append(f"\n## ⚠️ Violations Blacklist\n")
            for domain in validation_result.blacklist_violations:
                report.append(f"- {domain}\n")

        if validation_result.errors:
            report.append(f"\n## Erreurs\n")
            for error in validation_result.errors:
                report.append(f"- {error}\n")

        if validation_result.warnings:
            report.append(f"\n## Warnings\n")
            for warning in validation_result.warnings:
                report.append(f"- {warning}\n")

        return "".join(report)
