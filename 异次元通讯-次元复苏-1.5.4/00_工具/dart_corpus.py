# -*- coding: utf-8 -*-
"""从 libapp.so 提取干净的 UTF-16LE 中文文案。

扫描产生的原始串里混有大量"错位噪声"（把 ASCII 串按 UTF-16 读出的颠倒字母），
用两条启发式过滤：出现中文标点或高频汉字，且汉字占比 ≥ 0.6。
"""
import re, sys, collections

sys.stdout.reconfigure(encoding='utf-8')
P = r'C:\03_Github\reverse\异次元通讯-次元复苏-1.5.4\02_解包\lib\arm64-v8a\libapp.so'
OUT = r'C:\03_Github\reverse\异次元通讯-次元复苏-1.5.4\03_反编译\dart_中文文案_清洗.txt'
OUT2 = r'C:\03_Github\reverse\异次元通讯-次元复苏-1.5.4\03_反编译\dart_释义候选.txt'

b = open(P, 'rb').read()
n = len(b)

CJK = re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff]')
PUNCT = set('，。！？：；、“”‘’（）《》…—～·「」【】')
COMMON = set('的了吗呢吧啊你我是他她它在不有就都也很要会这那什么怎')
PRINT_OK = re.compile(r'[\u0020-\u007e\u3000-\u303f\u4e00-\u9fff\uff00-\uffef\u2000-\u27bf\n\r\t]')


def scan():
    i = 0
    while i + 1 < n:
        c = b[i] | (b[i + 1] << 8)
        if 0x4e00 <= c <= 0x9fff or 0x3400 <= c <= 0x4dbf:
            out = []
            j = i
            while j + 1 < n:
                cc = b[j] | (b[j + 1] << 8)
                if PRINT_OK.match(chr(cc)):
                    out.append(chr(cc))
                    j += 2
                else:
                    break
            if len(out) >= 4:
                yield i, ''.join(out)
            i = j if j > i else i + 2
        else:
            i += 2


def clean(s):
    s = s.strip('\x00 \t\r\n')
    if len(s) < 4:
        return False
    cj = len(CJK.findall(s))
    if cj / len(s) < 0.6:
        return False
    has_punct = any(ch in PUNCT for ch in s)
    has_common = any(ch in COMMON for ch in s)
    return has_punct or has_common


runs = [(o, s) for o, s in scan()]
good = {}
for o, s in runs:
    if clean(s):
        good.setdefault(s, o)

items = sorted(good.items(), key=lambda kv: kv[1])
with open(OUT, 'w', encoding='utf-8') as f:
    for s, off in items:
        f.write('%08x\t%s\n' % (off, s))

prose = [(s, o) for s, o in items if 12 <= len(s) <= 400 and len(CJK.findall(s)) / len(s) >= 0.55]
with open(OUT2, 'w', encoding='utf-8') as f:
    for s, o in prose:
        f.write('%08x\t%s\n' % (o, s))

print('原始串 %d 条，清洗后唯一中文串 %d 条' % (len(runs), len(items)))
print('其中 12–400 字、汉字占比≥55%% 的"释义/文案候选" %d 条' % len(prose))
print('\n== 候选中最长的 20 条')
for s, o in sorted(prose, key=lambda x: -len(x[0]))[:20]:
    print('  %08x  len=%-4d %s' % (o, len(s), s.replace('\n', '\\n')[:150]))
print('\n== 含"词典/图鉴/设置"关键词的串')
for s, o in items:
    if any(k in s for k in ('词典', '图鉴', '设置', '开关', '解锁')) and len(s) < 120:
        print('  %08x  %s' % (o, s.replace('\n', '\\n')))
