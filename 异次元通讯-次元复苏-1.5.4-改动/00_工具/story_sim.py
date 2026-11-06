# -*- coding: utf-8 -*-
"""按两种标签解析策略模拟执行剧本，检验跳转模型的自洽性。

段 = 以 `分支N` 收尾的连续行（末尾无分支的行自成一段）。
跳转：遇到 `选项N` / 裸数字 N 时，找 label==N 的段跳过去。
  A 策略：找「当前段之后最近的」label==N（之后没有则回绕到文件头）
  B 策略：总是找第一处 label==N
输出：可达段占比、可达 BE 段、歧义跳转次数、回绕次数、解析失败次数。
"""
import csv, os, sys, collections

sys.stdout.reconfigure(encoding='utf-8')
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORDER = ['番外一', '番外二', '第一章', '第二章', '第三章', '第四章', '第五章', '第六章']


def tokens(row):
    return [t.strip() for t in (row[2].split(',') if len(row) > 2 else [])]


def load(name):
    rows = list(csv.reader(open(os.path.join(BASE, '04_资源分析', '剧情CSV', name + '.csv'), encoding='utf-8')))
    segs, cur = [], []
    for r in rows:
        cur.append(r)
        lab = None
        for t in tokens(r):
            if t.startswith('分支') and t[2:].isdigit():
                lab = int(t[2:])
        if lab is not None:
            segs.append((lab, cur))
            cur = []
    if cur:
        segs.append((None, cur))
    return segs


def jumps_of(row):
    jt = ot = None
    toks = tokens(row)
    for t in toks:
        if t.isdigit():
            jt = int(t)
            break
    if '选项' in toks:
        i = toks.index('选项')
        if i + 1 < len(toks) and toks[i + 1].isdigit():
            ot = int(toks[i + 1])
    return jt, ot


def build_index(segs):
    idx = collections.defaultdict(list)
    for i, (lab, _) in enumerate(segs):
        if lab is not None:
            idx[lab].append(i)
    return idx


def resolve(idx, lab, cur, strategy):
    cand = idx.get(lab) or []
    if not cand:
        return None, False
    if strategy == 'B':
        return cand[0], False
    for c in cand:
        if c > cur:
            return c, False
    return cand[0], True        # 需要回绕


def walk(segs, idx, strategy):
    """DFS 遍历所有 (段,行) 状态；每个状态只处理一次。"""
    seen = set()
    stack = [(0, 0)]
    amb = wrap = bad = 0
    be_segs = set()
    while stack:
        si, li = stack.pop()
        while True:
            if si >= len(segs):
                bad += 1        # 越过最后一个段（数据缺陷）
                break
            if (si, li) in seen:
                break
            seen.add((si, li))
            lab, rows = segs[si]
            if li >= len(rows):
                si, li = si + 1, 0
                continue
            row = rows[li]
            toks = tokens(row)
            if 'BE' in toks:
                be_segs.add(si)
            jt, ot = jumps_of(row)
            if ot is not None:
                cand = idx.get(ot) or []
                if len(cand) > 1:
                    amb += 1
                nxt, wp = resolve(idx, ot, si, strategy)
                if nxt is None:
                    bad += 1
                    li += 1
                    continue
                wrap += 1 if wp else 0
                stack.append((nxt, 0))      # 分支：推迟处理
                li += 1
                continue
            if jt is not None:
                cand = idx.get(jt) or []
                if len(cand) > 1:
                    amb += 1
                nxt, wp = resolve(idx, jt, si, strategy)
                if nxt is None:
                    bad += 1              # 悬空跳转
                    li += 1
                    continue
                wrap += 1 if wp else 0
                si, li = nxt, 0
                continue
            li += 1
    reach = {s for s, _ in seen}
    return reach, be_segs, amb, wrap, bad, len(seen)


ALL = {}
for name in ORDER:
    segs = load(name)
    idx = build_index(segs)
    print('== %s  段数 %d' % (name, len(segs)))
    for tag, st in (('A 向后最近(可回绕)', 'A'), ('B 第一处', 'B')):
        reach, be, amb, wrap, bad, states = walk(segs, idx, st)
        print('   %-18s 可达段 %3d/%3d (%.0f%%)，可达 BE 段 %2d，歧义跳转 %2d，回绕 %2d，越界 %2d，状态 %d'
              % (tag, len(reach), len(segs), len(reach) * 100.0 / len(segs), len(be), amb, wrap, bad, states))
    ALL[name] = (segs, idx)
