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
