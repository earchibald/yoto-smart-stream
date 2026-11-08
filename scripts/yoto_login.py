#!/usr/bin/env python3
"""One-shot Yoto OAuth login via browser redirect (authorization code + PKCE).

Starts a tiny local server on the callback URL, opens the Yoto login page in
your browser, exchanges the returned code for tokens, and saves the refresh
token to ``.yoto_refresh_token`` (what the other scripts read). The server
exits as soon as the callback arrives.

The redirect URI must be registered as an Allowed Callback URL on your Yoto app
at https://yoto.dev/ (default: http://localhost:8080/oauth/callback, as listed
in docs/YOTO_APP_REGISTRATION.md).

Usage:
    export YOTO_CLIENT_ID=...
    python scripts/yoto_login.py [--port 8080] [--no-browser]
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import os
import secrets
import sys
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import requests

LOGIN = "https://login.yotoplay.com"
AUDIENCE = "https://api.yotoplay.com"
SCOPE = "openid profile offline_access"
TOKEN_FILE = Path(".yoto_refresh_token")
CALLBACK_PATH = "/oauth/callback"


def login(client_id: str, port: int = 8080, open_browser: bool = True,
          token_file: Path = TOKEN_FILE) -> dict:
    """Run the redirect login and return the token response (refresh token saved)."""
    redirect_uri = f"http://localhost:{port}{CALLBACK_PATH}"
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = secrets.token_urlsafe(16)
    authorize_url = f"{LOGIN}/authorize?" + urllib.parse.urlencode(
        {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "audience": AUDIENCE,
            "scope": SCOPE,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "state": state,
        }
    )
    result: dict = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            url = urllib.parse.urlparse(self.path)
            if url.path != CALLBACK_PATH:
                self.send_response(302)
                self.send_header("Location", authorize_url)
                self.end_headers()
                return
            q = {k: v[0] for k, v in urllib.parse.parse_qs(url.query).items()}
            if q.get("state") != state:
                result["error"] = "state mismatch"
            elif "error" in q:
                result["error"] = f"{q['error']}: {q.get('error_description', '')}"
            else:
                resp = requests.post(
                    f"{LOGIN}/oauth/token",
                    data={
                        "grant_type": "authorization_code",
                        "client_id": client_id,
                        "code": q.get("code", ""),
                        "code_verifier": verifier,
                        "redirect_uri": redirect_uri,
                    },
                    timeout=30,
                )
                body = resp.json() if resp.content else {}
                if resp.status_code == 200 and body.get("refresh_token"):
                    result["tokens"] = body
                else:
                    result["error"] = f"token exchange HTTP {resp.status_code}: {body or resp.text}"
            ok = "tokens" in result
            msg = "Yoto login complete — you can close this tab." if ok else f"Login failed: {result['error']}"
            self.send_response(200 if ok else 400)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(f"<html><body><h2>{msg}</h2></body></html>".encode())

        def log_message(self, format, *args):  # noqa: A002
            pass

    server = HTTPServer(("localhost", port), Handler)
    print(f"Login launcher listening on http://localhost:{port}/")
    print(f"Open this to log in (or just visit http://localhost:{port}/):\n  {authorize_url}\n", flush=True)
    if open_browser:
        webbrowser.open(authorize_url)
    while not result:
        server.handle_request()
    server.server_close()

    if "error" in result:
        raise RuntimeError(result["error"])
    token_file.write_text(result["tokens"]["refresh_token"])
    token_file.chmod(0o600)
    print(f"✓ Logged in; refresh token saved to {token_file.resolve()}")
    return result["tokens"]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()
    client_id = os.environ.get("YOTO_CLIENT_ID")
    if not client_id:
        sys.exit("YOTO_CLIENT_ID is not set")
    login(client_id, port=args.port, open_browser=not args.no_browser)


if __name__ == "__main__":
    main()
