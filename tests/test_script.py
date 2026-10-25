"""Text lint (tools/tl.py): every page translated, fits its box, keeps its tokens and the glossary."""
import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import tl  # noqa: E402


def test_script_lint_clean():
    assert tl.lint() == []


def test_lint_catches_bad_lines():
    data = copy.deepcopy(tl.load())
    pages = {e["id"]: e for e in data["captions"]}
    pages["20_003"]["en"] = "“" + "Verdict! " * 40 + "”"  # 5+ lines
    pages["20_007"]["en"] = "“Kitarou, I’ll come too.”"  # Avoid spelling, 石臼 term missing
    pages["20_050"]["en"] = "“Gibberish!!”"  # alien tokens dropped
    pages["20_051"]["en"] = "The End of It All"  # wider than the 48 px fixed cell
    data["intro"][0]["en"][0] = "ユメコ"  # no glyph
    errs = "\n".join(tl.lint(data))
    for want in ("20_003", "avoid 'Kitarou'", "石臼 needs 'Millstone'", "20_050: alien", "20_051", "20_001#0"):
        assert want in errs, want
