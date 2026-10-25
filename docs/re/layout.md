# ROM layout and free space

| File range | CPU | Contents | State |
|---|---|---|---|
| 0x00000-0x27FFF | $80:8000-$84:FFFF | code and tables (banks $80-$84); header at 0x7FC0 | verified (disassembly) |
| 0x28000-0xF8C5D | $85:8000-$9F:8C5D | resource archive (40 categories), see compression.md | verified |
| 0xF8C5E-0xFFFFF | $9F:8C5E-$9F:FFFF | not parsed yet (after the last category; probably sound data) | guess |

Header: `SFX GEGEGENOKITARO 1`, map mode $30 (LoROM, FastROM), ROM size $0A (1 MiB), no SRAM, maker $B2 (Bandai),
checksum $52CF / complement $AD30.

## Free space

No runs of 0x00/0xFF longer than 0x10A bytes inside the 1 MiB image (the longest: 0x1DEF6 len 0x10A, 0x3A543 len
0x141 - both in code/data banks, not trusted). Plan: expand to 2 MiB (header size byte -> $0B; banks $A0-$BF become
free, filled with 0xFF) and move the rebuilt category $20 (and any other grown category) there by rewriting its
24-bit entry in the category table at 0x28000. The archive pointer math (`$82:A1B9`) handles any LoROM-linear offset
past 0xD8000 (file 0x100000 = `$A0:8000`).
