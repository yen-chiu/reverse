# -*- coding: utf-8 -*-
"""图鉴键 ↔ photo 插画文件 对账。"""
import csv, os, sys

sys.stdout.reconfigure(encoding='utf-8')
BASE = r'C:\03_Github\reverse\异次元通讯-次元复苏-1.5.4'
rows = list(csv.DictReader(open(os.path.join(BASE, '04_资源分析', '表', '资源清单.csv'), encoding='utf-8-sig')))
photos = {}
for r in rows:
    if r['相对路径'].startswith('photo/'):
        photos[os.path.splitext(r['相对路径'].split('/', 1)[1])[0]] = r['相对路径']

tj = [r for r in csv.DictReader(open(os.path.join(BASE, '04_资源分析', '表', '图鉴.csv'), encoding='utf-8-sig'))]
keys = [r['图片键'] for r in tj if r['图片键']]
print('photo 文件 %d 个；图鉴行 %d 条，非空键 %d 个（唯一 %d）' % (len(photos), len(tj), len(keys), len(set(keys))))
hit = [k for k in keys if k in photos]
miss = [k for k in keys if k not in photos]
base_hit = [k for k in miss if k[:-2] in photos and k.endswith('-n')]
print('图鉴键有同名文件 %d 个' % len(hit))
print('缺同名文件 %d 个，其中以 -n 结尾且基名存在 %d 个' % (len(miss), len(base_hit)))
print('仍无任何对应文件：', [k for k in miss if k not in base_hit])
used = set(hit) | {k[:-2] for k in base_hit}
未用 = sorted(set(photos) - used)
print('未进图鉴的插画 %d 个：%s' % (len(未用), 未用))
