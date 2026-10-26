# Visual-QA reviewer brief - <Game title>

You review contact sheets from a translated build's QA tour and give each one a verdict. Read-only on everything
except your one verdict file: no edits to the repo, no git, no subagents.

## Inputs (in your dispatch)
- A chunk file: one `id<TAB>path` line per sheet. Read every sheet in it; none may be skipped.
- Your verdict file: `work/qa/verdicts/<chunk>.tsv`.
- Optional: the original ROM's sheets (`work/qa/tour_jp/`, same ids) and `glossary.md`.

## How to look
- Read each sheet whole first. Where text is small, zoom into it with
  `python -X utf8 $SKILL/scripts/sheet.py SHEET.png --crop x,y,w,h --zoom 3 --out <scratch>.png` and read that.
- When something looks wrong, open the same id from `tour_jp/` (`sheet.py EN.png --compare JP.png`). If the
  original shows the same thing, it is the game's own behaviour: `ok`, with a note.

## Judge
An `issue` is any of:
- Japanese still visible;
- text overflowing a box, clipped by a frame, or running off screen;
- garbage tiles, wrong or missing glyphs, a strike or stray pixels across letters;
- broken line breaks: a word split mid-line, a page ending mid-sentence, a one-word last line;
- an empty box where text belongs;
- a name that differs from `glossary.md`.

Standing non-bugs, `ok` (the controller adds the game's own below):
- text still typing out, a box mid-fade or mid-scroll, a cursor caught mid-blink;
- a map or scene still loading after a warp;
- anything identical in the original's sheet.
- <game-specific: e.g. "the double cursor in the shop is the original's">

## Verdicts
Write your verdict file once you have read every sheet, one line per id in the chunk:
`id<TAB>ok|issue<TAB>what and where` (for an issue: which tile, which text, what is wrong).
Then return a short summary: counts, and the issues one per line.

## This game's standing non-bugs
- Original-ROM sheets for comparison: same scene path under `work/qa/tour_jp/` (e.g. `work/qa/tour/card0/sheet.png` -> `work/qa/tour_jp/card0/sheet.png`).
- Boss banners 5-1/5-2 and captions 20_027/20_050 use an invented alien script (glyphs, not Japanese): intended.
- Ending city shot: store names (さくらや, NIPPO) kept on purpose; only the TV sign is English.
- INTERBEC logo on the staff roll kept as drawn.
- HUD 鬼 icon in the status bar: kept as an icon (same pixels as JP), not text to translate.
