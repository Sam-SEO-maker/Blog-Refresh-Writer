"""
Fetch H1 titles from child articles to build PARENT H2 whitelist
"""

import sys
from pathlib import Path
import re

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from scripts.wordpress.stseo_client import STSEOClient

# Child article URLs
child_urls = [
    "https://cours-particuliers.com/combien-de-temps-pour-apprendre-langlais-en-angleterre/",
    "https://cours-particuliers.com/les-meilleures-villes-ou-apprendre-langlais-en-angleterre/",
    "https://cours-particuliers.com/les-meilleurs-sejours-linguistiques-a-faire-en-angleterre/",
    "https://cours-particuliers.com/quel-budget-prevoir-pour-apprendre-langlais-en-angleterre/",
]

def extract_h1(html: str) -> str:
    """Extract H1 from HTML."""
    h1_match = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.I | re.S)
    if not h1_match:
        return ""

    # Clean H1 (remove HTML tags)
    h1 = re.sub(r'<[^>]+>', '', h1_match.group(1))
    h1 = re.sub(r'\s+', ' ', h1).strip()
    return h1

def main():
    client = STSEOClient()

    print("="*70)
    print("RÉCUPÉRATION DES H1 ENFANTS (Whitelist PARENT)")
    print("="*70)
    print()

    mandatory_h2s = []

    for i, url in enumerate(child_urls, 1):
        print(f"[{i}/4] Fetching: {url[:60]}...")

        try:
            result = client.get_post_content_by_link(url)
            if not result or result.get("error") or not result.get("post_content"):
                print(f"  [ERROR] Failed to fetch")
                continue

            h1 = extract_h1(result["post_content"])
            if not h1:
                print(f"  [ERROR] No H1 found")
                continue

            mandatory_h2s.append(h1)
            print(f"  [OK] H1: {h1}")

        except Exception as e:
            print(f"  [ERROR] Error: {str(e)[:50]}")

    print()
    print("="*70)
    print("WHITELIST H2 OBLIGATOIRE (Article PARENT)")
    print("="*70)
    print()

    for i, h2 in enumerate(mandatory_h2s, 1):
        print(f"{i}. {h2}")

    print()
    print(f"TOTAL: {len(mandatory_h2s)} H2 obligatoires")
    print()

    # Save to file for easy copy-paste
    output_file = project_root / "_shared" / "context" / "parent_h2_whitelist.txt"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# WHITELIST H2 OBLIGATOIRE - Article PARENT\n")
        f.write("# Apprendre l'anglais au Royaume-Uni\n\n")
        for i, h2 in enumerate(mandatory_h2s, 1):
            f.write(f"{i}. {h2}\n")

    print(f"[OK] Whitelist sauvegardée: {output_file}")

if __name__ == "__main__":
    main()
