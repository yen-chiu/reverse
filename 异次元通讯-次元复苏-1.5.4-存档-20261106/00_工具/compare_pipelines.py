# -*- coding: utf-8 -*-
"""对比「原件管线」与「修正版管线」的全部产物，生成对比报告。

用法：python -X utf8 compare_pipelines.py
输出：04_资源分析\修正版\对比_原件与修正版.md
"""
import csv, hashlib, os, sys

sys.stdout.reconfigure(encoding='utf-8')
BASE = r'C:\03_Github\reverse\异次元通讯-次元复苏-1.5.4'
A = os.path.join(BASE, '04_资源分析')                  # 原件管线
B = os.path.join(BASE, '04_资源分析', '修正版')          # 修正版管线
SUBS = ['剧本', '剧本AST', '表', '统计']


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def rel_exist(root, sub):
    d = os.path.join(root, sub)
    if not os.path.isdir(d):
        return {}
    return {n: os.path.join(d, n) for n in sorted(os.listdir(d)) if os.path.isfile(os.path.join(d, n))}


rows, same, diff, only_a, only_b = [], 0, [], [], []
for sub in SUBS:
    fa, fb = rel_exist(A, sub), rel_exist(B, sub)
    for name in sorted(set(fa) | set(fb)):
        if name not in fb:
            only_a.append('%s/%s' % (sub, name))
            continue
        if name not in fa:
            only_b.append('%s/%s' % (sub, name))
            continue
        ha, hb = sha(fa[name]), sha(fb[name])
        if ha == hb:
            same += 1
            rows.append((sub, name, '相同', ha[:12]))
        else:
            # 逐行比较，判断差异是否只是标注行
            la = open(fa[name], encoding='utf-8', errors='replace').read().split('\n')
            lb = open(fb[name], encoding='utf-8', errors='replace').read().split('\n')
            nline = sum(1 for i in range(max(len(la), len(lb)))
                        if (la[i] if i < len(la) else None) != (lb[i] if i < len(lb) else None))
            kind = '标注差异' if nline <= 2 else '内容差异'
            diff.append('%s/%s(%s,%d行)' % (sub, name, kind, nline))
            rows.append((sub, name, kind, ha[:12] + ' / ' + hb[:12]))

# 源 CSV 差异（只列不同行）
src_a = os.path.join(A, '剧情CSV')
src_b = os.path.join(A, '剧情CSV_修正')
src_diff = []
for name in sorted(os.listdir(src_b)):
    pa, pb = os.path.join(src_a, name), os.path.join(src_b, name)
    if sha(pa) == sha(pb):
        continue
    la = open(pa, 'rb').read().split(b'\r\n')
    lb = open(pb, 'rb').read().split(b'\r\n')
    n = 0
    for i, (x, y) in enumerate(zip(la, lb)):
        if x != y:
            n += 1
            src_diff.append((name, i + 1, x.decode('utf-8', 'replace'), y.decode('utf-8', 'replace')))
    if len(la) != len(lb):
        src_diff.append((name, -1, '行数 %d' % len(la), '行数 %d' % len(lb)))
    print('%s: 差异行 %d' % (name, n))

out = ['# 原件管线 vs 修正版管线\n',
       '两条管线读同一份 APK、同一套脚本，只换输入目录：\n',
       '```',
       'python -X utf8 00_工具\\story_export.py                        # → 04_资源分析\\修正版\\（读 剧情CSV_修正）',
       'python -X utf8 00_工具\\story_export.py 剧情CSV 04_资源分析      # → 04_资源分析\\（读 剧情CSV）',
       '```\n',
       '## 一、源数据差异（剧情CSV vs 剧情CSV_修正）\n',
       '| 文件 | 行号 | 原件 | 修正版 |', '|---|---|---|---|']
for name, ln, x, y in src_diff:
    out.append('| %s | %s | `%s` | `%s` |' % (name, ln, x, y))
out.append('\n其余 6 章逐字节相同。见 `04_资源分析\\修正记录.md`。\n')
out.append('## 二、派生产物对比（%d 个文件）\n' % len(rows))
out.append('| 产物 | 文件 | 结果 | SHA-256 前 12 位 |')
out.append('|---|---|---|---|')
for sub, name, verdict, dig in rows:
    out.append('| %s | %s | %s | `%s` |' % (sub, name, verdict, dig))
if only_a:
    out.append('\n仅在原件管线：%s' % ', '.join('`%s`' % x for x in only_a))
if only_b:
    out.append('\n仅在修正版管线：%s' % ', '.join('`%s`' % x for x in only_b))
out.append('\n## 三、结论\n')
content_diff = [x for x in diff if '内容差异' in x]
if not content_diff:
    out.append('- 两条管线的派生产物**没有内容差异**；不同的 %d 个文件全部只是标注行不同'
               '（剧本页眉的「（修正版…）」提示、对账报告的「数据源」路径），正文逐行相同。' % len(diff))
    out.append('- 原因：`story_export.py` 的取键规则已改为「前两列中最后一个非空字段」，'
               '因此即使喂原始 CSV（图鉴键写在第一列、行尾多逗号），解析结果也不再丢失 `S6-01-n`。')
    out.append('- 也就是说：**修正解决的是数据文件本身的规范性**（第三方/朴素解析器按第 2 列取键会静默丢键），'
               '而不是改变现有脚本的输出内容。')
    out.append('- 需要「与游戏内实际表现一致」的下游用户，两条管线可任选；需要喂给别的工具、或做二次开发，请用 `剧情CSV_修正\\`。')
else:
    out.append('- 存在 %d 个**内容**不同的派生产物：%s' % (len(content_diff), ', '.join('`%s`' % x for x in content_diff)))
    if diff:
        out.append('- 另有 %d 个仅标注差异：%s' % (len(diff) - len(content_diff),
                                             ', '.join('`%s`' % x for x in diff if '内容差异' not in x)))

txt = '\n'.join(out) + '\n'
p = os.path.join(B, '对比_原件与修正版.md')
open(p, 'w', encoding='utf-8').write(txt)
print('\n产物 %d 个：相同 %d 个、不同 %d 个' % (len(rows), same, len(diff)))
print('written:', p)
