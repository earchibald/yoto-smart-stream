from __future__ import annotations

import io

import pytest
from PIL import Image

from yoto_mcp import icons


def _spec(**over):
    rows = ["." * 16] * 3 + ["...##########..."] * 10 + ["." * 16] * 3
    return {"name": "box", "rows": rows, "palette": {"#": "#33ccff"}, **over}


def test_render_is_deterministic_rgba_png():
    a, b = icons.render(_spec()), icons.render(_spec())
    assert a.png == b.png and a.sha256 == b.sha256
    assert icons.check_png(a.png) == []
    img = Image.open(io.BytesIO(a.png))
    assert img.size == (16, 16) and img.mode == "RGBA"
    assert img.getpixel((0, 0)) == (0, 0, 0, 0)
    assert img.getpixel((5, 5)) == (0x33, 0xCC, 0xFF, 255)
    assert icons.cached(a.sha256)[0] == a.png


def test_spec_errors_name_row_and_column():
    rows = list(_spec()["rows"])
    rows[4] = rows[4][:7] + "x" + rows[4][8:]
    with pytest.raises(icons.SpecError, match="row 5, column 8"):
        icons.render(_spec(rows=rows))
    with pytest.raises(icons.SpecError, match="exactly 16"):
        icons.render(_spec(rows=rows[:15]))


def test_lint_flags_dark_edge_and_strays():
    rows = ["#" + "." * 15] + ["." * 16] * 14 + ["......#........."]
    report = icons.render({"rows": rows, "palette": {"#": "#101010"}}).lint
    text = " ".join(report)
    assert "visible pixels" in text and "too dark" in text and "edge" in text and "stray" in text


def test_glyphs_fit_and_centre():
    for text in ("4", "8", "12", "A", "★", "☾"):
        spec = icons.glyph(text, "#ffcc00")
        r = icons.render(spec)
        assert icons.check_png(r.png) == []
        assert not any("edge" in w for w in r.lint), (text, r.lint)
    outlined = icons.glyph("4", "#ffcc00", outline="#ff3366")
    assert "o" in "".join(outlined["rows"])
    with pytest.raises(icons.SpecError):
        icons.glyph("@")


def test_from_image_and_contact_sheet(tmp_path):
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    for x in range(16, 48):
        for y in range(16, 48):
            img.putpixel((x, y), (255, 0, 0, 255))
    path = tmp_path / "red.png"
    img.save(path)
    spec = icons.from_image(str(path), max_colours=2)
    rendered = icons.render(spec)
    assert len(spec["palette"]) == 1
    sheet = Image.open(
        io.BytesIO(icons.contact_sheet([("red", rendered.png), ("box", icons.render(_spec()).png)]))
    )
    assert sheet.size[0] > 2 * 128 * 2
