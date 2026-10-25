# Status

Updated at the end of every session. Keep it to what the next session needs; history is in git.

- **Phase:** 1 (recon) done; next is 2 (debug tool). Last build: none yet (2026-10-26).
- **Done:**
  - Step 0: repo set up (ROM pinned as `rom/kitarou.sfc`, MesenCE 2.2.1 in `tools/mesen/`, pre-commit runs
    `tools/check.py`, guard hook verified).
  - Phase 1: archive + LZ/Huffman codec decoded and verified (`tools/archive.py`, `tools/lzh.py`, tests); all text is
    pre-built tilemaps in category $20 (intro scroll, 63 caption pages, chapter cards); cutscene script VM and its
    script table mapped; graphics-text survey in `docs/re/graphics.md`. Notes index: `docs/re/README.md`.
- **Next (phase 2, debug tool):** `tools/debug/warp.lua` + `tools/debug/scenes.md`:
  - `cut0`..`cut10`: patch the script table at file 0xB881 (see docs/re/text.md) so the attract sequence plays
    script N; the ending script `C000` is long (captions 33-64): give it enough frames, and check whether the staff
    roll follows it.
  - `card0`..`card6`: new-game route (`1300 -;6 start;200 -;6 start;300 -;6 start`) + write `$7E:11BD` = N.
  - `title`, `options` (title + Select), `intro` (attract, no input).
  - still to find: game over / continue screen, pause, 2P mode screens, the staff roll, where 01_000 (font with
    フランケンシュタイン, boss names?) and 01_002 are shown. RAM search for lives/health for a game-over warp.
- **Plan for later phases:** no text engine: render English with an 8x16 fixed-width font into new glyph sheets and
  tilemaps offline, recompress, move category $20 to an expanded 2 MiB ROM (docs/re/layout.md). Captions: 4 lines x
  30 chars. Graphics labels (title menu, options, credits, chapter cards) redrawn as linear/planar tiles.
- **Open bugs:** none.
- **Waiting on the user:** nothing blocking. Non-blocking: background shop signs in cutscene art 18_013 (テレビ,
  さくらや, NIPPO): default = translate テレビ -> TV only, keep store names (proper nouns).
