# -*- coding: utf-8 -*-
import io, os
R = os.environ['ROOT']
p = os.path.join(R, '06_网页版', 'miko-web', 'README.md')
t = io.open(p, encoding='utf-8').read()
add = """
### 声音与自动存档（2026-11-06 追加）

- **音乐恢复**：浏览器禁止无交互自动播放，所以进页面后第一次点击/按键时补播 BGM（`armBgm()`）。
- **按键音**：`music/button.ogg`，按钮 / 选项 / 章节卡 / 菜单 / 头像一个列表点击时播放，与「音效 / 语音」开关共用（90ms 节流防叠音）。
- **曲目**：`重置版 · Chill Bells`（`bgm.ogg`，19.9s）与 `2016 原版 · 旧版音乐`（`oldBgm.ogg`，195.7s）可切，存 `settings.bgmTrack`。
- **自动存档**：`settings.autosave`（0 / 30 / 60 / 180 / 300 秒）定时 `save()` 到 localStorage；默认 60 秒。
- **本地备份文件**：Chrome/Edge 的 File System Access API，选一次 `miko-save.json` 后每次自动存档都写盘；句柄存 IndexedDB（`miko-web/h/saveFile`），下次进入提示重新授权。
"""
if '声音与自动存档' not in t:
    t = t.rstrip() + "\n" + add
io.open(p, 'w', encoding='utf-8', newline='\n').write(t)
print('readme ok')
