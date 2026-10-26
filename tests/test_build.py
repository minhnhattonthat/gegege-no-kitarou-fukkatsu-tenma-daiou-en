import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import archive  # noqa: E402
import build  # noqa: E402
import lzh  # noqa: E402

ROM = ROOT / "rom" / "kitarou.sfc"
needs_rom = pytest.mark.skipif(not ROM.is_file(), reason="no ROM dump in rom/")


@needs_rom
def test_identity():
    rom = ROM.read_bytes()
    assert build.build(rom) == rom


@needs_rom
def test_repack_every_category_in_place():
    """Repacking every category from its own blocks gives the original bytes (directory writer is exact)."""
    rom = ROM.read_bytes()
    edits = {(c, i): rom[off:off + size] for c, i, off, size in archive.blocks(rom)}
    assert build.build(rom, edits) == rom


@needs_rom
def test_grown_category_moves_to_expansion():
    """Our compressor is a few % larger, so recompressed category $20 must move past 1 MiB and still decode."""
    rom = ROM.read_bytes()
    cat20 = {c: bl for c, d, bl in archive.categories(rom)}[0x20]
    want = [archive.unpack(rom, off, size)[0] for i, off, size in cat20]
    out = build.build(rom, {(0x20, i): lzh.compress(w) for i, w in enumerate(want)})
    assert len(out) == build.SIZE_2M and out[0x7FD7] == 0x0B
    cats = {c: (d, bl) for c, d, bl in archive.categories(out)}
    d, bl = cats[0x20]
    assert d == build.EXPAND
    assert [archive.unpack(out, off, size)[0] for i, off, size in bl] == want
    # inside the old 1 MiB only the table entry, the header size byte and the checksum change
    allowed = {0x7FD7, 0x7FDC, 0x7FDD, 0x7FDE, 0x7FDF, 0x28080, 0x28081, 0x28082}
    assert {i for i in range(0x100000) if out[i] != rom[i]} <= allowed


@needs_rom
def test_hook_swallows_no_branch_target():
    """No branch/jump within 4 KB of a code hook lands strictly inside the bytes the hook overwrote (byte scan, no
    flow analysis, so it errs on the side of failing)."""
    import insert
    rom = ROM.read_bytes()
    for site, orig, _ in [insert.HOOK_SITE]:
        lo, hi = site + 1, site + len(orig)
        for p in range(site - 0x1000, site + 0x1000):
            op = rom[p]
            if op in (0x10, 0x30, 0x50, 0x70, 0x80, 0x90, 0xB0, 0xD0, 0xF0):
                t = p + 2 + ((rom[p + 1] ^ 0x80) - 0x80)
            elif op in (0x4C, 0x20, 0x5C, 0x22):
                t = (p & ~0x7FFF) | ((rom[p + 1] | rom[p + 2] << 8) & 0x7FFF)
            else:
                continue
            assert not lo <= t < hi, f"{p:#x} jumps to {t:#x}, inside the hook at {site:#x}"


@needs_rom
def test_no_stale_strip_immediates():
    """Every `LDA #ptr : STA $44 : LDA #$nnDD` that points into the banner/dialogue strips (raw 01_000/01_001) is
    a pair some patched strip record also holds: a missed copy draws the new tiles through the old-width map."""
    import re
    import insert
    rom = ROM.read_bytes()
    out = build.build(rom, *insert.edits(rom, "en"))
    recs = {out[o:o + 4] for o in range(0x8000, 0x18000) if out[o + 2] == 0xDD and 0xAC3A <= out[o] | out[o + 1] << 8 < 0xEFFA}
    for m in re.finditer(rb"\xA9(..)\x85\x44\xA9(\xDD.)", out[:0x100000], re.S):
        if 0xAC3A <= int.from_bytes(m[1], "little") < 0xEFFA:
            assert m[1] + m[2] in recs, f"{m.start():#x}: strip {m[1].hex()} {m[2].hex()} matches no record"


@needs_rom
@pytest.mark.parametrize("mode", ["en", "marker"])
def test_writes_romdiff_clean(mode):
    """romdiff gate: every changed byte is a logged write over the original bytes it expected, none overlap."""
    import insert
    rom = ROM.read_bytes()
    log = []
    out = build.build(rom, *insert.edits(rom, mode), log=log)
    assert build.verify(rom, out, log) == []
