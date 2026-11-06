import os
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import csv, glob, os, re, sys, collections
sys.stdout.reconfigure(encoding='utf-8')
d = os.path.join(BASE, '04_资源分析', '剧情CSV')
files = sorted(glob.glob(os.path.join(d, '*.csv')))
pat = collections.Counter()
samples = collections.defaultdict(list)
for f in files:
    name = os.path.basename(f)
    rows = list(csv.reader(open(f, encoding='utf-8'), delimiter=',', quotechar='"'))
    for ln, r in enumerate(rows, 1):
        r = (r + ['', '', ''])[:3]
        spk, txt, instr = r
        toks = [t.strip() for t in instr.split(',')] if instr else []
        tpl = []
        for t in toks:
            if re.fullmatch(r'分支\d+', t): tpl.append('分支N')
            elif re.fullmatch(r'\d+', t): tpl.append('N')
            else: tpl.append(t if t else '_')
        key = ' '.join(tpl)
        pat[key] += 1
        if len(samples[key]) < 2: samples[key].append('%s:%d %r' % (name, ln, r))
print('=== instruction patterns (n=%d distinct)' % len(pat))
for k, v in pat.most_common(70):
    print('%6d  %s' % (v, k))
    for s in samples[k][:2]: print('         ', s)
