"""Thin Yoto API client for one account. Every card it returns is normalized (``yoto:#`` refs)."""

from __future__ import annotations

import hashlib
import time
from collections.abc import Callable
from dataclasses import dataclass, field

import httpx

from . import refs
from .auth import TokenManager

API = "https://api.yotoplay.com"


class YotoError(RuntimeError):
    def __init__(self, status: int, message: str, body: object = None):
        super().__init__(f"Yoto API HTTP {status}: {message}")
        self.status = status
        self.body = body


def _error(resp: httpx.Response) -> YotoError:
    try:
        body = resp.json()
    except ValueError:
        body = resp.text
    message = body
    if isinstance(body, dict):
        err = body.get("error")
        message = (err.get("message") if isinstance(err, dict) else err) or body.get("message") or body
    return YotoError(resp.status_code, str(message)[:500], body)


@dataclass
class CardRead:
    card: dict  # normalized
    owned: bool


@dataclass
class UploadTicket:
    sha256: str
    upload_id: str
    upload_url: str | None  # None: Yoto already has these bytes

    @property
    def exists(self) -> bool:
        return self.upload_url is None


@dataclass
class AudioMedia:
    ref: str
    duration: int | None = None
    file_size: int | None = None
    channels: str | None = None
    format: str = "mp3"
    extra: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "ref": self.ref,
            "duration": self.duration,
            "fileSize": self.file_size,
            "channels": self.channels,
            "format": self.format,
        }


class YotoAPI:
    def __init__(
        self,
        sub: str,
        tokens: TokenManager,
        http: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.sub = sub
        self._tokens = tokens
        self._http = http or httpx.Client(timeout=60)
        self._sleep = sleep

    # -------------------------------------------------------------- plumbing

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._tokens.access_token(self.sub)}"}

    def request(self, method: str, path: str, **kw) -> httpx.Response:
        url = path if path.startswith("http") else f"{API}{path}"
        headers = {**self._headers(), **kw.pop("headers", {})}
        return self._http.request(method, url, headers=headers, **kw)

    def _json(self, method: str, path: str, ok=(200, 201), **kw) -> dict:
        resp = self.request(method, path, **kw)
        if resp.status_code not in ok:
            raise _error(resp)
        return resp.json() if resp.content else {}

    # -------------------------------------------------------------- cards

    def list_mine(self) -> list[dict]:
        """Cards this account owns (MYO). Entries carry no chapters."""
        return _cards(self._json("GET", "/content/mine"))

    def list_family(self) -> list[dict]:
        """Cards in the family library, which includes cards owned by other family accounts."""
        try:
            return _cards(self._json("GET", "/card/family/library"))
        except YotoError as exc:
            if exc.status in (403, 404):
                return []
            raise

    def get_card(self, card_id: str) -> CardRead:
        """``/content/{id}`` for owned cards; ``/card/{id}`` (owned: False) when that is 403."""
        resp = self.request("GET", f"/content/{card_id}")
        if resp.status_code == 200:
            return CardRead(refs.normalize(resp.json()["card"]), owned=True)
        if resp.status_code not in (403, 404):
            raise _error(resp)
        resp2 = self.request("GET", f"/card/{card_id}")
        if resp2.status_code != 200:
            raise _error(resp if resp.status_code == 404 else resp2)
        return CardRead(refs.normalize(resp2.json()["card"]), owned=False)

    def get_playable(self, card_id: str) -> dict:
        """The card with short-lived signed URLs, NOT normalized: for listening only."""
        resp = self.request("GET", f"/content/{card_id}", params={"playable": "true", "signingType": "s3"})
        if resp.status_code in (403, 404):
            resp = self.request("GET", f"/card/{card_id}")
        if resp.status_code != 200:
            raise _error(resp)
        return resp.json()["card"]

    def post_card(self, card: dict) -> dict:
        """Create (no ``cardId``) or replace (with ``cardId``) a whole card."""
        body = refs.strip_server_fields(card)
        data = self._json("POST", "/content", json=body)
        return data.get("card", data)

    def delete_card(self, card_id: str) -> None:
        self._json("DELETE", f"/content/{card_id}", ok=(200, 204))

    # -------------------------------------------------------------- audio

    def audio_upload_begin(self, sha256: str, filename: str) -> UploadTicket:
        data = self._json(
            "GET", "/media/transcode/audio/uploadUrl", params={"sha256": sha256, "filename": filename}
        )
        up = data["upload"]
        return UploadTicket(sha256=sha256, upload_id=up["uploadId"], upload_url=up.get("uploadUrl"))

    def put_bytes(self, url: str, data: bytes, content_type: str = "audio/mpeg") -> None:
        resp = self._http.put(url, content=data, headers={"Content-Type": content_type}, timeout=300)
        if resp.status_code >= 400:
            raise _error(resp)

    def audio_upload_wait(self, upload_id: str, timeout: float = 180, interval: float = 1.0) -> AudioMedia:
        deadline = time.monotonic() + timeout
        while True:
            resp = self.request("GET", f"/media/upload/{upload_id}/transcoded", params={"loudnorm": "false"})
            if resp.status_code == 200:
                tc = resp.json().get("transcode") or {}
                if tc.get("transcodedSha256"):
                    info = tc.get("transcodedInfo") or {}
                    return AudioMedia(
                        ref=refs.REF_PREFIX + tc["transcodedSha256"],
                        duration=info.get("duration"),
                        file_size=info.get("fileSize"),
                        channels=info.get("channels"),
                        format=info.get("format", "mp3"),
                    )
            elif resp.status_code not in (202, 404):
                raise _error(resp)
            if time.monotonic() >= deadline:
                raise TimeoutError(f"Transcoding of upload {upload_id} didn't finish in {timeout:.0f}s")
            self._sleep(interval)

    def upload_audio(self, data: bytes, filename: str, content_type: str = "audio/mpeg") -> AudioMedia:
        ticket = self.audio_upload_begin(hashlib.sha256(data).hexdigest(), filename)
        if ticket.upload_url:
            self.put_bytes(ticket.upload_url, data, content_type)
        return self.audio_upload_wait(ticket.upload_id)

    # -------------------------------------------------------------- icons and covers

    def upload_icon(self, png: bytes, filename: str, auto_convert: bool = False) -> dict:
        """Returns ``{"ref": "yoto:#<mediaId>", "new": bool, "raw": {...}}``."""
        data = self._json(
            "POST",
            "/media/displayIcons/user/me/upload",
            params={"autoConvert": str(auto_convert).lower(), "filename": filename},
            files={"file": (filename, png, "image/png")},
        )
        icon = data.get("displayIcon") or data
        return {
            "ref": refs.REF_PREFIX + icon["mediaId"],
            "new": data.get("new", icon.get("new")),
            "url": icon.get("url"),
            "raw": icon,
        }

    def list_icons(self, which: str = "me") -> list[dict]:
        """``which`` is ``me`` (this account's uploads) or ``yoto`` (Yoto's public icons)."""
        data = self._json("GET", f"/media/displayIcons/user/{which}")
        return data.get("displayIcons") or data.get("icons") or []

    def upload_cover(self, image: bytes, content_type: str, auto_convert: bool = True) -> dict:
        data = self._json(
            "POST",
            "/media/coverImage/user/me/upload",
            params={"autoconvert": str(auto_convert).lower(), "coverType": "default"},
            content=image,
            headers={"Content-Type": content_type},
        )
        cover = data.get("coverImage") or data
        return {"url": cover.get("mediaUrl"), "raw": cover}

    def download(self, url: str) -> bytes:
        resp = self._http.get(url, timeout=300, follow_redirects=True)
        if resp.status_code != 200:
            raise _error(resp)
        return resp.content

    def probe(self, url: str) -> int:
        """Status of a one-byte ranged GET (206 means the media is playable)."""
        resp = self._http.get(url, headers={"Range": "bytes=0-0"}, timeout=30, follow_redirects=True)
        return resp.status_code


def _cards(data: object) -> list[dict]:
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        items = data.get("cards") or data.get("items") or data.get("content") or []
    else:
        items = []
    out = []
    for item in items:
        card = item.get("card", item) if isinstance(item, dict) else None
        if isinstance(card, dict) and card.get("cardId"):
            out.append(card)
    return out
