"""Check all sheets and URLs in spreadsheet"""
import sys
from pathlib import Path

# Fix Windows encoding
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.sheets.sheets_client import SheetsClient

spreadsheet_id = '1F99FtN8fWQlQm0ZTJphBRz_c64iDs2DvohyHyM2Tk1M'
client = SheetsClient(spreadsheet_id)

# Get all sheets
sheet_metadata = client._sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
sheets = sheet_metadata.get('sheets', [])

print('📊 Onglets disponibles dans le spreadsheet:')
print('='*80)

total_urls = 0
sheet_stats = []

for sheet in sheets:
    title = sheet.get('properties', {}).get('title', 'Unknown')

    try:
        # For Refreshs_Audit, URLs are in column C (after cocon_branch in B)
        # For other sheets, URLs are in column B
        if title == 'Refreshs_Audit':
            col_range = f"{title}!C2:F"
        else:
            col_range = f"{title}!B2:E"

        result = client._sheets_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=col_range
        ).execute()

        rows = result.get('values', [])
        urls = [row[0] for row in rows if len(row) > 0 and row[0].startswith('http')]

        # Count post types
        parents = sum(1 for row in rows if len(row) > 3 and row[3] == 'PARENT')
        children = sum(1 for row in rows if len(row) > 3 and row[3] == 'CHILD')
        standalone = sum(1 for row in rows if len(row) > 3 and row[3] == 'STANDALONE')

        url_count = len(urls)
        total_urls += url_count

        print(f'  ✓ {title}: {url_count} URLs')
        if url_count > 0:
            print(f'      PARENT: {parents}, CHILD: {children}, STANDALONE: {standalone}')

        sheet_stats.append({
            'name': title,
            'urls': url_count,
            'parents': parents,
            'children': children,
            'standalone': standalone
        })

    except Exception as e:
        print(f'  ⚠️  {title}: Cannot read (error: {str(e)[:50]})')

print('='*80)
print(f'\n📈 Total URLs: {total_urls}')
print('\n📊 Répartition globale:')

total_parents = sum(s['parents'] for s in sheet_stats)
total_children = sum(s['children'] for s in sheet_stats)
total_standalone = sum(s['standalone'] for s in sheet_stats)

print(f'  PARENT:     {total_parents:3d}')
print(f'  CHILD:      {total_children:3d}')
print(f'  STANDALONE: {total_standalone:3d}')
print('='*80)
