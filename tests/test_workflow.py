#!/usr/bin/env python3
"""
Test du workflow complet avec les URLs de la feuille URLs_Input.
"""

import os
import sys
from pathlib import Path

# Ajouter le répertoire au path
sys.path.insert(0, str(Path(__file__).parent))

from scripts.sheets.sheets_client import SheetsClient, TaskStatus

# Configuration
SPREADSHEET_ID = "1F99FtN8fWQlQm0ZTJphBRz_c64iDs2DvohyHyM2Tk1M"


def main():
    print("=" * 60)
    print("TEST WORKFLOW COMPLET - Content Writer")
    print("=" * 60)

    # Initialiser le client Sheets
    print("\n[1] Connexion à Google Sheets...")
    client = SheetsClient(SPREADSHEET_ID)

    if client._sheets_service is None:
        print("   ERREUR: Impossible de se connecter à Google Sheets API")
        print("   Vérifiez le fichier service account:")
        print(f"   {os.environ.get('GOOGLE_SA_PATH', '~/.credentials/google/google-service-account.json')}")
        return

    print("   OK: Connecté à Google Sheets")

    # Lire les URLs depuis URLs_Input
    print("\n[2] Lecture des URLs depuis la feuille URLs_Input...")
    data = client._read_sheet("URLs_Input")

    if not data:
        print("   ERREUR: Feuille vide ou inexistante")
        return

    print(f"   Trouvé {len(data)} lignes (incluant header)")

    # Afficher le header
    if data:
        print(f"   Header: {data[0]}")

    # Afficher les URLs (skip header)
    urls_data = data[1:] if len(data) > 1 else []

    if not urls_data:
        print("   Aucune URL à traiter")
        return

    # Nouvelle structure: url, title, site_slug, post_type, status, ...
    print(f"\n[3] URLs trouvées ({len(urls_data)}):")
    for i, row in enumerate(urls_data, 1):
        url = row[0] if row else "N/A"
        site_slug = row[2] if len(row) > 2 else "N/A"
        post_type = row[3] if len(row) > 3 else "N/A"
        status = row[4] if len(row) > 4 else "N/A"
        print(f"   {i}. {url}")
        print(f"      Blog: {site_slug} | Type: {post_type} | Status: {status}")

    # Filtrer les URLs PENDING
    pending_urls = []
    for i, row in enumerate(urls_data, 2):  # 2 car on skip header
        if len(row) >= 5:
            status = row[4]
            if status == "PENDING" or status == "":
                pending_urls.append({
                    "url": row[0],
                    "site_slug": row[2] if len(row) > 2 else "enseigna",
                    "post_type": row[3] if len(row) > 3 else "standalone",
                    "priority": 3,
                    "row_index": i
                })

    print(f"\n[4] URLs en attente (PENDING): {len(pending_urls)}")

    if not pending_urls:
        print("   Toutes les URLs ont déjà été traitées")
        # Montrer quand même les URLs pour test
        pending_urls = [
            {
                "url": row[0],
                "site_slug": row[2] if len(row) > 2 else "enseigna",
                "post_type": row[3] if len(row) > 3 else "standalone",
                "priority": 3,
                "row_index": i
            }
            for i, row in enumerate(urls_data, 2) if row
        ]
        print(f"   Utilisation de toutes les URLs pour le test: {len(pending_urls)}")

    # Tester le fetch HTTP pour chaque URL
    print("\n[5] Test de récupération des pages...")

    import requests

    for url_data in pending_urls:
        url = url_data["url"]
        print(f"\n   Fetching: {url}")
        try:
            response = requests.get(url, timeout=30, headers={
                "User-Agent": "Mozilla/5.0 (compatible; SEO-Refresh-Bot/1.0)"
            })
            response.raise_for_status()
            html_content = response.text

            print(f"   OK: {len(html_content)} caractères récupérés")
            print(f"   Status HTTP: {response.status_code}")

            # Analyser basiquement le HTML
            title_start = html_content.find("<title>")
            title_end = html_content.find("</title>")
            if title_start != -1 and title_end != -1:
                title = html_content[title_start+7:title_end]
                print(f"   Title: {title[:60]}...")

        except Exception as e:
            print(f"   ERREUR: {e}")

    # Test du workflow complet via l'orchestrateur
    print("\n[6] Test du workflow via l'orchestrateur...")

    try:
        from main import RefreshAgent

        agent = RefreshAgent(spreadsheet_id=SPREADSHEET_ID)
        print("   Agent initialisé")

        for url_data in pending_urls[:2]:  # Limiter à 2 pour le test
            url = url_data["url"]
            site_slug = url_data["site_slug"]

            print(f"\n   Processing: {url}")

            # Récupérer le HTML
            try:
                response = requests.get(url, timeout=30, headers={
                    "User-Agent": "Mozilla/5.0 (compatible; SEO-Refresh-Bot/1.0)"
                })
                html_content = response.text
            except Exception as e:
                print(f"   ERREUR fetch: {e}")
                continue

            # Traiter via l'agent
            try:
                result = agent.process_single_url(
                    url=url,
                    site_slug=site_slug,
                    html_content=html_content
                )

                print(f"   Résultat:")
                print(f"     Success: {result['success']}")
                print(f"     Action: {result['action']}")
                print(f"     Score: {result['score']}")
                if result.get('rewrite_type'):
                    print(f"     Rewrite type: {result['rewrite_type']}")
                if result.get('errors'):
                    print(f"     Errors: {result['errors']}")
                print(f"     Temps: {result['execution_time']:.2f}s")

            except Exception as e:
                print(f"   ERREUR workflow: {e}")
                import traceback
                traceback.print_exc()

    except ImportError as e:
        print(f"   ERREUR import: {e}")
        print("   Test simplifié sans orchestrateur complet")

    print("\n" + "=" * 60)
    print("TEST TERMINÉ")
    print("=" * 60)


if __name__ == "__main__":
    main()
