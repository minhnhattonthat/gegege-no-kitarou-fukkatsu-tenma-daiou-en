"""extract.py: the game's text = pre-built BG3 tilemaps over glyph sheets (docs/re/text.md). Decode each map through a
glyph table into lines of text with their position, and encode them back to the exact map words.

Glyph tables (tbl/<set>.tbl), one glyph per line, KIND:TILE=text (TILE = hex tile id of the glyph's top-left tile):
    F:180=判    full width, 2x2 tiles: t t+1 / t+16 t+17
    H:2c2=「    half width, 1x2 tiles: t / t+16
    B:011=、    bottom only, 1x2 tiles: blank / t
Line text: table glyphs, ' ' = one blank column, [TTTT/BBBB] = one column of raw map words (top/bottom).
A line is a pair of tile rows; `pos` is [row, column of its first cell].

    python -X utf8 tools/extract.py dump [--force]      # write script/<set>.json (keeps en/notes of existing ids)
    python -X utf8 tools/extract.py unknown SET OUT.png # labelled sheet of glyphs the table doesn't cover yet
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import archive  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SETS = {  # set -> glyph-sheet block, map blocks, attribute bits every glyph word carries
    "captions": dict(font=(0x20, 2), maps=[(0x20, n) for n in range(3, 66)], attr=0),
    "intro": dict(font=(0x20, 0), maps=[(0x20, 1)], attr=0x2000),
}
RAW = re.compile(r"\[([0-9a-f]{4})/([0-9a-f]{4})\]")


def block(rom, cat, idx):
    for c, i, off, size in archive.blocks(rom):
        if (c, i) == (cat, idx):
            u = archive.unpack(rom, off, size)
            return u[0] if u else rom[off:off + size]
    raise KeyError((cat, idx))


def load_table(name):
    dec = {}
    for n, line in enumerate((ROOT / "tbl" / f"{name}.tbl").read_text(encoding="utf-8").splitlines(), 1):
        if not line or line.startswith("#"):
            continue
        key, sep, val = line.partition("=")
        kind, _, tile = key.partition(":")
        if not sep or not val or kind not in "FHB" or not tile:
            raise ValueError(f"tbl/{name}.tbl line {n}: bad entry {line!r}")
        dec[kind, int(tile, 16)] = val
    return dec


def split_map(data):
    """(width, height, words) of a map block: 4-byte header (width, height as words), then BG words."""
    w, h = data[0] | data[1] << 8, data[2] | data[3] << 8
    words = [data[i] | data[i + 1] << 8 for i in range(4, len(data), 2)]
    assert len(words) == w * h, (w, h, len(words))
    return w, h, words


def join_map(w, h, words):
    return bytes([w & 255, w >> 8, h & 255, h >> 8]) + b"".join(x.to_bytes(2, "little") for x in words)


def decode(w, h, words, dec, attr):
    """[[row, col, text]] for every line (tile-row pair) of a map."""
    lines, r = [], 0
    while r < h:
        top = words[r * w:(r + 1) * w]
        if not any(top):
            r += 1
            continue
        bot = words[(r + 1) * w:(r + 2) * w]
        assert len(bot) == w, f"line at the last row {r}"
        out, c = [], 0
        while c < w:
            T, B = top[c], bot[c]
            t = T & 0x3FF if T & ~0x3FF == attr else None
            if T == 0 and B == 0:
                out.append(" ")
            elif T == 0 and B & ~0x3FF == attr and ("B", B & 0x3FF) in dec:
                out.append(dec["B", B & 0x3FF])
            elif t is not None and B == T + 16 and ("F", t) in dec and c + 1 < w and top[c + 1] == T + 1 and bot[c + 1] == T + 17:
                out.append(dec["F", t])
                c += 1
            elif t is not None and B == T + 16 and ("H", t) in dec:
                out.append(dec["H", t])
            else:
                out.append(f"[{T:04x}/{B:04x}]")
            c += 1
        text = "".join(out)
        col = len(text) - len(text.lstrip(" "))
        lines.append([r, col, text.strip(" ")])
        r += 2
    return lines


def encode(w, h, lines, dec, attr):
    enc = {}
    for (kind, t), v in dec.items():
        enc.setdefault(v, (kind, t))
    vals = sorted(enc, key=len, reverse=True)
    words = [0] * (w * h)
    for r, c, text in lines:
        i = 0
        while i < len(text):
            m = RAW.match(text, i)
            if m:
                cols, i = [(int(m[1], 16), int(m[2], 16))], m.end()
            elif text[i] == " ":
                cols, i = [(0, 0)], i + 1
            else:
                v = next((v for v in vals if text.startswith(v, i)), None)
                if v is None:
                    raise ValueError(f"no glyph for {text[i]!r} in {text!r}")
                kind, t = enc[v]
                T = attr | t
                cols = {"F": [(T, T + 16), (T + 1, T + 17)], "H": [(T, T + 16)], "B": [(0, T)]}[kind]
                i += len(v)
            for top, bot in cols:
                assert c < w, f"line too long: {text!r}"
                words[r * w + c], words[(r + 1) * w + c] = top, bot
                c += 1
    return words


def play_order():
    """{caption index: "scene #n"} from the `captions ...` lists in tools/debug/scenes.md (cut0 repeats intro)."""
    order = {}
    for row in (ROOT / "tools" / "debug" / "scenes.md").read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in row.split("|")]
        if len(cells) < 5 or not re.fullmatch(r"intro|cut\d+", cells[1]):
            continue
        n = 0
        for run in re.findall(r"captions ([\d ,/_-]+)", cells[4].replace("20_", "")):
            for part in re.findall(r"\d+(?:-\d+)?", run):
                a, _, b = part.partition("-")
                for i in range(int(a), int(b or a) + 1):
                    n += 1
                    order.setdefault(i, f"{cells[1]} #{n}")
    return order


def dump(rom, force=False):
    for name, cfg in SETS.items():
        dec = load_table(name)
        path = ROOT / "script" / f"{name}.json"
        old = {}
        if path.exists():
            if not force:
                print(f"{path.name} exists, skipped (--force re-dumps jp and keeps en/notes)")
                continue
            old = {e["id"]: e for e in json.loads(path.read_text(encoding="utf-8"))}
        out, order = [], play_order() if name == "captions" else {}
        maps = list(enumerate(cfg["maps"]))  # entries in play order (scene list order), unused pages last
        maps.sort(key=lambda m: list(order).index(m[1][1]) if m[1][1] in order else len(order) + m[0])
        for _, (cat, idx) in maps:
            eid = f"{cat:02X}_{idx:03d}"
            lines = decode(*split_map(block(rom, cat, idx)), dec, cfg["attr"])
            prev = old.get(eid, {})
            out.append({"id": eid, "scene": order.get(idx, "unused" if order else "intro"),
                        "pos": [l[:2] for l in lines], "jp": [l[2] for l in lines],
                        "en": prev.get("en", ""), "notes": prev.get("notes", "")})
        path.parent.mkdir(exist_ok=True)
        text = re.sub(r"\[\s+(\d+),\s+(\d+)\s+\]", r"[\1, \2]", json.dumps(out, indent=1, ensure_ascii=False))
        path.write_text(text + "\n", encoding="utf-8", newline="\n")
        print(f"{path.name}: {len(out)} entries")


def unknown_sheet(rom, name, out):
    """PNG of every glyph-like cell the table doesn't decode, labelled with its tile id (to transcribe by eye)."""
    from PIL import Image, ImageDraw
    from render_map import tile_px
    cfg = SETS[name]
    font = block(rom, *cfg["font"])
    try:
        dec = load_table(name)
    except FileNotFoundError:
        dec = {}
    keys = set()
    for cat, idx in cfg["maps"]:
        for _, _, text in decode(*split_map(block(rom, cat, idx)), dec, cfg["attr"]):
            keys |= {int(m[1], 16) & 0x3FF or int(m[2], 16) & 0x3FF for m in RAW.finditer(text)}
    keys = sorted(keys)
    cols = 8
    img = Image.new("L", (cols * 90, max(1, (len(keys) + cols - 1) // cols) * 90), 40)
    d = ImageDraw.Draw(img)
    for n, t in enumerate(keys):
        g = Image.new("L", (16, 16))
        for dy in range(2):
            for dx in range(2):
                px = tile_px(font, t + dy * 16 + dx)
                for y in range(8):
                    for x in range(8):
                        g.putpixel((dx * 8 + x, dy * 8 + y), (0, 255, 170, 85)[px[y][x]])
        x, y = n % cols * 90, n // cols * 90
        d.text((x + 4, y + 2), f"{t:03x}", fill=255)
        img.paste(g.resize((64, 64), Image.NEAREST), (x + 4, y + 18))
    img.save(out)
    print(f"{out}: {len(keys)} glyphs")


if __name__ == "__main__":
    rom = (ROOT / "rom" / "kitarou.sfc").read_bytes()
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "dump":
        dump(rom, "--force" in sys.argv)
    elif cmd == "unknown":
        unknown_sheet(rom, sys.argv[2], sys.argv[3])
    else:
        sys.exit(__doc__)
