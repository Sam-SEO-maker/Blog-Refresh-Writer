"""
Quick script to identify PARENT vs CHILD articles from a list of URLs.

Usage:
    python scripts/utils/identify_parent_child.py --spreadsheet-id YOUR_SHEET_ID --sheet-name "Sheet1"

Or:
    python scripts/utils/identify_parent_child.py --urls-file urls.txt
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import argparse
from typing import List, Dict
from scripts.sheets.sheets_client import SheetsClient
from scripts.cocon.sibling_fetcher import SiblingFetcher


def analyze_from_spreadsheet(spreadsheet_id: str, sheet_name: str) -> Dict[str, List[str]]:
    """Analyze URLs directly from Google Spreadsheet."""
    print(f"📊 Fetching URLs from spreadsheet: {sheet_name}...")

    sheets_client = SheetsClient()
    sibling_fetcher = SiblingFetcher(sheets_client=sheets_client)

    # Fetch all rows
    rows = sheets_client.read_range(spreadsheet_id, f"{sheet_name}!A2:Z")

    parents = []
    children = []
    orphans = []

    print(f"🔍 Analyzing {len(rows)} URLs...\n")

    for idx, row in enumerate(rows, start=2):
        if len(row) < 2:
            continue

        url = row[2] if len(row) > 2 else ""  # Column C

        if not url or not url.startswith("http"):
            continue

        # Fetch siblings for this URL
        siblings = sibling_fetcher.fetch_siblings(url, spreadsheet_id, sheet_name)

        # Determine role
        if siblings.parent_url and siblings.sibling_articles:
            # Has both parent AND siblings → unusual case
            children.append(f"{url} (has parent: {siblings.parent_url}, but also {len(siblings.sibling_articles)} siblings)")
        elif siblings.parent_url:
            # Has parent → CHILD
            children.append(f"{url} → parent: {siblings.parent_url}")
        elif siblings.sibling_articles:
            # Has siblings but no parent → PARENT
            parents.append(f"{url} ({len(siblings.sibling_articles)} children)")
        else:
            # No parent, no siblings → ORPHAN
            orphans.append(url)

    return {
        "parents": parents,
        "children": children,
        "orphans": orphans
    }


def analyze_from_file(urls_file: str, spreadsheet_id: str, sheet_name: str) -> Dict[str, List[str]]:
    """Analyze URLs from a text file (one URL per line)."""
    print(f"📄 Reading URLs from file: {urls_file}...")

    with open(urls_file, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip() and line.startswith("http")]

    print(f"🔍 Analyzing {len(urls)} URLs...\n")

    sheets_client = SheetsClient()
    sibling_fetcher = SiblingFetcher(sheets_client=sheets_client)

    parents = []
    children = []
    orphans = []

    for url in urls:
        siblings = sibling_fetcher.fetch_siblings(url, spreadsheet_id, sheet_name)

        if siblings.parent_url and siblings.sibling_articles:
            children.append(f"{url} (has parent: {siblings.parent_url}, but also {len(siblings.sibling_articles)} siblings)")
        elif siblings.parent_url:
            children.append(f"{url} → parent: {siblings.parent_url}")
        elif siblings.sibling_articles:
            parents.append(f"{url} ({len(siblings.sibling_articles)} children)")
        else:
            orphans.append(url)

    return {
        "parents": parents,
        "children": children,
        "orphans": orphans
    }


def print_results(results: Dict[str, List[str]]):
    """Pretty print the analysis results."""
    print("\n" + "="*80)
    print("📊 ANALYSIS RESULTS")
    print("="*80 + "\n")

    print(f"🌳 PARENT ARTICLES ({len(results['parents'])} total)")
    print("-" * 80)
    if results['parents']:
        for parent in results['parents']:
            print(f"  ✓ {parent}")
    else:
        print("  (none)")

    print(f"\n👶 CHILD ARTICLES ({len(results['children'])} total)")
    print("-" * 80)
    if results['children']:
        for child in results['children']:
            print(f"  ✓ {child}")
    else:
        print("  (none)")

    print(f"\n🔗 ORPHAN ARTICLES ({len(results['orphans'])} total)")
    print("-" * 80)
    if results['orphans']:
        for orphan in results['orphans']:
            print(f"  ⚠️  {orphan}")
    else:
        print("  (none)")

    print("\n" + "="*80)
    print("📈 SUMMARY")
    print("="*80)
    total = len(results['parents']) + len(results['children']) + len(results['orphans'])
    print(f"  Total URLs: {total}")
    print(f"  Parents: {len(results['parents'])} ({len(results['parents'])/total*100:.1f}%)")
    print(f"  Children: {len(results['children'])} ({len(results['children'])/total*100:.1f}%)")
    print(f"  Orphans: {len(results['orphans'])} ({len(results['orphans'])/total*100:.1f}%)")
    print("="*80 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Identify PARENT vs CHILD articles from URLs"
    )

    # Input source
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--spreadsheet-id",
        help="Google Spreadsheet ID to analyze"
    )
    input_group.add_argument(
        "--urls-file",
        help="Text file with URLs (one per line)"
    )

    # Spreadsheet details
    parser.add_argument(
        "--sheet-name",
        default="Refreshs_Audit",
        help="Sheet name (default: Refreshs_Audit)"
    )

    args = parser.parse_args()

    try:
        if args.spreadsheet_id:
            results = analyze_from_spreadsheet(args.spreadsheet_id, args.sheet_name)
        else:
            # For file input, we still need a spreadsheet ID to fetch sibling data
            print("\n⚠️  For file input, you need to specify a spreadsheet to fetch sibling relationships.")
            print("Please provide --spreadsheet-id as well.")
            sys.exit(1)

        print_results(results)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
