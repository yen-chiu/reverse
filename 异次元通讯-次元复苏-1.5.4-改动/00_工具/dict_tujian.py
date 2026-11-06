import os
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import csv, glob, os, sys, urllib.parse
sys.stdout.reconfigure(encoding='utf-8')
d = os.path.join(BASE, '04_资源分析', '剧情CSV')
dicts = []
tujian = []
for f in sorted(glob.glob(os.path.join(d, '*.csv'))):
    ch = os.path.basename(f).replace('.csv','')
    rows = list(csv.reader(open(f, encoding='utf-8'), delimiter=',', quotechar='"'))
    for ln, r in enumerate(rows, 1):
        r = (r + ['','',''])[:3]
        toks = [t.strip() for t in r[2].split(',')]
        if '词典' in toks: dicts.append((r[0], r[1], ch, ln))
        if '图鉴' in toks: tujian.append((r[1].strip(), ch, ln))
print('=== 词典 rows:', len(dicts))
def k(x):
    return (int(x[0]) if x[0].strip().isdigit() else 9999, x[0])
for x in sorted(dicts, key=k): print('  id=%-5s %-12s (%s:%d)' % (x[0], x[1], x[2], x[3]))
print('\n=== 图鉴 keys:', len(tujian))
photo = set()
root = os.path.join(BASE, '02_解包', 'assets', 'flutter_assets', 'assets', 'photo')
for fn in os.listdir(root):
    photo.add(urllib.parse.unquote(fn).rsplit('.',1)[0])
tk = [t[0] for t in tujian]
print('  keys:', tk)
print('  missing photo file:', [k for k in tk if k not in photo])
print('  photo not in 图鉴:', sorted(photo - set(tk)))
