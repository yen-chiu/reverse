# -*- coding: utf-8 -*-
"""原版《异次元通讯3》(v3.1) 内嵌剧情提取 —— v3 节点模型

story 文件 = XOR 0x10 后的 JSON：
  {"version":1,"storyid":"3","storyData":{nodeId: node},"daysIndex":{...}}
  node = {id, type, contents{ZH_CN}, nextid, nextMessageDelayTime,
          choicesList[{contents,nextid}], day, photoid, scence, requirement}

type: MIKO_TEXT / CHOICE_TEXT / SYSTEM_STATUS_TIPS / SYSTEM_TIMELINE /
      MIKO_PHOTO / GAME_BE / GAME_HE / GAME_END
"""
import os
import csv
import json
import statistics
import zipfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APK = os.path.join(BASE, '99_临时', 'ch3.apk')
OUT = os.path.join(BASE, '03_分析')
TAB = os.path.join(OUT, '表格')
REMAKE = os.path.join(BASE, '..', '异次元通讯-次元复苏-1.5.4-改动', '04_资源分析', '剧情CSV')

FILES = [
    ('story_s1', 'S1', '第一章'),
    ('story_s2', 'S2', '第二章'),
    ('story_s3', 'S3', '第三章'),
    ('story_e1', 'E1', '番外一'),
    ('story_e2', 'E2', '番外二'),
]


def load(zf, name):
    raw = zf.read('assets/' + name)
    return json.loads(bytes(b ^ 0x10 for b in raw).decode('utf-8'))


def cn(node):
    c = node.get('contents') or {}
    if isinstance(c, dict):
        return (c.get('ZH_CN') or '').strip()
    return str(c).strip()


def rows_of(j):
    sd = j.get('storyData') or {}
    rows = []
    for nid, n in sd.items():
        ch = n.get('choicesList') or []
        rows.append({
            'id': nid,
            'type': n.get('type'),
            'text': cn(n),
            'next': n.get('nextid') or '',
            'delay': n.get('nextMessageDelayTime') or 0,
            'days': n.get('day') or '',
            'photo': n.get('photoid') or '',
            'scence': n.get('scence') or '',
            'choice1': cn(ch[0]) if len(ch) > 0 else '',
            'goto1': (ch[0].get('nextid') if len(ch) > 0 else '') or '',
            'choice2': cn(ch[1]) if len(ch) > 1 else '',
            'goto2': (ch[1].get('nextid') if len(ch) > 1 else '') or '',
        })
    return rows, (j.get('daysIndex') or {})


def remake_lines(csv_name):
    p = os.path.join(REMAKE, csv_name + '.csv')
    if not os.path.exists(p):
        return []
    with open(p, encoding='utf-8', newline='') as f:
        return [r[1].strip() for r in csv.reader(f) if len(r) >= 2 and r[1].strip()]


def main():
    os.makedirs(TAB, exist_ok=True)
    zf = zipfile.ZipFile(APK)
    report = ['# 原版 v3（异次元通讯 3）剧情与重置版对照', '',
              '原版 v3.1 的剧情文件是 `story_s1/s2/s3/e1/e2`，XOR 0x10 后为 JSON；'
              '每个节点自带 `nextMessageDelayTime`（毫秒），选项写在 `choicesList`。', '']
    report.append('| 文件 | 章 | 节点 | MIKO/CHOICE/系统 | 唯一文本 | 重置版行数 | 逐字相同 | 原版覆盖率 | 等待中位 | 最长等待 |')
    report.append('|---|---|---|---|---|---|---|---|---|---|')

    for name, tag, remake in FILES:
        j = load(zf, name)
        rows, days = rows_of(j)
        with open(os.path.join(OUT, '原版v3_%s.json' % remake), 'w', encoding='utf-8') as f:
            json.dump(j, f, ensure_ascii=False, indent=1)
        with open(os.path.join(TAB, '原版v3_%s.csv' % remake), 'w', encoding='utf-8', newline='') as f:
            w = csv.writer(f)
            w.writerow(['节点', '类型', '文本', '下一节点', '延时ms', 'Day', '配图', '场景',
                        '选项1', '跳转1', '选项2', '跳转2'])
            for r in rows:
                w.writerow([r['id'], r['type'], r['text'], r['next'], r['delay'], r['days'],
                            r['photo'], r['scence'], r['choice1'], r['goto1'], r['choice2'], r['goto2']])

        texts = {r['text'] for r in rows if r['text']}
        rl = remake_lines(remake)
        hit = len(texts & set(rl))
        delays = [int(r['delay']) for r in rows if r['delay']]
        kinds = {}
        for r in rows:
            kinds[r['type']] = kinds.get(r['type'], 0) + 1
        print('%s %-6s 节点 %4d  %-42s 唯一文本 %4d  重置版 %4d 行  逐字 %4d (%.1f%%) 中位 %5d ms  max %d  Day %s' % (
            name, remake, len(rows),
            ' '.join('%s=%d' % (k, v) for k, v in sorted(kinds.items(), key=lambda x: -x[1])[:3]),
            len(texts), len(rl), hit, (hit / len(texts) * 100) if texts else 0,
            statistics.median(delays) if delays else 0, max(delays) if delays else 0,
            ','.join(sorted(days.keys()))))
        report.append('| `%s` | %s | %d | %s | %d | %d | %d | %.1f%% | %s ms | %d ms |' % (
            name, remake, len(rows),
            ' / '.join('%d' % v for k, v in sorted(kinds.items(), key=lambda x: -x[1])[:3]),
            len(texts), len(rl), hit, (hit / len(texts) * 100) if texts else 0,
            statistics.median(delays) if delays else 0, max(delays) if delays else 0))

    with open(os.path.join(OUT, '原版v3对照.md'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(report) + '\n')
    print('\n已写 03_分析\\原版v3对照.md')


if __name__ == '__main__':
    main()
