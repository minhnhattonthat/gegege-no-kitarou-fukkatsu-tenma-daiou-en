"""lzh.py: the game's LZ + Huffman codec (decompressor at $82A08B; format in docs/re/compression.md).

Stream, bits MSB first:
  16 bits  output size (0 = empty stream)
   9 bits  N = number of leaf symbols, then N x 9-bit symbols (0-255 literal, 256+k = copy of k+3 bytes)
  N-1 internal nodes, each two children: bit 1 + 10-bit value sets a counter, bit 0 reuses it; the child is the
           counter, then the counter increments. Child < N is a leaf, else internal node (child - N). Root = node N-2.
  codes    walk from the root: bit 0 = first child, 1 = second. A copy symbol is followed by 1 bit
           (1: 10-bit distance, 0: 7-bit) d, source = out_pos - d - 1.

    python -X utf8 tools/lzh.py dec ROM SNESADDR OUT.bin     # decompress one block
    python -X utf8 tools/lzh.py --selftest
"""
import heapq
import sys


def lorom(addr):
    return ((addr & 0x7F0000) >> 1) | (addr & 0x7FFF)


class BitReader:
    """Reads ROM bytes MSB first; crosses LoROM banks like the game (Y wraps to $8000, bank+1)."""

    def __init__(self, rom, addr):
        self.rom, self.addr, self.n, self.cur = rom, addr, 0, 0

    def bit(self):
        if self.n == 0:
            self.cur = self.rom[lorom(self.addr)]
            self.addr += 1
            if self.addr & 0xFFFF == 0:
                self.addr += 0x8000  # next bank, offset $8000
            self.n = 8
        self.n -= 1
        return (self.cur >> self.n) & 1

    def bits(self, k):
        v = 0
        for _ in range(k):
            v = (v << 1) | self.bit()
        return v


def decompress(rom, addr, size_override=0):
    """Return (data, end_addr). end_addr = first byte after the last one read."""
    r = BitReader(rom, addr)
    size = r.bits(16)
    if size == 0:
        return b"", r.addr
    if size_override:
        size = size_override
    n = r.bits(9)
    syms = [r.bits(9) for _ in range(n)]
    left, right, cnt = [], [], 0
    for _ in range(n - 1):
        pair = []
        for _ in range(2):
            if r.bit():
                cnt = r.bits(10)
            pair.append(cnt)
            cnt += 1
        left.append(pair[0])
        right.append(pair[1])
    out = bytearray()
    while len(out) < size:
        node = n - 2
        while True:
            child = right[node] if r.bit() else left[node]
            if child < n:
                sym = syms[child]
                break
            node = child - n
        if sym < 0x100:
            out.append(sym)
        else:
            length = sym - 0xFD
            d = r.bits(10) if r.bit() else r.bits(7)
            src = len(out) - d - 1
            for i in range(length):
                out.append(out[src + i])
    return bytes(out[:size]), r.addr


class BitWriter:
    def __init__(self):
        self.out, self.cur, self.n = bytearray(), 0, 0

    def bits(self, v, k):
        for i in range(k - 1, -1, -1):
            self.cur = (self.cur << 1) | ((v >> i) & 1)
            self.n += 1
            if self.n == 8:
                self.out.append(self.cur)
                self.cur, self.n = 0, 0

    def done(self):
        if self.n:
            self.out.append(self.cur << (8 - self.n))
        return bytes(self.out)


MAXLEN = 0x1FF - 0xFD  # 9-bit symbol 0x1FF -> 258 bytes


def _tokens(data):
    """Greedy LZ parse with hash chains: list of ('L', byte) / ('C', length, dist)."""
    toks, i, heads = [], 0, {}
    n = len(data)
    while i < n:
        best, bestd = 0, 0
        if i + 3 <= n:
            for j in reversed(heads.get(data[i:i + 3], [])):
                d = i - j - 1
                if d >= 1024:
                    break
                k = 0
                while i + k < n and k < MAXLEN and data[j + k] == data[i + k]:
                    k += 1
                if k > best:
                    best, bestd = k, d
                    if k == MAXLEN:
                        break
        step = best if best >= 3 else 1
        toks.append(("C", best, bestd) if best >= 3 else ("L", data[i]))
        for p in range(i, i + step):
            if p + 3 <= n:
                heads.setdefault(data[p:p + 3], []).append(p)
        i += step
    return toks


def compress(data):
    """Encode `data` in the game's format. Round-trips through decompress()."""
    w = BitWriter()
    w.bits(len(data), 16)
    if not data:
        return w.done()
    toks = _tokens(data)
    freq = {}
    for t in toks:
        s = t[1] if t[0] == "L" else 0xFD + t[1]
        freq[s] = freq.get(s, 0) + 1
    if len(freq) == 1:  # the tree needs two leaves
        freq[0 if 0 not in freq else 1] = 0
    syms = sorted(freq)
    n = len(syms)
    # Huffman: leaves 0..n-1, internal nodes n.. in creation order; root is the last one created = node n-2.
    heap = [(freq[s], i, i) for i, s in enumerate(syms)]
    heapq.heapify(heap)
    left, right, tie = [], [], n
    while len(heap) > 1:
        fa, _, a = heapq.heappop(heap)
        fb, _, b = heapq.heappop(heap)
        left.append(a)
        right.append(b)
        heapq.heappush(heap, (fa + fb, tie, n + len(left) - 1))
        tie += 1
    codes = {}

    def walk(node, code, ln):
        if node < n:
            codes[syms[node]] = (code, ln)
            return
        k = node - n
        walk(left[k], code << 1, ln + 1)
        walk(right[k], (code << 1) | 1, ln + 1)

    walk(2 * n - 2, 0, 0)
    w.bits(n, 9)
    for s in syms:
        w.bits(s, 9)
    cnt = 0
    for k in range(n - 1):
        for child in (left[k], right[k]):
            if child == cnt:
                w.bits(0, 1)
            else:
                w.bits(1, 1)
                w.bits(child, 10)
            cnt = child + 1
    for t in toks:
        s = t[1] if t[0] == "L" else 0xFD + t[1]
        code, ln = codes[s]
        w.bits(code, ln)
        if t[0] == "C":
            d = t[2]
            if d < 128:
                w.bits(0, 1)
                w.bits(d, 7)
            else:
                w.bits(1, 1)
                w.bits(d, 10)
    return w.done()


def _selftest():
    import random
    rnd = random.Random(1)
    for data in [b"a", b"ab" * 300, bytes(rnd.randrange(4) for _ in range(5000)), bytes(range(256)) * 9, b"\0" * 4000]:
        c = compress(data)
        blob = bytearray(0x8000)
        blob[:len(c)] = c
        got, _ = decompress(bytes(blob), 0x808000)
        assert got == data, len(data)
    print("lzh selftest ok")


if __name__ == "__main__":
    if sys.argv[1:2] == ["--selftest"]:
        _selftest()
    elif sys.argv[1:2] == ["dec"]:
        rom = open(sys.argv[2], "rb").read()
        data, end = decompress(rom, int(sys.argv[3], 16))
        open(sys.argv[4], "wb").write(data)
        print(f"{len(data)} bytes, stream ends at {end:06X}")
    else:
        sys.exit(__doc__)
