# -*- coding: utf-8 -*-
import io, os, re
R = os.environ['ROOT']
p = os.path.join(R, '00_工具', 'web_build.py')
s = io.open(p, encoding='utf-8').read()

# 主题头像：按「照片」选，一张图一个主题；主角设定表，方便以后调
theme_block = '''
# 主题头像：她发某张照片时，头像同步换成对应主题（键 = 动态图片键）
AVATAR_THEME = {
    'S1-01': '头像2', 'S1-02': '头像2', 'S1-03': '头像2', 'S1-04': '头像2', 'S1-05': '头像2',
    'S2-01': '头像3', 'S2-02': '头像3', 'S2-03': '头像3', 'S2-04': '头像3', 'S2-05': '头像3',
    'S2-06': '头像3', 'S2-07': '头像3', 'S2-08': '头像3',
    'S3-01': '头像8', 'S3-02': '头像8', 'S3-03': '头像8', 'S3-04': '头像8',
    'S4-01': '头像2', 'S4-02': '头像2', 'S4-03': '头像2', 'S4-04': '头像2', 'S4-05': '头像2', 'S4-06': '头像2',
    'S5-01': '头像6', 'S5-02': '头像6', 'S5-03': '头像6', 'S5-05': '头像6', 'S5-06': '头像6',
    'S6-01': '头像7', 'S6-02': '头像7', 'S6-03': '头像7', 'S6-04': '头像7', 'S6-05': '头像7', 'S6-07': '头像7',
    'E1-01': '头像5', 'E1-02': '头像5', 'E2-01': '头像4', 'E2-02': '头像4', 'E2-03': '头像4',
}
AVATAR_DEFAULT = '头像1'   # 知道名字、但还没发过照片时的过渡头像（黑白无脸剪影）

'''
if 'AVATAR_THEME' not in s:
    i = s.index('INTRO = {')
    s = s[:i] + theme_block + s[i:]

# 收集每张带图动态为一个「换头像」事件
old = """    avatars = {}
    for ch in ordered:"""
new = """    avatars = {}
    avatar_events = []
    for ch in ordered:"""
assert s.count(old) == 1
s = s.replace(old, new)

old2 = """            if '动态' in tags and r.get('image'):
                avatars.setdefault(who or 'Miko', {'chapter': ch['id'], 'row': r['i'], 'how': 'photo'})"""
new2 = """            if '动态' in tags and r.get('image'):
                owner = who or 'Miko'
                avatars.setdefault(owner, {'chapter': ch['id'], 'row': r['i'], 'how': 'photo'})
                avatar_events.append({'who': owner, 'chapter': ch['id'], 'row': r['i'],
                                      'image': r.get('image'),
                                      'avatar': AVATAR_THEME.get(r.get('image'), AVATAR_DEFAULT)})"""
assert s.count(old2) == 1, s.count(old2)
s = s.replace(old2, new2)

old3 = "    meta['avatars'] = avatars"
if old3 not in s:
    old3 = "'avatars': avatars"
    assert s.count(old3) >= 1
    s = s.replace(old3, "'avatars': avatars, 'avatarEvents': avatar_events, 'avatarDefault': AVATAR_DEFAULT", 1)
else:
    s = s.replace(old3, old3 + "\n    meta['avatarEvents'] = avatar_events\n    meta['avatarDefault'] = AVATAR_DEFAULT")
io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('build patch ok')
