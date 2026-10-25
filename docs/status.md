# Status

Updated at the end of every session. Keep it to what the next session needs; history is in git.

- **Phase:** 4 (extract) done; next is 5 (engine spike and marker build). Last build: `build/kitarou_en.sfc` =
  original (sha1 0451530f..., smoke ok, 2026-10-26).
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
- **Next (phase 5, engine spike + marker build):**
  - English caption renderer: 8x16 (or 8x8 on 16 px lines) font into a new 20_002 sheet, keep $2E0/$2E1 as the
    line/page codes, re-encode maps with `extract.encode`-style layout (32 cols x 4 lines; lines may start at rows
    0-6), recompress, `build.build` with $20 relocated. Marker build: each page shows its id (`20_005`), the intro
    letter its line numbers. Verify with the tour (cut3..cut10, intro) that every page shows its marker, and
    that the reveal routine handles the new code positions.
  - Width gate: measure usable columns per caption page (32 tiles, text seen at cols 4-30) and per intro line.
  - Graphics labels (cards, title menu, options, game over, boss banners, staff roll) need per-element redraw
    plans; partner screen moves need P2 input to cycle partners (Mesen testRunner has no port 2; warp.lua writes
    `$F1`) to confirm which move belongs to whom.
- **Gotchas:** Mesen `--testRunner` has no port-2 input (`emu.setInput(x, 1)` lands on P1); warp.lua writes the
  P2 joypad mirror `$F1` instead. The in-game loop checks the stage-clear flag only once the HUD is up. Pressing
  right/down on the partner screen with P1 input does nothing.
- **Open bugs:** none.
- **Waiting on the user:** nothing blocking. Non-blocking: (1) shop signs in cutscene art 18_013 (テレビ, さくらや,
  NIPPO): default = テレビ -> TV only, keep store names. (2) Boss banners 15/16 (5-1, 5-2) and caption 27/50 use an
  invented alien script: default = keep as drawn. (3) Staff-roll name readings are unverified (labels.json notes);
  default = Hepburn readings of the most common reading, flagged in the README.
