"""build.py: rebuild the ROM from rom/kitarou.sfc plus edited archive blocks -> build/kitarou_en.sfc.

Untouched categories keep their original bytes and place. An edited category is repacked (directory + blocks back
to back); it stays in place when it fits, else it moves to the expansion area (ROM grows to 2 MiB, banks $A0-$BF)
and its category-table entry is rewritten. With no edits the output is byte-identical to the original (the identity
test in tests/test_build.py).

    python -X utf8 tools/build.py [OUT] [--marker | --ruler]   # text from tools/insert.py (en by default)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import archive  # noqa: E402
import bps  # noqa: E402
import check_rom  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
EXPAND = 0x100000  # first byte past the original 1 MiB = $A0:8000
SIZE_2M = 0x200000


def pack_category(blocks):
    """Directory (word 0 = its own size, then one size word per block) followed by the blocks."""
    head = 2 + 2 * len(blocks)
    out = bytearray(head.to_bytes(2, "little"))
    for b in blocks:
        assert len(b) <= 0xFFFF, "block too big for its 16-bit size"
        out += len(b).to_bytes(2, "little")
    for b in blocks:
        out += b
    return bytes(out)


def grow(out):
    if len(out) < SIZE_2M:
        out += b"\xff" * (SIZE_2M - len(out))
        out[0x7FD7] = 0x0B  # header ROM size: 2 MiB


def build(rom, edits=None, patches=()):
    """edits: {(cat, idx): stored block bytes (already compressed with lzh.compress, or raw)}; an idx past a
    category's last block appends blocks (the new indices must follow on without gaps).
    patches: (file offset, original bytes or None for expansion space, new bytes) code writes."""
    edits = edits or {}
    out = bytearray(rom)
    free = EXPAND
    code_lo = min((off for off, _, _ in patches if off >= EXPAND), default=SIZE_2M)
    for c, d, bl in archive.categories(rom):
        new = sorted(i for cc, i in edits if cc == c and i >= len(bl))
        assert new == list(range(len(bl), len(bl) + len(new))), f"category {c:02X}: appended blocks leave a gap"
        if not any((c, i) in edits for i, _, _ in bl) and not new:
            continue
        assert rom[d] | rom[d + 1] << 8 == 2 + 2 * len(bl), f"category {c:02X}: directory has extra bytes"
        old_len = bl[-1][1] + bl[-1][2] - d
        data = pack_category([edits.get((c, i), rom[off:off + size]) for i, off, size in bl] +
                             [edits[c, i] for i in new])
        if len(data) <= old_len:
            out[d:d + len(data)] = data  # leftover bytes past the last block are never read
            continue
        grow(out)
        assert free + len(data) <= code_lo, "expansion area full"
        out[free:free + len(data)] = data
        out[archive.BASE + 4 * c:archive.BASE + 4 * c + 3] = (free - archive.BASE).to_bytes(3, "little")
        free += len(data)
    for off, orig, new in patches:
        if off >= EXPAND:
            grow(out)
            assert out[off:off + len(new)] == b"\xff" * len(new), f"{off:#x}: expansion space already used"
        else:
            assert rom[off:off + len(orig)] == orig and len(orig) == len(new), f"{off:#x}: unexpected original bytes"
        out[off:off + len(new)] = new
    return bps.snes_checksum(out)[0]


def main():
    import insert
    check_rom.check()
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    mode = next((a[2:] for a in sys.argv[1:] if a.startswith("--")), "en")
    rom = (ROOT / "rom" / "kitarou.sfc").read_bytes()
    out = Path(args[0]) if args else ROOT / "build" / "kitarou_en.sfc"
    out.parent.mkdir(parents=True, exist_ok=True)
    data = build(rom, *insert.edits(rom, mode))
    out.write_bytes(data)
    print(f"{out}: {len(data):#x} bytes, {'identical to' if data == rom else 'differs from'} the original")


if __name__ == "__main__":
    main()
