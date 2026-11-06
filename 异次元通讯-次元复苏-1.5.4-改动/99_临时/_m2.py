# -*- coding: utf-8 -*-
import io, os
p = os.path.join(os.environ['ROOT'], '06_网页版', 'miko-web', 'index.html')
s = io.open(p, encoding='utf-8').read()
old = """<span class="npc-cur" data-cur="未知用户">未知用户</span><i class="chev"></i></button>
      </div>
      <div class="ava-pop" id="ava-pop" hidden></div>"""
new = """<span class="npc-cur" data-cur="未知用户">未知用户</span><i class="chev"></i></button>
      </div>
      </div><!-- /#npc-block -->
      <div class="ava-pop" id="ava-pop" hidden></div>"""
assert s.count(old) == 1
s = s.replace(old, new)
io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('closing ok')
