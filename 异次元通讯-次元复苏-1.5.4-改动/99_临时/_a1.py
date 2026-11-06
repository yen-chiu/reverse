# -*- coding: utf-8 -*-
import io, os
R = os.environ['ROOT']
p = os.path.join(R, '06_网页版', 'miko-web', 'index.html')
s = io.open(p, encoding='utf-8').read()

# 自动存档间隔 + 本地备份文件
old = """      <div class="set-row">
        <span>曲目</span>
        <select id="set-bgm-track" class="set-select">
          <option value="new">重置版 · Chill Bells</option>
          <option value="old">2016 原版 · 旧版音乐</option>
        </select>
      </div>"""
new = """      <div class="set-row">
        <span>曲目</span>
        <select id="set-bgm-track" class="set-select">
          <option value="new">重置版 · Chill Bells</option>
          <option value="old">2016 原版 · 旧版音乐</option>
        </select>
      </div>
      <div class="set-row">
        <span>自动存档间隔</span>
        <select id="set-autosave" class="set-select">
          <option value="0">关闭</option>
          <option value="30">每 30 秒</option>
          <option value="60">每 1 分钟</option>
          <option value="180">每 3 分钟</option>
          <option value="300">每 5 分钟</option>
        </select>
      </div>
      <div class="set-row">
        <span>本地备份文件</span>
        <span class="set-hint" id="autofile-state">未启用</span>
      </div>
      <div class="two-btn" style="margin:2px 0 6px">
        <button id="btn-autofile" class="ghost-btn">选一个文件，自动写盘</button>
        <button id="btn-autofile-off" class="ghost-btn">停止</button>
      </div>"""
assert s.count(old) == 1
s = s.replace(old, new)
io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('html ok')
