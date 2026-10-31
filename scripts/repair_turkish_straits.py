"""Classify complete strait banks and islands, then refresh shared sea ownership.

The native water channels separate Thrace from Anatolia. No coastline or island
is created. Gokceada stays European; Bozcaada and the southern Marmara islands
are Asian geographic groupings. Every ocean label remains unchanged.
"""
import argparse,gzip,hashlib,json
from pathlib import Path
import numpy as np
from scipy.ndimage import label,binary_erosion
from scipy.spatial import cKDTree
from correct_suez import xyz

LAND_BOUNDS=(24,35,32,43)
WATER_BOUNDS=(22,35,42.5,47.5)
COAST_BOUNDS=(15,25,52,53)
LAND_SEEDS=[('Thrace',27,41,19),('Anatolia',30,40,18),('Marmara Island',27.62,40.625,18),('Pasalimani',27.617,40.476,18),('Bozcaada',26.04,39.82,18),('Gokceada',25.9,40.17,19)]
SOURCES=['https://hasekieah.saglik.gov.tr/EN-880196/about--turkiye-amp-istanbul.html','https://canakkale.ktb.gov.tr/TR-70541/lapseki.html','https://canakkaletarihialan.gov.tr/en/visit/castles-and-forts/kilitbahir-castle','https://goturkiye.com/islands/islands-marmara-turkiye','https://canakkale.ktb.gov.tr/TR-70535/bozcaada.html']

def build(parent,output):
 output.mkdir(parents=True,exist_ok=True);m=json.loads((parent/'proposal.json').read_text());w,h,st=m['width'],m['height'],m['step'];rows=np.frombuffer(gzip.decompress((parent/'rows.u32.gz').read_bytes()),'<u4');runs=np.frombuffer(gzip.decompress((parent/'runs.u32.gz').read_bytes()),'<u4').reshape(-1,2)
 def extent(b):
  west,south,east,north=b;return int((west+180)/st),int((90-north)/st),int((east+180)/st)+1,int((90-south)/st)+1
 def decode(y,x0=0,x1=None):
  r=runs[rows[y]:rows[y+1]];return r[np.searchsorted(r[:,0],np.arange(x0,w if x1 is None else x1),side='right'),1].astype('uint8')
 lx0,ly0,lx1,ly1=extent(LAND_BOUNDS);patch=np.array([decode(y,lx0,lx1) for y in range(ly0,ly1)]);oldpatch=patch.copy();components,_=label(patch>=16);seed_audit=[];owners={}
 for name,lo,la,desired in LAND_SEEDS:
  sid=int(components[int((90-la)/st)-ly0,int((lo+180)/st)-lx0]);assert sid>0,name
  assert sid not in owners or owners[sid]==desired,(name,'conflicting native land seeds');owners[sid]=desired;mask=components==sid;old,cnt=np.unique(patch[mask],return_counts=True);assert np.isin(old,[18,19]).all();seed_audit.append({'name':name,'seed':[lo,la],'desired':desired,'land_cells':int(mask.sum()),'before':dict(zip(map(str,old),map(int,cnt))),'changed':int(np.count_nonzero(patch[mask]!=desired))});patch[mask]=desired
 assert np.array_equal(patch>=16,oldpatch>=16)
 def updated(y,x0=0,x1=None):
  x1=w if x1 is None else x1;row=decode(y,x0,x1)
  if ly0<=y<ly1:
   a=max(x0,lx0);b=min(x1,lx1)
   if a<b:row[a-x0:b-x0]=patch[y-ly0,a-lx0:b-lx0]
  return row
 cx0,cy0,cx1,cy1=extent(COAST_BOUNDS);coords=[];groups=[]
 for y in range(cy0,cy1,128):
  ya=max(cy0,y-1);yb=min(cy1,y+129);a=np.array([updated(z,cx0,cx1) for z in range(ya,yb)]);land=a>=16;edge=land&~binary_erosion(land);edge[[0,-1]]=False;edge[:,[0,-1]]=False;rr,cc=np.where(edge);coords.append(np.column_stack((-180+(cx0+cc+.5)*st,90-(ya+rr+.5)*st)));groups.append(a[rr,cc]&15)
 coords=np.concatenate(coords);groups=np.concatenate(groups);tree=cKDTree(xyz(coords[:,0],coords[:,1]));print('coast cells',len(coords),flush=True)
 wx0,wy0,wx1,wy1=extent(WATER_BOUNDS);water_patch=np.array([updated(y,wx0,wx1) for y in range(wy0,wy1)]);oldwater=water_patch.copy();water_count=0;min_margin=1e9;max_km=0
 for y in range(0,len(water_patch),64):
  a=water_patch[y:y+64];rr,cc=np.where(np.isin(a,[1,2,3]));lo=-180+(wx0+cc+.5)*st;la=90-(wy0+y+rr+.5)*st;d,ix=tree.query(xyz(lo,la),workers=4);km=2*6371.0088*np.arcsin(np.minimum(d/2,1));side=np.arcsin(np.cos(np.deg2rad(la))*np.sin(np.deg2rad(np.minimum(lo-COAST_BOUNDS[0],COAST_BOUNDS[2]-lo))))*6371.0088;vertical=np.minimum(la-COAST_BOUNDS[1],COAST_BOUNDS[3]-la)*np.pi/180*6371.0088;margin=np.minimum(side,vertical)-km;assert (margin>0).all();min_margin=min(min_margin,float(margin.min(initial=1e9)));max_km=max(max_km,float(km.max(initial=0)));a[rr,cc]=groups[ix];water_count+=len(rr)
 trees={g:cKDTree(xyz(coords[groups==g,0],coords[groups==g,1])) for g in [1,2,3]}
 for y in range(0,len(water_patch),64):
  a=water_patch[y:y+64];rr,cc=np.where(np.isin(a,[1,2,3]));lo=-180+(wx0+cc+.5)*st;la=90-(wy0+y+rr+.5)*st;q=xyz(lo,la);ds=np.stack([trees[g].query(q,workers=4)[0] for g in [1,2,3]]);assert np.all(ds[a[rr,cc]-1,np.arange(len(rr))]<=ds.min(axis=0)+1e-12)
 print('water independently verified',water_count,flush=True)
 # Boundary must not cut through changed water. Nonzero edge changes require a
 # larger region and another coast-margin proof, not an artificial rectangle.
 diff=(water_patch!=oldwater)&(oldwater<16);assert not(diff[0].any() or diff[-1].any() or diff[:,0].any() or diff[:,-1].any()),'expand water audit extent'
 offsets=[0];chunks=[];total=0;sha=hashlib.sha256();display=hashlib.sha256();base=hashlib.sha256();counts=np.zeros(11,dtype='int64');transitions={}
 for y in range(h):
  old=decode(y);row=updated(y)
  if wy0<=y<wy1:row[wx0:wx1]=water_patch[y-wy0]
  assert np.array_equal(row>=16,old>=16);ocean=np.isin(old,[7,8,9,10]);assert np.array_equal(row[ocean],old[ocean]);changed=row!=old;codes,ct=np.unique(old[changed].astype('uint16')*32+row[changed],return_counts=True)
  for code,n in zip(codes,ct):key=f'{code//32}->{code%32}';transitions[key]=transitions.get(key,0)+int(n)
  base.update((old&15).tobytes());display.update(row.tobytes());ids=row&15;sha.update(ids.tobytes());counts+=np.bincount(ids,minlength=11);ends=np.r_[np.flatnonzero(row[:-1]!=row[1:])+1,w].astype('uint32');pairs=np.column_stack((ends,row[ends-1])).astype('<u4');chunks.append(pairs.tobytes());total+=len(ends);offsets.append(total)
 assert base.hexdigest()==m['sha256_uncompressed'];rb=np.array(offsets,dtype='<u4').tobytes();vb=b''.join(chunks)
 for name,raw in [('rows',rb),('runs',vb)]:(output/f'{name}.u32.gz').write_bytes(gzip.compress(raw,compresslevel=6,mtime=0))
 m.update(proposal_id='continent-20261031-v19',sha256_uncompressed=sha.hexdigest(),display_sha256_uncompressed=display.hexdigest(),water_rule_version='bounded-families-native-coast-12nm-v19');m['local_grid'].update(run_count=total,rows_sha256=hashlib.sha256(rb).hexdigest(),runs_sha256=hashlib.sha256(vb).hexdigest(),decoded_bytes=len(rb)+len(vb),compressed_bytes=sum((output/f'{x}.u32.gz').stat().st_size for x in ['rows','runs']))
 for g in m['groups']:g['cells']=int(counts[g['id']])
 audit={'land_water_mask_changes':0,'ocean_label_changes':0,'land_affiliation_changes':int(np.count_nonzero(patch!=oldpatch)),'water_affiliation_changes':int(diff.sum()),'water_cells_audited':water_count,'land_components':seed_audit,'transitions':transitions,'coast_search_bounds':COAST_BOUNDS,'water_bounds':WATER_BOUNDS,'minimum_omitted_coast_distance_margin_km':min_margin,'max_nearest_coast_km':max_km,'independent_nearest_coast_mismatches':0,'changed_water_on_audit_extent_edge':0,'sources':SOURCES,'method':'Complete native connected strait-bank landmasses and named island affiliations; spherical nearest native coastline for shared waters. Both shores retain their actual shapes. No missing island is created.'}
 m['turkish_straits_audit']=audit;(output/'proposal.json').write_text(json.dumps(m,separators=(',',':'))+'\n');(output/'turkish-straits-audit.json').write_text(json.dumps(audit,indent=2)+'\n');print(json.dumps(audit),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('parent',type=Path);p.add_argument('output',type=Path);a=p.parse_args();build(a.parent,a.output)
