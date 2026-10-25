import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools/debug"))
import tour  # noqa: E402


def test_scene_table_parses():
    rows = tour.scenes()
    names = [r[0] for r in rows]
    assert len(names) == len(set(names))
    for want in ("intro", "title", "options", "coop", "card6", "stage18", "boss18", "gameover", "ending"):
        assert want in names
    assert all(frames > 0 for _, frames, _, _ in rows)
