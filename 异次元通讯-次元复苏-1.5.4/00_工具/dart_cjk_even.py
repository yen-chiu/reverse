import sys
sys.stdout.reconfigure(encoding='utf-8')
p = r'C:\03_Github\reverse\异次元通讯-次元复苏-1.5.4\02_解包\lib\arm64-v8a\libapp.so'
b = open(p, 'rb').read()
def is_cjk_cp(c): return 0x4e00 <= c <= 0x9fff or 0x3400 <= c <= 0x4dbf
def is_print_cp(c):
    return ((0x20 <= c <= 0x7e) or is_cjk_cp(c) or (0x3000 <= c <= 0x303f)
            or (0xff00 <= c <= 0xffef) or (0x2000 <= c <= 0x27bf) or c in (0x0a, 0x0d, 0x09))
runs = []
i = 0
n = len(b)
while i + 1 < n:
    c = b[i] | (b[i+1] << 8)
    if is_cjk_cp(c):
        start = i
        s = []
        j = i
        while j + 1 < n:
            cc = b[j] | (b[j+1] << 8)
            if is_print_cp(cc):
                s.append(chr(cc)); j += 2
            else:
                break
        txt = ''.join(s)
        if len(txt) >= 8:
            runs.append((start, txt))
        i = j if len(txt) >= 8 else i + 2
    else:
        i += 2
print('runs starting with CJK, len>=8:', len(runs))
def near(off, w=6000):
    for o, s in runs:
        if abs(o - off) <= w:
            print('%08x len=%-5d %r' % (o, len(s), s[:220]))
print('=== around 0x2a11e')
near(0x2a11e)
