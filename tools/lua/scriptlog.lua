-- Log every cutscene-script opcode the VM fetches (exec $80:AB78, opcode in A, script address in Y, bank $81).
--   emu.py ... --script tools/lua/scriptlog.lua [--var FROM=N]
local from = FROM or 0
L.on_exec(0x80AB78, 0x80AB78, function()
  if L.frame < from then return end
  local s = emu.getState()
  L.log(string.format("f%d obj=%04X y=%04X op=%02X", L.frame, s["cpu.x"], s["cpu.y"], s["cpu.a"] & 0xFF))
end)
