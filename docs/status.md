# Status

Updated at the end of every session. Keep it to what the next session needs; history is in git.

- **Phase:** 7 (insert, fit, check) done; next is 8 (QA in the emulator). Last builds (2026-10-26):
  `build/kitarou_en.sfc` (English captions + letter, smoke ok),
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
  - Phase 6: whole script translated in one batch by the controller (63 caption pages, 17-line letter, every
    graphics label in `script/labels.json` `en` as a list per `jp`). `tools/tl.py` merge (TSV `id<TAB>EN`, `ID#k`
    for list lines) / check (lint) / pairs; `tests/test_script.py` gates it (width via `insert.en_lines`, alien
    tokens, glyphs, glossary terms + Avoid, label charset). `glossary.md` filled (D&Q Kitaro names: Kitaro,
    Medama Oyaji, Nezumi Otoko...); speakers per page in `docs/synopsis.md`; `docs/reviewer-brief.md`. Reviewer
    (sonnet): Approved, 0 Critical, 1 Important (unused 20_032, fixed) + minors (most applied). Alien script kept
    as drawn: glyphs ①-④ in `fonts/caption.txt` (`insert.ALIEN`). `insert.wrap` now balances lines (greedy line
    count, narrowest width) so no one-word widows. `build/kitarou_en.sfc` smoke ok; all 60 pages shot English and
    in bounds (`work/qa/pages_en/pages.png`).
  - Phase 7: every graphics label redrawn by `tools/labels.py` (`edits(rom)`, called from `insert.edits`):
    chapter cards 20_066/067, game over 01_002, boss banners 01_000, options 27_004/005, staff roll 24_002/003
    (INTERBEC logo kept), title menu + copyright 1A_001/1B_001/22_002 (`LinearBG` reallocates tiles), partner
    select 1C_000/1D_000-006 (name/move per window read from the maps, so the mapping is not a guess), TV sign in
    18_013 (ending city shot; store names kept). `build.py` writes `build/kitarou_en.writes.txt`;
    `tests/test_build.py::test_writes_romdiff_clean` gates it with `romdiff.py --writes` (en + marker), plus a
    branch-into-hook scan. check.py 19 passed; tour on the EN build 59/59 arrived (`work/qa/tour/`).
  - Phase 8 (part): tour EN + `work/qa/tour_jp`; 111 sheets, 4 visual-qa agents (`docs/visual-qa-brief.md` has the
    game's non-bugs); `qa_gate.py check work/qa/manifest.tsv work/qa/verdicts` exits 0. Fixed: 2-cell boss banners
    (Witch/Suiko/Tenko) drew with a gap -> `labels.banners` pads to 3 cells. HUD 鬼 icon redrawn ONI (D8,
    `labels.hud`, 01_003). Found and translated G15: 28 in-stage dialogue strips in raw 01_001 (the archive list
    misreads it as packed, so the phase-1 survey missed it; format in text.md, `labels.dialogue`). Only the stage0
    list (G15.16-18) is shot in the emulator; the other 11 lists play deep in stages (callers in labels.json notes)
    and are checked offline by rendering the strips. Their speakers are guessed from the text.
- **Next (phase 8, QA):** shoot the other G15 lists (find a warp/state per caller, or an agent playtest); zoomed
  cold-boot shot of every graphics-text row (cards, game over, banners, options, staff roll, title, partner,
  TV sign: drawn in 18_013 and checked offline, but no cut10 shot every 300 frames showed it; find its frame). Partner screen
  only shows the first partner (P2 cursor can't be driven headless; writing `$F1` after the joypad read did
  nothing) - the other 5 windows are checked offline by rendering 1D_00x, or find the cursor RAM var.
  Optional polish from review: 20_018 "the me of this era", 20_061 wraps "Space / yokai".
- **Gotchas:** Mesen `--testRunner` has no port-2 input (`emu.setInput(x, 1)` lands on P1); warp.lua writes the
  P2 joypad mirror `$F1` instead. The in-game loop checks the stage-clear flag only once the HUD is up. Pressing
  right/down on the partner screen with P1 input does nothing. Caption page time is reveal-driven (8 frames per
  2 columns, then a ~60-frame hold), so long pages just play longer; 20_051 is the exception (fixed copies).
- **Open bugs:** none.
- **Waiting on the user:** nothing blocking. Non-blocking: (1) shop signs in cutscene art 18_013 (テレビ, さくらや,
  NIPPO): default = テレビ -> TV only, keep store names. (2) Boss banners 15/16 (5-1, 5-2) and caption 27/50 use an
  invented alien script: default = keep as drawn. (3) Staff-roll name readings are unverified (labels.json notes);
  default = Hepburn readings of the most common reading, flagged in the README.
