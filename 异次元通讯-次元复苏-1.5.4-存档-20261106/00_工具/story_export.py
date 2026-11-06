# -*- coding: utf-8 -*-
"""把 assets/story/*.csv 导出为可读剧本、结构化 AST 与统计表。

CSV 语法（逆向所得）：
    说话人,文本,指令列表
指令（逗号分隔）：
    左 / 中 / 右          气泡对齐：左=NPC，右=玩家，中=系统
    N                     跳转：把执行位置移到「以 分支N 结尾的那一段」
    分支N                 段结束标记（同时是标签 N）
    选项,N                玩家可选项；选择后跳转到 分支N
    等待,N                等待 N 分钟（N 与文本"预计N分钟/N小时"一致）
    词典                  解锁词典条目：字段1=条目编号（可为空），文本=词条名
    图鉴                  解锁图鉴：文本=图片键（如 E1-01-n）
    动态                  发布动态页：字段1=图片键，文本=正文
    语音                  语音消息：文本=语音文件名（assets/music/<文本>.ogg）
    BE                    坏结局标记
    无                    无气泡的章节内小标题（文本形如 Day1）
"""
import csv, glob, json, os, re, sys, collections

sys.stdout.reconfigure(encoding='utf-8')

BASE = r'C:\03_Github\reverse\异次元通讯-次元复苏-1.5.4'

# 用法：
#   python -X utf8 story_export.py                        # 默认：修正版 CSV → 04_资源分析\修正版\
#   python -X utf8 story_export.py 剧情CSV 04_资源分析      # 原件 CSV   → 04_资源分析\（剧本/剧本AST/表/统计）
#   python -X utf8 story_export.py 剧情CSV_修正 04_资源分析\修正版
SRC_NAME = sys.argv[1] if len(sys.argv) > 1 else '剧情CSV_修正'
OUT_ROOT = sys.argv[2] if len(sys.argv) > 2 else os.path.join('04_资源分析', '修正版')
SRC = os.path.join(BASE, '04_资源分析', SRC_NAME)
OUT_ROOT = OUT_ROOT if os.path.isabs(OUT_ROOT) else os.path.join(BASE, OUT_ROOT)
FIXED = SRC_NAME.endswith('修正')          # 是否为修正版数据（决定页眉要不要加提示）
OUT_MD = os.path.join(OUT_ROOT, '剧本')
OUT_JSON = os.path.join(OUT_ROOT, '剧本AST')
OUT_TAB = os.path.join(OUT_ROOT, '表')
OUT_STAT = os.path.join(OUT_ROOT, '统计')
for d in (OUT_MD, OUT_JSON, OUT_TAB, OUT_STAT):
    os.makedirs(d, exist_ok=True)

ORDER = ['番外一', '番外二', '第一章', '第二章', '第三章', '第四章', '第五章', '第六章']


def load(name):
    p = os.path.join(SRC, name + '.csv')
    rows = list(csv.reader(open(p, encoding='utf-8'), delimiter=',', quotechar='"'))
    return [(r + ['', '', ''])[:3] for r in rows]


def parse_directives(cell):
    toks = [t.strip() for t in cell.split(',')] if cell else []
    info = {'align': None, 'branch': None, 'jump': None, 'option': None,
            'wait': None, 'dict': False, 'tujian': False, 'dongtai': False,
            'voice': False, 'be': False, 'none': False, 'unknown': []}
    i = 0
    while i < len(toks):
        t = toks[i]
        if t in ('左', '中', '右'):
            info['align'] = t
        elif t == '分支' or re.fullmatch(r'分支\d+', t):
            m = re.search(r'\d+', t)
            info['branch'] = int(m.group()) if m else None
        elif t == '选项':
            i += 1
            if i < len(toks) and toks[i].isdigit():
                info['option'] = int(toks[i])
        elif t == '等待':
            i += 1
            if i < len(toks) and toks[i].isdigit():
                info['wait'] = int(toks[i])
        elif t == '词典':
            info['dict'] = True
        elif t == '图鉴':
            info['tujian'] = True
        elif t == '动态':
            info['dongtai'] = True
        elif t == '语音':
            info['voice'] = True
        elif t == 'BE':
            info['be'] = True
        elif t == '无':
            info['none'] = True
        elif t == '':
            pass
        elif t.isdigit():
            info['jump'] = int(t) if int(t) != 0 else None
        else:
            info['unknown'].append(t)
        i += 1
    return info


def nonempty(row):
    """前两列中非空的字段（保序，不含第三列的指令串）。

    这样对「键写错列」的脏数据免疫：`图鉴` 行的键无论落在第 1 列还是第 2 列都能取到。
    """
    return [c.strip() for c in (row + ['', ''])[:2] if c.strip()]


def chapter_events(name, rows):
    ev = []
    i = 0
    n = len(rows)
    while i < n:
        spk, txt, cell = rows[i]
        info = parse_directives(cell)
        ln = i + 1
        if info['option'] is not None:
            opts = []
            while i < n:
                s2, t2, c2 = rows[i]
                i2 = parse_directives(c2)
                if i2['option'] is None:
                    break
                opts.append({'speaker': s2, 'text': t2, 'target': i2['option'], 'line': i + 1})
                i += 1
            ev.append({'type': 'choice', 'line': opts[0]['line'], 'options': opts})
            continue
        base = {'line': ln}
        nn = nonempty(rows[i])
        if info['be']:
            ev.append(dict(base, type='be'))
        elif info['dict']:
            # 编号可有可无：有编号时 nn=[编号, 词条]，无编号时 nn=[词条]
            did = nn[0] if len(nn) >= 2 else ''
            term = nn[-1] if nn else ''
            ev.append(dict(base, type='dict', id=did, term=term))
        elif info['tujian']:
            # 图鉴行有两种形态：`键,,图鉴`（静默解锁）与 `Miko,键,图鉴`（顺便在聊天里发一张图）
            ev.append(dict(base, type='tujian', key=nn[-1] if nn else '',
                           sender=nn[0] if len(nn) > 1 else ''))
        elif info['dongtai']:
            ev.append(dict(base, type='dongtai',
                           image=nn[0] if nn else '', text=nn[1] if len(nn) > 1 else ''))
        elif info['voice']:
            ev.append(dict(base, type='voice', speaker=spk.strip(), text=txt.strip()))
        elif info['none']:
            ev.append(dict(base, type='day', text=txt.strip()))
        elif info['wait'] is not None:
            ev.append(dict(base, type='wait', text=txt.strip(), minutes=info['wait'],
                           jump=info['jump'], align=info['align']))
        elif txt.strip() == '' and spk.strip() == '' and info['align'] is None:
            ev.append(dict(base, type='blank'))
        else:
            ev.append(dict(base, type='msg', speaker=spk.strip(), text=txt.strip(),
                           align=info['align'], branch=info['branch'], jump=info['jump']))
        if info['unknown']:
            ev[-1]['unknown'] = info['unknown']
        i += 1
    return ev


def render_md(name, ev, stats):
    L = []
    L.append('# %s\n' % name)
    L.append('> 共 %d 行 / %d 条消息 / %d 个选择点（共 %d 个选项）/ %d 个分支段 / 等待合计 %d 分钟 / BE %d 处\n'
             % (stats['rows'], stats['msgs'], stats['options'], stats['option_items'],
                stats['segments'], stats['wait_min'], stats['be']))
    L.append('> 摘自 `assets/story/%s.csv`%s；`[分支N]` 表示该段结束（标签 N），`→N` 表示段结束后跳转到标签 N，'
             '`▸` 后的数字是选择该选项跳转到的标签。\n'
             % (name, '（修正版，见 `04_资源分析` 下的 `修正记录.md`）' if FIXED else ''))
    for e in ev:
        t = e['type']
        if t == 'blank':
            L.append('')
        elif t == 'day':
            L.append('\n---\n\n### %s\n' % e['text'])
        elif t == 'msg':
            who = e['speaker'] or '（系统）'
            tag = []
            if e.get('branch') is not None:
                tag.append('[分支%d]' % e['branch'])
            if e.get('jump') is not None:
                tag.append('→%d' % e['jump'])
            suffix = ('  ' + ' '.join(tag)) if tag else ''
            if e['align'] == '中':
                L.append('· *%s*%s' % (e['text'], suffix))
            else:
                L.append('**%s**：%s%s' % (who, e['text'], suffix))
        elif t == 'wait':
            tag = ('→%d' % e['jump']) if e.get('jump') is not None else ''
            L.append('· *%s* ⏳ 等待 %d 分钟 %s' % (e['text'] or '（无文本）', e['minutes'], tag))
        elif t == 'choice':
            L.append('\n**▶ 选择**')
            for o in e['options']:
                L.append('- ▸ %s：%s  →分支%d' % (o['speaker'] or '我', o['text'], o['target']))
            L.append('')
        elif t == 'dict':
            L.append('· 📖 词典解锁 `%s`：**%s**' % (e['id'] or '—', e['term']))
        elif t == 'tujian':
            who = e.get('sender') or ''
            L.append('· 🖼 图鉴解锁 `%s`%s' % (e['key'], ('（%s 发来图片）' % who) if who else ''))
        elif t == 'dongtai':
            L.append('· 📱 发布动态 `%s`：%s' % (e['image'], e['text']))
        elif t == 'voice':
            L.append('· 🎤 语音（%s）：%s' % (e['speaker'], e['text']))
        elif t == 'be':
            L.append('\n> ⚠ **BE（坏结局）**\n')
        else:
            L.append('· ? %r' % e)
    return '\n'.join(L) + '\n'


def main():
    all_ev = {}
    tab_dict, tab_tujian, tab_dong, tab_voice, tab_day, tab_be = [], [], [], [], [], []
    stat_lines = []
    summary = []
    for name in ORDER:
        rows = load(name)
        ev = chapter_events(name, rows)
        all_ev[name] = ev
        c = collections.Counter(e['type'] for e in ev)
        wait_min = sum(e['minutes'] for e in ev if e['type'] == 'wait')
        segs = [e['branch'] for e in ev if e['type'] == 'msg' and e.get('branch') is not None]
        stats = {'rows': len(rows), 'msgs': c['msg'], 'options': c['choice'],
                 'option_items': sum(len(e['options']) for e in ev if e['type'] == 'choice'),
                 'segments': len(segs), 'wait_min': wait_min, 'be': c['be']}
        md = render_md(name, ev, stats)
        open(os.path.join(OUT_MD, name + '.md'), 'w', encoding='utf-8').write(md)
        json.dump({'chapter': name, 'stats': stats, 'events': ev},
                  open(os.path.join(OUT_JSON, name + '.json'), 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
        for e in ev:
            if e['type'] == 'dict':
                tab_dict.append([e['id'], e['term'], name, e['line']])
            elif e['type'] == 'tujian':
                tab_tujian.append([e['key'], name, e['line'], e.get('sender', '')])
            elif e['type'] == 'dongtai':
                tab_dong.append([e['image'], e['text'], name, e['line']])
            elif e['type'] == 'voice':
                tab_voice.append([e['speaker'], e['text'], name, e['line']])
            elif e['type'] == 'day':
                tab_day.append([name, e['text'], e['line']])
            elif e['type'] == 'be':
                tab_be.append([name, e['line']])
        summary.append((name, stats, c))

    def write_csv(path, header, rows):
        with open(path, 'w', encoding='utf-8-sig', newline='') as f:
            w = csv.writer(f)
            w.writerow(header)
            w.writerows(rows)

    # 词典表：补稳定键与编号状态（编号空洞/重复见 04_资源分析\修正记录.md）
    id_count = collections.Counter(r[0] for r in tab_dict if r[0])

    def dict_status(r):
        if not r[0]:
            return '空编号'
        return '重复' if id_count[r[0]] > 1 else '正常'

    write_csv(os.path.join(OUT_TAB, '词典.csv'),
              ['编号', '词条', '章节', '行号', '稳定键', '编号状态'],
              [[r[0], r[1], r[2], r[3], 'D%s:%d' % (r[2], r[3]), dict_status(r)]
               for r in sorted(tab_dict, key=lambda x: (x[2], x[3]))])
    write_csv(os.path.join(OUT_TAB, '图鉴.csv'), ['图片键', '章节', '行号', '发送者'], tab_tujian)
    write_csv(os.path.join(OUT_TAB, '动态.csv'), ['图片键', '正文', '章节', '行号'], tab_dong)
    write_csv(os.path.join(OUT_TAB, '语音.csv'), ['说话人', '语音名', '章节', '行号'], tab_voice)
    write_csv(os.path.join(OUT_TAB, '章节天数.csv'), ['章节', '小标题', '行号'], tab_day)
    write_csv(os.path.join(OUT_TAB, 'BE节点.csv'), ['章节', '行号'], tab_be)

    # 总览
    L = ['# 剧情结构统计\n',
         '| 章节 | 行数 | 消息 | 选项组 | 选项条目 | 分支段 | 等待合计(分) | 词典 | 图鉴 | 动态 | 语音 | BE | Day |',
         '|---|---|---|---|---|---|---|---|---|---|---|---|---|']
    tot = collections.Counter()
    for name, s, c in summary:
        L.append('| %s | %d | %d | %d | %d | %d | %d | %d | %d | %d | %d | %d | %d |' % (
            name, s['rows'], s['msgs'], s['options'],
            sum(len(e['options']) for e in all_ev[name] if e['type'] == 'choice'),
            s['segments'], s['wait_min'], c['dict'], c['tujian'], c['dongtai'],
            c['voice'], c['be'], c['day']))
        for k in ('rows', 'msgs', 'options', 'segments', 'wait_min', 'dict', 'tujian', 'dongtai', 'voice', 'be', 'day'):
            tot[k] += (s[k] if k in s else c[k])
    L.append('| **合计** | %d | %d | %d | %d | %d | %d | %d | %d | %d | %d | %d | %d |' % (
        tot['rows'], tot['msgs'], tot['options'],
        sum(len(e['options']) for ev in all_ev.values() for e in ev if e['type'] == 'choice'),
        tot['segments'], tot['wait_min'], tot['dict'], tot['tujian'], tot['dongtai'],
        tot['voice'], tot['be'], tot['day']))
    doc = '\n'.join(L) + '\n'
    open(os.path.join(OUT_STAT, '剧情结构统计.md'), 'w', encoding='utf-8').write(doc)
    print(doc)
    print('written:', OUT_MD, OUT_JSON, OUT_TAB, OUT_STAT)


if __name__ == '__main__':
    main()
