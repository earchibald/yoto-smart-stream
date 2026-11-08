"""The yoto-mcp stdio server: card, media and icon tools over a local ``Session``."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP, Image
from mcp.types import ToolAnnotations

from . import cards, icons, vault
from .session import Session

INSTRUCTIONS = """\
Tools for the user's Yoto MYO playlists and interactive cards.

- Name cards by their title, the way the user sees them in the Yoto app. Never show card ids
  to the user; they can't see them anywhere.
- Every change is plan-then-apply: call yoto_card_plan, show the user the diff and warnings,
  and only call yoto_card_apply after they agree. Apply takes a backup and verifies the write.
- Cards owned by another family account are read-only from this account. Copy their media with
  yoto_media_import before reusing it on this account's cards.
- To draw an icon, write a 16×16 character grid with a palette (yoto_icon_render) or start from
  yoto_icon_glyph; look at the preview it returns before offering the icon.
"""

mcp = FastMCP("yoto", instructions=INSTRUCTIONS)
_session: Session | None = None

READ = ToolAnnotations(readOnlyHint=True, openWorldHint=True)
WRITE = ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=True, openWorldHint=True)
UPLOAD = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=True)
LOCAL = ToolAnnotations(readOnlyHint=True, openWorldHint=False)


def session() -> Session:
    global _session
    if _session is None:
        _session = Session()
    return _session


# ------------------------------------------------------------------ accounts


@mcp.tool(annotations=READ)
def yoto_whoami() -> dict[str, Any]:
    """List the linked Yoto accounts (by the short names the user gave them) and the default one."""
    s = session()
    messages = s.finish_logins()
    accts = vault.accounts()
    return {
        "accounts": [{"name": a.name, "default": a.default} for a in accts],
        "pending_logins": list(s.pending_logins),
        "messages": messages,
        "client_configured": bool(vault.client_id()),
        "scopes": "user:content:manage offline_access",
    }


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=True))
def yoto_account_link(name: str, open_browser: bool = True) -> dict[str, Any]:
    """Start a browser login that links a Yoto account under a short name such as "Family".

    Returns the login URL (opened in the browser by default). Call yoto_whoami after the user
    finishes logging in to confirm the account is linked.
    """
    url = session().start_login(name, open_browser=open_browser)
    return {
        "login_url": url,
        "name": name,
        "next": "Ask the user to finish logging in in the browser, then call yoto_whoami.",
    }


# ------------------------------------------------------------------ reading cards


@mcp.tool(annotations=READ)
def yoto_cards_list(
    account: str | None = None, search: str | None = None, fresh: bool = False
) -> dict[str, Any]:
    """List cards in My Playlists and the family library, by title.

    `owned: false` cards belong to another family account and are read-only from this one.
    """
    acct = vault.find_account(account)
    entries = session().index(account, fresh=fresh)
    if search:
        want = search.casefold()
        entries = [e for e in entries if want in e.title.casefold()]
    rows = sorted((e.row() for e in entries), key=lambda r: (not r["owned"], r["title"].casefold()))
    return {"account": acct.name, "count": len(rows), "cards": rows}


@mcp.tool(annotations=READ)
def yoto_card_get(card: str, view: str = "outline", account: str | None = None) -> dict[str, Any]:
    """Fetch one card by title. `view` is `summary`, `outline` (chapter list) or `full` (whole document).

    Media in every view is given as yoto:# refs, which are safe to reuse in plans on the same account.
    """
    acct, _api, _entry, doc, owned = session().read(card, account)
    out: dict[str, Any] = {"summary": cards.summary(doc, owned, acct.name)}
    if view in ("outline", "full"):
        out["outline"] = cards.outline(doc)
    if view == "full":
        out["document"] = {k: v for k, v in doc.items() if k not in ("userId",)}
    return out


@mcp.tool(annotations=READ)
def yoto_card_playable(
    card: str, chapters: list[str] | None = None, account: str | None = None
) -> dict[str, Any]:
    """Short-lived signed URLs for listening to or spot-checking a card's tracks. Don't store them."""
    s = session()
    acct, api = s.account(account)
    entry = s.find(card, account)
    doc = api.get_playable(entry.card_id)
    rows = []
    for c in cards.chapters(doc):
        if chapters and c.get("key") not in chapters and c.get("title") not in chapters:
            continue
        for t in c.get("tracks") or []:
            rows.append(
                {
                    "chapter": c.get("title"),
                    "key": c.get("key"),
                    "track": t.get("title"),
                    "duration": t.get("duration"),
                    "url": t.get("trackUrl"),
                }
            )
    return {"card": entry.title, "account": acct.name, "tracks": rows}


# ------------------------------------------------------------------ plan and apply

OPS_HELP = """\
Ops (address chapters by key, or by exact chapter title):
- insert_chapter {key, title, audio: <media from yoto_media_upload_wait>, icon?, before|after: chapter, or position: start|end|N}
  or {key, title, tracks: [{key?, title, audio, icon?}], ...}
- remove_chapter {chapter}
- move_chapter {chapter, before|after|position}
- retitle {title} (the card) or {chapter, track?, title}
- set_track_audio {chapter, track?, audio}
- set_icon {chapter, track?, icon: "yoto:#…"} (no track: the chapter and all its tracks)
- set_events {chapter, track?, events: {onEnd|onLhb|onRhb: {cmd: goto|stop, params?} | null}}
- set_config {config: {resumeTimeout, autoadvance, disableTrackNav, …: value | null}, playbackType?}
- set_cover {url}
- set_metadata {metadata: {description, author, …}}
- replace_refs {map: {"yoto:#old": "yoto:#new" | media}} (after yoto_media_import)
- renumber_labels {} (runs automatically after structural ops)
"""


PLAN_DOC = (
    """Plan an edit to a card without writing anything. Returns a plan_id, a readable diff and warnings.

`card` is the card's title, or "new" (with `title`) to plan a new card. Show the user the diff
before applying. Plans expire after 30 minutes.

"""
    + OPS_HELP
)


@mcp.tool(annotations=READ, description=PLAN_DOC)
def yoto_card_plan(
    card: str, ops: list[dict], account: str | None = None, title: str | None = None, renumber: bool = True
) -> dict[str, Any]:
    return session().make_plan(card, ops, account, title=title, renumber=renumber).public()


@mcp.tool(annotations=WRITE)
def yoto_card_apply(plan_id: str, verify_playback: bool = True) -> dict[str, Any]:
    """Apply a plan the user has seen: checks the card hasn't changed, backs it up, writes, re-reads, verifies.

    Applying the same plan twice does nothing the second time.
    """
    return session().apply(plan_id, verify_playback=verify_playback)


@mcp.tool(annotations=READ)
def yoto_card_backups(card: str, account: str | None = None) -> dict[str, Any]:
    """List the local backups of a card, newest first (taken before every apply; the last 20 are kept)."""
    return {"card": card, "backups": session().backups(card, account)}


@mcp.tool(annotations=READ)
def yoto_card_restore(card: str, backup: str | None = None, account: str | None = None) -> dict[str, Any]:
    """Plan restoring a card from a backup (the newest by default). Apply the returned plan to restore."""
    return session().restore_plan(card, backup, account).public()


# ------------------------------------------------------------------ media


@mcp.tool(annotations=UPLOAD)
def yoto_media_upload_begin(sha256: str, filename: str, account: str | None = None) -> dict[str, Any]:
    """Start an audio upload. `exists: true` means Yoto already has these bytes (no PUT needed).

    Otherwise PUT the file to upload_url (bin/yoto-upload does this), then call yoto_media_upload_wait.
    """
    _acct, api = session().account(account)
    ticket = api.audio_upload_begin(sha256, filename)
    return {"exists": ticket.exists, "upload_id": ticket.upload_id, "upload_url": ticket.upload_url}


@mcp.tool(annotations=UPLOAD)
def yoto_media_upload_wait(
    upload_id: str, account: str | None = None, timeout: float = 180
) -> dict[str, Any]:
    """Wait for Yoto to transcode an upload. Returns the yoto:# ref plus duration, fileSize, channels, format."""
    s = session()
    acct, api = s.account(account)
    media = api.audio_upload_wait(upload_id, timeout=timeout)
    s.note_owned(acct.sub, media.ref)
    return {**media.as_dict(), "account": acct.name}


@mcp.tool(annotations=UPLOAD)
def yoto_media_upload_file(path: str, account: str | None = None) -> dict[str, Any]:
    """Upload a local audio file in one step and wait for transcoding. The bytes never pass through Claude."""
    return session().upload_file(path, account)


@mcp.tool(annotations=UPLOAD)
def yoto_media_import(
    card: str, from_account: str, to_account: str | None = None, chapters: list[str] | None = None
) -> dict[str, Any]:
    """Copy a card's audio and icons from one linked account into another (media refs are per account).

    Returns a map from old refs to new media; use it in a `replace_refs` op on the destination's copy.
    """
    return session().media_import(card, from_account, to_account, chapters)


# ------------------------------------------------------------------ icons


def _render_result(rendered: list[icons.Rendered]) -> list:
    sheet = icons.contact_sheet([(r.name, r.png) for r in rendered])
    info = {
        "icons": [r.info() for r in rendered],
        "preview": "Each icon at 8×: on black (as the player shows it), then on a checkerboard.",
    }
    return [json.dumps(info, indent=1), Image(data=sheet, format="png")]


@mcp.tool(annotations=LOCAL, structured_output=False)
def yoto_icon_render(specs: list[dict]) -> list:
    """Render 16×16 icons from character grids and return a preview sheet to look at.

    Each spec: {"name": str, "rows": [16 strings of 16 chars], "palette": {char: "#RRGGBB" | "#RRGGBBAA" | "transparent"}}.
    "." and " " are transparent unless the palette says otherwise. Style: strokes at least 2 px, 4 colours
    or fewer, a 1 px margin, bright colours that read on black, one idea per icon. Fix lint warnings and
    re-render (at most three rounds) before offering an icon.
    """
    return _render_result([icons.render(spec) for spec in specs])


@mcp.tool(annotations=LOCAL, structured_output=False)
def yoto_icon_glyph(
    text: str, colour: str = "#ffffff", outline: str | None = None, name: str | None = None
) -> list:
    """A centred icon of 1–2 characters (digits, A–Z, ? ! + -) or one symbol (★ ♥ ♪ ☾ ☀).

    Returns the spec (editable, for yoto_icon_render) and its preview.
    """
    spec = icons.glyph(text, colour, outline, name)
    rendered = icons.render(spec)
    out = _render_result([rendered])
    data = json.loads(out[0])
    data["spec"] = spec
    return [json.dumps(data, indent=1), out[1]]


@mcp.tool(annotations=LOCAL, structured_output=False)
def yoto_icon_from_image(
    path: str, max_colours: int = 6, alpha_threshold: int = 128, name: str | None = None
) -> list:
    """Downscale and quantize a local image into a 16×16 spec, as a starting point to clean up."""
    spec = icons.from_image(str(Path(path).expanduser()), max_colours, alpha_threshold, name)
    rendered = icons.render(spec)
    out = _render_result([rendered])
    data = json.loads(out[0])
    data["spec"] = spec
    return [json.dumps(data, indent=1), out[1]]


@mcp.tool(annotations=UPLOAD)
def yoto_icon_upload(icon: str, account: str | None = None, auto_convert: bool = False) -> dict[str, Any]:
    """Upload an icon: the sha256 of a rendered icon, or a local PNG/GIF path. Returns its yoto:# ref.

    Without auto_convert the file must be exactly 16×16 RGBA PNG, so Yoto stores the pixels as drawn.
    Use the ref in a set_icon op.
    """
    s = session()
    acct, api = s.account(account)
    hit = icons.cached(icon) if len(icon) == 64 and all(c in "0123456789abcdef" for c in icon) else None
    if hit:
        png, meta = hit
        filename = f"{(meta.get('name') or icon[:8]).replace(' ', '-')}.png"
    else:
        f = Path(icon).expanduser()
        if not f.is_file():
            raise FileNotFoundError(f"{icon!r} is neither a rendered icon's sha256 nor a file.")
        png, filename = f.read_bytes(), f.name
    if not auto_convert and filename.lower().endswith(".png") and (problems := icons.check_png(png)):
        raise ValueError(
            "Not a 16×16 RGBA PNG (" + "; ".join(problems) + "). Re-render it, or pass "
            "auto_convert=true to let Yoto resize it."
        )
    up = api.upload_icon(png, filename, auto_convert=auto_convert)
    s.note_owned(acct.sub, up["ref"])
    return {"ref": up["ref"], "new": up["new"], "account": acct.name}


@mcp.tool(annotations=READ)
def yoto_icons_search(query: str, account: str | None = None, limit: int = 24) -> dict[str, Any]:
    """Search this account's uploaded icons and Yoto's public icons by title and tags."""
    return {"query": query, "icons": session().search_icons(query, account, limit)}


@mcp.tool(annotations=UPLOAD)
def yoto_cover_upload(path: str, account: str | None = None) -> dict[str, Any]:
    """Upload cover art from a local image (Yoto resizes it). Use the url in a set_cover op."""
    _acct, api = session().account(account)
    f = Path(path).expanduser()
    ext = f.suffix.lower().lstrip(".")
    ctype = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "gif": "image/gif",
        "webp": "image/webp",
    }.get(ext)
    if not ctype:
        raise ValueError("Cover art must be a JPEG, PNG, GIF or WebP file.")
    return api.upload_cover(f.read_bytes(), ctype)


def run() -> None:
    mcp.run()
