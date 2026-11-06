# -*- coding: utf-8 -*-
import io, os
R = os.environ['ROOT']
p = os.path.join(R, '00_工具', 'web_build.py')
s = io.open(p, encoding='utf-8').read()

old = """            if who not in ('Miko', 'Iris', 'Lily') or who in avatars:
                continue
            if '动态' in tags or '图鉴' in tags:
                avatars[who] = {'chapter': ch['id'], 'row': r['i'], 'how': 'photo'}"""
new = """            if who not in ('Miko', 'Iris', 'Lily'):
                continue
            if '动态' in tags or '图鉴' in tags:
                if who not in avatars:
                    avatars[who] = {'chapter': ch['id'], 'row': r['i'], 'how': 'photo'}
                if '动态' in tags and r.get('image'):
                    avatar_events.append({
                        'who': who, 'chapter': ch['id'], 'row': r['i'],
                        'image': r.get('image'),
                        'avatar': AVATAR_THEME.get(r.get('image'), AVATAR_DEFAULT),
                    })"""
assert s.count(old) == 1
s = s.replace(old, new)

# 声明 avatar_events
s = s.replace("    avatars = {}\n    for ch in ordered:",
              "    avatars = {}\n    avatar_events = []\n    for ch in ordered:", 1)

# 并入 meta
s = s.replace("'avatars': avatars,", "'avatars': avatars, 'avatarEvents': avatar_events, 'avatarDefault': AVATAR_DEFAULT,", 1)
io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('ok', s.count('avatar_events'))
