#!/usr/bin/env python3
"""Insert a "Hilo Book N: Subtitle" title track before each book of a linear MYO card.

Edits the card in place (it must be owned by the logged-in account), keeping
every existing chapter in its order and renumbering the overlay labels. Reuses
the announcement audio from build_book_selector_card.py (generating it if
missing). Idempotent: books that already have a title track are left alone.
Also regenerates the card's spoken intro track ("Hilo books 4 through 8. Book 4,
track 2. ...") with the track numbers recalculated for the new layout.
A JSON backup of the card is written before updating.

Usage:
    export YOTO_CLIENT_ID=... YOTO_CLIENT_SECRET=...
    python scripts/add_title_tracks.py dK3N1 [--dry-run]
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_book_selector_card as bsc  # noqa: E402

SERVER_FIELDS = ("createdAt", "updatedAt", "userId", "slug", "sortkey")
INTRO_TITLE = "intro"


def book_start_tracks(card: dict, books: list[int]) -> dict[int, int]:
    """1-based track number where each book starts (its title track)."""
    keys = [c["key"] for c in card["content"]["chapters"]]
    return {b: keys.index(bsc.announce_id(b)) + 1 for b in books}


def intro_text(starts: dict[int, int]) -> str:
    books = list(starts)
    lines = [f"High-low books {books[0]} through {books[-1]}."]
    lines += [f"Book {b}, track {n}." for b, n in starts.items()]
    return " ".join(lines)


def replace_intro_audio(card: dict, asset: bsc.Asset) -> None:
    intros = [c for c in card["content"]["chapters"] if c["title"] == INTRO_TITLE]
    assert len(intros) == 1, f"expected one {INTRO_TITLE!r} chapter, found {len(intros)}"
    chapter = intros[0]
    track = chapter["tracks"][0]
    track.update(trackUrl=asset.track_url, format=asset.format, type="audio")
    for k, v in (("duration", asset.duration), ("fileSize", asset.file_size),
                 ("channels", asset.channels)):
        if v is not None:
            track[k] = v
    if asset.duration is not None:
        chapter["duration"] = asset.duration


def title_chapter(book: int, asset: bsc.Asset) -> dict:
    key = bsc.announce_id(book)
    track = {
        "key": key,
        "title": asset.title,
        "type": "audio",
        "format": asset.format,
        "trackUrl": asset.track_url,
    }
    for k, v in (("duration", asset.duration), ("fileSize", asset.file_size),
                 ("channels", asset.channels)):
        if v is not None:
            track[k] = v
    chapter = {"key": key, "title": asset.title, "tracks": [track]}
    if asset.icon:
        track["display"] = chapter["display"] = {"icon16x16": asset.icon}
    if asset.duration is not None:
        chapter["duration"] = asset.duration
    return chapter


def insert_title_chapters(card: dict, titles: dict[int, bsc.Asset]) -> dict:
    """Return a copy of *card* with each book's title chapter before its first chapter."""
    out = copy.deepcopy(card)
    existing = {c["key"] for c in out["content"]["chapters"]}
    chapters: list[dict] = []
    seen_books: set[int] = set()
    for chapter in out["content"]["chapters"]:
        m = bsc.BOOK_RE.match(chapter["title"])
        if m and (book := int(m.group(1))) not in seen_books:
            seen_books.add(book)
            if book in titles and bsc.announce_id(book) not in existing:
                chapters.append(title_chapter(book, titles[book]))
        chapters.append(chapter)
    for n, chapter in enumerate(chapters, start=1):
        chapter["overlayLabel"] = str(n)
        for track in chapter["tracks"]:
            track["overlayLabel"] = str(n)
    out["content"]["chapters"] = chapters

    media = out.get("metadata", {}).get("media")
    if media:
        added = [c for c in chapters if c["key"] not in existing]
        media["duration"] = media.get("duration", 0) + sum(c.get("duration", 0) for c in added)
        media["fileSize"] = media.get("fileSize", 0) + sum(
            t.get("fileSize", 0) for c in added for t in c["tracks"])
    for field in SERVER_FIELDS:
        out.pop(field, None)
    return out


def check(before: dict, after: dict, books: list[int]) -> None:
    """Every original chapter survives in order; exactly one title chapter precedes each book."""
    keys_before = [c["key"] for c in before["content"]["chapters"]]
    chapters_after = after["content"]["chapters"]
    keys_after = [c["key"] for c in chapters_after]
    assert [k for k in keys_after if k in set(keys_before)] == keys_before, "original order changed"
    for b in books:
        i = keys_after.index(bsc.announce_id(b))
        assert keys_after.count(bsc.announce_id(b)) == 1
        assert chapters_after[i + 1]["title"].startswith(f"Book {b} Chapter 1"), chapters_after[i + 1]["title"]
    assert [c["overlayLabel"] for c in chapters_after] == [str(n) for n in range(1, len(keys_after) + 1)]
    for c in chapters_after:
        for t in c["tracks"]:
            assert t["trackUrl"].startswith("yoto:#"), c["title"]
    print(f"✓ {len(keys_before)} original chapters kept in order, "
          f"{len(keys_after) - len(keys_before)} title tracks added, labels 1-{len(keys_after)}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("card_id")
    ap.add_argument("--voice", default="Harper")
    ap.add_argument("--model", default="phonon")
    ap.add_argument("--audio-dir", type=Path, default=Path("book_selector_audio"))
    ap.add_argument("--backup-dir", type=Path, default=Path("backups"))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    client_id = os.environ.get("YOTO_CLIENT_ID")
    if not client_id:
        sys.exit("YOTO_CLIENT_ID is not set")
    token = bsc.get_access_token(client_id)
    headers = {"Authorization": f"Bearer {token}"}

    resp = requests.get(f"{bsc.API}/content/{args.card_id}", headers=headers, timeout=30)
    if resp.status_code == 403:
        sys.exit(f"{args.card_id} isn't owned by this account; log in as its owner "
                 "(scripts/yoto_login.py --force-login)")
    resp.raise_for_status()
    card = resp.json()["card"]
    print(f"Card: {card['title']!r} ({args.card_id}), {len(card['content']['chapters'])} chapters")

    books = list(bsc.parse_books(card))
    args.audio_dir.mkdir(exist_ok=True)
    first_icons = {b: ts[0].icon for b, ts in bsc.parse_books(card).items()}
    titles: dict[int, bsc.Asset] = {}
    for b in books:
        mp3 = bsc.generate_prompt(
            bsc.ANNOUNCE_TEXT.format(n=b, subtitle=bsc.SUBTITLES[b].replace("—", ", ")),
            args.audio_dir / f"announce-book{b}.mp3", args.model, args.voice)
        title = bsc.ANNOUNCE_TITLE.format(n=b, subtitle=bsc.SUBTITLES[b])
        if args.dry_run:
            titles[b] = bsc.Asset(title=title, track_url="yoto:#dry-run", format="mp3", icon=first_icons[b])
        else:
            titles[b] = bsc.prompt_asset(bsc.upload_audio(token, mp3), title, first_icons[b])

    payload = insert_title_chapters(card, titles)
    check(card, payload, books)

    starts = book_start_tracks(payload, books)
    text = intro_text(starts)
    print(f"Intro: {text}")
    intro_mp3 = bsc.generate_prompt(
        text, args.audio_dir / f"intro-{'-'.join(map(str, starts.values()))}.mp3", args.model, args.voice)
    if args.dry_run:
        print("Dry run: card not changed.")
        return
    old_intro_url = next(c for c in card["content"]["chapters"]
                         if c["title"] == INTRO_TITLE)["tracks"][0]["trackUrl"]
    replace_intro_audio(payload, bsc.prompt_asset(bsc.upload_audio(token, intro_mp3), INTRO_TITLE, None))

    args.backup_dir.mkdir(exist_ok=True)
    backup = args.backup_dir / f"{args.card_id}-{card.get('updatedAt', 'unknown')}.json"
    backup.write_text(json.dumps({"card": card}, indent=1))
    print(f"Backup written to {backup}")

    resp = requests.post(f"{bsc.API}/content", headers=headers, json=payload, timeout=60)
    if resp.status_code >= 400:
        sys.exit(f"Update failed: HTTP {resp.status_code}: {resp.text}")

    stored = requests.get(f"{bsc.API}/content/{args.card_id}", headers=headers, timeout=30).json()["card"]
    check(card, stored, books)
    assert book_start_tracks(stored, books) == starts
    stored_intro = next(c for c in stored["content"]["chapters"] if c["title"] == INTRO_TITLE)
    assert stored_intro["tracks"][0]["trackUrl"] != old_intro_url, "intro audio not replaced"
    print(f"✓ Intro replaced; books start at tracks {starts}")
    print(f"✓ Updated {args.card_id}: {stored['title']!r} now has {len(stored['content']['chapters'])} chapters")


if __name__ == "__main__":
    main()
