# -*- coding: utf-8 -*-
import io, os
R = os.environ['ROOT']
p = os.path.join(R, '00_工具', 'web_build.py')
s = io.open(p, encoding='utf-8').read()
s = s.replace("AVATAR_DEFAULT = '头像-黑白'   # 知道名字、但还没发过照片时的过渡头像（原版 chat_left_avatar 反色）",
              "AVATAR_DEFAULT = '头像-黑白'   # 知道名字、但还没发过照片时的过渡头像（原版 chat_left_avatar 去蓝边裁圆）")
io.open(p, 'w', encoding='utf-8', newline='\n').write(s)

p2 = os.path.join(R, '06_网页版', 'miko-web', 'README.md')
t = io.open(p2, encoding='utf-8').read()
t = t.replace("还没发过照片时用 `头像1`（黑白、无脸的剪影）——就是原作第一章那个「看不清脸」的头像。",
              "还没发过照片时用 `头像-黑白`（原版 `chat_left_avatar.png` 去掉蓝色描边后裁圆，奶白底 + 黑色无脸身影）——就是原作第一章那个「看不清脸」的头像。")
io.open(p2, 'w', encoding='utf-8', newline='\n').write(t)
print('docs ok')
