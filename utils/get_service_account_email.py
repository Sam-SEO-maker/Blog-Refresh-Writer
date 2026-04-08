#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Affiche l'email du service account pour le partage Google Sheets.
"""

import json
import sys
from pathlib import Path

# Force UTF-8 pour Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

import os
SERVICE_ACCOUNT_PATH = Path(os.environ.get("GOOGLE_SA_PATH", "~/.credentials/google/google-service-account.json")).expanduser()

def main():
    print("\n" + "=" * 60)
    print("📧 EMAIL DU SERVICE ACCOUNT")
    print("=" * 60)

    if not SERVICE_ACCOUNT_PATH.exists():
        print(f"❌ Service account introuvable: {SERVICE_ACCOUNT_PATH}")
        return

    try:
        with open(SERVICE_ACCOUNT_PATH, 'r') as f:
            data = json.load(f)

        email = data.get('client_email')
        project_id = data.get('project_id')

        print(f"\n✅ Service account trouvé")
        print(f"\n📧 Email: {email}")
        print(f"🆔 Project ID: {project_id}")

        print("\n" + "=" * 60)
        print("📝 ÉTAPES POUR PARTAGER LE SPREADSHEET")
        print("=" * 60)
        print("\n1. Ouvrir le spreadsheet dans Google Sheets")
        print("2. Cliquer sur le bouton 'Partager' (en haut à droite)")
        print("3. Ajouter cet email:")
        print(f"\n   📧 {email}")
        print("\n4. Sélectionner 'Éditeur' dans les permissions")
        print("5. Cliquer sur 'Envoyer'")
        print("\n6. Relancer le test: python test_sheets_connection.py")
        print("=" * 60)

    except Exception as e:
        print(f"❌ Erreur lors de la lecture du fichier: {e}")


if __name__ == "__main__":
    main()
