# Text

There is no character encoding in this game: every Japanese line is a pre-built BG3 tilemap (2bpp) over a
per-scene glyph sheet, both stored compressed in archive category $20. Translating means drawing new glyph tiles
and new tilemaps offline and repacking the category (no text engine to patch). - verified

## Category $20 (68 blocks)

| Block | What | Format |
|---|---|---|
| 20_000 | intro-scroll glyph sheet (8704 B, 2bpp) | loaded to `$7E:B800`, DMA to VRAM $4000 |
| 20_001 | intro scroll "過去の時代の鬼太郎さんへ ... 天童ユメコ" | map 32x64, 4-byte header (w=32, h=64) |
| 20_002 | caption glyph sheet (12064 B, 2bpp, 754 tiles) | `$82:ACD5` with A=$0220 |
| 20_003-065 | 63 caption pages (cutscene dialogue) | map 32x8, header (32, 8); 16x16 glyphs = 2x2 tiles, half-width digits/punctuation 1x2 |
| 20_066 | chapter-card glyphs (32x32 kanji) | 2bpp |
| 20_067 | chapter cards 序章 / 第一章..第五章 / 最終章 | map 12x28 (header 12, 28); row `$11BD` x 4 rows of 12 tiles DMA'd to VRAM $5C83 (`$82:BB07`) |

Map header: byte 0 = width in tiles, byte 2 = height (words). Glyph sheets: a 16x16 glyph uses tiles t, t+1 (top)
and t+16, t+17 (bottom). Line spacing in captions is 16 px: 4 lines per page, 32 tiles wide.

Caption tiles $2E0 / $2E1 (sheet 20_002) are never drawn: every caption line but the last ends in $2E0, every page
in $2E1, and tour shots show no tile there, so the reveal routine reads them as line-end / page-end codes. An English
sheet must keep them at those ids (or the routine be patched). - verified (screenshot cut3 f675; routine not traced)

Glyph tables: `tbl/captions.tbl` (20_002), `tbl/intro.tbl` (20_000), format in `tools/extract.py`. Sheet 20_002
draws ー and 一 with one glyph ($0AE), and its カ ($104) is only used as 力. Two map cells have no glyph: page 10's
comma has a blank top (0/$2D1 instead of $2C1/$2D1), page 46 has 8 blank tiles with both flip bits ($C000). The
intro map sets priority ($2000) on every glyph word; its 。、 are bottom-only tiles ($010, $011 under a blank).
Roundtrip: `tests/test_extract.py`. - verified

Staff roll 24_003 (glyphs 24_002): 9 screens back to back, each `[w, h]` (words) then w*h BG words. - verified
(each screen rendered with `render_map.render(font, words, 0, w)` reads as a credits page; transcribed in
`script/labels.json` G9.0-G9.8)

Captions 20, 32 and 46 are not referenced by any `e8 NN 25` in the scripts (probably unused; translate anyway).

## Cutscene script VM - verified

- Scripts are bytecode in bank $81. Interpreter `$80:AB73`; opcode >= $DB dispatches through the table at
  `$81:8B1E` (index = (op ^ $FF) * 2); bytes < $DB are data/wait counts.
- Known ops: `E8 vv ff` set object field ff = vv; `EB llhh` call native handler `$80:hhll`; `EC llhh` gosub
  `$81:hhll`; `FF` return/end; `EE llhh` goto; `E3 llhh` loop; `F4`/`F5`/`FD nn` waits.
- Caption: `E8 nn 25` (field $25 = caption block index) then `EB 7B ED` (handler `$80:ED7B` -> `$82:B84B`: loads
  block $20/nn to `$7E:E800` and font $20/2 to `$7E:B800`). Picture: `E8 nn 24` + gosub.
- Script table at `$81:B881` (odd address!), 11 entries: B89D (attract intro), BA82, BAF5, BB00, BAFA, BB6C, BC2F,
  BCF5, BDFF, BF0F, C000 (the long ending script runs to ~$81:C3B5). The attract object reads entry 0.
- Debug warp: write another script address into PRG ROM at file 0xB881/0xB882 from Lua at frame 1; the attract
  sequence then plays that script (`tools/debug/warp.lua`).

## Chapter variable

`$7E:11BD` = stage index 0..18, not the chapter (see ram.md). Writing it at the title before New Game starts that
stage; the first stage of each chapter (0, 1, 5, 8, 13, 15, 17) shows its card, row = chapter. - verified (`cardN`
warps)

In-stage captions: the stage scripts (`$81:A1DD`, `$81:DFB2`... `E8 80 25` / `E8 00 25`) also show caption pages
over gameplay (0-1 boss intro). The warp logs every caption load as `caption 20_NNN at fF`.
