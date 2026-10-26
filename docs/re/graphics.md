# Graphics-text survey

Every Japanese element drawn with tiles. Since the game has no text engine, this list is also the whole script.
Sources: static sweep of every archive block (`tools/sweep.py`, planar 4bpp pages in `work/re/sweep4/`, linear
pages in `work/re/sweepL/`, read by visual-qa subagents; verdict files beside the pages) plus the attract/title
tour. Formats: planar = SNES 2/4bpp tiles; linear = packed 4bpp, converted by `$82:A238` (compression.md).

| # | Screen | Block(s) | Format | How it is shown | Warp (phase 2) | Plan |
|---|---|---|---|---|---|---|
| G1 | intro scroll (letter from Yumeko) | 20_000 glyphs + 20_001 map | planar 2bpp + 32x64 map | BG3, attract | `intro` | script: re-render |
| G2 | 63 caption pages (all cutscene dialogue) | 20_002 glyphs + 20_003..065 maps | planar 2bpp + 32x8 maps | BG3 via script `E8 nn 25` / `EB 7B ED` | `cut0`..`cut10` | script: re-render |
| G3 | chapter cards 序章, 第一章..第五章, 最終章 | 20_066 glyphs + 20_067 map | planar 2bpp, 12x4 tiles per card | BG3, `$82:BB07`, row = `$11BD` | `card0`..`card6` | redraw: Prologue / Chapter 1..5 / Final Chapter |
| G4 | title menu 一人でガンバル / 力を合わせる | 1A_001 (and 22_002 scroll sprite) | linear 4bpp | BG1 title screen | `title` | redraw: 1 Player / 2 Players (co-op) |
| G5 | title copyright ©水木プロ・東映動画 | 1A_001 | linear 4bpp | BG1 title | `title` | redraw: (c) Mizuki Pro / Toei Animation |
| G6 | title logo ゲゲゲの鬼太郎 / 復活!天魔大王 | 1A_001 | linear 4bpp | BG1 title | `title` | keep Japanese (no official English logo; D5) |
| G7 | options menu 難易度 (難しい / ふつう / 易しい) / 面選択 / 音楽 / 効果音 / 仲間の選択 (する / しない) | 27_004 glyphs (+ 27_005 map) | planar 2bpp | title + Select | `options` | re-render glyphs + map |
| G8 | partner select: names and moves (子泣きじじい, 砂かけばばあ, ねずみ男, シーサー, 地獄童子, 必殺技, 火炎, 突進, おなら, 仲間を...) | 1C_000 | linear 4bpp | partner screen 仲間を選んでね: 2P co-op with option 仲間の選択 on, after the card | `coop` | redraw labels |
| G9 | staff roll (監督, 演出, プログラム, ... names, 水木しげる, 東映動画, バンダイ; INTERBEC logo); also おわり after the ending captions | 24_002 glyphs (+ 24_000/001/003/004, `$82:BF11`) | planar 2bpp | after the ending | `ending` | English credits (D3), romanised names |
| G10 | boss-name banners (たんたん坊 ... フランケンシュタイン ... 天魔大王), one strip per boss | 01_000 (raw) | planar 2bpp | DMA to VRAM $5008 when the boss appears; pointer in each stage record (ram.md) | `boss0`..`boss18` | re-render strips |
| G11 | game over ゲームオーバー / 復活する / 復活しない | 01_002 (raw) | planar 2bpp | DMA to VRAM $4C00 | `gameover` | re-render |
| G12 | shop signs テレビ, さくらや, NIPPO in a city cutscene | 18_013 | linear 4bpp | cutscene background | `cut10` (city shot; guess, confirm zoomed) | テレビ -> TV; store names kept (non-blocking, status.md) |
| G14 | HUD icon 鬼 (left box of the status bar) | 01_003 (raw, 4096 bytes; the archive list misreads it as packed) block tiles $2E/$2F/$3E/$3F | planar 4bpp, BG2 palette 7 (2 stone, 7 engraved ink) | DMA to VRAM $5000 (BG2 tiles $280+), map at $7800 rows 25-26 cols 2-3 | every stage | redraw ONI (D8) |
| G15 | in-stage dialogue, 28 one-line strips (「お前を未来に / いかせるわけには / いかない」 in the prologue, ...) | 01_001 (raw, 12224 bytes; the archive list misreads it as packed, which is why the first survey missed it) | planar 2bpp, G10 strip format | event lists `$81:8562-$81:870B` run by `$80:A4F4` (text.md) | `stage0` f2300-2420 (the others are deep in stages) | redrawn (`labels.dialogue`) |
| G13 | possible small sign on Kitaro's house | 1E_003 | linear 4bpp | intro picture | `intro` | check zoomed in the tour |

Not text (checked): level art, sprites, 1A_000 brush texture (check zoomed in the tour), 13_000 roof marks.
Unassessed: raw blocks that are neither planar nor linear art (categories 25/26 data); the marker tour (phase 5)
catches anything the sweep missed.
