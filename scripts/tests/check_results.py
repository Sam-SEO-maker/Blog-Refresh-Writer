#!/usr/bin/env python3
"""
Check batch results in spreadsheet
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.sheets.sheets_client import SheetsClient

spreadsheet_id = "1F99FtN8fWQlQm0ZTJphBRz_c64iDs2DvohyHyM2Tk1M"
sheets_client = SheetsClient(spreadsheet_id)

print("=" * 70)
print("RESULTATS DU WORKFLOW BATCH")
print("=" * 70)

# Check URLs_Input statuses
print("\n1. Statuts des URLs traitees (URLs_Input):")
data = sheets_client._read_sheet("URLs_Input")
if data:
    for i, row in enumerate(data[1:], start=2):  # Skip header
        if len(row) >= 5:
            url = row[0][:50] + "..." if len(row[0]) > 50 else row[0]
            status = row[4] if len(row) > 4 else "N/A"
            print(f"   Row {i}: {url}")
            print(f"      Status: {status}")

# Check Audit_Results
print("\n2. Donnees d'audit (Audit_Results):")
audit_data = sheets_client._read_sheet("Audit_Results")
if audit_data and len(audit_data) > 1:
    print(f"   {len(audit_data)-1} audit(s) enregistre(s)")
    for i, row in enumerate(audit_data[1:3], start=2):  # First 2 audits
        if len(row) >= 1:
            print(f"   Row {i}: {row[0][:50]}")

# Check Decision_Log
print("\n3. Decisions appliquees (Decision_Log):")
decision_data = sheets_client._read_sheet("Decision_Log")
if decision_data and len(decision_data) > 1:
    print(f"   {len(decision_data)-1} decision(s) enregistree(s)")
    for i, row in enumerate(decision_data[1:3], start=2):  # First 2 decisions
        if len(row) >= 4:
            print(f"   Row {i}: {row[0][:50]}")
            print(f"      Action: {row[3]}")

print("\n" + "=" * 70)
print("Verifiez manuellement le spreadsheet pour plus de details")
print("=" * 70)
