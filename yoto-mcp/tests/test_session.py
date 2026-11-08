from __future__ import annotations

import json

import pytest

from yoto_mcp import cards, paths
from yoto_mcp.cards import chapters

from .conftest import OWNER_A, OWNER_B, interactive_card

TITLE_AUDIO = {"ref": "yoto:#title4", "duration": 4, "fileSize": 100, "channels": "mono", "format": "mp3"}


def _first_of_book4(card):
    return next(c["key"] for c in chapters(card) if c["title"].startswith("Book 4 Chapter 1"))


def test_cards_are_found_by_title(session, fake, hilo):
    fake.add_card(interactive_card(hilo), OWNER_B)
    assert session.find("hilo books 4-8", "Eugene").card_id == "LIN01"  # exact, ignoring case
    assert session.find("Choose a Book", "Family").card_id == "SEL01"  # unique partial
    with pytest.raises(cards.Ambiguous):
        session.find("Hilo", "Family")  # both cards are visible to Family
    with pytest.raises(cards.NotFound, match="Closest titles"):
        session.find("Hilo Bokks 4-8", "Eugene")


def test_card_on_another_account_names_that_account(session, fake, hilo):
    fake.add_card(interactive_card(hilo), OWNER_B)
    with pytest.raises(LookupError, match="Pass account='Family'"):
        session.find("Hilo Books 4-8 (Choose a Book)", "Eugene")


def test_plan_apply_backs_up_writes_and_verifies(session, fake, hilo):
    ops = [
        {
            "op": "insert_chapter",
            "key": "announce-book4",
            "title": "Hilo Book 4: Waking the Monsters",
            "audio": TITLE_AUDIO,
            "before": _first_of_book4(hilo),
        }
    ]
    fake.media_owner["title4"] = OWNER_A
    p = session.make_plan("Hilo Books 4-8", ops, "Eugene")
    pub = p.public()
    assert pub["can_apply"] and pub["card"] == "Hilo Books 4-8"
    assert "+ add chapter 2: Hilo Book 4: Waking the Monsters" in pub["diff"]
    assert any("intro" in w for w in pub["warnings"])
    result = session.apply(p.plan_id)
    assert result["verified"], result
    assert result["playback_checks"] and set(result["playback_checks"].values()) == {206}
    stored = fake.cards["LIN01"]
    assert [c["key"] for c in stored["content"]["chapters"]][1] == "announce-book4"
    assert "updatedAt" not in json.dumps({k: v for k, v in stored.items() if k == "content"})
    backup = json.loads(open(result["backup"]).read())
    assert len(backup["card"]["content"]["chapters"]) == 7
    log = paths.change_log().read_text().strip().splitlines()
    assert json.loads(log[-1])["plan_id"] == p.plan_id
    # Applying twice sends nothing.
    posts = sum(1 for m, path in fake.calls if m == "POST" and path == "/content")
    again = session.apply(p.plan_id)
    assert "already applied" in again["note"]
    assert sum(1 for m, path in fake.calls if m == "POST" and path == "/content") == posts


def test_apply_refuses_when_card_changed_meanwhile(session, fake, hilo):
    p = session.make_plan(
        "Hilo Books 4-8", [{"op": "retitle", "chapter": "intro", "title": "Intro"}], "Eugene"
    )
    fake.cards["LIN01"]["updatedAt"] = "2026-11-08T09:00:00.000Z"
    with pytest.raises(RuntimeError, match="changed since the plan"):
        session.apply(p.plan_id)


def test_plan_expires(session, fake):
    p = session.make_plan(
        "Hilo Books 4-8", [{"op": "retitle", "chapter": "intro", "title": "Intro"}], "Eugene"
    )
    fake.now += 31 * 60
    with pytest.raises(ValueError, match="30 minutes"):
        session.apply(p.plan_id)


def test_family_card_is_read_only_and_its_refs_are_foreign(session, hilo):
    p = session.make_plan("Hilo Books 4-8", [{"op": "retitle", "chapter": "intro", "title": "x"}], "Family")
    assert p.errors and "belongs to another account" in p.errors[0]
    with pytest.raises(ValueError, match="has errors"):
        session.apply(p.plan_id)
    # A copy on Family that reuses Eugene's audio is caught before POST.
    _a, _api, _e, doc, _owned = session.read("Hilo Books 4-8", "Family")
    copy_plan = session.make_plan(
        "new", [{"op": "replace_document", "card": {**doc, "title": "Copy"}}], "Family", title="Copy"
    )
    assert any("owned by another account" in e for e in copy_plan.errors)


def test_media_import_then_copy_applies(session, fake, hilo):
    imported = session.media_import("Hilo Books 4-8", from_account="Eugene", to_account="Family")
    assert imported["copied"] >= 7  # every audio track, plus icons
    _a, _api, _e, doc, _owned = session.read("Hilo Books 4-8", "Family")
    p = session.make_plan(
        "new",
        [
            {"op": "replace_document", "card": {**doc, "title": "Hilo Books 4-8 (Family copy)"}},
            {"op": "replace_refs", "map": imported["map"]},
        ],
        "Family",
        title="Hilo Books 4-8 (Family copy)",
    )
    assert not p.errors, p.errors
    result = session.apply(p.plan_id)
    assert result["created"] and result["verified"], result
    assert session.find("Family copy", "Family").owned


def test_restore_from_backup(session, fake, hilo):
    p = session.make_plan("Hilo Books 4-8", [{"op": "remove_chapter", "chapter": "intro"}], "Eugene")
    session.apply(p.plan_id)
    assert len(fake.cards["LIN01"]["content"]["chapters"]) == 6
    backups = session.backups("Hilo Books 4-8", "Eugene")
    assert len(backups) == 1 and backups[0]["chapters"] == 7
    r = session.restore_plan("Hilo Books 4-8", account="Eugene")
    assert r.diff["added"][0]["title"] == "intro"
    session.apply(r.plan_id)
    assert len(fake.cards["LIN01"]["content"]["chapters"]) == 7


def test_new_card_needs_title(session):
    with pytest.raises(ValueError, match="title"):
        session.make_plan("new", [], "Eugene")


def test_upload_file_registers_owned_ref(session, tmp_path):
    f = tmp_path / "prompt.mp3"
    f.write_bytes(b"mp3-bytes")
    media = session.upload_file(str(f), "Eugene")
    assert media["ref"] in session.refs_for(OWNER_A).owned


def test_icon_search_matches_tags(session):
    hits = session.search_icons("night", "Eugene")
    assert {h["title"] for h in hits} == {"Moon", "Star"}
    assert session.search_icons("moon sleep", "Eugene")[0]["ref"] == "yoto:#pubMoon"
