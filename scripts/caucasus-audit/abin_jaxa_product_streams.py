"""Screen complete mapped OSM river/stream ways against unselected cut."""
import json,xml.etree.ElementTree as ET
from shapely.geometry import LineString
root=ET.parse('west-habl-combined.osm').getroot();nodes={n.attrib['id']:(float(n.attrib['lon']),float(n.attrib['lat'])) for n in root.findall('node')};candidate=LineString(json.load(open('west-abin-jaxa-product-cut-research.json'))['coordinates']);complete=[];incomplete=0;hits=[]
for w in root.findall('way'):
 tags={t.attrib['k']:t.attrib['v'] for t in w.findall('tag')}
 if tags.get('waterway') not in ('river','stream'):continue
 ids=[n.attrib['ref'] for n in w.findall('nd')]
 if len(ids)<2 or any(x not in nodes for x in ids):incomplete+=1;continue
 line=LineString([nodes[x] for x in ids]);complete.append(w.attrib['id'])
 if candidate.intersects(line):hits.append((w.attrib['id'],tags.get('name'),candidate.intersection(line).geom_type))
print('complete',len(complete),'incomplete',incomplete,'intersecting',len(hits),'hits',hits)
