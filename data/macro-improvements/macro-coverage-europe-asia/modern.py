from pathlib import Path
from urllib.request import urlopen,Request
from concurrent.futures import ThreadPoolExecutor
import json,hashlib,gzip,xml.etree.ElementTree as ET
from shapely.geometry import Polygon,Point
from shapely.geometry.polygon import orient
from pyproj import Geod
P=Path(__file__).parent;(P/'modern-coastlines').mkdir(exist_ok=True);geod=Geod(ellps='WGS84')
DOM={'RoWide':(29.47,36.13,29.53,36.18),'Comino':(14.312,35.99,14.365,36.031),'Channel':(-2.49,49.405,-2.315,49.495),'FugloyWide':(-6.43,62.26,-6.22,62.40),'CocosSouth':(96.79,-12.25,96.93,-12.05),'CocosNorth':(96.8,-11.88,96.845,-11.8),'Minamitorishima':(153.958,24.267,154.002,24.306),'DiegoGarcia':(72.30,-7.48,72.52,-7.20),'SalomonWide':(72.17,-5.45,72.36,-5.25)}
def run(a):
 n,bbox=a;u='https://api.openstreetmap.org/api/0.6/map?bbox='+','.join(map(str,bbox));path=P/'modern-coastlines'/f'{n}.osm.xml.gz'
 try:
  if path.exists():b=gzip.decompress(path.read_bytes());status=200
  else:
   with urlopen(Request(u,headers={'User-Agent':'WorldAtlas sourced geographical audit contact github.com/ChengshuLi/WorldAtlas'}),timeout=60) as r:b=r.read();status=r.status
   path.write_bytes(gzip.compress(b,mtime=0))
  root=ET.fromstring(b);nodes={x.attrib['id']:(float(x.attrib['lon']),float(x.attrib['lat'])) for x in root.findall('node')};ways=[]
  for w in root.findall('way'):
   tags={t.attrib['k']:t.attrib['v'] for t in w.findall('tag')}
   if tags.get('natural')=='coastline':ways.append(dict(id=w.attrib['id'],version=w.attrib.get('version'),timestamp=w.attrib.get('timestamp'),nodes=[x.attrib['ref'] for x in w.findall('nd')],tags=tags))
  pending=list(ways);rings=[];openchains=[]
  while pending:
   w=pending.pop();chain=w['nodes'][:];ids=[w['id']];versions=[{'id':w['id'],'version':w['version'],'timestamp':w['timestamp']}]
   while chain[0]!=chain[-1]:
    found=False
    for i,z in enumerate(pending):
     zz=z['nodes']
     if chain[-1]==zz[0]:chain.extend(zz[1:])
     elif chain[0]==zz[-1]:chain=zz[:-1]+chain
     else:continue
     found=True;ids.append(z['id']);versions.append({'id':z['id'],'version':z['version'],'timestamp':z['timestamp']});pending.pop(i);break
    if not found:break
   missing=[x for x in chain if x not in nodes]
   if chain[0]!=chain[-1] or missing:openchains.append(dict(way_ids=ids,node_count=len(chain),missing_nodes=missing));continue
   coords=[nodes[x] for x in chain];g=Polygon(coords);land_direction=geod.geometry_area_perimeter(g)[0];ak=abs(land_direction)/1e6
   rings.append(dict(way_ids=ids,way_versions=versions,node_count=len(chain),bounds=list(g.bounds),area_km2=ak,land_on_left_signed_area_km2=land_direction/1e6,valid=g.is_valid,coordinates=coords))
  return dict(name=n,url=u,requested_bbox=bbox,http_status=status,original_bytes=len(b),original_sha256=hashlib.sha256(b).hexdigest(),original_path='modern-coastlines/'+path.name,license='OpenStreetMap contributors; ODbL1.0 database, attribution https://www.openstreetmap.org/copyright',retrieved_on='2026-10-02UTC',node_count=len(nodes),coastline_way_count=len(ways),closed_rings=rings,open_chains=openchains)
 except Exception as e:return dict(name=n,url=u,error=str(e))
with ThreadPoolExecutor(max_workers=3) as ex:rows=list(ex.map(run,DOM.items()))
(P/'modern-coastline-index.json').write_text(json.dumps(rows,separators=(',',':'))+'\n')
print([(r['name'],r.get('http_status'),len(r.get('closed_rings',[])),len(r.get('open_chains',[])),r.get('error')) for r in rows])
