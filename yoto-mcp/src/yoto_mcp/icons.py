"""16×16 icons from a character grid: deterministic RGBA PNGs, a lint report and a preview sheet.

Claude never paints pixels by describing an image. It writes 16 rows of 16 characters and a
palette; this module turns that into bytes. The same spec always gives the same bytes and
sha256, so Yoto recognises a re-upload and the local cache can key on it.
"""

from __future__ import annotations

import hashlib
import io
import json
import struct
import zlib
from dataclasses import dataclass, field

from PIL import Image, ImageDraw

from . import paths

SIZE = 16
TRANSPARENT = (0, 0, 0, 0)
DEFAULT_TRANSPARENT_CHARS = (".", " ")


class SpecError(ValueError):
    pass


@dataclass
class Rendered:
    name: str
    png: bytes
    sha256: str
    spec: dict
    lint: list[str] = field(default_factory=list)

    @property
    def path(self) -> str:
        return str(paths.icons() / f"{self.sha256}.png")

    def info(self) -> dict:
        return {"name": self.name, "sha256": self.sha256, "path": self.path, "lint": self.lint}


# ------------------------------------------------------------------ colours


def parse_colour(value: str) -> tuple[int, int, int, int]:
    v = value.strip().lower()
    if v in ("transparent", "none", "clear"):
        return TRANSPARENT
    if v.startswith("#") and len(v) in (7, 9):
        try:
            rgb = tuple(int(v[i : i + 2], 16) for i in range(1, len(v), 2))
        except ValueError:
            pass
        else:
            return rgb if len(rgb) == 4 else (*rgb, 255)  # type: ignore[return-value]
    raise SpecError(f"Colour {value!r} must be #RRGGBB, #RRGGBBAA or transparent.")


def _luminance(rgb: tuple[int, int, int]) -> float:
    def ch(c: int) -> float:
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (ch(x) for x in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


# ------------------------------------------------------------------ render


def pixels(spec: dict) -> list[list[tuple[int, int, int, int]]]:
    rows = spec.get("rows")
    palette_in = spec.get("palette") or {}
    if not isinstance(rows, list) or len(rows) != SIZE:
        raise SpecError(f"rows must be a list of exactly {SIZE} strings (got {len(rows or [])}).")
    palette = {c: TRANSPARENT for c in DEFAULT_TRANSPARENT_CHARS}
    for ch, colour in palette_in.items():
        if len(ch) != 1:
            raise SpecError(f"Palette key {ch!r} must be a single character.")
        palette[ch] = parse_colour(colour)
    grid = []
    problems = []
    for r, row in enumerate(rows, start=1):
        if not isinstance(row, str) or len(row) != SIZE:
            problems.append(
                f"row {r} has {len(row) if isinstance(row, str) else '?'} characters, needs {SIZE}"
            )
            continue
        out = []
        for c, ch in enumerate(row, start=1):
            if ch not in palette:
                problems.append(f"row {r}, column {c}: {ch!r} isn't in the palette")
                out.append(TRANSPARENT)
            else:
                out.append(palette[ch])
        grid.append(out)
    if problems:
        raise SpecError("; ".join(problems[:12]))
    return grid


def encode_png(grid: list[list[tuple[int, int, int, int]]]) -> bytes:
    """A minimal PNG: IHDR (8-bit RGBA, colour type 6), one IDAT, IEND. No gamma/ICC/text chunks."""
    raw = b"".join(b"\x00" + bytes(v for px in row for v in px) for row in grid)

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))

    ihdr = struct.pack(">IIBBBBB", SIZE, SIZE, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def check_png(png: bytes) -> list[str]:
    """Problems against Yoto's rule for unconverted icons: 16×16, 24-bit RGBA, no palette."""
    problems = []
    if png[:8] != b"\x89PNG\r\n\x1a\n":
        return ["not a PNG"]
    width, height, depth, colour_type = struct.unpack(">IIBB", png[16:26])
    if (width, height) != (SIZE, SIZE):
        problems.append(f"size is {width}×{height}, needs 16×16")
    if depth != 8 or colour_type != 6:
        problems.append(f"bit depth {depth}, colour type {colour_type}; needs 8-bit RGBA (type 6)")
    pos, tags = 8, []
    while pos < len(png):
        (length,) = struct.unpack(">I", png[pos : pos + 4])
        tags.append(png[pos + 4 : pos + 8].decode("latin-1"))
        pos += 12 + length
    extra = [t for t in tags if t not in ("IHDR", "IDAT", "IEND")]
    if extra:
        problems.append(f"unexpected chunks: {', '.join(extra)}")
    return problems


def lint(grid: list[list[tuple[int, int, int, int]]]) -> list[str]:
    out = []
    opaque = {(y, x) for y, row in enumerate(grid) for x, px in enumerate(row) if px[3] > 0}
    if len(opaque) < 12:
        out.append(f"only {len(opaque)} visible pixels; it will be hard to see")
    colours = {px[:3] for row in grid for px in row if px[3] > 0}
    if len(colours) > 6:
        out.append(f"{len(colours)} colours; 4 or fewer read best at 16×16")
    dark = sorted(f"#{r:02x}{g:02x}{b:02x}" for r, g, b in colours if _luminance((r, g, b)) < 0.05)
    if dark:
        out.append(f"colours too dark for the player's black screen: {', '.join(dark)}")
    if any(y in (0, SIZE - 1) or x in (0, SIZE - 1) for y, x in opaque):
        out.append("art touches the edge; leave a 1 px margin")
    strays = [
        (y, x)
        for y, x in opaque
        if not any((y + dy, x + dx) in opaque for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dy or dx)
    ]
    if strays:
        y, x = strays[0]
        out.append(f"{len(strays)} stray single pixel(s), e.g. row {y + 1}, column {x + 1}")
    if any(0 < px[3] < 255 for row in grid for px in row):
        out.append("partial transparency; the player may show it as solid or not at all")
    return out


def render(spec: dict) -> Rendered:
    grid = pixels(spec)
    png = encode_png(grid)
    if problems := check_png(png):  # belt and braces: our own encoder must meet Yoto's rule
        raise SpecError("; ".join(problems))
    sha = hashlib.sha256(png).hexdigest()
    clean = {"rows": spec["rows"], "palette": spec.get("palette") or {}}
    out = Rendered(name=spec.get("name") or sha[:8], png=png, sha256=sha, spec=clean, lint=lint(grid))
    cache_dir = paths.icons()
    (cache_dir / f"{sha}.png").write_bytes(png)
    (cache_dir / f"{sha}.json").write_text(json.dumps({"name": out.name, "spec": clean, "lint": out.lint}))
    return out


def cached(sha256: str) -> tuple[bytes, dict] | None:
    png = paths.icons() / f"{sha256}.png"
    meta = paths.icons() / f"{sha256}.json"
    if not png.exists():
        return None
    return png.read_bytes(), (json.loads(meta.read_text()) if meta.exists() else {})


# ------------------------------------------------------------------ preview


def contact_sheet(items: list[tuple[str, bytes]], scale: int = 8) -> bytes:
    """Each icon at ``scale``×, on black (as the player shows it) and on a checkerboard."""
    cell = SIZE * scale
    pad, label_h = 12, 18
    width = pad + len(items) * (2 * cell + 3 * pad)
    height = pad + cell + label_h + pad
    sheet = Image.new("RGB", (max(width, 160), height), (40, 40, 40))
    draw = ImageDraw.Draw(sheet)
    x = pad
    for name, png in items:
        icon = Image.open(io.BytesIO(png)).convert("RGBA").resize((cell, cell), Image.Resampling.NEAREST)
        black = Image.new("RGBA", (cell, cell), (0, 0, 0, 255))
        black.alpha_composite(icon)
        checker = Image.new("RGBA", (cell, cell), (200, 200, 200, 255))
        cd = ImageDraw.Draw(checker)
        for cy in range(0, cell, scale):
            for cx in range(0, cell, scale):
                if (cx // scale + cy // scale) % 2:
                    cd.rectangle([cx, cy, cx + scale - 1, cy + scale - 1], fill=(150, 150, 150, 255))
        checker.alpha_composite(icon)
        sheet.paste(black.convert("RGB"), (x, pad))
        sheet.paste(checker.convert("RGB"), (x + cell + pad, pad))
        draw.text((x, pad + cell + 4), name[: 2 * cell // 7], fill=(230, 230, 230))
        x += 2 * cell + 3 * pad
    buf = io.BytesIO()
    sheet.save(buf, format="PNG")
    return buf.getvalue()


# ------------------------------------------------------------------ glyphs

# 3×5 bitmap font: digits, capitals and a little punctuation.
FONT = {
    "0": ["###", "#.#", "#.#", "#.#", "###"],
    "1": [".#.", "##.", ".#.", ".#.", "###"],
    "2": ["###", "..#", "###", "#..", "###"],
    "3": ["###", "..#", ".##", "..#", "###"],
    "4": ["#.#", "#.#", "###", "..#", "..#"],
    "5": ["###", "#..", "###", "..#", "###"],
    "6": ["###", "#..", "###", "#.#", "###"],
    "7": ["###", "..#", ".#.", ".#.", ".#."],
    "8": ["###", "#.#", "###", "#.#", "###"],
    "9": ["###", "#.#", "###", "..#", "###"],
    "A": [".#.", "#.#", "###", "#.#", "#.#"],
    "B": ["##.", "#.#", "##.", "#.#", "##."],
    "C": [".##", "#..", "#..", "#..", ".##"],
    "D": ["##.", "#.#", "#.#", "#.#", "##."],
    "E": ["###", "#..", "##.", "#..", "###"],
    "F": ["###", "#..", "##.", "#..", "#.."],
    "G": [".##", "#..", "#.#", "#.#", ".##"],
    "H": ["#.#", "#.#", "###", "#.#", "#.#"],
    "I": ["###", ".#.", ".#.", ".#.", "###"],
    "J": ["..#", "..#", "..#", "#.#", ".#."],
    "K": ["#.#", "#.#", "##.", "#.#", "#.#"],
    "L": ["#..", "#..", "#..", "#..", "###"],
    "M": ["#.#", "###", "###", "#.#", "#.#"],
    "N": ["##.", "#.#", "#.#", "#.#", "#.#"],
    "O": [".#.", "#.#", "#.#", "#.#", ".#."],
    "P": ["##.", "#.#", "##.", "#..", "#.."],
    "Q": [".#.", "#.#", "#.#", "##.", ".##"],
    "R": ["##.", "#.#", "##.", "#.#", "#.#"],
    "S": [".##", "#..", ".#.", "..#", "##."],
    "T": ["###", ".#.", ".#.", ".#.", ".#."],
    "U": ["#.#", "#.#", "#.#", "#.#", "###"],
    "V": ["#.#", "#.#", "#.#", "#.#", ".#."],
    "W": ["#.#", "#.#", "###", "###", "#.#"],
    "X": ["#.#", "#.#", ".#.", "#.#", "#.#"],
    "Y": ["#.#", "#.#", ".#.", ".#.", ".#."],
    "Z": ["###", "..#", ".#.", "#..", "###"],
    "?": ["###", "..#", ".##", "...", ".#."],
    "!": [".#.", ".#.", ".#.", "...", ".#."],
    "+": ["...", ".#.", "###", ".#.", "..."],
    "-": ["...", "...", "###", "...", "..."],
}

# 7×7 symbols, drawn at 2× (14×14).
SYMBOLS = {
    "★": ["...#...", "...#...", "#######", ".#####.", "..###..", ".##.##.", "##...##"],
    "♥": [".##.##.", "#######", "#######", "#######", ".#####.", "..###..", "...#..."],
    "♪": ["...####", "...#..#", "...#..#", "...#..#", ".###.##", "####.##", ".##...."],
    "☾": ["..###..", ".##....", "##.....", "##.....", "##.....", ".##....", "..###.."],
    "☀": ["#..#..#", ".#...#.", "..###..", "#######", "..###..", ".#...#.", "#..#..#"],
}


def _blit(canvas: list[list[str]], bitmap: list[str], x0: int, y0: int, xs: int, ys: list[int]) -> None:
    """Draw ``bitmap`` with each column ``xs`` px wide and row ``i`` ``ys[i]`` px tall."""
    y = y0
    for row, h in zip(bitmap, ys, strict=True):
        for x, ch in enumerate(row):
            if ch == "#":
                for dy in range(h):
                    for dx in range(xs):
                        canvas[y + dy][x0 + x * xs + dx] = "#"
        y += h


def glyph(text: str, colour: str = "#ffffff", outline: str | None = None, name: str | None = None) -> dict:
    """A centred spec for 1–2 characters (digits, letters, ? ! + -) or one symbol (★ ♥ ♪ ☾ ☀)."""
    text = text.upper() if text not in SYMBOLS else text
    if not 1 <= len(text) <= 2:
        raise SpecError("glyph takes 1 or 2 characters.")
    if text in SYMBOLS:
        bitmaps, scale, gap = [SYMBOLS[text]], 2, 0
        ys = [2] * 7
    else:
        missing = [c for c in text if c not in FONT]
        if missing:
            raise SpecError(
                f"No glyph for {''.join(missing)!r}. Known: digits, A–Z, ? ! + - and {' '.join(SYMBOLS)}."
            )
        bitmaps = [FONT[c] for c in text]
        # One character is 9×14 (rows 3,3,2,3,3 px, leaving a 1 px margin); two at 2× are 6×10 each
        # with a 2 px gap. An outline needs a pixel more all round, so it uses 2× too.
        big = len(text) == 1 and not outline
        scale, ys = (3, [3, 3, 2, 3, 3]) if big else (2, [2] * 5)
        gap = 2
    w = sum(len(b[0]) * scale for b in bitmaps) + gap * (len(bitmaps) - 1)
    h = sum(ys)
    canvas = [["." for _ in range(SIZE)] for _ in range(SIZE)]
    x0, y0 = (SIZE - w) // 2, (SIZE - h) // 2
    x = x0
    for b in bitmaps:
        _blit(canvas, b, x, y0, scale, ys)
        x += len(b[0]) * scale + gap
    palette = {"#": colour}
    if outline:
        palette["o"] = outline
        fill = {(y, x) for y in range(SIZE) for x in range(SIZE) if canvas[y][x] == "#"}
        for y, x in fill:
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < SIZE and 0 <= nx < SIZE and canvas[ny][nx] == ".":
                        canvas[ny][nx] = "o"
    return {"name": name or f"glyph {text}", "rows": ["".join(r) for r in canvas], "palette": palette}


# ------------------------------------------------------------------ from an image

SPEC_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"


def from_image(path: str, max_colours: int = 6, alpha_threshold: int = 128, name: str | None = None) -> dict:
    """A starting-point spec: fit the image in 16×16, quantize it, and cut alpha at a threshold."""
    img = Image.open(path).convert("RGBA")
    img.thumbnail((SIZE, SIZE), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (SIZE, SIZE), TRANSPARENT)
    canvas.paste(img, ((SIZE - img.width) // 2, (SIZE - img.height) // 2))
    rgb = canvas.convert("RGB").quantize(
        colors=max(1, min(max_colours, len(SPEC_CHARS))), method=Image.Quantize.MEDIANCUT
    )
    pal = rgb.getpalette() or []
    alpha = canvas.getchannel("A")
    used: dict[int, str] = {}
    rows = []
    for y in range(SIZE):
        row = ""
        for x in range(SIZE):
            if alpha.getpixel((x, y)) < alpha_threshold:
                row += "."
                continue
            idx = rgb.getpixel((x, y))
            if idx not in used:
                used[idx] = SPEC_CHARS[len(used)]
            row += used[idx]
        rows.append(row)
    palette = {ch: "#{:02x}{:02x}{:02x}".format(*pal[3 * i : 3 * i + 3]) for i, ch in used.items()}
    return {"name": name or "from image", "rows": rows, "palette": palette}
