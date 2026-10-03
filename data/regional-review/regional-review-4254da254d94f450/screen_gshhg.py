#!/usr/bin/env python3
"""Screen all issue #485 locations against GSHHG full-resolution land polygon centroids."""
import gzip,hashlib,json,pathlib,struct,sys
HERE=pathlib.Path(__file__).resolve().parent; ROOT=HERE.parents[2]
if len(sys.argv)!=2: raise SystemExit('usage: screen_gshhg_scope.py /path/to/gshhs_f.b')
data=pathlib.Path(sys.argv[1]).read_bytes(); member_sha='af9215d58ebc525b2d09654a89959829f09e6edc457f3666759cded37be4ecf6'
if hashlib.sha256(data).hexdigest()!=member_sha: raise SystemExit('GSHHG member hash mismatch')
ids=set(json.loads((HERE/'scope.json').read_text())['member_location_ids']); feats={}
for part_name in json.loads((ROOT/'data/world-index.json').read_text())['parts']:
 for f in json.loads((ROOT/'data'/part_name).read_text())['features']:
  if f['properties']['id'] in ids: feats[f['properties']['id']]=f
if set(feats)!=ids: raise SystemExit('pinned scope IDs differ from current baseline')
def polys(g): return [g['coordinates']] if g['type']=='Polygon' else g['coordinates']
def bbox(g):
 ps=[pt for poly in polys(g) for ring in poly for pt in ring]
 return [min(p[0] for p in ps),min(p[1] for p in ps),max(p[0] for p in ps),max(p[1] for p in ps)]
def inside_ring(x,y,r):
 yes=False
 for i,(x1,y1) in enumerate(r):
  x2,y2=r[(i+1)%len(r)]
  if (y1>y)!=(y2>y) and x<(x2-x1)*(y-y1)/(y2-y1)+x1: yes=not yes
 return yes
def inside(x,y,g):
 return any(inside_ring(x,y,p[0]) and not any(inside_ring(x,y,h) for h in p[1:]) for p in polys(g))
def centroid(c):
 a=sx=sy=0.0
 for i,(x,y) in enumerate(c):
  x2,y2=c[(i+1)%len(c)]; z=x*y2-x2*y; a+=z; sx+=(x+x2)*z; sy+=(y+y2)*z
 if abs(a)<1e-14:return sum(p[0] for p in c)/len(c),sum(p[1] for p in c)/len(c)
 return sx/(3*a),sy/(3*a)
# Spatial bins avoid comparing every source record to all 222 units.
units={i:{'name':f['properties']['name'],'geometry':f['geometry'],'bbox':bbox(f['geometry']),'representative_point':f['properties']['metadata']['representative_point']} for i,f in feats.items()}
bins={}
for i,u in units.items():
 x1,y1,x2,y2=u['bbox']
 for gx in range(int(x1//2),int(x2//2)+1):
  for gy in range(int(y1//2),int(y2//2)+1):bins.setdefault((gx,gy),[]).append(i)
pos=0; matched=[]; n_level1=0; total=0; point_hits={i:[] for i in units}
while pos<len(data):
 lid,num,flag,west,east,south,north,area,area_full,container,ancestor=struct.unpack_from('>IIIiiiiIIii',data,pos)
 start=pos; pos+=44; end=pos+num*8
 if end>len(data):raise SystemExit('truncated GSHHG record')
 total+=1
 if flag&255==1:
  n_level1+=1; west/=1e6;east/=1e6;south/=1e6;north/=1e6
  if west>=180:west-=360;east-=360
  # Only decode coordinates if a source polygon extent can touch an assigned location.
  maybe=[i for i,u in units.items() if west<=u['bbox'][2] and east>=u['bbox'][0] and south<=u['bbox'][3] and north>=u['bbox'][1]]
  point_candidates=[i for i,u in units.items() if west<=u['representative_point'][0]<=east and south<=u['representative_point'][1]<=north]
  if maybe or point_candidates:
   coords=[]
   for j in range(num):
    x,y=struct.unpack_from('>ii',data,pos+j*8);x/=1e6;y/=1e6
    if x>180:x-=360
    coords.append((x,y))
   x,y=centroid(coords); hit=[]
   source_contains=[i for i in point_candidates if inside_ring(*units[i]['representative_point'],coords)]
   for i in source_contains: point_hits[i].append(lid)
   for i in maybe:
    u=units[i]
    if u['bbox'][0]<=x<=u['bbox'][2] and u['bbox'][1]<=y<=u['bbox'][3] and inside(x,y,u['geometry']):hit.append(i)
   if hit or source_contains:matched.append({'id':lid,'point':[x,y],'hits':hit,'source_representative_points_inside':source_contains,'bytes':data[start:end]})
 pos=end
counts={i:0 for i in units}
for rec in matched:
 for i in rec['hits']:counts[i]+=1
native=b''.join(x['bytes'] for x in matched); packed=gzip.compress(native,mtime=0)
(HERE/'sources/gshhg-scope-land-candidates.bin.gz').write_bytes(packed)
report={'source':{'title':'GSHHG full-resolution binary, release 2.3.7','release_date':'2017-06-15','archive_url':'https://www.soest.hawaii.edu/pwessel/gshhg/gshhg-bin-2.3.7.zip','archive_sha256':'28600e8f7a08645aab43079326df6504212ec5ccb2b4bcf3b5f4f12ed60e82bc','member':'gshhs_f.b','member_bytes':len(data),'member_sha256':member_sha,'license':'LGPLv3 or later; license retained in sources/gshhg-COPYING.LESSERv3.txt','restore':'Download the pinned archive, verify archive SHA-256, extract gshhs_f.b and verify member SHA-256.'},'scope_count':len(units),'source_level1_record_count':n_level1,'source_total_record_count':total,'retained':{'path':'sources/gshhg-scope-land-candidates.bin.gz','record_count':len(matched),'uncompressed_bytes':len(native),'uncompressed_sha256':hashlib.sha256(native).hexdigest(),'compressed_bytes':len(packed),'compressed_sha256':hashlib.sha256(packed).hexdigest()},'method':{'selection':'For every pinned assigned location, bbox-index full-resolution level-1 physical land records, calculate each candidate ring vertex centroid, and ray-crossing test that point against all bbox-compatible assigned polygons, respecting current holes. Retain complete matched GSHHG records only.','interpretation':'Two distinct screens are reported: (1) source land-polygon centroid within a current assigned polygon; (2) each pinned source representative point lies within a GSHHG level-1 land polygon. Either point test is screening only; it does not establish whole-boundary agreement, component containment, island identity, named-land completeness, or settlement coverage. A no-hit does not prove omitted land. Physical source is independent of political ownership and current administrative status.'},'per_location':{i:{'name':u['name'],'current_polygon_components':len(polys(u['geometry'])),'current_interior_rings':sum(len(p)-1 for p in polys(u['geometry'])),'representative_point':u['representative_point'],'representative_point_in_level1_land':bool(point_hits[i]),'gshhg_level1_containing_source_ids':point_hits[i],'level1_centroid_hits':counts[i],'decision':'screen_only; named land, full extent, coastline and settlement completeness unresolved'} for i,u in sorted(units.items())},'matched_source_records':[{'gshhg_id':x['id'],'land_polygon_centroid_hits':x['hits'],'assigned_location_representative_points_inside_land_polygon':x['source_representative_points_inside']} for x in matched],'limitations':['2017 global shoreline compilation is not an authoritative national island gazetteer, administrative boundary, hydrographic inventory, or settlement source.','The centroid screen leaves coastlines, tiny islands, enclosed waters and geometry intersections unverified. A complete no-hit location can be an inland feature far from any separately centroided island polygon.','A candidate matched to an assigned polygon is not evidence of legal ownership or the correctness of its parent chain.']}
(HERE/'gshhg-scope-screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'scope':len(units),'source_level1':n_level1,'matched_records':len(matched),'retained_bytes':len(native),'sha256':hashlib.sha256(native).hexdigest(),'locations_with_land_polygon_centroid_hits':sum(v>0 for v in counts.values()),'locations_with_admin_rep_point_on_gshhg_land':sum(bool(v) for v in point_hits.values())},indent=2))
