# -*- coding: utf-8 -*-
"""汇总报告所需的细节事实：章节首屏文本、Day 标记、每章图鉴/动态清单、选项规模。"""
import csv, json, os, sys, collections

sys.stdout.reconfigure(encoding='utf-8')
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AST = os.path.join(BASE, '04_资源分析', '剧本AST')
ORDER = ['番外一', '番外二', '第一章', '第二章', '第三章', '第四章', '第五章', '第六章']

for name in ORDER:
    d = json.load(open(os.path.join(AST, name + '.json'), encoding='utf-8'))
    ev = d['events']
    days = [e['text'] for e in ev if e['type'] == 'day']
    tj = [e['key'] for e in ev if e['type'] == 'tujian']
    dt = [(e['image'], e['text']) for e in ev if e['type'] == 'dongtai']
    ch = [e['options'] for e in ev if e['type'] == 'choice']
    sizes = collections.Counter(len(o) for o in ch)
    first = [e for e in ev if e['type'] in ('msg', 'wait')][:2]
    print('== %s  Day=%s' % (name, days))
    print('   首屏: %s' % ' / '.join('%s:%s' % (f.get('speaker') or '·', f.get('text') or '') for f in first))
    print('   选项规模分布: %s   最大 %d' % (dict(sorted(sizes.items())), max(sizes)))
    print('   图鉴: %s' % tj)
    print('   动态: %s' % ['%s=%s' % (a, b) for a, b in dt])
