# -*- coding: utf-8 -*-
"""图鉴键 ↔ photo 插画文件 对账 + 资源闭合性检查。

用法：
    python -X utf8 tujian_reconcile.py                       # 默认读 04_资源分析\表
    python -X utf8 tujian_reconcile.py 04_资源分析\修正版\表   # 对修正版表再跑一遍

资源清单.csv 属包级产物，始终取顶层 04_资源分析\表\资源清单.csv。
结果同时打印并写入 <表目录>\图鉴对账.md。
"""
import csv, os, sys

sys.stdout.reconfigure(encoding='utf-8')
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAB = sys.argv[1] if len(sys.argv) > 1 else os.path.join('04_资源分析', '表')
TAB = TAB if os.path.isabs(TAB) else os.path.join(BASE, TAB)
RES = os.path.join(BASE, '04_资源分析', '表', '资源清单.csv')   # 包级，恒取顶层


def rd(name):
    p = os.path.join(TAB, name)
    return list(csv.DictReader(open(p, encoding='utf-8-sig'))) if os.path.exists(p) else []


rows = list(csv.DictReader(open(RES, encoding='utf-8-sig')))
photos = {}
for r in rows:
    if r['相对路径'].startswith('photo/'):
        photos[os.path.splitext(r['相对路径'].split('/', 1)[1])[0]] = r['相对路径']

tj = rd('图鉴.csv')
keys = [r['图片键'] for r in tj if r['图片键']]
hit = [k for k in keys if k in photos]
miss = [k for k in keys if k not in photos]
base_hit = [k for k in miss if k.endswith('-n') and k[:-2] in photos]
orphan = [k for k in miss if k not in base_hit]
used = set(hit) | {k[:-2] for k in base_hit}

# 动态页图片也算被引用
dt = rd('动态.csv')
dyn_imgs = []
for r in dt:
    for v in r.values():
        v = (v or '').strip()
        if v in photos and v not in dyn_imgs:
            dyn_imgs.append(v)
used |= set(dyn_imgs)
unused = sorted(set(photos) - used)

out = []
out.append('# 图鉴 / 插画资源对账\n')
out.append('- 数据源：`%s`' % os.path.relpath(TAB, BASE).replace('\\', '/'))
out.append('- photo 文件 %d 个（唯一基名 %d 个）' % (len(rows) and sum(1 for r in rows if r['相对路径'].startswith('photo/')), len(photos)))
out.append('- 图鉴行 %d 条，非空键 %d 个，唯一键 %d 个\n' % (len(tj), len(keys), len(set(keys))))
out.append('| 情况 | 数量 |\n|---|---|')
out.append('| 键在 photo/ 有完全同名文件 | %d |' % len(hit))
out.append('| 键缺文件但基名存在（`-n` 回退） | %d |' % len(base_hit))
out.append('| 键无任何对应文件 | %d |' % len(orphan))
out.append('| 动态页引用插画 | %d |' % len(dyn_imgs))
out.append('| 未被任何页面引用的插画 | %d |' % len(unused))
out.append('')
if orphan:
    out.append('无对应文件的键：%s\n' % ', '.join(orphan))
out.append('`-n` 回退的键（无独立文件，渲染时回退到基名）：\n')
out.append(', '.join('`%s`→`%s`' % (k, k[:-2]) for k in base_hit) + '\n')
out.append('未被引用的插画：%s\n' % (', '.join(unused) if unused else '无'))
# 按章统计
if tj:
    by = {}
    for r in tj:
        by[r.get('章节', '?')] = by.get(r.get('章节', '?'), 0) + 1
    out.append('按章图鉴数：%s' % '、'.join('%s %d' % (k, v) for k, v in by.items()))

txt = '\n'.join(out)
print(txt)
p = os.path.join(TAB, '图鉴对账.md')
open(p, 'w', encoding='utf-8').write(txt + '\n')
print('\nwritten:', p)
