"""Resolve a reviewed disconnected ocean label using its containing ocean.

The input topology mask must be generated from this exact candidate. This does
not auto-reassign legitimate separated basins such as Arctic Baffin/Davis.
"""
import argparse,json,gzip,hashlib
from pathlib import Path
import numpy as np
from shapely.geometry import shape
from shapely import covers,points,distance
p=argparse.ArgumentParser();p.add_argument('parent',type=Path);p.add_argument('output',type=Path);p.add_argument('open_mask',type=Path);p.add_argument('reference',type=Path);p.add_argument('--from-code',type=int,required=True);p.add_argument('--to-code',type=int,required=True);a=p.parse_args()
a.output.mkdir(parents=True,exist_ok=True);m=json.loads((a.parent/'proposal.json').read_text());r=np.frombuffer(gzip.decompress((a.parent/'rows.u32.gz').read_bytes()),'<u4');v=np.frombuffer(gzip.decompress((a.parent/'runs.u32.gz').read_bytes()),'<u4').reshape(-1,2);opened=np.load(a.open_mask);assert len(opened)==len(v)
pin=json.loads(Path(str(a.open_mask)+'.meta.json').read_text());assert pin['runs_sha256']==m['local_grid']['runs_sha256'];assert pin['ocean_code']==a.from_code
chosen=(v[:,1]==a.from_code)&~opened;coordinates=[]
for y in range(m['height']):
 start,end=map(int,r[y:y+2])
 for i in range(start,end):
  if not chosen[i]:continue
  x0=int(v[i-1,0]) if i>start else 0;x=np.arange(x0,int(v[i,0]));coordinates.extend(zip(-180+(x+.5)*m['step'],np.full(len(x),90-(y+.5)*m['step'])))
c=np.array(coordinates);reference=json.loads(a.reference.read_text());g=shape(reference['geometry']);ps=points(c);inside=covers(g,ps);d=distance(g,ps[~inside]);max_distance=float(d.max()) if len(d) else 0
# Every reassigned native center must belong to the verified parent basin.
assert inside.all(),(int((~inside).sum()),max_distance)
out=v.copy();out[chosen,1]=a.to_code;sha=hashlib.sha256();display=hashlib.sha256();counts=np.zeros(11,dtype='int64')
for y in range(m['height']):
 rr=out[r[y]:r[y+1]];row=np.repeat(rr[:,1],np.diff(np.r_[0,rr[:,0]])).astype('uint8');display.update(row.tobytes());sha.update((row&15).tobytes());counts+=np.bincount(row&15,minlength=11)
rb=r.astype('<u4').tobytes();vb=out.astype('<u4').tobytes()
for n,raw in [('rows',rb),('runs',vb)]:(a.output/f'{n}.u32.gz').write_bytes(gzip.compress(raw,compresslevel=6,mtime=0))
m.update(sha256_uncompressed=sha.hexdigest(),display_sha256_uncompressed=display.hexdigest());m['local_grid'].update(rows_sha256=hashlib.sha256(rb).hexdigest(),runs_sha256=hashlib.sha256(vb).hexdigest(),compressed_bytes=sum((a.output/f'{x}.u32.gz').stat().st_size for x in ['rows','runs']))
for group in m['groups']:group['cells']=int(counts[group['id']])
audit={'from':a.from_code,'to':a.to_code,'changed_water_cells':len(c),'land_cells_changed':0,'reference_name':reference['properties']['name'],'reference_sha256':hashlib.sha256(a.reference.read_bytes()).hexdigest(),'centers_inside_reference':int(inside.sum()),'source_coast_residual_centers':int((~inside).sum()),'maximum_residual_distance_degrees':max_distance,'source':'https://doi.org/10.14284/323'}
m['reviewed_parent_ocean_component']=audit;(a.output/'proposal.json').write_text(json.dumps(m,separators=(',',':'))+'\n');print(json.dumps(audit))
