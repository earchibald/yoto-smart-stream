"""Secrets in the OS keychain; the (non-secret) account list in ``~/.yoto/accounts.json``.

Keychain service ``yoto-mcp`` holds:

* ``client_id`` and ``client_secret`` (``YOTO_CLIENT_ID`` / ``YOTO_CLIENT_SECRET`` override them)
* ``refresh:<sub>``, one rotating refresh token per Yoto account

Nothing here is ever returned by a tool.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass

import keyring

from . import paths

SERVICE = "yoto-mcp"
DEFAULT_REDIRECT_URI = "http://localhost/oauth/callback"


@dataclass
class Account:
    sub: str  # auth0|… from the access token; never shown to the user
    name: str  # what the user calls this account, e.g. "Family"
    default: bool = False


def _get(key: str) -> str | None:
    return keyring.get_password(SERVICE, key)


def _set(key: str, value: str) -> None:
    keyring.set_password(SERVICE, key, value)


def client_id() -> str | None:
    return os.environ.get("YOTO_CLIENT_ID") or _get("client_id")


def client_secret() -> str | None:
    return os.environ.get("YOTO_CLIENT_SECRET") or _get("client_secret")


def save_client(client_id_: str, client_secret_: str | None) -> None:
    _set("client_id", client_id_)
    if client_secret_:
        _set("client_secret", client_secret_)


def redirect_uri() -> str:
    return os.environ.get("YOTO_REDIRECT_URI") or _settings().get("redirect_uri") or DEFAULT_REDIRECT_URI


def refresh_token(sub: str) -> str | None:
    return _get(f"refresh:{sub}")


def save_refresh_token(sub: str, token: str) -> None:
    _set(f"refresh:{sub}", token)


# ------------------------------------------------------------------ accounts


def _accounts_file():
    return paths.home() / "accounts.json"


def _settings() -> dict:
    f = paths.home() / "settings.json"
    return json.loads(f.read_text()) if f.exists() else {}


def accounts() -> list[Account]:
    f = _accounts_file()
    if not f.exists():
        return []
    return [Account(**a) for a in json.loads(f.read_text())]


def _save_accounts(items: list[Account]) -> None:
    f = _accounts_file()
    f.write_text(json.dumps([asdict(a) for a in items], indent=1))
    f.chmod(0o600)


def add_account(sub: str, name: str) -> Account:
    """Add or rename an account. The first account becomes the default."""
    items = [a for a in accounts() if a.sub != sub]
    if any(a.name.casefold() == name.casefold() for a in items):
        raise ValueError(f"Another account is already called {name!r}; pick a different name.")
    acct = Account(sub=sub, name=name, default=not any(a.default for a in items))
    items.append(acct)
    _save_accounts(items)
    return acct


def set_default(name: str) -> Account:
    items = accounts()
    target = find_account(name)
    for a in items:
        a.default = a.sub == target.sub
    _save_accounts(items)
    return target


def find_account(name: str | None) -> Account:
    """The named account (case-insensitive), or the default one when ``name`` is empty."""
    items = accounts()
    if not items:
        raise LookupError("No Yoto account is linked yet. Run `yoto-mcp login` or call yoto_account_link.")
    if not name:
        return next((a for a in items if a.default), items[0])
    for a in items:
        if a.name.casefold() == name.casefold():
            return a
    names = ", ".join(repr(a.name) for a in items)
    raise LookupError(f"No linked account called {name!r}. Linked accounts: {names}.")


def account_by_sub(sub: str) -> Account | None:
    return next((a for a in accounts() if a.sub == sub), None)
