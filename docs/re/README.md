# Reverse-engineering notes

One file per subsystem. Mark every finding with how far it is proven, so a later session doesn't build on a guess:

- **verified** - and how: a decoded known string, a corrupt-and-boot test, a breakpoint hit on the drawing path, a
  passing roundtrip test. Name the test or savestate.
- **guess** - and why it seems likely. Promote it to verified before code depends on it.

Addresses are for the dump in `rom.sha1` (LoROM, 1 MiB, no SRAM, no copier header). File offset of a CPU address:
`((addr & 0x7F0000) >> 1) | (addr & 0x7FFF)`.

| File | Covers | State |
|---|---|---|
| compression.md | resource archive at $85:8000, LZ+Huffman codec, linear 4bpp image pass | verified |
| text.md | caption/intro tilemaps (category $20), cutscene script VM, script table, chapter variable | verified |
| graphics.md | survey of every tile-drawn Japanese element, with sources | verified (static sweep + tour) |
| layout.md | ROM map and free space | verified |
| ram.md | RAM map, game flow (stage clear, ending, game over), stage records + boss banners, debug warp | verified (warp tour) |

## Probes and helpers (repo `tools/`)

- `tools/lua/dmalog.lua`, `iowatch.lua`: I/O hooks in every bank. The game runs with DBR=$81, so `STA $420B`
  lands on `$81:420B`, which the skill's `snes_dmalog.lua`/`watch.lua` (banks $00/$80 only) never see.
- `tools/lua/ramwrites.lua` (every write to a WRAM range), `declog.lua` (every decompression: source, dest),
  `scriptlog.lua` (every cutscene opcode fetched).
- `tools/archive.py`, `tools/lzh.py`, `tools/render_map.py`, `tools/sweep.py`.
