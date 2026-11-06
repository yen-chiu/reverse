import re, sys, json, io, os
sys.stdout.reconfigure(encoding='utf-8')
p = r'C:\03_Github\reverse\异次元通讯-次元复苏-1.5.4\02_解包\lib\arm64-v8a\libapp.so'
b = open(p,'rb').read()
n = len(b)
out = []
i = 0
def ok(c):
    if c in (0x09,0x0a,0x0d): return True
    if 0x20 <= c <= 0x7e: return True
    if 0x4e00 <= c <= 0x9fff: return True
    if 0x3000 <= c <= 0x303f: return True
    if 0xff00 <= c <= 0xffef: return True
    if 0x2000 <= c <= 0x27bf: return True   # punctuation/symbols
    if 0x3400 <= c <= 0x4dbf: return True
    if 0x0400 <= c <= 0x04ff: return True
    if 0x00a0 <= c <= 0x00ff: return True
    return False
cur = []
start = 0
i = 0
while i + 1 < n:
    c = b[i] | (b[i+1] << 8)
    if ok(c):
        if not cur: start = i
        cur.append(chr(c))
        i += 2
    else:
        if len(cur) >= 3:
            out.append((start, ''.join(cur)))
        cur = []
        i += 2
if len(cur) >= 3:
    out.append((start, ''.join(cur)))
# only keep entries containing CJK
def has_cjk(s): return any('\u4e00' <= ch <= '\u9fff' for ch in s)
cjk = [(o,s) for o,s in out if has_cjk(s)]
with open(r'C:\03_Github\reverse\异次元通讯-次元复苏-1.5.4\03_反编译\dart_strings_utf16.txt','w',encoding='utf-8') as f:
    for o,s in out:
        f.write('%08x\t%s\n' % (o,s))
print('total utf16 runs:', len(out), 'with CJK:', len(cjk))
keys = ['选项','分支','等待','词典','图鉴','动态','对方已上线','预计','左','右','中','BE','无','图片','语音','章节','标题','结束','跳转']
for k in keys:
    hits = [(o,s) for o,s in out if k in s]
    if not hits: 
        print('==',k,'(none)')
        continue
    print('==',k,'hits',len(hits))
    for o,s in hits[:6]:
        print('   %08x  %r' % (o, s[:160]))
