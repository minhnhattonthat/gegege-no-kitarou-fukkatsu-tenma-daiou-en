import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import archive  # noqa: E402
import build  # noqa: E402
import extract  # noqa: E402
import font  # noqa: E402
import insert  # noqa: E402

ROM = ROOT / "rom" / "kitarou.sfc"
needs_rom = pytest.mark.skipif(not ROM.is_file(), reason="no ROM dump in rom/")


def reveal(words, w=32):
    """Cells the caption reveal ($80:EE02) copies to the screen, walking the map like the game does."""
    shown, i = set(), 0
    while True:
        while words[i] & 0x3FF == 0:
            i += 1
        t = words[i] & 0x3FF
        if t == 0x2E0:
            i = i // w * w + 2 * w
        elif t > 0x2E0:
            return shown
        else:
            step = 1 if t >= 0x2C0 else 2
            shown |= {i + d for d in range(step)} | {i + w + d for d in range(step)}
            i += step
            if i % w == 0:
                i += w


def check_page(words):
    shown = reveal(words)
    drawn = {i for i, x in enumerate(words) if x & 0x3FF and x & 0x3FF not in (0x2E0, 0x2E1, 0x2F0, 0x2F1)}
    assert drawn <= shown, f"cells never revealed: {sorted(drawn - shown)}"
    assert all(words[i] & 0x3FF < 0x2E0 for i in shown), "a code cell got revealed"


@needs_rom
def test_reveal_model_on_japanese_pages():
    """The model reveals every Japanese glyph cell (page 10's blank-topped comma is the game's own quirk)."""
    rom = ROM.read_bytes()
    for n in range(3, 66):
        words = extract.split_map(extract.block(rom, 0x20, n))[2]
        if n == 10:
            words = [x if x != 0x2D1 else 0 for x in words]
        check_page(words)


@pytest.fixture(scope="module", params=["marker", "ruler"])
def built(request):
    rom = ROM.read_bytes()
    ed, patches = insert.edits(rom, request.param)
    return request.param, build.build(rom, ed, patches)


@needs_rom
def test_every_built_page_reveals_fully(built):
    mode, out = built
    table = out[insert.TABLE:insert.TABLE + 66]
    assert out[0x13857:0x1385D] == insert.HOOK_SITE[2] and out[0x1FFF00:0x1FFF1E] == insert.HOOK[2]
    for n in range(3, 66):
        assert insert.FIRST_SHEET <= table[n] <= insert.LAST_SHEET
        words = extract.split_map(extract.block(out, 0x20, n))[2]
        check_page(words)
        sheet = extract.block(out, 0x20, table[n])
        assert len(sheet) == insert.SHEET_BYTES
        assert max(x & 0x3FF for x in words if x & 0x3FF < 0x2E0) < len(sheet.rstrip(b"\0")) // 16 + 2


def test_font_covers_marker_text():
    assert font.width(insert.FILLER + "“”[]_0123456789|") > 0
    lines = insert.wrap("“" + "word " * 60 + "end”", insert.MAX_PX["captions"], 5)
    assert all(font.width(t) <= insert.MAX_PX["captions"] - (5 if k else 0) for k, t in enumerate(lines))
