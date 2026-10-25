"""archive.py: the game's resource archive at $85:8000 (file 0x28000). Format in docs/re/compression.md.

Category table: 40 x 4 bytes, each a 24-bit LE offset from 0x28000 to the category directory (+1 pad byte).
Directory: word 0 = offset from the directory to its first block (= directory size); then one 16-bit size per
block. Blocks follow back to back, each an LZ+Huffman stream (tools/lzh.py).

    python -X utf8 tools/archive.py list            # every block: cat, idx, file offset, packed and unpacked size
    python -X utf8 tools/archive.py dump OUTDIR     # decompress every block to OUTDIR/cc_iii.bin
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lzh  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BASE = 0x28000
NCAT = 40


def off_to_snes(off):
    return 0x800000 | ((off >> 15) << 16) | 0x8000 | (off & 0x7FFF)


def categories(rom):
    """[(cat, dir_off, [(idx, file_off, packed_size)])]."""
    out = []
    for c in range(NCAT):
        e = rom[BASE + 4 * c: BASE + 4 * c + 4]
        d = BASE + (e[0] | e[1] << 8 | e[2] << 16)
        first = rom[d] | rom[d + 1] << 8
        sizes = [rom[d + i] | rom[d + i + 1] << 8 for i in range(2, first, 2)]
        blocks, p = [], d + first
        for i, s in enumerate(sizes):
            blocks.append((i, p, s))
            p += s
        out.append((c, d, blocks))
    return out


def blocks(rom):
    for c, d, bl in categories(rom):
        for i, off, size in bl:
            yield c, i, off, size


def unpack(rom, off, size):
    """(data, used) for a packed block, or None when it isn't a valid stream within its size (raw data)."""
    if size < 3:
        return None
    try:
        data, end = lzh.decompress(rom, off_to_snes(off))
    except (IndexError, ValueError):
        return None
    used = lzh.lorom(end) - off
    return (data, used) if used <= size else None


def main():
    rom = (ROOT / "rom" / "kitarou.sfc").read_bytes()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    if cmd == "list":
        for c, i, off, size in blocks(rom):
            u = unpack(rom, off, size)
            if u:
                print(f"{c:02X} {i:03d} {off:06X} {off_to_snes(off):06X} packed {size:5d} used {u[1]:5d} -> {len(u[0]):5d}")
            else:
                print(f"{c:02X} {i:03d} {off:06X} {off_to_snes(off):06X} raw    {size:5d}")
    elif cmd == "dump":
        outdir = Path(sys.argv[2])
        outdir.mkdir(parents=True, exist_ok=True)
        for c, i, off, size in blocks(rom):
            u = unpack(rom, off, size)
            (outdir / f"{c:02X}_{i:03d}.bin").write_bytes(u[0] if u else rom[off:off + size])
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
