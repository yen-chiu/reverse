# -*- coding: utf-8 -*-
"""把修正版剧情 CSV 与资源编译成网页版运行数据。

输入：04_资源分析\剧情CSV\*.csv、04_资源分析\表\*.csv、02_解包\assets\flutter_assets\assets
输出：06_网页版\miko-web\data\*.json、06_网页版\miko-web\assets\*（全部静态资源）

同时做流程模拟校验（见 simulate()）。
"""
import csv
import json
import os
import re
import shutil
import sys
from urllib.parse import unquote

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_DIR = os.path.join(BASE, '04_资源分析', '剧情CSV')
TAB_DIR = os.path.join(BASE, '04_资源分析', '表')
WEB_EXTRA = os.path.join(BASE, '00_工具', 'web_extra')
SRC_ASSETS = os.path.join(BASE, '02_解包', 'assets', 'flutter_assets', 'assets')
WEB = os.path.join(BASE, '06_网页版', 'miko-web')

CHAPTERS = ['番外一', '番外二', '第一章', '第二章', '第三章', '第四章', '第五章', '第六章']

# 章节关系：番外挂在对应主章节下面（首页按「第一章 → 番外 → 第二章 → 番外 → 第三章 …」排列）
EXTRAS = {
    '番外一': {'parent': '第一章', 'title': '你要来我家吃蛋糕吗？'},
    '番外二': {'parent': '第二章', 'title': '令人羞耻的游戏惩罚'},
}

DIRS = {'左': 'left', '中': 'center', '右': 'right'}
KEYWORDS = {'选项', '分支', '等待', '词典', '图鉴', '动态', '语音', 'BE', '无'}


def read_csv(path):
    with open(path, encoding='utf-8', newline='') as f:
        return list(csv.reader(f))


def toks(cell):
    return [t.strip() for t in (cell or '').split(',') if t.strip()]


def parse_cmd(cell):
    """把指令列解析成结构化字段。

    实际词表只有这些 token：`左/中/右`、`选项`、`分支N`（关键字与数字连写）、
    `等待`、`词典/图鉴/动态/语音/BE/无`，以及裸数字（选项目标 / 显式跳转 / 等待分钟）。
    """
    out = {'dir': '', 'choice': None, 'block': None, 'jump': None,
           'wait': None, 'tags': []}
    ts = toks(cell)
    i = 0
    if ts and ts[0] in DIRS:
        out['dir'] = DIRS[ts[0]]
        i = 1
    while i < len(ts):
        t = ts[i]
        m = re.match(r'^分支(\d+)$', t)
        if t == '选项':
            if i + 1 < len(ts) and ts[i + 1].isdigit():
                out['choice'] = int(ts[i + 1])
            i += 2
        elif m:
            out['block'] = int(m.group(1))
            i += 1
        elif t == '等待':
            if i + 1 < len(ts) and ts[i + 1].isdigit():
                out['wait'] = int(ts[i + 1])
            i += 2
        elif t in KEYWORDS:
            out['tags'].append(t)
            i += 1
        elif t.isdigit():
            out['jump'] = int(t)
            i += 1
        else:
            i += 1
    return out


def nonempty(row):
    return [c.strip() for c in (row + ['', ''])[:2] if c.strip()]


def build_chapter(name):
    rows_raw = read_csv(os.path.join(CSV_DIR, name + '.csv'))
    rows = []
    blocks = {}
    choices = []
    for i, r in enumerate(rows_raw):
        who, text, cmd = (r + ['', '', ''])[:3]
        p = parse_cmd(cmd)
        row = {
            'i': i,
            'who': who.strip(),
            'text': text,
            'dir': p['dir'],
            'tags': p['tags'],
        }
        if p['choice'] is not None:
            row['choice'] = p['choice']
        if p['block'] is not None:
            row['block'] = p['block']
            blocks.setdefault(int(p['block']), []).append(i)
        if p['jump'] not in (None, 0):
            row['jump'] = p['jump']
        if p['wait'] is not None:
            row['wait'] = p['wait']
        # 词典 / 图鉴 / 动态 / 语音 的附注字段
        nn = nonempty(r)
        if '词典' in p['tags']:
            row['dictId'] = nn[0] if len(nn) >= 2 else ''
            row['dictTerm'] = nn[-1]
        elif '图鉴' in p['tags']:
            row['key'] = nn[-1]
            if len(nn) > 1:
                row['sender'] = nn[0]
        elif '动态' in p['tags']:
            row['image'] = nn[0] if nn else ''
            row['text'] = nn[1] if len(nn) > 1 else ''
        elif '语音' in p['tags']:
            row['voice'] = text.strip()
        elif '无' in p['tags']:
            row['day'] = text.strip()
        elif 'BE' in p['tags']:
            row['text'] = text.strip()
        rows.append(row)
    # 选项组：连续出现 choice 的行
    cur = []
    for row in rows:
        if 'choice' in row:
            cur.append(row['i'])
        else:
            if len(cur) > 1:
                choices.append(cur)
            cur = []
    if len(cur) > 1:
        choices.append(cur)
    return {'id': name, 'rows': rows, 'blocks': blocks, 'choices': choices}


def make_resolver(blocks):
    """同名标签可能重复（第一章 444/848/936 等），引擎取「引用点之后最近的一处」，
    没有则回绕到章内第一处。"""
    idx = {int(k): sorted(v) for k, v in blocks.items()}

    def resolve(label, ref):
        lst = idx.get(int(label))
        if not lst:
            return None
        for t in lst:
            if t >= ref:
                return t
        return lst[0]
    return resolve


def block_end(rows, idx, starts):
    """块 = 从 分支 标记行起，到下一个 分支 标记行（或章末）之前。"""
    j = idx + 1
    while j < len(rows) and j not in starts:
        j += 1
    return j


def simulate(ch, limit=200000):
    """模拟「顺序播放 + 选项跳块 + 显式跳转 + 兄弟块跳过」模型。

    规则（与网页运行时一致）：
      1. 块 = 从 `分支N` 所在行起，到下一个 `分支` 行（或章末）之前；
      2. 行内有显式数字跳转 → 播完本行 goto 该块；
      3. 选项组 → 进入所选选项的目标块，并记住「兄弟块」集合与该集合之后的回归点；
         播放过程中一旦顺序落到兄弟块的块首（说明本分支的正文已播完），直接跳到回归点。
    """
    rows = ch['rows']
    blocks = {int(k): v[0] for k, v in ch['blocks'].items()}
    labels_at = {}
    for k, v in ch['blocks'].items():
        for t in v:
            labels_at[t] = int(k)
    resolve = make_resolver(ch['blocks'])
    choice_of = {}
    for g in ch['choices']:
        for i in g:
            choice_of[i] = g

    def block_end(idx):
        j = idx + 1
        while j < len(rows) and j not in labels_at:
            j += 1
        return j

    def after_siblings(labels, idx):
        j = idx
        while j < len(rows) and labels_at.get(j) in labels:
            j = block_end(j)
        return j

    seen = set()
    stack = [(0, None, 0)]     # (cursor, ctx, depth)；ctx = (labels, resume)
    nodes = 0
    ends = 0
    broken = []
    reach = set()
    while stack:
        cur, ctx, depth = stack.pop()
        steps = 0
        while True:
            nodes += 1
            steps += 1
            if nodes > limit:
                broken.append(('limit-nodes', cur))
                break
            if steps > 5000 or depth > 600:
                broken.append(('limit-steps', cur))
                break
            if cur >= len(rows):
                ends += 1
                break
            key = (cur, ctx[1] if ctx else None, depth)
            if key in seen:
                break
            seen.add(key)
            reach.add(cur)
            row = rows[cur]
            if ctx and cur >= ctx[1]:
                ctx = None            # 已回到主线
            if 'choice' in row:
                g = choice_of.get(cur, [cur])
                targets = []
                for i in g:
                    t = rows[i].get('choice')
                    if t is None:
                        continue
                    t = resolve(t, i)
                    if t is not None and t not in targets:
                        targets.append(t)
                if not targets:
                    broken.append(('no-target', cur))
                    break
                labels = {labels_at.get(t) for t in targets}
                for t in targets[1:]:
                    stack.append((t, (labels, after_siblings(labels, block_end(t)), t), depth + 1))
                t = targets[0]
                cur = t
                ctx = (labels, after_siblings(labels, block_end(t)), t)
                continue
            if row.get('jump'):
                t = resolve(row['jump'], cur)
                if t is not None:
                    cur = t
                    continue
            if ctx and cur != ctx[2] and labels_at.get(cur) in ctx[0]:
                cur = ctx[1]          # 播完本块后落到兄弟块块首 → 回归主线
                continue
            cur += 1
    return {'rows': len(rows), 'blocks': sum(len(v) for v in ch['blocks'].values()),
            'labels': len(ch['blocks']),
            'reach_rows': len(reach), 'ends': ends, 'broken': broken[:5],
            'broken_n': len(broken), 'nodes': nodes}




# ---- 释义清洗：还原被当作 UTF-16 读出的 ASCII，并裁掉两端扫描噪声 ----
def _is_ascii_pair(cp):
    hi, lo = cp >> 8, cp & 0xffff & 0xff
    return 0x20 <= hi <= 0x7e and 0x20 <= lo <= 0x7e


def _demojibake(text):
    return text          # 慎用：CJK 与「ASCII 双字节」区间重叠，自动还原会损坏正文
    out = []
    buf = []
    for ch in text:
        if _is_ascii_pair(ord(ch)):
            buf.append(ch)
        else:
            if buf:
                out.append(''.join(chr(ord(c) & 0xff) + chr(ord(c) >> 8) for c in buf))
                buf = []
            out.append(ch)
    if buf:
        out.append(''.join(chr(ord(c) & 0xff) + chr(ord(c) >> 8) for c in buf))
    return ''.join(out)


def clean_def(text, charset):
    """裁掉错位扫描粘在释义两端的怪字。

    判据：字符既不是 ASCII、也不在正文用字集合里 → 视为噪声；按 8 字窗口
    的干净比例定位正文真正的起止（单字判据会把「妆」这类常见字误留）。
    """
    t = (text or '').strip()

    def noisy(ch):
        return (not ch.isascii()) and (ch not in charset)

    def dirty_ratio(seg):
        if not seg:
            return 0.0
        return sum(1 for c in seg if noisy(c)) / len(seg)

    i = 0
    while i < len(t) and dirty_ratio(t[i:i + 8]) > 0.3:
        i += 1
    j = len(t)
    while j > i and dirty_ratio(t[max(i, j - 8):j]) > 0.3:
        j -= 1
    t = t[i:j].strip()

    # 括号未闭合 → 后面粘了下一条释义
    if t.count('（') > t.count('）'):
        k = t.rfind('（')
        if k > 0:
            t = t[:k].rstrip('，,、;； ')
    # 句末收尾
    for k in range(len(t) - 1, -1, -1):
        if t[k] in '。！？」』':
            return t[:k + 1]
    return t


def table(name):
    return read_csv(os.path.join(TAB_DIR, name))


RENAME = {'异次元通讯.webp': 'logo-title.webp', '次元复苏.webp': 'logo-sub.webp'}


def copy_assets():
    dst = os.path.join(WEB, 'assets')
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    count = 0
    size = 0
    for root, dirs, files in os.walk(SRC_ASSETS):
        rel = os.path.relpath(root, SRC_ASSETS).replace('\\', '/')
        for fn in files:
            src = os.path.join(root, fn)
            name = unquote(fn)
            if rel == 'story':
                continue  # 剧情已编译成 json
            outdir = os.path.join(dst, *([] if rel == '.' else rel.split('/')))
            os.makedirs(outdir, exist_ok=True)
            # 中文文件名会让 htmlproofer 报错，两张 logo 改成 ASCII 名
            name = RENAME.get(name, name)
            shutil.copy2(src, os.path.join(outdir, name))
            count += 1
            size += os.path.getsize(src)
    # 生成/改色的附加素材（源包里没有）：00_工具\web_extra 下按同样的相对路径覆盖
    if os.path.isdir(WEB_EXTRA):
        for root, dirs, files in os.walk(WEB_EXTRA):
            rel = os.path.relpath(root, WEB_EXTRA).replace('\\', '/')
            for fn in files:
                src2 = os.path.join(root, fn)
                outdir2 = os.path.join(dst, *([] if rel == '.' else rel.split('/')))
                os.makedirs(outdir2, exist_ok=True)
                shutil.copy2(src2, os.path.join(outdir2, fn))
                count += 1
                size += os.path.getsize(src2)
    return count, size


# 主题头像：她发某张照片时，头像同步换成对应主题（键 = 动态图片键）
AVATAR_THEME = {
    'S1-01': '头像2', 'S1-02': '头像2', 'S1-03': '头像2', 'S1-04': '头像2', 'S1-05': '头像2',
    'S2-01': '头像3', 'S2-02': '头像3', 'S2-03': '头像3', 'S2-04': '头像3', 'S2-05': '头像3',
    'S2-06': '头像3', 'S2-07': '头像3', 'S2-08': '头像3',
    'S3-01': '头像8', 'S3-02': '头像8', 'S3-03': '头像8', 'S3-04': '头像8',
    'S4-01': '头像2', 'S4-02': '头像2', 'S4-03': '头像2', 'S4-04': '头像2', 'S4-05': '头像2', 'S4-06': '头像2',
    'S5-01': '头像6', 'S5-02': '头像6', 'S5-03': '头像6', 'S5-05': '头像6', 'S5-06': '头像6',
    'S6-01': '头像7', 'S6-02': '头像7', 'S6-03': '头像7', 'S6-04': '头像7', 'S6-05': '头像7', 'S6-07': '头像7',
    'E1-01': '头像5', 'E1-02': '头像5', 'E2-01': '头像4', 'E2-02': '头像4', 'E2-03': '头像4',
}
AVATAR_DEFAULT = '头像-黑白'   # 知道名字、但还没发过照片时的过渡头像（原版 chat_left_avatar 去蓝边裁圆）

INTRO = {
    # 章节预览卡上的「钩子」：全部取自该章原文（多为原版 2016 文本）
    '第一章': {'tag': '深夜的陌生人', 'hook': ['喂！有人看得到吗？', '有人在线吗？', '喂喂！有人吗？']},
    '第二章': {'tag': '再度上线的她', 'hook': ['hi！你还在吗？', '喂，我是Miko！', '喂喂！陌生人你还在吗？']},
    '第三章': {'tag': '潜入博物馆', 'hook': ['阿ho噶！', '笨蛋', '你除了打问号还有没有的回复啊？']},
    '第四章': {'tag': '学院传说', 'hook': ['你好...', '在吗？', '喂...', '好像没人']},
    '第五章': {'tag': '剧院惊魂', 'hook': ['hi', '在吗', '好些天没跟你讲话了呢']},
    '第六章': {'tag': '医院迷离旧世纪', 'hook': ['嘿...你在吗？', '好久不见呀，你最近还好吗？', '对了，上次歌剧院的事情还没有谢谢你']},
    '番外一': {'tag': '番外篇', 'hook': ['莫西莫西～', '在干嘛？！', '喂！']},
    '番外二': {'tag': '番外篇', 'hook': ['哈喽！', '还活着吗？', '你猜猜我现在在干嘛']},
}

# 空间互动：谁点赞、谁评论、Miko 怎么回。need = 该角色登场过的章节（按剧情进度逐条解锁）
SOCIAL = {
    'E1-01': {'likes': ['Iris'], 'need': '第三章', 'comments': [
        {'who': 'Iris', 'text': '又要做什么奇怪的事？', 'miko': '才、才不是奇怪的事！'}]},
    'E1-02': {'likes': ['Iris', 'Lily'], 'need': '第三章', 'comments': [
        {'who': 'Iris', 'text': '糖分超标了。', 'miko': '就这一次嘛…'},
        {'who': 'Lily', 'text': '看起来能吃。', 'miko': '本来就很好吃！'}]},
    'E2-01': {'likes': ['Lily'], 'need': '第六章', 'comments': [
        {'who': 'Lily', 'text': '……', 'miko': '莉姐你倒是说句话啊'}]},
    'E2-03': {'likes': ['Iris'], 'need': '第三章', 'comments': [
        {'who': 'Iris', 'text': '谁在笑你？', 'miko': '反正不是好人'}]},
    'E2-02': {'likes': ['Iris'], 'need': '第三章', 'comments': [
        {'who': 'Iris', 'text': '删掉。', 'miko': '不删！这张很好看'}]},
    'S1-01': {'likes': ['Iris', 'Lily'], 'need': '第三章', 'comments': [
        {'who': 'Iris', 'text': '那不是星星，是城市的灯。', 'miko': '在我心里就是星星'},
        {'who': 'Lily', 'text': '嗯。', 'miko': '莉姐你也看到过吧'}]},
    'S1-04': {'likes': ['Iris'], 'need': '第三章', 'comments': [
        {'who': 'Iris', 'text': '……', 'miko': '（别问了）'}]},
    'S1-05': {'likes': ['Lily'], 'need': '第六章', 'comments': [
        {'who': 'Lily', 'text': '分我一半。', 'miko': '下次给你带！'}]},
    'S2-01': {'likes': ['Iris'], 'need': '第三章', 'comments': [
        {'who': 'Iris', 'text': '你也是。', 'miko': '嘿嘿'}]},
    'S2-04': {'likes': ['Iris'], 'need': '第三章', 'comments': [
        {'who': 'Iris', 'text': '下次还去。', 'miko': '说好了哦'}]},
    'S2-05': {'likes': ['Iris'], 'need': '第三章', 'comments': [
        {'who': 'Iris', 'text': '这次我请。', 'miko': '那我可要点最贵的'}]},
    'S2-07': {'likes': ['Lily'], 'need': '第六章', 'comments': [
        {'who': 'Lily', 'text': '不违和。', 'miko': '莉姐说的，我记下了'}]},
    'S2-08': {'likes': ['Iris'], 'need': '第三章', 'comments': [
        {'who': 'Iris', 'text': '别发。', 'miko': '晚了！'}]},
    'S2-03': {'likes': ['Lily'], 'need': '第六章', 'comments': [
        {'who': 'Lily', 'text': '好看。', 'miko': '真的吗！'}]},
    'S3-01': {'likes': ['Iris', 'Lily'], 'need': '第三章', 'comments': [
        {'who': 'Iris', 'text': '彼此彼此。', 'miko': '以后请多指教！'}]},
    'S3-03': {'likes': ['Lily'], 'need': '第六章', 'comments': [
        {'who': 'Lily', 'text': '好看。', 'miko': '谢谢莉姐（小声）'}]},
    'S3-04': {'likes': ['Iris'], 'need': '第三章', 'comments': [
        {'who': 'Iris', 'text': '是你自己走出来的。', 'miko': '…嗯'}]},
    'S4-01': {'likes': ['Iris', 'Lily'], 'need': '第三章', 'comments': [
        {'who': 'Iris', 'text': '别客气。', 'miko': '要谢的'},
        {'who': 'Lily', 'text': '…加油。', 'miko': '莉姐这句我截图了'}]},
    'S4-02': {'likes': ['Iris'], 'need': '第三章', 'comments': [
        {'who': 'Iris', 'text': '练完记得吃饭。', 'miko': '知道了知道了'}]},
    'S4-03': {'likes': ['Lily'], 'need': '第六章', 'comments': [
        {'who': 'Lily', 'text': '？？', 'miko': '别问，问就是意外'}]},
    'S4-04': {'likes': ['Iris'], 'need': '第三章', 'comments': [
        {'who': 'Iris', 'text': '谁送的花？', 'miko': '秘密！'}]},
    'S4-05': {'likes': ['Iris'], 'need': '第三章', 'comments': [
        {'who': 'Iris', 'text': '不是。你不是一个人。', 'miko': '…你怎么知道'}]},
    'S4-06': {'likes': ['Iris'], 'need': '第三章', 'comments': [
        {'who': 'Iris', 'text': '复杂的是人，不是世界。', 'miko': '听起来很厉害'}]},
    'S5-01': {'likes': ['Lily'], 'need': '第六章', 'comments': [
        {'who': 'Lily', 'text': '可以。', 'miko': '莉姐说的对'}]},
    'S5-02': {'likes': ['Lily'], 'need': '第六章', 'comments': [
        {'who': 'Lily', 'text': '嗯。', 'miko': '你也试试嘛'}]},
    'S5-03': {'likes': ['Iris'], 'need': '第三章', 'comments': [
        {'who': 'Iris', 'text': '你确实晃了一下午。', 'miko': '不要说出来啊'}]},
    'S5-05': {'likes': ['Lily'], 'need': '第六章', 'comments': [
        {'who': 'Lily', 'text': '抓紧。', 'miko': '抓得紧紧的！'}]},
    'S5-06': {'likes': ['Iris'], 'need': '第三章', 'comments': [
        {'who': 'Iris', 'text': '你也在帮自己。', 'miko': '嗯…好像是这样'}]},
    'S6-01': {'likes': ['Lily'], 'need': '第六章', 'comments': [
        {'who': 'Lily', 'text': '糖有用。', 'miko': '那我也给你一颗'}]},
    'S6-02': {'likes': ['Lily'], 'need': '第六章', 'comments': [
        {'who': 'Lily', 'text': '穿。', 'miko': '好！'}]},
    'S6-03': {'likes': ['Iris'], 'need': '第三章', 'comments': [
        {'who': 'Iris', 'text': '没有人抛弃你。', 'miko': '…谢谢'}]},
    'S6-04': {'likes': ['Iris'], 'need': '第三章', 'comments': [
        {'who': 'Iris', 'text': '不是你的错。', 'miko': '可是…'}]},
    'S6-05': {'likes': ['Lily'], 'need': '第六章', 'comments': [
        {'who': 'Lily', 'text': '大佬。', 'miko': '嘿嘿嘿'}]},
    'S6-07': {'likes': ['Iris', 'Lily'], 'need': '第三章', 'comments': [
        {'who': 'Iris', 'text': '你已经做得很好。', 'miko': '…'}]},
}

def main():
    os.makedirs(os.path.join(WEB, 'data'), exist_ok=True)
    chapters = []
    print('== 编译剧情 ==')
    for name in CHAPTERS:
        ch = build_chapter(name)
        sim = simulate(ch)
        print('%-6s 行 %4d  块 %4d  选项组 %3d  可达行 %4d/%4d  终局 %3d  异常 %d'
              % (name, len(ch['rows']), len(ch['blocks']), len(ch['choices']),
                 sim['reach_rows'], len(ch['rows']), sim['ends'], sim['broken_n']))
        if sim['broken']:
            print('       异常样例:', sim['broken'])
        ch['sim'] = {k: sim[k] for k in ('reach_rows', 'ends', 'broken_n')}
        chapters.append(ch)

    story = {'chapters': chapters, 'generated': '2026-11-06'}
    with open(os.path.join(WEB, 'data', 'story.json'), 'w', encoding='utf-8') as f:
        json.dump(story, f, ensure_ascii=False, separators=(',', ':'))

    # 词典
    dic = []
    for r in table('词典.csv')[1:]:
        if len(r) < 2:
            continue
        dic.append({'id': r[0], 'term': r[1], 'chapter': r[2], 'line': r[3],
                    'key': r[4] if len(r) > 4 else '', 'state': r[5] if len(r) > 5 else ''})
    # 释义（来自匹配表）
    defs = {}
    charset = set()
    for c in CHAPTERS:
        for r in read_csv(os.path.join(CSV_DIR, c + '.csv')):
            for cell in r:
                charset.update(cell)
    p = os.path.join(TAB_DIR, '词典释义_匹配.csv')
    if os.path.exists(p):
        for r in table('词典释义_匹配.csv')[1:]:
            if len(r) >= 8 and r[5] in ('强', '弱') and r[1]:
                defs.setdefault(r[1], {'id': r[0], 'text': clean_def(r[7], charset), 'conf': r[5]})
    # 图鉴
    gal = [{'key': r[0], 'chapter': r[1], 'line': r[2], 'sender': r[3] if len(r) > 3 else ''}
           for r in table('图鉴.csv')[1:] if len(r) >= 3]
    # 动态
    dyn = [{'image': r[0], 'text': r[1], 'chapter': r[2], 'line': r[3], 'who': 'Miko'}
           for r in table('动态.csv')[1:] if len(r) >= 4]

    # 角色资料页（封面 / 签名 / 标签 / 兴趣）
    # 文案全部取自原版 APK com.yinshi.cityline 的 resources.arsc 字符串池：
    #   标签 = 甜食控 / 腿玩年 / 傲娇；兴趣 = 异次元通讯 / JK制服 / 腿控 / 自拍；
    #   签名 = 「走在未知的道路上，不许停也不能回头。」（与包内语音文件名一致）
    profiles = {
        'Miko': {
            'sig': '走在未知的道路上，不许停也不能回头。',
            'tags': ['甜食控', '腿玩年', '傲娇'],
            'interests': ['异次元通讯', 'JK制服', '腿控', '自拍'],
            'age': '妹子 · 16岁',
            'cover': 'images/聊天背景.webp',
        },
        'Iris': {'sig': '', 'tags': [], 'interests': [], 'age': '', 'cover': 'images/菜单背景.webp'},
        'Lily': {'sig': '', 'tags': [], 'interests': [], 'age': '', 'cover': 'images/菜单背景.webp'},
    }
    # 语音
    voi = [{'who': r[0], 'name': r[1], 'chapter': r[2], 'line': r[3]}
           for r in table('语音.csv')[1:] if len(r) >= 4]
    # 章节天数
    days = {}
    for r in table('章节天数.csv')[1:]:
        if len(r) >= 3:
            days.setdefault(r[0], []).append(r[1])

    photo_dir = os.path.join(SRC_ASSETS, 'photo')
    photos = []
    if os.path.isdir(photo_dir):
        for fn in sorted(os.listdir(photo_dir)):
            base = unquote(fn)
            photos.append(base.rsplit('.', 1)[0])

    # 首次自报姓名 = 头像揭示点（原作：未认识时头像是问号）
    # 头像揭示点（原作：未认识时头像是问号）。取「最早出现」的那一处：
    #   ① 角色第一次开口说话（who == 名字）  ② 文本里第一次被点名（含「我叫Miko」这种自报姓名）
    ORDER = ['第一章', '第二章', '第三章', '第四章', '第五章', '第六章', '番外一', '番外二']
    def _ord(cid):
        return ORDER.index(cid) if cid in ORDER else 9

    reveals = {}
    cand = []
    for ch in chapters:
        for r in ch['rows']:
            t = r.get('text') or ''
            for who in ('Miko', 'Iris', 'Lily'):
                spoke = (r.get('who') == who)
                named = (who in t)
                if spoke or named:
                    cand.append((_ord(ch['id']), r['i'], who, ch['id'], r, 'speak' if spoke else 'mention'))
    cand.sort(key=lambda x: (x[0], x[1]))
    for _o, _i, who, cid, r, why in cand:
        if who in reveals:
            continue
        reveals[who] = {'chapter': cid, 'row': r['i'], 'how': why, 'line': (r.get('text') or '')[:40]}

    # 原版节奏：从原版 APK 的 busyWaitTime / nextMessageDelayTime 提取「章 -> 文本 -> 毫秒」映射
    # 来源：异次元通讯2 v2.3（story1/story1_1/story2/story2_1）+ 异次元通讯3 v3.1（story_s1..s3/e1/e2）
    # 拟合兜底：wait_ms ≈ 523 + 175 × 字数；只保留与重置版同章逐字相同的句子
    delay_map = {}
    timing_csv = os.path.join(TAB_DIR, '原版节奏_全量.csv')
    if os.path.isfile(timing_csv):
        want = {}
        for ch in chapters:
            want[ch['id']] = set((r.get('text') or '').strip() for r in ch['rows'])
        with open(timing_csv, encoding='utf-8-sig', newline='') as f:
            for r in csv.reader(f):
                if len(r) >= 3 and r[0].strip() and r[2].strip().isdigit():
                    ch, text, ms = r[0].strip(), r[1].strip(), int(r[2])
                    if text and text in want.get(ch, ()):
                        delay_map.setdefault(ch, {})[text] = ms
    hit = sum(len(v) for v in delay_map.values())
    timing = {'base': 523, 'per': 175,
              'source': '原版 异次元通讯2 v2.3 / 异次元通讯3 v3.1 的 busyWaitTime 与 nextMessageDelayTime'}

    timing = {'base': 523, 'per': 175, 'source': '原版 com.yinshi.cityline v1.0 assets/story.txt busyWaitTime'}

    # 头像：角色第一次「发图」（动态带图 / 图鉴由她发出）时，头像从字母换成人物立绘
    # 只用主线六章：番外不是每个人都会看，头像切换点必须落在主线
    AVA_ORDER = ['第一章', '第二章', '第三章', '第四章', '第五章', '第六章']
    ordered = sorted(chapters, key=lambda c: AVA_ORDER.index(c['id']) if c['id'] in AVA_ORDER else 9)
    avatars = {}
    avatar_events = []
    for ch in ordered:
        for r in ch['rows']:
            who = r.get('who') or ''
            tags = r.get('tags') or []
            if '动态' in tags and r.get('image'):
                who = 'Miko'          # 动态一律由 Miko 发布（数据里第 1 列是图片键）
            elif '图鉴' in tags and r.get('sender'):
                who = r['sender']
            if who not in ('Miko', 'Iris', 'Lily'):
                continue
            if '动态' in tags or '图鉴' in tags:
                if who not in avatars:
                    avatars[who] = {'chapter': ch['id'], 'row': r['i'], 'how': 'photo'}
                if '动态' in tags and r.get('image'):
                    avatar_events.append({
                        'who': who, 'chapter': ch['id'], 'row': r['i'],
                        'image': r.get('image'),
                        'avatar': AVATAR_THEME.get(r.get('image'), AVATAR_DEFAULT),
                    })
    for ch in ordered:
        for r in ch['rows']:
            who = r.get('who') or ''
            if who in ('Miko', 'Iris', 'Lily') and who not in avatars:
                avatars[who] = {'chapter': ch['id'], 'row': r['i'], 'how': 'speak'}

    meta = {'dictionary': dic, 'defs': defs, 'reveals': reveals, 'avatars': avatars, 'avatarEvents': avatar_events, 'avatarDefault': AVATAR_DEFAULT, 'extras': EXTRAS, 'timing': timing, 'delayMap': delay_map, 'gallery': gal, 'dynamics': dyn, 'profiles': profiles, 'intro': INTRO, 'social': SOCIAL,
            'voices': voi, 'days': days, 'photos': photos,
            'chapters': [{'id': c, 'cover': 'chapter/%s.webp' % c, 'days': len(days.get(c, []))}
                         for c in CHAPTERS]}
    with open(os.path.join(WEB, 'data', 'meta.json'), 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, separators=(',', ':'))

    print('== 复制资源 ==')
    n, size = copy_assets()
    print('资源 %d 个 / %.1f MB' % (n, size / 1048576))
    print('词典 %d 条（释义命中 %d）、图鉴 %d、动态 %d、语音 %d'
          % (len(dic), len(defs), len(gal), len(dyn), len(voi)))
    print('原版节奏映射 %d 章 / %d 条（逐字命中的句子）' % (len(delay_map), hit))
    for fn in ('story.json', 'meta.json'):
        print('%s  %.0f KB' % (fn, os.path.getsize(os.path.join(WEB, 'data', fn)) / 1024))


if __name__ == '__main__':
    sys.exit(main())
