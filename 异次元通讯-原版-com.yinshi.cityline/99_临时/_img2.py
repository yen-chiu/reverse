import json, os, glob
for f in sorted(glob.glob(os.path.join(os.environ['OV'], '03_分析', '原版剧情_*.json'))):
    j = json.load(open(f, encoding='utf-8'))
    rows = j.get('rows') if isinstance(j, dict) else j
    hits = [(r.get('chapterId'), r.get('text', '')[:50]) for r in (rows or []) if 'image' in (r.get('text') or '').lower()]
    print(os.path.basename(f), len(hits))
    for h in hits[:6]:
        print('   ', h)
