import json, os
j = json.load(open(os.path.join(os.environ['OV'], '03_分析', '原版v3_第一章.json'), encoding='utf-8'))
for nid, n in (j.get('storyData') or {}).items():
    ph = n.get('photoid') or ''
    if ph:
        c = (n.get('contents') or {}).get('ZH_CN') or ''
        print(ph, '|', nid, '|', c[:44])
