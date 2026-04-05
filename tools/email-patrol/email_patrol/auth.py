"""OAuth 2.0 authentication for Gmail API.

Usage:
    python -m email_patrol.auth          # First-time: opens browser for consent
    python -m email_patrol.auth --check  # Verify existing token is valid
"""

import json
import os
import sys
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.labels",
]

DEFAULT_CREDENTIALS_PATH = Path(__file__).parent.parent / "credentials.json"
DEFAULT_TOKEN_PATH = Path(__file__).parent.parent / "token.json"


def get_credentials(
    credentials_path: Path = DEFAULT_CREDENTIALS_PATH,
    token_path: Path = DEFAULT_TOKEN_PATH,
) -> Credentials:
    """Load or refresh OAuth credentials. Opens browser if no token exists."""
    # Railway deployment: read token from environment variable
    env_token = os.environ.get("GOOGLE_TOKEN")
    if env_token:
        token_data = json.loads(env_token)
        creds = Credentials.from_authorized_user_info(token_data, SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
        return creds

    creds = None

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_path.write_text(creds.to_json())
        return creds

    if creds and creds.valid:
        return creds

    if not credentials_path.exists():
        print(f"ERROR: {credentials_path} not found.")
        print("Download it from Google Cloud Console > Credentials > OAuth client ID")
        sys.exit(1)

    flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
    creds = flow.run_local_server(port=0)
    token_path.write_text(creds.to_json())
    print(f"Token saved to {token_path}")
    return creds


def check_token(token_path: Path = DEFAULT_TOKEN_PATH) -> bool:
    """Check if existing token is valid."""
    if not token_path.exists():
        print("No token.json found. Run: python -m email_patrol.auth")
        return False
    creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if creds.valid:
        print("Token is valid.")
        return True
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_path.write_text(creds.to_json())
        print("Token refreshed successfully.")
        return True
    print("Token is invalid. Re-run: python -m email_patrol.auth")
    return False


if __name__ == "__main__":
    if "--check" in sys.argv:
        check_token()
    else:
        creds = get_credentials()
        print(f"Authenticated. Token valid: {creds.valid}")
