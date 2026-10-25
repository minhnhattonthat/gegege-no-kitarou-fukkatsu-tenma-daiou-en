"""tour.py: run every scene in tools/debug/scenes.md from a cold boot with warp.lua, check that each one arrived,
write a contact sheet per scene and save its last frame as work/states/<scene>.mss.

    python -X utf8 tools/debug/tour.py [ROM] [--only title,stage3] [--jobs 3] [--out work/qa/tour] [--no-states]

Exit 1 if any scene fails to arrive (no "arrived:" line in its log) or the emulator run fails.
"""
import argparse
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from skill import SKILL  # noqa: E402


def scenes():
    """Rows of the scenes.md table: (scene, frames, god, shows)."""
    rows = []
    for line in (ROOT / "tools/debug/scenes.md").read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*([a-z]+\d*)\s*\|\s*(\d+)\s*\|\s*([01])\s*\|\s*(.*?)\s*\|$", line)
        if m:
            rows.append((m[1], int(m[2]), m[3] == "1", m[4]))
    return rows


def run(rom, out, states, scene, frames, god):
    d = out / scene
    cmd = [sys.executable, "-X", "utf8", str(Path(SKILL) / "scripts/emu.py"), str(rom), "--out", str(d),
           "--script", str(ROOT / "tools/debug/warp.lua"), "--var", f"SCENE='{scene}'", "--frames", str(frames),
           "--shot-every", str(max(60, frames // 32)), "--sheet"]
    if god:
        cmd += ["--var", "GOD=1"]
    if states:
        cmd += ["--state-out", str(states / f"{scene}.mss")]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    log = d / "log.txt"
    lines = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
    arrived = next((l for l in lines if l.startswith("arrived:")), None)
    ok = p.returncode == 0 and arrived is not None
    why = arrived or (f"emu.py exit {p.returncode}: {p.stdout[-300:]}{p.stderr[-300:]}" if p.returncode else "no arrival")
    return scene, ok, why


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("rom", nargs="?", default=str(ROOT / "rom/kitarou.sfc"))
    ap.add_argument("--only", help="comma-separated scene names")
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--out", default=str(ROOT / "work/qa/tour"))
    ap.add_argument("--no-states", action="store_true")
    a = ap.parse_args()
    rows = scenes()
    if a.only:
        want = a.only.split(",")
        unknown = set(want) - {r[0] for r in rows}
        if unknown:
            sys.exit(f"not in scenes.md: {', '.join(sorted(unknown))}")
        rows = [r for r in rows if r[0] in want]
    out = Path(a.out)
    states = None if a.no_states else ROOT / "work/states"
    if states:
        states.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(a.jobs) as ex:
        results = list(ex.map(lambda r: run(Path(a.rom), out, states, r[0], r[1], r[2]), rows))
    bad = 0
    for scene, ok, why in results:
        bad += not ok
        print(f"{'ok  ' if ok else 'FAIL'} {scene:10} {why}")
    print(f"{len(results) - bad}/{len(results)} scenes arrived; sheets in {out}/<scene>/sheet.png")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
