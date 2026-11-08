"""Where yoto-mcp keeps state on disk (``~/.yoto`` unless ``YOTO_HOME`` is set)."""

from __future__ import annotations

import os
from pathlib import Path


def home() -> Path:
    root = Path(os.environ.get("YOTO_HOME") or Path.home() / ".yoto")
    root.mkdir(parents=True, exist_ok=True)
    return root


def sub(name: str) -> Path:
    path = home() / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def backups() -> Path:
    return sub("backups")


def icons() -> Path:
    return sub("icons")


def plans() -> Path:
    return sub("plans")


def locks() -> Path:
    return sub("locks")


def cache() -> Path:
    return sub("cache")


def change_log() -> Path:
    return home() / "changes.log"
