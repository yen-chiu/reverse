BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import os, sys, re, json
sys.stdout.reconfigure(encoding='utf-8')
p = os.path.join(BASE, '03_反编译', 'dart_strings_utf16.txt')
data = open(p, encoding='utf-8').read()
chunks = re.split(r'\n(?=[0-9a-f]{8}\t)', data)
rows = []
for c in chunks:
    if '\t' not in c: continue
    off, s = c.split('\t', 1)
    try: rows.append((int(off, 16), s))
    except ValueError: pass
cjk = [(o, s) for o, s in rows if any('\u4e00' <= ch <= '\u9fff' for ch in s)]
longs = [x for x in cjk if len(x[1]) >= 120]
print('strings total:', len(rows), 'CJK:', len(cjk), 'long(>=120):', len(longs))
for o, s in longs[:5]:
    print('%08x len=%d %r' % (o, len(s), s[:80]))
print('--- term lookup')
for term in ['莫西莫西', '变色牌', '万能牌']:
    hits = [(o, s) for o, s in rows if term in s]
    print(term, len(hits), [(hex(o), len(s)) for o, s in hits[:8]])
json.dump([[o, s] for o, s in rows], open(os.path.join(BASE, '03_反编译', 'dart_strings_utf16.json'), 'w', encoding='utf-8'), ensure_ascii=False)
