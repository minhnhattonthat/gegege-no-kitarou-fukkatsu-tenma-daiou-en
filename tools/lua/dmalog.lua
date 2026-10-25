-- SNES (Mesen): DMA log hooked in every bank. This game runs with DBR=$81, so `STA $420B` lands on $81:420B,
-- which the skill's snes_dmalog.lua (banks $00/$80 only) never sees. Same output format.
--   emu.py ... --script tools/lua/dmalog.lua [--var FROM=N --var TO=M] [--var SRC_LO=0x7E0000 --var SRC_HI=0x7FFFFF]
local mem = emu.memType.snesMemory
local lo, hi = SRC_LO or 0, SRC_HI or 0xFFFFFF
local from, to = FROM or 0, TO or math.huge
local function rd(a) return emu.read(a, mem) end
local function cb(addr, value)
  if L.frame < from or L.frame > to then return end
  for ch = 0, 7 do
    if value & (1 << ch) ~= 0 then
      local b = 0x4300 + ch * 16
      local src = rd(b + 4) << 16 | rd(b + 3) << 8 | rd(b + 2)
      if src >= lo and src <= hi then
        local s = emu.getState()
        L.log(string.format("f%d pc=%06X ch%d src=%06X n=%04X bbus=21%02X vram=%04X", L.frame,
          (s["cpu.k"] << 16) | s["cpu.pc"], ch, src, rd(b + 6) << 8 | rd(b + 5), rd(b + 1), s["ppu.vramAddress"]))
      end
    end
  end
end
for bank = 0, 0xBF do
  if bank < 0x40 or bank >= 0x80 then
    emu.addMemoryCallback(L.safe(cb), emu.callbackType.write, (bank << 16) | 0x420B, (bank << 16) | 0x420B,
      emu.cpuType.snes, mem)
  end
end
