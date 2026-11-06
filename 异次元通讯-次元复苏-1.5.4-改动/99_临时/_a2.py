# -*- coding: utf-8 -*-
import io, os
R = os.environ['ROOT']
p = os.path.join(R, '06_网页版', 'miko-web', 'app.js')
s = io.open(p, encoding='utf-8').read()

# ---------- 1) 设置项默认值 ----------
s = s.replace("speed: 'normal', wait: 1, bgm: false, bgmTrack: 'new', sfx: true, autoUnlock: false,",
              "speed: 'normal', wait: 1, bgm: false, bgmTrack: 'new', sfx: true, autoUnlock: false, autosave: 60,")

# ---------- 2) 音乐：浏览器策略要求的首次手势解锁 ----------
old_apply = """  function bgmFile() {"""
new_apply = """  var bgmArmed = false;

  // 浏览器不允许无手势自动播放：在第一次点击/按键时补上
  function armBgm() {
    if (bgmArmed) return;
    bgmArmed = true;
    if (st.settings.bgm) applyBgm();
  }

  function bgmFile() {"""
assert s.count(old_apply) == 1
s = s.replace(old_apply, new_apply)

# ---------- 3) 按键音效 ----------
old_sfx = """  function playVoice(name) {"""
new_sfx = """  var lastSfx = 0;

  // 界面按键音（button.ogg），与语音共用「音效 / 语音」开关
  function playClick() {
    if (!st.settings.sfx) return;
    var now = Date.now();
    if (now - lastSfx < 90) return;
    lastSfx = now;
    var a = $('#au-click');
    if (!a) return;
    try {
      a.currentTime = 0;
      a.play().catch(function () {});
    } catch (e) {}
  }

  function playVoice(name) {"""
assert s.count(old_sfx) == 1
s = s.replace(old_sfx, new_sfx)
io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('part1 ok')
