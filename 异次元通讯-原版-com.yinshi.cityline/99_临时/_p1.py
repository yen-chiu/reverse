# -*- coding: utf-8 -*-
import io, os, re, zipfile
R = os.environ['OV']
terms = ['甜食控','腿玩年','傲娇','Jk制服','JK制服','腿控','自拍','异次元通讯','走在未知的道路上']
res = {}
# 1) assets 文本
apk = os.path.join(R, '01_原始', '异次元通讯-v1.0-962.apk')
z = zipfile.ZipFile(apk)
blob = b''
for n in z.namelist():
    if n.startswith('assets/') and n.endswith(('.txt','.xml','.json')):
        blob += z.read(n)
txt8 = blob.decode('utf-8', 'ignore')
txt16 = blob.decode('utf-16-le', 'ignore')
for t in terms:
    res[t] = (txt8.count(t), txt16.count(t))
print('assets utf8/utf16:', res)
