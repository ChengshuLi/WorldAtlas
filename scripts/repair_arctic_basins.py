"""Assign northern ocean parents from complete IHO areas, then Nordic convention.

Continental waters have priority. In the Nordic sector the project explicitly
keeps Norwegian Sea in Atlantic and Greenland/Barents seas in Arctic.
"""
import argparse,gzip,json,hashlib
from pathlib import Path
import numpy as np
from rasterio.features import rasterize
from rasterio.transform import from_origin
from arctic_atlantic_boundary import arctic_side
from bering_strait_boundary import north_of_strait

def build(parent,output,source):
 output.mkdir(parents=True,exist_ok=True);m=json.loads((parent/'proposal.json').read_text());w,h,step=m['width'],m['height'],m['step'];rows=np.frombuffer(gzip.decompress((parent/'rows.u32.gz').read_bytes()),'<u4');runs=np.frombuffer(gzip.decompress((parent/'runs.u32.gz').read_bytes()),'<u4').reshape(-1,2)
 def decode(y):
  r=runs[rows[y]:rows[y+1]];return np.repeat(r[:,1],np.diff(np.r_[0,r[:,0]])).astype('uint8')
 src=json.loads(gzip.decompress(source.read_bytes()));features=[]
 for f in src['features']:
  n=f['properties']['name'];code=8 if n=='Bering Sea' else 7 if n in {'Labrador Sea','Norwegian Sea'} else 10
  features.append((f['geometry'],code))
 north_height=int((90-47)/step)+1
 print('rasterizing northern source once',north_height,flush=True)
 northern=rasterize(features,out_shape=(north_height,w),transform=from_origin(-180,90,step,step),fill=0,dtype='uint8')
 print('northern source ready',flush=True)
 offsets=[0];chunks=[];total=0;sha=hashlib.sha256();display=hashlib.sha256();base=hashlib.sha256();counts=np.zeros(11,dtype='int64');transitions={};lon=-180+(np.arange(w)+.5)*step
 for y in range(0,h,128):
  end=min(y+128,h);a=np.array([decode(z) for z in range(y,end)]);old=a.copy();lat=90-(np.arange(y,end)+.5)*step
  if lat[0]>=47:
   codes=np.zeros_like(a);n=min(end,north_height)-y
   if n>0:codes[:n]=northern[y:y+n]
   use=(a>=7)&(a<=10)&(codes>0);a[use]=codes[use]
   # Project gateway convention has priority over the older IHO sea-area
   # Arctic-Circle boundary. Scope ends inland on either side of the strait.
   bering=(lon[None,:]>=-172)&(lon[None,:]<=-164)&(lat[:,None]>=64)&(lat[:,None]<=68)&np.isin(a,[8,10])
   rr,cc=np.where(bering);a[rr,cc]=np.where(north_of_strait(lon[cc],lat[rr]),10,8)
   # The chosen northern Atlantic boundary across Davis Strait is 60N.
   # This covers residual source/coastline seams without splitting inner bays.
   west=(lon[None,:]>=-100)&(lon[None,:]<-45)&(lat[:,None]>=55)&np.isin(a,[7,10])
   a[west& (lat[:,None]>=60)]=10;a[west&(lat[:,None]<60)]=7
   nordic=(lon[None,:]>=-45)&(lon[None,:]<=50)&(lat[:,None]>=58)&np.isin(a,[7,10])
   rr,cc=np.where(nordic);a[rr,cc]=np.where(arctic_side(lon[cc],lat[rr]),10,7)
  changed=a!=old
  pairs,cnt=np.unique(old[changed].astype('uint16')*32+a[changed],return_counts=True)
  for pair,n in zip(pairs,cnt):
   key=f'{pair//32}->{pair%32}';transitions[key]=transitions.get(key,0)+int(n)
  assert np.array_equal(a[old>=16],old[old>=16]);assert np.array_equal(a[old<=6],old[old<=6])
  for j in range(end-y):
   row=a[j];base.update((old[j]&15).tobytes());display.update(row.tobytes());ids=row&15;sha.update(ids.tobytes());counts+=np.bincount(ids,minlength=11)
   ends=np.r_[np.flatnonzero(row[:-1]!=row[1:])+1,w].astype('uint32');pairs=np.column_stack((ends,row[ends-1])).astype('<u4');chunks.append(pairs.tobytes());total+=len(ends);offsets.append(total)
  if y%2048==0:print('rows',end,'changed',sum(transitions.values()),flush=True)
 assert base.hexdigest()==m['sha256_uncompressed'];rb=np.array(offsets,dtype='<u4').tobytes();vb=b''.join(chunks)
 for name,raw in [('rows',rb),('runs',vb)]:(output/f'{name}.u32.gz').write_bytes(gzip.compress(raw,compresslevel=6,mtime=0))
 m.update(proposal_id='continent-20261031-v16',sha256_uncompressed=sha.hexdigest(),display_sha256_uncompressed=display.hexdigest());m['local_grid'].update(run_count=total,rows_sha256=hashlib.sha256(rb).hexdigest(),runs_sha256=hashlib.sha256(vb).hexdigest(),decoded_bytes=len(rb)+len(vb),compressed_bytes=sum((output/f'{x}.u32.gz').stat().st_size for x in ['rows','runs']))
 for g in m['groups']:g['cells']=int(counts[g['id']])
 audit={'source':src['citation'],'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'changed_ocean_cells':sum(transitions.values()),'transitions':transitions,'land_cells_changed':0,'continental_water_cells_changed':0,'convention':'Complete IHO ocean/marginal-sea areas; Davis Strait 60N; Norwegian Sea Atlantic and Greenland/Barents Arctic using continuous named-cape divider. Bering gateway uses the Cape Dezhnev–Cape Prince of Wales great circle with priority over the older IHO Arctic-Circle sea limit. No global Arctic-Circle fallback.'}
 m['arctic_parent_audit']=audit;(output/'proposal.json').write_text(json.dumps(m,separators=(',',':'))+'\n');(output/'arctic-parent-audit.json').write_text(json.dumps(audit,indent=2)+'\n');print(json.dumps(audit),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('parent',type=Path);p.add_argument('output',type=Path);p.add_argument('source',type=Path);v=p.parse_args();build(v.parent,v.output,v.source)
