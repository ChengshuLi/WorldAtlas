"""Check complete OSM ways in twelve corridor extracts against selected line."""
import json,xml.etree.ElementTree as E,hashlib
from pathlib import Path
from shapely.geometry import LineString
src=LineString(json.load(open('caucasus-anapa-abin-combined-candidate.json'))['coordinates']);seen={};hits=[];incomplete=set();counts={};assets=[]
for i in range(12):
 path=Path('/tmp/east-audit-%d.osm'%i);data=path.read_bytes();assets.append({'name':path.name,'sha256':hashlib.sha256(data).hexdigest()});root=E.fromstring(data);nodes={n.get('id'):(float(n.get('lon')),float(n.get('lat'))) for n in root.findall('node')}
 for w in root.findall('way'):
  t={x.get('k'):x.get('v') for x in w.findall('tag')};kind=t.get('waterway');ids=[x.get('ref') for x in w.findall('nd')]
  if kind not in ('river','stream','canal','drain','ditch'):continue
  key=(w.get('id'),w.get('version'))
  if len(ids)<2 or any(n not in nodes for n in ids):incomplete.add(key);continue
  coords=[nodes[n] for n in ids]
  if key in seen:
   if seen[key]!=coords:raise ValueError('source conflict '+str(key))
   continue
  seen[key]=coords;incomplete.discard(key);counts[kind]=counts.get(kind,0)+1;inter=src.intersection(LineString(coords))
  if not inter.is_empty:
   pts=[p for p in getattr(inter,'geoms',[inter]) if p.geom_type=='Point' and p.x>=47]
   if pts:hits.append({'id':key[0],'version':key[1],'type':kind,'name':t.get('name'),'points':[[p.x,p.y] for p in pts]})
print('completed ways',counts,'incomplete',len(incomplete),'intersecting',len(hits));
for x in hits:print(json.dumps(x,ensure_ascii=False))
Path('eastern-waterway-audit-research.json').write_text(json.dumps({'assets':assets,'counts':counts,'incomplete':len(incomplete),'hits':hits},ensure_ascii=False,indent=2)+'\n')
