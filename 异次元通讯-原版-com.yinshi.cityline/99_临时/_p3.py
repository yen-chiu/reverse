# -*- coding: utf-8 -*-
import io, os, re, zipfile
R = os.environ['OV']
apk = os.path.join(R, '01_原始', '异次元通讯-v1.0-962.apk')
arsc = zipfile.ZipFile(apk).read('resources.arsc')
txt = arsc.decode('utf-8', 'ignore')
runs = re.findall(r'[\u4e00-\u9fff][\u4e00-\u9fff0-9A-Za-z：:，。！？·、（）()\-~～…]{0,30}', txt)
seen = []
for r in runs:
    if r not in seen:
        seen.append(r)
print('unique runs', len(seen))
for r in seen:
    print(repr(r))
