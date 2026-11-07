"""Coordinate-linear OSM/selected-line intersection screen, research only."""
import sys,json,xml.etree.ElementTree as E
from collections import Counter
from shapely.geometry import LineString
r=E.parse(sys.argv[1]).getroot();nodes={n.get('id'):(float(n.get('lon')),float(n.get('lat'))) for n in r.findall('node')};line=LineString(json.load(open('caucasus-line.json'))['coordinates']);counts=Counter()
for w in r.findall('way'):
 t={v.get('k'):v.get('v') for v in w.findall('tag')};kind=t.get('waterway')
 if kind not in ('river','stream','canal','drain','ditch'):continue
 ids=[v.get('ref') for v in w.findall('nd')]
 if len(ids)<2 or any(x not in nodes for x in ids):counts['incomplete']+=1;continue
 counts['complete']+=1;x=LineString([nodes[i] for i in ids]).intersection(line)
 if not x.is_empty:
  counts['crossing']+=1;print('way',w.get('id'),'version',w.get('version'),'tags',t,'intersection',x.wkt,'end_nodes',ids[0],ids[-1])
print('counts',dict(counts))
