import json,gzip,struct,hashlib,math
from pathlib import Path
import numpy as np
from shapely.geometry import Polygon,box
from shapely import from_wkb,make_valid,STRtree,to_wkb
from pyproj import Geod
P=Path('/tmp/worldatlas-macro-coverage-africa-americas');repo=Path('/workspace/WorldAtlas'); geod=Geod(ellps='WGS84')
def area(g):
 try: return abs(geod.geometry_area_perimeter(g)[0])/1e6
 except: return sum(area(a) for a in g.geoms if a.geom_type in ('Polygon','MultiPolygon'))
rows=json.load(open(repo/'data/macro-foundation/envelopes-v3/envelope-index.json'))['groups']; envs={x['id']:from_wkb(gzip.decompress((repo/'data/macro-foundation/envelopes-v3'/x['path']).read_bytes())) for x in rows};regions=[x for x in rows if x['level']=='region'];rg=[envs[x['id']] for x in regions];tree=STRtree(rg)
domains={
'Madeira':[[-17.5,31.9,-15.5,33.3],[-16.2,29.9,-15.7,30.3]],
'Canary Islands':[[-18.3,27.5,-13.2,29.6]],
'Cabo Verde':[[-25.7,14.5,-22.5,17.4]],
'Socotra archipelago':[[51.7,11.9,54.7,12.9]],
'Comoros and Mayotte':[[43.0,-13.2,45.5,-11.2]],
'Seychelles':[[45.9,-10.4,56.7,-3.5]],
'Mozambique Channel Islands':[[40.2,-22.6,40.5,-22.1],[42.65,-21.65,42.85,-21.4],[42.5,-17.2,42.9,-16.8],[47.1,-11.7,47.45,-11.35],[54.3,-15.95,54.6,-15.7]],
'Tristan da Cunha archipelago':[[-12.9,-37.7,-12.0,-36.9],[-10.15,-40.5,-9.6,-40.1]],
'Greenland':[[-75,59,-10,85]],
'Bermuda':[[-65,31.9,-64.5,32.6]],
'Saint Pierre and Miquelon':[[-56.6,46.65,-56,47.2]],
'Bahamian and Turks and Caicos Lucayan archipelagos':[[-80.7,20.5,-70.4,27.6]],
'Greater/Lesser Antilles, Venezuelan Antilles and southwest Caribbean islands/banks':[[-85,9,-59,23.6]],
'Clipperton':[[-109.3,10.2,-109.1,10.4]],
'Galapagos':[[-92,-1.7,-89,1.8]],
'Juan Fernandez and Chilean mainland-associated Pacific islands':[[-81,-34.2,-78.6,-33.4],[-80.2,-26.5,-79.7,-26.1]],
'Falkland Islands':[[-61.6,-52.6,-57.5,-50.8]],
'South Georgia and South Sandwich Islands':[[-39,-55.2,-34,-53.8],[-28.8,-60,-25.5,-56]],
'Ceuta':[[-5.44,35.85,-5.27,35.94]],'Melilla':[[-3.03,35.25,-2.92,35.34]],
'Madagascar main island':[[43,-26,51,-11.5]],
'Mascarene principal islands: Mauritius, Rodrigues and Reunion':[[55,-21.5,56,-20.6],[57.1,-20.6,58,-19.8],[63.2,-19.85,63.6,-19.6]],
'Bouvet Island':[[3.2,-54.55,3.5,-54.35]], 'Saint Helena':[[-5.9,-16.1,-5.5,-15.8]],'Ascension':[[-14.5,-8.05,-14.2,-7.8]]}
components=[];reader=(P/'gshhs_f.b').open('rb');total=0
while hdr:=reader.read(44):
 vals=struct.unpack('>11i',hdr);identity,n,flag,west,east,south,north,akm,fulla,container,ancestor=vals;raw=reader.read(n*8);total+=1
 if flag&255!=1: continue
 if south/1e6 < -61: continue
 coords=np.frombuffer(raw,dtype='>i4').reshape(n,2).astype('float64')/1e6
 # Longitude unwrap preserves closed polygon; translate negative longitudes convention.
 xs=np.rad2deg(np.unwrap(np.deg2rad(coords[:,0])));xs-=360*math.floor((float(xs.mean())+180)/360);coords[:,0]=xs
 bounds=(coords[:,0].min(),coords[:,1].min(),coords[:,0].max(),coords[:,1].max())
 relevant=[name for name,boxes in domains.items() if any(bounds[0]<=b[2] and bounds[2]>=b[0] and bounds[1]<=b[3] and bounds[3]>=b[1] for b in boxes)]
 if not relevant:continue
 geom=Polygon(coords);valid=geom.is_valid
 if not valid: geom=make_valid(geom)
 ak=area(geom)
 if ak<=0:continue
 # Exclude continental mainland except Greenland/Madagascar when a family actually intersects.
 for name in relevant:
  boxes=domains[name]; domainhits=[b for b in boxes if geom.intersects(box(*b))]
  if not domainhits:continue
  if ak>100000 and name not in ('Greenland','Madagascar main island','Ceuta','Melilla'):continue
  if name=='Greenland' and ak>100000 and not geom.intersects(box(-50,65,-40,75)):continue
  if name=='Madagascar main island' and ak>100000 and not geom.intersects(box(45,-22,48,-17)):continue
  overlap=[]
  for i in tree.query(geom):
   inter=geom.intersection(rg[int(i)])
   ai=area(inter)
   if ai>1e-9: overlap.append({'region_id':regions[int(i)]['id'],'region':regions[int(i)]['name'],'intersection_km2':ai,'share':min(1,ai/ak)})
  overlap.sort(key=lambda x:x['intersection_km2'],reverse=True)
  best=overlap[0] if overlap else None
  components.append({'family':name,'gshhg_id':identity,'gshhg_points':n,'gshhg_native_bounds':list(vals[3:7]),'bounds':list(bounds),'area_km2':ak,'header_area_km2':akm/(10**((flag>>26)&63)),'source_polygon_valid':valid,'audit_normalization':'longitude unwrap; make_valid retained audit-only' if not valid else 'longitude unwrap only','majority_region':best,'all_region_overlaps':overlap,'within_domain':all(box(*b).covers(geom) for b in domainhits),'representative_point':list(geom.representative_point().coords)[0],'boundary_distance_degree':geom.distance(rg[int(tree.nearest(geom))]) if not best else 0,'geometry_wkb_sha256':hashlib.sha256(to_wkb(geom)).hexdigest()})
  # Keep normalized candidate only; original full binary is immutable.
  (P/'candidate-components').mkdir(exist_ok=True)
  asset=P/'candidate-components'/f'{identity}.wkb.gz'
  if not asset.exists(): asset.write_bytes(gzip.compress(to_wkb(geom),mtime=0))
reader.close();(P/'components.json').write_text(json.dumps({'gshhg_polygons_read':total,'components':components},separators=(',',':')))
entries=json.load(open('/tmp/worldatlas-africa-americas-entries.json'));led=[]
for e in entries:
 cs=[c for c in components if c['family']==e['name']];scope=[c for c in cs if c['area_km2']>=0.1];pres=[c for c in scope if c['majority_region'] and c['majority_region']['share']>.5];miss=[c for c in scope if not c['majority_region'] or c['majority_region']['share']<=.5];wrong=[c for c in pres if c['majority_region']['region_id']!=e['region_id']]
 row={**e,'independent_source':'GSHHG2.3.7 fullresolutionlevel1','domain_boxes':domains[e['name']],'coverage_domain':'ocean-land polygon components >=0.1 km² within defined geographic window; continental mainland excluded except focalmainisland; windows do not by themselves establish archipelago membership; all lower-size candidates retained','source_components_all_sizes':len(cs),'source_components_gte_0_1km2':len(scope),'components_majority_represented':len(pres),'components_lacking_majority':len(miss),'represented_majority_wrong_region':len(wrong),'below_0_1km2_count':len(cs)-len(scope),'missing_candidate_ids':[c['gshhg_id'] for c in miss],'wrong_region_candidate_ids':[c['gshhg_id'] for c in wrong],'status':'source-window-tested-association-review-required','component_details_path':'components.json'};led.append(row)
 print(e['name'],len(cs),'scope',len(scope),'present',len(pres),'missing',len(miss),'wrong',len(wrong))
(P/'ledger-initial.json').write_text(json.dumps(led,indent=2));print('totalGSHHG',total,'components',len(components))
