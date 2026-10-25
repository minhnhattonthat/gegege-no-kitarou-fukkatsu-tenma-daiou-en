"""cmpdirs.py: pixel-compare same-named frame PNGs in two emu.py output dirs (regression check between builds).

    python -X utf8 tools/cmpdirs.py work/qa/a/cut3 work/qa/b/cut3

Prints each differing frame and a count; view a pair with sheet.py --compare. Exit 1 if any frame differs.
"""
import sys
from pathlib import Path

from PIL import Image, ImageChops


def main(a, b):
    a, b = Path(a), Path(b)
    same = diff = 0
    for p in sorted(a.glob("f*.png")):
        q = b / p.name
        if not q.exists():
            continue
        if ImageChops.difference(Image.open(p).convert("RGB"), Image.open(q).convert("RGB")).getbbox():
            diff += 1
            print("diff", p.name)
        else:
            same += 1
    print(f"{a.name}: {same} same, {diff} differ")
    return 1 if diff else 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:3]) if len(sys.argv) == 3 else __doc__)
