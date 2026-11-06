# -*- coding: utf-8 -*-
import io, os
p = os.path.join(os.environ['ROOT'], '06_网页版', 'miko-web', 'app.js')
s = io.open(p, encoding='utf-8').read()
old = """    $('#set-reveal-lock').onchange = function () {
      st.settings.revealLock = this.checked;
      save();
      $$('.ava[data-who]').forEach(function (el) { refreshAvatars(el.getAttribute('data-who')); });
    };"""
new = """    $('#set-reveal-lock').onchange = function () {
      st.settings.revealLock = this.checked;
      save();
      syncNpcBlock();
      $$('.ava[data-who]').forEach(function (el) { refreshAvatars(el.getAttribute('data-who')); });
    };"""
assert s.count(old) == 1
s = s.replace(old, new)
io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('bind ok')
