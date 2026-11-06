# -*- coding: utf-8 -*-
"""资产清单：遍历解包后的 assets，解码百分号文件名，计算 SHA-256、尺寸、图片/音频元数据。"""
import csv, hashlib, os, struct, sys, urllib.parse

sys.stdout.reconfigure(encoding='utf-8')

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.join(BASE, '02_解包')
ASSETS = os.path.join(ROOT, 'assets', 'flutter_assets', 'assets')
OUT = os.path.join(BASE, '04_资源分析', '表')
os.makedirs(OUT, exist_ok=True)


def webp_size(b):
    if b[:4] != b'RIFF' or b[8:12] != b'WEBP':
        return None
    fourcc = b[12:16]
    if fourcc == b'VP8 ':
        # 数据区自 20 起：3 字节 frame tag → 起始码 9d 01 2a（23..26）→ 宽、高各 2 字节（14 bit）
        p = 20 + 6
        w, h = struct.unpack('<HH', b[p:p + 4])
        return w & 0x3FFF, h & 0x3FFF
    if fourcc == b'VP8L':
        bits = struct.unpack('<I', b[21:25])[0]
        w = (bits & 0x3FFF) + 1
        h = ((bits >> 14) & 0x3FFF) + 1
        return w, h
    if fourcc == b'VP8X':
        w = int.from_bytes(b[24:27], 'little') + 1
        h = int.from_bytes(b[27:30], 'little') + 1
        return w, h
    return None


def png_size(b):
    if b[:8] != b'\x89PNG\r\n\x1a\n':
        return None
    w, h = struct.unpack('>II', b[16:24])
    return w, h


def ogg_info(b):
    """返回 (时长秒, 采样率, 声道数)，尽力解析 Ogg Vorbis 头与 granule position。"""
    if b[:4] != b'OggS':
        return None, None, None
    ident = b.find(b'\x01vorbis')
    sr = ch = None
    if ident > 0:
        ch = b[ident + 11]
        sr = struct.unpack('<I', b[ident + 12:ident + 16])[0]
    # 最后一个页的 granule position
    last = b.rfind(b'OggS')
    gran = None
    if last > 0:
        gran = struct.unpack('<q', b[last + 6:last + 14])[0]
    dur = (gran / sr) if (gran and sr) else None
    return dur, sr, ch


rows = []
for dp, dns, fns in os.walk(ASSETS):
    dns.sort()
    for fn in sorted(fns):
        p = os.path.join(dp, fn)
        rel = os.path.relpath(p, ASSETS).replace('\\', '/')
        rel_dec = urllib.parse.unquote(rel)
        b = open(p, 'rb').read()
        sha = hashlib.sha256(b).hexdigest()
        ext = os.path.splitext(fn)[1].lower()
        w = h = None
        dur = sr = ch = None
        if ext == '.webp':
            s = webp_size(b)
            if s:
                w, h = s
        elif ext == '.png':
            s = png_size(b)
            if s:
                w, h = s
        elif ext == '.ogg':
            dur, sr, ch = ogg_info(b)
        rows.append({
            'path': rel_dec, 'ext': ext, 'bytes': len(b), 'sha256': sha,
            'w': w, 'h': h, 'dur': (round(dur, 1) if dur else None),
            'sr': sr, 'ch': ch,
        })

with open(os.path.join(OUT, '资源清单.csv'), 'w', encoding='utf-8-sig', newline='') as f:
    wr = csv.writer(f)
    wr.writerow(['相对路径', '类型', '字节', '宽', '高', '时长秒', '采样率', '声道', 'SHA-256'])
    for r in rows:
        wr.writerow([r['path'], r['ext'], r['bytes'], r['w'] or '', r['h'] or '',
                     r['dur'] or '', r['sr'] or '', r['ch'] or '', r['sha256']])

# 按目录汇总
cat = {}
for r in rows:
    top = r['path'].split('/')[0]
    c = cat.setdefault(top, {'n': 0, 'bytes': 0})
    c['n'] += 1
    c['bytes'] += r['bytes']
print('== 目录汇总')
for k in sorted(cat):
    print('  %-10s %3d 个  %9d 字节' % (k, cat[k]['n'], cat[k]['bytes']))
print('  合计 %d 个文件 / %d 字节' % (len(rows), sum(r['bytes'] for r in rows)))

print('\n== 逐项明细')
for r in rows:
    dim = ('%dx%d' % (r['w'], r['h'])) if r['w'] else ''
    dur = ('%.1fs' % r['dur']) if r['dur'] else ''
    print('  %-34s %8d  %-10s %-9s %s' % (r['path'], r['bytes'], dim, dur, r['sha256'][:12]))

# CSV 副本与包内文件一致性
print('\n== 剧情 CSV 副本一致性')
src = os.path.join(ASSETS, 'story')
dst = os.path.join(BASE, '04_资源分析', '剧情CSV')
for fn in sorted(os.listdir(src)):
    a = hashlib.sha256(open(os.path.join(src, fn), 'rb').read()).hexdigest()
    p2 = os.path.join(dst, urllib.parse.unquote(fn))
    bsha = hashlib.sha256(open(p2, 'rb').read()).hexdigest() if os.path.exists(p2) else 'MISSING'
    print('  %-14s %s' % (urllib.parse.unquote(fn), 'OK' if a == bsha else 'MISMATCH ' + bsha))
