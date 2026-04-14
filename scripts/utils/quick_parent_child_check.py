"""
ULTRA-FAST parent/child identification.
Reads spreadsheet columns directly without fetching siblings.

Assumes spreadsheet has:
- Column C: URL
- Column G: parent_url
- Column H: siblings (pipe-separated URLs)

Usage:
    python scripts/utils/quick_parent_child_check.py --spreadsheet-id YOUR_SHEET_ID
"""

import sys
from pathlib import Path

# Fix Windows encoding for emojis
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import argparse
from scripts.sheets.sheets_client import SheetsClient


def quick_analyze(spreadsheet_id: str, sheet_name: str = "Refreshs_Audit"):
    """Ultra-fast analysis using spreadsheet columns directly."""

    print(f"📊 Fetching data from: {sheet_name}...")

    sheets_client = SheetsClient(spreadsheet_id)

    # Read data using Google Sheets API directly
    result = sheets_client._sheets_service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=f"{sheet_name}!A2:Z"
    ).execute()

    rows = result.get('values', [])

    parents = []
    children = []
    orphans = []

    print(f"🔍 Analyzing {len(rows)} rows...\n")

    for row in rows:
        if len(row) < 2:
            continue

        # Column C (index 2) = blogpost_url
        # Column D (index 3) = main_keyword
        # Column E (index 4) = title
        # Column F (index 5) = post_type (PARENT/CHILD/STANDALONE)

        url = row[2] if len(row) > 2 else ""
        keyword = row[3] if len(row) > 3 else ""
        title = row[4] if len(row) > 4 else ""
        post_type = row[5] if len(row) > 5 else ""

        if not url or not url.startswith("http"):
            continue

        if post_type == "PARENT":
            parents.append((url, title, keyword))
        elif post_type == "CHILD":
            children.append((url, title, keyword))
        else:
            # STANDALONE or empty
            orphans.append((url, title, keyword))

    # Print results
    print("\n" + "="*100)
    print("🌳 PARENT ARTICLES (process LAST)")
    print("="*100)
    for idx, (url, title, keyword) in enumerate(parents, 1):
        print(f"{idx:2d}. {url}")
        print(f"    └─ {title}")
        if keyword:
            print(f"    └─ KW: {keyword}")

    print(f"\n\n👶 CHILD ARTICLES (process FIRST)")
    print("="*100)
    for idx, (url, title, keyword) in enumerate(children, 1):
        print(f"{idx:2d}. {url}")
        print(f"    └─ {title}")
        if keyword:
            print(f"    └─ KW: {keyword}")

    print(f"\n\n🔗 STANDALONE ARTICLES (no cocon)")
    print("="*100)
    for idx, (url, title, keyword) in enumerate(orphans, 1):
        print(f"{idx:2d}. {url}")
        print(f"    └─ {title}")
        if keyword:
            print(f"    └─ KW: {keyword}")

    print("\n" + "="*100)
    print("📈 SUMMARY")
    print("="*100)
    total = len(parents) + len(children) + len(orphans)
    print(f"Total:    {total:3d} URLs")
    print(f"Parents:  {len(parents):3d} ({len(parents)/total*100:5.1f}%) ← Process LAST")
    print(f"Children: {len(children):3d} ({len(children)/total*100:5.1f}%) ← Process FIRST")
    print(f"Orphans:  {len(orphans):3d} ({len(orphans)/total*100:5.1f}%)")
    print("="*100 + "\n")

    # Export order
    print("📝 RECOMMENDED PROCESSING ORDER:")
    print("="*100)
    print("\n1️⃣  PHASE 1: Children (execute first)")
    for idx, (url, title, _) in enumerate(children, 1):
        print(f"   {idx}. {url}")
        print(f"      {title}")

    print("\n2️⃣  PHASE 2: Standalone (no dependencies)")
    for idx, (url, title, _) in enumerate(orphans, 1):
        print(f"   {idx}. {url}")
        print(f"      {title}")

    print("\n3️⃣  PHASE 3: Parents (execute last)")
    for idx, (url, title, _) in enumerate(parents, 1):
        print(f"   {idx}. {url}")
        print(f"      {title}")
    print("="*100 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Quick PARENT/CHILD identification from spreadsheet"
    )
    parser.add_argument(
        "--spreadsheet-id",
        required=True,
        help="Google Spreadsheet ID"
    )
    parser.add_argument(
        "--sheet-name",
        default="Refreshs_Audit",
        help="Sheet name (default: Refreshs_Audit)"
    )

    args = parser.parse_args()

    try:
        quick_analyze(args.spreadsheet_id, args.sheet_name)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
