# -*- coding: utf-8 -*-
import io, os
R = os.environ['ROOT']
p = os.path.join(R, '06_网页版', 'miko-web', 'app.js')
s = io.open(p, encoding='utf-8').read()

# 1) 设置同步：自动存档间隔
s = s.replace("    if ($('#set-bgm-track')) $('#set-bgm-track').value = st.settings.bgmTrack || 'new';",
"""    if ($('#set-bgm-track')) $('#set-bgm-track').value = st.settings.bgmTrack || 'new';
    if ($('#set-autosave')) $('#set-autosave').value = String(st.settings.autosave || 0);""")

# 2) 绑定：自动存档 + 备份文件
s = s.replace("""    if ($('#set-bgm-track')) $('#set-bgm-track').onchange = function () {
      st.settings.bgmTrack = this.value; save(); applyBgm();
    };""",
"""    if ($('#set-bgm-track')) $('#set-bgm-track').onchange = function () {
      st.settings.bgmTrack = this.value; save(); applyBgm();
    };
    if ($('#set-autosave')) $('#set-autosave').onchange = function () {
      st.settings.autosave = Number(this.value) || 0; save(); startAutosave();
      toast(st.settings.autosave ? ('自动存档：每 ' + st.settings.autosave + ' 秒') : '自动存档已关闭');
    };
    if ($('#btn-autofile')) $('#btn-autofile').onclick = pickBackupFile;
    if ($('#btn-autofile-off')) $('#btn-autofile-off').onclick = function () {
      fileHandle = null; idbSet('saveFile', null).catch(function () {});
      setAutoFileState('未启用');
    };""")

# 3) 启动：开自动存档、恢复文件句柄
s = s.replace("  boot();", """  boot();
  startAutosave();
  restoreBackupFile();""")
io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('part3 ok')
