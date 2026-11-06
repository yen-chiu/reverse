# -*- coding: utf-8 -*-
import io, os
R = os.environ['ROOT']

# 构建脚本：默认过渡头像换成生成的黑白头像
p = os.path.join(R, '00_工具', 'web_build.py')
s = io.open(p, encoding='utf-8').read()
s = s.replace("AVATAR_DEFAULT = '头像1'   # 知道名字、但还没发过照片时的过渡头像（黑白无脸剪影）",
              "AVATAR_DEFAULT = '头像-黑白'   # 知道名字、但还没发过照片时的过渡头像（原版 chat_left_avatar 反色）")
io.open(p, 'w', encoding='utf-8', newline='\n').write(s)

# 前端：头像选择列表补上这张；默认兜底也改成它
p2 = os.path.join(R, '06_网页版', 'miko-web', 'app.js')
a = io.open(p2, encoding='utf-8').read()
a = a.replace("var AVATARS = ['头像1', '头像2', '头像3', '头像4', '头像5', '头像6', '头像7', '头像8'];",
              "var AVATARS = ['头像-黑白', '头像1', '头像2', '头像3', '头像4', '头像5', '头像6', '头像7', '头像8'];")
a = a.replace("((st.meta && st.meta.avatarDefault) || '头像1')", "((st.meta && st.meta.avatarDefault) || '头像-黑白')")
io.open(p2, 'w', encoding='utf-8', newline='\n').write(a)
print('patched')
