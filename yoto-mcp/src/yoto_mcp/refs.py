"""Media refs and card documents in the form that is always safe to write back.

* Reads from ``/card`` and playable reads return signed URLs. Their last path segment is
  the same id the ``yoto:#`` ref uses, so every read rewrites them to ``yoto:#<id>``.
* ``POST /content`` replaces the whole card, and server-owned fields must not be sent.
"""

from __future__ import annotations

import copy
import urllib.parse
from collections.abc import Iterator

SERVER_FIELDS = ("createdAt", "updatedAt", "userId", "slug", "sortkey", "deleted")
MEDIA_HOSTS = ("secure-media.yotoplay.com", "card-content.yotoplay.com", "media-secure-v2.yotoplay.com")
REF_PREFIX = "yoto:#"


def is_ref(value: object) -> bool:
    return isinstance(value, str) and value.startswith(REF_PREFIX)


def to_ref(url: str | None) -> str | None:
    """``https://secure-media.yotoplay.com/<owner>~/<id>?Expires=…`` → ``yoto:#<id>``.

    Anything that isn't Yoto-hosted (a stream URL, a public icon URL) is left alone.
    """
    if not url or not isinstance(url, str) or is_ref(url):
        return url
    parsed = urllib.parse.urlparse(url)
    if parsed.hostname in MEDIA_HOSTS and parsed.path.strip("/"):
        return REF_PREFIX + parsed.path.rsplit("/", 1)[-1]
    return url


def ref_id(ref: str) -> str:
    return ref[len(REF_PREFIX) :] if is_ref(ref) else ref


def iter_media(card: dict) -> Iterator[tuple[str, dict, str]]:
    """Yield ``(kind, holder, field)`` for every media slot in a card: audio and icons."""
    for chapter in (card.get("content") or {}).get("chapters") or []:
        display = chapter.get("display") or {}
        if "icon16x16" in display:
            yield "icon", display, "icon16x16"
        for track in chapter.get("tracks") or []:
            if "trackUrl" in track:
                yield "audio", track, "trackUrl"
            tdisplay = track.get("display") or {}
            if "icon16x16" in tdisplay:
                yield "icon", tdisplay, "icon16x16"


def normalize(card: dict) -> dict:
    """A deep copy with signed media URLs turned into ``yoto:#`` refs."""
    out = copy.deepcopy(card)
    for _kind, holder, field in iter_media(out):
        holder[field] = to_ref(holder[field])
    return out


def strip_server_fields(card: dict) -> dict:
    out = copy.deepcopy(card)
    for field in SERVER_FIELDS:
        out.pop(field, None)
    return out


def media_refs(card: dict) -> dict[str, set[str]]:
    """``{"audio": {...}, "icon": {...}}`` of the ``yoto:#`` refs a card uses."""
    found: dict[str, set[str]] = {"audio": set(), "icon": set()}
    for kind, holder, field in iter_media(card):
        if is_ref(holder[field]):
            found[kind].add(holder[field])
    return found


def has_signed_urls(card: dict) -> bool:
    for _kind, holder, field in iter_media(card):
        value = holder[field]
        if isinstance(value, str) and urllib.parse.urlparse(value).hostname in MEDIA_HOSTS:
            return True
    return False
