# -*- coding: utf-8 -*-
import io, os
R = os.environ['ROOT']
p = os.path.join(R, '06_网页版', 'miko-web', 'README.md')
s = io.open(p, encoding='utf-8').read()
add = """- **主题头像**：她在剧情里发照片（动态）时，头像同步换成与该照片主题对应的一张（表在 `00_工具/web_build.py` 的 `AVATAR_THEME`）：
  第一章 星空自拍 → `头像2`、第二章 咖啡店 → `头像3`、第三章 沙发/遮脸 → `头像8`、第四章 校服 → `头像2`、
  第五章 → `头像6`、第六章 → `头像7`、番外一 → `头像5`（草帽/夏天）、番外二 → `头像4`。
  还没发过照片时用 `头像1`（黑白、无脸的剪影）——就是原作第一章那个「看不清脸」的头像。
"""
if '**主题头像**' not in s:
    i = s.find('- **头像三态**')
    s = s[:i] + add + s[i:]
    io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('readme ok')
