# -*- coding: utf-8 -*-
"""原版《异次元通讯2》内嵌剧情提取（story1/story1_1/story2/story2_1，XOR 0x10）

输出：
  03_分析/原版剧情_<名>.json   解密后的结构化剧情
  03_分析/表格/原版_<名>.csv   每行一行的扁平表
  03_分析/原版第2章与重置版对照.md
"""
import os
import csv
import json
import zipfile
import statistics

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APK = os.path.join(BASE, '99_临时', 'ch2.apk')
OUT = os.path.join(BASE, '03_分析')
TAB = os.path.join(OUT, '表格')
REMAKE = os.path.join(BASE, '..', '异次元通讯-次元复苏-1.5.4-改动', '04_资源分析', '剧情CSV')

FILES = [
    ('story1',   '第1章',  '第一章'),
    ('story1_1', '番外1',  '番外一'),
    ('story2',   '第2章',  '第二章'),
    ('story2_1', '番外2',  '番外二'),
]


def load(zf, name):
    raw = zf.read('assets/' + name)
    dec = bytes(b ^ 0x10 for b in raw)
    return json.loads(dec.decode('utf-8'))


def flat(j):
    rows = []
    for ch in j.get('chapters') or []:
        for ln in ch.get('subtitlelines') or []:
            rows.append({
                'chapter': ch.get('id'),
                'text': ln.get('text') or '',
                'option1': ln.get('option1') or '',
                'goto1': ln.get('option1GotoChapterId') or '',
                'option2': ln.get('option2') or '',
                'goto2': ln.get('option2GotoChapterId') or '',
                'wait': ln.get('busyWaitTime') or 0,
                'ctype': ln.get('contentType'),
                'picture': ln.get('pictureResourceId') or 0,
            })
    return rows


def remake_lines(csv_name):
    p = os.path.join(REMAKE, csv_name + '.csv')
    if not os.path.exists(p):
        return []
    with open(p, encoding='utf-8', newline='') as f:
        return [r[1].strip() for r in csv.reader(f) if len(r) >= 2 and r[1].strip()]


def main():
    os.makedirs(TAB, exist_ok=True)
    zf = zipfile.ZipFile(APK)
    report = ['# 原版第 2 章（及两个番外）与重置版的对照', '']
    summary = []

    for name, label, remake in FILES:
        j = load(zf, name)
        rows = flat(j)

        with open(os.path.join(OUT, '原版剧情_%s.json' % label), 'w', encoding='utf-8') as f:
            json.dump(j, f, ensure_ascii=False, indent=1)

        with open(os.path.join(TAB, '原版_%s.csv' % label), 'w', encoding='utf-8', newline='') as f:
            w = csv.writer(f)
            w.writerow(['节点', '文本', '选项1', '跳转1', '选项2', '跳转2', 'busyWaitTime', 'contentType', '配图'])
            for r in rows:
                w.writerow([r['chapter'], r['text'], r['option1'], r['goto1'],
                            r['option2'], r['goto2'], r['wait'], r['ctype'], r['picture']])

        waits = [int(r['wait']) for r in rows if r['wait']]
        nodes = len({r['chapter'] for r in rows})
        texts = {(r['text'] or '').strip() for r in rows if (r['text'] or '').strip()}
        rl = remake_lines(remake)
        rset = set(rl)
        hit = len(texts & rset)

        summary.append({
            'label': label, 'file': name, 'nodes': nodes, 'lines': len(rows),
            'texts': len(texts), 'remake_lines': len(rl),
            'hit': hit,
            'recall': (hit / len(texts)) if texts else 0,
            'precision': (hit / len(rset)) if rset else 0,
            'wait_median': statistics.median(waits) if waits else 0,
        })

        print('%s  %-8s 节点 %3d  行 %4d  唯一文本 %4d  重置版 %s 行 %4d  逐字相同 %4d  (%.1f%% / %.1f%%)  等待中位 %s ms' % (
            name, label, nodes, len(rows), len(texts), remake, len(rl), hit,
            (hit / len(texts) * 100) if texts else 0,
            (hit / len(rset) * 100) if rset else 0,
            statistics.median(waits) if waits else 0))

    report.append('| 原版文件 | 对应章 | 节点 | 行数 | 唯一文本 | 重置版行数 | 逐字相同 | 原版覆盖率 | 重置版覆盖率 | 等待中位(ms) |')
    report.append('|---|---|---|---|---|---|---|---|---|---|')
    for s in summary:
        report.append('| `assets/%s` | %s | %d | %d | %d | %d | %d | %.1f%% | %.1f%% | %s |' % (
            s['file'], s['label'], s['nodes'], s['lines'], s['texts'], s['remake_lines'],
            s['hit'], s['recall'] * 100, s['precision'] * 100, s['wait_median']))
    report.append('')
    report.append('> 「原版覆盖率」= 原版唯一文本中能在重置版找到逐字相同的比例；'
                  '「重置版覆盖率」= 重置版行中被原版逐字覆盖的比例。')
    with open(os.path.join(OUT, '原版第2章与重置版对照.md'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(report) + '\n')
    print('\n已写 03_分析\\原版第2章与重置版对照.md')


if __name__ == '__main__':
    main()
