# Status

Updated at the end of every session. Keep it to what the next session needs; history is in git.

- **Phase:** 2 (debug tool) done; next is 3 (identity build). Last build: none yet (2026-10-26).
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
- **Next (phase 3, identity build):** `tools/build.py`: unpack the archive (all 40 categories), repack with
  `lzh.py` + original raw blocks, rebuild the category table, write `build/kitarou_en.sfc`; test: byte-identical
  to `rom/kitarou.sfc`. Our compressor is ~3-7% larger than the original, so identity = keep the original packed
  bytes for untouched blocks (repack only edited ones); also test decompress(compress(x)) == x per block.
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
