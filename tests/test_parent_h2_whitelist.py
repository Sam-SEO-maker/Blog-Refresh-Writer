"""
Test Parent H2 Whitelist System

Validates that PARENT articles respect mandatory H2 structure (H2 = H1 of children).
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from scripts.ghostwriter import Ghostwriter


def test_whitelist_validation():
    """Test H2 whitelist validation for PARENT articles."""

    ghostwriter = Ghostwriter()

    # Expected H2s (H1 titles from child articles)
    mandatory_h2s = [
        "Comment choisir sa ville pour apprendre l'anglais au Royaume-Uni ?",
        "Quel type de séjour pour apprendre l'anglais au Royaume-Uni ?",
        "Combien coûte un séjour linguistique au Royaume-Uni ?",
    ]

    # Test Case 1: VALID HTML (all H2s present, no extras)
    valid_html = """
    <h1>Guide complet pour apprendre l'anglais au Royaume-Uni</h1>

    <h2>Comment choisir sa ville pour apprendre l'anglais au Royaume-Uni ?</h2>
    <p>Contenu section 1...</p>

    <h2>Quel type de séjour pour apprendre l'anglais au Royaume-Uni ?</h2>
    <p>Contenu section 2...</p>

    <h2>Combien coûte un séjour linguistique au Royaume-Uni ?</h2>
    <p>Contenu section 3...</p>
    """

    result_valid = ghostwriter.validate_parent_h2_structure(
        generated_html=valid_html,
        mandatory_h2s=mandatory_h2s,
        strict=True
    )

    print("="*70)
    print("TEST 1: HTML valide (tous les H2 présents, aucun extra)")
    print("="*70)
    print(f"Valid: {result_valid['valid']}")
    print(f"H2 attendus: {result_valid['h2_expected_count']}")
    print(f"H2 trouvés: {result_valid['h2_actual_count']}")
    print(f"H2 manquants: {result_valid['h2_missing']}")
    print(f"H2 extra: {result_valid['h2_extra']}")
    print(f"Erreurs: {result_valid['errors']}")
    assert result_valid['valid'] == True, "HTML valide devrait passer la validation"
    print("[OK] TEST PASSED\n")

    # Test Case 2: INVALID HTML (extra H2 not in whitelist)
    invalid_html = """
    <h1>Guide complet pour apprendre l'anglais au Royaume-Uni</h1>

    <h2>Comment choisir sa ville pour apprendre l'anglais au Royaume-Uni ?</h2>
    <p>Contenu section 1...</p>

    <h2>Quel est le moyen le plus efficace d'apprendre l'anglais ?</h2>
    <p>ERREUR: Ce H2 n'est PAS dans la whitelist !</p>

    <h2>Quel type de séjour pour apprendre l'anglais au Royaume-Uni ?</h2>
    <p>Contenu section 2...</p>

    <h2>Combien coûte un séjour linguistique au Royaume-Uni ?</h2>
    <p>Contenu section 3...</p>
    """

    result_invalid = ghostwriter.validate_parent_h2_structure(
        generated_html=invalid_html,
        mandatory_h2s=mandatory_h2s,
        strict=True
    )

    print("="*70)
    print("TEST 2: HTML invalide (H2 hors whitelist)")
    print("="*70)
    print(f"Valid: {result_invalid['valid']}")
    print(f"H2 attendus: {result_invalid['h2_expected_count']}")
    print(f"H2 trouvés: {result_invalid['h2_actual_count']}")
    print(f"H2 manquants: {result_invalid['h2_missing']}")
    print(f"H2 extra: {result_invalid['h2_extra']}")
    print(f"Erreurs: {result_invalid['errors']}")
    assert result_invalid['valid'] == False, "HTML avec H2 extra devrait échouer"
    assert len(result_invalid['h2_extra']) > 0, "Devrait détecter le H2 hors whitelist"
    print("[OK] TEST PASSED\n")

    # Test Case 3: INVALID HTML (missing mandatory H2)
    incomplete_html = """
    <h1>Guide complet pour apprendre l'anglais au Royaume-Uni</h1>

    <h2>Comment choisir sa ville pour apprendre l'anglais au Royaume-Uni ?</h2>
    <p>Contenu section 1...</p>

    <h2>Combien coûte un séjour linguistique au Royaume-Uni ?</h2>
    <p>Contenu section 3...</p>

    <!-- MANQUE: "Quel type de séjour pour apprendre l'anglais au Royaume-Uni ?" -->
    """

    result_incomplete = ghostwriter.validate_parent_h2_structure(
        generated_html=incomplete_html,
        mandatory_h2s=mandatory_h2s,
        strict=True
    )

    print("="*70)
    print("TEST 3: HTML invalide (H2 manquant)")
    print("="*70)
    print(f"Valid: {result_incomplete['valid']}")
    print(f"H2 attendus: {result_incomplete['h2_expected_count']}")
    print(f"H2 trouvés: {result_incomplete['h2_actual_count']}")
    print(f"H2 manquants: {result_incomplete['h2_missing']}")
    print(f"H2 extra: {result_incomplete['h2_extra']}")
    print(f"Erreurs: {result_incomplete['errors']}")
    assert result_incomplete['valid'] == False, "HTML avec H2 manquant devrait échouer"
    assert len(result_incomplete['h2_missing']) > 0, "Devrait détecter le H2 manquant"
    print("[OK] TEST PASSED\n")

    # Test Case 4: Case-insensitive matching (normalization)
    normalized_html = """
    <h1>Guide complet pour apprendre l'anglais au Royaume-Uni</h1>

    <h2>COMMENT CHOISIR SA VILLE POUR APPRENDRE L'ANGLAIS AU ROYAUME-UNI ?</h2>
    <p>Contenu section 1...</p>

    <h2>Quel Type de Séjour pour Apprendre l'Anglais au Royaume-Uni ?</h2>
    <p>Contenu section 2...</p>

    <h2>  Combien coûte un séjour linguistique au Royaume-Uni  ?  </h2>
    <p>Contenu section 3...</p>
    """

    result_normalized = ghostwriter.validate_parent_h2_structure(
        generated_html=normalized_html,
        mandatory_h2s=mandatory_h2s,
        strict=True
    )

    print("="*70)
    print("TEST 4: Normalisation (case-insensitive, espaces)")
    print("="*70)
    print(f"Valid: {result_normalized['valid']}")
    print(f"H2 attendus: {result_normalized['h2_expected_count']}")
    print(f"H2 trouvés: {result_normalized['h2_actual_count']}")
    print(f"H2 manquants: {result_normalized['h2_missing']}")
    print(f"H2 extra: {result_normalized['h2_extra']}")
    print(f"Erreurs: {result_normalized['errors']}")
    assert result_normalized['valid'] == True, "La normalisation devrait permettre le match"
    print("[OK] TEST PASSED\n")

    print("="*70)
    print("[SUCCESS] TOUS LES TESTS RÉUSSIS")
    print("="*70)


if __name__ == "__main__":
    test_whitelist_validation()
