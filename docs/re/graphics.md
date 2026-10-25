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
| G7 | options menu 難易度 / 画面? / 音楽 / 効果音 / 仲間選択 / ふつう / なし ... | 27_004 glyphs (+ 27_005 map) | planar 2bpp | title + Select | `options` | re-render glyphs + map |
| G8 | partner select: names and moves (子泣きじじい, 砂かけばばあ, ねずみ男, シーサー, 地獄童子, 必殺技, 火炎, 突進, おなら, 仲間を...) | 1C_000 | linear 4bpp | partner screen (2P / 仲間 option) | to find | redraw labels |
| G9 | staff roll (監督, 演出, プログラム, ... names, 水木しげる, 東映動画, バンダイ; INTERBEC logo) | 24_002 glyphs (+ 24_00x maps) | planar 2bpp | after the ending | to find | English credits (D3), romanised names |
| G10 | 16x16 glyph set with フランケンシュタイン, kana, alien glyphs | 01_000 (raw) | planar 2bpp | not seen yet (boss names?) | to find | re-render |
| G11 | kana/kanji glyph halves (ゲ ム オ ト ノ パ す な い) | 01_002 (raw) | planar 2bpp | not seen yet (game over / continue?) | to find | re-render |
| G12 | shop signs テレビ, さくらや, NIPPO in a city cutscene | 18_013 | linear 4bpp | cutscene background | a cut scene | テレビ -> TV; store names kept (non-blocking, status.md) |
| G13 | possible small sign on Kitaro's house | 1E_003 | linear 4bpp | intro picture | `intro` | check zoomed in the tour |

Not text (checked): level art, sprites, 1A_000 brush texture (check zoomed in the tour), 13_000 roof marks.
Unassessed: raw blocks that are neither planar nor linear art (categories 25/26 data); the marker tour (phase 5)
catches anything the sweep missed.
