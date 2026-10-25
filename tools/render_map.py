"""render_map.py: draw an archive tilemap block with its font block (2bpp) as a PNG, greyscale.

Map blocks start with a 4-byte header (byte 0-1: VRAM word address hint, 2-3: byte count); entries are SNES BG words.
    python -X utf8 tools/render_map.py FONT.bin MAP.bin OUT.png [--tile-base N] [--rows R] [--zoom 2]
"""
import argparse
import struct
import zlib


def tile_px(font, t):
    o = t * 16
    rows = []
    for y in range(8):
        lo, hi = (font[o + 2 * y], font[o + 2 * y + 1]) if o + 16 <= len(font) else (0, 0)
        rows.append([((lo >> (7 - x)) & 1) | (((hi >> (7 - x)) & 1) << 1) for x in range(8)])
    return rows


def render(font, mapdata, tile_base=0, width=32):
    words = [mapdata[i] | mapdata[i + 1] << 8 for i in range(0, len(mapdata) - 1, 2)]
    h = (len(words) + width - 1) // width
    img = [[0] * (width * 8) for _ in range(h * 8)]
    for i, w in enumerate(words):
        t = (w & 0x3FF) - tile_base
        if t < 0:
            continue
        px = tile_px(font, t)
        hf, vf = w & 0x4000, w & 0x8000
        cx, cy = (i % width) * 8, (i // width) * 8
        for y in range(8):
            for x in range(8):
                v = px[7 - y if vf else y][7 - x if hf else x]
                img[cy + y][cx + x] = v
    return img


def write_png(path, img, zoom=2):
    pal = [0, 255, 170, 85]
    h, w = len(img) * zoom, len(img[0]) * zoom
    raw = bytearray()
    for row in img:
        line = bytes(pal[v] for v in row for _ in range(zoom))
        for _ in range(zoom):
            raw += b"\0" + line
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d))
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw))) + chunk(b"IEND", b"")
    open(path, "wb").write(png)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("font")
    ap.add_argument("map")
    ap.add_argument("out")
    ap.add_argument("--tile-base", type=lambda s: int(s, 0), default=0)
    ap.add_argument("--skip", type=int, default=4, help="header bytes before the map")
    ap.add_argument("--zoom", type=int, default=2)
    a = ap.parse_args()
    font = open(a.font, "rb").read()
    m = open(a.map, "rb").read()[a.skip:]
    write_png(a.out, render(font, m, a.tile_base), a.zoom)
