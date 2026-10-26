"""dlg_shots.py: shoot every in-stage dialogue list (G15) in the emulator.

Most lists play deep inside stages that the warp can't reach, so each one is shown in place of the prologue's: a
copy of the ROM gets the stage-0 caller's `LDA #$864A` (before `JSL $80:A4F4`) pointed at the list, then the stage0
warp runs and a strip of the dialogue row is cut from frames every 10 frames.

    python -X utf8 tools/debug/dlg_shots.py [ROM] [--out work/qa/dlg] [--jobs 4]

Writes OUT/<list>.png (one row per distinct dialogue frame) and OUT/sheet.png (all lists).
"""
import argparse
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from skill import SCRIPTS  # noqa: E402

CALLER = 0x20CE0  # operand of the stage-0 `LDA #$864A`
LISTS = [0x8562, 0x8582, 0x85AE, 0x85CE, 0x861E, 0x864A, 0x8676, 0x868A, 0x869E, 0x86B2, 0x86D2, 0x86FE]
FIRST, LAST = 2200, 3600  # the stage-0 list starts at f2217 (warp from cold boot)
ROW = (0, 192, 256, 224)  # the strip sits on BG3 rows 25-26


def shoot(rom, lst, out):
    data = bytearray(rom)
    assert data[CALLER - 1:CALLER + 2] == bytes.fromhex("a94a86"), "stage-0 caller moved"
    data[CALLER:CALLER + 2] = lst.to_bytes(2, "little")
    d = out / f"{lst:04X}"
    d.mkdir(parents=True, exist_ok=True)
    (d / "rom.sfc").write_bytes(data)
    shots = ",".join(str(f) for f in range(FIRST, LAST, 10))
    subprocess.run([sys.executable, "-X", "utf8", str(Path(SCRIPTS) / "emu.py"), str(d / "rom.sfc"), "--out", str(d),
                    "--script", str(ROOT / "tools" / "debug" / "warp.lua"), "--var", "SCENE='stage0'", "--var", "GOD=1",
                    "--frames", str(LAST), "--shots", shots], check=True, capture_output=True)
    rows, prev = [], None
    for f in range(FIRST, LAST, 10):
        p = d / f"f{f:06d}.png"
        if not p.exists():
            continue
        row = Image.open(p).convert("RGB").crop(ROW)
        if row.getpixel((12, 4)) != (0, 0, 0):  # the HUD box edge: the list is over, the row now holds the HUD
            break
        if row.tobytes() != prev and row.getextrema() != ((0, 0), (0, 0), (0, 0)):
            rows.append(row)
        prev = row.tobytes()
    img = Image.new("RGB", (256, max(1, len(rows)) * 33), (60, 0, 60))
    for i, row in enumerate(rows):
        img.paste(row, (0, i * 33))
    img.save(out / f"{lst:04X}.png")
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rom", nargs="?", default=str(ROOT / "build" / "kitarou_en.sfc"))
    ap.add_argument("--out", default=str(ROOT / "work" / "qa" / "dlg"))
    ap.add_argument("--jobs", type=int, default=4)
    a = ap.parse_args()
    rom, out = Path(a.rom).read_bytes(), Path(a.out)
    with ThreadPoolExecutor(a.jobs) as ex:
        imgs = list(ex.map(lambda lst: shoot(rom, lst, out), LISTS))
    sheet = Image.new("RGB", (256 * 3 + 8, max(i.height for i in imgs) * 4 + 12), (60, 0, 60))
    for k, img in enumerate(imgs):
        sheet.paste(img, ((k % 3) * 260, (k // 3) * (max(i.height for i in imgs) + 4)))
    sheet.save(out / "sheet.png")
    print(f"{len(LISTS)} lists; sheets in {out}")


if __name__ == "__main__":
    main()
