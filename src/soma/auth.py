"""
WHOOP OAuth2 flow. Run automatically when token is missing or invalid.
"""
import os
import re
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

import requests
from dotenv import load_dotenv, set_key

from .config import ENV_PATH

load_dotenv(ENV_PATH)

REDIRECT_URI = "http://localhost:8080"


def _save_tokens(tokens: dict):
    """Save access and refresh tokens to .env."""
    content = ENV_PATH.read_text() if ENV_PATH.exists() else ""
    for key, val in [
        ("WHOOP_ACCESS_TOKEN", tokens.get("access_token", "")),
        ("WHOOP_REFRESH_TOKEN", tokens.get("refresh_token", "")),
    ]:
        if key in content:
            content = re.sub(rf"^{key}=.*$", f"{key}={val}", content, flags=re.MULTILINE)
        else:
            content += f"\n{key}={val}\n"
    ENV_PATH.parent.mkdir(parents=True, exist_ok=True)
    ENV_PATH.write_text(content)
    os.environ["WHOOP_ACCESS_TOKEN"] = tokens.get("access_token", "")
    os.environ["WHOOP_REFRESH_TOKEN"] = tokens.get("refresh_token", "")


def refresh_token():
    """Refresh access token using refresh_token. Saves new tokens to .env."""
    resp = requests.post(
        "https://api.prod.whoop.com/oauth/oauth2/token",
        data={
            "grant_type": "refresh_token",
            "refresh_token": os.getenv("WHOOP_REFRESH_TOKEN"),
            "client_id": os.getenv("WHOOP_CLIENT_ID"),
            "client_secret": os.getenv("WHOOP_CLIENT_SECRET"),
        },
    )
    resp.raise_for_status()
    tokens = resp.json()
    set_key(ENV_PATH, "WHOOP_ACCESS_TOKEN", tokens["access_token"])
    set_key(ENV_PATH, "WHOOP_REFRESH_TOKEN", tokens["refresh_token"])
    os.environ["WHOOP_ACCESS_TOKEN"] = tokens["access_token"]
    os.environ["WHOOP_REFRESH_TOKEN"] = tokens["refresh_token"]
    print("🔄 Token refreshed.")


def refresh_if_needed():
    """If token exists but returns 401, refresh automatically."""
    token = os.getenv("WHOOP_ACCESS_TOKEN")
    if not token:
        return False
    resp = requests.get(
        "https://api.prod.whoop.com/developer/v2/user/profile/basic",
        headers={"Authorization": f"Bearer {token}"},
    )
    if resp.status_code == 401:
        refresh_token()
        return True
    return False


def ensure_authenticated():
    """Ensure WHOOP is authenticated. Run auth flow if token missing or invalid."""
    token = os.getenv("WHOOP_ACCESS_TOKEN")
    if not token:
        run_auth_flow()
        load_dotenv(ENV_PATH)
        return
    try:
        resp = requests.get(
            "https://api.prod.whoop.com/developer/v2/user/profile/basic",
            headers={"Authorization": f"Bearer {token}"},
        )
        if resp.status_code == 401:
            refresh_token()
    except Exception:
        run_auth_flow()
        load_dotenv(ENV_PATH)


def run_auth_flow():
    """
    Opens browser → spins up local server on port 8080 → catches redirect →
    exchanges code for tokens → saves to config/.env automatically.
    """
    client_id = os.getenv("WHOOP_CLIENT_ID")
    client_secret = os.getenv("WHOOP_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise ValueError("WHOOP_CLIENT_ID and WHOOP_CLIENT_SECRET required in config/.env")

    auth_url = (
        "https://api.prod.whoop.com/oauth/oauth2/auth"
        f"?client_id={client_id}"
        f"&redirect_uri={REDIRECT_URI}"
        "&response_type=code"
        "&scope=offline read:profile read:recovery read:cycles read:sleep read:workout"
        "&state=12345678"
    )

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            code = parse_qs(urlparse(self.path).query).get("code", [None])[0]
            if not code:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"No code found.")
                return

            resp = requests.post(
                "https://api.prod.whoop.com/oauth/oauth2/token",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": REDIRECT_URI,
                },
            )
            resp.raise_for_status()
            tokens = resp.json()
            _save_tokens(tokens)

            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h2>Done! You can close this tab and go back to the terminal.</h2>")

    print("🔐 WHOOP not connected. Starting authorization...")
    webbrowser.open(auth_url)
    print("Waiting for WHOOP to redirect back...")
    HTTPServer(("localhost", 8080), Handler).handle_request()
    print("✅ Authorization complete. Tokens saved.")
