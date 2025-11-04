#!/usr/bin/env python3
"""
OAuth Authorization Script for Google Drive Integration

Run this script once to authorize the application to access your Google Drive.
This will open a browser window for you to sign in and grant permissions.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

import config

# Scopes for Google Drive and Docs access
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/documents",
]


def authorize():
    """Run OAuth authorization flow."""

    oauth_creds_path = os.path.join(config.DATA_PATH_FOLDER, "oauth_credentials.json")
    token_path = os.path.join(config.DATA_PATH_FOLDER, "token.json")

    # Check if OAuth credentials file exists
    if not os.path.exists(oauth_creds_path):
        print(f"\n❌ OAuth credentials file not found: {oauth_creds_path}")
        print("\nPlease follow these steps:")
        print("1. Go to Google Cloud Console")
        print("2. Create OAuth Client ID (Desktop app)")
        print("3. Download the JSON file")
        print(f"4. Save it as: {oauth_creds_path}")
        print("\nSee OAUTH_SETUP.md for detailed instructions.")
        return False

    print("\n=== Google Drive OAuth Authorization ===\n")
    print("This will open a browser window for you to sign in.")
    print("Please authorize the application to access your Google Drive.\n")

    creds = None

    # Check if we already have a token
    if os.path.exists(token_path):
        try:
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            print("✓ Found existing token")
        except Exception as e:
            print(f"⚠️  Could not load existing token: {e}")

    # If there are no (valid) credentials available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("⟳ Refreshing expired token...")
            try:
                creds.refresh(Request())
                print("✓ Token refreshed")
            except Exception as e:
                print(f"⚠️  Could not refresh token: {e}")
                print("   Will request new authorization...")
                creds = None

        if not creds:
            print("⟳ Starting OAuth flow...")
            print("   A browser window will open shortly...")
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    oauth_creds_path, SCOPES
                )
                creds = flow.run_local_server(port=0)
                print("✓ Authorization successful!")
            except Exception as e:
                print(f"\n❌ Authorization failed: {e}")
                return False

        # Save the credentials for the next run
        try:
            with open(token_path, "w") as token:
                token.write(creds.to_json())
            print(f"✓ Token saved to: {token_path}")
        except Exception as e:
            print(f"⚠️  Could not save token: {e}")
    else:
        print("✓ Token is valid")

    print("\n✅ Authorization complete!")
    print("\nYou can now use the Google Drive integration in the application.")
    print("The token will be automatically refreshed when needed.\n")

    return True


if __name__ == "__main__":
    try:
        success = authorize()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nAuthorization cancelled")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        sys.exit(1)
