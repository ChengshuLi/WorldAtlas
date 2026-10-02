from pathlib import Path
import json,gzip,struct,hashlib,math,re
import numpy as np
from shapely import from_wkb,STRtree,make_valid,to_wkb,orient_polygons
from shapely.geometry import Polygon,Point,box
from pyproj import Geod,Transformer,CRS
from shapely.ops import transform
P=Path('/tmp/worldatlas-macro-coverage-africa-americas');repo=Path('/workspace/WorldAtlas');geod=Geod(ellps='WGS84')
cs=json.load(open(P/'components.json'))['components'];desired=set(c['gshhg_id'] for c in cs); rawrecords={};headers={};f=(P/'gshhs_f.b').open('rb')
while hdr:=f.read(44):
 v=struct.unpack('>11i',hdr);offset=f.tell()-44;raw=f.read(v[1]*8)
 if v[0] in desired or v[0]==22:headers[v[0]]=dict(offset=offset,bytes=44+len(raw),n=v[1],flag=v[2],raw_area=v[7],magnitude=(v[2]>>26)&63,level=v[2]&255);rawrecords[v[0]]=hdr+raw
 if v[0]==22:
  co=np.frombuffer(raw,dtype='>i4').reshape(v[1],2).astype('float64')/1e6;xs=np.rad2deg(np.unwrap(np.deg2rad(co[:,0])));xs-=360*math.floor((float(xs.mean())+180)/360);co[:,0]=xs;g=Polygon(co);g=make_valid(g) if not g.is_valid else g;(P/'candidate-components/22.wkb.gz').write_bytes(gzip.compress(to_wkb(g),mtime=0));cubageom=g
# append Cuba excluded by prototype mainland cutoff; exact focused validation only.
regrows=[x for x in json.load(open(repo/'data/macro-foundation/envelopes-v3/envelope-index.json'))['groups'] if x['level']=='region'];rgeoms=[from_wkb(gzip.decompress((repo/'data/macro-foundation/envelopes-v3'/x['path']).read_bytes())) for x in regrows];rtree=STRtree(rgeoms)
def area(g):
 if g.is_empty:return 0
 if g.geom_type=='Polygon': return abs(geod.geometry_area_perimeter(orient_polygons(g))[0])/1e6
 if hasattr(g,'geoms'):return sum(area(x) for x in g.geoms)
 return 0
ak=area(cubageom);ovs=[]
for i in rtree.query(cubageom):
 ai=area(cubageom.intersection(rgeoms[int(i)]))
 if ai>1e-9:ovs.append(dict(region_id=regrows[int(i)]['id'],region=regrows[int(i)]['name'],intersection_km2=ai,share=min(1,ai/ak)))
ovs.sort(key=lambda x:x['intersection_km2'],reverse=True)
cs.append(dict(family='Greater/Lesser Antilles, Venezuelan Antilles and southwest Caribbean islands/banks',gshhg_id=22,gshhg_points=headers[22]['n'],bounds=list(cubageom.bounds),area_km2=ak,source_polygon_valid=cubageom.is_valid,audit_normalization='longitude unwrap only',majority_region=ovs[0] if ovs else None,all_region_overlaps=ovs,within_domain=True,representative_point=list(cubageom.representative_point().coords)[0],boundary_distance_degree=0,geometry_wkb_sha256=hashlib.sha256(to_wkb(cubageom)).hexdigest()))
ids=sorted(set(c['gshhg_id'] for c in cs)); geoms=[from_wkb(gzip.decompress((P/'candidate-components'/f'{i}.wkb.gz').read_bytes())) for i in ids]; ix={ident:i for i,ident in enumerate(ids)};tree=STRtree(geoms)
# independent named island association: exact point-in-sourcepolygon preferred; closestwithin1km only provisional.
names={i:[] for i in ids};unmatched=[]
for fn in sorted((P/'geonames').glob('*-islands.json')):
 for n in json.load(open(fn)):
  if n['feature_code']!='ISL':continue
  pt=Point(n['longitude'],n['latitude']);found=[int(i) for i in tree.query(pt) if geoms[int(i)].covers(pt)]
  method='gazetteer-coordinate-in-whole-source-polygon'
  if not found:
   i=int(tree.nearest(pt));near=geoms[i].representative_point();dist=abs(geod.inv(pt.x,pt.y,near.x,near.y)[2]);boundary=geoms[i].distance(pt)*111000
   if boundary<=1000:found=[i];method='gazetteer-coordinate-within-approx1km-source-boundary-provisional'
  if not found:unmatched.append(n);continue
  for i in found:names[ids[i]].append({**n,'source_file':str(fn.relative_to(P)), 'match_method':method})
# Named Wikipedia coordinates with snapshot/sourcehash; deliberately identitycontext, not coverageproof.
wiki=json.load(open(P/'gazetteer-source-inventory.json'));wp=[]
for n in wiki:
 points=[s for s in n.get('coordinate_spans',[]) if re.fullmatch(r'-?\d+(?:\.\d+)?; -?\d+(?:\.\d+)?',s)]
 if not points:continue
 lat,lon=map(float,points[0].split('; '));pt=Point(lon,lat);i=int(tree.nearest(pt));g=geoms[i];nearest=g.representative_point();dist=abs(geod.inv(lon,lat,nearest.x,nearest.y)[2]);wp.append(dict(name=n['name'],source=n['url'],source_sha256=n.get('sha256'),coordinate=[lon,lat],nearest_component_id=ids[i],source_polygon_covers_coordinate=g.covers(pt),approx_boundary_distance_m=g.distance(pt)*111000,component_centroid_distance_m=dist))
byid={c['gshhg_id']:c for c in cs}
for c in cs:
 h=headers[c['gshhg_id']];c['header_area_km2']=h['raw_area']/10**h['magnitude'];c['source_record']=h;c['independent_gazetteer_names']=names[c['gshhg_id']];c['named_wikipedia_coordinate_context']=[n for n in wp if n['nearest_component_id']==c['gshhg_id'] and n['approx_boundary_distance_m']<=5000]
 # Quantify proximity at the chosen atlas grid source uncertainty scale without changing any geometry.
 best=c.get('majority_region');share=best['share'] if best else 0
 if c['area_km2']>=.1 and share<=.5 and c['boundary_distance_degree']<=.01:
  g=geoms[ix[c['gshhg_id']]];pt=g.representative_point();crs=CRS.from_proj4(f'+proj=aeqd +lat_0={pt.y} +lon_0={pt.x} +datum=WGS84 +units=m');project=Transformer.from_crs('EPSG:4326',crs,always_xy=True).transform;local=transform(project,g);candidate=rtree.query(g.buffer(.01));shares=[]
  for j in candidate:
   region=transform(project,rgeoms[int(j)].intersection(box(g.bounds[0]-.05,g.bounds[1]-.05,g.bounds[2]+.05,g.bounds[3]+.05)))
   if not region.is_empty:shares.append((local.intersection(region.buffer(200)).area/local.area,regrows[int(j)]['id']))
  if shares:c['overlap_with_200m_reference_buffer']={'share':min(1,max(shares)[0]),'region_id':max(shares)[1],'method':'localAEQDmetric200mregionbuffer diagnostic; no geographychanged'}
(P/'components-reviewed.json').write_text(json.dumps({'gshhg_polygons_read':188612,'components':cs,'unmatched_gazetteer_named_islands':unmatched,'wikipedia_coordinate_context':wp},separators=(',',':')))
# Retain exact sourcebyte fragments, never serialize raw coordinates as if theywere original bytes.
pack=b''.join(rawrecords[i] for i in ids);(P/'selected-gshhg-source-records.bin.gz').write_bytes(gzip.compress(pack,mtime=0));offset=0;rec=[]
for i in ids:
 b=rawrecords[i];rec.append(dict(id=i,source_offset=headers[i]['offset'],source_bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),pack_offset=offset));offset+=len(b)
(P/'source-record-index.json').write_text(json.dumps(dict(source_binary='gshhs_f.b',source_binary_sha256=hashlib.sha256((P/'gshhs_f.b').read_bytes()).hexdigest(),record_pack_sha256=hashlib.sha256((P/'selected-gshhg-source-records.bin.gz').read_bytes()).hexdigest(),records=rec),separators=(',',':')))
print('components',len(cs),'unique',len(ids),'namedassociations',sum(bool(names[i]) for i in ids),'rawsourcepack',len(pack),'gz',(P/'selected-gshhg-source-records.bin.gz').stat().st_size)
for name in ['Madeira','Socotra archipelago','Tristan da Cunha archipelago','Greenland','Seychelles','Juan Fernandez and Chilean mainland-associated Pacific islands']:
 print('\n',name)
 for c in sorted([c for c in cs if c['family']==name and c['area_km2']>=.1 and c['independent_gazetteer_names'] and (not c['majority_region'] or c['majority_region']['share']<=.5)],key=lambda x:x['area_km2'],reverse=True)[:10]:print(c['gshhg_id'],round(c['area_km2'],3),[n['name'] for n in c['independent_gazetteer_names'][:3]],round(c['majority_region']['share'],3) if c['majority_region'] else 0,c.get('overlap_with_200m_reference_buffer'))
