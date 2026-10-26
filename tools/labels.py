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


def tile2(img, cx, cy):
    """SNES 2bpp tile of the 8x8 cell (cx, cy) of a colour-index image (colours 0-3)."""
    out = bytearray()
    for y in range(8):
        r = img[cy * 8 + y][cx * 8:cx * 8 + 8]
        out += bytes([sum((v & 1) << (7 - x) for x, v in enumerate(r)), sum((v >> 1) << (7 - x) for x, v in enumerate(r))])
    return bytes(out)


# G7 options: 27_004 = 64-byte palette + 2bpp tiles, DMA'd from $7F:A040 to VRAM $6000 (BG3 chars; size word in
# the DMA list at 0x12651, room up to $7F:B000 where the 27_005 map is decompressed: 252 tiles). Map 27_005 32x32:
# label rows 8/11/14/17/20 (2 tile rows each), cols 6-24 get their palette toggled when the cursor moves ($82:A66B),
# so labels go in cols 6-18 and values in cols 19-24 (6 tiles). Value strings are copied from map rows 30-31:
# difficulty ($82:A9D6: Easy col 0, Normal col 6, Hard col 12), partner ($82:A9DC: Off col 24, On col 18). Digits
# for the stage / sound numbers come from ROM tables ($82:A9E0, $82:ABA8) and keep their tiles.
OPT_ROWS = [8, 11, 14, 17, 20]
OPT_VALUES = {"Easy": 0, "Normal": 6, "Hard": 12, "On": 18, "Off": 24}  # column in map rows 30-31
OPT_DMA = 0x12651
OPT_TILES = 252


def gradient(img):
    """0/1 text bitmap (16 rows) -> the options screen's colour bands: 1 above row 8, 2 to row 11, 3 below."""
    return [[(1 if y < 8 else 2 if y < 12 else 3) if p else 0 for p in row] for y, row in enumerate(img)]


def options(en, rom):
    sheet_raw = extract.block(rom, 0x27, 4)
    pal, tiles = sheet_raw[:64], [sheet_raw[64 + 16 * i:80 + 16 * i] for i in range((len(sheet_raw) - 64) // 16)]
    w, h, words = extract.split_map(extract.block(rom, 0x27, 5))
    text = {(r + dy, c) for r in OPT_ROWS for dy in (0, 1) for c in range(6, 25)} | \
        {(r, c) for r in (30, 31) for c in range(32)}
    keep = {words[r * w + c] & 0x3FF for r in range(h) for c in range(w) if (r, c) not in text}
    for base, n in ((0x129E0, 19 * 12), (0x12BA8, 10 * 4)):  # digit tables
        keep |= {(rom[base + 2 * i] | rom[base + 2 * i + 1] << 8) & 0x3FF for i in range(n)}
    free = iter(t for t in range(1, OPT_TILES) if t not in keep)
    tiles += [bytes(16)] * (OPT_TILES - len(tiles))
    ids = {}

    def put(img, row, col, attr):
        for cy in range(2):
            for cx in range(len(img[0]) // 8):
                data = tile2(img, cx, cy)
                if any(data) and data not in ids:
                    ids[data] = next(free)
                    tiles[ids[data]] = data
                words[(row + cy) * w + col + cx] = attr | ids.get(data, 0)

    def line(s, cols, x0=2):
        assert x0 + font.width(s) <= cols * 8, f"G7: {s!r} wider than {cols} tiles"
        img = [[0] * (cols * 8)] + font.render(s, x0, cols * 8)[:15]  # one row lower: cap height rows 3-12
        return gradient(img)

    labels_en, values_en = en["G7"][:5], en["G7"][5:]
    for row, s in zip(OPT_ROWS, labels_en):
        attr = next(words[row * w + c] & 0xFC00 for c in range(6, 19) if words[row * w + c] & 0x3FF)
        put(line(s, 13), row, 6, attr)
    order = dict(zip(["Hard", "Normal", "Easy", "On", "Off"], values_en))  # labels.json order: 難しい ふつう 易しい する しない
    for key, col in OPT_VALUES.items():
        put(line(order[key], 6, 0), 30, col, 0)
    for row, key in ((8, "Normal"), (20, "Off")):  # what the screen shows before any value changes
        for dy in (0, 1):
            for k in range(6):
                words[(row + dy) * w + 19 + k] = words[(30 + dy) * w + OPT_VALUES[key] + k]
    data = pal + b"".join(tiles)
    size = (len(data) - 64).to_bytes(2, "little")
    return {(0x27, 4): data, (0x27, 5): extract.join_map(w, h, words)}, [(OPT_DMA, rom[OPT_DMA:OPT_DMA + 2], size)]


# G9 staff roll: 24_002 sheet (2bpp, colour 1 text, 552 tiles: DMA list $81:CC3C copies 0x2280 bytes to VRAM
# $6000), 24_003 = 9 screens back to back, each [w, h] then w*h BG words, decompressed to $7E:E800. Each screen has
# a 20-byte record from 0xCB64 (stride 20): VRAM word address (BG map at $3C00, 32 wide), source address, bank,
# bytes per row, rows, source stride. Screens may grow and move; the INTERBEC logo cells stay put on screen.
STAFF_RECS = 0xCB64
STAFF_SHEET = 8832
# Per screen: (map row, x px, en line, part) - part 0/1 = before/after ": ", None = the whole line (wrapped to the
# box, continuation 2 rows down).
STAFF = [
    [(0, 0, 0, 0), (0, 56, 0, 1)],
    [(0, 0, 0, None), (4, 16, 1, None), (9, 0, 2, None), (12, 16, 3, None), (16, 16, 4, None), (20, 16, 5, None)],
    [(0, 0, 0, None), (4, 0, 1, 0), (4, 56, 1, 1), (8, 0, 2, 0), (8, 56, 2, 1), (12, 0, 3, None), (14, 56, 4, None),
     (18, 56, 5, None), (22, 56, 6, None)],
    [(0, 0, 0, None), (2, 16, 1, 0), (4, 32, 1, 1), (2, 128, 2, 0), (4, 144, 2, 1), (6, 16, 3, 0), (8, 32, 3, 1),
     (8, 144, 4, None)],
    [(0, 0, 0, None), (3, 24, 1, None), (3, 136, 2, None), (7, 24, 3, None), (7, 136, 4, None)],
    [(0, 0, 0, None), (4, 16, 1, None), (7, 16, 2, None), (10, 16, 3, None), (13, 16, 4, None), (16, 16, 5, None)],
    [(0, 0, 0, None), (3, 8, 1, None), (3, 136, 2, None), (6, 136, 3, None), (9, 136, 4, None)],
    [(0, 0, 0, None), (5, 16, 1, None), (9, 0, 2, None), (12, 16, 3, None)],  # line 4 = the logo, kept
    [(0, 24, 0, None)],
]
STAFF_MAXW = {7: 15}  # side panel beside the picture: wrap instead of growing
STAFF_LOGO_ROW = {7: 15}  # INTERBEC logo: rows 15-17 of screen 7, kept as drawn


def staff(en, rom):
    import insert
    old_sheet = extract.block(rom, 0x24, 2)
    raw = extract.block(rom, 0x24, 3)
    sheet = Sheet(STAFF_SHEET // 16, blank=0)
    out, patches, p = bytearray(), [], 0
    for k, layout in enumerate(STAFF):
        w0, h = raw[p] | raw[p + 1] << 8, raw[p + 2] | raw[p + 3] << 8
        words0 = [raw[p + 4 + 2 * i] | raw[p + 5 + 2 * i] << 8 for i in range(w0 * h)]
        p += 4 + 2 * w0 * h
        lines = en[f"G9.{k}"]
        items = []
        for row, x, li, part in layout:
            text = lines[li] if part is None else lines[li].split(": ", 1)[part]
            wmax = STAFF_MAXW.get(k, 32) * 8 - x
            for n, t in enumerate(insert.wrap(text, wmax) if font.width(text) > wmax else [text]):
                items.append((row + 2 * n, x, t))
        w = max(w0, max(-(-(x + font.width(t)) // 8) for _, x, t in items))
        rec = STAFF_RECS + 20 * k
        vram = rom[rec] | rom[rec + 1] << 8
        row0, col0 = divmod(vram - 0x3C00, 32)
        col = min(max(0, col0 - (w - w0) // 2), 32 - w)
        img = canvas(w * 8, h * 8)
        for row, x, t in items:
            assert row * 8 + 16 <= h * 8, f"G9.{k}: {t!r} below the box"
            blit(img, font.render(t), x, row * 8)
        words = [0] * (w * h)
        place(sheet, words, w, img, 0, 0)
        for i, wd in enumerate(words0):  # the logo: same tiles, same place on screen
            r, c = divmod(i, w0)
            if wd & 0x3FF and r >= STAFF_LOGO_ROW.get(k, h):
                t = wd & 0x3FF
                words[r * w + c + col0 - col] = (wd & 0xFC00) | sheet.id(old_sheet[16 * t:16 * t + 16])
        src = 0xE800 + len(out) + 4  # past the [w, h] header
        out += extract.join_map(w, h, words)
        new = (0x3C00 + row0 * 32 + col).to_bytes(2, "little") + src.to_bytes(2, "little") + bytes([0x7E, 2 * w, h, 2 * w])
        assert rom[rec + 4] == 0x7E and rom[rec + 5] == 2 * w0 and rom[rec + 6] == h
        patches.append((rec, rom[rec:rec + 8], new))
    # 24_003 grows into $7E:F86C+; nothing writes there during the staff roll (ramwrites probe on the ending, 2026-10-26)
    assert len(out) <= len(raw) + 0x200, f"staff maps: {len(out)} bytes"
    return {(0x24, 2): sheet.data(STAFF_SHEET), (0x24, 3): bytes(out)}, patches


RAW = {(0x01, 0), (0x01, 2)}  # blocks the game reads uncompressed (DMA straight from ROM)


def edits(rom):
    """(blocks {(cat, idx): unpacked bytes}, patches [(off, orig, new)]); blocks in RAW are stored as they are."""
    en = labels()
    blocks, patches = {}, []
    for fn in (cards, gameover, banners, options, staff):
        b, p = fn(en, rom)
        blocks.update(b)
        patches += p
    return blocks, patches
