# Archive and compression

## Resource archive ($85:8000, file 0x28000) - verified

- Category table: 40 entries x 4 bytes at file 0x28000: 24-bit LE offset (+1 pad) from 0x28000 to the category's
  directory. Code: `$82:A1B9` (offset is LoROM-linear: word + 0x8000, wrap into the next bank).
- Directory: word 0 = offset from the directory to its first block (= directory size), then one 16-bit size per
  block; trailing zero sizes are padding. Block i = dir + word0 + sum(size[0..i-1]) (`$82:A1FD`).
- Archive spans file 0x280A0-0xF8C5E. Blocks must sit back to back after their directory, so a grown block means
  moving its whole category (change the 24-bit table entry).
- A load request: `$0669` = category, `$066A` = index, then `JSR $82A321` (dest bank `$7E`: decompress, then the
  linear->planar pass below) or `JSR $82A22B` (decompress only). Wrappers: `$82:ACD5` (A = cat | idx<<8 -> `$7E:B800`),
  `$82:ACEB` (-> `$7E:E800`), `$82:AC7E` (-> `$7E:4000`), `$82:AC8D` (-> `$7E:B000`).
- `tools/archive.py list|dump` parses it. `unpack()` tells raw from packed by trial decode (some raw blocks still
  decode by chance, e.g. 01_001/01_003: the loader, not the data, decides).
- verified: decompressing 20_000/20_001 gives the exact WRAM bytes the game produced (RAM dump at frame 1954).

## LZ + Huffman codec ($82:A08B) - verified

Bit stream MSB first. 16-bit output size (0 = empty); 9-bit leaf count N and N 9-bit symbols; N-1 internal nodes
of two children each (bit 1 + 10-bit value sets a running counter, bit 0 reuses it; child < N = leaf, else node
child-N; root = node N-2). Symbols 0-255 literal, 256+k = copy k+3 bytes; after a copy, 1 bit picks a 10- or 7-bit
distance d, source = out - d - 1. Copies run through an MVN built at `$1600`. Python: `tools/lzh.py` (decompress +
compress; `--selftest` round-trips). Our greedy compressor is ~3-7% larger than the original packer.

## Linear 4bpp images ($82:A238) - verified

Loads with destination bank `$7E` (via `$82:A321`) decompress to dest+$200, then `$82:A238` converts packed pixels
(4bpp, high nibble first, 128 px = 16 tiles per row, 8 pixel rows per tile row) into SNES planar 4bpp at dest.
The title screen tiles (1A_001) are stored this way. `tools/sweep.py --linear` renders blocks in this format.
