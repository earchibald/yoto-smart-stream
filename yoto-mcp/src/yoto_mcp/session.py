"""The server's state for one process: linked accounts, the card index, plans, backups.

Everything the MCP tools do goes through ``Session``, so it can be tested without MCP.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path

import httpx

from . import cards, paths, plan, refs, vault
from .api import YotoAPI, YotoError
from .auth import LoginFlow, TokenManager

PLAN_TTL = 30 * 60
INDEX_TTL = 60
BACKUPS_KEPT = 20


@dataclass
class Plan:
    plan_id: str
    account: str  # short name
    sub: str
    card_id: str | None  # None for a new card
    base_title: str
    base_updated_at: str | None
    ops: list[dict]
    expected: dict
    diff: dict
    warnings: list[str]
    errors: list[str]
    created_at: float
    applied: dict | None = None

    def public(self) -> dict:
        return {
            "plan_id": self.plan_id,
            "card": self.base_title if self.card_id else f"(new) {plan.title_of(self.expected)}",
            "account": self.account,
            "diff": plan.diff_text(self.diff),
            "changes": self.diff,
            "warnings": self.warnings,
            "errors": self.errors,
            "base_last_changed": self.base_updated_at,
            "expires_in_minutes": max(0, int((self.created_at + PLAN_TTL - time.time()) // 60)),
            "can_apply": not self.errors and not plan.is_noop(self.diff),
        }


@dataclass
class RefBook:
    """Which ``yoto:#`` refs this account has seen as its own, and which belong to others."""

    owned: set[str] = field(default_factory=set)
    foreign: set[str] = field(default_factory=set)


class Session:
    def __init__(
        self,
        http: httpx.Client | None = None,
        clock: Callable[[], float] = time.time,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.http = http or httpx.Client(timeout=60)
        self.clock = clock
        self.sleep = sleep
        self.tokens = TokenManager(self.http, clock)
        self._apis: dict[str, YotoAPI] = {}
        self._index: dict[str, tuple[float, list[cards.Entry]]] = {}
        self._refs: dict[str, RefBook] = {}
        self.plans: dict[str, Plan] = {}
        self.pending_logins: dict[str, tuple[LoginFlow, str]] = {}

    # -------------------------------------------------------------- accounts

    def account(self, name: str | None = None) -> tuple[vault.Account, YotoAPI]:
        self.finish_logins()
        acct = vault.find_account(name)
        if acct.sub not in self._apis:
            self._apis[acct.sub] = YotoAPI(acct.sub, self.tokens, self.http, self.sleep)
        return acct, self._apis[acct.sub]

    def start_login(self, name: str, open_browser: bool = True) -> str:
        """Begin a browser login that links an account under ``name``; returns the URL."""
        if any(a.name.casefold() == name.casefold() for a in vault.accounts()):
            force = True
        else:
            force = bool(vault.accounts())
        flow = LoginFlow(force_login=force)
        url = flow.start(open_browser=open_browser)
        self.pending_logins[name] = (flow, name)
        return url

    def finish_logins(self) -> list[str]:
        """Register any browser logins that have completed. Returns messages."""
        out = []
        for key, (flow, name) in list(self.pending_logins.items()):
            if not flow.done:
                continue
            del self.pending_logins[key]
            if result := flow.result():
                existing = vault.account_by_sub(result.sub)
                if existing and existing.name.casefold() != name.casefold():
                    out.append(f"That login is the account already linked as {existing.name!r}.")
                else:
                    try:
                        vault.add_account(result.sub, name)
                        out.append(f"Linked account {name!r}.")
                    except ValueError as exc:  # the name belongs to a different account
                        out.append(f"Logged in, but not linked: {exc}")
                self.tokens.remember(result.sub, result.access_token, result.expires_in)
            else:
                out.append(f"Login for {name!r} failed: {flow.error()}")
        return out

    # -------------------------------------------------------------- card index

    def refs_for(self, sub: str) -> RefBook:
        if sub not in self._refs:
            f = paths.cache() / f"refs-{hashlib.sha256(sub.encode()).hexdigest()[:16]}.json"
            book = RefBook()
            if f.exists():
                data = json.loads(f.read_text())
                book = RefBook(set(data.get("owned", [])), set(data.get("foreign", [])))
            self._refs[sub] = book
        return self._refs[sub]

    def _save_refs(self, sub: str) -> None:
        book = self.refs_for(sub)
        f = paths.cache() / f"refs-{hashlib.sha256(sub.encode()).hexdigest()[:16]}.json"
        f.write_text(json.dumps({"owned": sorted(book.owned), "foreign": sorted(book.foreign)}))

    def note_card(self, sub: str, card: dict, owned: bool) -> None:
        book = self.refs_for(sub)
        found = refs.media_refs(card)
        all_refs = found["audio"] | found["icon"]
        if owned:
            book.owned |= all_refs
            book.foreign -= all_refs
        else:
            book.foreign |= all_refs - book.owned
        self._save_refs(sub)

    def note_owned(self, sub: str, *new_refs: str) -> None:
        book = self.refs_for(sub)
        book.owned.update(new_refs)
        book.foreign.difference_update(new_refs)
        self._save_refs(sub)

    def index(self, account: str | None = None, fresh: bool = False) -> list[cards.Entry]:
        acct, api = self.account(account)
        hit = self._index.get(acct.sub)
        if hit and not fresh and self.clock() - hit[0] < INDEX_TTL:
            return hit[1]
        entries: list[cards.Entry] = []
        mine = api.list_mine()
        mine_ids = {c["cardId"] for c in mine}
        for c in mine:
            entries.append(cards.Entry(c["cardId"], cards.title_of(c), acct.name, True, c.get("updatedAt")))
        for c in api.list_family():
            if c["cardId"] not in mine_ids:
                entries.append(
                    cards.Entry(c["cardId"], cards.title_of(c), acct.name, False, c.get("updatedAt"))
                )
        self._index[acct.sub] = (self.clock(), entries)
        return entries

    def forget_index(self, sub: str) -> None:
        self._index.pop(sub, None)

    def find(self, name: str, account: str | None = None, prefer_owned: bool = False) -> cards.Entry:
        try:
            return cards.resolve(name, self.index(account), prefer_owned=prefer_owned)
        except cards.NotFound as exc:
            # Maybe it lives on another linked account.
            here = vault.find_account(account)
            for other in vault.accounts():
                if other.sub == here.sub:
                    continue
                try:
                    hit = cards.resolve(name, self.index(other.name), prefer_owned=True)
                except LookupError:
                    continue
                raise LookupError(
                    f"{hit.title!r} isn't in {here.name!r}'s library but is in {other.name!r}'s. "
                    f"Pass account={other.name!r}."
                ) from exc
            raise

    def read(
        self, name: str, account: str | None = None
    ) -> tuple[vault.Account, YotoAPI, cards.Entry, dict, bool]:
        acct, api = self.account(account)
        entry = self.find(name, account)
        got = api.get_card(entry.card_id)
        self.note_card(acct.sub, got.card, got.owned)
        return acct, api, entry, got.card, got.owned

    # -------------------------------------------------------------- plans

    def make_plan(
        self,
        card: str,
        ops: list[dict],
        account: str | None = None,
        title: str | None = None,
        renumber: bool = True,
    ) -> Plan:
        acct, _api = self.account(account)
        if card.strip().casefold() == "new":
            if not title:
                raise ValueError("A new card needs a title.")
            base, card_id, base_title, updated, owned = plan.new_card(title), None, title, None, True
        else:
            acct, _api, entry, base, owned = self.read(card, account)
            card_id, base_title, updated = entry.card_id, cards.title_of(base), base.get("updatedAt")
        expected = plan.build(base, ops, renumber=renumber)
        d = plan.diff(base, expected)
        book = self.refs_for(acct.sub)
        report = plan.lint(expected, book.owned, book.foreign)
        errors = list(report["errors"])
        if not owned:
            errors.insert(
                0,
                f"{base_title!r} belongs to another account; {acct.name!r} can't change it. "
                "Plan against a copy (card='new') or use the owner's account.",
            )
        p = Plan(
            plan_id=secrets.token_urlsafe(8),
            account=acct.name,
            sub=acct.sub,
            card_id=card_id,
            base_title=base_title,
            base_updated_at=updated,
            ops=ops,
            expected=expected,
            diff=d,
            warnings=plan.warnings(base, expected, d) + report["warnings"],
            errors=errors,
            created_at=self.clock(),
        )
        self.plans[p.plan_id] = p
        self._persist(p)
        return p

    def _persist(self, p: Plan) -> None:
        (paths.plans() / f"{p.plan_id}.json").write_text(json.dumps(asdict(p), default=str))

    def get_plan(self, plan_id: str) -> Plan:
        p = self.plans.get(plan_id)
        if p is None:
            raise LookupError(f"No plan {plan_id!r} in this session. Make one with yoto_card_plan.")
        return p

    def apply(self, plan_id: str, verify_playback: bool = True) -> dict:
        p = self.get_plan(plan_id)
        if p.applied:
            return {**p.applied, "note": "This plan was already applied; nothing was sent again."}
        if self.clock() - p.created_at > PLAN_TTL:
            raise ValueError("This plan is older than 30 minutes. Make a fresh plan.")
        if p.errors:
            raise ValueError("The plan has errors and can't be applied: " + "; ".join(p.errors))
        if plan.is_noop(p.diff):
            return {"card": p.base_title, "changed": False, "note": "Nothing to change."}
        acct, api = self.account(p.account)
        backup_path = None
        body = dict(p.expected)
        body.pop("cardId", None)
        if p.card_id:
            current = api.get_card(p.card_id)
            if not current.owned:
                raise PermissionError(f"{p.base_title!r} isn't owned by {p.account!r}.")
            if current.card.get("updatedAt") != p.base_updated_at:
                raise RuntimeError(
                    f"{p.base_title!r} changed since the plan was made "
                    f"({p.base_updated_at} → {current.card.get('updatedAt')}). Make a fresh plan."
                )
            if cards.title_of(current.card) != p.base_title:
                raise RuntimeError(
                    f"The card is now titled {cards.title_of(current.card)!r}, "
                    f"not {p.base_title!r}. Make a fresh plan."
                )
            backup_path = self.backup(acct, p.card_id, current.card)
            body["cardId"] = p.card_id
        posted = api.post_card(body)
        card_id = p.card_id or posted.get("cardId")
        if not card_id:
            raise RuntimeError(f"Yoto accepted the write but returned no cardId: {str(posted)[:200]}")
        stored = api.get_card(card_id).card
        self.note_card(acct.sub, stored, True)
        problems = plan.compare(p.expected, stored)
        playback = self._probe(api, card_id, p) if verify_playback else {}
        result = {
            "card": cards.title_of(stored),
            "account": acct.name,
            "changed": True,
            "created": p.card_id is None,
            "verified": not problems and all(v == 206 for v in playback.values()),
            "problems": problems,
            "playback_checks": playback,
            "backup": backup_path,
            "last_changed": stored.get("updatedAt"),
        }
        if problems and backup_path:
            result["restore_hint"] = f"Restore with yoto_card_restore(card={p.base_title!r})."
        p.applied = result
        self._persist(p)
        self.forget_index(acct.sub)
        self._log(p, card_id, result)
        return result

    def _probe(self, api: YotoAPI, card_id: str, p: Plan) -> dict:
        """Ranged GETs on the first, last and changed tracks; 206 means playable."""
        try:
            playable = api.get_playable(card_id)
        except YotoError as exc:
            return {"playable": exc.status}
        chs = cards.chapters(playable)
        if not chs:
            return {}
        wanted = {chs[0]["key"], chs[-1]["key"]}
        wanted |= {x["key"] for x in p.diff["added"]} | {x["key"] for x in p.diff["changed"]}
        out = {}
        for c in chs:
            if c.get("key") in wanted and c.get("tracks"):
                url = c["tracks"][0].get("trackUrl")
                if isinstance(url, str) and url.startswith("https://"):
                    try:
                        out[c["key"]] = api.probe(url)
                    except httpx.HTTPError:
                        out[c["key"]] = 0
        return out

    def _log(self, p: Plan, card_id: str, result: dict) -> None:
        line = {
            "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "account": p.account,
            "card": result["card"],
            "card_id": card_id,
            "plan_id": p.plan_id,
            "backup": result.get("backup"),
            "last_changed": result.get("last_changed"),
            "verified": result.get("verified"),
        }
        with paths.change_log().open("a") as fh:
            fh.write(json.dumps(line) + "\n")

    # -------------------------------------------------------------- backups

    def backup(self, acct: vault.Account, card_id: str, card: dict) -> str:
        folder = paths.backups() / card_id
        folder.mkdir(parents=True, exist_ok=True)
        stamp = (card.get("updatedAt") or time.strftime("%Y-%m-%dT%H:%M:%S")).replace(":", "-")
        path = folder / f"{stamp}.json"
        path.write_text(
            json.dumps(
                {
                    "title": cards.title_of(card),
                    "account": acct.name,
                    "card_id": card_id,
                    "saved_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "card": card,
                },
                indent=1,
            )
        )
        for old in sorted(folder.glob("*.json"))[:-BACKUPS_KEPT]:
            old.unlink()
        return str(path)

    def backups(self, name: str, account: str | None = None) -> list[dict]:
        entry = self.find(name, account, prefer_owned=True)
        folder = paths.backups() / entry.card_id
        out = []
        for f in sorted(folder.glob("*.json"), reverse=True) if folder.exists() else []:
            data = json.loads(f.read_text())
            out.append(
                {
                    "backup": f.stem,
                    "title": data.get("title"),
                    "saved_at": data.get("saved_at"),
                    "chapters": len(cards.chapters(data.get("card") or {})),
                    "path": str(f),
                }
            )
        return out

    def restore_plan(self, name: str, backup: str | None = None, account: str | None = None) -> Plan:
        entry = self.find(name, account, prefer_owned=True)
        folder = paths.backups() / entry.card_id
        files = sorted(folder.glob("*.json")) if folder.exists() else []
        if not files:
            raise LookupError(f"No backups of {entry.title!r}.")
        chosen = next((f for f in files if f.stem == backup), None) if backup else files[-1]
        if chosen is None:
            raise LookupError(f"No backup {backup!r} of {entry.title!r}; see yoto_card_backups.")
        snapshot = json.loads(chosen.read_text())["card"]
        return self.make_plan(
            entry.title, [{"op": "replace_document", "card": snapshot}], account, renumber=False
        )

    # -------------------------------------------------------------- media

    def upload_file(self, path: str, account: str | None = None) -> dict:
        acct, api = self.account(account)
        f = Path(path).expanduser()
        if not f.is_file():
            raise FileNotFoundError(f"No file at {f}")
        media = api.upload_audio(f.read_bytes(), f.name, _audio_type(f.name))
        self.note_owned(acct.sub, media.ref)
        return {**media.as_dict(), "account": acct.name, "file": f.name}

    def media_import(
        self, card: str, from_account: str, to_account: str | None = None, chapters_: list[str] | None = None
    ) -> dict:
        """Copy a card's audio (and icons) from one linked account into another."""
        src_acct, src_api, entry, _card, _owned = self.read(card, from_account)
        dst_acct, dst_api = self.account(to_account)
        if src_acct.sub == dst_acct.sub:
            raise ValueError("Source and destination are the same account.")
        playable = src_api.get_playable(entry.card_id)
        mapping: dict[str, dict | str] = {}
        for c in cards.chapters(playable):
            if chapters_ and c.get("key") not in chapters_ and c.get("title") not in chapters_:
                continue
            for t in c.get("tracks") or []:
                url, old = t.get("trackUrl"), refs.to_ref(t.get("trackUrl"))
                if not (isinstance(url, str) and url.startswith("https://")) or old in mapping:
                    continue
                data = src_api.download(url)
                media = dst_api.upload_audio(data, f"{t.get('key') or 'track'}.{t.get('format', 'mp3')}")
                mapping[old] = media.as_dict()
                self.note_owned(dst_acct.sub, media.ref)
            for holder in [c.get("display") or {}] + [t.get("display") or {} for t in c.get("tracks") or []]:
                url = holder.get("icon16x16")
                old = refs.to_ref(url)
                if isinstance(url, str) and url.startswith("https://") and old not in mapping:
                    up = dst_api.upload_icon(
                        src_api.download(url), f"{refs.ref_id(old or 'icon')}.png", auto_convert=True
                    )
                    mapping[old] = up["ref"]
                    self.note_owned(dst_acct.sub, up["ref"])
        return {
            "card": entry.title,
            "from": src_acct.name,
            "to": dst_acct.name,
            "copied": len(mapping),
            "map": mapping,
            "next": "Use {'op': 'replace_refs', 'map': <map>} in a yoto_card_plan on the copy.",
        }

    # -------------------------------------------------------------- icons

    def search_icons(self, query: str, account: str | None = None, limit: int = 24) -> list[dict]:
        acct, api = self.account(account)
        words = [w for w in query.casefold().split() if w]
        results = []
        for source, items in (("mine", api.list_icons("me")), ("yoto", self._public_icons(api))):
            for icon in items:
                title = icon.get("title") or ""
                tags = icon.get("publicTags") or icon.get("tags") or []
                hay = " ".join([title, *tags]).casefold()
                if not words or all(w in hay for w in words):
                    media_id = icon.get("mediaId")
                    results.append(
                        {
                            "ref": refs.REF_PREFIX + media_id if media_id else None,
                            "title": title,
                            "tags": tags,
                            "url": icon.get("url"),
                            "source": source,
                        }
                    )
        # The account's own icons and Yoto's public ones are both safe to put on its cards.
        self.note_owned(acct.sub, *[r["ref"] for r in results if r["ref"]])
        return results[:limit]

    def _public_icons(self, api: YotoAPI) -> list[dict]:
        f = paths.cache() / "public-icons.json"
        if f.exists() and self.clock() - f.stat().st_mtime < 86400:
            return json.loads(f.read_text())
        items = api.list_icons("yoto")
        f.write_text(json.dumps(items))
        return items


def _audio_type(name: str) -> str:
    ext = name.rsplit(".", 1)[-1].lower()
    return {
        "mp3": "audio/mpeg",
        "m4a": "audio/mp4",
        "aac": "audio/aac",
        "wav": "audio/wav",
        "ogg": "audio/ogg",
        "flac": "audio/flac",
    }.get(ext, "application/octet-stream")
