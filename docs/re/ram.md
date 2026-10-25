# RAM, game flow and the debug warp

All verified by `tools/debug/warp.lua` runs (`tools/debug/tour.py`, phase 2) unless marked guess.

| Address | Meaning | How verified |
|---|---|---|
| `$7E:0539` | main mode: 4 attract/title, 5 chapter card / stage intro, 6 options, 3 in game (also game over) | RAM dumps across modes; every warp waits on it |
| `$7E:11BD` | stage index 0..18 (0 = 0-1 ... 17 = 6-1, 18 = 6-2); the options 面選択 row edits it | options stage select + ramsearch; writing it at the title starts that stage with its chapter card |
| `$7F:3FF4` | copy of the options stage pick | changes with `$11BD` in options |
| `$7E:11C3` | difficulty, 0 easy / 1 normal (guess from the `$80:8193` branch: on 0, clearing 6-1 ends the game) | `ending` warp ends after 6-1 with 0 |
| `$7E:11D1` | game flags: bit $8000 stage clear, $4000 stage end (with $0800: game over path), $0400 in stage | `clear0` warp |
| `$7E:004E` | Kitaro's health, 10 per hit (90-100 at stage start) | ramsearch while idling in 4-1; GOD pin keeps the bar full |
| `$7E:00EF/F1` | P1 / P2 joypad held (`$80:86ED` reads `$4218`/`$421A`); `$F3/$F5` newly pressed | P2 L+R at the title unlocks the options stage select |
| `$7E:0669/066A` | archive load request: category, index | `$82:A321` / `$82:A22B` |

## Flow

- Options: title + Select. 面選択 shows 0-1 and is locked unless P2 holds L+R when Select is pressed (the known
  cheat). Mesen's `--testRunner` gives no port-2 input (`emu.setInput(x, 1)` lands on P1), so warp.lua writes `$F1`
  after the joypad read instead.
- In-game loop calls `$80:816F` every frame once the HUD is up: `$11D1` bit $8000 set -> if `$11C3` = 0 and
  `$11BD` = 17: `$82:B1D9` (ending cutscene, script with `$F9` = 7) then `$82:BF11` (staff roll: loads 24_004,
  24_000, 24_001, 24_002 glyphs, 24_003 map); else `INC $11BD` and load the next stage (card when a chapter starts).
  The normal path sets the flag at `$80:8F0C` (stage goal, `$80:8EA7`), `$80:9BD3`, `$82:C685` (boss death).
- 6-2's boss death runs `$82:DCA8` -> `$82:B1D9` + `$82:BF11` directly.
- Game over: health 0 -> screen with ゲームオーバー / 復活する / 復活しない, glyphs from raw block 01_002 DMA'd to VRAM
  $4C00 (`$80:8391`).

## Stage records and boss banners (G10)

Bank $82 holds one record per stage; each has a word pointer into raw block 01_000 (`$85:AC3A-$85:C039`) followed by
`$DD` and a length-like byte ($84-$8B). When the stage's boss appears, 0x200 bytes from the pointer are DMA'd to VRAM
$5008 and the name shows as a banner under the playfield (6-2: 天魔大王 at once). Pointer locations:

| Stage | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|---|
| record | 8D09 | 8D23 | 8D3B | 8D51 | 8D73 | 8D95 | 8DAF | 8DD1 | 8DE7 | 8DFD |
| 01_000 offset | 000 | 2C0 | 140 | 380 | 440 | 580 | 600 | 640 | 700 | 900 |

| Stage | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18 |
|---|---|---|---|---|---|---|---|---|---|
| record | 8E13 | 8E29 | 8E3F | 8E55 | 8E6F | 8E85 | 8EA7 | (FF FF: no banner) | 8ED3 |
| 01_000 offset | A40 | B80 | C00 | 1240 | DC0 | E40 | F40 | - | 1140 |

Banners read in the `boss0`..`boss18` tour shots: 0 たんたん坊, 1 白山坊, 2 がしゃどくろ, 3 山天狗, 4 見上げ入道,
5 水虎, 6 雷, 7 だるま, 8 フランケンシュタイン, 9 オオカミ男, 10 ドラキュラ, 11 魔女, 12 バックベアード,
13 やまたのおろち, 14 天狐, 15 and 16 an invented alien script (not Japanese), 18 天魔大王.

The `bossN` warp copies record N's 4 bytes over 6-2's at frame 1. Strip format (glyph layout, what the length byte
means) is for phase 5.
