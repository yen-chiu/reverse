# -*- coding: utf-8 -*-
"""原版《异次元通讯》(com.yinshi.cityline v1.0) 剧情与节奏分析。
输入：01_原始/*.apk 内的 assets/story.txt、assets/50402new.xls
输出：03_分析/ 下的 JSON / CSV / Markdown
"""
import io, os, json, csv, zipfile, math, collections, difflib

WS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APK = os.path.join(WS, '01_原始', '异次元通讯-v1.0-962.apk')
OUT = os.path.join(WS, '03_分析')
TAB = os.path.join(OUT, '表格')
os.makedirs(TAB, exist_ok=True)

z = zipfile.ZipFile(APK)
J = json.loads(z.read('assets/story.txt').decode('utf-8'))
lines = [l for c in J['chapters'] for l in c['subtitlelines']]
CT = {0: 'NPC 消息', 1: '玩家消息', 2: '玩家选项', 3: '未知3', 4: '系统/状态'}

# ---------- 1. 结构化导出 ----------
with io.open(os.path.join(OUT, '原版剧情.json'), 'w', encoding='utf-8') as f:
    json.dump({'version': J.get('version'), 'chapters': J['chapters']}, f, ensure_ascii=False, indent=1)

rows = []
for l in lines:
    rows.append([
        l['chapterId'], l['contentType'], CT.get(l['contentType'], '?'),
        (l['text'] or '').replace('\n', ' '),
        l['busyWaitTime'], l['showTime'],
        l['option1'] or '', l['option1GotoChapterId'] or '',
        l['option2'] or '', l['option2GotoChapterId'] or '',
        l['isNewData'], l['pictureResourceId'],
    ])
with io.open(os.path.join(TAB, '原版第1章.csv'), 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f)
    w.writerow(['节点', 'contentType', '类型', '文本', 'busyWaitTime_ms', 'showTime',
                '选项1', '选项1跳转', '选项2', '选项2跳转', 'isNewData', 'pictureResourceId'])
    w.writerows(rows)

# ---------- 2. 节奏模型 ----------
waits = [l['busyWaitTime'] for l in lines if l.get('busyWaitTime')]
pairs = [(len((l['text'] or '')), l['busyWaitTime']) for l in lines
         if l.get('busyWaitTime') and l['busyWaitTime'] <= 60000 and (l['text'] or '')]
n = len(pairs)
sx = sum(p[0] for p in pairs); sy = sum(p[1] for p in pairs)
sxx = sum(p[0] ** 2 for p in pairs); sxy = sum(p[0] * p[1] for p in pairs)
b = (n * sxy - sx * sy) / (n * sxx - sx * sx)
a = (sy - b * sx) / n
mx, my = sx / n, sy / n
cov = sum((p[0] - mx) * (p[1] - my) for p in pairs) / n
sd1 = math.sqrt(sum((p[0] - mx) ** 2 for p in pairs) / n)
sd2 = math.sqrt(sum((p[1] - my) ** 2 for p in pairs) / n)
r = cov / (sd1 * sd2)

with io.open(os.path.join(TAB, '原版节奏.csv'), 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f)
    w.writerow(['文本', '字数', 'busyWaitTime_ms'])
    for l in lines:
        if (l['text'] or '').strip():
            w.writerow([l['text'].replace('\n', ' '), len(l['text']), l['busyWaitTime']])

big = sorted(set(l['busyWaitTime'] for l in lines if l.get('busyWaitTime', 0) > 60000))
top = collections.Counter(l['busyWaitTime'] for l in lines if l.get('busyWaitTime'))
small = sorted(w for w in waits if w <= 60000)
def pct(v):
    return small[min(len(small) - 1, int(len(small) * v))]

# ---------- 3. 保真度对比（与重置版第一章）----------
REM = os.path.join(os.path.dirname(WS), '异次元通讯-次元复苏-1.5.4-改动')
cmp_md = None
try:
    rows2 = list(csv.reader(io.open(os.path.join(REM, '04_资源分析', '剧情CSV', '第一章.csv'),
                                    encoding='utf-8')))
    rem = [(r[1] or '').strip() for r in rows2 if len(r) > 1 and (r[1] or '').strip()]
    oset = set((l['text'] or '').strip() for l in lines if (l['text'] or '').strip())
    rset = set(rem)
    same = oset & rset
    miss = sorted(oset - rset)
    pairs_near = []
    for t in miss:
        c = difflib.get_close_matches(t, rset, n=1, cutoff=0.45)
        pairs_near.append((t, c[0] if c else ''))
    cmp_md = (len(oset), len(rem), len(rset), len(same), pairs_near)
except Exception as e:  # noqa
    print('对比跳过:', e)

# ---------- 4. 报告 ----------
L = []
L.append('# 原版《异次元通讯》v1.0 剧情数据与节奏分析\n')
L.append('样本：`01_原始/异次元通讯-v1.0-962.apk`（`com.yinshi.cityline`，versionName 1.0，'
         '9,924,566 字节，原生 Android，minSdk 14 / targetSdk 19）。\n')
L.append('## 1. 数据结构\n')
L.append('- 剧情文件：`assets/story.txt`，UTF-8 JSON，%d 字符，顶层 `{chapters, version}`；'
         '`chapters` %d 个节点，共 **%d 行**，%d 条不同文本，最长 %d 字。'
         % (len(z.read('assets/story.txt').decode('utf-8')), len(J['chapters']), len(lines),
            len(set(l['text'] for l in lines if l['text'])), max(len(l['text'] or '') for l in lines)))
L.append('- 每行字段：`chapterId / option1 / option1GotoChapterId / option2 / option2GotoChapterId / '
         'text / busyWaitTime / showTime / isNewData / pictureResourceId / contentType`。')
L.append('- `contentType`：%s。' % '、'.join('%s=%d' % (CT.get(k, k), v)
                                            for k, v in collections.Counter(l['contentType'] for l in lines).most_common()))
L.append('- 节点 id 是数字串（1, 7, 11, 14, 19, 24 … 1220，末尾还有一个 `AAA`），'
         '**分支靠 `*GotoChapterId` 指向目标节点**，与重置版的 `选项N / 分支N` 标签模型同构。\n')
L.append('> 说明：这份 `story.txt` 只覆盖**第一章**（261 个节点）。原版其余章节由服务器下发，'
         'APK 里没有缓存。\n')

L.append('## 2. 节奏：`busyWaitTime`\n')
L.append('每条消息自带一个「对方输入中」的毫秒数，共 %d 条，取值 200 – %d ms：'
         '中位 **%d ms**、p25 %d、p75 %d、p90 %d。\n' % (len(waits), max(waits), sorted(waits)[len(waits)//2],
                                                        pct(.25), pct(.75), pct(.90)))
L.append('对 ≤60 秒的 %d 条按字数做最小二乘：**`wait_ms ≈ %.0f + %.1f × 字数`**（r = %.3f）。'
         '即约 0.5 秒起步、每字 0.175 秒：\n' % (n, a, b, r))
L.append('| 字数 | 2 | 5 | 10 | 20 | 40 |')
L.append('|---|---|---|---|---|---|')
L.append('| 估算 | ' + ' | '.join('%.0f ms' % (a + b * x) for x in (2, 5, 10, 20, 40)) + ' |\n')
L.append('最常见的取值：' + '、'.join('%d ms ×%d' % (k, v) for k, v in top.most_common(8)) + '。\n')
L.append('另有 %d 条 **>60 秒的「离线等待」**（对方下线）：%s。\n'
         % (len([w for w in waits if w > 60000]),
            '、'.join('%d 分' % (w // 60000) if w < 3600000 else '%.0f 小时' % (w / 3600000) for w in big)))
L.append('> 这解释了「原版并没有这么快」：原版平均一条消息要等 2–3 秒，长句 5–7 秒，'
         '而不是即时弹出。\n')

if cmp_md:
    o, remn, remu, same, near = cmp_md
    L.append('## 3. 与重置版的文本保真度\n')
    L.append('- 原版第一章唯一文本 **%d** 条；重置版第一章 %d 行（%d 唯一）。' % (o, remn, remu))
    L.append('- **逐字相同 %d 条**：占原版 %.1f%%，占重置版 %.1f%%。' % (same, 100.0 * same / o, 100.0 * same / remu))
    L.append('- 剩下 %d 条是改写或标点差异，节选（原版 → 重置版最相近的一句）：\n' % len(near))
    for t, c in near[:14]:
        L.append('  - `%s` → %s' % (t[:34], ('`%s`' % c[:34]) if c else '（无相近）'))
    L.append('\n> 结论：开头几屏几乎一字不差（`对方已上线`、`喂！有人看得到吗？`、`有人在线吗？`、'
             '`喂喂！有人吗？`），越往后改写越多；重置版还统一了省略号（`…` → `...`）、'
             '去掉了「Miko酱」等称呼。\n')

L.append('## 4. 与重置版的字段对应\n')
L.append('| 原版 | 重置版 CSV | 说明 |')
L.append('|---|---|---|')
L.append('| `text` | 第 2 列 | 文本 |')
L.append('| `contentType=0` | `左` / `右` | NPC / 玩家消息 |')
L.append('| `contentType=4` | `中` | 系统状态（上线/下线/词典解锁…） |')
L.append('| `option1/2` + `GotoChapterId` | `右,选项,N` | 选项与其目标块 |')
L.append('| `busyWaitTime` | （无） | 原版逐条计时；重置版只保留分钟级 `等待` |')
L.append('| `pictureResourceId` / 文本前缀 `imageN&` | `动态` / `图鉴` | 原版把配图编号塞进文本前缀 |')
L.append('')
L.append('`imageN&` 前缀实例：`image1&我这里能看到星星，你呢` —— 原版用「文本前半截写图片编号」的方式带图，'
         '重置版改成了独立的 `动态` 指令。\n')
L.append('## 5. 原版 UI 素材（与网页版的对照）\n')
L.append('| 原版资源 | 说明 | 网页版 |')
L.append('|---|---|---|')
L.append('| `drawable-xhdpi-v4/unknow_miko_avatar.png` 296×296 | 灰底圆 + 白问号，**未认识时的头像** | 用重置版同款 `未知用户.webp`，一致 |')
L.append('| `chat_left_avatar.png` | 左侧头像（已认识） | `icon/头像2.webp` |')
L.append('| `chat_background*.png`（最大 402 KB） | 聊天背景 | `images/聊天背景.webp` |')
L.append('| `screen_750x1334.png` 等 7 张 | 启动图：夜景街道 + 剪影少女 + 蓝色标题 | 首页顶部 logo 同源 |')
L.append('| `layout/activity_image_gallery.xml` | 图鉴页 | 已按「分章 + n/m + 三列」重做 |')
L.append('| `layout/item_user_moment.xml` / `item_user_profile.xml` | 动态与个人资料卡 | 已按 QQ 空间式重做 |')
L.append('| `layout/item_chat_system_state.xml` | 系统状态气泡 | `.pill` 样式 |')
L.append('')
with io.open(os.path.join(OUT, '原版剧情与节奏分析.md'), 'w', encoding='utf-8', newline='\n') as f:
    f.write('\n'.join(L))

# 给网页版用的节奏表（文本 → 原版毫秒）
with io.open(os.path.join(TAB, '原版节奏_文本映射.csv'), 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f)
    w.writerow(['文本', 'busyWaitTime_ms'])
    seen = set()
    for l in lines:
        t = (l['text'] or '').strip()
        if t and t not in seen and l.get('busyWaitTime'):
            seen.add(t)
            w.writerow([t, l['busyWaitTime']])

print('节点 %d / 行 %d / 唯一文本 %d' % (len(J['chapters']), len(lines), len(set(l['text'] for l in lines if l['text']))))
print('拟合 wait_ms = %.0f + %.1f * 字数  r=%.3f' % (a, b, r))
print('保真度：%s' % (('逐字相同 %d/%d = %.1f%%' % (cmp_md[3], cmp_md[0], 100.0 * cmp_md[3] / cmp_md[0])) if cmp_md else '跳过'))
print('输出：03_分析/原版剧情.json、原版剧情与节奏分析.md、表格/*.csv')
