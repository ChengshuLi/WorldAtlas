"""Targeted v19 audit corrections; preserve coastlines and chosen land route."""
import argparse,gzip,hashlib,json
from pathlib import Path
import numpy as np
from scipy.ndimage import label,binary_erosion
from scipy.spatial import cKDTree
from rasterio.features import rasterize
from rasterio.transform import from_origin
from shapely.geometry import LineString,box,mapping
from correct_suez import xyz
from arctic_atlantic_boundary import arctic_side

def build(parent,output):
 output.mkdir(parents=True,exist_ok=True);m=json.loads((parent/'proposal.json').read_text());w,h,st=m['width'],m['height'],m['step'];rows=np.frombuffer(gzip.decompress((parent/'rows.u32.gz').read_bytes()),'<u4');runs=np.frombuffer(gzip.decompress((parent/'runs.u32.gz').read_bytes()),'<u4').reshape(-1,2)
 def decode(y):
  r=runs[rows[y]:rows[y+1]];return np.repeat(r[:,1],np.diff(np.r_[0,r[:,0]])).astype('uint8')
 def extent(b):
  west,south,east,north=b;return int((west+180)/st),int((90-north)/st),int((east+180)/st)+1,int((90-south)/st)+1
 patches=[];land_audits=[]
 b=(63,67,70,71);x0,y0,x1,y1=extent(b);a=np.array([decode(y)[x0:x1] for y in range(y0,y1)]);old=a.copy();ref=json.loads((parent/'eurasia-boundary-reference.geojson').read_text())['features'][0]['geometry'];route=LineString(ref['coordinates']).intersection(box(*b));barrier=rasterize([(mapping(route),1)],out_shape=a.shape,transform=from_origin(-180+x0*st,90-y0*st,st,st),all_touched=True,dtype='uint8')>0;land=a>=16;components,n=label(land&~barrier);main_ids=[]
 for name,lo,la,value in [('European Ural coast',64.5,68.7,19),('Asian mainland and Yamal',68.5,68,18)]:
  sid=int(components[int((90-la)/st)-y0,int((lo+180)/st)-x0]);assert sid>0 and sid not in main_ids;main_ids.append(sid);mask=components==sid;assert mask.sum()>100000;a[mask]=value
 # Reclassify whole offshore components against corrected mainland, not longitude.
 mainland=np.isin(components,main_ids);edge=mainland&~binary_erosion(mainland);rr,cc=np.where(edge);tree=cKDTree(xyz(-180+(x0+cc+.5)*st,90-(y0+rr+.5)*st));coast_groups=a[rr,cc];islands=[]
 for sid in range(1,n+1):
  if sid in main_ids:continue
  rr,cc=np.where(components==sid)
  if not len(rr):continue
  # A component touching an audit edge may be a continuation of a reviewed
  # northern island or mainland; preserve it rather than infer from a clip.
  if (rr==0).any() or (rr==a.shape[0]-1).any() or (cc==0).any() or (cc==a.shape[1]-1).any():continue
  d,ix=tree.query(xyz(-180+(x0+cc+.5)*st,90-(y0+rr+.5)*st));desired=int(coast_groups[ix[int(np.argmin(d))]]);changed=int(np.count_nonzero(a[rr,cc]!=desired));a[rr,cc]=desired
  if changed:islands.append({'cells':len(rr),'changed':changed,'group':desired&15,'sample_cell':[int(x0+cc[len(cc)//2]),int(y0+rr[len(rr)//2])]})
 assert np.array_equal(land,a>=16);land_audits.append({'region':'Northern join','changed':int(np.count_nonzero(a!=old)),'offshore_components':islands,'route_changed':False});patches.append((x0,y0,a));print(land_audits[-1],flush=True)
 # Lampedusa/Lampione footprint only; Linosa lies outside this box.
 b=(12.1,35.4,12.75,35.7);x0,y0,x1,y1=extent(b);a=np.array([decode(y)[x0:x1] for y in range(y0,y1)]);land=a>=16;assert np.isin(a[land],[19]).all();a[land]=17;patches.append((x0,y0,a));land_audits.append({'region':'Lampedusa and represented Lampione footprint','changed':int(land.sum()),'new_group':1,'missing_islands_added':0})
 def updated(y):
  row=decode(y)
  for x0,y0,a in patches:
   if y0<=y<y0+len(a):row[x0:x0+a.shape[1]]=a[y-y0]
  return row
 coords=[];groups=[]
 for y in range(0,h,128):
  ya=max(0,y-1);yb=min(h,y+129);a=np.array([updated(z) for z in range(ya,yb)]);land=a>=16;edge=land&~binary_erosion(np.pad(land,((0,0),(1,1)),mode='wrap'))[:,1:-1];edge[[0,-1]]=False;rr,cc=np.where(edge);coords.append(np.column_stack((-180+(cc+.5)*st,90-(ya+rr+.5)*st)));groups.append(a[rr,cc]&15)
 coords=np.concatenate(coords);groups=np.concatenate(groups);tree=cKDTree(xyz(coords[:,0],coords[:,1]));water_audits=[]
 for name,b in [('northern coastal transition',(60,65,75,74)),('Caspian',(46,36,55,48)),('Diomede strait',(-175,62,-160,70)),('central Mediterranean',(5,30,20,41))]:
  x0,y0,x1,y1=extent(b);a=np.array([updated(y)[x0:x1] for y in range(y0,y1)]);old=a.copy();audited=0
  for y in range(0,len(a),64):
   rr,cc=np.where((a[y:y+64]>=1)&(a[y:y+64]<=6));rr+=y;d,ix=tree.query(xyz(-180+(x0+cc+.5)*st,90-(y0+rr+.5)*st),workers=4)
   if name=='Diomede strait':
    # The identified defect is in the 12nm coast band. Do not turn this into
    # an unrequested reclassification of the entire Bering Sea.
    near=d<=2*np.sin(22.224/(2*6371.0088));rr=rr[near];cc=cc[near];ix=ix[near]
   a[rr,cc]=groups[ix];audited+=len(rr)
  diff=a!=old;edge_changes=int(diff[0].sum()+diff[-1].sum()+diff[:,0].sum()+diff[:,-1].sum());assert edge_changes==0,(name,'expand audit window',edge_changes)
  water_audits.append({'region':name,'cells_audited':audited,'changed':int(diff.sum()),'edge_changes':edge_changes});patches.append((x0,y0,a));print(water_audits[-1],flush=True)
 offsets=[0];chunks=[];total=0;sha=hashlib.sha256();display=hashlib.sha256();base=hashlib.sha256();counts=np.zeros(11,dtype='int64');transitions={};lon=-180+(np.arange(w)+.5)*st
 for y in range(h):
  old=decode(y);row=updated(y);lat=90-(y+.5)*st
  if lat>=58:
   mask=np.isin(row,[7,10])&(lon>=-45)&(lon<=50);row[mask]=np.where(arctic_side(lon[mask],np.full(mask.sum(),lat)),10,7)
  assert np.array_equal(row>=16,old>=16);changed=row!=old;codes,ct=np.unique(old[changed].astype('uint16')*32+row[changed],return_counts=True)
  for code,n in zip(codes,ct):key=f'{code//32}->{code%32}';transitions[key]=transitions.get(key,0)+int(n)
  base.update((old&15).tobytes());display.update(row.tobytes());ids=row&15;sha.update(ids.tobytes());counts+=np.bincount(ids,minlength=11);ends=np.r_[np.flatnonzero(row[:-1]!=row[1:])+1,w].astype('uint32');pairs=np.column_stack((ends,row[ends-1])).astype('<u4');chunks.append(pairs.tobytes());total+=len(ends);offsets.append(total)
 assert base.hexdigest()==m['sha256_uncompressed'];rb=np.array(offsets,dtype='<u4').tobytes();vb=b''.join(chunks)
 for name,raw in [('rows',rb),('runs',vb)]:(output/f'{name}.u32.gz').write_bytes(gzip.compress(raw,compresslevel=6,mtime=0))
 m.update(proposal_id='continent-20261031-v20',sha256_uncompressed=sha.hexdigest(),display_sha256_uncompressed=display.hexdigest(),water_rule_version='bounded-families-native-coast-12nm-v20');m['local_grid'].update(run_count=total,rows_sha256=hashlib.sha256(rb).hexdigest(),runs_sha256=hashlib.sha256(vb).hexdigest(),decoded_bytes=len(rb)+len(vb),compressed_bytes=sum((output/f'{x}.u32.gz').stat().st_size for x in ['rows','runs']))
 for g in m['groups']:g['cells']=int(counts[g['id']])
 # Remove obsolete historical buffer wording; retain the latest approved rule.
 for d in m.get('reviewed_grouping_decisions',[]):
  if d['subject']=='Socotra Archipelago':d['scope']='Archipelago; ordinary coastal water uses the current 22.224 km native-shore rule, with the Gulf of Aden bounded-water convention separate.'
 audit={'land_water_mask_changes':0,'land_representation_changes':0,'northern_route_changed':False,'land_patches':land_audits,'water_patches':water_audits,'transitions':transitions,'arctic_precision':'Direct great-circle plane classification, replacing interpolated curve latitude.','pending_convention_review':'The northern lowland connector and Caucasus coastal continuations remain explicitly editorial interpretations; this repair corrects implementation and does not silently substitute a new route.'};m['independent_review_repairs']=audit;(output/'proposal.json').write_text(json.dumps(m,separators=(',',':'))+'\n');(output/'independent-review-repairs.json').write_text(json.dumps(audit,indent=2)+'\n');print(json.dumps(audit),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('parent',type=Path);p.add_argument('output',type=Path);a=p.parse_args();build(a.parent,a.output)
