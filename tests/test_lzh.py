import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import archive  # noqa: E402
import lzh  # noqa: E402

ROM = ROOT / "rom" / "kitarou.sfc"
needs_rom = pytest.mark.skipif(not ROM.is_file(), reason="no ROM dump in rom/")


def test_selftest():
    lzh._selftest()


@needs_rom
def test_category_20_roundtrip():
    """Every text block decodes inside its packed size and survives our compressor."""
    rom = ROM.read_bytes()
    cats = {c: bl for c, d, bl in archive.categories(rom)}
    assert len(cats[0x20]) == 68
    for i, off, size in cats[0x20]:
        data, used = archive.unpack(rom, off, size)
        assert used <= size
        c = lzh.compress(data)
        blob = bytearray(0x8000)
        blob[:len(c)] = c
        assert lzh.decompress(bytes(blob), 0x808000)[0] == data
