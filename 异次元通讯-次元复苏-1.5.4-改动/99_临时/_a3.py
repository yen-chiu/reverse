# -*- coding: utf-8 -*-
import io, os
R = os.environ['ROOT']

# index.html：加按键音音频元素
p = os.path.join(R, '06_网页版', 'miko-web', 'index.html')
s = io.open(p, encoding='utf-8').read()
s = s.replace('<audio id="au-sfx" preload="none"></audio>',
              '<audio id="au-sfx" preload="none"></audio>\n<audio id="au-click" src="assets/music/button.ogg" preload="auto"></audio>')
io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('audio el ok', 'au-click' in s)
