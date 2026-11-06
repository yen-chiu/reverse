# -*- coding: utf-8 -*-
import io, os, re, zipfile
R = os.environ['OV']
terms = ['甜食控','腿玩年','傲娇','Jk制服','JK制服','腿控','自拍','走在未知']
apk = os.path.join(R, '01_原始', '异次元通讯-v1.0-962.apk')
z = zipfile.ZipFile(apk)
dex = z.read('classes.dex')
arsc = z.read('resources.arsc')
def scan(name, blob):
    out = {}
    for t in terms:
        n8 = blob.count(t.encode('utf-8'))
        n16 = blob.count(t.encode('utf-16-le'))
        out[t] = (n8, n16)
    print(name, out)
scan('dex', dex)
scan('arsc', arsc)
# 也扫一下 resources.arsc 里的 UTF-8 串样本
i = arsc.find('标签'.encode('utf-8'))
print('arsc 标签 idx', i)
