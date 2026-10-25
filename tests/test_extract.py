import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import extract  # noqa: E402

ROM = ROOT / "rom" / "kitarou.sfc"
needs_rom = pytest.mark.skipif(not ROM.is_file(), reason="no ROM dump in rom/")
# Map cells no glyph explains: a lone comma bottom (top blank instead of 2c1) and 8 flipped blank tiles.
RAW_OK = {"20_010": 1, "20_046": 8}


def test_labels_json():
    """Graphics-text labels (hand transcribed): valid JSON, unique ids, every entry has Japanese."""
    labels = json.loads((ROOT / "script" / "labels.json").read_text(encoding="utf-8"))
    assert len({e["id"] for e in labels}) == len(labels) and all(e["jp"] for e in labels)


@needs_rom
@pytest.mark.parametrize("name", extract.SETS)
def test_roundtrip_and_coverage(name):
    """Re-encoding every decoded map gives the original block bytes; every non-blank cell decodes to a glyph."""
    rom = ROM.read_bytes()
    cfg, dec = extract.SETS[name], extract.load_table(name)
    script = {e["id"]: e for e in json.loads((ROOT / "script" / f"{name}.json").read_text(encoding="utf-8"))}
    for cat, idx in cfg["maps"]:
        eid = f"{cat:02X}_{idx:03d}"
        data = extract.block(rom, cat, idx)
        w, h, words = extract.split_map(data)
        lines = extract.decode(w, h, words, dec, cfg["attr"])
        assert extract.join_map(w, h, extract.encode(w, h, lines, dec, cfg["attr"])) == data, eid
        raw = sum(t.count("[") for _, _, t in lines)
        assert raw == RAW_OK.get(eid, 0), f"{eid}: {raw} undecoded cells"
        assert script[eid]["jp"] == [t for _, _, t in lines] and script[eid]["pos"] == [l[:2] for l in lines], \
            f"script/{name}.json {eid} is stale: extract.py dump --force"
