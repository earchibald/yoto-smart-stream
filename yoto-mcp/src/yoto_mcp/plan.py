"""Edit ops on a whole card document, plus the diff, warnings and lint a plan reports.

Ops are small and addressed by chapter key (or exact chapter title), so applying the same
ops to their own result changes nothing.
"""

from __future__ import annotations

import copy
import re
from typing import Any

from . import refs
from .cards import chapters, title_of

STRUCTURAL = {"insert_chapter", "remove_chapter", "move_chapter", "replace_document"}
OPS = STRUCTURAL | {
    "retitle",
    "set_track_audio",
    "set_icon",
    "set_events",
    "set_config",
    "set_cover",
    "set_metadata",
    "replace_refs",
    "renumber_labels",
}
INTRO_RE = re.compile(r"\b(intro|introduction|contents|track list)\b", re.I)


class OpError(ValueError):
    pass


def new_card(title: str) -> dict:
    return {
        "title": title,
        "content": {"chapters": [], "config": {}, "playbackType": "linear"},
        "metadata": {"media": {}},
    }


# ------------------------------------------------------------------ addressing


def find_chapter(card: dict, ref: str) -> tuple[int, dict]:
    chs = chapters(card)
    for i, c in enumerate(chs):
        if c.get("key") == ref:
            return i, c
    by_title = [(i, c) for i, c in enumerate(chs) if (c.get("title") or "").casefold() == ref.casefold()]
    if len(by_title) == 1:
        return by_title[0]
    if len(by_title) > 1:
        raise OpError(f"Chapter title {ref!r} is used {len(by_title)} times; address it by key.")
    raise OpError(f"No chapter with key or title {ref!r}.")


def find_track(chapter: dict, ref: str | int | None) -> list[dict]:
    tracks = chapter.get("tracks") or []
    if ref is None or ref == "all":
        return tracks
    if isinstance(ref, int) or (isinstance(ref, str) and ref.isdigit()):
        i = int(ref) - 1
        if not 0 <= i < len(tracks):
            raise OpError(f"Chapter {chapter.get('key')!r} has no track {ref}.")
        return [tracks[i]]
    for t in tracks:
        if t.get("key") == ref or (t.get("title") or "").casefold() == str(ref).casefold():
            return [t]
    raise OpError(f"Chapter {chapter.get('key')!r} has no track {ref!r}.")


def _position(card: dict, op: dict) -> int:
    chs = chapters(card)
    if "before" in op:
        return find_chapter(card, op["before"])[0]
    if "after" in op:
        return find_chapter(card, op["after"])[0] + 1
    pos = op.get("position", "end")
    if pos == "start":
        return 0
    if pos == "end":
        return len(chs)
    if isinstance(pos, int):
        return max(0, min(len(chs), pos - 1))
    raise OpError(f"Unknown position {pos!r}: use before/after a chapter, 'start', 'end' or a number.")


# ------------------------------------------------------------------ building blocks


def _apply_audio(track: dict, audio: dict) -> None:
    ref = audio.get("ref") or audio.get("trackUrl")
    if not ref:
        raise OpError("audio needs a ref (yoto:#…), as returned by yoto_media_upload_wait.")
    track["trackUrl"] = ref
    track["type"] = audio.get("type", "stream" if str(ref).startswith("http") else "audio")
    track["format"] = audio.get("format") or track.get("format") or "mp3"
    for src, dst in (
        ("duration", "duration"),
        ("fileSize", "fileSize"),
        ("file_size", "fileSize"),
        ("channels", "channels"),
    ):
        if audio.get(src) is not None:
            track[dst] = audio[src]


def _make_track(spec: dict, default_key: str, default_title: str) -> dict:
    track = {"key": spec.get("key") or default_key, "title": spec.get("title") or default_title}
    _apply_audio(track, spec.get("audio") or spec)
    if spec.get("icon"):
        track["display"] = {"icon16x16": spec["icon"]}
    if spec.get("events"):
        track["events"] = spec["events"]
    return track


def _make_chapter(op: dict) -> dict:
    key = op.get("key")
    title = op.get("title")
    if not key or not title:
        raise OpError("insert_chapter needs a key and a title.")
    if op.get("tracks"):
        tracks = [
            _make_track(t, f"{key}-{i:02d}" if len(op["tracks"]) > 1 else key, t.get("title", title))
            for i, t in enumerate(op["tracks"], start=1)
        ]
    elif op.get("audio"):
        tracks = [
            _make_track(
                {"audio": op["audio"], "icon": op.get("icon"), "events": op.get("events")}, key, title
            )
        ]
    else:
        raise OpError("insert_chapter needs audio (one track) or tracks.")
    chapter: dict[str, Any] = {"key": key, "title": title, "tracks": tracks}
    if op.get("icon"):
        chapter["display"] = {"icon16x16": op["icon"]}
        for t in tracks:
            t.setdefault("display", {"icon16x16": op["icon"]})
    return chapter


def _recompute_durations(card: dict) -> None:
    total_d = total_s = 0
    for c in chapters(card):
        ds = [t.get("duration") for t in c.get("tracks") or []]
        if ds and all(d is not None for d in ds):
            c["duration"] = sum(ds)
        total_d += c.get("duration") or 0
        total_s += sum(t.get("fileSize") or 0 for t in c.get("tracks") or [])
    media = card.setdefault("metadata", {}).setdefault("media", {})
    if total_d:
        media["duration"] = total_d
    if total_s:
        media["fileSize"] = total_s


def renumber_labels(card: dict) -> None:
    for n, c in enumerate(chapters(card), start=1):
        c["overlayLabel"] = str(n)
        for t in c.get("tracks") or []:
            t["overlayLabel"] = str(n)


# ------------------------------------------------------------------ ops


def apply_op(card: dict, op: dict) -> None:
    kind = op.get("op")
    if kind not in OPS:
        raise OpError(f"Unknown op {kind!r}. Known ops: {', '.join(sorted(OPS))}.")
    content = card.setdefault("content", {})
    chs = content.setdefault("chapters", [])

    if kind == "replace_document":
        doc = refs.strip_server_fields(op["card"])
        doc.pop("cardId", None)  # the write target comes from the plan, never from the document
        card.clear()
        card.update(copy.deepcopy(doc))
    elif kind == "insert_chapter":
        new = _make_chapter(op)
        existing = next((c for c in chs if c.get("key") == new["key"]), None)
        if existing is not None:
            if _same_chapter(existing, new):
                return  # already there: replaying a plan is a no-op
            raise OpError(f"A different chapter with key {new['key']!r} already exists.")
        chs.insert(_position(card, op), new)
    elif kind == "remove_chapter":
        try:
            i, _ = find_chapter(card, op["chapter"])
        except OpError:
            return  # already gone
        chs.pop(i)
    elif kind == "move_chapter":
        i, c = find_chapter(card, op["chapter"])
        chs.pop(i)
        try:
            chs.insert(_position(card, op), c)
        except OpError:
            chs.insert(i, c)
            raise
    elif kind == "retitle":
        if not op.get("chapter"):
            card["title"] = op["title"]
            card.setdefault("metadata", {})["title"] = op["title"]
            return
        _, c = find_chapter(card, op["chapter"])
        if op.get("track") is None:
            c["title"] = op["title"]
            if len(c.get("tracks") or []) == 1:
                c["tracks"][0]["title"] = op["title"]
        else:
            for t in find_track(c, op["track"]):
                t["title"] = op["title"]
    elif kind == "set_track_audio":
        _, c = find_chapter(card, op["chapter"])
        tracks = find_track(c, op.get("track"))
        if len(tracks) != 1:
            raise OpError(f"Chapter {c.get('key')!r} has {len(tracks)} tracks; say which with track.")
        _apply_audio(tracks[0], op["audio"])
    elif kind == "set_icon":
        icon = op["icon"]
        _, c = find_chapter(card, op["chapter"])
        if op.get("track") is None:
            c.setdefault("display", {})["icon16x16"] = icon
            targets = c.get("tracks") or []
        else:
            targets = find_track(c, op["track"])
        for t in targets:
            t.setdefault("display", {})["icon16x16"] = icon
    elif kind == "set_events":
        _, c = find_chapter(card, op["chapter"])
        tracks = c.get("tracks") or []
        targets = find_track(c, op["track"]) if op.get("track") is not None else tracks[-1:]
        for t in targets:
            events = t.setdefault("events", {})
            for name, cmd in (op.get("events") or {}).items():
                if cmd is None:
                    events.pop(name, None)
                else:
                    events[name] = cmd
            if not events:
                t.pop("events")
    elif kind == "set_config":
        config = content.setdefault("config", {})
        for k, v in (op.get("config") or {}).items():
            if v is None:
                config.pop(k, None)
            else:
                config[k] = v
        if "playbackType" in op:
            content["playbackType"] = op["playbackType"]
    elif kind == "set_cover":
        card.setdefault("metadata", {}).setdefault("cover", {})["imageL"] = op["url"]
    elif kind == "set_metadata":
        meta = card.setdefault("metadata", {})
        for k, v in (op.get("metadata") or {}).items():
            if v is None:
                meta.pop(k, None)
            else:
                meta[k] = v
    elif kind == "replace_refs":
        # {"map": {"yoto:#old": "yoto:#new" | {"ref": …, "duration": …}}}, e.g. from yoto_media_import
        mapping = op.get("map") or {}
        for c in chs:
            disp = c.get("display") or {}
            if disp.get("icon16x16") in mapping:
                new = mapping[disp["icon16x16"]]
                disp["icon16x16"] = new["ref"] if isinstance(new, dict) else new
            for t in c.get("tracks") or []:
                if t.get("trackUrl") in mapping:
                    new = mapping[t["trackUrl"]]
                    _apply_audio(t, new if isinstance(new, dict) else {"ref": new})
                tdisp = t.get("display") or {}
                if tdisp.get("icon16x16") in mapping:
                    new = mapping[tdisp["icon16x16"]]
                    tdisp["icon16x16"] = new["ref"] if isinstance(new, dict) else new
    elif kind == "renumber_labels":
        renumber_labels(card)


def _same_chapter(a: dict, b: dict) -> bool:
    def core(c: dict) -> tuple:
        return (c.get("title"), tuple((t.get("key"), t.get("trackUrl")) for t in c.get("tracks") or []))

    return core(a) == core(b)


def build(base: dict, ops: list[dict], renumber: bool = True) -> dict:
    """The document that results from applying ``ops`` to ``base`` (``base`` is not changed)."""
    card = refs.strip_server_fields(base)
    for n, op in enumerate(ops, start=1):
        try:
            apply_op(card, op)
        except OpError as exc:
            raise OpError(f"op {n} ({op.get('op')}): {exc}") from None
        except KeyError as exc:
            raise OpError(f"op {n} ({op.get('op')}): missing field {exc}") from None
    if renumber and (any(o.get("op") in STRUCTURAL for o in ops) or _labels_off(card)):
        renumber_labels(card)
    _recompute_durations(card)
    return card


def _labels_off(card: dict) -> bool:
    labels = [c.get("overlayLabel") for c in chapters(card)]
    return any(labels) and labels != [str(n) for n in range(1, len(labels) + 1)]


# ------------------------------------------------------------------ diff


def _chapter_view(c: dict) -> dict:
    tracks = c.get("tracks") or []
    return {
        "title": c.get("title"),
        "label": c.get("overlayLabel"),
        "icon": (c.get("display") or {}).get("icon16x16"),
        "audio": [t.get("trackUrl") for t in tracks],
        "track_titles": [t.get("title") for t in tracks],
        "track_icons": [(t.get("display") or {}).get("icon16x16") for t in tracks],
        "events": [t.get("events") or {} for t in tracks],
    }


def diff(before: dict, after: dict) -> dict:
    b = {c["key"]: c for c in chapters(before)}
    a = {c["key"]: c for c in chapters(after)}
    b_order = [c["key"] for c in chapters(before)]
    a_order = [c["key"] for c in chapters(after)]
    added = [
        {"key": k, "title": a[k].get("title"), "position": a_order.index(k) + 1}
        for k in a_order
        if k not in b
    ]
    removed = [{"key": k, "title": b[k].get("title")} for k in b_order if k not in a]
    kept_b = [k for k in b_order if k in a]
    kept_a = [k for k in a_order if k in b]
    moved = [
        {"key": k, "title": a[k].get("title"), "from": b_order.index(k) + 1, "to": a_order.index(k) + 1}
        for k in kept_a
        if kept_b.index(k) != kept_a.index(k)
    ]
    changed = []
    relabelled = 0
    for k in kept_a:
        vb, va = _chapter_view(b[k]), _chapter_view(a[k])
        fields = [f for f in vb if f != "label" and vb[f] != va[f]]
        if vb["label"] != va["label"]:
            relabelled += 1
        if fields:
            changed.append(
                {
                    "key": k,
                    "title": a[k].get("title"),
                    "changes": {f: {"from": vb[f], "to": va[f]} for f in fields},
                }
            )
    card_changes = {}
    for label, get in (
        ("title", title_of),
        ("cover", lambda c: ((c.get("metadata") or {}).get("cover") or {}).get("imageL")),
        ("config", lambda c: (c.get("content") or {}).get("config") or {}),
        ("playbackType", lambda c: (c.get("content") or {}).get("playbackType")),
        ("description", lambda c: (c.get("metadata") or {}).get("description")),
    ):
        if get(before) != get(after):
            card_changes[label] = {"from": get(before), "to": get(after)}
    return {
        "added": added,
        "removed": removed,
        "moved": moved,
        "changed": changed,
        "relabelled_chapters": relabelled,
        "card": card_changes,
        "chapters_before": len(b_order),
        "chapters_after": len(a_order),
    }


def is_noop(d: dict) -> bool:
    return not (
        d["added"] or d["removed"] or d["moved"] or d["changed"] or d["card"] or d["relabelled_chapters"]
    )


def diff_text(d: dict) -> str:
    lines = []
    for x in d["added"]:
        lines.append(f"+ add chapter {x['position']}: {x['title']} [{x['key']}]")
    for x in d["removed"]:
        lines.append(f"- remove chapter: {x['title']} [{x['key']}]")
    for x in d["moved"]:
        lines.append(f"~ move {x['title']} [{x['key']}] from {x['from']} to {x['to']}")
    for x in d["changed"]:
        what = ", ".join(x["changes"])
        lines.append(f"* change {x['title']} [{x['key']}]: {what}")
    for k, v in d["card"].items():
        lines.append(f"* card {k}: {v['from']!r} -> {v['to']!r}")
    if d["relabelled_chapters"]:
        lines.append(f"  ({d['relabelled_chapters']} chapter labels renumbered)")
    lines.append(f"  chapters: {d['chapters_before']} -> {d['chapters_after']}")
    return "\n".join(lines) if lines else "no changes"


# ------------------------------------------------------------------ warnings and lint


def warnings(before: dict, after: dict, d: dict) -> list[str]:
    out = []
    if d["added"] or d["removed"] or d["moved"]:
        for c in chapters(after):
            if INTRO_RE.search(c.get("title") or ""):
                old = next((x for x in chapters(before) if x.get("key") == c.get("key")), None)
                if old and _chapter_view(old)["audio"] == _chapter_view(c)["audio"]:
                    out.append(
                        f"Chapter {c.get('title')!r} may name track numbers that this change "
                        "makes stale; regenerate its audio."
                    )
    if d["removed"]:
        out.append(f"{len(d['removed'])} chapter(s) will be removed; the backup keeps them.")
    return out


def lint(card: dict, owned_refs: set[str] | None = None, foreign_refs: set[str] | None = None) -> dict:
    errors: list[str] = []
    warns: list[str] = []
    chs = chapters(card)
    keys = [c.get("key") for c in chs]
    dupes = sorted({k for k in keys if keys.count(k) > 1})
    if dupes:
        errors.append(f"Duplicate chapter keys: {', '.join(map(str, dupes))}")
    if not chs:
        errors.append("The card has no chapters.")
    labels = [c.get("overlayLabel") for c in chs]
    if any(labels) and labels != [str(n) for n in range(1, len(chs) + 1)]:
        warns.append("Chapter labels don't run 1..N; add a renumber_labels op to fix them.")
    track_keys = {c.get("key"): {t.get("key") for t in c.get("tracks") or []} for c in chs}
    unknown = set()
    for c in chs:
        if not c.get("tracks"):
            errors.append(f"Chapter {c.get('key')!r} has no tracks.")
        for t in c.get("tracks") or []:
            url = t.get("trackUrl")
            if t.get("type") == "stream" and isinstance(url, str) and url.startswith("https://"):
                pass
            elif not refs.is_ref(url):
                errors.append(
                    f"Track {t.get('key')!r} in {c.get('key')!r} has no yoto:# audio ref ({url!r})."
                )
            elif foreign_refs and url in foreign_refs:
                errors.append(
                    f"Track {t.get('key')!r} uses audio owned by another account ({url}); "
                    "copy it with yoto_media_import first."
                )
            elif owned_refs is not None and url not in owned_refs:
                unknown.add(url)
            for name, cmd in (t.get("events") or {}).items():
                if cmd.get("cmd") == "goto":
                    p = cmd.get("params") or {}
                    if p.get("chapterKey") not in track_keys:
                        errors.append(
                            f"{c.get('key')}.{name} goes to missing chapter {p.get('chapterKey')!r}."
                        )
                    elif p.get("trackKey") and p["trackKey"] not in track_keys[p["chapterKey"]]:
                        errors.append(f"{c.get('key')}.{name} goes to missing track {p.get('trackKey')!r}.")
        for icon_holder in [c.get("display") or {}] + [t.get("display") or {} for t in c.get("tracks") or []]:
            icon = icon_holder.get("icon16x16")
            if foreign_refs and icon in foreign_refs:
                errors.append(f"Chapter {c.get('key')!r} uses an icon owned by another account ({icon}).")
    if unknown:
        warns.append(
            f"{len(unknown)} audio ref(s) weren't seen on this account's cards or uploads; "
            "if they came from another account's card, the write will fail."
        )
    return {"errors": errors, "warnings": warns}


def compare(expected: dict, stored: dict) -> list[str]:
    """Differences between the plan's document and what Yoto stored (after normalizing)."""
    problems = []
    e, s = chapters(expected), chapters(refs.normalize(stored))
    if [c.get("key") for c in e] != [c.get("key") for c in s]:
        problems.append("chapter order or keys differ")
    for ce, cs in zip(e, s, strict=False):
        ve, vs = _chapter_view(ce), _chapter_view(cs)
        for f in ve:
            if ve[f] != vs[f] and not (f == "icon" and ve[f] is None):
                problems.append(f"{ce.get('key')}: {f} differs")
    if title_of(expected) != title_of(stored):
        problems.append("title differs")
    ce, cs = (
        (expected.get("content") or {}).get("config") or {},
        (stored.get("content") or {}).get("config") or {},
    )
    for k, v in ce.items():
        if cs.get(k) != v:
            problems.append(f"config.{k} differs")
    return problems
