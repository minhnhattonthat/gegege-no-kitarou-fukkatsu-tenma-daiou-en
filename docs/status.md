# Status

Updated at the end of every session. Keep it to what the next session needs; history is in git.

- **Phase:** 5 (engine spike + marker build) done; next is 6 (translate). Last builds (2026-10-26):
  `build/marker.sfc` (`build.py build/marker.sfc --marker`, smoke ok, every page shows its id) and
  `build/ruler.sfc` (`--ruler`, width gate).
- **Done:**
  - Step 0: repo set up (ROM pinned as `rom/kitarou.sfc`, MesenCE 2.2.1 in `tools/mesen/`, pre-commit runs
    `tools/check.py`, guard hook verified).
  - Phase 1: archive + LZ/Huffman codec (`tools/archive.py`, `tools/lzh.py`); all text is pre-built tilemaps in
    category $20 plus raw/linear graphics blocks; script VM and table mapped; graphics survey `docs/re/graphics.md`.
  - Phase 2: `tools/debug/warp.lua` + `tools/debug/scenes.md` (59 scenes) and `tools/debug/tour.py`. Tour on the
    original ROM: 59/59 arrived. RAM map and flow: `docs/re/ram.md`.
  - Phase 3: `tools/build.py` `build(rom, edits)` takes `{(cat, idx): stored bytes}`; edited categories repack in
    place or move to 0x100000+ (2 MiB). Tests: identity, in-place repack identical, relocated $20 decodes.
  - Phase 4: `tools/extract.py dump` -> `script/captions.json` (63 caption pages in play order, `scene` from
    scenes.md, unused 20/32/46 last) and `script/intro.json` (intro letter), through glyph tables
    `tbl/captions.tbl` / `tbl/intro.tbl` (transcribed by eye, read in context). `tests/test_extract.py`: every map
    re-encodes to its exact block bytes, every non-blank cell is a glyph (2 known exceptions), script not stale.
    `script/labels.json`: hand transcription of all graphics text (cards, title, options, partner select, staff
    roll 9 screens, 18 boss banners, game over, shop sign). Tokens: `{br}`/`{end}` = caption line/page codes
    ($2E0/$2E1, never drawn), `{alien1-4}` = invented alien script. Notes: `docs/re/text.md`.
  - Phase 5: VWF without engine code. `fonts/caption.txt` (drawn, 1 bpp proportional, `tools/font.py`);
    `tools/insert.py` renders each caption page pixel-exact into tiles, packs pages into shared sheets (blocks
    20_068+; block indices must stay < 128, the loader counts in a signed byte) and a JSL hook at `$82:B857` ->
    `$BF:FF00` reads the page -> sheet table at `$BF:FF40`. Intro letter: same font into 20_000/20_001, one line
    per Japanese slot. Reveal walker `$80:EE02` modelled in `tests/test_insert.py` (every built page reveals every
    cell). Width gate in `docs/re/text.md` (224 px; 4 lines, 2 on the 6 "low" pages, 20_051 fixed 48 px box;
    intro 17 lines x 224 px). `tools/debug/pages.py` shoots every page at its page end (warp.lua logs
    `page end at fF`): `work/qa/pages_marker/pages.png` = all 60 pages with their ids; torture line on 20_003.
- **Next (phase 6, translate):**
  - Translator input: `script/captions.json` `en` = one string per page (wrapped by `insert.wrap` at 224 px, `{br}`
    forces a break, max 4 lines / 2 on low pages / 48 px for 20_051; “ starts get a hanging indent);
    `script/intro.json` `en` = list of 17 lines (224 px each). Write the batch TSVs + a lint (width/lines via
    `insert.en_lines`, glossary, no JP) into `tools/check.py` before dispatching translators.
  - Graphics labels (cards, title menu, options, game over, boss banners, staff roll) need per-element redraw
    plans; partner screen moves need P2 input to cycle partners (Mesen testRunner has no port 2; warp.lua writes
    `$F1`) to confirm which move belongs to whom.
- **Gotchas:** Mesen `--testRunner` has no port-2 input (`emu.setInput(x, 1)` lands on P1); warp.lua writes the
  P2 joypad mirror `$F1` instead. The in-game loop checks the stage-clear flag only once the HUD is up. Pressing
  right/down on the partner screen with P1 input does nothing. Caption page time is reveal-driven (8 frames per
  2 columns, then a ~60-frame hold), so long pages just play longer; 20_051 is the exception (fixed copies).
- **Open bugs:** none.
- **Waiting on the user:** nothing blocking. Non-blocking: (1) shop signs in cutscene art 18_013 (テレビ, さくらや,
  NIPPO): default = テレビ -> TV only, keep store names. (2) Boss banners 15/16 (5-1, 5-2) and caption 27/50 use an
  invented alien script: default = keep as drawn. (3) Staff-roll name readings are unverified (labels.json notes);
  default = Hepburn readings of the most common reading, flagged in the README.
