"""Yoto OAuth: loopback browser login (PKCE) and serialized refresh-token rotation.

Facts this relies on (verified 2026-11-07 on the Hilo cards):

* The Yoto app is a confidential client: token calls need ``client_secret``.
* Only ``user:content:manage offline_access`` is pre-approved; ``openid profile`` is refused.
* There is no id_token. The access token is a JWT whose ``sub`` names the account.
* Refresh tokens rotate on every use, so refreshes for one account are serialized (a thread
  lock plus an flock on ``~/.yoto/locks/<account>.lock`` across processes) and the new token
  is saved before the access token is used.
"""

from __future__ import annotations

import base64
import fcntl
import hashlib
import json
import secrets
import threading
import time
import urllib.parse
import webbrowser
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer

import httpx

from . import paths, vault

LOGIN = "https://login.yotoplay.com"
AUDIENCE = "https://api.yotoplay.com"
SCOPE = "user:content:manage offline_access"
REFRESH_MARGIN = 300  # seconds before expiry that a cached access token is replaced


class NeedsLogin(RuntimeError):
    """The account has no usable refresh token; the user has to log in again."""


def jwt_claims(token: str) -> dict:
    """Decode a JWT payload without verifying it (Yoto verifies it; we only read ``sub``/``exp``)."""
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload))
    except (IndexError, ValueError) as exc:
        raise ValueError("Access token is not a JWT") from exc


def _require_client_id() -> str:
    cid = vault.client_id()
    if not cid:
        raise NeedsLogin("No Yoto client id is stored. Run `yoto-mcp setup` first.")
    return cid


def token_request(data: dict, http: httpx.Client | None = None) -> dict:
    body = {**data, "client_id": _require_client_id()}
    if secret := vault.client_secret():
        body["client_secret"] = secret
    client = http or httpx.Client(timeout=30)
    resp = client.post(f"{LOGIN}/oauth/token", data=body)
    payload = resp.json() if resp.content else {}
    if resp.status_code != 200:
        err = payload.get("error", f"HTTP {resp.status_code}")
        desc = payload.get("error_description", "")
        if resp.status_code in (400, 401, 403) and err in ("invalid_grant", "access_denied"):
            raise NeedsLogin(f"Yoto refused the token request ({err}: {desc}). Log in again.")
        raise RuntimeError(f"Token request failed: {err} {desc}".strip())
    return payload


# ------------------------------------------------------------------ token cache


@dataclass
class _Cached:
    token: str
    expires_at: float


class TokenManager:
    """Hands out access tokens per account, refreshing at most one at a time per account."""

    def __init__(self, http: httpx.Client | None = None, clock: Callable[[], float] = time.time):
        self._http = http
        self._clock = clock
        self._cache: dict[str, _Cached] = {}
        self._locks: dict[str, threading.Lock] = {}
        self._guard = threading.Lock()

    def _lock(self, sub: str) -> threading.Lock:
        with self._guard:
            return self._locks.setdefault(sub, threading.Lock())

    @contextmanager
    def _file_lock(self, sub: str):
        name = hashlib.sha256(sub.encode()).hexdigest()[:16]
        with open(paths.locks() / f"{name}.lock", "w") as fh:
            fcntl.flock(fh, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(fh, fcntl.LOCK_UN)

    def remember(self, sub: str, access_token: str, expires_in: int | None) -> None:
        exp = jwt_claims(access_token).get("exp") or (self._clock() + (expires_in or 3600))
        self._cache[sub] = _Cached(access_token, float(exp))

    def access_token(self, sub: str) -> str:
        cached = self._cache.get(sub)
        if cached and cached.expires_at - self._clock() > REFRESH_MARGIN:
            return cached.token
        with self._lock(sub), self._file_lock(sub):
            cached = self._cache.get(sub)
            if cached and cached.expires_at - self._clock() > REFRESH_MARGIN:
                return cached.token
            # Read inside the lock: another process may have rotated it since we last looked.
            refresh = vault.refresh_token(sub)
            if not refresh:
                raise NeedsLogin("This account has no saved login. Run `yoto-mcp login`.")
            tokens = token_request({"grant_type": "refresh_token", "refresh_token": refresh}, self._http)
            if tokens.get("refresh_token"):
                vault.save_refresh_token(sub, tokens["refresh_token"])
            self.remember(sub, tokens["access_token"], tokens.get("expires_in"))
            return tokens["access_token"]


# ------------------------------------------------------------------ browser login


@dataclass
class LoginResult:
    sub: str
    access_token: str
    expires_in: int | None


def authorize_url(redirect_uri: str, challenge: str, state: str, force_login: bool) -> str:
    params = {
        "response_type": "code",
        "client_id": _require_client_id(),
        "redirect_uri": redirect_uri,
        "audience": AUDIENCE,
        "scope": SCOPE,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": state,
    }
    if force_login:
        params["prompt"] = "login"
    return f"{LOGIN}/authorize?" + urllib.parse.urlencode(params)


class LoginFlow:
    """One-shot loopback listener on the registered redirect URI.

    ``start()`` binds the port and returns the URL to open; ``wait()`` blocks until the
    callback arrives and the refresh token is saved under the account's ``sub``.
    """

    def __init__(self, redirect_uri: str | None = None, force_login: bool = False):
        self.redirect_uri = redirect_uri or vault.redirect_uri()
        self.force_login = force_login
        self._verifier = secrets.token_urlsafe(64)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(self._verifier.encode()).digest())
        self._state = secrets.token_urlsafe(16)
        self.url = authorize_url(self.redirect_uri, challenge.rstrip(b"=").decode(), self._state, force_login)
        self._result: dict = {}
        self._done = threading.Event()
        self._server: HTTPServer | None = None

    def start(self, open_browser: bool = True) -> str:
        parsed = urllib.parse.urlparse(self.redirect_uri)
        port = parsed.port or 80
        callback_path = parsed.path or "/"
        flow = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                url = urllib.parse.urlparse(self.path)
                if url.path != callback_path:
                    self.send_response(302)
                    self.send_header("Location", flow.url)
                    self.end_headers()
                    return
                q = {k: v[0] for k, v in urllib.parse.parse_qs(url.query).items()}
                flow._handle_callback(q)
                ok = "login" in flow._result
                msg = (
                    "Yoto login complete. You can close this tab."
                    if ok
                    else (f"Login failed: {flow._result.get('error')}")
                )
                self.send_response(200 if ok else 400)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(f"<html><body><h2>{msg}</h2></body></html>".encode())

            def log_message(self, format, *args):  # noqa: A002
                pass

        # macOS only lets unprivileged processes bind ports below 1024 on all interfaces.
        host = "" if port < 1024 else "127.0.0.1"
        try:
            self._server = HTTPServer((host, port), Handler)
        except OSError as exc:
            raise RuntimeError(
                f"Can't listen on port {port} for the Yoto login callback ({exc.strerror}). "
                f"Free the port, or register another callback URL on your Yoto app and set it "
                f"with YOTO_REDIRECT_URI (currently {self.redirect_uri})."
            ) from exc
        threading.Thread(target=self._serve, daemon=True).start()
        if open_browser:
            webbrowser.open(self.url)
        return self.url

    def _serve(self, give_up_after: float = 600) -> None:
        """Answer requests until the callback arrives, or free the port after 10 minutes."""
        assert self._server is not None
        self._server.timeout = 1
        deadline = time.monotonic() + give_up_after
        while not self._done.is_set():
            if time.monotonic() > deadline:
                self._result["error"] = "No login callback within 10 minutes; start the login again."
                self._done.set()
                break
            self._server.handle_request()
        self._server.server_close()

    def _handle_callback(self, q: dict) -> None:
        try:
            if q.get("state") != self._state:
                raise RuntimeError("state mismatch")
            if "error" in q:
                raise RuntimeError(f"{q['error']}: {q.get('error_description', '')}")
            tokens = token_request(
                {
                    "grant_type": "authorization_code",
                    "code": q.get("code", ""),
                    "code_verifier": self._verifier,
                    "redirect_uri": self.redirect_uri,
                }
            )
            if not tokens.get("refresh_token"):
                raise RuntimeError("Yoto returned no refresh token (is offline_access granted?)")
            sub = jwt_claims(tokens["access_token"])["sub"]
            vault.save_refresh_token(sub, tokens["refresh_token"])
            self._result["login"] = LoginResult(sub, tokens["access_token"], tokens.get("expires_in"))
        except Exception as exc:  # reported to the browser and to wait()
            self._result["error"] = str(exc)
        finally:
            self._done.set()

    def wait(self, timeout: float | None = None) -> LoginResult:
        if not self._done.wait(timeout):
            raise TimeoutError("No Yoto login callback arrived in time.")
        if "error" in self._result:
            raise RuntimeError(self._result["error"])
        return self._result["login"]

    @property
    def done(self) -> bool:
        return self._done.is_set()

    def result(self) -> LoginResult | None:
        return self._result.get("login")

    def error(self) -> str | None:
        return self._result.get("error")
