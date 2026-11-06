# -*- coding: utf-8 -*-
"""汇总原版各章「文本 -> busyWaitTime」全量映射

来源：
  ch2.apk  assets/story1   -> 第一章      (v2 JSON，XOR 0x10，subtitlelines[].busyWaitTime)
  ch2.apk  assets/story1_1 -> 番外一
  ch2.apk  assets/story2   -> 第二章
  ch2.apk  assets/story2_1 -> 番外二
  ch3.apk  assets/story_s1 -> 第一章      (v3 节点模型，nextMessageDelayTime)
  ch3.apk  assets/story_s2 -> 第二章
  ch3.apk  assets/story_s3 -> 第三章
  ch3.apk  assets/story_e1 -> 番外一
  ch3.apk  assets/story_e2 -> 番外二

输出：03_分析/表格/原版节奏_全量.csv（章,文本,毫秒,来源）
v3 优先（结构与文案更完备），同章同文本保留首次出现的值。
"""
import os
import csv
import json
import zipfile
import statistics

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, '03_分析', '表格')

V2 = [
    ('ch2.apk', 'story1', '第一章'),
    ('ch2.apk', 'story1_1', '番外一'),
    ('ch2.apk', 'story2', '第二章'),
    ('ch2.apk', 'story2_1', '番外二'),
]
V3 = [
    ('ch3.apk', 'story_s1', '第一章'),
    ('ch3.apk', 'story_s2', '第二章'),
    ('ch3.apk', 'story_s3', '第三章'),
    ('ch3.apk', 'story_e1', '番外一'),
    ('ch3.apk', 'story_e2', '番外二'),
]
ORDER = ['番外一', '番外二', '第一章', '第二章', '第三章', '第四章', '第五章', '第六章']


def cn(node):
    c = node.get('contents') or {}
    return (c.get('ZH_CN') or '').strip() if isinstance(c, dict) else str(c).strip()


def main():
    os.makedirs(OUT, exist_ok=True)
    seen = {}
    order = []
    zips = {}

    for apk, name, chapter in V3 + V2:          # v3 先跑，优先占用
        if apk not in zips:
            zips[apk] = zipfile.ZipFile(os.path.join(BASE, '99_临时', apk))
        raw = zips[apk].read('assets/' + name)
        j = json.loads(bytes(b ^ 0x10 for b in raw).decode('utf-8'))
        n = 0
        if 'storyData' in j:
            for node in j['storyData'].values():
                t = cn(node)
                ms = int(node.get('nextMessageDelayTime') or 0)
                if t and ms and (chapter, t) not in seen:
                    seen[(chapter, t)] = ms
                    order.append((chapter, t, ms, '%s:%s' % (apk, name)))
                    n += 1
        else:
            for ch in j.get('chapters') or []:
                for ln in ch.get('subtitlelines') or []:
                    t = (ln.get('text') or '').strip()
                    ms = int(ln.get('busyWaitTime') or 0)
                    if t and ms and (chapter, t) not in seen:
                        seen[(chapter, t)] = ms
                        order.append((chapter, t, ms, '%s:%s' % (apk, name)))
                        n += 1
        print('%-10s %-8s -> %-5s  新增 %4d 条' % (apk, name, chapter, n))

    order.sort(key=lambda r: (ORDER.index(r[0]) if r[0] in ORDER else 99, -r[2]))
    path = os.path.join(OUT, '原版节奏_全量.csv')
    with open(path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['章', '文本', '毫秒', '来源'])
        for r in order:
            w.writerow(list(r))

    print('\n合计 %d 条 -> %s' % (len(order), path))
    for ch in ORDER:
        vals = [r[2] for r in order if r[0] == ch]
        if vals:
            print('  %-5s %4d 条  中位 %5d ms  p90 %6d  max %8d' % (
                ch, len(vals), statistics.median(vals),
                sorted(vals)[int(len(vals) * 0.9)], max(vals)))


if __name__ == '__main__':
    main()
