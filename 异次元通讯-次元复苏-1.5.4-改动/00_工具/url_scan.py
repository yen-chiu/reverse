# -*- coding: utf-8 -*-
"""从导出字符串中提取 URL / 邮箱 / 关键 API 常量，并统计剧情文本规模。"""
import csv, collections, glob, os, re, sys

sys.stdout.reconfigure(encoding='utf-8')
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASCII = os.path.join(BASE, '03_反编译', 'dart_strings_ascii.txt')

pat = re.compile(r'(?:https?|ftp)://[^\s"\'<>\\]{4,}|[\w.+-]+@[\w-]+\.[a-z]{2,}')
urls = collections.Counter()
for line in open(ASCII, encoding='utf-8', errors='replace'):
    for m in pat.finditer(line):
        urls[m.group()] += 1

print('== URL/邮箱常量：%d 个唯一值' % len(urls))
for u, c in urls.most_common(50):
    print('  %-78s x%d' % (u, c))
print('\n== 明文 HTTP（非 TLS）：')
for u in urls:
    if u.lower().startswith('http://'):
        print('  ', u)

print('\n== 与网络/存储/权限相关的高层常量')
KWS = ('http', 'socket', 'HttpClient', 'dio', 'package:http', 'MethodChannel',
       'shared_preferences', 'path_provider', 'notifications', 'gallery',
       'window_manager', 'device_info', 'package_info', 'url_launcher')
lines = open(ASCII, encoding='utf-8', errors='replace').read().splitlines()
seen = set()
for line in lines:
    for k in KWS:
        if k in line and len(line) < 200:
            s = line.strip()
            if s not in seen:
                seen.add(s)
                print('  ', s[:160])
            break

# 剧情规模
print('\n== 剧情文本规模')
tot_bytes = tot_chars = 0
for f in sorted(glob.glob(os.path.join(BASE, '04_资源分析', '剧情CSV', '*.csv'))):
    b = open(f, 'rb').read()
    s = b.decode('utf-8')
    ch = sum(1 for c in s if '\u4e00' <= c <= '\u9fff')
    tot_bytes += len(b)
    tot_chars += ch
    print('  %-12s %8d 字节  %7d 汉字' % (os.path.basename(f), len(b), ch))
print('  合计 %d 字节 / %d 汉字' % (tot_bytes, tot_chars))
