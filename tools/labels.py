"""labels.py: redraw the graphics text of script/labels.json (`en`) into its blocks. insert.edits() calls edits().

Survey and block formats: docs/re/graphics.md. Each element is one function returning raw blocks and code patches.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract  # noqa: E402
import font  # noqa: E402
from insert import Sheet, tile_bytes  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def labels():
    return {e["id"]: e["en"] for e in json.loads((ROOT / "script" / "labels.json").read_text(encoding="utf-8"))}


def scale(img, k):
    return [[p for p in row for _ in range(k)] for row in img for _ in range(k)]


def canvas(w, h):
    return [[0] * w for _ in range(h)]


def blit(dst, src, x, y):
    for dy, row in enumerate(src):
        for dx, p in enumerate(row):
            if p:
                dst[y + dy][x + dx] = p


def place(sheet, words, w, img, row, col):
    """Every 8x8 cell of a 0/1 bitmap into `sheet`, its ids into map `words` (width w) at row/col."""
    for cy in range(len(img) // 8):
        for cx in range(len(img[0]) // 8):
            words[(row + cy) * w + col + cx] = sheet.attr | sheet.id(tile_bytes(img, cx, cy))


# G3 chapter cards: 20_066 sheet -> VRAM $5000 (BG3 chars; the BG3 map sits at $5C00, so up to 384 tiles), size in
# the DMA list entry at $81:C907; 20_067 map, card k = 4 rows from $7E:E804 + k * stride, each row DMA'd to $5C83+
# by $82:BB07. The card is widened from 12 to CARD_W tiles.
CARD_W = 18
CARD_TILES = 0x180
CARD_PATCHES = [  # (file offset, original bytes, new bytes)
    (0xC907, bytes.fromhex("9009"), None),  # DMA size of 20_066, set from the sheet
    (0x13B1F, bytes.fromhex("6000"), (CARD_W * 8).to_bytes(2, "little")),  # ADC #stride: one card = 4 rows
    (0x13B50, bytes.fromhex("1800"), (CARD_W * 2).to_bytes(2, "little")),  # LDY #bytes per row
    (0x13B6C, bytes.fromhex("1800"), (CARD_W * 2).to_bytes(2, "little")),  # ADC #next row
]


def cards(en, rom):
    sheet = Sheet(CARD_TILES, blank=0)
    words = [0] * (CARD_W * 28)
    for k in range(7):
        (text,) = en[f"G3.{k}"]
        img = canvas(CARD_W * 8, 32)
        assert 8 + 2 * font.width(text) <= CARD_W * 8, f"card {k}: {text!r} too wide"
        blit(img, scale(font.render(text), 2)[2:], 8, 4)  # 2x caption font, cap height rows 4-23
        place(sheet, words, CARD_W, img, 4 * k, 0)
    data = b"".join(sheet.tiles)
    patches = [(off, orig, new if new is not None else len(data).to_bytes(2, "little")) for off, orig, new in CARD_PATCHES]
    return {(0x20, 66): data, (0x20, 67): extract.join_map(CARD_W, 28, words)}, patches


def shadowed(img, ink, shade):
    """0/1 bitmap -> colour indices: `ink`, with a `shade` drop shadow 1 px right and down (the game's sprite text)."""
    h, w = len(img), len(img[0])
    out = [[ink if p else 0 for p in row] for row in img]
    for y in range(h):
        for x in range(w):
            if img[y][x]:
                for dx, dy in ((1, 0), (0, 1), (1, 1)):
                    if x + dx < w and y + dy < h and not img[y + dy][x + dx]:
                        out[y + dy][x + dx] = shade
    return out


def tile4(img, cx, cy):
    """SNES 4bpp tile of the 8x8 cell (cx, cy) of a colour-index image."""
    rows = [img[cy * 8 + y][cx * 8:cx * 8 + 8] for y in range(8)]
    plane = lambda p, r: sum(((v >> p) & 1) << (7 - x) for x, v in enumerate(r))  # noqa: E731
    return bytes(b for r in rows for b in (plane(0, r), plane(1, r))) + \
        bytes(b for r in rows for b in (plane(2, r), plane(3, r)))


# G11 game over: sprites. Raw 01_002 (60 4bpp tiles) is DMA'd to VRAM $4C00 = OBJ tiles $C0-$FF; 16x16 sprites,
# palette 7 (colour 2 white ink, 14 shadow). Meta-sprite records at $83:99DC (5 bytes: tile - $C0, attr, dy, dx,
# flags = extra sprites to the right (tile + 2, dx + 16 each) | $80 last record of the group); origin (128, 112).
# Groups: title (5 records at 0x199DC), the two options (6 at 0x199F5), cursor (0x19A13, kept).
GO_CELLS = [0x00, 0x02, 0x04, 0x06, 0x08, 0x0A, 0x0C, 0x0E, 0x20, 0x22, 0x24, 0x26]  # $E8/$EA = cursor
GO_TITLE, GO_OPTS = (0x199DC, 5), (0x199F5, 6)


def gameover(en, rom):
    title, yes, no = en["G11"]
    no_head, no_tail = no.rsplit(" ", 1)
    assert no_tail == yes, f"G11: {no!r} must end in {yes!r} (the two share sprites)"
    data = bytearray(rom[0x2EFFA:0x2EFFA + 1920])
    cells = iter(GO_CELLS)

    def strip(text, w, x0):
        """Sprite cells (relative tile numbers) of `text` drawn at x0 in a w px strip."""
        assert x0 + font.width(text) <= w, f"G11: {text!r} too wide"
        img = shadowed(font.render(text, x0, w), 2, 14)
        out = []
        for k in range(w // 16):
            t = next(cells)
            for cy in range(2):
                for cx in range(2):
                    o = (t + cy * 16 + cx) * 32
                    data[o:o + 32] = tile4(img, 2 * k + cx, cy)
            out.append(t)
        return out

    def rec(tile, dy, dx, last=False):
        return bytes([tile, 0x38, dy & 255, dx & 255, 0x80 if last else 0])

    t = strip(title, 80, (80 - font.width(title)) // 2)
    head = strip(no_head, 32, 32 - 4 - font.width(no_head))  # right-aligned: one space before the shared word
    word = strip(yes, 32, 0)
    title_recs = b"".join(rec(c, -48, -40 + 16 * k, k == 4) for k, c in enumerate(t))
    opt_recs = b"".join([rec(head[0], 8, -39), rec(head[1], 8, -23), rec(word[0], 8, -7), rec(word[1], 8, 9),
                         rec(word[0], -16, -39), rec(word[1], -16, -23, True)])
    patches = []
    for (off, n), recs in ((GO_TITLE, title_recs), (GO_OPTS, opt_recs)):
        assert len(recs) == 5 * n and rom[off + 5 * n - 1] & 0x80
        patches.append((off, rom[off:off + 5 * n], recs))
    return {(0x01, 2): bytes(data)}, patches


def bold(img):
    """Thicken a 0/1 bitmap by 1 px to the right (needs a blank last column)."""
    return [[p | (x > 0 and row[x - 1]) for x, p in enumerate(row)] for row in img]


# G10 boss banners: raw 01_000 ($85:AC3A), 2bpp colour 1. One banner = n 16x16 cells stored as the top row of 2n
# tiles, then the bottom row; it is DMA'd to VRAM $5008 (BG3 chars at $5000) when the boss appears. Each stage
# record in bank $82 holds the banner's address word, $DD, then n + $83. 6-1 (stage 17) has none.
BANNER_RECS = [0x10D09, 0x10D23, 0x10D3B, 0x10D51, 0x10D73, 0x10D95, 0x10DAF, 0x10DD1, 0x10DE7, 0x10DFD, 0x10E13,
               0x10E29, 0x10E3F, 0x10E55, 0x10E6F, 0x10E85, 0x10EA7, None, 0x10ED3]
BANNER_BASE, BANNER_SIZE = 0x2AC3A, 5120
KEEP_DRAWN = ("{alien",)  # alien-script banners keep their original tiles


def banners(en, rom):
    data, patches = bytearray(), []
    for stage, off in enumerate(BANNER_RECS):
        if off is None:
            continue
        ptr, n = rom[off] | rom[off + 1] << 8, (rom[off + 3] & 0x7F) - 3
        assert rom[off + 2] == 0xDD and 1 <= n
        (text,) = en[f"G10.{stage}"]
        if text.startswith(KEEP_DRAWN):
            src = BANNER_BASE + ptr - 0xAC3A
            cells = rom[src:src + 64 * n]
        else:
            n = -(-(font.width(text) + 2) // 16)
            img = canvas(16 * n, 16)
            blit(img, bold(font.render(text, 0, font.width(text) + 1)), (16 * n - font.width(text) - 1) // 2, 0)
            cells = b"".join(tile_bytes(img, cx, cy) for cy in range(2) for cx in range(2 * n))
        new = (0xAC3A + len(data)).to_bytes(2, "little") + bytes([0xDD, n + 0x83])
        patches.append((off, rom[off:off + 4], new))
        data += cells
    assert len(data) <= BANNER_SIZE, f"banners: {len(data)} bytes > {BANNER_SIZE}"
    return {(0x01, 0): bytes(data) + rom[BANNER_BASE + len(data):BANNER_BASE + BANNER_SIZE]}, patches


RAW = {(0x01, 0), (0x01, 2)}  # blocks the game reads uncompressed (DMA straight from ROM)


def edits(rom):
    """(blocks {(cat, idx): unpacked bytes}, patches [(off, orig, new)]); blocks in RAW are stored as they are."""
    en = labels()
    blocks, patches = {}, []
    for fn in (cards, gameover, banners):
        b, p = fn(en, rom)
        blocks.update(b)
        patches += p
    return blocks, patches
