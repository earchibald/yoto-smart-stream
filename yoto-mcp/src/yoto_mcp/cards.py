"""Card views (summary, outline) and title resolution.

The user never sees a card's id in the Yoto app, so every tool names a card by its title.
"""

from __future__ import annotations

from dataclasses import dataclass


def title_of(card: dict) -> str:
    return card.get("title") or (card.get("metadata") or {}).get("title") or ""


@dataclass
class Entry:
    """One card as listed: enough to resolve a title and show a library row."""

    card_id: str
    title: str
    account: str  # the linked account's short name that listed it
    owned: bool
    updated_at: str | None = None
    chapters: int | None = None

    def row(self) -> dict:
        row = {"title": self.title, "account": self.account, "owned": self.owned}
        if self.chapters is not None:
            row["chapters"] = self.chapters
        if self.updated_at:
            row["last_changed"] = self.updated_at
        return row


class Ambiguous(LookupError):
    def __init__(self, name: str, matches: list[Entry]):
        titles = "; ".join(f"{m.title!r} ({m.account})" for m in matches[:10])
        super().__init__(f"{name!r} matches more than one card: {titles}. Use the full title.")
        self.matches = matches


class NotFound(LookupError):
    def __init__(self, name: str, suggestions: list[str]):
        hint = f" Closest titles: {', '.join(repr(s) for s in suggestions)}." if suggestions else ""
        super().__init__(f"No card titled {name!r}.{hint}")
        self.suggestions = suggestions


def _norm(s: str) -> str:
    return " ".join(s.casefold().split())


def resolve(name: str, entries: list[Entry], prefer_owned: bool = False) -> Entry:
    """Exact title (ignoring case and spacing), then a unique partial match, then an id.

    When the same title appears more than once (owned and family copies), ``prefer_owned``
    picks the owned one if that makes it unique.
    """
    want = _norm(name)
    for match in (
        [e for e in entries if _norm(e.title) == want],
        [e for e in entries if want and want in _norm(e.title)],
        [e for e in entries if e.card_id == name.strip()],
    ):
        match = _dedupe(match)
        if len(match) == 1:
            return match[0]
        if len(match) > 1:
            owned = [e for e in match if e.owned]
            if prefer_owned and len(owned) == 1:
                return owned[0]
            raise Ambiguous(name, match)
    raise NotFound(name, _closest(want, entries))


def _dedupe(entries: list[Entry]) -> list[Entry]:
    """The same card listed by two endpoints (mine + family) counts once, owned wins."""
    by_id: dict[tuple[str, str], Entry] = {}
    for e in entries:
        key = (e.card_id, e.account)
        if key not in by_id or (e.owned and not by_id[key].owned):
            by_id[key] = e
    return list(by_id.values())


def _closest(want: str, entries: list[Entry], n: int = 5) -> list[str]:
    import difflib

    titles = sorted({e.title for e in entries})
    close = difflib.get_close_matches(want, [_norm(t) for t in titles], n=n, cutoff=0.4)
    by_norm = {_norm(t): t for t in titles}
    return [by_norm[c] for c in close]


# ------------------------------------------------------------------ views


def chapters(card: dict) -> list[dict]:
    return (card.get("content") or {}).get("chapters") or []


def summary(card: dict, owned: bool, account: str) -> dict:
    chs = chapters(card)
    content = card.get("content") or {}
    duration = sum(c.get("duration") or 0 for c in chs) or (card.get("metadata") or {}).get("media", {}).get(
        "duration"
    )
    return {
        "title": title_of(card),
        "account": account,
        "owned": owned,
        "chapters": len(chs),
        "tracks": sum(len(c.get("tracks") or []) for c in chs),
        "duration_seconds": duration,
        "interactive": content.get("playbackType") == "interactive",
        "last_changed": card.get("updatedAt"),
        "config": content.get("config") or {},
    }


def _events(track: dict) -> dict:
    out = {}
    for name, cmd in (track.get("events") or {}).items():
        if cmd.get("cmd") == "goto":
            out[name] = f"goto {cmd.get('params', {}).get('chapterKey')}"
        else:
            out[name] = cmd.get("cmd")
    return out


def outline(card: dict) -> list[dict]:
    rows = []
    for c in chapters(card):
        tracks = c.get("tracks") or []
        row = {
            "label": c.get("overlayLabel"),
            "key": c.get("key"),
            "title": c.get("title"),
            "duration": c.get("duration"),
            "icon": (c.get("display") or {}).get("icon16x16"),
            "tracks": len(tracks),
        }
        if len(tracks) > 1:
            row["track_titles"] = [t.get("title") for t in tracks]
        if tracks and (ev := _events(tracks[-1])):
            row["events"] = ev
        rows.append(row)
    return rows


def outline_markdown(card: dict) -> str:
    lines = [
        f"# {title_of(card)}",
        "",
        "| # | Key | Title | Duration | Icon | Events |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for r in outline(card):
        ev = ", ".join(f"{k}: {v}" for k, v in (r.get("events") or {}).items())
        dur = f"{r['duration'] // 60}:{r['duration'] % 60:02d}" if r.get("duration") else ""
        lines.append(f"| {r['label'] or ''} | {r['key']} | {r['title']} | {dur} | {r['icon'] or ''} | {ev} |")
    return "\n".join(lines)
