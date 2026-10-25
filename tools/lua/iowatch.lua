-- SNES (Mesen): log every write to an I/O register range, hooked in every bank ($00-$3F, $80-$BF): this game
-- writes I/O with DBR=$81. One line per write: frame, pc, register, value. Use a narrow frame window.
--   emu.py ... --script tools/lua/iowatch.lua --var IO_LO=0x2181 --var IO_HI=0x2183 --var FROM=N --var TO=M
local mem = emu.memType.snesMemory
local lo, hi = assert(IO_LO, "set --var IO_LO"), IO_HI or IO_LO
local from, to = FROM or 0, TO or math.huge
local function cb(addr, value)
  if L.frame < from or L.frame > to then return end
  L.log(string.format("f%d pc=%06X %04X=%02X", L.frame, L.pc(), addr & 0xFFFF, value))
end
for bank = 0, 0xBF do
  if bank < 0x40 or bank >= 0x80 then
    emu.addMemoryCallback(L.safe(cb), emu.callbackType.write, (bank << 16) | lo, (bank << 16) | hi,
      emu.cpuType.snes, mem)
  end
end
