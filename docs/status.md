# Status

Updated at the end of every session. Keep it to what the next session needs; history is in git.

- **Phase:** 3 (identity build) done; next is 4 (extract). Last build: `build/kitarou_en.sfc` = original
  (sha1 0451530f..., smoke ok, 2026-10-26).
- **Done:**
  - Step 0: repo set up (ROM pinned as `rom/kitarou.sfc`, MesenCE 2.2.1 in `tools/mesen/`, pre-commit runs
    `tools/check.py`, guard hook verified).
  - Phase 1: archive + LZ/Huffman codec (`tools/archive.py`, `tools/lzh.py`); all text is pre-built tilemaps in
    category $20 plus raw/linear graphics blocks; script VM and table mapped; graphics survey `docs/re/graphics.md`.
  - Phase 2: `tools/debug/warp.lua` + `tools/debug/scenes.md` (59 scenes: intro, title, options, coop/partner select,
    cut0-cut10, card0-6, stage0-18, boss0-18 banners, clear0, gameover, ending + staff roll) and
    `tools/debug/tour.py` (runs all, checks the `arrived:` log line, sheets in `work/qa/tour/`, states in
    `work/states/`). Tour on the original ROM: 59/59 arrived (2026-10-26). RAM map and flow: `docs/re/ram.md`.
    G8-G11 located: partner select (`coop`), staff roll (`ending`), boss-name banners from 01_000 (`bossN`),
    game over from 01_002 (`gameover`).
  - Phase 3: `tools/build.py` `build(rom, edits)` takes `{(cat, idx): stored bytes}`; untouched categories keep
    their bytes, an edited one is repacked in place or moved to 0x100000+ (ROM -> 2 MiB, header $0B, table entry
    rewritten, checksum fixed). `tests/test_build.py`: identity, every category repacked in place = identical,
    recompressed $20 relocates and decodes. `test_lzh.py`: compress/decompress roundtrip on every packed block.
    In emulator: relocated-$20 ROM shows the same captions (cut3/cut8, 1-2 frames later). `tools/cmpdirs.py`
    pixel-diffs two emu runs.
- **Next (phase 4, extract):** no encoding exists, so "extract" = transcribe every caption page into `script/`:
  build a glyph table for sheet 20_002 (tile id of each 16x16 glyph -> kana/kanji; half-width 1x2 digits and
  punctuation), and same for 20_000 (intro scroll) and 20_066 (cards); `tools/extract.py` reads each map
  (20_001, 20_003-065, 20_067) into `script/captions.tsv` (id, 4 lines). Roundtrip test: re-rendering each
  transcription through the table gives the original map bytes; every non-blank map cell is covered. Glyph
  identification: render the sheet (`render_map.py`/`tiles.py render`) and transcribe by eye, cross-check with
  the tour shots; unused captions 20/32/46 included.
- **Plan for later phases:** no text engine: render English with an 8x16 fixed-width font into new glyph sheets and
  tilemaps offline, recompress, move category $20 (and 01, 24, 27, 1A, 1C as needed) to an expanded 2 MiB ROM
  (docs/re/layout.md). Captions: 4 lines x 30 chars. Boss banners: one 01_000 strip per boss (format still to
  decode: ram.md). Graphics labels (title menu, options, credits, chapter cards) redrawn as linear/planar tiles.
- **Gotchas:** Mesen `--testRunner` has no port-2 input (`emu.setInput(x, 1)` lands on P1); warp.lua writes the
  P2 joypad mirror `$F1` instead. The in-game loop checks the stage-clear flag only once the HUD is up.
- **Open bugs:** none.
- **Waiting on the user:** nothing blocking. Non-blocking: (1) shop signs in cutscene art 18_013 (テレビ, さくらや,
  NIPPO): default = テレビ -> TV only, keep store names. (2) Boss banners 15/16 (5-1, 5-2) use an invented alien
  script: default = keep as drawn.
