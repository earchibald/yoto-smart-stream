"""Live checks for the design's open questions. They write to the account, then clean up.

* ``icons``: does an icon uploaded with autoConvert=false come back pixel-identical, with its
  transparency?
* ``resume``: does Yoto accept ``resumeTimeout: 0`` (and keep ``1``)? Uses a scratch card that is
  deleted afterwards.
"""

from __future__ import annotations

import io
import math
import struct
import wave

from PIL import Image

from . import icons
from .session import Session

SCRATCH_TITLE = "yoto-mcp check (safe to delete)"


def _rgba(png: bytes) -> list[tuple[int, int, int, int]]:
    img = Image.open(io.BytesIO(png)).convert("RGBA")
    return list(img.getdata())  # type: ignore[arg-type]


def check_icons(s: Session, account: str | None = None) -> dict:
    _acct, api = s.account(account)
    spec = icons.glyph("4", "#ffcc00", outline="#ff3366", name="yoto-mcp-check-4")
    rendered = icons.render(spec)
    up = api.upload_icon(rendered.png, "yoto-mcp-check-4.png", auto_convert=False)
    url = up.get("url")
    if not url:
        media_id = up["ref"].removeprefix("yoto:#")
        url = next((i.get("url") for i in api.list_icons("me") if i.get("mediaId") == media_id), None)
    if not url:
        return {
            "check": "icons",
            "ok": False,
            "detail": "Upload worked but no download URL was found.",
            "upload": {k: v for k, v in up.items() if k != "raw"},
            "raw": up.get("raw"),
        }
    back = api.download(url)
    want, got = _rgba(rendered.png), _rgba(back)
    size = Image.open(io.BytesIO(back)).size
    diffs = sum(1 for a, b in zip(want, got, strict=False) if a != b)
    transparent_kept = all(g[3] == 0 for w, g in zip(want, got, strict=False) if w[3] == 0)
    return {
        "check": "icons",
        "ok": size == (16, 16) and diffs == 0,
        "same_bytes": back == rendered.png,
        "downloaded_size": list(size),
        "downloaded_format": Image.open(io.BytesIO(back)).format,
        "pixels_different": diffs,
        "transparency_kept": transparent_kept,
        "new_upload": up.get("new"),
        "ref": up["ref"],
    }


def _silent_wav(seconds: float = 1.0, rate: int = 22050) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        # A quiet 440 Hz tone, so the transcoder has real audio to work with.
        frames = b"".join(
            struct.pack("<h", int(800 * math.sin(2 * math.pi * 440 * i / rate)))
            for i in range(int(seconds * rate))
        )
        w.writeframes(frames)
    return buf.getvalue()


def check_resume(s: Session, account: str | None = None) -> dict:
    _acct, api = s.account(account)
    media = api.upload_audio(_silent_wav(), "yoto-mcp-check.wav", "audio/wav")
    card = {
        "title": SCRATCH_TITLE,
        "content": {
            "playbackType": "linear",
            "config": {"resumeTimeout": 0},
            "chapters": [
                {
                    "key": "01",
                    "title": "check",
                    "overlayLabel": "1",
                    "tracks": [
                        {
                            "key": "01",
                            "title": "check",
                            "overlayLabel": "1",
                            "type": "audio",
                            "format": media.format,
                            "trackUrl": media.ref,
                            "duration": media.duration,
                            "fileSize": media.file_size,
                            "channels": media.channels,
                        }
                    ],
                }
            ],
        },
        "metadata": {"description": "Created by `yoto-mcp check resume`; deleted straight after."},
    }
    results: dict = {"check": "resume"}
    card_id = None
    try:
        created = api.post_card(card)
        card_id = created.get("cardId")
        stored = api.get_card(card_id).card if card_id else {}
        results["zero_accepted"] = True
        results["zero_stored_as"] = (
            (stored.get("content") or {}).get("config", {}).get("resumeTimeout", "absent")
        )
    except Exception as exc:  # the answer we're looking for may be a 400
        results["zero_accepted"] = False
        results["zero_error"] = str(exc)[:300]
    try:
        if card_id is None:
            card["content"]["config"]["resumeTimeout"] = 1
            card_id = api.post_card(card).get("cardId")
        else:
            card["cardId"] = card_id
            card["content"]["config"]["resumeTimeout"] = 1
            api.post_card(card)
        stored = api.get_card(card_id).card
        results["one_stored_as"] = (
            (stored.get("content") or {}).get("config", {}).get("resumeTimeout", "absent")
        )
    finally:
        if card_id:
            try:
                api.delete_card(card_id)
                results["scratch_card_deleted"] = True
            except Exception as exc:
                results["scratch_card_deleted"] = False
                results["cleanup"] = f"Delete the card titled {SCRATCH_TITLE!r} by hand: {exc}"
    results["ok"] = True
    return results


CHECKS = {"icons": check_icons, "resume": check_resume}
