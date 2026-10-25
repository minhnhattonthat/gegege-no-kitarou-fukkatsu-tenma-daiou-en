# Debug scenes

Every scene is reached from a cold boot by `tools/debug/warp.lua` (no route, no save):

    python -X utf8 "$(python tools/skill.py)/scripts/emu.py" build/kitarou_en.sfc --out work/qa/warp/<scene> \
      --script tools/debug/warp.lua --var "SCENE='<scene>'" --frames <frames> --shot-every 300 --sheet

`python -X utf8 tools/debug/tour.py [ROM] [--only a,b] [--jobs 3]` runs every row below, checks that the log has the
`warp:` arrival line, writes `work/qa/tour/<scene>/sheet.png` and saves `work/states/<scene>.mss` at the last frame
(regenerate after any code, font or graphics change). Opt-in globals: `GOD=1` pins health, `P2LR=1` holds P2 L+R
(the game's own stage-select unlock).

`python -X utf8 tools/debug/pages.py ROM` runs the caption scenes (intro, cut3, cut5-10) and keeps one shot per
caption page right after its reveal ends (`page end at fF` in the warp log): `work/qa/pages/pages.png`. Exit 1 if
any used page never finishes its reveal.

RAM: `$0539` main mode (4 attract/title, 5 chapter card, 6 options, 3 in game), `$11BD` stage index, `$11C3`
difficulty (0 easy, 1 normal), `$11D1` game flags (bit $8000 stage clear), `$004E` health (10 per hit).
Stage index: 0 = 0-1 (prologue), 1-4 = 1-1..1-4, 5-7 = 2-1..2-3, 8-12 = 3-1..3-5, 13-14 = 4-1..4-2,
15-16 = 5-1..5-2, 17 = 6-1, 18 = 6-2 (Tenma Daiou, normal difficulty only).

The tour reads the table below: `scene | frames | god | shows`. Keep it a single table.

| scene | frames | god | shows |
|---|---|---|---|
| intro | 6200 | 0 | attract: captions 20_003/004/065, intro scroll 20_001 (f1941-3106), captions 005/006/007 (G1, G2) |
| title | 900 | 0 | title screen with menu 一人でガンバル / 力を合わせる, copyright (G4-G6) |
| options | 900 | 0 | options screen 難易度 / 面選択 / 音楽 / 効果音 / 仲間の選択 (G7) |
| coop | 3000 | 0 | 2P co-op with 仲間の選択 on: prologue card, then partner select 仲間を選んでね (G8) |
| cut0 | 6200 | 0 | script 0 (attract): same as intro, through table patch path |
| cut3 | 2400 | 0 | script 3: captions 8, 9 |
| cut5 | 4000 | 0 | script 5: captions 48, 49, 10-14 |
| cut6 | 3500 | 0 | script 6: captions 15-19 |
| cut7 | 4500 | 0 | script 7: captions 52, 62, 63, 53, 21-24 |
| cut8 | 5000 | 0 | script 8: captions 25, 60, 61, 50, 26-31 |
| cut9 | 3500 | 0 | script 9: captions 56, 57, 54, 55 |
| cut10 | 11000 | 0 | script 10 (ending): captions 47, 33-45, 59, 58, 64, 51 |
| card0 | 1600 | 0 | 序章 card (G3) |
| card1 | 1600 | 0 | 第一章 card |
| card2 | 1600 | 0 | 第二章 card |
| card3 | 1600 | 0 | 第三章 card |
| card4 | 1600 | 0 | 第四章 card |
| card5 | 1600 | 0 | 第五章 card |
| card6 | 1600 | 0 | 最終章 card |
| stage0 | 3000 | 1 | 0-1 with its in-stage captions |
| stage1 | 3000 | 1 | 1-1 |
| stage2 | 3000 | 1 | 1-2 |
| stage3 | 3000 | 1 | 1-3 |
| stage4 | 3000 | 1 | 1-4 |
| stage5 | 3000 | 1 | 2-1 |
| stage6 | 3000 | 1 | 2-2 |
| stage7 | 3000 | 1 | 2-3 |
| stage8 | 3000 | 1 | 3-1 |
| stage9 | 3000 | 1 | 3-2 |
| stage10 | 3000 | 1 | 3-3 |
| stage11 | 3000 | 1 | 3-4 |
| stage12 | 3000 | 1 | 3-5 |
| stage13 | 3000 | 1 | 4-1 |
| stage14 | 3000 | 1 | 4-2 |
| stage15 | 3000 | 1 | 5-1 |
| stage16 | 3000 | 1 | 5-2 |
| stage17 | 3000 | 1 | 6-1 |
| stage18 | 3000 | 1 | 6-2 (Tenma Daiou) |
| boss0 | 1500 | 1 | boss-name banner of 0-1 (たんたん坊) under the playfield (G10, block 01_000), shown in 6-2 |
| boss1 | 1500 | 1 | banner of 1-1 |
| boss2 | 1500 | 1 | banner of 1-2 |
| boss3 | 1500 | 1 | banner of 1-3 |
| boss4 | 1500 | 1 | banner of 1-4 |
| boss5 | 1500 | 1 | banner of 2-1 |
| boss6 | 1500 | 1 | banner of 2-2 |
| boss7 | 1500 | 1 | banner of 2-3 |
| boss8 | 1500 | 1 | banner of 3-1 |
| boss9 | 1500 | 1 | banner of 3-2 |
| boss10 | 1500 | 1 | banner of 3-3 |
| boss11 | 1500 | 1 | banner of 3-4 |
| boss12 | 1500 | 1 | banner of 3-5 |
| boss13 | 1500 | 1 | banner of 4-1 |
| boss14 | 1500 | 1 | banner of 4-2 |
| boss15 | 1500 | 1 | banner of 5-1 |
| boss16 | 1500 | 1 | banner of 5-2 |
| boss18 | 1500 | 1 | banner of 6-2 (天魔大王) |
| clear0 | 4000 | 1 | 0-1 cleared: next stage's 第一章 card |
| gameover | 3600 | 0 | game over: ゲームオーバー / 復活する / 復活しない (G11, block 01_002) |
| ending | 16000 | 1 | 6-1 cleared on easy: ending captions, おわり, staff roll (G9), closing picture |

Not reachable yet: none known. Add a row whenever a bug report names a place the list can't reach.
