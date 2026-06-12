"""
Run this script once to authenticate your Google account and generate a local token.
A browser tab will open — sign in with the Google account that has GSC access.
"""

import os
import sys

CREDENTIALS_FILE = os.path.expanduser('~/.credentials/google/credentials.json')
TOKEN_FILE = os.path.expanduser('~/.credentials/google/token.json')

SCOPES = [
    'https://www.googleapis.com/auth/webmasters.readonly',
    'https://www.googleapis.com/auth/spreadsheets',
]


def main():
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
    except ImportError:
        print("Missing dependencies. Run: pip install google-auth-oauthlib google-api-python-client")
        sys.exit(1)

    if not os.path.exists(CREDENTIALS_FILE):
        print(f"credentials.json not found at: {CREDENTIALS_FILE}")
        print("Ask your technical contact to send you the credentials.json file,")
        print(f"then place it at: {CREDENTIALS_FILE}")
        sys.exit(1)

    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing existing token...")
            creds.refresh(Request())
        else:
            print("Opening browser for Google authentication...")
            print("Sign in with the Google account that has access to Superprof US Search Console.\n")
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
        with open(TOKEN_FILE, 'w') as f:
            f.write(creds.to_json())
        print(f"\nToken saved to: {TOKEN_FILE}")

    # Verify access
    print("\nVerifying GSC access...")
    service = build('webmasters', 'v3', credentials=creds)
    sites = service.sites().list().execute()
    entries = sites.get('siteEntry', [])

    if not entries:
        print("Authentication worked, but no GSC properties are visible with this account.")
        print("Ask your technical contact to add your Google account to the Superprof US property in Search Console.")
    else:
        print("GSC properties accessible with your account:")
        for s in entries:
            print(f"  {s['siteUrl']} — {s['permissionLevel']}")
        print("\nSetup complete. You can now run the Content Writer system.")


if __name__ == '__main__':
    main()
