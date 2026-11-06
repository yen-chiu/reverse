# -*- coding: utf-8 -*-
import io, os
R = os.environ['ROOT']
p = os.path.join(R, '06_网页版', 'miko-web', 'app.js')
s = io.open(p, encoding='utf-8').read()

# ---------- A) 全局：首次手势补播 BGM + 按键音 ----------
old = """  function bind() {
    document.addEventListener('click', function (e) {"""
new = """  function bind() {
    // 第一次交互才允许出声：补播 BGM
    ['pointerdown', 'keydown', 'touchstart'].forEach(function (ev) {
      document.addEventListener(ev, armBgm, { passive: true });
    });

    // 按键音：按钮 / 选项 / 卡片 / 菜单 / 导航
    document.addEventListener('pointerdown', function (e) {
      if (e.target.closest('.choice-btn, .chapter-card, .menu-item, .npc-pick, .ava-opt, .diff-wrap summary, .tab, .btn, button, .end-back')) {
        playClick();
      }
    }, { passive: true });

    document.addEventListener('click', function (e) {"""
assert s.count(old) == 1
s = s.replace(old, new)

# ---------- B) 自动存档 ----------
old2 = """  function loadSave() {"""
new2 = """  /* ---------------- 自动存档 ---------------- */
  var autoTimer = null;
  var fileHandle = null;
  var lastAuto = 0;

  function startAutosave() {
    if (autoTimer) { clearInterval(autoTimer); autoTimer = null; }
    var sec = Number(st.settings.autosave || 0);
    if (!sec) return;
    autoTimer = setInterval(function () {
      if (st.importing) return;
      save();
      lastAuto = Date.now();
      writeBackup();
    }, sec * 1000);
  }

  // ---- 本地文件备份（Chrome/Edge 的 File System Access API）----
  function idb() {
    return new Promise(function (res, rej) {
      var r = indexedDB.open('miko-web', 1);
      r.onupgradeneeded = function () { r.result.createObjectStore('h'); };
      r.onsuccess = function () { res(r.result); };
      r.onerror = function () { rej(r.error); };
    });
  }

  function idbSet(k, v) {
    return idb().then(function (db) {
      return new Promise(function (res, rej) {
        var tx = db.transaction('h', 'readwrite');
        tx.objectStore('h').put(v, k);
        tx.oncomplete = function () { res(1); };
        tx.onerror = function () { rej(tx.error); };
      });
    });
  }

  function idbGet(k) {
    return idb().then(function (db) {
      return new Promise(function (res, rej) {
        var tx = db.transaction('h', 'readonly');
        var q = tx.objectStore('h').get(k);
        q.onsuccess = function () { res(q.result); };
        q.onerror = function () { rej(q.error); };
      });
    });
  }

  function setAutoFileState(txt) {
    var el = $('#autofile-state');
    if (el) el.textContent = txt;
  }

  function writeBackup() {
    if (!fileHandle) return;
    try {
      save();
      var data = localStorage.getItem(SAVE_KEY) || '{}';
      fileHandle.createWritable().then(function (w) {
        return w.write(new Blob([data], { type: 'application/json' })).then(function () { return w.close(); });
      }).then(function () {
        setAutoFileState('已写入 · ' + new Date().toLocaleTimeString('zh-CN'));
      }).catch(function () {
        setAutoFileState('写入失败（可能权限已失效）');
      });
    } catch (e) {}
  }

  function pickBackupFile() {
    if (!window.showSaveFilePicker) {
      toast('这个浏览器不支持自动写文件，请用「导出存档」手动存');
      return;
    }
    window.showSaveFilePicker({
      suggestedName: 'miko-save.json',
      types: [{ description: '存档 JSON', accept: { 'application/json': ['.json'] } }]
    }).then(function (h) {
      fileHandle = h;
      return idbSet('saveFile', h);
    }).then(function () {
      setAutoFileState('已连接，开始自动写入');
      writeBackup();
      toast('已连接本地存档文件');
    }).catch(function (e) {
      if (e && e.name !== 'AbortError') toast('没选文件，已取消');
    });
  }

  function restoreBackupFile() {
    if (!window.showSaveFilePicker) return;
    idbGet('saveFile').then(function (h) {
      if (!h) { setAutoFileState('未启用'); return; }
      fileHandle = h;
      return h.queryPermission({ mode: 'readwrite' }).then(function (st2) {
        if (st2 === 'granted') { setAutoFileState('已连接（' + (h.name || 'save.json') + '）'); writeBackup(); }
        else setAutoFileState('需点「选一个文件」重新授权');
      });
    }).catch(function () { setAutoFileState('未启用'); });
  }

  function loadSave() {"""
assert s.count(old2) == 1
s = s.replace(old2, new2, 1)
io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('part2 ok')
