-- Log every call of the game's LZ+Huffman decompressor ($82A08B): frame, caller X/DB, source, destination and
-- size override, read from the 18-byte descriptor at DB:X (see docs/re/compression.md).
--   emu.py ... --script tools/lua/declog.lua
local mem = emu.memType.snesMemory
local function rd(a) return emu.read(a, mem) end
L.on_exec(0x82A08B, 0x82A08B, function()
  local s = emu.getState()
  local x, db = s["cpu.x"], s["cpu.dbr"]
  local base = (db << 16) | x
  local function b(i) return rd(base + i) end
  local src = b(4) << 16 | b(3) << 8 | b(2)
  local dst = b(7) << 16 | b(6) << 8 | b(5)
  local size = b(0x10) << 8 | b(0x0F)
  local sp = s["cpu.sp"]
  local ret = rd(0x000000 + sp + 2) << 8 | rd(0x000000 + sp + 1)
  L.log(string.format("f%d desc=%02X:%04X src=%06X dst=%06X size=%04X ret=%04X", L.frame, db, x, src, dst, size, ret))
end)
