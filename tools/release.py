"""release.py: build, gate and package a release patch. Stops at the first failure.

    python -X utf8 tools/release.py [--version v1.0] [--force]

Steps: build (en text, so no marker/ruler debug pages) -> check.py -> smoke -> leftover-Japanese check -> visual-QA
gate -> BPS patch (bps.py make re-applies it) -> apply to a clean original and compare -> release/<name>.zip with
the patch and README.txt. The playable image stays in build/. Never publishes anything.

Leftover Japanese: this game has no text encoding (every line is a picture), so jp_left.py has nothing to scan. The
check is tl.py's lint (every caption, letter line and graphics label has English) plus the visual-QA gate, whose
reviewers flag any Japanese left on screen.
"""
import argparse
import hashlib
import subprocess
import sys
import zipfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from skill import SCRIPTS  # noqa: E402

PY = [sys.executable, "-X", "utf8"]


def run(step, args):
    print(f"== {step}")
    r = subprocess.run(PY + [str(a) for a in args], cwd=ROOT)
    if r.returncode:
        sys.exit(f"release stopped: {step} failed (exit {r.returncode})")


def hashes(data):
    return {"size": len(data), "crc": f"{zlib.crc32(data):08X}", "md5": hashlib.md5(data).hexdigest(),
            "sha1": hashlib.sha1(data).hexdigest()}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", default="v1.0")
    ap.add_argument("--force", action="store_true", help="overwrite this version's existing release files")
    a = ap.parse_args()
    name = f"Gegege_no_Kitarou_Fukkatsu_Tenma_Daiou_EN_{a.version}"
    rel = ROOT / "release"
    patch, zpath = rel / f"{name}.bps", rel / f"{name}.zip"
    if (patch.exists() or zpath.exists()) and not a.force:
        sys.exit(f"{zpath.name} or {patch.name} exists; pass --force to overwrite")
    rel.mkdir(exist_ok=True)
    built = ROOT / "build" / "kitarou_en.sfc"
    scripts = Path(SCRIPTS)

    run("build", [ROOT / "tools" / "build.py", built])
    run("tests + lint", [ROOT / "tools" / "check.py"])
    run("smoke", [scripts / "emu.py", built, "--out", ROOT / "work" / "qa" / "smoke", "--route",
                  ROOT / "tools" / "routes" / "boot.txt", "--smoke"])
    run("leftover Japanese (script lint)", [ROOT / "tools" / "tl.py", "check"])
    run("visual-QA gate", [scripts / "qa_gate.py", "check", ROOT / "work" / "qa" / "manifest.tsv",
                           ROOT / "work" / "qa" / "verdicts"])
    run("patch", [scripts / "bps.py", "make", ROOT / "rom" / "kitarou.sfc", built, patch])

    print("== re-apply to a clean original")
    check = ROOT / "work" / "release_check.sfc"
    run("apply", [scripts / "bps.py", "apply", ROOT / "rom" / "kitarou.sfc", patch, check])
    out = built.read_bytes()
    if check.read_bytes() != out:
        sys.exit("release stopped: the patched clean original differs from build/kitarou_en.sfc")
    check.unlink()

    orig, new = hashes((ROOT / "rom" / "kitarou.sfc").read_bytes()), hashes(out)
    readme = (ROOT / "docs" / "release-readme.txt").read_text(encoding="utf-8").format(
        version=a.version, patch=patch.name, out_size=new["size"], out_crc=new["crc"], out_sha1=new["sha1"], **orig)
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(patch, patch.name)
        z.writestr("README.txt", readme.replace("\n", "\r\n"))
    print(f"release: {zpath} (patch {patch.stat().st_size} bytes; patched CRC32 {new['crc']})")


if __name__ == "__main__":
    main()
