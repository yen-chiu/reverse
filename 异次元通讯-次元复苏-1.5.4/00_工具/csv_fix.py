# -*- coding: utf-8 -*-
"""把 `04_资源分析\剧情CSV`（APK 原件副本，只读证据）修正为 `04_资源分析\剧情CSV_修正`。

只做**可证明的字节级修正**，不改动任何剧情文本：
   1) 第六章 第 106 行：图鉴键写进了第一列 → 移到第二列
        S6-01-n,,图鉴   →   ,S6-01-n,图鉴
   2) 第四章 第 760 行：图鉴行多一个尾随逗号（第 4 个空字段） → 删除
        ,S4-01-n,图鉴,  →   ,S4-01-n,图鉴

其余 6 个文件逐字节复制（SHA-256 必须与原件一致）。
语义层的数据异常（词典编号空洞/重复/空编号）**不改值**，只登记到 `修正记录.md`，
因为编号是 libapp.so 释义数组的下标，擅自重排会破坏 id→释义 映射。

输出：04_资源分析\修正记录.md（修正清单 + 数据体检）
"""
import csv, hashlib, os, sys, collections

sys.stdout.reconfigure(encoding='utf-8')
BASE = r'C:\03_Github\reverse\异次元通讯-次元复苏-1.5.4'
SRC = os.path.join(BASE, '04_资源分析', '剧情CSV')
DST = os.path.join(BASE, '04_资源分析', '剧情CSV_修正')
os.makedirs(DST, exist_ok=True)

ORDER = ['番外一', '番外二', '第一章', '第二章', '第三章', '第四章', '第五章', '第六章']

# (章节, 1-based 行号, 原始字节, 修正后字节)
FIXES = [
    ('第六章', 106, 'S6-01-n,,图鉴', ',S6-01-n,图鉴'),
    ('第四章', 760, ',S4-01-n,图鉴,', ',S4-01-n,图鉴'),
]


def sha(b):
    return hashlib.sha256(b).hexdigest()


def fields(row):
    return [c.strip() for c in (row + ['', '', ''])[:3]]


def audit(name, rows):
    """返回该章的数据体检项。"""
    out = []
    for i, r in enumerate(rows, 1):
        if len(r) != 3:
            out.append((name, i, '列数 %d（应为 3）' % len(r), ' / '.join(repr(c) for c in r)))
        spk, txt, cell = [c.strip() for c in (r + ['', '', ''])[:3]]
        toks = [t.strip() for t in cell.split(',')] if cell else []
        if '图鉴' in toks and not txt:
            out.append((name, i, '图鉴键缺失（键=%r）' % spk, cell))
        if '动态' in toks and not spk:
            out.append((name, i, '动态配图键为空', txt))
    return out


report = []
log = []

# ---- 1. 逐文件修正 ----
for name in ORDER:
    src_path = os.path.join(SRC, name + '.csv')
    raw = open(src_path, 'rb').read()
    lines = raw.split(b'\r\n')
    applied = []
    for chap, lineno, old, new in FIXES:
        if chap != name:
            continue
        idx = lineno - 1
        cur = lines[idx].decode('utf-8')
        if cur != old:
            raise SystemExit('修正前提不成立：%s 第 %d 行为 %r，期望 %r' % (name, lineno, cur, old))
        lines[idx] = new.encode('utf-8')
        applied.append((lineno, old, new))
    new_raw = b'\r\n'.join(lines)
    open(os.path.join(DST, name + '.csv'), 'wb').write(new_raw)
    same = sha(raw) == sha(new_raw)
    log.append({'chapter': name, 'fixed': applied, 'bytes': len(raw),
                'sha_orig': sha(raw), 'sha_new': sha(new_raw), 'identical': same})
    print('%-4s %8d 字节  %s  %s' % (name, len(raw), sha(new_raw)[:16], '未改动' if same else '已修正 %d 行' % len(applied)))

# ---- 2. 体检（修正后）----
all_rows = {}
issues = []
for name in ORDER:
    rows = list(csv.reader(open(os.path.join(DST, name + '.csv'), encoding='utf-8')))
    all_rows[name] = rows
    issues += audit(name, rows)

# 词典编号
ids = []
for name in ORDER:
    for i, r in enumerate(all_rows[name], 1):
        spk, txt, cell = fields(r)
        if '词典' in ([t.strip() for t in cell.split(',')] if cell else []):
            ids.append((name, i, spk, txt))
present = sorted({int(i) for _, _, i, _ in ids if i.isdigit()})
holes = [n for n in range(0, max(present) + 1) if n not in present]
dups = {k: v for k, v in collections.Counter(int(i) for _, _, i, _ in ids if i.isdigit()).items() if v > 1}
empty_ids = [(n, ln, t) for n, ln, i, t in ids if not i]

# 图鉴键
keys = []
for name in ORDER:
    for i, r in enumerate(all_rows[name], 1):
        spk, txt, cell = fields(r)
        if '图鉴' in ([t.strip() for t in cell.split(',')] if cell else []):
            keys.append(txt)

# ---- 3. 写修正记录 ----
R = []
R.append('# 数据修正记录\n')
R.append('> 源：`04_资源分析\\剧情CSV\\`（APK 内 `assets/story/*.csv` 的逐字节副本，**只读证据**）')
R.append('> 目标：`04_资源分析\\剧情CSV_修正\\`（唯一被下游脚本读取的版本）')
R.append('> 原则：只做可证明的字节级修正；会改变语义的数据异常一律**只登记不改值**。\n')

R.append('## 一、已修正（2 处）\n')
R.append('| 章节 | 行号 | 修正前 | 修正后 | 影响 |')
R.append('|---|---|---|---|---|')
R.append('| 第六章 | 106 | `S6-01-n,,图鉴` | `,S6-01-n,图鉴` | 图鉴键从第一列移到第二列；修正前解析出**空键**，`S6-01-n` 实际无法解锁 |')
R.append('| 第四章 | 760 | `,S4-01-n,图鉴,` | `,S4-01-n,图鉴` | 删除多余的尾随逗号（第 4 个空字段）；语义不变，仅消除解析歧义 |')
R.append('')
R.append('字节级影响：仅上述两行的字节内容变化，其余 6 个文件 SHA-256 与原件完全一致。\n')
R.append('| 章节 | 原始字节 | 修正后 SHA-256 | 状态 |')
R.append('|---|---|---|---|')
for d in log:
    R.append('| %s | %d | `%s` | %s |' % (d['chapter'], d['bytes'], d['sha_new'], '未改动' if d['identical'] else '已修正'))
R.append('')

R.append('## 二、只登记、不修改（语义层异常）\n')
R.append('### 2.1 词典编号空洞\n')
R.append('共 **%d** 个编号未被使用：`%s`。' % (len(holes), ','.join(str(h) for h in holes)))
R.append('原因不可知（可能是早期版本删条目留下的编号，也可能对应 libapp.so 里存在但剧本未引用的释义）。编号是释义数组的下标，**重排会破坏 id→释义 映射**，故不改。\n')
R.append('### 2.2 词典编号重复\n')
for k, v in sorted(dups.items()):
    names = ['%s:%d `%s`' % (n, ln, t) for n, ln, i, t in ids if i.isdigit() and int(i) == k]
    R.append('- 编号 **%d** 出现 %d 次：%s' % (k, v, '、'.join(names)))
R.append('')
R.append('`39` 的两条词条名不同（`uno` / `Tango One`），而 id 39 的释义经自证匹配为 **Tango One**，说明 `uno` 复用了错误编号——这是原作的语义缺陷，改成别的编号只会指向另一条错释义，因此保留原值并在此登记。`44` 的两条都是 `熵`，属于同名重复解锁，无实际影响。\n')
R.append('### 2.3 词典编号为空\n')
R.append('共 **%d** 条词典行没有编号（%s）。' % (len(empty_ids),
         '、'.join('%s:%d' % (n, ln) for n, ln, _ in empty_ids[:8]) + ('…' if len(empty_ids) > 8 else '')))
R.append('说明编号是**可选字段**，引擎可以只按词条名解锁。为了下游能唯一定位，`词典.csv` 增加 `稳定键`（`章节:行号`）与 `编号状态` 两列。\n')

R.append('### 2.4 结构体检（修正后应全部为空）\n')
if issues:
    R.append('| 章节 | 行号 | 问题 | 原文 |')
    R.append('|---|---|---|---|')
    for n, ln, why, raw in issues:
        R.append('| %s | %d | %s | `%s` |' % (n, ln, why, raw))
else:
    R.append('无异常：所有行均为 3 列，图鉴行都有键，动态行都有配图键。\n')

R.append('### 2.5 图鉴键总量与两种形态\n')
silent = 0
bysender = collections.Counter()
for name in ORDER:
    for i, r in enumerate(all_rows[name], 1):
        spk, txt, cell = fields(r)
        if '图鉴' in ([t.strip() for t in cell.split(',')] if cell else []):
            nn = [c for c in (spk, txt) if c]
            if len(nn) > 1:
                bysender[nn[0]] += 1
            else:
                silent += 1
R.append('修正后共 **%d** 个图鉴解锁点、**%d** 个唯一键（修正前因列错位少 1 个，且有一条键被误读成 `Miko`）。' % (len(keys), len(set(keys))))
R.append('**两种形态**：%d 行是「静默解锁」（`键,,图鉴`），%d 行带发送者（`Miko,键,图鉴` / `Iris,键,图鉴`），'
         '后者除了解锁，还会在聊天里由该角色「发出」这张图，因此键必须取前两列中**最后一个**非空字段。'
         % (silent, sum(bysender.values())))
for who, cnt in sorted(bysender.items()):
    R.append('- `%s` 发送 %d 次' % (who, cnt))
R.append('')

R.append('### 2.6 资源引用情况\n')
import os as _os
photo_dir = os.path.join(BASE, '02_解包', 'assets', 'flutter_assets', 'assets', 'photo')
photos = sorted({_os.path.splitext(f)[0] for f in _os.listdir(photo_dir)})
dong_keys = set()
for name in ORDER:
    for i, r in enumerate(all_rows[name], 1):
        spk, txt, cell = fields(r)
        if '动态' in ([t.strip() for t in cell.split(',')] if cell else []):
            dong_keys.add(spk)
used = set(keys) | dong_keys
unused = sorted(p for p in photos if p not in used and p + '-n' not in used)
R.append('图鉴键 %d 个 + 动态配图 %d 个；`photo/` 共 %d 张插画，其中 **%d 张**既不在图鉴也不在动态里（多为分支里的过场图与 4 张节日彩蛋）：%s。\n'
         % (len(set(keys)), len(dong_keys), len(photos), len(unused), '、'.join('`%s`' % u for u in unused) if unused else '无'))

open(os.path.join(BASE, '04_资源分析', '修正记录.md'), 'w', encoding='utf-8').write('\n'.join(R))
print('\n体检：结构异常 %d 项；词典编号空洞 %d、重复 %d 组、空编号 %d 条；图鉴键 %d 个（唯一 %d）'
      % (len(issues), len(holes), len(dups), len(empty_ids), len(keys), len(set(keys))))
print('已写 04_资源分析\\修正记录.md')
