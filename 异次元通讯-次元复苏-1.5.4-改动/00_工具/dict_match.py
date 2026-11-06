# -*- coding: utf-8 -*-
"""把 libapp.so 中提取的释义文本块与 CSV 词典词条做内容自证匹配。

匹配依据：释义块内出现词条名本身（忽略大小写、书名号），这是可验证的强证据；
未命中的词条不猜测，留作"待反序列化确认"。
"""
import csv, os, re, sys

sys.stdout.reconfigure(encoding='utf-8')
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAND = os.path.join(BASE, '03_反编译', 'dart_释义候选.txt')
# 用法：python -X utf8 dict_match.py [表目录]；默认 04_资源分析\表
TAB = sys.argv[1] if len(sys.argv) > 1 else os.path.join('04_资源分析', '表')
TAB = TAB if os.path.isabs(TAB) else os.path.join(BASE, TAB)
os.makedirs(TAB, exist_ok=True)
DICT = os.path.join(TAB, '词典.csv')
OUT = os.path.join(TAB, '词典释义_匹配.csv')
OUT_MD = os.path.join(TAB, '词典释义_匹配.md')


def norm(s):
    s = s.replace('《', '').replace('》', '')
    s = s.replace('（', '(').replace('）', ')')
    return s.strip().lower()


cands = []
for line in open(CAND, encoding='utf-8'):
    off, _, txt = line.rstrip('\n').partition('\t')
    cands.append((off, txt))

rows = list(csv.DictReader(open(DICT, encoding='utf-8-sig')))
print('词条 %d 条，释义块 %d 个' % (len(rows), len(cands)))

UI_MARK = ('开：', '关：', 'BE：', '错字是人设', '点击我', '本次启动')


def is_ui(txt):
    return any(m in txt for m in UI_MARK)


out, unmatched, matched_terms, strong = [], [], set(), 0
for r in rows:
    term = r['词条']
    nt = norm(term)
    hits = []
    if nt:
        for off, txt in cands:
            if is_ui(txt):
                continue
            idx = norm(txt).find(nt)
            if idx >= 0:
                hits.append((idx, off, txt))
    if hits:
        hits.sort(key=lambda h: (h[0] > 24, h[0], len(h[2])))
        idx, off, txt = hits[0]
        conf = '强' if idx <= 24 else '弱'
        if conf == '强':
            strong += 1
        out.append([r['编号'], term, r['章节'], r['行号'], off, conf, len(hits), txt])
        matched_terms.add(term)
    else:
        out.append([r['编号'], term, r['章节'], r['行号'], '', '未匹配', 0, ''])
        unmatched.append((r['编号'], term, r['章节'], r['行号']))

with open(OUT, 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f)
    w.writerow(['编号', '词条', '章节', '行号', '释义偏移', '置信度', '候选块数', '释义原文'])
    w.writerows(out)

md = ['# 词典条目 ↔ 释义文本匹配\n',
      '共 %d 条词条：**强匹配 %d 条**（词条名出现在释义开头 24 字内）、弱匹配 %d 条、未匹配 %d 条。'
      '未匹配不代表没有释义——多数释义正文里并不重复词条名（例如 `塞尔提` 的释义以"史特路尔森"开头），'
      '要确定归属必须反序列化 Dart snapshot 才能拿到 id→字符串 的表结构。\n'
      % (len(rows), strong, len(matched_terms) - strong, len(unmatched)),
      '| 编号 | 词条 | 章节:行 | 置信度 | 释义（首 200 字） |',
      '|---|---|---|---|---|']
for r in out:
    prev = r[7].replace('|', '\\|').replace('\n', ' ')[:200] if r[7] else '—'
    md.append('| %s | %s | %s:%s | %s | %s |' % (r[0] or '—', r[1], r[2], r[3], r[5], prev))
open(OUT_MD, 'w', encoding='utf-8').write('\n'.join(md) + '\n')

print('强匹配 %d 条，弱匹配 %d 条，未匹配 %d 条' % (strong, len(matched_terms) - strong, len(unmatched)))
print('\n== 强匹配清单')
for r in out:
    if r[5] == '强':
        print('  [%s] %-10s :: %s' % (r[0] or '—', r[1], r[7][:90].replace('\n', ' ')))
