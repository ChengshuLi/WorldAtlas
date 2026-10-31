"""Recompute the existing Bering continental-water split across the dateline."""
import argparse,gzip,json,hashlib
from pathlib import Path
import numpy as np
from scipy.ndimage import binary_erosion
from scipy.spatial import cKDTree
from correct_suez import xyz

def build(parent,output):
 output.mkdir(parents=True,exist_ok=True);m=json.loads((parent/'proposal.json').read_text());s=m['step'];w=m['width'];h=m['height'];rr=np.frombuffer(gzip.decompress((parent/'rows.u32.gz').read_bytes()),'<u4');vv=np.frombuffer(gzip.decompress((parent/'runs.u32.gz').read_bytes()),'<u4').reshape(-1,2)
 def row(y):
  r=vv[rr[y]:rr[y+1]];return np.repeat(r[:,1],np.diff(np.r_[0,r[:,0]])).astype('uint8')
 xs=np.r_[np.arange(int(330/s),w),np.arange(0,int(35/s))];lo=-180+(xs+.5)*s;pts=[];groups=[]
 for y in range(int(15/s),int(45/s),128):
  ya=y-1;yb=min(int(45/s)+1,y+129);a=np.array([row(z)[xs] for z in range(ya,yb)]);land=a>=16;edge=land&~binary_erosion(land);edge[[0,-1]]=False;edge[:,[0,-1]]=False;iy,ix=np.where(edge&np.isin(a&15,[2,4]));pts.append(xyz(lo[ix],90-(ya+iy+.5)*s));groups.append(a[iy,ix]&15)
 pts=np.concatenate(pts);groups=np.concatenate(groups);tree=cKDTree(pts);trees={g:cKDTree(pts[groups==g]) for g in (2,4)};print('Bering native coasts',len(pts),flush=True)
 lon=-180+(np.arange(w)+.5)*s;columns=(lon>=160)|(lon<=-153);offsets=[0];chunks=[];total=0;counts=np.zeros(11,dtype='int64');sha=hashlib.sha256();display=hashlib.sha256();base=hashlib.sha256();audited=changed=0;examples=[]
 for y in range(h):
  old=row(y);a=old.copy();la=90-(y+.5)*s
  if 50<=la<=67:
   x=np.where(columns&np.isin(a,[2,4]))[0]
   if len(x):
    q=xyz(lon[x],np.full(len(x),la));_,i=tree.query(q);new=groups[i];bad=new!=a[x];audited+=len(x);changed+=int(bad.sum())
    if bad.any():
     ds=np.stack([trees[g].query(q[bad])[0] for g in (2,4)]);expect=np.array([2,4])[ds.argmin(axis=0)];assert np.array_equal(new[bad],expect)
     if len(examples)<20:j=np.where(bad)[0][0];examples.append({'cell':[int(x[j]),y],'before':int(a[x[j]]),'after':int(new[j])})
    a[x]=new
  assert np.array_equal(a[old>=16],old[old>=16]);assert np.array_equal(a[old>=7],old[old>=7])
  base.update((old&15).tobytes());display.update(a.tobytes());ids=a&15;sha.update(ids.tobytes());counts+=np.bincount(ids,minlength=11);ends=np.r_[np.flatnonzero(a[:-1]!=a[1:])+1,w].astype('uint32');pairs=np.column_stack((ends,a[ends-1])).astype('<u4');chunks.append(pairs.tobytes());total+=len(ends);offsets.append(total)
 assert base.hexdigest()==m['sha256_uncompressed'];rb=np.array(offsets,dtype='<u4').tobytes();vb=b''.join(chunks)
 for n,data in [('rows',rb),('runs',vb)]:(output/f'{n}.u32.gz').write_bytes(gzip.compress(data,compresslevel=6,mtime=0))
 m.update(sha256_uncompressed=sha.hexdigest(),display_sha256_uncompressed=display.hexdigest());m['local_grid'].update(run_count=total,rows_sha256=hashlib.sha256(rb).hexdigest(),runs_sha256=hashlib.sha256(vb).hexdigest(),decoded_bytes=len(rb)+len(vb),compressed_bytes=sum((output/f'{n}.u32.gz').stat().st_size for n in ['rows','runs']))
 for g in m['groups']:g['cells']=int(counts[g['id']])
 audit={'water_cells_audited':audited,'water_cells_changed':changed,'land_cells_changed':0,'ocean_cells_changed':0,'changed_cell_independent_mismatches':0,'examples':examples,'method':'Uniform nearest represented coast across the full existing continental-water footprint in the Bering review region, with longitude wrapping. No ocean boundary or land affiliation changes.'};m['bering_partition_refinement']=audit;(output/'proposal.json').write_text(json.dumps(m,separators=(',',':'))+'\n');(output/'bering-partition-audit.json').write_text(json.dumps(audit,indent=2)+'\n');print(json.dumps(audit),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('parent',type=Path);p.add_argument('output',type=Path);v=p.parse_args();build(v.parent,v.output)
