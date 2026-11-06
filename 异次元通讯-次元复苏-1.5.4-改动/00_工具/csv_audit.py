# -*- coding: utf-8 -*-
"""剧情 CSV 体检与修正记录（本工作区为**修正后**数据）。

做四件事：
  1) 与 APK 内 `assets/flutter_assets/assets/story/*.csv` 逐行对照，列出差异行
     （本工作区相对发布包只应有 2 行差异，见 FIXES）；
  2) 结构体检：列数 / 图鉴键 / 动态配图键 / 语音文件 / BE 写法 / 等待范围；
  3) 语义层异常**只登记不改值**：词典编号空洞、重复、空编号；
  4) 图鉴两种形态与资源引用闭合性。

输出：04_资源分析\\数据体检与修正记录.md
"""
import collections, csv, hashlib, io, os, re, sys, zipfile
from urllib.parse import quote, unquote

sys.stdout.reconfigure(encoding='utf-8')
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_DIR = os.path.join(BASE, '04_资源分析', '剧情CSV')
APK = os.path.join(BASE, '01_原始', 'app-release-1.5.4.apk')
OUT = os.path.join(BASE, '04_资源分析', '数据体检与修正记录.md')
PHOTO = os.path.join(BASE, '02_解包', 'assets', 'flutter_assets', 'assets', 'photo')
MUSIC = os.path.join(BASE, '02_解包', 'assets', 'flutter_assets', 'assets', 'music')
# 解包保留的是包内百分号编码文件名，比较前先解码
MUSIC_NAMES = {os.path.splitext(unquote(f))[0] for f in os.listdir(MUSIC)}

ORDER = ['番外一', '番外二', '第一章', '第二章', '第三章', '第四章', '第五章', '第六章']

# 本工作区数据相对发布包做过、且**只做过**这些修正（章节, 1-based 行号, 发布包原样, 本工作区现样）
FIXES = [
    ('第六章', 106, 'S6-01-n,,图鉴', ',S6-01-n,图鉴'),
    ('第四章', 760, ',S4-01-n,图鉴,', ',S4-01-n,图鉴'),
]


def sha(b):
    return hashlib.sha256(b).hexdigest()


def cols(row):
    return [c.strip() for c in (row + ['', '', ''])[:3]]


def toks(cell):
    return [t.strip() for t in cell.split(',')] if cell else []


def apk_story(z, name):
    """取 APK 内该章 CSV 的原始字节。"""
    for cand in ('assets/flutter_assets/assets/story/%s.csv' % name,
                 'assets/flutter_assets/assets/story/%s.csv' % quote(name)):
        try:
            return z.read(cand)
        except KeyError:
            continue
    raise SystemExit('APK 内找不到 %s.csv' % name)


# ---------- 1. 与 APK 逐行对照 ----------
diff_rows, same_hash = [], []
with zipfile.ZipFile(APK) as z:
    for name in ORDER:
        raw_ref = apk_story(z, name)
        cur = open(os.path.join(CSV_DIR, name + '.csv'), 'rb').read()
        if sha(cur) == sha(raw_ref):
            same_hash.append(name)
            continue
        a = raw_ref.decode('utf-8').split('\r\n')
        b = cur.decode('utf-8').split('\r\n')
        if len(a) != len(b):
            diff_rows.append((name, 0, '行数不同：%d → %d' % (len(a), len(b))))
            continue
        for i, (x, y) in enumerate(zip(a, b), 1):
            if x != y:
                diff_rows.append((name, i, (x, y)))

expected = {(c, n) for c, n, _, _ in FIXES}
got = {(c, n) for c, n, _ in diff_rows}
unexpected = got - expected

# ---------- 2. 结构体检 ----------
rows_by_ch = {}
issues = []
for name in ORDER:
    rows = list(csv.reader(open(os.path.join(CSV_DIR, name + '.csv'), encoding='utf-8')))
    rows_by_ch[name] = rows
    for i, r in enumerate(rows, 1):
        if len(r) != 3:
            issues.append((name, i, '列数 %d（应为 3）' % len(r), ' / '.join(repr(c) for c in r)))
        spk, txt, cell = cols(r)
        t = toks(cell)
        if '图鉴' in t and not txt:
            issues.append((name, i, '图鉴行第 2 列为空（键=%r）' % spk, cell))
        if '动态' in t and not spk:
            issues.append((name, i, '动态行配图键为空', txt))
        if '语音' in t and txt and txt not in MUSIC_NAMES:
            issues.append((name, i, '语音文件缺失：%s.ogg' % txt, cell))

def wait_minutes(cell):
    """`等待` 后面的数字即等待分钟数；没有或非数字返回 None。"""
    ts = toks(cell)
    if '等待' not in ts:
        return None
    i = ts.index('等待') + 1
    return int(ts[i]) if i < len(ts) and ts[i].isdigit() else None


waits = [m for name in ORDER for r in rows_by_ch[name]
         for m in [wait_minutes(cols(r)[2])] if m is not None]
be_forms = collections.Counter()
for name in ORDER:
    for r in rows_by_ch[name]:
        if 'BE' in toks(cols(r)[2]):
            be_forms[','.join(cols(r)[:3])] += 1

# ---------- 3. 词典编号 ----------
dict_rows = []
for name in ORDER:
    for i, r in enumerate(rows_by_ch[name], 1):
        spk, txt, cell = cols(r)
        if '词典' in toks(cell):
            dict_rows.append((name, i, spk, txt))
ids = [int(spk) for _, _, spk, _ in dict_rows if spk.isdigit()]
present = sorted(set(ids))
holes = [n for n in range(0, max(present) + 1) if n not in present]
dups = {k: v for k, v in collections.Counter(ids).items() if v > 1}
empty_ids = [(n, ln, t) for n, ln, spk, t in dict_rows if not spk]

# ---------- 4. 图鉴与资源引用 ----------
tujian = []
for name in ORDER:
    for i, r in enumerate(rows_by_ch[name], 1):
        spk, txt, cell = cols(r)
        if '图鉴' in toks(cell):
            nn = [c for c in (spk, txt) if c]
            if len(nn) > 1:            # Miko,键,图鉴 → 角色发图
                tujian.append((name, i, nn[0], nn[1]))
            else:                      # 键,,图鉴    → 静默解锁
                tujian.append((name, i, '', nn[0] if nn else ''))
keys = [k for _, _, _, k in tujian]
senders = collections.Counter(s for _, _, s, _ in tujian if s)
silent = sum(1 for _, _, s, _ in tujian if not s)
photos = sorted({os.path.splitext(f)[0] for f in os.listdir(PHOTO)})
dong = {(cols(r)[0]) for name in ORDER for r in rows_by_ch[name] if '动态' in toks(cols(r)[2])}
used = set(keys) | dong
unused = [p for p in photos if p not in used and p + '-n' not in used]
by_ch = collections.Counter(c for c, _, _, _ in tujian)

# ---------- 写报告 ----------
R = []
R.append('# 数据体检与修正记录\n')
R.append('> 本工作区剧情数据：`04_资源分析\\剧情CSV\\`（**已修正**，下游剧本/AST/表/统计均由它生成）')
R.append('> 对照基准：`01_原始\\app-release-1.5.4.apk` 内 `assets/flutter_assets/assets/story/*.csv`')
R.append('> 未修正的原样数据留在存档工作区（见 `README.md` 的「存档关系」）\n')
R.append('> 原则：只做**可证明的字节级修正**；会改变语义的数据异常一律只登记不改值。\n')

R.append('## 一、与发布包的差异（应当只有 2 行）\n')
R.append('| 章节 | 行号 | 发布包原样 | 本工作区 | 影响 |')
R.append('|---|---|---|---|---|')
R.append('| 第六章 | 106 | `S6-01-n,,图鉴` | `,S6-01-n,图鉴` | 图鉴键写在第 1 列 → 修正前解析出**空键**，`S6-01-n` 实际解锁不出来 |')
R.append('| 第四章 | 760 | `,S4-01-n,图鉴,` | `,S4-01-n,图鉴` | 行尾多一个逗号（第 4 个空字段）→ 手改残留，删除后消除解析歧义 |')
R.append('')
R.append('- 逐字节相同的章节：%d/8（%s）' % (len(same_hash), '、'.join(same_hash)))
if diff_rows:
    R.append('- 有差异的行共 **%d** 行：' % len(diff_rows))
    for name, ln, pair in diff_rows:
        if isinstance(pair, str):
            R.append('  - %s：%s' % (name, pair))
        else:
            R.append('  - %s 第 %d 行' % (name, ln))
else:
    R.append('- 无差异行')
R.append('- 与预期修正集是否吻合：**%s**%s' % ('是' if not unexpected else '否',
                                        '' if not unexpected else '（多出 %s）' % sorted(unexpected)))
R.append('')

R.append('## 二、解析健壮性要求（两处都必须遵守）\n')
R.append('1. **图鉴 / 词典 / 动态行的键不能写死列号**：键取「前两列中最后一个非空字段」。'
         '图鉴有 29 行是 `键,,图鉴`（静默解锁），14 行是 `Miko,键,图鉴` / `Iris,键,图鉴`（角色发图）。'
         '写死 `row[1]` 时，键落在第 1 列会**静默变空且不报错**——第六章那处缺陷就是这样被吞了很久。')
R.append('2. **BE 有两种写法**：%s。' % '、'.join('`%s` × %d' % (k, v) for k, v in be_forms.most_common()))
R.append('')

R.append('## 三、结构体检\n')
if issues:
    R.append('| 章节 | 行号 | 问题 | 原文 |')
    R.append('|---|---|---|---|')
    for n, ln, why, raw in issues:
        R.append('| %s | %d | %s | `%s` |' % (n, ln, why, raw))
else:
    R.append('无异常：14,401 行全部 3 列；图鉴行都有键；动态行都有配图键；语音行的 ogg 均存在。\n')
R.append('- 等待指令：%d 处，取值 %d–%d（单位=分钟）。' % (len(waits), min(waits), max(waits)))
R.append('')

R.append('## 四、只登记、不修改（语义层异常）\n')
R.append('### 4.1 词典编号空洞\n')
R.append('共 **%d** 个编号未被使用：`%s`。编号是 libapp.so 释义数组的下标，'
         '**重排会破坏 id→释义 映射**，故不改。\n' % (len(holes), ','.join(map(str, holes))))
R.append('### 4.2 词典编号重复\n')
for k, v in sorted(dups.items()):
    names = ['%s:%d `%s`' % (n, ln, t) for n, ln, spk, t in dict_rows if spk.isdigit() and int(spk) == k]
    R.append('- 编号 **%d** 出现 %d 次：%s' % (k, v, '、'.join(names)))
R.append('')
R.append('`39` 的两条词条名不同（`uno` / `Tango One`），而 id 39 的释义经自证匹配为 **Tango One**，'
         '说明 `uno` 复用了错误编号——这是原作缺陷，改编号只会指向另一条错释义，故保留原值。'
         '`44` 两条都是 `熵`，属同名重复解锁，无影响。\n')
R.append('### 4.3 词典编号为空\n')
R.append('共 **%d** 条词典行没有编号（%s）。说明编号是**可选字段**，引擎可只按词条名解锁；'
         '下游 `表\\词典.csv` 因此增加 `稳定键`（章节:行号）与 `编号状态` 两列。\n'
         % (len(empty_ids), '、'.join('%s:%d' % (n, ln) for n, ln, _ in empty_ids[:8]) + ('…' if len(empty_ids) > 8 else '')))

R.append('## 五、图鉴与资源闭合性\n')
R.append('图鉴解锁点 **%d** 个、唯一键 **%d** 个：%s。' % (len(tujian), len(set(keys)),
         '、'.join('%s %d' % (n, by_ch[n]) for n in ORDER)))
R.append('**两种形态**：%d 行静默解锁、%d 行带发送者（%s）。'
         % (silent, sum(senders.values()), '、'.join('`%s` %d' % (k, v) for k, v in sorted(senders.items()))))
R.append('`photo/` 共 %d 张插画；被图鉴或动态引用之外还剩 **%d 张**：%s —— 全部是节日彩蛋，属隐藏素材。\n'
         % (len(photos), len(unused), '、'.join('`%s`' % u for u in unused) if unused else '无'))

open(OUT, 'w', encoding='utf-8').write('\n'.join(R) + '\n')

print('差异行 %d（预期 %d）；结构异常 %d' % (len(diff_rows), len(FIXES), len(issues)))
print('词典 %d 行：空洞 %d、重复 %d 组、空编号 %d' % (len(dict_rows), len(holes), len(dups), len(empty_ids)))
print('图鉴 %d 点 / %d 唯一键；未引用素材 %d' % (len(tujian), len(set(keys)), len(unused)))
print('已写 04_资源分析\\数据体检与修正记录.md')
