-- SNES (Mesen): log the first MAX writes (no dedupe) to a WRAM range: frame, pc, address, value.
--   emu.py ... --script tools/lua/ramwrites.lua --var LO=0x7EB800 --var HI=0x7EBFFF [--var MAX=64] [--var FROM=N]
local lo, hi = assert(LO, "set --var LO"), HI or LO
local max, from, n = MAX or 64, FROM or 0, 0
-- WRAM is hooked as work RAM (catches $00:0000-1FFF mirror writes too); the logged pc is after the store.
L.on_write(lo, hi, function(a, v)
  if L.frame < from or n >= max then return end
  n = n + 1
  local s = emu.getState()
  L.log(string.format("f%d pc=%02X%04X a=%06X v=%02X A=%04X X=%04X Y=%04X DB=%02X D=%04X", L.frame, s["cpu.k"],
    s["cpu.pc"], a, v, s["cpu.a"], s["cpu.x"], s["cpu.y"], s["cpu.dbr"], s["cpu.d"]))
end)
