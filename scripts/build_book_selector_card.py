#!/usr/bin/env python3
"""Build a "choose your book" interactive Yoto card from an existing MYO playlist.

Takes a linear multi-book playlist (chapters titled ``Book N ...``), drops its
non-book chapters (e.g. ``intro``), and publishes a NEW interactive card:

    choose-book4 --left--> Book 4 ch1 -> ... -> Book 4 end -> Book 5 ch1 -> ...
         |right
    choose-book5 --left--> Book 5 ch1 -> ...
         |right
        ...
    choose-book8 --right--> choose-book4   (loops)

Finishing a book flows straight into the next book (no prompt); the last book
stops. Prompts are TTS'd locally with ollama, uploaded to Yoto, and the book
audio/icons are reused by reference (``yoto:#...``) — nothing is re-uploaded.

The graph goes through the redesign's ``validate_graph`` / ``serialize_story``
(which refuse dangling gotos, orphans, etc.), then stream URLs are swapped for
Yoto-hosted refs, and the final payload is walked like the device would before
anything is POSTed.

Usage:
    export YOTO_CLIENT_ID=...
    export YOTO_CLIENT_SECRET=...   # only if your app has one
    python scripts/build_book_selector_card.py dK3N1 --dry-run
    python scripts/build_book_selector_card.py dK3N1
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
from dataclasses import dataclass
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import yoto_login  # noqa: E402

from yoto_smart_stream.schemas.story import (  # noqa: E402
    EdgeHandle,
    NodeType,
    OnEnd,
    StoryEdge,
    StoryGraph,
    StoryNode,
    Track,
)
from yoto_smart_stream.stories.keys import build_chapter_keys  # noqa: E402
from yoto_smart_stream.stories.serializer import serialize_story  # noqa: E402

API = "https://api.yotoplay.com"
LOGIN = yoto_login.LOGIN
TOKEN_FILE = yoto_login.TOKEN_FILE
BOOK_RE = re.compile(r"^Book (\d+)\b")
PROMPT_TEXT = "For book {n}, click left dial. For other books, click right dial."
PLACEHOLDER_BASE = "placeholder://unused"


# --------------------------------------------------------------------------- auth


def _token_request(data: dict) -> dict:
    resp = requests.post(
        f"{LOGIN}/oauth/token", data={**data, **yoto_login.client_secret_param()}, timeout=30
    )
    body = resp.json() if resp.content else {}
    if resp.status_code != 200:
        raise RuntimeError(body.get("error") or f"HTTP {resp.status_code}: {resp.text}")
    return body


def get_access_token(client_id: str, token_file: Path = TOKEN_FILE) -> str:
    """Refresh-token grant from the cached token; browser redirect login if missing/expired.

    Yoto rotates refresh tokens, so the new one is always persisted.
    """
    if token_file.exists() and token_file.read_text().strip():
        try:
            tokens = _token_request(
                {
                    "grant_type": "refresh_token",
                    "refresh_token": token_file.read_text().strip(),
                    "client_id": client_id,
                }
            )
            print("✓ Refreshed Yoto access token from cached refresh token")
            if tokens.get("refresh_token"):
                token_file.write_text(tokens["refresh_token"])
                token_file.chmod(0o600)
            return tokens["access_token"]
        except RuntimeError as exc:
            print(f"⚠ Cached refresh token unusable ({exc}); starting browser login")
    return yoto_login.login(client_id, token_file=token_file)["access_token"]


# ------------------------------------------------------------------- source card


@dataclass
class Asset:
    """Playable audio + display already (or newly) hosted by Yoto."""

    title: str
    track_url: str  # yoto:#<sha>
    format: str
    duration: int | None = None
    file_size: int | None = None
    channels: str | None = None
    icon: str | None = None


def fetch_card(token: str, card_id: str) -> dict:
    """Own MYO cards come from /content; family-library cards (403 there) from /card."""
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(f"{API}/content/{card_id}", headers=headers, timeout=30)
    if resp.status_code == 403:
        print(f"Card {card_id} isn't owned by this account; reading it from the family library")
        resp = requests.get(f"{API}/card/{card_id}", headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()["card"]


def yoto_ref(url: str | None) -> str | None:
    """Normalise a media URL to a reusable ``yoto:#<id>`` ref.

    Signed playback/display URLs end in the same id the ``yoto:#`` ref uses, e.g.
    ``https://secure-media.yotoplay.com/<owner>~/<id>?Expires=...`` -> ``yoto:#<id>``.
    """
    if not url or url.startswith("yoto:#"):
        return url
    parsed = urllib.parse.urlparse(url)
    if parsed.hostname not in ("secure-media.yotoplay.com", "card-content.yotoplay.com"):
        raise ValueError(f"Not a Yoto-hosted media URL: {url[:60]}")
    return "yoto:#" + parsed.path.rsplit("/", 1)[-1]


def parse_books(card: dict) -> dict[int, list[Asset]]:
    """Group the card's tracks by book number, preserving order; skip non-book chapters."""
    books: dict[int, list[Asset]] = {}
    skipped: list[str] = []
    for chapter in card["content"]["chapters"]:
        m = BOOK_RE.match(chapter["title"])
        if not m:
            skipped.append(chapter["title"])
            continue
        for t in chapter["tracks"]:
            icon = yoto_ref((t.get("display") or {}).get("icon16x16") or (
                chapter.get("display") or {}
            ).get("icon16x16"))
            books.setdefault(int(m.group(1)), []).append(
                Asset(
                    title=re.sub(r"\.mp3$", "", t["title"]),
                    track_url=yoto_ref(t["trackUrl"]),
                    format=t.get("format", "mp3"),
                    duration=t.get("duration"),
                    file_size=t.get("fileSize"),
                    channels=t.get("channels"),
                    icon=icon,
                )
            )
    print(f"Skipped non-book chapters: {skipped}")
    for n, tracks in books.items():
        print(f"  Book {n}: {len(tracks)} tracks")
    return dict(sorted(books.items()))


# --------------------------------------------------------------- prompt audio


def generate_prompt(text: str, out: Path, model: str, voice: str) -> Path:
    if out.exists() and out.stat().st_size > 0:
        return out
    ollama = subprocess.Popen(
        ["ollama", "run", model, "--voice", voice, text], stdout=subprocess.PIPE
    )
    ffmpeg = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", "-",
         "-codec:a", "libmp3lame", "-qscale:a", "2", str(out)],
        stdin=ollama.stdout,
    )
    assert ollama.stdout is not None
    ollama.stdout.close()
    if ollama.wait() != 0 or ffmpeg.returncode != 0:
        out.unlink(missing_ok=True)
        raise RuntimeError(f"TTS failed for {text!r}")
    print(f"✓ Generated {out.name}")
    return out


def upload_audio(token: str, path: Path) -> dict:
    """Upload to Yoto and wait for transcoding. Returns the ``transcode`` object."""
    headers = {"Authorization": f"Bearer {token}"}
    data = path.read_bytes()
    resp = requests.get(
        f"{API}/media/transcode/audio/uploadUrl",
        headers=headers,
        params={"sha256": hashlib.sha256(data).hexdigest(), "filename": path.name},
        timeout=30,
    )
    resp.raise_for_status()
    upload = resp.json()["upload"]
    if upload.get("uploadUrl"):  # null means Yoto already has these bytes
        requests.put(
            upload["uploadUrl"], data=data, headers={"Content-Type": "audio/mpeg"}, timeout=120
        ).raise_for_status()
    for _ in range(120):
        resp = requests.get(
            f"{API}/media/upload/{upload['uploadId']}/transcoded",
            headers=headers,
            params={"loudnorm": "false"},
            timeout=30,
        )
        if resp.status_code == 200:
            transcode = resp.json().get("transcode", {})
            if transcode.get("transcodedSha256"):
                print(f"✓ Uploaded {path.name} -> {transcode['transcodedSha256'][:12]}…")
                return transcode
        time.sleep(1)
    raise TimeoutError(f"Transcoding timed out for {path.name}")


def prompt_asset(transcode: dict, title: str, icon: str | None) -> Asset:
    info = transcode.get("transcodedInfo") or {}
    return Asset(
        title=title,
        track_url=f"yoto:#{transcode['transcodedSha256']}",
        format=info.get("format", "mp3"),
        duration=info.get("duration"),
        file_size=info.get("fileSize"),
        channels=info.get("channels"),
        icon=icon,
    )


# ------------------------------------------------------------------ graph/card


def choice_id(book: int) -> str:
    return f"choose-book{book}"


def segment_id(book: int, i: int) -> str:
    return f"book{book}-{i:02d}"


def build_graph(books: dict[int, list[Asset]]) -> StoryGraph:
    order = list(books)
    nodes: list[StoryNode] = []
    edges: list[StoryEdge] = []

    def edge(src: str, dst: str, handle: EdgeHandle) -> None:
        edges.append(StoryEdge(id=f"{src}->{dst}:{handle.value}", source=src, target=dst, handle=handle))

    for idx, book in enumerate(order):
        cid = choice_id(book)
        nodes.append(
            StoryNode(id=cid, type=NodeType.choice, title=f"Book {book}?",
                      tracks=[Track(key=cid, title=f"Book {book}?")])
        )
        edge(cid, segment_id(book, 1), EdgeHandle.left)
        edge(cid, choice_id(order[(idx + 1) % len(order)]), EdgeHandle.right)

    for idx, book in enumerate(order):
        tracks = books[book]
        for i, asset in enumerate(tracks, start=1):
            sid = segment_id(book, i)
            last_of_book = i == len(tracks)
            last_book = idx == len(order) - 1
            nodes.append(
                StoryNode(
                    id=sid,
                    type=NodeType.segment,
                    title=asset.title,
                    tracks=[Track(key=sid, title=asset.title)],
                    on_end=OnEnd.stop if (last_of_book and last_book) else OnEnd.next,
                )
            )
            if not last_of_book:
                edge(sid, segment_id(book, i + 1), EdgeHandle.next)
            elif not last_book:
                edge(sid, segment_id(order[idx + 1], 1), EdgeHandle.next)

    return StoryGraph(start_node_id=choice_id(order[0]), nodes=nodes, edges=edges)


def build_payload(
    graph: StoryGraph, assets: dict[str, Asset], source: dict, title: str
) -> dict:
    card = serialize_story(
        graph,
        story_id=0,
        base_url=PLACEHOLDER_BASE,
        title=title,
        description=f"Interactive book chooser built from card {source.get('cardId')}.",
        author=source.get("metadata", {}).get("author"),
    )
    payload = card.model_dump(exclude_none=True)

    # Serializer emits stream URLs (Plan 4 will add Yoto-hosted audio); swap in
    # the Yoto-hosted refs + display/duration metadata the schema doesn't model.
    by_chapter_key = {build_chapter_keys(graph.nodes)[n.id]: n.id for n in graph.nodes}
    for chapter in payload["content"]["chapters"]:
        asset = assets[by_chapter_key[chapter["key"]]]
        for track in chapter["tracks"]:
            track.update(type="audio", trackUrl=asset.track_url, format=asset.format)
            for k, v in (("duration", asset.duration), ("fileSize", asset.file_size),
                         ("channels", asset.channels)):
                if v is not None:
                    track[k] = v
            if asset.icon:
                track["display"] = {"icon16x16": asset.icon}
        if asset.icon:
            chapter["display"] = {"icon16x16": asset.icon}
        if asset.duration is not None:
            chapter["duration"] = asset.duration

    # All audio is Yoto-hosted, so the card can play offline.
    payload["content"]["config"]["onlineOnly"] = False
    cover = source.get("metadata", {}).get("cover") or source.get("content", {}).get("cover")
    if cover:
        payload["metadata"]["cover"] = cover
    return payload


def check_payload(payload: dict, books: dict[int, list[Asset]]) -> None:
    """Walk the final payload like the device would; raise on any surprise."""
    chapters = {c["key"]: c for c in payload["content"]["chapters"]}

    def resolve(cmd: dict) -> str:
        p = cmd["params"]
        ch = chapters.get(p["chapterKey"])
        assert ch is not None, f"goto to missing chapter {p}"
        assert ch["tracks"][0]["key"] == p["trackKey"], f"goto to wrong track {p}"
        return p["chapterKey"]

    for c in chapters.values():
        for t in c["tracks"]:
            assert t["trackUrl"].startswith("yoto:#"), f"{c['key']} has non-Yoto URL"
            for cmd in (t.get("events") or {}).values():
                if cmd["cmd"] == "goto":
                    resolve(cmd)

    order = list(books)
    first = payload["content"]["chapters"][0]["key"]
    assert first == choice_id(order[0]), f"card starts at {first}"

    # Right button cycles through every prompt and back to the start.
    key, seen = first, []
    for _ in order:
        ev = chapters[key]["tracks"][-1]["events"]
        assert ev["onEnd"]["cmd"] == "stop", f"{key} doesn't wait for a choice"
        seen.append(key)
        key = resolve(ev["onRhb"])
    assert key == first and seen == [choice_id(b) for b in order], seen

    # Left on each prompt starts that book; onEnd then plays straight through to the end.
    for b in order:
        key = resolve(chapters[choice_id(b)]["tracks"][-1]["events"]["onLhb"])
        assert key == segment_id(b, 1), key
        played = [key]
        while (ev := chapters[key]["tracks"][-1].get("events", {}).get("onEnd"))["cmd"] == "goto":
            key = resolve(ev)
            played.append(key)
        assert ev["cmd"] == "stop"
        expected = [segment_id(bb, i) for bb in order[order.index(b):]
                    for i in range(1, len(books[bb]) + 1)]
        assert played == expected, f"Book {b} play-through mismatch"
    print(f"✓ Device walk OK: {len(chapters)} chapters, every goto resolves, "
          f"prompts cycle {' -> '.join(map(str, order))} -> {order[0]}, books play through")


# ------------------------------------------------------------------------ main


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("card_id", help="Source MYO card id, e.g. dK3N1")
    ap.add_argument("--voice", default="Harper", help="ollama speech voice (default: Harper)")
    ap.add_argument("--model", default="phonon", help="ollama speech model (default: phonon)")
    ap.add_argument("--title", help="New card title (default: '<source title> (Choose a Book)')")
    ap.add_argument("--audio-dir", type=Path, default=Path("book_selector_audio"))
    ap.add_argument("--dry-run", action="store_true", help="Build + check, write payload JSON, don't upload/POST")
    args = ap.parse_args()

    client_id = os.environ.get("YOTO_CLIENT_ID")
    if not client_id:
        sys.exit("YOTO_CLIENT_ID is not set")

    token = get_access_token(client_id)
    source = fetch_card(token, args.card_id)
    print(f"Source card: {source['title']!r} ({args.card_id})")
    books = parse_books(source)
    graph = build_graph(books)

    assets: dict[str, Asset] = {}
    for b, tracks in books.items():
        for i, asset in enumerate(tracks, start=1):
            assets[segment_id(b, i)] = asset

    args.audio_dir.mkdir(exist_ok=True)
    for b, tracks in books.items():
        mp3 = generate_prompt(PROMPT_TEXT.format(n=b), args.audio_dir / f"choose-book{b}.mp3",
                              args.model, args.voice)
        title = f"Book {b}?"
        if args.dry_run:
            fake = hashlib.sha256(mp3.read_bytes()).hexdigest()
            assets[choice_id(b)] = Asset(title=title, track_url=f"yoto:#{fake}", format="mp3",
                                         icon=tracks[0].icon)
        else:
            assets[choice_id(b)] = prompt_asset(upload_audio(token, mp3), title, tracks[0].icon)

    title = args.title or f"{source['title']} (Choose a Book)"
    payload = build_payload(graph, assets, source, title)
    check_payload(payload, books)

    out = args.audio_dir / "payload.json"
    out.write_text(json.dumps(payload, indent=2))
    print(f"Payload written to {out}")
    if args.dry_run:
        print("Dry run: nothing uploaded or created.")
        return

    resp = requests.post(f"{API}/content", headers={"Authorization": f"Bearer {token}"},
                         json=payload, timeout=60)
    if resp.status_code >= 400:
        sys.exit(f"Create failed: HTTP {resp.status_code}: {resp.text}")
    created = resp.json().get("card", resp.json())
    print(f"✓ Created interactive card {created.get('cardId')!r}: {created.get('title')!r}")


if __name__ == "__main__":
    main()
