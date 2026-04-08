#!/usr/bin/env python3
"""
Fix shifted columns in Refreshs_Audit spreadsheet.

Bug: bulk_index_diagnostic.py was missing cocon_branch (col B) in INSERT,
and writing to col W instead of X for UPDATE.

This script:
1. Identifies wrongly inserted rows (URL in col B instead of col C)
2. Deletes those rows
3. Moves values from col W to col X for updated rows (where W has a scenario value)
"""

import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.sheets.sheets_client import SheetsClient

SPREADSHEET_ID = "1F99FtN8fWQlQm0ZTJphBRz_c64iDs2DvohyHyM2Tk1M"
SHEET_NAME = "Refreshs_Audit"

# Known scenarios from bulk_index_diagnostic
KNOWN_SCENARIOS = {
    "URL_NOT_ON_GOOGLE",
    "DISCOVERED_NOT_INDEXED",
    "INDEXING_ISSUE",
    "INDEXED",
    "URL_404",
    "URL_REDIRECTED",
}


def main():
    sheets = SheetsClient(SPREADSHEET_ID)

    # Read all data
    print("Reading all rows from Refreshs_Audit...")
    result = sheets._sheets_service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{SHEET_NAME}",
        valueRenderOption="UNFORMATTED_VALUE"
    ).execute()

    rows = result.get("values", [])
    print(f"Total rows: {len(rows)} (including header)")

    if len(rows) < 2:
        print("No data rows found.")
        return

    header = rows[0]
    data_rows = rows[1:]

    # --- STEP 1: Identify wrongly inserted rows ---
    # These rows have a URL (starts with http) in column B (index 1)
    # instead of cocon_branch
    shifted_row_indices = []  # 1-indexed (sheet row numbers)
    for i, row in enumerate(data_rows):
        if len(row) > 1:
            col_b = str(row[1]) if row[1] is not None else ""
            if col_b.startswith("http"):
                shifted_row_indices.append(i + 2)  # +2 for header + 0-index

    print(f"\n--- STEP 1: Shifted rows (URL in col B) ---")
    print(f"Found {len(shifted_row_indices)} wrongly inserted rows")
    for idx in shifted_row_indices:
        row = rows[idx - 1]
        blog_id = row[0] if len(row) > 0 else "?"
        url_in_b = row[1] if len(row) > 1 else "?"
        print(f"  Row {idx}: blog={blog_id}, url_in_B={url_in_b}")

    # --- STEP 2: Identify W→X corrections needed ---
    # For existing rows that were updated, scenario was written to col W (index 22)
    # instead of col X (index 23)
    w_to_x_fixes = []
    for i, row in enumerate(data_rows):
        row_num = i + 2
        if row_num in shifted_row_indices:
            continue  # Will be deleted, skip
        if len(row) > 22:
            col_w = str(row[22]) if len(row) > 22 and row[22] is not None else ""
            if col_w in KNOWN_SCENARIOS:
                w_to_x_fixes.append((row_num, col_w))

    print(f"\n--- STEP 2: W→X fixes needed ---")
    print(f"Found {len(w_to_x_fixes)} rows with scenario in col W")
    for row_num, scenario in w_to_x_fixes:
        print(f"  Row {row_num}: W='{scenario}' → move to X")

    # --- APPLY FIXES ---
    input_val = input("\nApply fixes? (y/n): ").strip().lower()
    if input_val != "y":
        print("Aborted.")
        return

    # Fix 2: Move W→X (do this BEFORE deleting rows to avoid index shifts)
    if w_to_x_fixes:
        print(f"\nMoving {len(w_to_x_fixes)} values from W to X...")
        updates = []
        for row_num, scenario in w_to_x_fixes:
            updates.append({"sheet": SHEET_NAME, "cell": f"X{row_num}", "value": scenario})
            updates.append({"sheet": SHEET_NAME, "cell": f"W{row_num}", "value": ""})

        # Batch update in chunks of 50
        for chunk_start in range(0, len(updates), 50):
            chunk = updates[chunk_start:chunk_start + 50]
            sheets._batch_update_cells(chunk)
            print(f"  Updated {min(chunk_start + 50, len(updates))}/{len(updates)} cells")

        print("  ✅ W→X fixes applied")

    # Fix 1: Delete shifted rows (delete from bottom to top to avoid index shifts)
    if shifted_row_indices:
        print(f"\nDeleting {len(shifted_row_indices)} wrongly inserted rows...")

        # Get sheet ID (gid) for delete request
        sheet_metadata = sheets._sheets_service.spreadsheets().get(
            spreadsheetId=SPREADSHEET_ID
        ).execute()

        sheet_id = None
        for sheet in sheet_metadata["sheets"]:
            if sheet["properties"]["title"] == SHEET_NAME:
                sheet_id = sheet["properties"]["sheetId"]
                break

        if sheet_id is None:
            print(f"  ❌ Sheet '{SHEET_NAME}' not found!")
            return

        # Delete from bottom to top
        sorted_indices = sorted(shifted_row_indices, reverse=True)
        for row_num in sorted_indices:
            request = {
                "requests": [{
                    "deleteDimension": {
                        "range": {
                            "sheetId": sheet_id,
                            "dimension": "ROWS",
                            "startIndex": row_num - 1,  # 0-indexed
                            "endIndex": row_num          # exclusive
                        }
                    }
                }]
            }
            sheets._sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=SPREADSHEET_ID,
                body=request
            ).execute()
            print(f"  Deleted row {row_num}")

        print("  ✅ Shifted rows deleted")

    print("\n✅ All fixes applied successfully!")


if __name__ == "__main__":
    main()
