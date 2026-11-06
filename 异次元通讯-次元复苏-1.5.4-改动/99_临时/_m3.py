# -*- coding: utf-8 -*-
import io, os
p = os.path.join(os.environ['ROOT'], '06_网页版', 'miko-web', 'app.js')
s = io.open(p, encoding='utf-8').read()

# 1) 设置项：曲目
s = s.replace("speed: 'normal', wait: 1, bgm: false, sfx: true, autoUnlock: false,",
              "speed: 'normal', wait: 1, bgm: false, bgmTrack: 'new', sfx: true, autoUnlock: false,")

# 2) applyBgm 支持两首；换曲时重设 src
old = """  function applyBgm() {
    var a = $('#au-bgm');
    if (st.settings.bgm) {
      if (!a.src) a.src = asset('music/bgm.ogg');
      a.volume = 0.35;
      a.play().catch(function () { /* 需用户交互 */ });
    } else {
      a.pause();
    }
  }"""
new = """  function bgmFile() {
    return st.settings.bgmTrack === 'old' ? 'music/oldBgm.ogg' : 'music/bgm.ogg';
  }

  function applyBgm() {
    var a = $('#au-bgm');
    var want = asset(bgmFile());
    if (st.settings.bgm) {
      if (a.getAttribute('data-src') !== want) {
        a.src = want;
        a.setAttribute('data-src', want);
      }
      a.volume = st.settings.bgmTrack === 'old' ? 0.3 : 0.35;
      a.play().catch(function () { /* 需用户交互后才允许播放 */ });
    } else {
      a.pause();
    }
  }"""
assert s.count(old) == 1
s = s.replace(old, new)

# 3) 设置同步：曲目 + 头像块显隐
old2 = "    $('#set-bgm').checked = !!st.settings.bgm;"
new2 = """    $('#set-bgm').checked = !!st.settings.bgm;
    if ($('#set-bgm-track')) $('#set-bgm-track').value = st.settings.bgmTrack || 'new';
    syncNpcBlock();"""
assert s.count(old2) == 1
s = s.replace(old2, new2)

# 4) 绑定：曲目切换
old3 = """    $('#set-bgm').onchange = function () {
      st.settings.bgm = this.checked; save(); applyBgm();
    };"""
new3 = """    $('#set-bgm').onchange = function () {
      st.settings.bgm = this.checked; save(); applyBgm();
    };
    if ($('#set-bgm-track')) $('#set-bgm-track').onchange = function () {
      st.settings.bgmTrack = this.value; save(); applyBgm();
    };"""
assert s.count(old3) == 1
s = s.replace(old3, new3)

# 5) 头像块显隐：开了「随剧情解锁」就藏掉手动选择
helper = """
  // 「头像随剧情解锁」开着时，角色头像由剧情决定，把手动选择收起来
  function syncNpcBlock() {
    var block = $('#npc-block');
    var hint = $('#npc-hint');
    if (!block) return;
    var locked = st.settings.revealLock !== false;
    block.hidden = locked;
    if (hint) hint.hidden = !locked;
  }
"""
anchor = "  function applyBgm() {"
s = s.replace(anchor, helper + "\n" + anchor, 1)
io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('app ok')
