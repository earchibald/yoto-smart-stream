from __future__ import annotations

import threading

import httpx
import pytest

from yoto_mcp import refs, vault
from yoto_mcp.api import YotoAPI, YotoError
from yoto_mcp.auth import NeedsLogin, TokenManager, jwt_claims

from .conftest import OWNER_A, OWNER_B
from .fake_yoto import FakeYoto, make_jwt


def _api(fake: FakeYoto, sub: str) -> tuple[YotoAPI, TokenManager]:
    http = httpx.Client(transport=fake.transport())
    tm = TokenManager(http, clock=lambda: fake.now)
    vault.save_refresh_token(sub, fake.add_account(sub))
    return YotoAPI(sub, tm, http, sleep=lambda _s: None), tm


def test_jwt_sub_names_the_account():
    assert jwt_claims(make_jwt("auth0|abc", 5))["sub"] == "auth0|abc"


def test_refresh_rotates_and_saves_before_use(fake):
    api, tm = _api(fake, OWNER_A)
    first = vault.refresh_token(OWNER_A)
    api.list_mine()
    second = vault.refresh_token(OWNER_A)
    assert second != first and second in fake.refresh  # the rotated token is the live one
    api.list_mine()
    assert fake.token_calls == 1  # cached access token reused


def test_concurrent_calls_refresh_once(fake):
    api, tm = _api(fake, OWNER_A)
    errors = []

    def call():
        try:
            tm.access_token(OWNER_A)
        except Exception as exc:  # pragma: no cover - would fail the assert below
            errors.append(exc)

    threads = [threading.Thread(target=call) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors
    assert fake.token_calls == 1


def test_reused_refresh_token_asks_for_login(fake):
    _api_, tm = _api(fake, OWNER_A)
    vault.save_refresh_token(OWNER_A, "rt-stale")
    with pytest.raises(NeedsLogin):
        tm.access_token(OWNER_A)


def test_missing_client_secret_is_a_401(fake, monkeypatch):
    monkeypatch.delenv("YOTO_CLIENT_SECRET")
    _api_, tm = _api(fake, OWNER_A)
    with pytest.raises(NeedsLogin, match="access_denied"):
        tm.access_token(OWNER_A)


def test_family_card_falls_back_to_card_endpoint_and_normalizes(fake):
    api, _ = _api(fake, OWNER_B)
    got = api.get_card("LIN01")
    assert got.owned is False
    assert not refs.has_signed_urls(got.card)
    first = got.card["content"]["chapters"][1]["tracks"][0]
    assert first["trackUrl"] == "yoto:#3otzKd_rxPVj4Luwo6w9vNEJkvuP3br5iZxV8TFwRqM"
    assert fake.calls[-2:] == [("GET", "/content/LIN01"), ("GET", "/card/LIN01")]


def test_owned_card_reads_content(fake):
    api, _ = _api(fake, OWNER_A)
    assert api.get_card("LIN01").owned is True


def test_upload_skips_put_when_yoto_has_the_bytes_and_polls_transcode(fake):
    api, _ = _api(fake, OWNER_A)
    fake.pending_polls = 2
    media = api.upload_audio(b"same bytes", "a.mp3")
    assert media.ref.startswith("yoto:#") and media.duration == 3
    assert fake.puts == 1
    again = api.upload_audio(b"same bytes", "a.mp3")
    assert again.ref == media.ref
    assert fake.puts == 1  # uploadUrl was null the second time


def test_foreign_ref_post_is_a_400(fake, hilo):
    api, _ = _api(fake, OWNER_B)
    body = {**hilo, "title": "copy"}
    body.pop("cardId")
    with pytest.raises(YotoError, match="Media file not found"):
        api.post_card(body)


def test_to_ref_leaves_non_yoto_urls():
    assert refs.to_ref("https://example.com/stream.mp3") == "https://example.com/stream.mp3"
    assert refs.to_ref("https://secure-media.yotoplay.com/o~/abc?Expires=1") == "yoto:#abc"
    assert refs.to_ref("yoto:#abc") == "yoto:#abc"


def test_strip_server_fields(hilo):
    out = refs.strip_server_fields(hilo)
    assert not set(refs.SERVER_FIELDS) & set(out)
    assert out["cardId"] == "LIN01"


def test_second_account_is_separate(fake):
    api_a, _ = _api(fake, OWNER_A)
    api_b, _ = _api(fake, OWNER_B)
    assert [c["cardId"] for c in api_a.list_mine()] == ["LIN01"]
    assert api_b.list_mine() == []
    assert [c["cardId"] for c in api_b.list_family()] == ["LIN01"]
