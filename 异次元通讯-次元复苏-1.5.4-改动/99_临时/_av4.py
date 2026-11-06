# -*- coding: utf-8 -*-
import io, os
R = os.environ['ROOT']
p = os.path.join(R, '00_工具', 'web_build.py')
s = io.open(p, encoding='utf-8').read()
if 'WEB_EXTRA' not in s:
    # 1) 常量
    s = s.replace("SRC_ASSETS = ", "WEB_EXTRA = os.path.join(BASE, '00_工具', 'web_extra')\nSRC_ASSETS = ", 1)
    # 2) copy_assets 末尾补一层：把 web_extra 覆盖过去（改色/生成的素材，源包里没有）
    anchor = "    print('资源 %d 文件 / %.1f MB' % (count, size / 1024 / 1024))"
    add = """    # 生成/改色的附加素材（源包里没有），放在 00_工具\\web_extra 下，按同样的相对路径覆盖
    if os.path.isdir(WEB_EXTRA):
        for root, dirs, files in os.walk(WEB_EXTRA):
            rel = os.path.relpath(root, WEB_EXTRA).replace('\\\\', '/')
            for fn in files:
                s2 = os.path.join(root, fn)
                d2 = os.path.join(dst, rel, fn) if rel != '.' else os.path.join(dst, fn)
                os.makedirs(os.path.dirname(d2), exist_ok=True)
                shutil.copy2(s2, d2)
"""
    assert s.count(anchor) == 1
    s = s.replace(anchor, add + anchor)
    io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('copy_assets patched:', 'WEB_EXTRA' in s)
