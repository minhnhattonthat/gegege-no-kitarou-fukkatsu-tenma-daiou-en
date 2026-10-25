"""sweep.py: static graphics-text sweep. Renders every archive block as tiles into numbered pages for reading.

Each block is drawn 32 tiles wide (greyscale by index) under a white separator row; a block whose size isn't a
multiple of 16 bytes is skipped and listed. Pages are ~1000 px tall; page_index.txt says which block sits where.
    python -X utf8 tools/sweep.py OUTDIR [--bpp 4] [--cats 01,02,...]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import archive  # noqa: E402
import render_map  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def tile(data, t, bpp):
    tb = 8 * bpp
    o = t * tb
    rows = []
    for y in range(8):
        planes = [data[o + 2 * y], data[o + 2 * y + 1]]
        if bpp == 4:
            planes += [data[o + 16 + 2 * y], data[o + 17 + 2 * y]]
        rows.append([sum(((p >> (7 - x)) & 1) << i for i, p in enumerate(planes)) for x in range(8)])
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--bpp", type=int, default=4)
    ap.add_argument("--cats")
    ap.add_argument("--max-tiles", type=int, default=1024)
    ap.add_argument("--page-h", type=int, default=1000)
    ap.add_argument("--zoom", type=int, default=1)
    ap.add_argument("--linear", action="store_true", help="render packed blocks as 128-px linear 4bpp images")
    a = ap.parse_args()
    rom = (ROOT / "rom" / "kitarou.sfc").read_bytes()
    cats = {int(c, 16) for c in a.cats.split(",")} if a.cats else None
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    scale = 255 // ((1 << a.bpp) - 1)
    page, rows, index, skipped, n = [], [], [], [], 0

    def flush():
        nonlocal page, n
        if page:
            img = [[min(255, v * scale) // 85 if False else v for v in r] for r in page]
            write(out / f"page_{n:03d}.png", img)
            n += 1
            page = []

    def write(path, img):
        import struct, zlib
        z = a.zoom
        h, w = len(img) * z, 256 * z
        raw = bytearray()
        for r in img:
            line = bytes(min(255, v) for v in r for _ in range(z))
            raw += (b"\0" + line) * z
        def chunk(t, d):
            return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d))
        png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0))
        png += chunk(b"IDAT", zlib.compress(bytes(raw))) + chunk(b"IEND", b"")
        path.write_bytes(png)

    tb = 8 * a.bpp
    for c, i, off, size in archive.blocks(rom):
        if cats is not None and c not in cats:
            continue
        u = archive.unpack(rom, off, size)
        data = u[0] if u else rom[off:off + size]
        if a.linear:  # packed-pixel 4bpp, 128 px wide, high nibble first ($82:A238 converts it to planar)
            if not u or len(data) < 512:
                continue
            rows = len(data) // 64
            if page and len(page) + rows + 2 > a.page_h:
                flush()
            index.append(f"page_{n:03d} y={len(page) + 2} {c:02X}_{i:03d} linear {len(data)} bytes")
            page += [[255] * 256, [0] * 256]
            for r in range(rows):
                line = data[r * 64:(r + 1) * 64]
                page.append([v * 17 for b in line for v in (b >> 4, b & 15)] + [0] * 128)
            continue
        if len(data) < tb or len(data) % 16:
            skipped.append(f"{c:02X}_{i:03d} {len(data)} bytes")
            continue
        nt = min(len(data) // tb, a.max_tiles)
        h = (nt + 31) // 32 * 8
        if page and len(page) + h + 2 > a.page_h:
            flush()
        index.append(f"page_{n:03d} y={len(page) + 2} {c:02X}_{i:03d} {'packed' if u else 'raw'} {len(data)} bytes")
        page.append([255] * 256)
        page.append([0] * 256)
        block = [[0] * 256 for _ in range(h)]
        for t in range(nt):
            px = tile(data, t, a.bpp)
            for y in range(8):
                for x in range(8):
                    block[(t // 32) * 8 + y][(t % 32) * 8 + x] = px[y][x] * scale
        page += block
    flush()
    (out / "page_index.txt").write_text("\n".join(index + ["", "skipped:"] + skipped) + "\n", encoding="utf-8")
    print(f"{n} pages -> {out}")


if __name__ == "__main__":
    main()
