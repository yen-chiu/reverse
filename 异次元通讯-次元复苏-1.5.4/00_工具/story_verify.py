import csv, glob, os, re, sys, collections
sys.stdout.reconfigure(encoding='utf-8')
d = r'C:\03_Github\reverse\异次元通讯-次元复苏-1.5.4\04_资源分析\剧情CSV'
files = sorted(glob.glob(os.path.join(d, '*.csv')))
stats = collections.Counter()
waitvals = collections.Counter()
numvals = collections.Counter()
issues = []
dict_ids = collections.Counter()
tu_ids = collections.Counter()
dong = collections.Counter()
for f in files:
    name = os.path.basename(f)
    rows = list(csv.reader(open(f, encoding='utf-8'), delimiter=',', quotechar='"'))
    opt_ids, br_ids, bare_ids = [], [], []
    for ln, r in enumerate(rows, 1):
        if len(r) != 3:
            issues.append((name, ln, 'ncols=%d' % len(r), r))
            continue
        spk, txt, instr = r
        parts = [p.strip() for p in instr.split(',')] if instr else []
        has_br = [p for p in parts if re.fullmatch(r'分支\d+', p)]
        bares = [p for p in parts if re.fullmatch(r'\d+', p)]
        stats['rows'] += 1
        for p in parts:
            if p == '': stats['empty_instr'] += 1
            elif p in ('左','右','中'): stats['align_' + p] += 1
            elif p == '选项': stats['选项'] += 1
            elif p == '等待': stats['等待'] += 1
            elif p in ('词典','图鉴','动态','BE','无'): stats[p] += 1
            elif re.fullmatch(r'分支\d+', p): stats['分支'] += 1; br_ids.append(int(p[2:]))
            elif re.fullmatch(r'\d+', p): stats['bare'] += 1; bare_ids.append(int(p))
            else: stats['UNKNOWN:' + p] += 1
        # option id = number right after 选项
        for i, p in enumerate(parts):
            if p == '选项' and i + 1 < len(parts) and re.fullmatch(r'\d+', parts[i+1]):
                opt_ids.append(int(parts[i+1]))
            if p == '等待' and i + 1 < len(parts) and re.fullmatch(r'\d+', parts[i+1]):
                waitvals[int(parts[i+1])] += 1
        if bares and not has_br:
            issues.append((name, ln, 'bare without 分支', r))
        if has_br and not bares:
            stats['分支_nobare'] += 1
        if has_br and bares:
            stats['分支_with_bare'] += 1
        if '词典' in parts: dict_ids[spk] += 1
        if '图鉴' in parts: tu_ids[txt] += 1
        if '动态' in parts: dong[spk] += 1
    miss_opt = sorted(set(opt_ids) - set(br_ids))
    miss_br = sorted(set(br_ids) - set(opt_ids))
    miss_bare = sorted(set(bare_ids) - set(br_ids))
    print('%-12s rows=%4d opts=%4d br=%4d  opt_no_branch=%s  branch_no_opt=%s  bare_no_branch=%s'
          % (name, len(rows), len(opt_ids), len(br_ids), miss_opt[:12], miss_br[:12], miss_bare[:12]))
print('\n=== stats'); 
for k, v in sorted(stats.items()): print('  %-14s %d' % (k, v))
print('\n=== 等待 values:', dict(sorted(waitvals.items())))
print('\n=== 图鉴 keys:', list(tu_ids)[:20], 'n=', len(tu_ids))
print('\n=== 动态 speakers:', dict(dong))
print('\n=== 词典 id count:', len(dict_ids), 'ids:', sorted(int(k) for k in dict_ids if k.isdigit())[:20], 'max', max(int(k) for k in dict_ids if k.isdigit()))
print('\n=== issues n=', len(issues))
for i in issues[:10]: print('   ', i)
# table-ish lines
print('\n=== table-like rows (no separate text)')
for f in files[:2]:
    rows = list(csv.reader(open(f, encoding='utf-8'), delimiter=',', quotechar='"'))
    for ln, r in enumerate(rows, 1):
        if len(r) == 3 and '词典' in r[2]:
            print(' ', os.path.basename(f), ln, r)
