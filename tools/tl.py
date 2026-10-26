"""tl.py: translation merge, lint and review pairs for script/*.json.

    python -X utf8 tools/tl.py merge work/tl/b001.out.tsv   # id<TAB>EN rows into the script (refuses bad rows)
    python -X utf8 tools/tl.py check                         # lint every translated entry; exit 1 on errors
    python -X utf8 tools/tl.py pairs OUT.txt                 # reviewer pairs file, play order

Ids: a caption page id (20_003; `en` is one string, wrapped by insert.wrap), or ID#k for line k of a list entry
(intro 20_001: one string per Japanese slot; labels G*: one string per `jp` item; a bare label id means #0).
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import font  # noqa: E402
import insert  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FILES = ("captions", "intro", "labels")
TOKEN = re.compile(r"\{alien\d\}")
LABEL_CHARS = set(" !&'(),-./:?©’“”") | set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789")


def load():
    return {name: json.loads((ROOT / "script" / f"{name}.json").read_text(encoding="utf-8")) for name in FILES}


def save(name, entries):
    if name == "labels":  # one entry per line, as hand-written
        text = "[\n" + ",\n".join(" " + json.dumps(e, ensure_ascii=False) for e in entries) + "\n]"
    else:  # extract.dump's format
        text = re.sub(r"\[\s+(\d+),\s+(\d+)\s+\]", r"[\1, \2]", json.dumps(entries, indent=1, ensure_ascii=False))
    (ROOT / "script" / f"{name}.json").write_text(text + "\n", encoding="utf-8", newline="\n")


def glossary():
    """[(jp, en, [avoid...])] from the tables of glossary.md, longest JP first."""
    rows = []
    for line in (ROOT / "glossary.md").read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().split("|")[1:-1]]
        if len(cells) == 5 and cells[0] not in ("JP", "") and not set(cells[0]) <= set("-"):
            rows.append((cells[0], cells[1], [a.strip() for a in cells[4].split(",") if a.strip()]))
    return sorted(rows, key=lambda r: -len(r[0]))


def term_errors(eid, jp, en, terms):
    """JP terms (longest match first, matched spans masked) whose EN form is missing; Avoid spellings present."""
    errs, low = [], en.lower()
    for t_jp, t_en, avoid in terms:
        if t_jp in jp:
            jp = jp.replace(t_jp, "\0" * len(t_jp))
            if t_en.lower() not in low:
                errs.append(f"{eid}: {t_jp} needs {t_en!r}")
        errs += [f"{eid}: avoid {a!r}" for a in avoid if re.search(rf"\b{re.escape(a)}\b", en)]
    return errs


def lint(data=None):
    data, terms, errs = data or load(), glossary(), []
    for e in data["captions"]:
        eid, en, jp = e["id"], e["en"], "".join(e["jp"])
        if not en:
            errs.append(f"{eid}: untranslated")
            continue
        if Counter(TOKEN.findall(en)) != Counter(TOKEN.findall(jp)):
            errs.append(f"{eid}: alien tokens differ from the JP")
        if re.search(r"\{(?!br\}|alien\d\})", en):
            errs.append(f"{eid}: unknown {{code}}")
        try:
            if eid in insert.FIXED:
                assert font.width(en) <= insert.FIXED[eid][2], f"wider than {insert.FIXED[eid][2]} px"
            else:
                insert.en_lines(en, insert.is_low(e))
        except (AssertionError, ValueError) as x:
            errs.append(f"{eid}: {x}")
        errs += term_errors(eid, jp, en, terms)
    for name in ("intro", "labels"):
        for e in data[name]:
            eid, en = e["id"], e["en"]
            if not isinstance(en, list) or len(en) != len(e["jp"]) or not all(en):
                errs.append(f"{eid}: en must be {len(e['jp'])} non-empty strings")
                continue
            for k, line in enumerate(en):
                if name == "intro":
                    try:
                        if font.width(line) > insert.MAX_PX["intro"]:
                            errs.append(f"{eid}#{k}: {font.width(line)} px > {insert.MAX_PX['intro']}")
                    except ValueError as x:
                        errs.append(f"{eid}#{k}: {x}")
                elif line != e["jp"][k] and not set(TOKEN.sub("", line)) <= LABEL_CHARS:  # kept-as-drawn = jp
                    errs.append(f"{eid}#{k}: characters outside the label set: {line!r}")
            errs += term_errors(eid, "".join(e["jp"]), " ".join(en), terms)
    return errs


def merge(tsv):
    data, index, errs, seen = load(), {}, [], set()
    for name, entries in data.items():
        for e in entries:
            index[e["id"]] = (name, e)
    for n, line in enumerate(Path(tsv).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) != 2 or not parts[1].strip() or "\\" in parts[1]:
            errs.append(f"line {n}: want id<TAB>EN, no tabs or escapes in EN")
            continue
        key, en = parts
        eid, _, k = key.partition("#")
        if eid not in index or key in seen:
            errs.append(f"line {n}: unknown or repeated id {key!r}")
            continue
        seen.add(key)
        name, e = index[eid]
        if name == "captions":
            if k:
                errs.append(f"line {n}: caption pages take one string, no #k")
            e["en"] = en
        else:
            k = int(k or 0)
            if not 0 <= k < len(e["jp"]):
                errs.append(f"line {n}: {eid} has {len(e['jp'])} lines")
                continue
            if not isinstance(e["en"], list) or len(e["en"]) != len(e["jp"]):
                e["en"] = [""] * len(e["jp"])
            e["en"][k] = en
    if errs:
        sys.exit("\n".join(errs) + "\nnothing merged")
    for name, entries in data.items():
        save(name, entries)
    print(f"merged {len(seen)} rows")


def pairs(out):
    data, lines = load(), []
    for name in FILES:
        for e in data[name]:
            en = e["en"] if isinstance(e["en"], list) else [e["en"]]
            lines.append(f">> {e['id']} | {e['scene']} | {e.get('notes', '')}")
            lines.append("   JP: " + " / ".join(j.replace("{br}", "").replace("{end}", "") for j in e["jp"]))
            lines.append("   EN: " + " / ".join(en))
    Path(out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{out}: {sum(len(v) for v in data.values())} entries")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "merge" and len(sys.argv) == 3:
        merge(sys.argv[2])
    elif cmd == "check":
        problems = lint()
        print("\n".join(problems) or "OK")
        sys.exit(1 if problems else 0)
    elif cmd == "pairs" and len(sys.argv) == 3:
        pairs(sys.argv[2])
    else:
        sys.exit(__doc__)
