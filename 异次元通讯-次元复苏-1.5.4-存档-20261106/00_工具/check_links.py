# -*- coding: utf-8 -*-
"""检查工作区所有 Markdown 里的相对链接与反引号路径是否存在。"""
import os, re, sys

sys.stdout.reconfigure(encoding='utf-8')
BASE = r'C:\03_Github\reverse\异次元通讯-次元复苏-1.5.4'
MDS = ['README.md', '存档清单.md',
       os.path.join('05_报告', '逆向分析报告.md'),
       os.path.join('04_资源分析', '修正记录.md'),
       os.path.join('04_资源分析', '修正版', 'README.md'),
       os.path.join('04_资源分析', '修正版', '对比_原件与修正版.md')]

bad = 0
for rel in MDS:
    p = os.path.join(BASE, rel)
    if not os.path.exists(p):
        print('缺文件:', rel); bad += 1; continue
    txt = open(p, encoding='utf-8').read()
    d = os.path.dirname(p)
    # 1) markdown 链接 ](path)
    for m in re.finditer(r'\]\(([^)#\s]+)', txt):
        t = m.group(1)
        if t.startswith(('http://', 'https://', 'mailto:')):
            continue
        t2 = t.replace('/', os.sep)
        if not os.path.exists(os.path.normpath(os.path.join(d, t2))):
            print('[链接断] %s → %s' % (rel, t)); bad += 1
    # 2) 反引号里形如 xx\yy 的路径（只查工作区内的顶层目录）
    def expands(t):
        """展开并列写法，返回 (候选路径列表, 是否要求全部存在)。

        支持两种速记：
          a\\b.md/.csv   → a\\b.md 与 a\\b.csv（除末段扩展名外的同名兄弟）
          a\\b/c/d      → a\\b、a\\c、a\\d（a 下的同级条目）
        """
        toks = [x for x in t.replace('\\', '/').split('/') if x]
        dots = [i for i, x in enumerate(toks) if x.startswith('.') and i > 0]
        if dots:
            out = ['/'.join(toks)]
            for i in dots:
                prev = toks[i - 1]
                stem = prev.rsplit('.', 1)[0] if '.' in prev else prev
                out.append('/'.join(toks[:i - 1] + [stem + toks[i]]))
            return out, False
        if len(toks) > 2:
            return ['/'.join([toks[0], x]) for x in toks[1:]], True
        return ['/'.join(toks)], False

    def exists(rel_path):
        return os.path.exists(os.path.normpath(os.path.join(BASE, rel_path.replace('/', os.sep))))

    for m in re.finditer(r'`((?:00_工具|01_原始|02_解包|03_反编译|04_资源分析|05_报告|99_临时)[^`]*)`', txt):
        t = m.group(1).rstrip('\\')
        if any(ch in t for ch in '*{…|<>'):
            continue
        cands, need_all = expands(t)
        if exists(t):
            ok = True
        elif need_all:
            ok = all(exists(c) for c in cands)
        else:
            ok = any(exists(c) for c in cands)
        if not ok:
            print('[路径缺] %s → %s' % (rel, t)); bad += 1

print('\n检查 %d 个 Markdown，问题 %d 处' % (len(MDS), bad))
