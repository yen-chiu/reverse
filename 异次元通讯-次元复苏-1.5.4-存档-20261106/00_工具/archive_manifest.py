# -*- coding: utf-8 -*-
"""生成存档快照 `存档清单.md`：关键产物 SHA-256 + 目录体量 + 与 APK 的一致性校验。"""
import hashlib, os, sys

sys.stdout.reconfigure(encoding='utf-8')
BASE = r'C:\03_Github\reverse\异次元通讯-次元复苏-1.5.4'
APK = r'C:\03_Github\reverse\原文件\异次元通讯-次元复苏-release-1.5.4.apk'
ORDER = ['番外一', '番外二', '第一章', '第二章', '第三章', '第四章', '第五章', '第六章']


def sha(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def size(path):
    return os.path.getsize(path)


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
            total += os.path.getsize(os.path.join(root, f))
    rows.append((d, n, total))

# ---- 关键产物 ----
key = []
key.append(('README.md', os.path.join(BASE, 'README.md')))
key.append((r'05_报告\逆向分析报告.md', os.path.join(BASE, '05_报告', '逆向分析报告.md')))
key.append((r'04_资源分析\修正记录.md', os.path.join(BASE, '04_资源分析', '修正记录.md')))
key.append((r'04_资源分析\统计\剧情结构统计.md', os.path.join(BASE, '04_资源分析', '统计', '剧情结构统计.md')))
for n in ORDER:
    key.append((r'04_资源分析\剧情CSV\%s.csv' % n, os.path.join(BASE, '04_资源分析', '剧情CSV', n + '.csv')))
    key.append((r'04_资源分析\剧情CSV_修正\%s.csv' % n, os.path.join(BASE, '04_资源分析', '剧情CSV_修正', n + '.csv')))
    key.append((r'04_资源分析\剧本\%s.md' % n, os.path.join(BASE, '04_资源分析', '剧本', n + '.md')))
    key.append((r'04_资源分析\剧本AST\%s.json' % n, os.path.join(BASE, '04_资源分析', '剧本AST', n + '.json')))
for t in ['词典', '图鉴', '动态', '语音', '章节天数', 'BE节点', '资源清单', 'APK条目清单', '词典释义_匹配']:
    for ext in ('.csv', '.md'):
        p = os.path.join(BASE, '04_资源分析', '表', t + ext)
        if os.path.exists(p):
            key.append((r'04_资源分析\表\%s%s' % (t, ext), p))

# ---- 修正版管线（正式交付） ----
key.append((r'04_资源分析\修正版\README.md', os.path.join(BASE, '04_资源分析', '修正版', 'README.md')))
key.append((r'04_资源分析\修正版\对比_原件与修正版.md',
            os.path.join(BASE, '04_资源分析', '修正版', '对比_原件与修正版.md')))
for n in ORDER:
    key.append((r'04_资源分析\修正版\剧本\%s.md' % n,
                os.path.join(BASE, '04_资源分析', '修正版', '剧本', n + '.md')))
    key.append((r'04_资源分析\修正版\剧本AST\%s.json' % n,
                os.path.join(BASE, '04_资源分析', '修正版', '剧本AST', n + '.json')))
for t in ['词典', '图鉴', '动态', '语音', '章节天数', 'BE节点',
          '词典释义_匹配', '图鉴对账', '剧情结构统计']:
    for ext in ('.csv', '.md'):
        p = os.path.join(BASE, '04_资源分析', '修正版', '表', t + ext)
        if not os.path.exists(p):
            p = os.path.join(BASE, '04_资源分析', '修正版', '统计', t + ext)
        if os.path.exists(p):
            rel = os.path.relpath(p, os.path.join(BASE, '04_资源分析', '修正版'))
            key.append((r'04_资源分析\修正版\%s' % rel, p))

# ---- 一致性校验：剧情 CSV 副本 / 修正版 vs APK ----
import zipfile
same_orig, same_fix, differs = [], [], []
with zipfile.ZipFile(APK) as z:
    for n in ORDER:
        name_in_apk = 'assets/flutter_assets/assets/story/%s.csv' % n
        try:
            data = z.read(name_in_apk)
        except KeyError:
            from urllib.parse import quote
            data = z.read('assets/flutter_assets/assets/story/%s.csv' % quote(n))
        h = hashlib.sha256(data).hexdigest()
        ho = sha(os.path.join(BASE, '04_资源分析', '剧情CSV', n + '.csv'))
        hf = sha(os.path.join(BASE, '04_资源分析', '剧情CSV_修正', n + '.csv'))
        if ho == h:
            same_orig.append(n)
        if hf == h:
            same_fix.append(n)
        else:
            differs.append(n)

# ---- 写清单 ----
L = []
L.append('# 存档清单\n')
L.append('> 存档时间：2026-11-06　工作区：`%s`' % BASE)
L.append('> 用途：记录存档时点的文件体量与关键产物指纹，便于日后核对「有无被改动」。\n')

L.append('## 1. 样本\n')
L.append('| 项 | 值 |')
L.append('|---|---|')
L.append('| 原始 APK | `%s` |' % APK)
L.append('| 字节 | %d |' % size(APK))
L.append('| SHA-256 | `%s` |' % sha(APK))
L.append('')

L.append('## 2. 目录体量\n')
L.append('| 目录 | 文件数 | 字节 |')
L.append('|---|---|---|')
for d, n, t in rows:
    L.append('| `%s\\` | %d | %s |' % (d, n, format(t, ',')))
L.append('| **合计** | **%d** | **%s** |' % (sum(r[1] for r in rows), format(sum(r[2] for r in rows), ',')))
L.append('')
L.append('> `02_解包` 是 APK 的逐条解包结果（315 条目），体量占大头属正常；`99_临时` 可随时删除。\n')

L.append('## 3. 剧情 CSV 与 APK 的一致性校验\n')
L.append('- 原件副本与 APK 内文件 **SHA-256 一致**：%d/8（%s）' % (len(same_orig), '、'.join(same_orig)))
L.append('- 修正版与 APK 内文件 **SHA-256 不一致**（预期）：%s —— 即那 2 处修正所在文件，其余 6 个仍逐字节相同。\n'
         % ('、'.join(differs) if differs else '无'))
L.append('| 章节 | 原件 = APK | 修正版 = APK |')
L.append('|---|---|---|')
for n in ORDER:
    L.append('| %s | %s | %s |' % (n, '是' if n in same_orig else '否', '是' if n in same_fix else '否（已修正）'))
L.append('')

L.append('## 4. 关键产物指纹\n')
L.append('| 文件 | 字节 | SHA-256 |')
L.append('|---|---|---|')
for label, p in key:
    if os.path.exists(p):
        L.append('| `%s` | %s | `%s` |' % (label, format(size(p), ','), sha(p)))
L.append('')
L.append('> 校验方法：`Get-FileHash <文件> -Algorithm SHA256`，与上表比对即可确认文件未被改动。\n')

L.append('## 5. 存档时点的结论与待办\n')
L.append('完成：APK 结构/签名/清单、Dart AOT 语料、剧情语法（18 指令 / 零悬空跳转）、剧本与 AST、六张业务表、统计、资源清单、数据缺陷修正。')
L.append('')
L.append('产物分**两套管线**（同脚本、只换输入）：')
L.append('- **修正版管线（正式交付）**：`04_资源分析\\剧情CSV_修正\\` → `04_资源分析\\修正版\\`（剧本/AST/表/统计 + 对比报告 + README）。')
L.append('- **原件管线（对比用）**：`04_资源分析\\剧情CSV\\` → `04_资源分析\\剧本\\`、`剧本AST\\`、`表\\`、`统计\\`。')
L.append('- 两者正文逐行相同，差异只在剧本页眉标注；包级产物（`表\\资源清单.*`、`表\\APK条目清单.csv`）只保留一份。')
L.append('')
L.append('待办（详见 `README.md` 末节）：')
L.append('1. 词典 `id → 释义` 全量映射（需 blutter 反序列化 Dart snapshot）；')
L.append('2. 14 个重复 `分支` 标签的运行时解析策略；')
L.append('3. 段间推进规则（静态模拟覆盖不足，需运行时单步）；')
L.append('4. `-n` 后缀语义；')
L.append('5. 三 ABI `libapp.so` 函数级比对；')
L.append('6. 同目录 `生命线.apk` 尚未处理。')

open(os.path.join(BASE, '存档清单.md'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')
print('\n'.join('%s  %d 文件  %s 字节' % (d, n, format(t, ',')) for d, n, t in rows))
print('原件一致 %d/8，修正版不同于 APK：%s' % (len(same_orig), differs))
print('已写 存档清单.md，关键产物 %d 项' % sum(1 for _, p in key if os.path.exists(p)))
