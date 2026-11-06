# -*- coding: utf-8 -*-
"""APK 结构与签名证书细节：ZIP 清单、目录聚合、体积 Top、证书 RDN（GBK 还原）。"""
import csv, os, sys, zipfile, collections

sys.stdout.reconfigure(encoding='utf-8')
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APK = os.path.join(BASE, '01_原始', 'app-release-1.5.4.apk')
OUT = os.path.join(BASE, '04_资源分析', '表')

zf = zipfile.ZipFile(APK)
infos = zf.infolist()
rows = []
for i in infos:
    rows.append([i.filename, i.file_size, i.compress_size,
                 round(i.compress_size / i.file_size, 4) if i.file_size else '',
                 i.compress_type, i.date_time and '%04d-%02d-%02d %02d:%02d:%02d' % i.date_time])
with open(os.path.join(OUT, 'APK条目清单.csv'), 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f)
    w.writerow(['条目', '原始字节', '压缩字节', '压缩率', '压缩方式', '时间戳'])
    w.writerows(rows)

print('== APK 概览')
print('  条目数 %d' % len(rows))
print('  解压后总计 %d 字节 (%.2f MB)' % (sum(r[1] for r in rows), sum(r[1] for r in rows) / 1048576))
print('  压缩后总计 %d 字节 (%.2f MB)' % (sum(r[2] for r in rows), sum(r[2] for r in rows) / 1048576))

# 顶层目录聚合
agg = collections.Counter()
cnt = collections.Counter()
for r in rows:
    top = r[0].split('/')[0] if '/' in r[0] else '(根目录文件)'
    agg[top] += r[1]
    cnt[top] += 1
print('\n== 顶层条目聚合（按解压后字节）')
for k, v in agg.most_common():
    print('  %-32s %4d 项  %10d 字节  %5.1f%%' % (k, cnt[k], v, v * 100.0 / sum(agg.values())))

print('\n== 体积 Top 15')
for r in sorted(rows, key=lambda x: -x[1])[:15]:
    print('  %-52s %9d  %6.1f%%' % (r[0], r[1], r[1] * 100.0 / sum(x[1] for x in rows)))

print('\n== 压缩方式分布')
ct = collections.Counter(r[4] for r in rows)
for k, v in ct.items():
    print('  method=%d: %d 项' % (k, v))

print('\n== 时间戳分布')
dts = collections.Counter(r[5][:10] for r in rows)
for k, v in sorted(dts.items()):
    print('  %s: %d' % (k, v))

# 证书 RDN 还原（PKCS#7 内嵌 X.509，RDN 字符串多为 GBK）
print('\n== 签名证书')
certs = [n for n in zf.namelist() if n.upper().startswith('META-INF/') and n.upper().endswith(('.RSA', '.DSA', '.EC'))]
for c in certs:
    b = zf.read(c)
    print('  %s (%d 字节)' % (c, len(b)))
    # OID 2.5.4.x 后紧跟 TLV 字符串
    OID_NAME = {b'\x03': 'CN', b'\x06': 'C', b'\x07': 'L', b'\x08': 'ST', b'\x0a': 'O', b'\x0b': 'OU'}
    i = 0
    out = []
    while True:
        j = b.find(b'\x06\x03\x55\x04', i)
        if j < 0:
            break
        tag = b[j + 4:j + 5]
        p = j + 5
        t = b[p]
        ln = b[p + 1]
        p += 2
        if t in (0x0c, 0x13, 0x16, 0x14) and ln < 128 and p + ln <= len(b):
            raw = b[p:p + ln]
            for enc in ('utf-8', 'gbk'):
                try:
                    s = raw.decode(enc)
                    break
                except Exception:
                    s = None
            if s is None:
                s = raw.decode('latin-1')
            out.append((OID_NAME.get(tag, tag.hex()), s, enc))
        i = p
    for k, v, e in out:
        print('    %-3s = %s   [%s]' % (k, v, e))
