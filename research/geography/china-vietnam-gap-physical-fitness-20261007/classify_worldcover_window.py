#!/usr/bin/env python3
"""Classify pinned restored component geometries against retained native COG blocks."""
import hashlib,json,math,resource,struct,subprocess,zlib
from pathlib import Path
BASE='c9518bafefb0e7c4bd53842284e0208ab5223dc6'
ROOT=Path(__file__).resolve().parent; SRC=ROOT/'sources'
def read_required(path):
 return path.read_bytes()
COMPONENTS={
 'physical-component:002641892e7354093a13a207fc47deb3141691473079e89537752c78dc5a92fa':('research/geography/indonesia-borneo-source-fitness-20261007/vintages/restore-450126d0/components-000.json','eac8b87294e31722939ff834289c00be512312ab83e81720d4fabd577cd5da36'),
 'physical-component:4716f097520ef2f6a7cecc0a5d7b4d00e4066aaa1252765726fa5a244a4b0b91':('research/geography/indonesia-borneo-source-fitness-20261007/vintages/restore-450126d0/components-003.json','b02763e7ee4e514a6208432d5ec3d78713cdae5f15b19118a3ac8ba43184cf85'),
}
features={}
for fid,(path,digest) in COMPONENTS.items():
 raw=subprocess.check_output(['git','show',f'{BASE}:{path}']); assert hashlib.sha256(raw).hexdigest()==digest
 fc=json.loads(raw); features.update({x['id']:x for x in fc['features'] if x.get('id')==fid})
assert set(features)==set(COMPONENTS)
# Original candidate fragments supply contact context only; the restored components above are the subject geometries.
frag_path='coordination/engineering/physical-gap-audit-1005-20261005-local18/detection-v4/candidates-007.geojson.gz'
frag_raw=subprocess.check_output(['git','show',f'{BASE}:{frag_path}'])
assert hashlib.sha256(frag_raw).hexdigest()=='ff497d1127d47e9df308d118e89a4c3e893a0ed4078da82aaab82326cc9919c7'
import gzip
fc=json.loads(gzip.decompress(frag_raw)); frag_ids={'physical-component:002641892e7354093a13a207fc47deb3141691473079e89537752c78dc5a92fa':'physical-gap:1209:217:028bd47648ec7f25603ea996f687a78431b6c7bed8e2cd4e694f13d2bdb4e5d4','physical-component:4716f097520ef2f6a7cecc0a5d7b4d00e4066aaa1252765726fa5a244a4b0b91':'physical-gap:1209:215:51b716544421fbf2635ace1b0ec4e341aa96c69c082fe26075cbd60863ad5372'}
fragments={x['id']:x for x in fc['features'] if x.get('id') in frag_ids.values()}; assert len(fragments)==2
geoms={k:v['geometry'] for k,v in features.items()}
def points(v):
 if isinstance(v,(list,tuple)) and len(v)>=2 and all(isinstance(x,(int,float)) for x in v[:2]): yield (float(v[0]),float(v[1]))
 elif isinstance(v,(list,tuple)):
  for x in v: yield from points(x)
def bounds(g):
 ps=list(points(g['coordinates'])); return min(x for x,y in ps),min(y for x,y in ps),max(x for x,y in ps),max(y for x,y in ps)
def on_segment(p,a,b):
 x,y=p; ax,ay=a; bx,by=b; cross=(x-ax)*(by-ay)-(y-ay)*(bx-ax)
 return cross==0.0 and min(ax,bx)<=x<=max(ax,bx) and min(ay,by)<=y<=max(ay,by)
def ring_covers(p,ring):
 inside=False
 for a,b in zip(ring,ring[1:]):
  if on_segment(p,a,b): return True
  x,y=p; ax,ay=a; bx,by=b
  if (ay>y)!=(by>y) and x < (bx-ax)*(y-ay)/(by-ay)+ax: inside=not inside
 return inside
def polygon_covers(p,poly):
 return ring_covers(p,poly[0]) and not any(ring_covers(p,r) for r in poly[1:])
def covers(g,p):
 t=g['type']; c=g['coordinates']
 if t=='Polygon': return polygon_covers(p,c)
 if t=='MultiPolygon': return any(polygon_covers(p,q) for q in c)
 if t=='GeometryCollection': return any(covers(x,p) for x in g['geometries'])
 return False
def geometry_area(g):
 def ring_area(r): return abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(r,r[1:]+r[:1])))/2
 def poly_area(q): return max(0,ring_area(q[0])-sum(ring_area(r) for r in q[1:]))
 t=g['type']; c=g['coordinates']
 return poly_area(c) if t=='Polygon' else sum(poly_area(q) for q in c) if t=='MultiPolygon' else 0
def contact_summary(g):
 return {'type':g['type'],'length_degrees':sum(math.hypot(b[0]-a[0],b[1]-a[1]) for a,b in zip(list(points(g['coordinates'])),list(points(g['coordinates']))[1:])) if g['type'] in ('LineString','MultiLineString') else 0.0,'bounds':list(bounds(g)),'areal_pixel_sampling_applicable':False}
# Parse retained native TIFF metadata.
d=read_required(SRC/'worldcover-ifd-range-0-131071.bin'); ifd=struct.unpack_from('<I',d,4)[0]; n=struct.unpack_from('<H',d,ifd)[0]
sizes={1:1,2:1,3:2,4:4,5:8,6:1,7:1,8:2,9:4,10:8,11:4,12:8}; tags={}
for i in range(n):
 pos=ifd+2+12*i; tag,typ,count=struct.unpack_from('<HHI',d,pos); length=sizes[typ]*count
 val=d[pos+8:pos+8+length] if length<=4 else d[struct.unpack_from('<I',d,pos+8)[0]:struct.unpack_from('<I',d,pos+8)[0]+length]
 tags[tag]=(typ,count,val)
def values(tag,fmt):
 t,c,b=tags[tag]; return struct.unpack('<'+fmt*c,b)
scale=values(33550,'d'); tie=values(33922,'d'); assert scale[:2]==(1/12000,1/12000) and tie[3:5]==(105.0,24.0)
metadata=tags[42112][2].decode('ascii'); assert 'name="license">CC-BY 4.0' in metadata and '80  Permanent water bodies' in metadata and '90  Herbaceous wetland' in metadata
offsets=values(324,'I'); block_counts=values(325,'I'); block_rc=[(26,25,961),(26,26,962)]; blocks={}
for row,col,index in block_rc:
 f=SRC/f'block-{row}-{col}.bin'; data=read_required(f); assert len(data)==block_counts[index]
 raw=zlib.decompress(data); assert len(raw)==1024*1024
 blocks[(row,col)]={'raw':raw,'file':f.name,'compressed_bytes':len(data),'decoded_bytes':len(raw),'compressed_sha256':hashlib.sha256(data).hexdigest(),'offset':offsets[index]}
results={}; contacts={}
for fid,feature in features.items():
 g=geoms[fid]; minx,miny,maxx,maxy=bounds(g)
 c0=max(0,math.floor((minx-105)*12000)); c1=min(36000,math.ceil((maxx-105)*12000)); r0=max(0,math.floor((24-maxy)*12000)); r1=min(36000,math.ceil((24-miny)*12000))
 class_counts={}; n=0
 for gr in range(r0,r1):
  for gc in range(c0,c1):
   block=blocks.get((gr//1024,gc//1024))
   if block is None: continue
   x=105+(gc+0.5)/12000; y=24-(gr+0.5)/12000
   if covers(g,(x,y)):
    v=block['raw'][(gr%1024)*1024+(gc%1024)]; class_counts[str(v)]=class_counts.get(str(v),0)+1; n+=1
 results[fid]={'geometry_type':g['type'],'geometry_area_square_degrees':geometry_area(g),'geometry_area_m2_reported':feature['properties'].get('measured_fragment_area_sum_m2'),'candidate_geometry_id_hash':fid.rsplit(':',1)[-1],'pixel_window':[c0,c1,r0,r1],'pixel_center_count':n,'class_counts':dict(sorted(class_counts.items(),key=lambda kv:int(kv[0])))}
 frag=fragments[frag_ids[fid]]
 for c in frag['properties'].get('exact_location_contacts',[]):
  key=(c['id'],fid,c['kind']); contacts.setdefault(key,[]).append(contact_summary(c['geometry']))
contact_results=[{'contact_id':k[0],'candidate_id':k[1],'kind':k[2],'exact_contact_geometry_parts':v} for k,v in sorted(contacts.items())]
maxrss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
out={'baseline_commit':BASE,'component_sources':{fid:{'path':path,'sha256':digest} for fid,(path,digest) in COMPONENTS.items()},'contact_source':{'path':frag_path,'sha256':hashlib.sha256(frag_raw).hexdigest(),'bytes':len(frag_raw),'commit':BASE,'role':'contact context only'},'method':'Decode complete original ESA COG blocks with zlib and count native pixel centers covered by the exact restored component geometries. No reprojection, resampling, interpolation, geometry repair, or raster fill.','source_version':'ESA WorldCover 10m 2021 v200 Map','source_observation_period':['2021-01-01T00:00:00Z','2021-12-31T23:59:59Z'],'source_license':'CC BY 4.0','source_crs':'EPSG:4326','source_embedded_metadata_checks':['license CC-BY 4.0','class 80 Permanent water bodies','class 90 Herbaceous wetland'],'resolution_degrees':list(scale[:2]),'worldcover_global_validation_accuracy':0.767,'global_validation_caveat':'Product-level overall accuracy; not an estimate for this footprint or these near-zero-area candidate pointsets.','source_object_bytes':102974131,'source_etag':'"a0c724f8d28f1c4d198ac6f69ff4fded-13"','source_last_modified':'Wed, 26 Oct 2022 12:47:57 GMT','block_decode_cost_bytes':sum(b['decoded_bytes'] for b in blocks.values()),'process_max_rss_bytes':maxrss,'component_results':results,'contact_local_source_geometry':contact_results,'contact_scope_note':'Exact source contact geometries from pinned candidate fragments; contacts are line or point context, not physical authority.','class_semantics':{'80':'permanent water bodies','90':'herbaceous wetlands; not synonymous with open water','95':'mangroves','other_values':'WorldCover land-cover classes, not a legal shoreline delineation'},'fitness_decision':'WorldCover is not fit to adjudicate either exact restored component geometry as areal land/water: both contain zero native 10 m pixel centers. This is inability to evaluate these geometries, not evidence of land or water.','limits':['10 m land-cover raster cannot classify the two tiny component geometries.','Class 90 is wetlands, not an open-water finding.','Class 80 does not validate the boundary or gap geometry.','No source authority or release approval is implied.']}
(ROOT/'worldcover-window-findings.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'components':results,'contacts':contact_results,'peak_rss_bytes':maxrss,'decode_bytes':out['block_decode_cost_bytes'],'decision':out['fitness_decision']},indent=2))
