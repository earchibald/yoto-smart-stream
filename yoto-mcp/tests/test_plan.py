from __future__ import annotations

import pytest

from yoto_mcp import plan
from yoto_mcp.cards import chapters

TITLE_AUDIO = {"ref": "yoto:#title4", "duration": 4, "fileSize": 100, "channels": "mono", "format": "mp3"}


def _keys(card):
    return [c["key"] for c in chapters(card)]


def _first_of(card, book):
    return next(c["key"] for c in chapters(card) if c["title"].startswith(f"Book {book} Chapter 1"))


def test_insert_title_tracks_renumbers_and_flags_intro(hilo):
    ops = [
        {
            "op": "insert_chapter",
            "key": "announce-book4",
            "title": "Hilo Book 4: Waking the Monsters",
            "audio": TITLE_AUDIO,
            "before": _first_of(hilo, 4),
        },
        {
            "op": "insert_chapter",
            "key": "announce-book5",
            "title": "Hilo Book 5: Then Everything Went Wrong",
            "audio": {**TITLE_AUDIO, "ref": "yoto:#title5"},
            "before": _first_of(hilo, 5),
        },
    ]
    after = plan.build(hilo, ops)
    keys = _keys(after)
    assert keys.index("announce-book4") == keys.index(_first_of(hilo, 4)) - 1
    assert [c["overlayLabel"] for c in chapters(after)] == [str(n) for n in range(1, 10)]
    assert all(t["overlayLabel"] == c["overlayLabel"] for c in chapters(after) for t in c["tracks"])
    d = plan.diff(hilo, after)
    assert [a["key"] for a in d["added"]] == ["announce-book4", "announce-book5"]
    assert d["chapters_before"] == 7 and d["chapters_after"] == 9
    warns = plan.warnings(hilo, after, d)
    assert any("intro" in w for w in warns)
    # Replaying the same ops on the result changes nothing.
    again = plan.build(after, ops)
    assert plan.is_noop(plan.diff(after, again))


def test_inserted_chapter_inherits_icon_on_tracks(hilo):
    after = plan.build(
        hilo,
        [
            {
                "op": "insert_chapter",
                "key": "x",
                "title": "X",
                "audio": TITLE_AUDIO,
                "icon": "yoto:#icon4",
                "position": "start",
            }
        ],
    )
    first = chapters(after)[0]
    assert first["display"]["icon16x16"] == "yoto:#icon4"
    assert first["tracks"][0]["display"]["icon16x16"] == "yoto:#icon4"
    assert first["duration"] == 4


def test_conflicting_insert_is_an_error(hilo):
    key = chapters(hilo)[0]["key"]
    with pytest.raises(plan.OpError, match="already exists"):
        plan.build(hilo, [{"op": "insert_chapter", "key": key, "title": "other", "audio": TITLE_AUDIO}])


def test_remove_move_retitle_by_title(hilo):
    ops = [
        {"op": "remove_chapter", "chapter": "intro"},
        {"op": "move_chapter", "chapter": _first_of(hilo, 5), "position": "start"},
        {"op": "retitle", "title": "Hilo Books 4-8 (copy)"},
    ]
    after = plan.build(hilo, ops)
    assert chapters(after)[0]["title"].startswith("Book 5 Chapter 1")
    assert "intro" not in [c["title"] for c in chapters(after)]
    d = plan.diff(hilo, after)
    assert d["removed"][0]["title"] == "intro"
    assert d["card"]["title"]["to"] == "Hilo Books 4-8 (copy)"
    # Removing what's already gone is a no-op.
    assert plan.is_noop(plan.diff(after, plan.build(after, ops)))


def test_set_icon_events_config(hilo):
    k = chapters(hilo)[1]["key"]
    after = plan.build(
        hilo,
        [
            {"op": "set_icon", "chapter": k, "icon": "yoto:#num4"},
            {"op": "set_events", "chapter": k, "events": {"onEnd": {"cmd": "stop"}}},
            {"op": "set_config", "config": {"resumeTimeout": 1, "onlineOnly": None}},
        ],
    )
    ch = chapters(after)[1]
    assert ch["display"]["icon16x16"] == "yoto:#num4" == ch["tracks"][0]["display"]["icon16x16"]
    assert ch["tracks"][-1]["events"] == {"onEnd": {"cmd": "stop"}}
    assert after["content"]["config"] == {"resumeTimeout": 1}
    d = plan.diff(hilo, after)
    assert {"icon", "track_icons", "events"} <= set(d["changed"][0]["changes"])


def test_lint_catches_foreign_refs_bad_gotos_and_labels(hilo):
    foreign = {chapters(hilo)[1]["tracks"][0]["trackUrl"]}
    after = plan.build(
        hilo,
        [
            {
                "op": "set_events",
                "chapter": chapters(hilo)[0]["key"],
                "events": {"onEnd": {"cmd": "goto", "params": {"chapterKey": "nope"}}},
            }
        ],
    )
    report = plan.lint(after, owned_refs=set(), foreign_refs=foreign)
    assert any("another account" in e for e in report["errors"])
    assert any("missing chapter 'nope'" in e for e in report["errors"])
    assert report["warnings"]
    bad = plan.build(hilo, [], renumber=False)
    chapters(bad)[0]["overlayLabel"] = "9"
    assert any("1..N" in w for w in plan.lint(bad)["warnings"])


def test_replace_refs(hilo):
    old = chapters(hilo)[1]["tracks"][0]["trackUrl"]
    icon = chapters(hilo)[1]["display"]["icon16x16"]
    after = plan.build(
        hilo,
        [{"op": "replace_refs", "map": {old: {"ref": "yoto:#new", "duration": 9}, icon: "yoto:#newicon"}}],
    )
    ch = chapters(after)[1]
    assert ch["tracks"][0]["trackUrl"] == "yoto:#new" and ch["tracks"][0]["duration"] == 9
    assert ch["display"]["icon16x16"] == "yoto:#newicon"
    assert ch["tracks"][0]["display"]["icon16x16"] == "yoto:#newicon"


def test_unknown_op_names_the_known_ones(hilo):
    with pytest.raises(plan.OpError, match="Known ops"):
        plan.build(hilo, [{"op": "explode"}])


def test_compare_spots_dropped_chapters(hilo):
    stored = plan.build(hilo, [{"op": "remove_chapter", "chapter": "intro"}])
    assert "chapter order or keys differ" in plan.compare(hilo, stored)
    assert plan.compare(hilo, hilo) == []
