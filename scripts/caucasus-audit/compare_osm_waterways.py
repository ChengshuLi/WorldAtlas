import json,sys,xml.etree.ElementTree as E
from shapely.geometry import LineString
old=LineString(json.load(open(sys.argv[1]))['coordinates']);new=LineString(json.load(open(sys.argv[2]))['coordinates']);r=E.parse(sys.argv[3]).getroot();nodes={x.get('id'):(float(x.get('lon')),float(x.get('lat'))) for x in r.findall('node')};hits={'old':[],'new':[]};n=0;miss=0
for w in r.findall('way'):
 t={x.get('k'):x.get('v') for x in w.findall('tag')};ids=[x.get('ref') for x in w.findall('nd')]
 if t.get('waterway') not in ('river','stream'):continue
 if len(ids)<2 or any(x not in nodes for x in ids):miss+=1;continue
 n+=1;g=LineString([nodes[x] for x in ids])
 for name,line in [('old',old),('new',new)]:
  if line.intersects(g):hits[name].append((w.get('id'),t.get('name')))
print('complete',n,'incomplete',miss,'crossings',hits)
