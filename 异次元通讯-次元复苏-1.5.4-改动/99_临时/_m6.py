# -*- coding: utf-8 -*-
import io, os
p = os.path.join(os.environ['ROOT'], '06_网页版', 'miko-web', 'app.js')
s = io.open(p, encoding='utf-8').read()
old = """    var want = asset(bgmFile());
    if (st.settings.bgm) {
      if (a.getAttribute('data-src') !== want) {
        a.src = want;
        a.setAttribute('data-src', want);
      }"""
new = """    var want = asset(bgmFile());
    if (a.getAttribute('data-src') !== want) {
      a.src = want;
      a.setAttribute('data-src', want);
    }
    if (st.settings.bgm) {"""
assert s.count(old) == 1
s = s.replace(old, new)
io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('ok')
