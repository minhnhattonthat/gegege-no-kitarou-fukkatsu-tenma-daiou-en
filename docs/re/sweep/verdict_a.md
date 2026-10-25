# verdict_a: static sweep pages 000-010 (blocks 01_000 .. 15_010)

## Japanese text hits
- page_000 y~2 (img y~4) | 01_000 raw 5120 B | 2bpp 16x16 kana/kanji glyph set (320 tiles; reads clean at 2bpp, 16 tiles per row). Legible word: フランケンシュタイン; rest are kana (hira+kata, dakuten) and kanji pieces of names/labels, probably enemy/boss names or banner words. Some rows misaligned at 16 cols, so arrangement varies. | high
- page_000 y~62 (img y~124) | 01_002 raw 1920 B | 2bpp glyph halves (kana/kanji, e.g. ゲ, ム, オ, ト, ノ, パ, す, な, い, plus a few small sprites). Tiles are assembled by a tilemap, so no linear width reads cleanly; likely title/banner/label text. | medium-high

## English/Latin text hits
- none on pages 000-010

## Not text (checked)
- 01_001 starfield dots; 01_004 palette (32 B)
- small art blocks 02_000 04_001 05_001 07_001 08_001 09_001 0A_001 0D_001 0E_000 0F_001 11_001 12_001 14_001: scenery/icons, checked at 2bpp and 4bpp
- big blocks (04_000 05_000 05_005 06_005 07_000 08_000 09_000 0A_000 0C_000 0D_000 0F_000 10_000 11_000 12_000 13_000 14_000): column-striped non-planar data in both 2bpp and 4bpp (tilemaps or another format)
- 15_000..15_010: non-planar structured data in both depths, no glyphs

checked pages: 000, 001, 002, 003, 004, 005, 006, 007, 008, 009, 010 (also re-rendered the same blocks at 2bpp)
