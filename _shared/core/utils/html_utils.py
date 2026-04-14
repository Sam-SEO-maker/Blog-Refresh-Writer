"""
HTML Utils Module

Fonctions utilitaires pour l'extraction et le traitement de contenu HTML.
Version unifiée et dédupliquée depuis html_analyzer.py et asset_manager.py.
"""

import re
from typing import Optional
from urllib.parse import urljoin, urlparse

from ..models.audit_models import ImageAsset, LinkAsset, CTABlock
from ..constants import BLACKLIST_DOMAINS, SUPERPROF_DOMAIN


def extract_images(
    html: str,
    base_url: str,
    h2_list: Optional[list[str]] = None
) -> list[ImageAsset]:
    """
    Extrait toutes les images avec leur contexte.

    Args:
        html: HTML brut
        base_url: URL de base pour résoudre les URLs relatives
        h2_list: Liste des H2 pour trouver le contexte (optionnel)

    Returns:
        Liste des ImageAsset extraits
    """
    images = []
    h2_list = h2_list or []

    # Pattern pour les balises img
    img_pattern = r'<img[^>]+>'

    for match in re.finditer(img_pattern, html, re.I):
        img_tag = match.group(0)

        # Extraire src
        src_match = re.search(r'src=["\']([^"\']+)["\']', img_tag, re.I)
        if not src_match:
            continue
        src = urljoin(base_url, src_match.group(1))

        # Extraire alt
        alt_match = re.search(r'alt=["\']([^"\']*)["\']', img_tag, re.I)
        alt = alt_match.group(1) if alt_match else ""

        # Extraire dimensions
        width_match = re.search(r'width=["\']?(\d+)', img_tag, re.I)
        height_match = re.search(r'height=["\']?(\d+)', img_tag, re.I)

        # Trouver le H2 de contexte
        context_h2 = find_context_h2(html, match.start(), h2_list)

        images.append(ImageAsset(
            src=src,
            alt=alt,
            html=img_tag,
            context_h2=context_h2,
            width=int(width_match.group(1)) if width_match else None,
            height=int(height_match.group(1)) if height_match else None,
        ))

    return images


def extract_links(
    html: str,
    base_url: str,
    domain: str,
    h2_list: Optional[list[str]] = None
) -> tuple[list[LinkAsset], list[LinkAsset], Optional[LinkAsset]]:
    """
    Extrait tous les liens avec classification.

    Args:
        html: HTML brut
        base_url: URL de base pour résoudre les URLs relatives
        domain: Domaine du site (pour classifier internal vs external)
        h2_list: Liste des H2 pour trouver le contexte (optionnel)

    Returns:
        Tuple (internal_links, external_links, superprof_link)
    """
    all_links = []
    h2_list = h2_list or []

    # Pattern pour les balises a
    link_pattern = r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>'

    for match in re.finditer(link_pattern, html, re.I | re.S):
        href = match.group(1)
        anchor = clean_html_text(match.group(2))
        full_tag = match.group(0)

        # Ignorer les ancres internes et javascript
        if href.startswith('#') or href.startswith('javascript:'):
            continue

        # Résoudre l'URL
        full_href = urljoin(base_url, href)
        parsed = urlparse(full_href)

        # Classifier le lien
        link_type = classify_link(parsed.netloc, domain)

        # Vérifier blacklist
        is_blacklisted = any(bl in parsed.netloc for bl in BLACKLIST_DOMAINS)

        # Trouver le H2 de contexte
        context_h2 = find_context_h2(html, match.start(), h2_list)

        all_links.append(LinkAsset(
            href=full_href,
            anchor=anchor,
            html=full_tag,
            link_type=link_type,
            context_h2=context_h2,
            is_blacklisted=is_blacklisted,
        ))

    # Séparer par type
    internal_links = [l for l in all_links if l.link_type == "internal"]
    external_links = [l for l in all_links if l.link_type == "external"]
    superprof_links = [l for l in all_links if l.link_type == "superprof"]

    superprof_link = superprof_links[0] if superprof_links else None

    return internal_links, external_links, superprof_link


def classify_link(netloc: str, domain: str) -> str:
    """
    Classifie un lien selon son domaine.

    Args:
        netloc: Netloc du lien (ex: "www.example.com")
        domain: Domaine du site (ex: "example.com")

    Returns:
        Type de lien: "superprof", "internal", ou "external"
    """
    netloc = netloc.lower()

    if SUPERPROF_DOMAIN in netloc:
        return "superprof"
    elif domain in netloc:
        return "internal"
    else:
        return "external"


def find_context_h2(html: str, position: int, h2_list: list[str]) -> Optional[str]:
    """
    Trouve le H2 précédant une position donnée dans le HTML.

    Args:
        html: HTML brut
        position: Position dans le HTML
        h2_list: Liste des H2 de l'article

    Returns:
        Le H2 de contexte, ou None
    """
    # Chercher le dernier H2 avant cette position
    html_before = html[:position]
    h2_matches = list(re.finditer(r'<h2[^>]*>(.*?)</h2>', html_before, re.I | re.S))

    if h2_matches:
        last_h2 = clean_html_text(h2_matches[-1].group(1))
        return last_h2 if last_h2 in h2_list else None

    return None


def clean_html_text(text: str) -> str:
    """
    Nettoie le texte HTML (supprime balises, espaces multiples).

    Args:
        text: Texte HTML à nettoyer

    Returns:
        Texte nettoyé
    """
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def identify_featured_image(images: list[ImageAsset], html: str) -> Optional[ImageAsset]:
    """
    Identifie l'image à la Une parmi les images extraites.

    L'image à la Une est généralement :
    - La première image après le H1
    - Ou la première image de grande taille (width >= 800)

    Args:
        images: Liste des images extraites
        html: HTML brut pour analyse de position

    Returns:
        L'image identifiée comme featured, ou None
    """
    if not images:
        return None

    # Trouver la position du H1
    h1_match = re.search(r'<h1[^>]*>', html, re.I)
    h1_position = h1_match.end() if h1_match else 0

    # La première image est probablement la featured image si :
    # 1. Elle est proche du H1 (dans les 1000 premiers caractères après H1)
    # 2. Ou elle a une grande taille (width >= 800)
    first_img = images[0]

    # Trouver la position de la première image
    first_img_match = re.search(re.escape(first_img.html[:50]), html)
    if first_img_match:
        img_position = first_img_match.start()

        # Si l'image est dans les 1000 caractères après le H1
        if img_position <= h1_position + 1000:
            first_img.is_featured_image = True
            return first_img

    # Fallback : si la première image est grande (>= 800px de large)
    if first_img.width and first_img.width >= 800:
        first_img.is_featured_image = True
        return first_img

    return None


def extract_cta_blocks(html: str, h2_list: Optional[list[str]] = None) -> list[CTABlock]:
    """
    Extrait les blocs CTA stylés de l'article.

    Détecte :
    - Boutons Superprof (style avec background-color)
    - Blocs définition/info (div avec border-left)

    Args:
        html: HTML brut
        h2_list: Liste des H2 pour contexte (optionnel)

    Returns:
        Liste des CTABlock extraits
    """
    cta_blocks = []
    h2_list = h2_list or []

    # Pattern 1 : CTA bouton Superprof (paragraphe centré avec lien stylé)
    superprof_cta_pattern = r'(<p[^>]*style="[^"]*text-align:\s*center[^"]*"[^>]*>.*?<a[^>]*style="[^"]*background-color[^"]*"[^>]*>.*?</a>.*?</p>)'
    for match in re.finditer(superprof_cta_pattern, html, re.I | re.S):
        context_h2 = find_context_h2(html, match.start(), h2_list)
        cta_blocks.append(CTABlock(
            html=match.group(1),
            cta_type="superprof_button",
            context_h2=context_h2,
            required=True  # Le CTA Superprof est obligatoire
        ))

    # Pattern 2 : Bloc définition/info (div avec border-left stylé)
    definition_pattern = r'(<div[^>]*style="[^"]*border-left[^"]*"[^>]*>.*?</div>)'
    for match in re.finditer(definition_pattern, html, re.I | re.S):
        context_h2 = find_context_h2(html, match.start(), h2_list)
        cta_blocks.append(CTABlock(
            html=match.group(1),
            cta_type="definition_box",
            context_h2=context_h2,
            required=False  # Les blocs définition sont optionnels
        ))

    # Pattern 3 : Bloc info avec background stylé
    info_pattern = r'(<div[^>]*style="[^"]*background-color:\s*#f[0-9a-f]{5}[^"]*"[^>]*>.*?</div>)'
    for match in re.finditer(info_pattern, html, re.I | re.S):
        # Éviter les doublons avec definition_box
        if any(match.group(1) in cta.html for cta in cta_blocks):
            continue
        context_h2 = find_context_h2(html, match.start(), h2_list)
        cta_blocks.append(CTABlock(
            html=match.group(1),
            cta_type="info_box",
            context_h2=context_h2,
            required=False  # Les blocs info sont optionnels
        ))

    return cta_blocks
