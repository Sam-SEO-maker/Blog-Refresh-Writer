#!/usr/bin/env python3
"""
Verification de la structure du Google Spreadsheet

Valide que :
1. Le spreadsheet est accessible
2. Les feuilles requises existent
3. Il y a au moins 4 URLs PENDING pour le test
"""

import sys
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.sheets.sheets_client import SheetsClient


def verify_spreadsheet():
    """Verifie la structure du spreadsheet."""

    print("=" * 70)
    print("VERIFICATION : Structure Google Spreadsheet")
    print("=" * 70)

    spreadsheet_id = "1F99FtN8fWQlQm0ZTJphBRz_c64iDs2DvohyHyM2Tk1M"

    print(f"\n1. Initialization du client Sheets...")
    try:
        sheets_client = SheetsClient(spreadsheet_id)
        print(f"   [OK] Client Sheets initialise")
    except Exception as e:
        print(f"   [FAIL] Erreur initialization : {e}")
        return False

    # Verifier les feuilles
    print(f"\n2. Verification des feuilles...")
    required_sheets = [
        SheetsClient.SHEET_URLS_INPUT,
        SheetsClient.SHEET_AUDIT_RESULTS,
        SheetsClient.SHEET_REFRESH_RESULTS,
        SheetsClient.SHEET_DECISION_LOG,
        SheetsClient.SHEET_ASSETS,
    ]

    for sheet_name in required_sheets:
        try:
            data = sheets_client._read_sheet(sheet_name)
            if data:
                print(f"   [OK] Feuille '{sheet_name}' existe ({len(data)} lignes)")
            else:
                print(f"   [WARN] Feuille '{sheet_name}' vide")
        except Exception as e:
            print(f"   [FAIL] Erreur lecture '{sheet_name}' : {e}")

    # Verifier les URLs PENDING
    print(f"\n3. Verification des URLs PENDING...")
    try:
        pending_urls = sheets_client.read_pending_urls()
        print(f"   [OK] {len(pending_urls)} URLs PENDING trouvees")

        if pending_urls:
            print(f"\n   Details des 5 premieres URLs :")
            for i, task in enumerate(pending_urls[:5], 1):
                print(f"   {i}. {task.url}")
                print(f"      Blog ID: {task.site_slug}")
                print(f"      Post Type: {task.post_type}")
                print()

            if len(pending_urls) >= 4:
                print(f"   [OK] Au moins 4 URLs trouvees - pret pour le workflow !")
                return True
            else:
                print(f"   [WARN] Moins de 4 URLs ({len(pending_urls)})")
                return False
        else:
            print(f"   [FAIL] Aucune URL PENDING trouvee")
            return False

    except Exception as e:
        print(f"   [FAIL] Erreur lecture URLs PENDING : {e}")
        return False


def main():
    """Fonction principale."""
    success = verify_spreadsheet()

    print("\n" + "=" * 70)
    if success:
        print("[SUCCESS] Spreadsheet pret pour le workflow batch !")
        print("   -> Vous pouvez lancer : python main.py --mode batch --limit 4")
    else:
        print("[FAILURE] Verifiez la structure du spreadsheet")
    print("=" * 70)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
