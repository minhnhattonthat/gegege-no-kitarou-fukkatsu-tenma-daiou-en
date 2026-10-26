"""insert.py: typeset script/captions.json and script/intro.json into new tilemaps + glyph sheets (fonts/caption.txt,
tools/font.py) and the code hook that gives caption pages their own sheets. build.py calls edits().

Captions (docs/re/text.md): the loader `$82:B84B` reads map 20_nn to $7E:E800, then the shared sheet 20_002. The
hook (JSL at $82:B857) looks the sheet up in a page table instead, so every page is rendered pixel-exact (a VWF with
no engine code). Pages are packed several to a sheet (blocks 20_068 up; the loader's block counter is a signed byte,
so indices must stay below 128). The reveal routine `$80:EE02` walks the top row: tile 0 = skip, id < $2C0 = reveal
2 columns, $2C0-$2DF = 1 column, $2E0 = go to the next row pair, $2E1 = page end. So a line has an even number of
columns, blank cells inside it use tile 1 (never 0), ids stay < $2C0, and the code cell follows the line (column 31
at most).

Modes: en (pages with English; the rest keep the Japanese blocks), marker ([id] + filler at the full measured width
on 4 lines), ruler (column numbers 1-30 on every line, for the width gate).
"""
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import archive  # noqa: E402
import extract  # noqa: E402
import font  # noqa: E402
import lzh  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FIRST_SHEET, LAST_SHEET = 68, 127  # new caption sheets: right after 20_067, below the loader's 128 limit
SHEET_TILES = 0x2C0  # ids from $2C0 reveal one column at a time
SHEET_BYTES = 12064  # the original 20_002 size; sheets are padded to it so the load and DMA see what they did
INTRO_SHEET_BYTES = 8704  # 20_000
LINE_END, PAGE_END = (0x2E0, 0x2F0), (0x2E1, 0x2F1)
BLANK_IN_LINE = 1  # tile 0 would make the reveal skip the cell
LEFT = {"captions": 16, "intro": 16}  # x of the text's left edge
MAX_PX = {"captions": 224, "intro": 224}  # width gate: docs/re/text.md
FILLER = "The quick brown fox jumps over the lazy dog. " * 4

TABLE = 0x1FFF40  # $BF:FF40: sheet block of caption page nn, 66 bytes
# JSL $BF:FF00 over `LDA #$0220 / JSR $ACD5` at $82:B857.
HOOK_SITE = (0x13857, bytes.fromhex("a92002 20d5ac"), bytes.fromhex("2200ffbf eaea"))
HOOK = (0x1FFF00, None, bytes.fromhex(
    "ad6a06"    # LDA $066A      ; caption index nn (the map load just stored $20 | nn << 8 at $0669)
    "29ff00"    # AND #$00FF
    "aa"        # TAX
    "bf40ffbf"  # LDA $BFFF40,x  ; TABLE
    "29ff00"    # AND #$00FF
    "eb"        # XBA
    "092000"    # ORA #$0020     ; A = $20 | sheet << 8, what LDA #$0220 gave for 20_002
    "4b"        # PHK
    "f41cff"    # PEA $FF1C      ; RTL target - 1 = the RTL below
    "f47db8"    # PEA $B87D      ; ACD5 ends in RTS: return to $82:B87E, an RTL, which pops our PEA
    "5cd5ac82"  # JML $82ACD5    ; load the sheet to $7E:B800 (it reloads X)
    "6b"))      # RTL            ; back to $82:B85B
assert HOOK[2][0x1D] == 0x6B and len(HOOK[2]) <= TABLE - HOOK[0]


class SheetFull(Exception):
    pass


def tile_bytes(img, cx, cy):
    """2bpp SNES tile (colour 1 = ink) of the 8x8 cell at (cx, cy) of a 0/1 bitmap."""
    out = bytearray()
    for y in range(8):
        row = img[cy * 8 + y]
        out += bytes([sum(row[cx * 8 + x] << (7 - x) for x in range(8)), 0])
    return bytes(out)


class Sheet:
    """Deduplicating tile sheet: tiles 0..blank are blank (blank cells get id `blank`), glyph tiles follow."""

    def __init__(self, limit, attr=0, blank=BLANK_IN_LINE):
        self.tiles, self.ids, self.limit, self.attr, self.blank = [bytes(16)] * (blank + 1), {}, limit, attr, blank

    def id(self, data):
        if not any(data):
            return self.blank
        if data not in self.ids:
            if len(self.tiles) >= self.limit:
                raise SheetFull(self.limit)
            self.ids[data] = len(self.tiles)
            self.tiles.append(data)
        return self.ids[data]

    def put(self, words, w, img, row, col):
        """Write the bitmap's cells (2 tile rows) at map row/col."""
        for cx in range(len(img[0]) // 8):
            for dy in range(2):
                words[(row + dy) * w + col + cx] = self.attr | self.id(tile_bytes(img, cx, dy))

    def data(self, size):
        out = b"".join(self.tiles)
        assert len(out) <= size
        return out + bytes(size - len(out))


def greedy(para, limit, indent, cont):
    """Greedy word wrap of one paragraph; lines after the first (all of them when `cont`) lose `indent` px."""
    out, cur = [], ""
    for word in para.split(" "):
        cand = f"{cur} {word}" if cur else word
        if cur and font.width(cand) > limit - (indent if out or cont else 0):
            out.append(cur)
            cur = word
        else:
            cur = cand
    out.append(cur)
    return out


def wrap(text, limit, indent=0):
    """Balanced word wrap to `limit` px: each paragraph keeps the greedy line count at the narrowest width that still
    gives it (no one-word widows); {br} forces a break; continuation lines lose `indent` px."""
    lines = []
    for para in text.split("{br}"):
        best = greedy(para, limit, indent, bool(lines))
        for w in range(limit - 1, 0, -1):
            cand = greedy(para, w, indent, bool(lines))
            if len(cand) != len(best):
                break
            best = cand
        lines += best
    return lines


def rows_for(n, low=False):
    """Map rows of n caption lines, the Japanese pages' rule: 24 px apart for up to 3 lines, else 16. A low page
    (scenes whose picture covers caption rows 0-3) has rows 4-7 only: 2 lines."""
    if low:
        assert n <= 2, f"{n} lines on a 2-line page"
        return {1: [5], 2: [4, 6]}[n]
    return {1: [3], 2: [1, 4], 3: [0, 3, 6], 4: [0, 2, 4, 6]}[n]


# Pages the script shows by copying fixed map cells (`F1 04 00 vram src` ops) instead of the reveal walker:
# id -> (row, column, width in px). 20_051 おわり: ending script $81:C37E copies rows 4-5, columns 21-26, 2 at a time.
FIXED = {"20_051": (4, 21, 48)}


def is_low(entry):
    """The Japanese page starts at row 4 or lower: its scene's picture hides rows 0-3 (ruler pages, docs/re/text.md)."""
    return min(r for r, _ in entry["pos"]) >= 4


def caption_map(sheet, imgs):
    """Map bytes of one page from (row, col, bitmap) lines; tiles go into `sheet`."""
    w, h = 32, 8
    words = [0] * (w * h)
    for k, (row, col, img) in enumerate(imgs):
        cols = len(img[0]) // 8
        assert cols % 2 == 0 and col + cols <= 31, f"line at column {col}, {cols} columns"
        sheet.put(words, w, img, row, col)
        words[row * w + col + cols], words[(row + 1) * w + col + cols] = PAGE_END if k == len(imgs) - 1 else LINE_END
    return extract.join_map(w, h, words)


def text_lines(lines, indents=None, low=False):
    """(row, col, bitmap) of wrapped text lines; the block (left-aligned lines) is centred in the caption width."""
    assert 1 <= len(lines) <= 4, f"{len(lines)} lines: {lines}"
    indents = indents or [0] * len(lines)
    wmax = max(i + font.width(t) for i, t in zip(indents, lines))
    assert wmax <= MAX_PX["captions"], f"too wide: {lines}"
    out = []
    for k, (row, text) in enumerate(zip(rows_for(len(lines), low), lines)):
        x = LEFT["captions"] + (MAX_PX["captions"] - wmax) // 2 + indents[k]
        cols = -(-(x % 8 + font.width(text)) // 8)
        out.append((row, x // 8, font.render(text, x % 8, (cols + cols % 2) * 8)))  # even: 2 columns a step
    return out


def ruler_img(cols, digit):
    """One 16 px line: a tick at the left edge of every column and digit(col) beside it."""
    img = [[0] * (cols * 8) for _ in range(16)]
    for c in range(cols):
        for y in range(12, 16):
            img[y][c * 8] = 1
        g = font.render(str(digit(c)), 0, 8)
        for y in range(16):
            for x in range(6):
                img[y][c * 8 + 2 + x] |= g[y][x]
    return img


def ruler_lines():
    ones, tens = (lambda c: (c + 1) % 10), (lambda c: (c + 1) // 10)
    return [(row, 1, ruler_img(30, ones if k % 2 == 0 else tens)) for k, row in enumerate([0, 2, 4, 6])]


def fill(prefix, limit):
    """prefix + as much filler as fits in `limit` px, ending in '|' to show the edge."""
    out = prefix
    for ch in FILLER:
        if font.width(out + ch + "|") > limit:
            break
        out += ch
    return out + "|"


TORTURE = ["ABCDEFGHIJKLMNOPQRSTUVWXYZ  01234", "abcdefghijklmnopqrstuvwxyz  .,!?'\"“”‘’",
           "-—:;()…/&~*+%[]_|  56789  ①②③④"]  # every glyph, double spaces; shown on the first page
assert set("".join(TORTURE)) == set(font.GLYPHS)
ALIEN = {f"{{alien{k}}}": ch for k, ch in enumerate("①②③④", 1)}  # script token -> its font glyph


def marker_lines(eid, low=False):
    n, indent = 2 if low else 4, font.width("“") + 1
    lines = [fill(f"“[{eid}] " if k == 0 else "", MAX_PX["captions"] - (indent if k else 0)) for k in range(n)]
    if eid == "20_003":
        lines[1:] = TORTURE
    return text_lines(lines, [0] + [indent] * (n - 1), low)


def en_lines(en, low=False):
    for token, ch in ALIEN.items():
        en = en.replace(token, ch)
    indent = font.width("“") + 1 if en.startswith("“") else 0
    lines = wrap(en, MAX_PX["captions"], indent)
    return text_lines(lines, [0] + [indent] * (len(lines) - 1), low)


def intro(entry, mode):
    """(map bytes, sheet bytes) of the intro letter 20_001: one line per Japanese position (layout kept), so `en` is a
    list as long as `jp`; leading spaces (4 px each) indent a line."""
    w, h = 32, 64
    words, sheet = [0] * (w * h), Sheet(INTRO_SHEET_BYTES // 16, attr=0x2000)
    assert mode != "en" or len(entry["en"]) == len(entry["pos"]), "intro: en needs one string per jp line"
    for k, (row, col) in enumerate(entry["pos"]):
        if mode == "ruler":
            img, col = ruler_img(32, (lambda c: c % 10) if k % 2 == 0 else (lambda c: c // 10)), 0
        else:
            text = fill(f"[intro {k:02d}] ", MAX_PX["intro"]) if mode == "marker" else entry["en"][k]
            x = LEFT["intro"]
            img, col = font.render(text, x % 8, -(-(x % 8 + font.width(text)) // 8) * 8), x // 8
        sheet.put(words, w, img, row, col)
    return extract.join_map(w, h, words), sheet.data(INTRO_SHEET_BYTES)


def captions(mode):
    """({(0x20, idx): raw block}, page table) for every caption page the mode changes."""
    blocks, table, sheets = {}, {}, []
    for e in json.loads((ROOT / "script" / "captions.json").read_text(encoding="utf-8")):
        nn = int(e["id"][3:])
        if mode == "en" and not e["en"]:
            table[nn] = 2  # Japanese map + the shared Japanese sheet
            continue
        low = is_low(e)
        if e["id"] in FIXED:  # not revealed by the walker: the script copies fixed cells
            row, col, px = FIXED[e["id"]]
            text = e["id"] if mode != "en" else e["en"]
            assert font.width(text) <= px, f"{e['id']}: {text!r} wider than {px} px"
            imgs = [(row, col, font.render(text, 0, px))]
        else:
            imgs = ruler_lines() if mode == "ruler" else \
                marker_lines(e["id"], low) if mode == "marker" else en_lines(e["en"], low)
        for attempt in range(2):
            if attempt or not sheets:
                sheets.append(Sheet(SHEET_TILES))
            trial = copy.deepcopy(sheets[-1])
            try:
                m = caption_map(trial, imgs)
                break
            except SheetFull:
                assert attempt == 0, f"{e['id']} alone overflows a sheet"
        sheets[-1] = trial
        idx = FIRST_SHEET + len(sheets) - 1
        assert idx <= LAST_SHEET, "too many caption sheets"
        blocks[0x20, nn], table[nn] = m, idx
    for k, s in enumerate(sheets):
        blocks[0x20, FIRST_SHEET + k] = s.data(SHEET_BYTES)
    return blocks, table


def edits(rom, mode="en"):
    """(edits, patches) for build.build."""
    if mode not in ("en", "marker", "ruler"):
        raise SystemExit(f"unknown mode {mode!r}")
    blocks, table = captions(mode)
    ie = json.loads((ROOT / "script" / "intro.json").read_text(encoding="utf-8"))[0]
    if mode != "en" or ie["en"]:
        blocks[0x20, 1], blocks[0x20, 0] = intro(ie, mode)
    tbl = bytes(table.get(nn, 2) for nn in range(66))
    patches = [HOOK_SITE, HOOK, (TABLE, None, tbl)]
    if mode == "en":
        import labels
        lb, lp = labels.edits(rom)
        blocks.update({k: v for k, v in lb.items() if k not in labels.RAW})
        patches += lp
    out = {k: lzh.compress(v) for k, v in blocks.items()}
    if mode == "en":
        out.update({k: lb[k] for k in labels.RAW if k in lb})
    return out, patches
