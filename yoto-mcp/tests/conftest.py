from __future__ import annotations

import copy
import json
from pathlib import Path

import httpx
import keyring
import pytest
from keyring.backend import KeyringBackend

from yoto_mcp import vault
from yoto_mcp.session import Session

from .fake_yoto import FakeYoto

FIXTURES = Path(__file__).parent / "fixtures"
OWNER_A = "auth0|owner-a"  # made the Hilo playlist
OWNER_B = "auth0|owner-b"


class MemoryKeyring(KeyringBackend):
    priority = 1  # type: ignore[assignment]

    def __init__(self):
        super().__init__()
        self.items: dict[tuple[str, str], str] = {}

    def get_password(self, service, username):
        return self.items.get((service, username))

    def set_password(self, service, username, password):
        self.items[(service, username)] = password

    def delete_password(self, service, username):
        self.items.pop((service, username), None)


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("YOTO_HOME", str(tmp_path / "yoto-home"))
    monkeypatch.setenv("YOTO_CLIENT_ID", "client-123")
    monkeypatch.setenv("YOTO_CLIENT_SECRET", "secret-xyz")
    ring = MemoryKeyring()
    keyring.set_keyring(ring)
    return ring


@pytest.fixture
def hilo() -> dict:
    return json.loads((FIXTURES / "hilo_linear.json").read_text())


@pytest.fixture
def fake(hilo) -> FakeYoto:
    f = FakeYoto()
    f.add_card(hilo, OWNER_A, family=True)
    return f


def link(fake: FakeYoto, sub: str, name: str) -> None:
    vault.save_refresh_token(sub, fake.add_account(sub))
    vault.add_account(sub, name)


@pytest.fixture
def session(fake) -> Session:
    link(fake, OWNER_A, "Eugene")
    link(fake, OWNER_B, "Family")
    return Session(
        http=httpx.Client(transport=fake.transport()), clock=lambda: fake.now, sleep=lambda _s: None
    )


def interactive_card(hilo: dict) -> dict:
    """A small selector card owned by B, reusing A's refs (what the family library shows)."""
    card = copy.deepcopy(hilo)
    card["cardId"] = "SEL01"
    card["title"] = "Hilo Books 4-8 (Choose a Book)"
    return card
