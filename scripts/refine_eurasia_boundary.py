"""Apply a source-based Urals/Ural River/Greater Caucasus continent divide.

Preserves the complete accepted land/water mask and reviewed northern islands.
Only Europe/Asia affiliations change; water follows changed nearest shore groups.
"""
import argparse,json,gzip,hashlib
from pathlib import Path
import numpy as np
from scipy.ndimage import binary_erosion
from scipy.spatial import cKDTree
from rasterio.features import rasterize
from rasterio.transform import from_origin
from shapely.geometry import Polygon,LineString,mapping
from correct_suez import xyz

def build(parent,reference,output):
 output.mkdir(parents=True,exist_ok=True);m=json.loads((parent/'proposal.json').read_text());w,h,st=m['width'],m['height'],m['step'];rows=np.frombuffer(gzip.decompress((parent/'rows.u32.gz').read_bytes()),'<u4');runs=np.frombuffer(gzip.decompress((parent/'runs.u32.gz').read_bytes()),'<u4').reshape(-1,2)
 def decode(y):
  r=runs[rows[y]:rows[y+1]];return np.repeat(r[:,1],np.diff(np.r_[0,r[:,0]])).astype('uint8')
 ref=json.loads(reference.read_text());f=ref['features'];u=f[0]['geometry']['coordinates'];river=f[1]['geometry']['coordinates'];c=f[2]['geometry']['coordinates'];water=[[50.5,46.2],[49.3,45.3],[48.8,44.3],c[-1]]
 route=u+river[1:]+water+list(reversed(c))[1:]+[[29.1,41.2],[29,41],[28.9,40.8],[27.3,40.5],[26.2,40],[25.5,39]]
 poly=Polygon([[-30,90],[u[0][0],90]]+route+[[-30,39]]);assert poly.is_valid and LineString(route).is_simple
 x0,x1=int(215/st),int(255/st)+1;y0,y1=int((90-u[0][1])/st),int(51/st)+1
 patch=np.array([decode(y)[x0:x1] for y in range(y0,y1)]);oldpatch=patch.copy();eur=rasterize([(mapping(poly),1)],out_shape=patch.shape,transform=from_origin(-180+x0*st,90-y0*st,st,st),fill=0,dtype='uint8')>0;land=np.isin(patch,[18,19]);patch[land]=np.where(eur[land],19,18)
 land_changes=int(np.count_nonzero(patch!=oldpatch));assert np.array_equal(patch>=16,oldpatch>=16);print('land affiliations changed',land_changes,flush=True)
 def updated(y):
  row=decode(y)
  if y0<=y<y1:row[x0:x1]=patch[y-y0]
  return row
 coords=[];before=[];after=[]
 for y in range(0,h,128):
  ya=max(0,y-1);yb=min(h,y+129);a=np.array([decode(z) for z in range(ya,yb)]);b=np.array([updated(z) for z in range(ya,yb)]);mask=a>=16;edge=mask&~binary_erosion(np.pad(mask,((0,0),(1,1)),mode='wrap'))[:,1:-1];edge[[0,-1]]=False;rr,cc=np.where(edge);coords.append(np.column_stack((-180+(cc+.5)*st,90-(rr+ya+.5)*st)));before.append(a[rr,cc]&15);after.append(b[rr,cc]&15)
 coords=np.concatenate(coords);before=np.concatenate(before);after=np.concatenate(after);tree=cKDTree(xyz(coords[:,0],coords[:,1]));print('coast tree ready',flush=True)
 offsets=[0];chunks=[];total=0;sha=hashlib.sha256();display=hashlib.sha256();base=hashlib.sha256();counts=np.zeros(11,dtype='int64');water_changes=0;transitions={};lon=-180+(np.arange(w)+.5)*st
 for y in range(0,h,64):
  end=min(y+64,h);old=np.array([decode(z) for z in range(y,end)]);a=np.array([updated(z) for z in range(y,end)]);lat=90-(np.arange(y,end)+.5)*st
  eligible=np.isin(a,[2,3])&(lon[None,:]>=25)&(lon[None,:]<=80)&(lat[:,None]>=35)&(lat[:,None]<=71)
  rr,cc=np.where(eligible)
  if len(rr):
   _,ix=tree.query(xyz(lon[cc],lat[rr]),workers=4);hit=before[ix]!=after[ix];rr=rr[hit];cc=cc[hit];desired=after[ix[hit]];water_changes+=int(np.count_nonzero(a[rr,cc]!=desired));a[rr,cc]=desired
  assert np.array_equal(a>=16,old>=16);ocean=np.isin(old,[7,8,9,10]);assert np.array_equal(a[ocean],old[ocean])
  changed=a!=old;codes,cnt=np.unique(old[changed].astype('uint16')*32+a[changed],return_counts=True)
  for code,n in zip(codes,cnt):
   key=f'{code//32}->{code%32}';transitions[key]=transitions.get(key,0)+int(n)
  for j in range(end-y):
   row=a[j];base.update((old[j]&15).tobytes());display.update(row.tobytes());ids=row&15;sha.update(ids.tobytes());counts+=np.bincount(ids,minlength=11);ends=np.r_[np.flatnonzero(row[:-1]!=row[1:])+1,w].astype('uint32');pairs=np.column_stack((ends,row[ends-1])).astype('<u4');chunks.append(pairs.tobytes());total+=len(ends);offsets.append(total)
  if y%4096==0:print('rows',end,flush=True)
 assert base.hexdigest()==m['sha256_uncompressed'];rb=np.array(offsets,dtype='<u4').tobytes();vb=b''.join(chunks)
 for name,raw in [('rows',rb),('runs',vb)]:(output/f'{name}.u32.gz').write_bytes(gzip.compress(raw,compresslevel=6,mtime=0))
 m.update(proposal_id='continent-20261031-v18',sha256_uncompressed=sha.hexdigest(),display_sha256_uncompressed=display.hexdigest(),water_rule_version='bounded-families-native-coast-12nm-v18');m['local_grid'].update(run_count=total,rows_sha256=hashlib.sha256(rb).hexdigest(),runs_sha256=hashlib.sha256(vb).hexdigest(),decoded_bytes=len(rb)+len(vb),compressed_bytes=sum((output/f'{x}.u32.gz').stat().st_size for x in ['rows','runs']))
 for g in m['groups']:g['cells']=int(counts[g['id']])
 audit={'land_water_mask_changes':0,'ocean_label_changes':0,'land_affiliation_changes':land_changes,'water_affiliation_changes':water_changes,'transitions':transitions,'reference_sha256':hashlib.sha256(reference.read_bytes()).hexdigest(),'route_vertices':len(route),'method':'Center-side classification against mapped river and source watershed route; reviewed land north of the Arctic coastal endpoint is preserved. Existing Europe/Asia waters change only when their nearest represented shore changes affiliation.','reference_limits':'Source-based geographic convention, not a universally official demarcation. Northern relief data are coarser. Short coastal connectors and the northern lowland continuation are documented in the source reference.'}
 m['eurasia_boundary_audit']=audit;(output/'proposal.json').write_text(json.dumps(m,separators=(',',':'))+'\n');(output/'eurasia-boundary-reference.geojson').write_text(json.dumps(ref));(output/'eurasia-boundary-audit.json').write_text(json.dumps(audit,indent=2)+'\n');print(json.dumps(audit),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('parent',type=Path);p.add_argument('reference',type=Path);p.add_argument('output',type=Path);v=p.parse_args();build(v.parent,v.reference,v.output)
