from __future__ import annotations

import socket
import urllib.parse

import httpx

from yoto_mcp import auth, vault
from yoto_mcp.session import Session

from .fake_yoto import make_jwt


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_loopback_login_links_account_by_jwt_sub(monkeypatch):
    seen = {}

    def fake_token_request(data, http=None):
        seen.update(data)
        return {"access_token": make_jwt("auth0|new-user", 9e9), "refresh_token": "rt-1", "expires_in": 60}

    monkeypatch.setattr(auth, "token_request", fake_token_request)
    port = _free_port()
    monkeypatch.setenv("YOTO_REDIRECT_URI", f"http://localhost:{port}/oauth/callback")
    s = Session()
    url = s.start_login("Family", open_browser=False)
    params = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(url).query))
    assert params["scope"] == "user:content:manage offline_access"
    assert params["code_challenge_method"] == "S256" and "prompt" not in params
    resp = httpx.get(
        f"http://127.0.0.1:{port}/oauth/callback", params={"state": params["state"], "code": "abc"}
    )
    assert resp.status_code == 200 and "complete" in resp.text
    flow, _ = s.pending_logins["Family"]
    flow.wait(5)
    assert s.finish_logins() == ["Linked account 'Family'."]
    assert seen["grant_type"] == "authorization_code" and seen["code"] == "abc"
    assert vault.refresh_token("auth0|new-user") == "rt-1"
    assert vault.find_account(None).name == "Family"


def test_wrong_state_is_refused(monkeypatch):
    port = _free_port()
    monkeypatch.setenv("YOTO_REDIRECT_URI", f"http://localhost:{port}/oauth/callback")
    flow = auth.LoginFlow()
    flow.start(open_browser=False)
    resp = httpx.get(f"http://127.0.0.1:{port}/oauth/callback", params={"state": "nope", "code": "x"})
    assert resp.status_code == 400 and "state mismatch" in resp.text


def test_busy_port_names_the_uri(monkeypatch):
    with socket.socket() as busy:
        busy.bind(("127.0.0.1", 0))
        busy.listen()
        port = busy.getsockname()[1]
        monkeypatch.setenv("YOTO_REDIRECT_URI", f"http://localhost:{port}/oauth/callback")
        try:
            auth.LoginFlow().start(open_browser=False)
        except RuntimeError as exc:
            assert "YOTO_REDIRECT_URI" in str(exc) and str(port) in str(exc)
        else:  # pragma: no cover
            raise AssertionError("expected a busy-port error")
