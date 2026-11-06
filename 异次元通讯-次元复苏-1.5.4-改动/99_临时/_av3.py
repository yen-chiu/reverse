# -*- coding: utf-8 -*-
import os
from PIL import Image, ImageOps
src = os.path.join(os.environ['OV'], '02_解包', 'res', 'drawable-xhdpi-v4', 'chat_left_avatar.png')
dst = os.path.join(os.environ['ROOT'], '00_工具', 'web_extra', 'icon', '头像-黑白.webp')
os.makedirs(os.path.dirname(dst), exist_ok=True)
ImageOps.invert(Image.open(src).convert('RGB')).save(dst, 'WEBP', quality=92, method=6)
print('gen', os.path.getsize(dst))
