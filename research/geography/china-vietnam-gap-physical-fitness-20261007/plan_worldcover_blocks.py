#!/usr/bin/env python3
"""Plan complete ESA WorldCover blocks for pinned restored component geometries."""
import hashlib, json, math, struct, subprocess
from pathlib import Path

BASE='c9518bafefb0e7c4bd53842284e0208ab5223dc6'
ROOT=Path(__file__).resolve().parent
SRC=ROOT/'sources'
COMPONENTS={
 'physical-component:002641892e7354093a13a207fc47deb3141691473079e89537752c78dc5a92fa':('research/geography/indonesia-borneo-source-fitness-20261007/vintages/restore-450126d0/components-000.json','eac8b87294e31722939ff834289c00be512312ab83e81720d4fabd577cd5da36'),
 'physical-component:4716f097520ef2f6a7cecc0a5d7b4d00e4066aaa1252765726fa5a244a4b0b91':('research/geography/indonesia-borneo-source-fitness-20261007/vintages/restore-450126d0/components-003.json','b02763e7ee4e514a6208432d5ec3d78713cdae5f15b19118a3ac8ba43184cf85'),
}
def pinned(path, expected):
 data=subprocess.check_output(['git','show',f'{BASE}:{path}'])
 assert hashlib.sha256(data).hexdigest()==expected,(path,hashlib.sha256(data).hexdigest())
 return json.loads(data)
features={}
for fid,(path,digest) in COMPONENTS.items():
 fc=pinned(path,digest)
 features.update({x['id']:x for x in fc['features'] if x.get('id')==fid})
assert set(features)==set(COMPONENTS)
coords=[]
def walk(v):
 if isinstance(v,(list,tuple)):
  if len(v)>=2 and all(isinstance(x,(int,float)) for x in v[:2]): coords.append((float(v[0]),float(v[1])))
  else:
   for x in v: walk(x)
for f in features.values(): walk(f['geometry']['coordinates'])
west=min(x for x,y in coords); east=max(x for x,y in coords); south=min(y for x,y in coords); north=max(y for x,y in coords)
d=(SRC/'worldcover-ifd-range-0-131071.bin').read_bytes(); ifd=struct.unpack_from('<I',d,4)[0]; n=struct.unpack_from('<H',d,ifd)[0]
sizes={1:1,2:1,3:2,4:4,5:8,6:1,7:1,8:2,9:4,10:8,11:4,12:8}; tags={}
for i in range(n):
 pos=ifd+2+12*i; tag,typ,c=struct.unpack_from('<HHI',d,pos); length=sizes[typ]*c
 raw=d[pos+8:pos+8+length] if length<=4 else d[struct.unpack_from('<I',d,pos+8)[0]:struct.unpack_from('<I',d,pos+8)[0]+length]
 tags[tag]=(typ,c,raw)
def vals(t,fmt):
 typ,c,raw=tags[t]; return struct.unpack('<'+fmt*c,raw)
assert vals(256,'H')==(36000,) and vals(257,'H')==(36000,)
scale=vals(33550,'d'); tie=vals(33922,'d'); assert scale[:2]==(1/12000,1/12000) and tie[3:5]==(105.0,24.0)
assert 'N21E105' in tags[42112][2].decode('ascii')
c0=math.floor((west-tie[3])/scale[0]); c1=math.ceil((east-tie[3])/scale[0]); r0=math.floor((tie[4]-north)/scale[1]); r1=math.ceil((tie[4]-south)/scale[1]); bw,bh=vals(322,'H')[0],vals(323,'H')[0]
off=vals(324,'I'); counts=vals(325,'I'); blocks=[]
for row in range(r0//bh,(r1-1)//bh+1):
 for col in range(c0//bw,(c1-1)//bw+1):
  i=row*36+col; blocks.append({'row':row,'column':col,'tile_index':i,'offset':off[i],'byte_count':counts[i]})
assert len(blocks)==2 and sum(x['byte_count'] for x in blocks)<=32*1024*1024
out={'baseline_commit':BASE,'component_sources':{fid:{'path':path,'sha256':digest} for fid,(path,digest) in COMPONENTS.items()},'candidate_ids':sorted(features),'candidate_reported_areas_m2':{i:features[i]['properties']['measured_fragment_area_sum_m2'] for i in features},'candidate_geometry_bbox':[west,south,east,north],'source':'ESA WorldCover 10m 2021 v200 Map COG N21E105','source_object_bytes':102974131,'etag':'"a0c724f8d28f1c4d198ac6f69ff4fded-13"','last_modified':'Wed, 26 Oct 2022 12:47:57 GMT','tile_origin':[105.0,24.0],'pixel_scale_degrees':list(scale[:2]),'tile_pixels':[36000,36000],'block_pixels':[bw,bh],'pixel_window':[c0,c1,r0,r1],'selected_complete_original_blocks':blocks,'compressed_bytes':sum(x['byte_count'] for x in blocks),'decoded_bytes':len(blocks)*bw*bh,'max_individual_source_file_bytes':33554432,'phase_limit_bytes':268435456,'method':'complete native source blocks covering complete restored component geometries; no raster resampling or fill'}
(ROOT/'worldcover-block-plan.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
