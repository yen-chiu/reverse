# -*- coding: utf-8 -*-
import io, os
R = os.environ['ROOT']
p = os.path.join(R, '00_工具', 'web_build.py')
s = io.open(p, encoding='utf-8').read()

if 'WEB_EXTRA = ' not in s:
    s = s.replace("SRC_ASSETS = ", "WEB_EXTRA = os.path.join(BASE, '00_工具', 'web_extra')\nSRC_ASSETS = ", 1)

anchor = "            count += 1\n            size += os.path.getsize(src)\n    return count, size"
add = """            count += 1
            size += os.path.getsize(src)
    # 生成/改色的附加素材（源包里没有）：00_工具\\web_extra 下按同样的相对路径覆盖
    if os.path.isdir(WEB_EXTRA):
        for root, dirs, files in os.walk(WEB_EXTRA):
            rel = os.path.relpath(root, WEB_EXTRA).replace('\\\\', '/')
            for fn in files:
                src2 = os.path.join(root, fn)
                outdir2 = os.path.join(dst, *([] if rel == '.' else rel.split('/')))
                os.makedirs(outdir2, exist_ok=True)
                shutil.copy2(src2, os.path.join(outdir2, fn))
                count += 1
                size += os.path.getsize(src2)
    return count, size"""
assert s.count(anchor) == 1
s = s.replace(anchor, add)
io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('patched', 'WEB_EXTRA = ' in s)
