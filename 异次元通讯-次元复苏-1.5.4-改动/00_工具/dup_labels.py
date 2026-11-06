# -*- coding: utf-8 -*-
"""检查重复的 分支 标签是否被任何跳转指向（决定"按标签定位段"在运行时是否唯一）。"""
import json, os, sys, collections
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.stdout.reconfigure(encoding='utf-8')
AST = os.path.join(BASE, '04_资源分析', '剧本AST')
ORDER = ['番外一', '番外二', '第一章', '第二章', '第三章', '第四章', '第五章', '第六章']
for name in ORDER:
    ev = json.load(open(os.path.join(AST, name + '.json'), encoding='utf-8'))['events']
    labels = collections.Counter()
    targets = collections.Counter()
    for e in ev:
        if e['type'] == 'msg' and e.get('branch') is not None:
            labels[e['branch']] += 1
        if e['type'] == 'choice':
            for o in e['options']:
                targets[o['target']] += 1
        if e['type'] in ('msg', 'wait') and e.get('jump') is not None:
            targets[e['jump']] += 1
    dup = [k for k, v in labels.items() if v > 1]
    dup_targeted = [(k, targets[k]) for k in dup if targets[k]]
    print('%s: 重复标签 %d 个，其中被跳转指向的 %d 个 %s' % (name, len(dup), len(dup_targeted), dup_targeted))
