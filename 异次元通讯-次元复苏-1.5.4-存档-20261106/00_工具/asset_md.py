# -*- coding: utf-8 -*-
"""把资源清单.csv 渲染成分目录的 Markdown 清单。"""
import csv, collections, os, sys

sys.stdout.reconfigure(encoding='utf-8')
BASE = r'C:\03_Github\reverse\异次元通讯-次元复苏-1.5.4'
CSVP = os.path.join(BASE, '04_资源分析', '表', '资源清单.csv')
OUT = os.path.join(BASE, '04_资源分析', '表', '资源清单.md')

rows = list(csv.DictReader(open(CSVP, encoding='utf-8-sig')))
groups = collections.OrderedDict()
for r in rows:
    top = r['相对路径'].split('/')[0]
    groups.setdefault(top, []).append(r)

L = ['# 资源清单（assets/flutter_assets/assets）\n',
     '共 %d 个文件 / %d 字节（%.2f MB）。尺寸与时长由脚本解析文件头得到，SHA-256 为文件整体摘要。\n'
     % (len(rows), sum(int(r['字节']) for r in rows),
        sum(int(r['字节']) for r in rows) / 1048576)]
for top, items in groups.items():
    tot = sum(int(r['字节']) for r in items)
    L.append('\n## %s/ — %d 个文件 / %d 字节（%.2f MB）\n' % (top, len(items), tot, tot / 1048576))
    L.append('| 文件 | 字节 | 尺寸 | 时长 | SHA-256（前 16） |')
    L.append('|---|---|---|---|---|')
    for r in items:
        dim = '%s×%s' % (r['宽'], r['高']) if r['宽'] else '—'
        dur = ('%ss' % r['时长秒']) if r['时长秒'] else '—'
        L.append('| %s | %s | %s | %s | `%s` |' % (
            r['相对路径'].split('/', 1)[1], r['字节'], dim, dur, r['SHA-256'][:16]))
open(OUT, 'w', encoding='utf-8').write('\n'.join(L) + '\n')
print('written', OUT, 'groups=%d rows=%d' % (len(groups), len(rows)))
