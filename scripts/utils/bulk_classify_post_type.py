"""
Bulk PARENT/CHILD classification via STSEO Mindmaps API.

Source of truth: mindmaps structure from SuperTeamSEO API.
- URL found as branch parent → PARENT
- URL found as branch child  → CHILD
- URL not in any mindmap     → STANDALONE (category pages, orphans)

Usage:
    python scripts/utils/bulk_classify_post_type.py --start-row 96 --end-row 152
    python scripts/utils/bulk_classify_post_type.py --start-row 96 --end-row 152 --dry-run
    python scripts/utils/bulk_classify_post_type.py --start-row 96 --end-row 152 --blog mymusicteacher
"""

import sys
import json
from pathlib import Path

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import argparse
import requests
from dotenv import load_dotenv
import os

load_dotenv()

from scripts.sheets.sheets_client import SheetsClient

SPREADSHEET_ID = "1F99FtN8fWQlQm0ZTJphBRz_c64iDs2DvohyHyM2Tk1M"
SHEET_NAME = "Refreshs_Audit"

STSEO_BASE = "https://www.superteamseo.com/wp-json/sp/v1"

# PBN website IDs per blog
PBN_IDS = {
    "enseigna": 492,
    "cours-particuliers": 602,
    "educationetdevenir": 653,
    "moments-yoga": 15,
    "mymusicteacher": 610,
    "coachsportlyon": 17,
}


def get_stseo_auth():
    email = os.environ.get("STSEO_EMAIL", "")
    password = os.environ.get("STSEO_PASSWORD", "")
    return (email, password)


def build_url_type_map(blog_ids: list[str]) -> dict[str, str]:
    """
    Fetch mindmaps for the given blogs and build url → post_type mapping.
    """
    auth = get_stseo_auth()
    url_type = {}

    for blog_id in blog_ids:
        pbn_id = PBN_IDS.get(blog_id)
        if not pbn_id:
            print(f"  [WARN] Unknown blog_id: {blog_id}")
            continue

        resp = requests.get(
            f"{STSEO_BASE}/get_pbn_website_mindmaps",
            params={"pbn_website_id": pbn_id},
            auth=auth,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        mindmaps = data.get("mindmaps", [])
        print(f"  {blog_id}: {len(mindmaps)} mindmaps")

        for mm in mindmaps:
            for branch in mm.get("branches", []):
                parent_url = branch["parent"]["url"].rstrip("/")
                url_type[parent_url] = "PARENT"
                for child in branch.get("children", []):
                    child_url = child["url"].rstrip("/")
                    if child_url not in url_type:  # PARENT takes precedence
                        url_type[child_url] = "CHILD"

    return url_type


def get_domain_blog_id(url: str) -> str | None:
    """Map a URL's domain to a blog_id."""
    domain_map = {
        "enseigna.fr": "enseigna",
        "cours-particuliers.com": "cours-particuliers",
        "educationetdevenir.fr": "educationetdevenir",
        "moments-yoga.fr": "moments-yoga",
        "mymusicteacher.fr": "mymusicteacher",
        "coachsportlyon.fr": "coachsportlyon",
    }
    from urllib.parse import urlparse
    netloc = urlparse(url).netloc.replace("www.", "")
    return domain_map.get(netloc)


def classify_urls(start_row: int, end_row: int, dry_run: bool = False, blog_filter: str | None = None):
    sheets = SheetsClient(SPREADSHEET_ID)

    range_str = f"{SHEET_NAME}!A{start_row}:F{end_row}"
    print(f"Reading range: {range_str}")

    result = sheets._sheets_service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=range_str,
    ).execute()

    rows = result.get("values", [])
    print(f"Found {len(rows)} rows\n")

    # Collect unique blog_ids needed
    needed_blogs = set()
    for row in rows:
        url = row[2] if len(row) > 2 else ""
        if not url or not url.startswith("http"):
            continue
        blog_id = get_domain_blog_id(url)
        if blog_id and (not blog_filter or blog_id == blog_filter):
            needed_blogs.add(blog_id)

    print(f"Fetching mindmaps for: {', '.join(sorted(needed_blogs))}")
    url_type_map = build_url_type_map(list(needed_blogs))
    print(f"Loaded {len(url_type_map)} URLs from mindmaps\n")

    updates = []
    stats = {"PARENT": 0, "CHILD": 0, "STANDALONE": 0, "SKIP": 0, "ALREADY": 0}

    print(f"{'ROW':>4}  {'TYPE':12}  URL")
    print("-" * 90)

    for i, row in enumerate(rows):
        row_num = start_row + i
        url = row[2] if len(row) > 2 else ""
        existing_type = row[5] if len(row) > 5 else ""

        if not url or not url.startswith("http"):
            print(f"{row_num:>4}  {'SKIP':12}  (no URL)")
            stats["SKIP"] += 1
            continue

        if blog_filter and get_domain_blog_id(url) != blog_filter:
            print(f"{row_num:>4}  {'SKIP':12}  (filtered out) {url}")
            stats["SKIP"] += 1
            continue

        if existing_type in ("PARENT", "CHILD", "STANDALONE"):
            print(f"{row_num:>4}  {'ALREADY ' + existing_type:12}  {url}")
            stats["ALREADY"] += 1
            continue

        # Category pages → STANDALONE
        from urllib.parse import urlparse
        if "/category/" in urlparse(url).path:
            post_type = "STANDALONE"
        else:
            post_type = url_type_map.get(url.rstrip("/"), "STANDALONE")

        print(f"{row_num:>4}  {post_type:12}  {url}")
        stats[post_type] += 1
        updates.append({"range": f"{SHEET_NAME}!F{row_num}", "values": [[post_type]]})

    print(f"\n{'='*90}")
    print(f"RESULTS: {stats['PARENT']} PARENT  |  {stats['CHILD']} CHILD  |  {stats['STANDALONE']} STANDALONE  |  {stats['ALREADY']} already set  |  {stats['SKIP']} skipped")
    print(f"{'='*90}")

    if not dry_run and updates:
        sheets._sheets_service.spreadsheets().values().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body={"valueInputOption": "RAW", "data": updates},
        ).execute()
        print(f"\nWritten {len(updates)} cells to column F")
    elif dry_run:
        print("\n[DRY RUN] No changes written to spreadsheet")
    else:
        print("\nNo updates needed")


def main():
    parser = argparse.ArgumentParser(
        description="Bulk classify blog posts as PARENT/CHILD/STANDALONE via STSEO Mindmaps API"
    )
    parser.add_argument("--start-row", type=int, required=True)
    parser.add_argument("--end-row", type=int, required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--blog", default=None, help="Filter by blog_id (e.g. mymusicteacher)")

    args = parser.parse_args()
    classify_urls(args.start_row, args.end_row, args.dry_run, args.blog)


if __name__ == "__main__":
    main()
