-- Debug warp: cold boot to any scene in tools/debug/scenes.md. No route needed; this script presses the buttons.
--   emu.py rom/kitarou.sfc --out work/qa/warp --script tools/debug/warp.lua --var "SCENE='stage13'" --frames 2400 --sheet
-- Opt-in: --var GOD=1 (pin Kitaro's health), --var P2LR=1 (unlock stage select in the options screen).
-- Waits on RAM, not frame counts: $7E:0539 = main mode (4 attract/title, 5 chapter card, 6 options, 3 in game);
-- the title script is running once the script VM reads table entry 1 ($81:B883). The log line "arrived: ..."
-- marks arrival (tools/debug/tour.py checks it).
local m, prg = emu.memType.snesMemory, emu.memType.snesPrgRom
local SC = assert(SCENE, "set --var \"SCENE='name'\"")
local function mode() return emu.read(0x0539, m) end

-- First stage index ($11BD) of each chapter: 0 = 0-1 (prologue) ... 17 = 6-1, 18 = 6-2 (Tenma Daiou).
local CARD = { [0] = 0, 1, 5, 8, 13, 15, 17 }
-- Cutscene script table entries ($81:B881, 11 words); cutN makes the attract sequence play entry N.
local TABLE = 0xB881

local plan = {}  -- what this scene needs: new game (stage), options, title, cutscene patch, plain attract
local n = SC:match("^stage(%d+)$"); if n then plan.stage = tonumber(n) end
n = SC:match("^card(%d)$"); if n then plan.stage = assert(CARD[tonumber(n)], "card0..card6") end
n = SC:match("^cut(%d+)$"); if n then plan.cut = tonumber(n) end
if SC == "title" or SC == "options" then plan[SC] = true end
if SC == "coop" then plan.coop = { "down", "down", "down", "down", "right", "start:200", "down", "start" } end
-- clearN: play stage N, then raise the stage-clear flag ($11D1 bit $8000) that the in-game loop checks every
-- frame at $80:816F once the HUD is up (health > 0): it loads the next stage. Clearing stage 17 (6-1) with
-- $11C3 = 0 runs the ending cutscene ($82:B1D9) and the staff roll ($82:BF11).
n = SC:match("^clear(%d+)$"); if n then plan.stage, plan.clear = tonumber(n), 0 end
if SC == "ending" then plan.stage, plan.clear, plan.easy = 17, 0, true end
-- bossN: boss-name banner of stage N (G10, block 01_000). Each stage record in bank $82 holds a word pointer into
-- 01_000 ($85:AC3A-$85:C039) + 2 bytes; 6-2 (stage 18) shows its banner at once, so play 6-2 with its record
-- (PRG $82:8ED3) swapped for stage N's. 6-1 (17) has no banner.
local BANNER = { [0] = 0x8D09, 0x8D23, 0x8D3B, 0x8D51, 0x8D73, 0x8D95, 0x8DAF, 0x8DD1, 0x8DE7, 0x8DFD, 0x8E13,
  0x8E29, 0x8E3F, 0x8E55, 0x8E6F, 0x8E85, 0x8EA7, nil, 0x8ED3 }
n = SC:match("^boss(%d+)$"); if n then plan.stage, plan.boss = 18, assert(BANNER[tonumber(n)], "boss0..16, boss18") end
if SC == "gameover" then plan.stage, plan.die = 13, true end  -- 4-1: fireballs hit a Kitaro who stands still
if SC ~= "intro" and not next(plan) then error("unknown SCENE " .. SC .. " (see tools/debug/scenes.md)") end

-- Call fn(src) when a DMA reads from ROM src_lo..src_hi (raw archive blocks go straight to VRAM). The game
-- writes $420B with DBR=$81, so hook every bank mirror.
local function on_dma(lo, hi, fn)
  local function cb(_, v)
    for ch = 0, 7 do
      if v & (1 << ch) ~= 0 then
        local b = 0x4300 + ch * 16
        local src = emu.read(b + 4, m) << 16 | emu.read(b + 3, m) << 8 | emu.read(b + 2, m)
        if src >= lo and src <= hi then fn(src) end
      end
    end
  end
  for bank = 0, 0xBF do
    if bank < 0x40 or bank >= 0x80 then
      emu.addMemoryCallback(L.safe(cb), emu.callbackType.write, bank << 16 | 0x420B, bank << 16 | 0x420B,
        emu.cpuType.snes, m)
    end
  end
end

-- Call fn(idx) when the game loads archive block cat_idx (idx nil = any) through its loaders ($82:A321 /
-- $82:A22B read the request from $0669 = category, $066A = index; docs/re/compression.md).
local function on_load(cat, idx, fn)
  local function cb()
    local i = emu.read(0x066A, m)
    if emu.read(0x0669, m) == cat and (idx == nil or i == idx) then fn(i) end
  end
  L.on_exec(0x82A321, 0x82A321, cb)
  L.on_exec(0x82A22B, 0x82A22B, cb)
end

local press, hold, gap, titled, arrived = nil, 0, 0, false, false
L.on_read(0x81B883, 0x81B883, function() titled = true end)
emu.addEventCallback(L.safe(function()
  if press then emu.setInput(press, 0) end
end), emu.eventType.inputPolled)
-- Hold a button for 6 frames, then release for `g` frames before the next decision.
local function tap(b, g) press, hold, gap = { [b] = true }, 6, g or 34 end
local function arrive(what)
  if not arrived then arrived = true; L.log(string.format("arrived: %s at f%d mode=%d", what, L.frame, mode())) end
end
-- Every caption page / intro scroll load is logged; a cutN or intro run arrives with its first one.
on_load(0x20, nil, function(i)
  if i >= 1 and i ~= 2 and i < 66 then
    L.log(string.format("caption 20_%03d at f%d", i, L.frame))
    if plan.cut or SC == "intro" then arrive("text block 20_" .. string.format("%03d", i)) end
  end
end)
if plan.coop then on_load(0x1C, 0, function() arrive("partner select (1C_000 loaded)") end) end
on_dma(0x85AC3A, 0x85C039, function(src)
  L.log(string.format("boss banner $85:%04X at f%d", src & 0xFFFF, L.frame))
  if plan.boss then arrive("boss banner") end
end)
if plan.clear then L.on_exec(0x82BF11, 0x82BF11, function() arrive("staff roll ($82:BF11)") end) end
if plan.die then on_dma(0x85EFFA, 0x85EFFA, function() arrive("game over (01_002 -> VRAM)") end) end

if P2LR then  -- P2 holding L+R at the title: the game's own stage-select cheat. Mesen's testRunner has no
  -- port 2 input, so write the game's P2 joypad mirror ($F1) right after its read ($80:86FC).
  L.on_exec(0x80870B, 0x80870B, function() if not arrived then emu.write(0xF1, 0x30, m) end end)
end
if GOD then
  local top = 0  -- $4E = health, 10 per hit; pin it at the stage's starting value
  L.on_frame(function()
    local hp = emu.read(0x004E, m)
    if mode() ~= 3 or hp == 0 then top = 0 elseif hp > top then top = hp elseif hp < top then emu.write(0x004E, top, m) end
  end)
end

L.on_frame(function(f)
  if f == 1 and plan.boss then
    local function off(a) return 0x10000 | (a & 0x7FFF) end  -- bank $82 -> PRG offset
    for i = 0, 3 do emu.write(off(0x8ED3) + i, emu.read(off(plan.boss) + i, prg), prg) end
  end
  if f == 1 and plan.cut then
    local a = emu.read(TABLE + 2 * plan.cut, prg) | emu.read(TABLE + 2 * plan.cut + 1, prg) << 8
    emu.write(TABLE, a & 0xFF, prg); emu.write(TABLE + 1, a >> 8, prg)
    L.log(string.format("note: attract plays script %d ($81:%04X)", plan.cut, a))
  end
  if hold > 0 then hold = hold - 1; if hold == 0 then press = nil end; return end
  if gap > 0 then gap = gap - 1; return end
  if arrived or plan.cut or SC == "intro" then return end
  local md = mode()
  if md == 0 then return end  -- boot
  if not titled then tap("start"); return end
  if plan.title then arrive("title"); return end
  if plan.options then
    if md == 6 then arrive("options") else tap("select") end
    return
  end
  if plan.coop then  -- options: 仲間の選択 -> する, back to the title, 力を合わせる; the partner screen follows the card
    if not plan.inopt then
      if md == 6 then plan.inopt, gap = true, 120 else tap("select") end
      return
    end
    local s = table.remove(plan.coop, 1)
    if s then local b, g = s:match("(%a+):?(%d*)"); tap(b, tonumber(g) or 40) end
    return
  end
  if plan.stage then
    if md == 4 then emu.write(0x11BD, plan.stage, m); tap("start", 60); return end
    if plan.die then  -- health 10; the next hit ends the game
      if md == 3 and not plan.died and emu.read(0x004E, m) > 10 then emu.write(0x004E, 10, m); plan.died = true end
      return
    end
    if plan.boss then return end
    if plan.clear then  -- 120 frames after the HUD comes up, flag the stage cleared
      if md == 5 and plan.clear >= 120 and not plan.easy then arrive("next stage card, $11BD=" .. emu.read(0x11BD, m)) end
      if md == 3 and emu.read(0x004E, m) > 0 then
        plan.clear = plan.clear + 1
        if plan.clear == 120 then
          L.log(string.format("note: stage %d cleared at f%d ($11C3=%d)", plan.stage, f, emu.read(0x11C3, m)))
          if plan.easy then emu.write(0x11C3, 0, m) end  -- easy mode: the game ends after 6-1
          emu.write(0x11D2, emu.read(0x11D2, m) | 0x80, m)
        end
      end
      return
    end
    if md == 5 or md == 3 then arrive("stage " .. plan.stage .. " $11BD=" .. emu.read(0x11BD, m)) end
  end
end)
