import json, os, re, glob
for f in sorted(glob.glob(os.path.join(os.environ['OV'], '03_分析', '原版v3_*.json'))):
    j = json.load(open(f, encoding='utf-8'))
    sd = j.get('storyData') or {}
    hits = []
    for nid, n in sd.items():
        c = (n.get('contents') or {}).get('ZH_CN') or ''
        if 'image' in c.lower():
            hits.append((nid, n.get('type'), n.get('photoid'), c[:60]))
    print(os.path.basename(f), len(hits))
    for h in hits[:8]:
        print('   ', h)
