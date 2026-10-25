"""pages.py: shoot every caption page of the cutscenes fully revealed, one labelled crop per page.

Runs the caption scenes of tools/debug/scenes.md (intro, cut3, cut5-10) with warp.lua for `--stretch` times their
frame budget (longer text reveals longer), takes a shot every --every frames, and for each `caption 20_NNN at fF`
log line keeps the first shot after the reveal's `page end at fF` (logged at $80:EE37).

    python -X utf8 tools/debug/pages.py ROM [--only cut3,cut5] [--out work/qa/pages] [--stretch 2.2] [--every 20]
        [--reuse]   # re-pick from the runs already in OUT

Writes OUT/<scene>/... runs, OUT/<id>.png (full frame of the page) and OUT/pages.png (all crops, labelled).
Exit 1 if a scene's run fails or a page of script/captions.json (except unused ones) never reached its page end.
"""
import argparse
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools/debug"))
import insert  # noqa: E402
from skill import SKILL  # noqa: E402
from tour import scenes  # noqa: E402

CROP = (0, 144, 256, 224)


def run(rom, out, scene, frames, every, reuse=False):
    d = out / scene
    cmd = [sys.executable, "-X", "utf8", str(Path(SKILL) / "scripts/emu.py"), str(rom), "--out", str(d),
           "--script", str(ROOT / "tools/debug/warp.lua"), "--var", f"SCENE='{scene}'", "--frames", str(frames),
           "--shot-every", str(every), "--timeout", "3600"]
    if not (reuse and (d / "log.txt").exists()):
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if p.returncode not in (0, 124) or not (d / "log.txt").exists():  # 124: wall-clock timeout, shots count
            return scene, None
    log = (d / "log.txt").read_text(encoding="utf-8")
    events = [(m[1], int(m[2])) for m in re.finditer(r"caption (20_\d{3}) at f(\d+)", log)]
    ends = [int(m[1]) for m in re.finditer(r"page end at f(\d+)", log)]
    shots = sorted((int(f.stem[1:]), f) for f in d.glob("f*.png") if f.stem[1:].isdigit())
    best = []
    for k, (eid, f0) in enumerate(events):
        f1 = events[k + 1][1] if k + 1 < len(events) else frames + 1
        end = next((e for e in ends if f0 <= e < f1), None)
        # the first shot a few frames after the page-end code: the full page, before the hold fades it
        # pages the script draws by fixed cell copies (insert.FIXED) never log a page end: 300 frames after the load
        start = end + 4 if end is not None else f0 + 300 if eid in insert.FIXED else f1
        cand = [s for s in shots if start <= s[0] < f1]
        if cand and eid != "20_001":  # the intro letter scrolls; its own check is the tour sheet
            best.append((eid, cand[0]))
    return scene, best


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("rom")
    ap.add_argument("--only")
    ap.add_argument("--out", default=str(ROOT / "work/qa/pages"))
    ap.add_argument("--stretch", type=float, default=2.2)
    ap.add_argument("--every", type=int, default=20)
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--reuse", action="store_true", help="re-pick shots from earlier runs in OUT, no emulator")
    a = ap.parse_args()
    rows = [r for r in scenes() if re.fullmatch(r"intro|cut(3|5|6|7|8|9|10)", r[0])]
    if a.only:
        rows = [r for r in rows if r[0] in a.only.split(",")]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(a.jobs) as ex:
        results = list(ex.map(lambda r: run(Path(a.rom), out, r[0], int(r[1] * a.stretch), a.every, a.reuse), rows))
    seen, crops, bad = {}, [], 0
    for scene, best in results:
        if best is None:
            print(f"FAIL {scene}: emulator run failed")
            bad += 1
            continue
        for eid, (f, path) in best:
            if eid in seen:
                continue
            seen[eid] = f"{scene} f{f}"
            Image.open(path).save(out / f"{eid}.png")
            crops.append((f"{eid}  {scene} f{f}", Image.open(path).convert("RGB").crop(CROP)))
    entries = json.loads((ROOT / "script/captions.json").read_text(encoding="utf-8"))
    ran = {r[0] for r in rows}
    missing = [e["id"] for e in entries if e["scene"].split()[0] in ran and e["id"] not in seen]
    if crops:
        w, h = CROP[2] - CROP[0], CROP[3] - CROP[1] + 12
        cols = 3
        sheet = Image.new("RGB", (cols * w, -(-len(crops) // cols) * h), (60, 0, 60))
        d = ImageDraw.Draw(sheet)
        for i, (label, im) in enumerate(crops):
            x, y = i % cols * w, i // cols * h
            d.text((x + 2, y), label, fill=(255, 255, 0))
            sheet.paste(im, (x, y + 12))
        sheet.save(out / "pages.png")
    print(f"{len(seen)} pages shot -> {out / 'pages.png'}" + (f"; never seen: {', '.join(missing)}" if missing else ""))
    sys.exit(1 if bad or missing else 0)


if __name__ == "__main__":
    main()
