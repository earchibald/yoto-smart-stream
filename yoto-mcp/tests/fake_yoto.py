"""An in-memory Yoto API with the behaviour recorded from the real Hilo calls (2026-11-07/08).

* ``/content/{id}`` is owner-only (403 otherwise); ``/card/{id}`` returns signed URLs.
* ``POST /content`` refuses audio refs the posting account didn't upload: 400 "Media file not found".
* Audio upload is sha256-addressed: a known sha gets ``uploadUrl: null``. Transcoding is async.
* Refresh tokens rotate on every use; a reused one is ``invalid_grant``.
"""

from __future__ import annotations

import base64
import copy
import hashlib
import itertools
import json
import urllib.parse

import httpx

SIGNED = "https://secure-media.yotoplay.com/{owner}~/{id}?Expires=1&Signature=x"


def make_jwt(sub: str, exp: float) -> str:
    def b64(obj: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(obj).encode()).rstrip(b"=").decode()

    return f"{b64({'alg': 'none'})}.{b64({'sub': sub, 'exp': exp})}.sig"


class FakeYoto:
    def __init__(self, now: float = 1_000_000.0):
        self.now = now
        self.cards: dict[str, dict] = {}  # cardId -> card (with userId)
        self.media_owner: dict[str, str] = {}  # media id (no yoto:#) -> sub
        self.icons: dict[str, dict] = {}  # mediaId -> icon record
        self.public_icons = [
            {
                "mediaId": "pubMoon",
                "title": "Moon",
                "publicTags": ["moon", "night", "sleep"],
                "url": "https://media-secure-v2.yotoplay.com/icons/pubMoon",
            },
            {
                "mediaId": "pubStar",
                "title": "Star",
                "publicTags": ["star", "night"],
                "url": "https://media-secure-v2.yotoplay.com/icons/pubStar",
            },
        ]
        self.refresh: dict[str, str] = {}  # live refresh token -> sub
        self.family: list[str] = []  # cardIds visible in every account's family library
        self.uploads: dict[str, dict] = {}
        self.pending_polls = 1  # transcode answers 202 this many times first
        self.calls: list[tuple[str, str]] = []
        self.token_calls = 0
        self.puts = 0
        self._ids = itertools.count(1)
        self._stamp = itertools.count(1)

    # ------------------------------------------------------------ setup helpers

    def add_account(self, sub: str) -> str:
        token = f"rt-{sub}-{next(self._ids)}"
        self.refresh[token] = sub
        return token

    def add_card(self, card: dict, owner: str, family: bool = False) -> str:
        card = copy.deepcopy(card)
        card["userId"] = owner
        card.setdefault("updatedAt", self._now_stamp())
        self.cards[card["cardId"]] = card
        for ch in card["content"]["chapters"]:
            for holder in [ch.get("display") or {}] + [t.get("display") or {} for t in ch["tracks"]]:
                if holder.get("icon16x16", "").startswith("yoto:#"):
                    self.media_owner.setdefault(holder["icon16x16"][6:], owner)
            for t in ch["tracks"]:
                if t.get("trackUrl", "").startswith("yoto:#"):
                    self.media_owner.setdefault(t["trackUrl"][6:], owner)
        if family:
            self.family.append(card["cardId"])
        return card["cardId"]

    def _now_stamp(self) -> str:
        return f"2026-11-08T02:00:{next(self._stamp):02d}.000Z"

    # ------------------------------------------------------------ transport

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handle)

    def handle(self, request: httpx.Request) -> httpx.Response:
        url = request.url
        self.calls.append((request.method, url.path))
        if url.host == "login.yotoplay.com":
            return self._token(request)
        if url.host in ("secure-media.yotoplay.com", "media-secure-v2.yotoplay.com"):
            return self._media_get(request)
        if url.host == "upload.example":
            self.puts += 1
            return httpx.Response(200)
        sub = self._auth(request)
        if sub is None:
            return httpx.Response(401, json={"error": "unauthorized"})
        path, method = url.path, request.method
        if method == "GET" and path == "/content/mine":
            mine = [self._listing(c) for c in self.cards.values() if c["userId"] == sub]
            return httpx.Response(200, json={"cards": mine})
        if method == "GET" and path == "/card/family/library":
            return httpx.Response(
                200,
                json={
                    "cards": [
                        {"cardId": cid, "title": self.cards[cid]["title"]}
                        for cid in self.family
                        if cid in self.cards
                    ]
                },
            )
        if path.startswith("/content/") and method == "GET":
            card = self.cards.get(path.split("/")[2])
            if card is None:
                return httpx.Response(404, json={"error": {"message": "Not found"}})
            if card["userId"] != sub:
                return httpx.Response(403, json={"error": {"message": "Forbidden"}})
            if url.params.get("playable") == "true":
                return httpx.Response(200, json={"card": self._signed(card)})
            return httpx.Response(200, json={"card": copy.deepcopy(card)})
        if path.startswith("/card/") and method == "GET":
            card = self.cards.get(path.split("/")[2])
            if card is None:
                return httpx.Response(404, json={"error": {"message": "Not found"}})
            return httpx.Response(200, json={"card": self._signed(card)})
        if path == "/content" and method == "POST":
            return self._post_content(sub, json.loads(request.content))
        if path.startswith("/content/") and method == "DELETE":
            card = self.cards.get(path.split("/")[2])
            if card is None or card["userId"] != sub:
                return httpx.Response(403, json={"error": "forbidden"})
            del self.cards[card["cardId"]]
            return httpx.Response(200, json={"status": "ok"})
        if path == "/media/transcode/audio/uploadUrl":
            sha = url.params["sha256"]
            upload_id = f"up-{next(self._ids)}"
            known = sha in self.uploads
            self.uploads.setdefault(sha, {"owner": sub, "polls": 0 if known else self.pending_polls})
            self.uploads[upload_id] = {"sha": sha, "owner": sub}
            return httpx.Response(
                200,
                json={
                    "upload": {
                        "uploadId": upload_id,
                        "uploadUrl": None if known else f"https://upload.example/{upload_id}",
                    }
                },
            )
        if path.startswith("/media/upload/") and path.endswith("/transcoded"):
            rec = self.uploads[path.split("/")[3]]
            state = self.uploads[rec["sha"]]
            if state["polls"] > 0:
                state["polls"] -= 1
                return httpx.Response(202, json={"transcode": {}})
            media_id = "tc" + rec["sha"][:20]
            self.media_owner.setdefault(media_id, rec["owner"])
            if self.media_owner[media_id] != rec["owner"]:
                # Same bytes uploaded by another account still yield a ref this account can use.
                self.media_owner[media_id + "@" + rec["owner"]] = rec["owner"]
            return httpx.Response(
                200,
                json={
                    "transcode": {
                        "transcodedSha256": media_id,
                        "transcodedInfo": {
                            "duration": 3,
                            "fileSize": 1234,
                            "channels": "mono",
                            "format": "opus",
                        },
                    }
                },
            )
        if path == "/media/displayIcons/user/me/upload" and method == "POST":
            body = request.content
            media_id = "ic" + hashlib.sha256(body).hexdigest()[:20]
            new = media_id not in self.icons
            self.icons[media_id] = {
                "mediaId": media_id,
                "userId": sub,
                "title": url.params.get("filename"),
                "url": f"https://media-secure-v2.yotoplay.com/icons/{media_id}",
                "png": _file_part(request),
            }
            self.media_owner.setdefault(media_id, sub)
            return httpx.Response(
                200,
                json={
                    "displayIcon": {k: v for k, v in self.icons[media_id].items() if k != "png"},
                    "new": new,
                },
            )
        if path == "/media/displayIcons/user/me":
            return httpx.Response(
                200,
                json={
                    "displayIcons": [
                        {k: v for k, v in i.items() if k != "png"}
                        for i in self.icons.values()
                        if i["userId"] == sub
                    ]
                },
            )
        if path == "/media/displayIcons/user/yoto":
            return httpx.Response(200, json={"displayIcons": self.public_icons})
        if path == "/media/coverImage/user/me/upload":
            return httpx.Response(
                200, json={"coverImage": {"mediaUrl": "https://card-content.yotoplay.com/cover/x"}}
            )
        return httpx.Response(404, json={"error": f"no fake route {method} {path}"})

    # ------------------------------------------------------------ behaviours

    def _token(self, request: httpx.Request) -> httpx.Response:
        self.token_calls += 1
        form = dict(urllib.parse.parse_qsl(request.content.decode()))
        if "client_secret" not in form:
            return httpx.Response(401, json={"error": "access_denied", "error_description": "Unauthorized"})
        if form["grant_type"] == "refresh_token":
            sub = self.refresh.pop(form["refresh_token"], None)
            if sub is None:
                return httpx.Response(403, json={"error": "invalid_grant", "error_description": "reused"})
            new = self.add_account(sub)
            return httpx.Response(
                200,
                json={
                    "access_token": make_jwt(sub, self.now + 86400),
                    "refresh_token": new,
                    "expires_in": 86400,
                },
            )
        return httpx.Response(400, json={"error": "unsupported_grant_type"})

    def _auth(self, request: httpx.Request) -> str | None:
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return None
        payload = header[7:].split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload))["sub"]

    def _listing(self, card: dict) -> dict:
        return {k: v for k, v in card.items() if k != "content"}

    def _signed(self, card: dict) -> dict:
        out = copy.deepcopy(card)
        for ch in out["content"]["chapters"]:
            holders = [ch.get("display") or {}] + [t.get("display") or {} for t in ch["tracks"]]
            for holder in holders:
                if holder.get("icon16x16", "").startswith("yoto:#"):
                    holder["icon16x16"] = SIGNED.format(owner="o", id=holder["icon16x16"][6:])
            for t in ch["tracks"]:
                if t.get("trackUrl", "").startswith("yoto:#"):
                    t["trackUrl"] = SIGNED.format(owner="o", id=t["trackUrl"][6:])
        return out

    def _post_content(self, sub: str, body: dict) -> httpx.Response:
        for ch in body["content"]["chapters"]:
            for t in ch["tracks"]:
                ref = t.get("trackUrl", "")
                if (
                    ref.startswith("yoto:#")
                    and self.media_owner.get(ref[6:]) != sub
                    and (ref[6:] + "@" + sub) not in self.media_owner
                ):
                    return httpx.Response(400, json={"error": {"message": "Media file not found"}})
        card_id = body.get("cardId")
        if card_id:
            if card_id not in self.cards or self.cards[card_id]["userId"] != sub:
                return httpx.Response(403, json={"error": "forbidden"})
        else:
            card_id = f"NEW{next(self._ids):02d}"
        stored = {**copy.deepcopy(body), "cardId": card_id, "userId": sub, "updatedAt": self._now_stamp()}
        self.cards[card_id] = stored
        return httpx.Response(200, json={"card": {"cardId": card_id, "title": stored["title"]}})

    def _media_get(self, request: httpx.Request) -> httpx.Response:
        media_id = request.url.path.rsplit("/", 1)[-1]
        if media_id in self.icons:
            return httpx.Response(200, content=self.icons[media_id]["png"])
        if request.headers.get("Range"):
            return httpx.Response(206, content=b"\x00")
        return httpx.Response(200, content=b"audio-bytes-" + media_id.encode())


def _file_part(request: httpx.Request) -> bytes:
    """Pull the uploaded file's bytes out of a multipart body (good enough for one PNG part)."""
    body = request.content
    start = body.find(b"\r\n\r\n") + 4
    end = body.rfind(b"\r\n--")
    return body[start:end]
