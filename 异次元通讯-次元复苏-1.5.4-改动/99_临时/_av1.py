# -*- coding: utf-8 -*-
import os
from PIL import Image, ImageOps
src = os.path.join(os.environ['OV'], '02_解包', 'res', 'drawable-xhdpi-v4', 'chat_left_avatar.png')
out_dir = os.path.join(os.environ['ROOT'], '06_网页版', 'miko-web', 'assets', 'icon')
os.makedirs(out_dir, exist_ok=True)
im = Image.open(src).convert('RGB')
inv = ImageOps.invert(im)
dst = os.path.join(out_dir, '头像-黑白.webp')
inv.save(dst, 'WEBP', quality=92, method=6)
print(dst, os.path.getsize(dst))
