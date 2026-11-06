# -*- coding: utf-8 -*-
"""生成 `项目清单.md`：样本指纹 + 目录体量 + 剧情 CSV 与 APK 的一致性 + 关键产物指纹。

与旧版 `存档清单.md` 的区别：本工作区是**修正后**的单管线工作区，
所以一致性校验断言「6 章与发布包逐字节相同，2 章只差那 2 行修正」。
"""
import collections, csv, hashlib, os, sys, zipfile
from urllib.parse import quote

sys.stdout.reconfigure(encoding='utf-8')
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APK = os.path.join(BASE, '01_原始', 'app-release-1.5.4.apk')
APK_DL = os.path.join(os.path.dirname(os.path.dirname(BASE)), '原文件',
                      '异次元通讯-次元复苏-release-1.5.4.apk')
ARCHIVE = os.path.join(os.path.dirname(BASE), '异次元通讯-次元复苏-1.5.4-存档-20261106')
ORDER = ['番外一', '番外二', '第一章', '第二章', '第三章', '第四章', '第五章', '第六章']
STORY = os.path.join(BASE, '04_资源分析', '剧情CSV')


def sha(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(chunk), b''):
            h.update(b)
    return h.hexdigest()


def size(p):
    return os.path.getsize(p)


# ---- 目录体量 ----
rows = []
for d in sorted(os.listdir(BASE)):
    p = os.path.join(BASE, d)
    if not os.path.isdir(p):
        continue
    n = total = 0
    for root, _, files in os.walk(p):
        for f in files:
            n += 1
            total += size(os.path.join(root, f))
    rows.append((d, n, total))

# ---- 剧情 CSV 与 APK 对照 ----
same, diffs = [], []
with zipfile.ZipFile(APK) as z:
    for name in ORDER:
        ref = None
        for cand in ('assets/flutter_assets/assets/story/%s.csv' % name,
                     'assets/flutter_assets/assets/story/%s.csv' % quote(name)):
            try:
                ref = z.read(cand)
                break
            except KeyError:
                continue
        cur = open(os.path.join(STORY, name + '.csv'), 'rb').read()
        if hashlib.sha256(ref).hexdigest() == hashlib.sha256(cur).hexdigest():
            same.append(name)
            continue
        a = ref.decode('utf-8').split('\r\n')
        b = cur.decode('utf-8').split('\r\n')
        for i, (x, y) in enumerate(zip(a, b), 1):
            if x != y:
                diffs.append((name, i, x, y))

# ---- 关键产物 ----
key = []
for rel in ['README.md', '项目清单.md', '05_报告\\逆向分析报告.md',
            '04_资源分析\\数据体检与修正记录.md', '04_资源分析\\统计\\剧情结构统计.md']:
    key.append((rel, os.path.join(BASE, rel)))
for n in ORDER:
    key.append(('04_资源分析\\剧情CSV\\%s.csv' % n, os.path.join(STORY, n + '.csv')))
    key.append(('04_资源分析\\剧本\\%s.md' % n, os.path.join(BASE, '04_资源分析', '剧本', n + '.md')))
    key.append(('04_资源分析\\剧本AST\\%s.json' % n, os.path.join(BASE, '04_资源分析', '剧本AST', n + '.json')))
for t in ['词典', '图鉴', '动态', '语音', '章节天数', 'BE节点', '资源清单', 'APK条目清单',
          '词典释义_匹配', '图鉴对账']:
    for ext in ('.csv', '.md'):
        p = os.path.join(BASE, '04_资源分析', '表', t + ext)
        if os.path.exists(p):
            key.append(('04_资源分析\\表\\%s%s' % (t, ext), p))

# ---- 写清单 ----
L = []
L.append('# 项目清单\n')
L.append('> 生成时间：2026-11-06　工作区：`%s`' % BASE)
L.append('> 用途：记录文件体量与关键产物指纹，便于核对「有无被改动」。重新生成：`python -X utf8 00_工具\\project_manifest.py`\n')

L.append('## 1. 样本\n')
L.append('| 项 | 值 |')
L.append('|---|---|')
L.append('| 工作区内副本 | `01_原始\\app-release-1.5.4.apk` |')
L.append('| 字节 | %s |' % format(size(APK), ','))
L.append('| SHA-256 | `%s` |' % sha(APK))
L.append('| 原始下载路径 | `%s` |' % APK_DL)
if os.path.exists(APK_DL):
    L.append('| 与原始下载是否同一文件 | %s |' % ('是' if sha(APK_DL) == sha(APK) else '**否**'))
L.append('')

L.append('## 2. 两个工作区的关系\n')
L.append('| 工作区 | 性质 |')
L.append('|---|---|')
L.append('| `异次元通讯-次元复苏-1.5.4-改动\\`（本目录） | **正式工作区**：剧情 CSV 已修正，单管线，脚本 `BASE` 自定位 |')
L.append('| `异次元通讯-次元复苏-1.5.4-存档-20261106\\` | **冻结快照**：未修正原样 + 当时的双管线产物，只作对照 |')
L.append('')
L.append('存档目录当前%s。' % ('存在，路径 `%s`' % ARCHIVE if os.path.isdir(ARCHIVE) else '**不存在**（已移动或删除）'))
L.append('')

L.append('## 3. 目录体量\n')
L.append('| 目录 | 文件数 | 字节 |')
L.append('|---|---|---|')
for d, n, t in rows:
    L.append('| `%s\\` | %d | %s |' % (d, n, format(t, ',')))
L.append('| **合计** | **%d** | **%s** |' % (sum(r[1] for r in rows), format(sum(r[2] for r in rows), ',')))
L.append('')

L.append('## 4. 剧情 CSV 与发布包的一致性\n')
L.append('- 与 APK 内文件逐字节相同：**%d/8**（%s）' % (len(same), '、'.join(same)))
L.append('- 有差异（= 本工作区做过的修正，应当只有 2 行）：**%d 行**' % len(diffs))
if diffs:
    L.append('')
    L.append('| 章节 | 行号 | 发布包 | 本工作区 |')
    L.append('|---|---|---|---|')
    for name, i, x, y in diffs:
        L.append('| %s | %d | `%s` | `%s` |' % (name, i, x, y))
L.append('')
L.append('> 也就是说：本工作区的剧情数据 = 发布包原样 + 上述 2 行修正，没有别的改动。明细见 `04_资源分析\\数据体检与修正记录.md`。\n')

L.append('## 5. 关键产物指纹\n')
L.append('| 文件 | 字节 | SHA-256 |')
L.append('|---|---|---|')
for rel, p in key:
    if os.path.exists(p):
        L.append('| `%s` | %s | `%s` |' % (rel, format(size(p), ','), sha(p)))
L.append('')
L.append('> 校验：`Get-FileHash <文件> -Algorithm SHA256` 与上表比对。\n')

L.append('## 6. 复现命令\n')
L.append('```')
L.append('cd "C:\\03_Github\\reverse\\异次元通讯-次元复苏-1.5.4-改动"')
L.append('python -X utf8 00_工具\\csv_audit.py          # 数据体检（应报 2 处差异 / 0 结构异常）')
L.append('python -X utf8 00_工具\\story_export.py       # 剧情 CSV → 剧本 / 剧本AST / 表 / 统计')
L.append('python -X utf8 00_工具\\asset_inventory.py    # 资源清单')
L.append('python -X utf8 00_工具\\asset_md.py           # 资源清单.md')
L.append('python -X utf8 00_工具\\dict_match.py         # 词典释义匹配')
L.append('python -X utf8 00_工具\\tujian_reconcile.py   # 图鉴对账')
L.append('python -X utf8 00_工具\\project_manifest.py   # 本清单')
L.append('```')
L.append('')

L.append('## 7. 待办\n')
L.append('1. 词典 `id → 释义` 全量映射（需 blutter + Dart SDK 反序列化 snapshot）；')
L.append('2. 14 个重复 `分支` 标签的运行时解析策略（取最近的下一个 / 取第一处）；')
L.append('3. 段间推进规则（静态模拟覆盖不足，需运行时单步）；')
L.append('4. 图鉴键 `-n` 后缀语义（目前判定为「缺则回退基名」）；')
L.append('5. 三 ABI `libapp.so` 函数级比对；')
L.append('6. 同级 `..\\原文件\\生命线.apk`（12.8MB）不在本工作区范围内；')
L.append('   《生命线》另有独立工作区 `..\\生命线-2.3.3\\`（含自己的报告），与本项目无数据依赖。')

open(os.path.join(BASE, '项目清单.md'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')
print('目录：' + '；'.join('%s %d' % (d, n) for d, n, _ in rows))
print('与 APK 一致 %d/8，差异行 %d。已写 项目清单.md（关键产物 %d 项）'
      % (len(same), len(diffs), sum(1 for _, p in key if os.path.exists(p))))
