import csv, glob, os, re, sys, collections
sys.stdout.reconfigure(encoding='utf-8')
d = r'C:\03_Github\reverse\异次元通讯-次元复苏-1.5.4\04_资源分析\剧情CSV'
files = sorted(glob.glob(os.path.join(d, '*.csv')))
allrows = {}
for f in files:
    name = os.path.basename(f).replace('.csv','')
    rows = list(csv.reader(open(f, encoding='utf-8'), delimiter=',', quotechar='"'))
    allrows[name] = [(r + ['','',''])[:3] for r in rows]

# 1) wait rows: text vs value
print('=== 等待 rows (text vs N)')
wt = collections.Counter()
for name, rows in allrows.items():
    for ln, (spk, txt, instr) in enumerate(rows, 1):
        toks = [t.strip() for t in instr.split(',')]
        if '等待' in toks:
            i = toks.index('等待')
            v = toks[i+1]
            pre = toks[:i]
            wt[(txt, v, tuple(pre))] += 1
for (txt, v, pre), c in wt.most_common(40):
    print('  text=%-10r wait=%-4s pre=%-12s x%d' % (txt, v, list(pre), c))

# 2) 无 rows
print('\n=== 无 rows')
wu = collections.Counter()
for name, rows in allrows.items():
    for ln, (spk, txt, instr) in enumerate(rows, 1):
        if instr.strip() == '无': wu[(name, spk, txt)] += 1
for k, c in wu.items(): print('  %-8s %-4r %-10r x%d' % (k[0], k[1], k[2], c))

# 3) 语音 rows
print('\n=== 语音 rows')
for name, rows in allrows.items():
    for ln, (spk, txt, instr) in enumerate(rows, 1):
        if '语音' in instr:
            for j in range(max(0,ln-3), min(len(rows), ln+2)):
                print('  %s:%d %r' % (name, j+1, rows[j]))

# 4) BE rows + context
print('\n=== BE rows + context')
for name, rows in allrows.items():
    for ln, (spk, txt, instr) in enumerate(rows, 1):
        if 'BE' in [t.strip() for t in instr.split(',')]:
            print('  %s:%d %r' % (name, ln, rows[ln-1]))
            for j in range(ln, min(len(rows), ln+4)):
                print('        +%d %r' % (j-ln+1, rows[j]))
            break

# 5) duplicate 分支 labels and unresolved jumps per file
print('\n=== labels')
for name, rows in allrows.items():
    brs = []
    jumps = []
    for ln, (spk, txt, instr) in enumerate(rows, 1):
        toks = [t.strip() for t in instr.split(',')]
        for i, t in enumerate(toks):
            m = re.fullmatch(r'分支(\d+)', t)
            if m: brs.append(int(m.group(1)))
            elif re.fullmatch(r'\d+', t) and (i == 0 or toks[i-1] in ('左','右','中')) and t != '0' and not (i+1 < len(toks) and toks[i+1] == '等待'):
                jumps.append(int(t))
    dup = [k for k, v in collections.Counter(brs).items() if v > 1]
    unres = sorted(set(jumps) - set(brs))
    print('  %-8s 分支=%4d dup=%s unresolved_jumps=%s' % (name, len(brs), dup[:10], unres[:10]))
