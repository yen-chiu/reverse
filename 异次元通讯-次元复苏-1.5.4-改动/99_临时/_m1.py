# -*- coding: utf-8 -*-
import io, os
R = os.environ['ROOT']

# ---------- index.html ----------
p = os.path.join(R, '06_网页版', 'miko-web', 'index.html')
s = io.open(p, encoding='utf-8').read()

# 1) 背景音乐下面加「曲目」选择
old_bgm = """      <div class="set-row">
        <span>背景音乐</span>
        <label class="switch"><input type="checkbox" id="set-bgm"><i></i></label>
      </div>"""
new_bgm = """      <div class="set-row">
        <span>背景音乐</span>
        <label class="switch"><input type="checkbox" id="set-bgm"><i></i></label>
      </div>
      <div class="set-row">
        <span>曲目</span>
        <select id="set-bgm-track" class="set-select">
          <option value="new">重置版 · Chill Bells</option>
          <option value="old">2016 原版 · 旧版音乐</option>
        </select>
      </div>"""
assert s.count(old_bgm) == 1
s = s.replace(old_bgm, new_bgm)

# 2) 角色头像整块包起来，便于随「头像随剧情解锁」隐藏
s = s.replace("""      <div class="set-row set-plain" style="margin-top:10px">
        <span>角色头像</span>
        <span class="set-hint">按喜好更换</span>
      </div>
      <div class="npc-row">""",
"""      <div id="npc-block">
      <div class="set-row set-plain" style="margin-top:10px">
        <span>角色头像</span>
        <span class="set-hint">按喜好更换</span>
      </div>
      <p class="set-note" id="npc-hint" hidden style="margin:0 2px 8px;text-align:left">
        已开启「头像随剧情解锁」：角色头像由剧情自动更换（问号 → 黑白 → 主题头像）。
        想手动指定，先把上面那个开关关掉。
      </p>
      <div class="npc-row">""")
io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('html ok')
