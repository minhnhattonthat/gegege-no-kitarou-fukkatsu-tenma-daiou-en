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
# Banners that the boss code also loads as immediates (the bossN warps go through the record, real play through
# these): stage 0 Tantanbo at $84:8CF3. Found by scanning for `A9 lo hi 85 44` / `A9 DD nn` (issue: garbled banner).
BANNER_IMM = {0: 0x20CF3}


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
            n, cells = strip(text, thick=True)
        new = (0xAC3A + len(data)).to_bytes(2, "little") + bytes([0xDD, n + 0x83])
        patches.append((off, rom[off:off + 4], new))
        if stage in BANNER_IMM:  # the same banner as immediates in the boss code: `LDA #ptr : STA $44 : LDA #map : STA $46`
            imm = BANNER_IMM[stage]
            patches.append((imm, rom[imm:imm + 8], bytes([0xA9, *new[:2], 0x85, 0x44, 0xA9, *new[2:], ])))
        data += cells
    assert len(data) <= BANNER_SIZE, f"banners: {len(data)} bytes > {BANNER_SIZE}"
    return {(0x01, 0): bytes(data) + rom[BANNER_BASE + len(data):BANNER_BASE + BANNER_SIZE]}, patches


def strip(text, thick):
    """(n, tiles) of a centred G10/G15 strip. The map word $nnDD points at one prebuilt BG3 map per width in bank
    $82 ($84DD = 1 cell .. $8BDD = 8) and the strip DMA is a fixed $200 bytes, so 8 cells is the limit."""
    w = font.width(text)
    n = -(-(w + 2) // 16)
    n += n == 2  # the 2-cell map is spaced (cell, gap, cell); the 3-cell map draws contiguous
    assert n <= 8, f"{text!r}: {w} px, over the 8-cell (126 px) strip"
    img = canvas(16 * n, 16)
    g = font.render(text, 0, w + 1)
    blit(img, bold(g) if thick else g, (16 * n - w - 1) // 2, 0)
    return n, b"".join(tile_bytes(img, cx, cy) for cy in range(2) for cx in range(2 * n))


# G15 in-stage dialogue: raw 01_001 ($85:C03A, the archive list misreads it as packed), the same strips as G10. The
# event lists in bank $81 ($81:8562-$81:870B, 6-byte records: delay / strip address, $nnDD map word, hold; 01 / FFFF
# end) are started by `LDA #list : JSL $80:A4F4` (callers in banks $82/$84, two in bank $80 via $80:9AA4). One
# record per strip, in list order; these are the offsets of their address words.
DLG_RECS = [0x8568, 0x8574, 0x8588, 0x8594, 0x85A0, 0x85B4, 0x85C0, 0x85D4, 0x85E0, 0x85EC, 0x85F8, 0x8604,
            0x8610, 0x8624, 0x8630, 0x863C, 0x8650, 0x865C, 0x8668, 0x867C, 0x8690, 0x86A4, 0x86B8, 0x86C4,
            0x86D8, 0x86E4, 0x86F0, 0x8704]
DLG_BASE, DLG_SIZE = 0x2C03A, 12224


def dialogue(en, rom):
    data, patches = bytearray(), []
    for k, off in enumerate(DLG_RECS):
        assert rom[off + 2] == 0xDD
        (text,) = en[f"G15.{k}"]
        n, cells = strip(text, thick=False)
        patches.append((off, rom[off:off + 4], (0xC03A + len(data)).to_bytes(2, "little") + bytes([0xDD, n + 0x83])))
        data += cells
    assert len(data) <= DLG_SIZE, f"dialogue: {len(data)} bytes > {DLG_SIZE}"
    return {(0x01, 1): bytes(data) + rom[DLG_BASE + len(data):DLG_BASE + DLG_SIZE]}, patches


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
    # the widened panel starts at screen x 0: text 8 px in, or the first column sits on the screen edge
    [(0, 8, 0, None), (4, 8, 1, 0), (4, 64, 1, 1), (8, 8, 2, 0), (8, 64, 2, 1), (12, 8, 3, None), (14, 64, 4, None),
     (18, 64, 5, None), (22, 64, 6, None)],
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


class LinearBG:
    """A BG screen whose tiles are a linear 4bpp block (128 px = 16 tiles per row, high nibble first; converted to
    planar by $82:A238) and whose map is a [w, h] + words block. Edit it in pixels, then commit(): each touched cell
    gets its tile rewritten in place when no other cell uses that tile, else a new tile appended to the block."""

    def __init__(self, tiles, mapdata, reuse=False):
        self.reuse, self.freed, self.made = reuse, [], {}
        self.tiles = bytearray(tiles)
        self.n0 = len(tiles) * 2 // 64
        self.w, self.h, self.words = extract.split_map(mapdata)
        self.uses = {}
        for wd in self.words:
            self.uses[wd & 0x3FF] = self.uses.get(wd & 0x3FF, 0) + 1
        self.img = [[self.cell_px(r, c, x, y) for c in range(self.w) for x in range(8)]
                    for r in range(self.h) for y in range(8)]
        self.touched = set()

    def px(self, k, x, y):
        b = self.tiles[(((k // 16) * 8 + y) * 128 + (k % 16) * 8 + x) // 2]
        return b >> 4 if x % 2 == 0 else b & 15

    def cell_px(self, r, c, x, y):
        wd = self.words[r * self.w + c]
        return self.px(wd & 0x3FF, 7 - x if wd & 0x4000 else x, 7 - y if wd & 0x8000 else y)

    def set_px(self, k, x, y, v):
        i = (((k // 16) * 8 + y) * 128 + (k % 16) * 8 + x) // 2
        self.tiles[i] = (self.tiles[i] & 0x0F) | v << 4 if x % 2 == 0 else (self.tiles[i] & 0xF0) | v

    def fill(self, x0, y0, x1, y1, v):
        for y in range(y0, y1):
            for x in range(x0, x1):
                self.img[y][x] = v
        self.touch(x0, y0, x1, y1)

    def draw(self, cimg, x0, y0):
        """Colour-index image; index 0 is transparent."""
        for y, row in enumerate(cimg):
            for x, v in enumerate(row):
                if v:
                    self.img[y0 + y][x0 + x] = v
        self.touch(x0, y0, x0 + len(cimg[0]), y0 + len(cimg))

    def touch(self, x0, y0, x1, y1):
        self.touched |= {(r, c) for r in range(y0 // 8, (y1 + 7) // 8) for c in range(x0 // 8, (x1 + 7) // 8)}

    def commit(self, attr):
        """Write touched cells back; cells that were blank tile 0 take `attr` (palette/priority)."""
        for r, c in sorted(self.touched):
            i = r * self.w + c
            wd = self.words[i]
            k = wd & 0x3FF
            if not any(self.img[r * 8 + y][c * 8 + x] for y in range(8) for x in range(8)):
                if k:
                    self.release(k)
                self.words[i] = 0
                continue
            cell = tuple(self.img[r * 8 + y][c * 8 + x] for y in range(8) for x in range(8))
            if self.made.get(cell) not in (None, k):  # same pixels as a tile this edit already wrote
                self.release(k)
                k = self.made[cell]
                self.uses[k] += 1
                self.words[i] = ((wd & 0x1C00) if wd & 0x3FF else attr) | (wd & 0x2000) | k
                continue
            if k == 0 or self.uses[k] > 1:
                self.release(k)
                k = self.alloc()
            self.made[cell] = k
            self.words[i] = ((wd & 0x1C00) if wd & 0x3FF else attr) | (wd & 0x2000) | k  # flips dropped
            for y in range(8):
                for x in range(8):
                    self.set_px(k, x, y, self.img[r * 8 + y][c * 8 + x])
        self.touched = set()

    def release(self, k):
        self.uses[k] -= 1
        if k and not self.uses[k] and self.reuse:
            self.freed.append(k)

    def alloc(self):
        """A tile no cell uses any more (with reuse: one only the edited cells used), else one past the original
        block (a new row of 16 when needed). Original tiles this map never used are left alone: another screen may
        draw them."""
        if self.freed:
            k = self.freed.pop(0)
            self.uses[k] = 1
            return k
        n = len(self.tiles) * 2 // 64
        k = next((t for t in range(self.n0, n) if not self.uses.get(t)), None)
        if k is None:
            self.tiles += bytes(512)
            k = n
        self.uses[k] = 1
        return k

    def blocks(self):
        return bytes(self.tiles), extract.join_map(self.w, self.h, self.words)


def styled(text, fill, ring, shade=None, thick=False):
    """Colour image of `text` (caption font): glyph pixels `fill`, a 1 px `ring` around them (8-neighbours), and
    an optional `shade` drop shadow 1 px right/down instead of the ring on those sides."""
    g = font.render(text, 1, font.width(text) + 3)[1:16]
    g = [[0] + row for row in g] + [[0] * (len(g[0]) + 1)]
    if thick:
        g = bold(g)
    h, w = len(g), len(g[0])
    out = [[fill if p else 0 for p in row] for row in g]
    for y in range(h):
        for x in range(w):
            if g[y][x]:
                continue
            near = [(dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                    if 0 <= x - dx < w and 0 <= y - dy < h and g[y - dy][x - dx]]
            if near:
                out[y][x] = shade if shade and any(dx >= 0 and dy >= 0 for dx, dy in near) else ring
    return out


# G4/G5 title: BG1 tiles 1A_001 (linear 4bpp, DMA 0x5000 bytes = 640 tiles to VRAM 0), map 1B_001 (32x28).
# Menu text on the scroll (palette 4: 3 parchment, 2 dark ink, 4 light brown), copyright row 23-24 (palette 5:
# 1 light, 4/5 blue edges). The logo (G6) stays Japanese (D5).
TITLE_MENU = [(104, 133, 167, 149, 106, 135), (104, 150, 167, 166, 106, 152)]  # erase box, text x, y
COPY_BOX, COPY_MARK = (72, 184, 200, 197), (78, 184, 90, 197)  # whole JP line; the © mark inside it


# While the scroll unrolls, the open scroll is 16x16 sprites from 22_002 (linear 4bpp, OBJ palette 0 = BG palette
# 4) holding the same menu art: sheet pixel = screen pixel - SCROLL_SPRITE.
SCROLL_SPRITE = (72, 118)


def title(en, rom):
    bg = LinearBG(extract.block(rom, 0x1A, 1), extract.block(rom, 0x1B, 1))
    obj = extract.block(rom, 0x22, 2)
    n = len(obj) * 2 // 64
    spr = LinearBG(obj, extract.join_map(16, n // 16, list(range(n))))  # identity map: every tile edits in place
    for (x0, y0, x1, y1, tx, ty), text in zip(TITLE_MENU, en["G4"]):
        img = styled(text, 2, 4)
        assert tx + len(img[0]) <= x1 and ty + len(img) <= y1 + 2, f"G4: {text!r} too big"
        for layer, (dx, dy) in ((bg, (0, 0)), (spr, SCROLL_SPRITE)):
            layer.fill(x0 - dx, y0 - dy, x1 - dx, y1 - dy, 3)
            layer.draw(img, tx - dx, ty - dy)
    bg.commit(0x1000)
    spr.commit(0)
    assert len(spr.tiles) == len(obj)
    (text,) = en["G5"]
    assert text.startswith("©")
    mark = [row[COPY_MARK[0]:COPY_MARK[2]] for row in bg.img[COPY_MARK[1]:COPY_MARK[3]]]
    img = styled(text[1:].strip(), 1, 4, shade=5)
    total = len(mark[0]) + 2 + len(img[0])
    x = 128 - total // 2
    bg.fill(min(x, COPY_BOX[0]), COPY_BOX[1], max(x + total, COPY_BOX[2]), COPY_BOX[3], 0)
    bg.draw(mark, x, COPY_MARK[1])
    bg.draw(img, x + len(mark[0]) + 2, COPY_BOX[1] - 1)
    bg.commit(0x1400)
    tiles, m = bg.blocks()
    assert len(tiles) <= 0x5000, "title tiles past the 0x5000-byte DMA"
    return {(0x1A, 1): tiles, (0x1B, 1): m, (0x22, 2): spr.blocks()[0]}, []


# G8 partner select: BG tiles 1C_000 (linear 4bpp, DMA 0x5400 bytes to VRAM $5000), screen map 1D_000 (32x28,
# header box rows 2-3 cols 8-23) and one 20x10 window map per partner, 1D_001..1D_006: name rows 1-2 and the move
# rows 7-8 in cols 8-19, 必殺技 rows 4-5. Text is colour 11 (white) on a transparent cell. The maps share tiles,
# so they are edited as one stacked map.
PARTNER_HEADER = (64, 16, 192, 32)  # px box in 1D_000
PARTNER_NAME, PARTNER_SPECIAL, PARTNER_MOVE = (64, 8, 160, 24), (64, 32, 160, 48), (64, 56, 160, 72)


def partner(en, rom):
    maps = [extract.split_map(extract.block(rom, 0x1D, i)) for i in range(7)]
    rows0, words = [], []
    for w, h, wd in maps:
        rows0.append(len(words) // 32)
        for r in range(h):
            words += wd[r * w:(r + 1) * w] + [0] * (32 - w)
    bg = LinearBG(extract.block(rom, 0x1C, 0), extract.join_map(32, len(words) // 32, words), reuse=True)
    header, special, *pairs = en["G8"]

    def put(box, text, y0, align):
        x0, y1, x1, y2 = box[0], box[1] + y0, box[2], box[3] + y0
        bg.fill(x0, y1, x1, y2, 0)
        w = font.width(text)
        assert w <= x1 - x0, f"G8: {text!r} wider than {x1 - x0} px"
        x = x0 + {"center": (x1 - x0 - w) // 2, "left": 0, "indent": min(24, x1 - x0 - w)}[align]
        bg.draw([[11 if p else 0 for p in row] for row in font.render(text)], x, y1)

    put(PARTNER_HEADER, header, 0, "center")
    for k in range(6):
        y0 = rows0[k + 1] * 8
        put(PARTNER_NAME, pairs[2 * k], y0, "center")
        put(PARTNER_SPECIAL, special, y0, "left")
        put(PARTNER_MOVE, pairs[2 * k + 1], y0, "indent")
    bg.commit(0)
    tiles, m = bg.blocks()
    # Extra tiles past the original 576 still sit inside the 0x5400-byte DMA (672 tiles, VRAM up to $7A00, which
    # held WRAM leftovers before) and the decompress buffer $7E:2000-$7E:7600 (scratch: the boot and title
    # graphics pass through it; nothing writes it from the title to the first stage, ramwrites probe 2026-10-26).
    assert len(tiles) <= 0x5400, f"partner screen: {len(tiles) * 2 // 64} tiles > 672"
    _, _, words = extract.split_map(m)
    out = {(0x1C, 0): tiles}
    for i, (w, h, _) in enumerate(maps):
        out[0x1D, i] = extract.join_map(w, h, [words[(rows0[i] + r) * 32 + c] for r in range(h) for c in range(w)])
    return out, []


# G12 city picture 18_013 (linear 4bpp; the picture map shows the sheet as it is): the vertical テレビ sign is a
# 5 px column (x 99-103, y 23-51, colour 1 on 11). TV is drawn in the same tiny pixel style; the store names stay
# (status.md default).
SIGN_TV = """
#####
..#..
..#..
..#..
..#..
..#..
..#..
.....
.....
.....
.....
#...#
#...#
#...#
#...#
.#.#.
.#.#.
..#..
"""


# The other signs in the picture, romanised in a 3x5 pixel font (the user's ruling, D9). Each: picture box
# (x0, y0, x1, y1) cleared to `bg`, then the text in `ink` at (x, y); "rot" = turned 90 degrees clockwise (reads top
# to bottom). The plate under the TV sign is widened left over the lamp pole: SAKURAYA needs 31 px, it had 18.
PIX5 = {
    "A": ".#.|#.#|###|#.#|#.#", "I": "###|.#.|.#.|.#.|###", "K": "#.#|#.#|##.|#.#|#.#", "N": "##.|#.#|#.#|#.#|#.#",
    "O": "###|#.#|#.#|#.#|###", "R": "##.|#.#|##.|#.#|#.#", "S": "###|#..|###|..#|###", "T": "###|.#.|.#.|.#.|.#.",
    "U": "#.#|#.#|#.#|#.#|###", "Y": "#.#|#.#|.#.|.#.|.#.",
}
CITY_SIGNS = [  # (en index in G12, box, bg, ink, x, y, rotated)
    (3, (0, 35, 17, 42), 2, 10, 1, 36, False),  # ..ントン on the left wall, cut by the picture edge
    (1, (21, 28, 26, 59), 10, 2, 21, 28, True),  # さくらや, red vertical sign under NIPPO
    (1, (84, 67, 117, 74), 7, 3, 85, 68, False),  # さくらや plate under the TV sign (border 6 drawn round it)
    (4, (118, 17, 128, 22), 12, 3, 118, 17, False),  # レイン.. top right, cut by the picture edge
]


def pix5(text, rot):
    rows = [""] * 5
    for k, ch in enumerate(text):
        for r, line in enumerate(PIX5[ch].split("|")):
            rows[r] += ("." if k else "") + line
    img = [[1 if ch == "#" else 0 for ch in row] for row in rows]
    return [[img[4 - c][r] for c in range(5)] for r in range(len(img[0]))] if rot else img


def city_sign(en, rom):
    assert en["G12"][0] == "TV", "G12: the sign art is drawn for 'TV'"
    sheet = extract.block(rom, 0x18, 13)
    n = len(sheet) * 2 // 64
    pic = LinearBG(sheet, extract.join_map(16, n // 16, list(range(n))))
    x0, y0, x1, y1 = 99, 23, 104, 52
    for y in range(y0, y1):
        for x in range(x0, x1):
            if pic.img[y][x] == 1:
                pic.img[y][x] = 11
    art = [[1 if ch == "#" else 0 for ch in line] for line in SIGN_TV.strip().splitlines()]
    pic.draw(art, x0, 24)
    pic.touch(x0, y0, x1, y1)
    w, h = len(pic.img[0]), len(pic.img)
    for k, (bx0, by0, bx1, by1), bg, ink, x, y, rot in CITY_SIGNS:
        for yy in range(by0, by1):
            for xx in range(bx0, bx1):
                edge = bg == 7 and (yy in (by0, by1 - 1) or xx in (bx0, bx1 - 1))  # the plate's border
                pic.img[yy][xx] = 6 if edge else bg
        glyphs = pix5(en["G12"][k], rot)
        if not rot and x + len(glyphs[0]) <= w:
            assert x + len(glyphs[0]) <= bx1 and y + 5 <= by1, f"G12: {en['G12'][k]!r} too big for its sign"
        assert not rot or y + len(glyphs) <= by1, f"G12: {en['G12'][k]!r} too long for its sign"
        for dy, row in enumerate(glyphs):
            for dx, p in enumerate(row):
                if p and x + dx < w and y + dy < h:  # signs at the picture edge are cut off, like the Japanese
                    pic.img[y + dy][x + dx] = ink
        pic.touch(bx0, by0, bx1, by1)
    pic.commit(0)
    assert len(pic.tiles) == len(sheet)
    return {(0x18, 13): pic.blocks()[0]}, []


# G14 HUD icon: raw 01_003 (planar 4bpp, DMA'd to VRAM $5000 = BG2 tiles $280+), the 16x16 鬼 = block tiles
# $2E/$2F over $3E/$3F; colour 2 stone, 7 engraved ink, the right column and bottom row are the box edge (kept).
HUD_BASE, HUD_TILES = 0x2F77A, (0x2E, 0x2F, 0x3E, 0x3F)
HUD_ONI = """
.##..#...#.##
#..#.##..#.##
#..#.##..#.##
#..#.#.#.#.##
#..#.#.#.#.##
#..#.#..##.##
#..#.#..##.##
#..#.#...#.##
.##..#...#.##
"""


def hud(en, rom):
    assert en["G14"] == ["ONI"], "G14: the icon art is drawn for 'ONI'"
    data = bytearray(rom[HUD_BASE:HUD_BASE + 4096])
    tiles = [data[t * 32:t * 32 + 32] for t in HUD_TILES]
    img = canvas(16, 16)
    for k, b in enumerate(tiles):
        for y in range(8):
            for x in range(8):
                v = sum(((b[(p // 2) * 16 + y * 2 + (p & 1)] >> (7 - x)) & 1) << p for p in range(4))
                img[(k // 2) * 8 + y][(k % 2) * 8 + x] = 2 if v == 7 and x + (k % 2) * 8 < 15 else v
    art = [[7 if ch == "#" else 0 for ch in line] for line in HUD_ONI.strip().splitlines()]
    blit(img, art, 1, 3)
    for k, t in enumerate(HUD_TILES):
        data[t * 32:t * 32 + 32] = tile4(img, k % 2, k // 2)
    return {(0x01, 3): bytes(data)}, []


RAW = {(0x01, 0), (0x01, 1), (0x01, 2), (0x01, 3)}  # blocks the game reads uncompressed (DMA straight from ROM)


def edits(rom):
    """(blocks {(cat, idx): unpacked bytes}, patches [(off, orig, new)]); blocks in RAW are stored as they are."""
    en = labels()
    blocks, patches = {}, []
    for fn in (cards, gameover, banners, options, staff, title, partner, city_sign, hud, dialogue):
        b, p = fn(en, rom)
        blocks.update(b)
        patches += p
    return blocks, patches
