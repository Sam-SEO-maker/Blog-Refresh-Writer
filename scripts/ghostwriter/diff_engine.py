"""
Diff Engine Module

Moteur de réécriture différentielle pour économiser les tokens.
"""

import re
from difflib import SequenceMatcher
from typing import Optional

from _shared.core.models import SectionDiff, ContentDiff
from _shared.core.constants import SIMILARITY_THRESHOLD
from _shared.core.utils.year_updater import YearUpdater


class DiffEngine:
    """
    Moteur de diff pour la réécriture différentielle.

    Permet de:
    - Comparer le contenu original et modifié
    - Identifier les sections à modifier
    - Générer des diffs lisibles
    - Économiser des tokens en ne traitant que les parties modifiées
    """

    def __init__(self):
        """Initialise le moteur de diff."""
        self.year_updater = YearUpdater()
        self._year_changes = []  # Traçabilité des changements d'années

    def extract_sections(self, html_content: str) -> dict[str, str]:
        """
        Extrait les sections d'un contenu HTML.

        Args:
            html_content: Contenu HTML

        Returns:
            Dictionnaire {section_id: content}
        """
        sections = {}

        # Extraire le titre H1
        h1_match = re.search(r'<h1[^>]*>(.*?)</h1>', html_content, re.I | re.S)
        if h1_match:
            sections["h1"] = self._clean_text(h1_match.group(1))

        # Extraire les sections H2
        h2_pattern = r'<h2[^>]*>(.*?)</h2>(.*?)(?=<h2|$)'
        h2_matches = re.findall(h2_pattern, html_content, re.I | re.S)

        for i, (h2_title, h2_content) in enumerate(h2_matches):
            section_id = f"h2_{i+1}"
            sections[section_id] = {
                "title": self._clean_text(h2_title),
                "content": self._clean_text(h2_content),
            }

        return sections

    def compare_content(
        self,
        original_html: str,
        modified_html: str
    ) -> ContentDiff:
        """
        Compare le contenu original et modifié.

        Args:
            original_html: HTML original
            modified_html: HTML modifié

        Returns:
            ContentDiff avec les différences
        """
        original_sections = self.extract_sections(original_html)
        modified_sections = self.extract_sections(modified_html)

        section_diffs = []

        # Comparer le H1
        title_diff = None
        if "h1" in original_sections or "h1" in modified_sections:
            orig_h1 = original_sections.get("h1", "")
            mod_h1 = modified_sections.get("h1", "")
            similarity = self._calculate_similarity(orig_h1, mod_h1)

            title_diff = SectionDiff(
                section_id="h1",
                section_title="Titre H1",
                original_content=orig_h1,
                modified_content=mod_h1 if similarity < SIMILARITY_THRESHOLD else None,
                modification_type="modified" if similarity < SIMILARITY_THRESHOLD else "unchanged",
                justification="" if similarity >= SIMILARITY_THRESHOLD else "Titre optimisé",
                similarity_ratio=similarity,
            )

        # Comparer les sections H2
        all_section_ids = set(
            k for k in original_sections if k.startswith("h2_")
        ) | set(
            k for k in modified_sections if k.startswith("h2_")
        )

        for section_id in sorted(all_section_ids):
            orig = original_sections.get(section_id, {})
            mod = modified_sections.get(section_id, {})

            orig_title = orig.get("title", "") if isinstance(orig, dict) else ""
            orig_content = orig.get("content", "") if isinstance(orig, dict) else ""
            mod_title = mod.get("title", "") if isinstance(mod, dict) else ""
            mod_content = mod.get("content", "") if isinstance(mod, dict) else ""

            # Calculer la similarité du contenu
            similarity = self._calculate_similarity(
                f"{orig_title} {orig_content}",
                f"{mod_title} {mod_content}"
            )

            # Déterminer le type de modification
            if not orig_title and mod_title:
                mod_type = "added"
            elif orig_title and not mod_title:
                mod_type = "removed"
            elif similarity >= SIMILARITY_THRESHOLD:
                mod_type = "unchanged"
            else:
                mod_type = "modified"

            section_diffs.append(SectionDiff(
                section_id=section_id,
                section_title=orig_title or mod_title,
                original_content=f"{orig_title}\n{orig_content}".strip(),
                modified_content=f"{mod_title}\n{mod_content}".strip() if mod_type != "unchanged" else None,
                modification_type=mod_type,
                justification=self._generate_justification(mod_type, similarity),
                similarity_ratio=similarity,
            ))

        # Calculer les statistiques
        modified_count = sum(1 for s in section_diffs if s.modification_type != "unchanged")
        unchanged_count = sum(1 for s in section_diffs if s.modification_type == "unchanged")
        total_sections = len(section_diffs)

        overall_similarity = sum(s.similarity_ratio for s in section_diffs) / total_sections if total_sections > 0 else 1.0

        return ContentDiff(
            title_diff=title_diff,
            meta_diff=None,  # À implémenter si nécessaire
            sections=section_diffs,
            total_sections=total_sections,
            modified_sections=modified_count,
            unchanged_sections=unchanged_count,
            overall_similarity=overall_similarity,
        )

    def generate_diff_output(self, content_diff: ContentDiff) -> str:
        """
        Génère une sortie diff lisible.

        Args:
            content_diff: Résultat du diff

        Returns:
            Texte formaté du diff
        """
        output_parts = []

        output_parts.append("# Résumé des Modifications\n")
        output_parts.append(f"- Sections totales: {content_diff.total_sections}")
        output_parts.append(f"- Sections modifiées: {content_diff.modified_sections}")
        output_parts.append(f"- Sections inchangées: {content_diff.unchanged_sections}")
        output_parts.append(f"- Similarité globale: {content_diff.overall_similarity:.1%}\n")

        # Titre H1
        if content_diff.title_diff and content_diff.title_diff.modification_type != "unchanged":
            output_parts.append("## Titre H1\n")
            output_parts.append(f"### AVANT:\n{content_diff.title_diff.original_content}\n")
            output_parts.append(f"### APRÈS:\n{content_diff.title_diff.modified_content}\n")
            output_parts.append(f"### JUSTIFICATION:\n{content_diff.title_diff.justification}\n")

        # Sections modifiées
        for section in content_diff.sections:
            if section.modification_type == "unchanged":
                continue

            output_parts.append(f"## {section.section_title}\n")
            output_parts.append(f"**Type de modification**: {section.modification_type}")
            output_parts.append(f"**Similarité**: {section.similarity_ratio:.1%}\n")

            if section.modification_type != "added":
                output_parts.append(f"### AVANT:\n{section.original_content[:500]}...\n")

            if section.modification_type != "removed" and section.modified_content:
                output_parts.append(f"### APRÈS:\n{section.modified_content[:500]}...\n")

            output_parts.append(f"### JUSTIFICATION:\n{section.justification}\n")
            output_parts.append("---\n")

        return "\n".join(output_parts)

    def identify_sections_to_modify(
        self,
        sections: dict[str, str],
        audit_recommendations: list[str]
    ) -> list[str]:
        """
        Identifie les sections qui nécessitent une modification.

        Args:
            sections: Sections extraites
            audit_recommendations: Recommandations de l'audit

        Returns:
            Liste des section_ids à modifier
        """
        sections_to_modify = []

        # Mots-clés indiquant des sections à modifier
        keywords_mapping = {
            "titre": ["h1"],
            "meta": ["meta"],
            "introduction": ["h2_1"],
            "faq": [],  # Chercher la section FAQ
            "statistique": [],  # Toutes les sections
            "source": [],  # Toutes les sections
        }

        recommendations_lower = " ".join(audit_recommendations).lower()

        # Analyser les recommandations
        if "titre" in recommendations_lower or "ctr" in recommendations_lower:
            sections_to_modify.append("h1")

        if "statistique" in recommendations_lower or "donnée" in recommendations_lower:
            # Modifier toutes les sections (refresh des stats)
            sections_to_modify.extend([k for k in sections if k.startswith("h2_")])

        if "faq" in recommendations_lower:
            # Trouver la section FAQ
            for section_id, content in sections.items():
                if isinstance(content, dict):
                    if "faq" in content.get("title", "").lower():
                        sections_to_modify.append(section_id)

        # Dédupliquer
        return list(set(sections_to_modify))

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calcule la similarité entre deux textes."""
        if not text1 and not text2:
            return 1.0
        if not text1 or not text2:
            return 0.0

        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()

    def _clean_text(self, text: str) -> str:
        """Nettoie le texte HTML."""
        # NOUVEAU: Remplacer les années obsolètes AVANT nettoyage
        text, changes = self.year_updater.replace_years(
            text,
            exclude_patterns=['url', 'href', 'citation', 'reference']
        )
        if changes:
            self._year_changes.extend(changes)

        # Supprimer les balises
        text = re.sub(r'<[^>]+>', ' ', text)
        # Normaliser les espaces
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _generate_justification(self, mod_type: str, similarity: float) -> str:
        """Génère une justification pour la modification."""
        if mod_type == "unchanged":
            return "Section pertinente et à jour, conservée sans modification."
        elif mod_type == "added":
            return "Nouvelle section ajoutée pour enrichir le contenu."
        elif mod_type == "removed":
            return "Section supprimée car obsolète ou redondante."
        else:
            if similarity < 0.5:
                return "Section significativement réécrite pour mise à jour et amélioration."
            else:
                return "Section légèrement modifiée pour actualisation des données."
