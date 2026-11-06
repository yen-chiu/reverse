# -*- coding: utf-8 -*-
"""分支标签拓扑统计：标签集合、重复标签、无对应选项的"纯跳转目标"、跳转目标是否存在。"""
import json, os, sys, collections
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.stdout.reconfigure(encoding='utf-8')
AST = os.path.join(BASE, '04_资源分析', '剧本AST')
ORDER = ['番外一', '番外二', '第一章', '第二章', '第三章', '第四章', '第五章', '第六章']
tot_missing = 0
for name in ORDER:
    ev = json.load(open(os.path.join(AST, name + '.json'), encoding='utf-8'))['events']
    labels = collections.Counter()
    opt_ids = set()
    jumps = []
    for e in ev:
        if e['type'] == 'msg' and e.get('branch') is not None:
            labels[e['branch']] += 1
        if e['type'] == 'choice':
            for o in e['options']:
                opt_ids.add(o['target'])
        if e['type'] in ('msg', 'wait') and e.get('jump') is not None:
            jumps.append(e['jump'])
    orphan = sorted(set(labels) - opt_ids)
    dup = sorted(k for k, v in labels.items() if v > 1)
    dangling = sorted(set(jumps) - set(labels))
    tot_missing += len(orphan)
    print('%s: 标签 %d 个(段 %d)，重复标签 %d 个 %s，无选项的纯跳转目标 %d 个 %s，悬空跳转 %s'
          % (name, len(labels), sum(labels.values()), len(dup), dup[:8], len(orphan), orphan[:12], dangling))
print('纯跳转目标合计 %d' % tot_missing)
