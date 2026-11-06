# -*- coding: utf-8 -*-
import io, os
p = os.path.join(os.environ['ROOT'], '06_网页版', 'miko-web', 'app.js')
s = io.open(p, encoding='utf-8').read()
if "settings.bgmTrack = d.settings.bgmTrack" not in s:
    s = s.replace("      if (d.settings) {",
"""      if (d.settings) {
        if (!d.settings.bgmTrack) d.settings.bgmTrack = 'new';""", 1)
io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('migrate ok', 'settings.bgmTrack = d.settings.bgmTrack' in s)
