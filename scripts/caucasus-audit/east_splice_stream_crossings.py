"""Check complete OSM waterway geometries against unselected eastern splice."""
import json,xml.etree.ElementTree as E
from shapely.geometry import LineString
r=E.parse('east-stream-broad-osm.osm').getroot(); nodes={n.attrib['id']:(float(n.attrib['lon']),float(n.attrib['lat'])) for n in r.findall('node')}; cand=LineString(json.load(open('east-connected-splice-cut-research.json'))['coordinates']);n=0;incomplete=0;hits=[]
for w in r.findall('way'):
 t={x.attrib['k']:x.attrib['v'] for x in w.findall('tag')}
 if t.get('waterway') not in ('river','stream'):continue
 ids=[x.attrib['ref'] for x in w.findall('nd')]
 if len(ids)<2 or any(i not in nodes for i in ids):incomplete+=1;continue
 n+=1;l=LineString([nodes[i] for i in ids]);q=cand.intersection(l)
 if not q.is_empty:hits.append((w.attrib['id'],t.get('name'),q.wkt))
print('complete',n,'incomplete',incomplete,'intersections',len(hits),'hits',hits)
