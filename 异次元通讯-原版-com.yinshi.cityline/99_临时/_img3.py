import json, os, glob, collections
p = os.path.join(os.environ['OV'], '99_临时', 'ch2.apk')
import zipfile
z = zipfile.ZipFile(p)
raw = z.read('assets/story1')
txt = bytes(b ^ 0x10 for b in raw).decode('utf-8')
import re
idx = [m.start() for m in re.finditer('image', txt, re.I)]
print('story1 image hits:', len(idx))
for i in idx[:5]:
    print('  ', txt[max(0,i-40):i+40].replace('\n',' '))
print()
for f in sorted(glob.glob(os.path.join(os.environ['OV'], '03_分析', '原版v3_*.json'))):
    j = json.load(open(f, encoding='utf-8'))
    sd = j.get('storyData') or {}
    ph = collections.Counter((n.get('photoid') or '') for n in sd.values())
    print(os.path.basename(f), dict(list(ph.items())[:6]))
