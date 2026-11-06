import zipfile, os, json
z = zipfile.ZipFile(os.path.join(os.environ['OV'], '99_临时', 'ch3.apk'))
for n in sorted(x for x in z.namelist() if x.startswith('assets/idmap')):
    raw = z.read(n)
    dec = bytes(b ^ 0x10 for b in raw)
    try:
        j = json.loads(dec.decode('utf-8'))
    except Exception as e:
        print(n, 'parse fail', e, dec[:60]); continue
    print(n, '->', json.dumps(j, ensure_ascii=False)[:300])
