import csv, glob, os, sys
sys.stdout.reconfigure(encoding='utf-8')
d = r'C:\03_Github\reverse\异次元通讯-次元复苏-1.5.4\04_资源分析\剧情CSV'
for f in sorted(glob.glob(os.path.join(d, '*.csv'))):
    rows = list(csv.reader(open(f, encoding='utf-8'), delimiter=',', quotechar='"'))
    bad = [(i, r) for i, r in enumerate(rows, 1) if len(r) != 3]
    if bad:
        print(os.path.basename(f), 'bad', len(bad))
        for i, r in bad[:8]:
            print('  ', i, r)
