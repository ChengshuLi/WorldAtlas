exec(open('.cache/shared-edge-991/prototype.py').read().split('candidates={k:current[k].union')[0])
report=json.loads(pathlib.Path('.cache/shared-edge-991/prototype-v1.json').read_text())[-1]
joint={k:shape(g)for k,g in report['candidates'].items()}
rejoined={k:joint[k].union(current[k])for k in joint}
assess('joint-faces-rejoin-originals',rejoined,{})
for cut in ['IRN','PAK']:
 other='PAK'if cut=='IRN'else'IRN'
 ordered={k:g for k,g in rejoined.items()};ordered[cut]=ordered[cut].difference(ordered[other]);assess('shared-face-original-priority-cut-'+cut,ordered,{})
pathlib.Path('.cache/shared-edge-991/variants-v1.json').write_text(json.dumps(results)+'\n')
