"""font.py: the proportional 1 bpp font in fonts/caption.txt (format in its header) and a line renderer.

    python -X utf8 tools/font.py "Some text" [OUT.png]   # width in px (and a 4x PNG of the line)
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROWS = 13  # 0-9 cap height, 10-12 descender
TOP = 2  # first pixel row of a glyph inside a 16 px text line


def load(path=ROOT / "fonts" / "caption.txt"):
    """{char: list of ROWS strings of '#'/'.'}"""
    glyphs, cur = {}, None
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.startswith("# ") or not line:  # glyph rows never hold a space
            continue
        if line.startswith("== "):
            name = line[3:]
            cur = glyphs.setdefault(" " if name == "space" else name, [])
            assert len(name) == 1 or name == "space", f"{path.name}:{n}: bad glyph name {name!r}"
            continue
        assert cur is not None and set(line) <= {"#", "."}, f"{path.name}:{n}: bad row {line!r}"
        cur.append(line)
    for ch, rows in glyphs.items():
        assert 0 < len(rows) <= ROWS and len({len(r) for r in rows}) == 1, f"glyph {ch!r}: ragged or too tall"
        rows += ["." * len(rows[0])] * (ROWS - len(rows))
    return glyphs


GLYPHS = load()


def width(text, glyphs=GLYPHS):
    """Advance width in px (no trailing gap after the last glyph)."""
    missing = [c for c in text if c not in glyphs]
    if missing:
        raise ValueError(f"no glyph for {missing[0]!r} in {text!r}")
    return max(0, sum(len(glyphs[c][0]) + 1 for c in text) - 1)


def render(text, x0=0, w=None, glyphs=GLYPHS):
    """16 rows x w px (default: just wide enough) of 0/1, text starting at pixel x0."""
    w = w if w is not None else x0 + width(text, glyphs)
    img = [[0] * w for _ in range(16)]
    x = x0
    for c in text:
        rows = glyphs[c]
        for y, row in enumerate(rows):
            for dx, p in enumerate(row):
                if p == "#":
                    if x + dx >= w:
                        raise ValueError(f"{text!r} runs past {w} px")
                    img[TOP + y][x + dx] = 1
        x += len(rows[0]) + 1
    return img


if __name__ == "__main__":
    text = sys.argv[1] if len(sys.argv) > 1 else "".join(sorted(GLYPHS))
    print(f"{width(text)} px: {text!r}")
    if len(sys.argv) > 2:
        from PIL import Image
        img = render(text, 2, width(text) + 4)
        im = Image.new("L", (len(img[0]), 16))
        im.putdata([255 * p for row in img for p in row])
        im.resize((im.width * 4, 64), Image.NEAREST).save(sys.argv[2])
