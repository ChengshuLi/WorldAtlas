import sys,json,gzip,hashlib
from pathlib import Path
sys.path.insert(0,'/tmp/worldatlas-macro-coverage-africa-americas/python-deps')
import osmium
from shapely.geometry import Polygon,Point,box
from shapely import from_wkb,orient_polygons,to_wkb,STRtree
from pyproj import Geod
P=Path('/tmp/worldatlas-macro-coverage-africa-americas');R=Path('/workspace/WorldAtlas');geod=Geod(ellps='WGS84')
class Coast(osmium.SimpleHandler):
 def __init__(self):super().__init__();self.ways=[]
 def way(self,w):
  if w.tags.get('natural')!='coastline':return
  self.ways.append(dict(id=w.id,version=w.version,timestamp=str(w.timestamp),nodes=[n.ref for n in w.nodes],geometry=[[n.lon,n.lat] for n in w.nodes]))
h=Coast();h.apply_file(str(P/'osm/greenland-latest.osm.pbf'),locations=True);ways=h.ways;(P/'osm/greenland-coast-ways.json.gz').write_bytes(gzip.compress(json.dumps(ways,separators=(',',':')).encode(),mtime=0));print('OSMways',len(ways))
# Append independent Inaccessible query way records; closed outercoast output permits current confirmation.
a=json.load(open(P/'osm/inaccessible.json'))
for w in a['elements']:
 if w.get('type')=='way':ways.append(dict(id=w['id'],version=w.get('version'),timestamp=a.get('osm3s',{}).get('timestamp_osm_base'),nodes=w['nodes'],geometry=[[n['lon'],n['lat']] for n in w['geometry']]))
starts={};ends={}
for i,w in enumerate(ways):starts.setdefault(w['nodes'][0],[]).append(i);ends.setdefault(w['nodes'][-1],[]).append(i)
seen=set();polys=[];openchains=[]
for i,w in enumerate(ways):
 if i in seen:continue
 chain=[i];seen.add(i);nodes=w['nodes'][:];coords=w['geometry'][:]
 while nodes[-1]!=nodes[0]:
  nxt=[n for n in starts.get(nodes[-1],[]) if n not in seen]
  if len(nxt)!=1:break
  j=nxt[0];seen.add(j);chain.append(j);nodes.extend(ways[j]['nodes'][1:]);coords.extend(ways[j]['geometry'][1:])
 if nodes[-1]!=nodes[0]:openchains.append({'way_ids':[ways[j]['id'] for j in chain],'first':nodes[0],'last':nodes[-1],'nodes':len(nodes)});continue
 g=Polygon(coords)
 if g.is_empty or not g.is_valid:continue
 signed=geod.geometry_area_perimeter(g)[0]/1e6
 if signed<=0:continue
 polys.append(dict(way_ids=[ways[j]['id'] for j in chain],geometry=g,area_km2=signed,vertices=len(coords),source_timestamp=max(str(ways[j]['timestamp']) for j in chain)))
print('ClosedCCWlandpolygons',len(polys),'openchains',len(openchains));rs=[x for x in json.load(open(R/'data/macro-foundation/envelopes-v3/envelope-index.json'))['groups'] if x['level']=='region'];rg=[from_wkb(gzip.decompress((R/'data/macro-foundation/envelopes-v3'/x['path']).read_bytes())) for x in rs];rt=STRtree(rg)
def area(g):
 if g.is_empty:return 0
 if g.geom_type=='Polygon':return abs(geod.geometry_area_perimeter(orient_polygons(g))[0])/1e6
 if hasattr(g,'geoms'):return sum(area(c) for c in g.geoms)
 return 0
pgeoms=[p['geometry'] for p in polys];ptree=STRtree(pgeoms);results=[]
for name,source_id,xy in [('Disko / Qeqertarsuaq',92,(-53.9,69.8)),('Milne Land',146,(-27,70.6)),('Inaccessible Island',4118,(-12.68,-37.30))]:
 pt=Point(*xy);idxs=[int(i) for i in ptree.query(pt) if pgeoms[int(i)].covers(pt)]
 if len(idxs)!=1:results.append(dict(name=name,gshhg_id=source_id,point=xy,matching_closed_rings=len(idxs),status='current-coast-not-certified'));continue
 p=polys[idxs[0]];g=p['geometry'];gs=from_wkb(gzip.decompress((P/'candidate-components'/f'{source_id}.wkb.gz').read_bytes()));ovs=[]
 for i in rt.query(g):
  ak=area(g.intersection(rg[int(i)]))
  if ak>1e-9:ovs.append(dict(region_id=rs[int(i)]['id'],region=rs[int(i)]['name'],area_km2=ak,share=ak/p['area_km2']))
 row=dict(name=name,gshhg_id=source_id,source='current-OSM-coast-closed-land-left-ring',osm_way_ids=p['way_ids'],source_timestamp=p['source_timestamp'],osm_area_km2=p['area_km2'],osm_vertices=p['vertices'],bounds=list(g.bounds),footprint_sha256=hashlib.sha256(to_wkb(g)).hexdigest(),current_atlas_region_overlaps=ovs,gshhg_overlap_of_osm=area(g.intersection(gs))/p['area_km2'],gshhg_overlap_of_gshhg=area(g.intersection(gs))/area(gs),status='missing-footprint-independently-confirmed' if not ovs else 'current-footprint-partly-represented')
 (P/'osm'/(name.split(' / ')[0].lower().replace(' ','-')+'-footprint.wkb.gz')).write_bytes(gzip.compress(to_wkb(g),mtime=0));results.append(row);print(json.dumps(row))
(P/'osm-correspondence.json').write_text(json.dumps(dict(version=1,osm_data_license='ODbL-1.0 OpenStreetMap contributors; Geofabrik',gshhg_data_license='LGPL-3.0-or-later',closed_land_polygons=len(polys),open_chain_count=len(openchains),open_chain_examples=openchains[:10],method='NativeOSMcoastlinewayendpoint-stitch with no invented links, verifyclosedCCWland-left validrings; inlandlake-maskseparate; representativepointselectswholeislandring only; allcoverageiswhole-footprintintersection',results=results),separators=(',',':')))
