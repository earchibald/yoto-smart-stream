from __future__ import annotations

import asyncio
import json

from yoto_mcp import server

EXPECTED = {
    "yoto_whoami",
    "yoto_account_link",
    "yoto_cards_list",
    "yoto_card_get",
    "yoto_card_playable",
    "yoto_card_plan",
    "yoto_card_apply",
    "yoto_card_backups",
    "yoto_card_restore",
    "yoto_media_upload_begin",
    "yoto_media_upload_wait",
    "yoto_media_upload_file",
    "yoto_media_import",
    "yoto_icon_render",
    "yoto_icon_glyph",
    "yoto_icon_from_image",
    "yoto_icon_upload",
    "yoto_icons_search",
    "yoto_cover_upload",
}


def test_tools_and_annotations():
    tools = {t.name: t for t in asyncio.run(server.mcp.list_tools())}
    assert set(tools) == EXPECTED
    writers = {n for n, t in tools.items() if t.annotations and t.annotations.destructiveHint}
    assert writers == {"yoto_card_apply"}
    assert "insert_chapter" in tools["yoto_card_plan"].description


def test_tools_run_against_the_fake(session, monkeypatch):
    monkeypatch.setattr(server, "_session", session)

    async def call(name, args):
        return await server.mcp.call_tool(name, args)

    listed = asyncio.run(call("yoto_cards_list", {"account": "Eugene"}))
    payload = listed[1] if isinstance(listed, tuple) else json.loads(listed[0].text)
    assert payload["cards"][0]["title"] == "Hilo Books 4-8"
    assert "card_id" not in json.dumps(payload)

    got = asyncio.run(call("yoto_card_get", {"card": "Hilo Books 4-8", "account": "Eugene"}))
    got = got[1] if isinstance(got, tuple) else json.loads(got[0].text)
    assert got["summary"]["chapters"] == 7 and got["outline"][0]["title"] == "intro"

    glyph = asyncio.run(call("yoto_icon_glyph", {"text": "4", "colour": "#ffcc00"}))
    content = glyph[0] if isinstance(glyph, tuple) else glyph
    assert any(getattr(c, "type", "") == "image" for c in content)
