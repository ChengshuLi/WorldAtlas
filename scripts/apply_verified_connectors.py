"""Apply source-validated connector replacements without changing the land mask."""
import argparse,gzip,hashlib,json
from pathlib import Path
import numpy as np
from scipy.ndimage import label,binary_erosion
from scipy.spatial import cKDTree
from rasterio.features import rasterize
from rasterio.transform import from_origin
from shapely.geometry import LineString,Polygon,box,mapping
from correct_suez import xyz

def build(parent,reference,output):
 output.mkdir(parents=True,exist_ok=True);m=json.loads((parent/'proposal.json').read_text());w,h,st=m['width'],m['height'],m['step'];rows=np.frombuffer(gzip.decompress((parent/'rows.u32.gz').read_bytes()),'<u4');runs=np.frombuffer(gzip.decompress((parent/'runs.u32.gz').read_bytes()),'<u4').reshape(-1,2);ref=json.loads(reference.read_text());u=ref['features'][0]['geometry']['coordinates'];river=ref['features'][1]['geometry']['coordinates'];c=ref['features'][2]['geometry']['coordinates'];route=u+river[1:]+[[50.5,46.2],[49.3,45.3],[48.8,44.3],c[-1]]+list(reversed(c))[1:]+[[29.1,41.2],[29,41],[28.9,40.8],[27.3,40.5],[26.2,40],[25.5,39]];poly=Polygon([[-30,90],[u[0][0],90]]+route+[[-30,39]]);assert poly.is_valid and LineString(route).is_simple
 def decode(y):
  r=runs[rows[y]:rows[y+1]];return np.repeat(r[:,1],np.diff(np.r_[0,r[:,0]])).astype('uint8')
 def extent(b):
  west,south,east,north=b;return int((west+180)/st),int((90-north)/st),int((east+180)/st)+1,int((90-south)/st)+1
 patches=[];land_audits=[]
 for name,b in [('Northern watershed',(63,67,70,71)),('Ural headwater ridge',(59.30,54.65,59.6,54.8)),('Western Caucasus ridge',(37.1,44.55,38,45.2))]:
  x0,y0,x1,y1=extent(b);a=np.array([decode(y)[x0:x1] for y in range(y0,y1)]);old=a.copy();land=np.isin(a,[18,19]);transform=from_origin(-180+x0*st,90-y0*st,st,st);eur=rasterize([(mapping(poly),1)],out_shape=a.shape,transform=transform,fill=0,dtype='uint8')>0
  if name=='Northern watershed':
   barrier=rasterize([(mapping(LineString(u).intersection(box(*b))),1)],out_shape=a.shape,transform=transform,all_touched=True,dtype='uint8')>0;components,n=label(land&~barrier);ids=[]
   for lo,la,desired in [(64.5,68.7,19),(68.5,68,18)]:
    sid=int(components[int((90-la)/st)-y0,int((lo+180)/st)-x0]);assert sid>0 and sid not in ids;ids.append(sid);a[components==sid]=desired
   a[land&barrier]=np.where(eur[land&barrier],19,18)
   # Preserve reviewed island membership, including Levdiyev and Yamal islands.
  else:a[land]=np.where(eur[land],19,18)
  diff=a!=old;assert not(diff[0].any() or diff[-1].any() or diff[:,0].any() or diff[:,-1].any()),(name,'land window cuts changes');assert np.array_equal(a>=16,old>=16);land_audits.append({'region':name,'changed':int(diff.sum()),'edge_changes':0});patches.append((x0,y0,a));print(land_audits[-1],flush=True)
 def updated(y):
  row=decode(y)
  for x0,y0,a in patches:
   if y0<=y<y0+len(a):row[x0:x0+a.shape[1]]=a[y-y0]
  return row
 coords=[];groups=[]
 for y in range(0,h,128):
  ya=max(0,y-1);yb=min(h,y+129);a=np.array([updated(z) for z in range(ya,yb)]);land=a>=16;edge=land&~binary_erosion(np.pad(land,((0,0),(1,1)),mode='wrap'))[:,1:-1];edge[[0,-1]]=False;rr,cc=np.where(edge);coords.append(np.column_stack((-180+(cc+.5)*st,90-(ya+rr+.5)*st)));groups.append(a[rr,cc]&15)
 coords=np.concatenate(coords);groups=np.concatenate(groups);tree=cKDTree(xyz(coords[:,0],coords[:,1]));water_audits=[]
 for name,b in [('Northern shore',(60,65,75,74)),('Ural headwaters',(59.2,54.5,59.8,55)),('Black Sea',(25,40,43,47.5))]:
  x0,y0,x1,y1=extent(b);a=np.array([updated(y)[x0:x1] for y in range(y0,y1)]);old=a.copy();n=0
  for y in range(0,len(a),64):
   rr,cc=np.where(np.isin(a[y:y+64],[2,3]));rr+=y;_,ix=tree.query(xyz(-180+(x0+cc+.5)*st,90-(y0+rr+.5)*st),workers=4);a[rr,cc]=groups[ix];n+=len(rr)
  diff=a!=old;assert not(diff[0].any() or diff[-1].any() or diff[:,0].any() or diff[:,-1].any()),(name,'water window cuts changes');water_audits.append({'region':name,'water_cells_audited':n,'changed':int(diff.sum()),'edge_changes':0});patches.append((x0,y0,a));print(water_audits[-1],flush=True)
 offsets=[0];chunks=[];total=0;sha=hashlib.sha256();display=hashlib.sha256();base=hashlib.sha256();counts=np.zeros(11,dtype='int64');transitions={}
 for y in range(h):
  old=decode(y);row=updated(y);assert np.array_equal(row>=16,old>=16);ocean=np.isin(old,[7,8,9,10]);assert np.array_equal(row[ocean],old[ocean]);changed=row!=old;codes,ct=np.unique(old[changed].astype('uint16')*32+row[changed],return_counts=True)
  for code,n in zip(codes,ct):key=f'{code//32}->{code%32}';transitions[key]=transitions.get(key,0)+int(n)
  base.update((old&15).tobytes());display.update(row.tobytes());ids=row&15;sha.update(ids.tobytes());counts+=np.bincount(ids,minlength=11);ends=np.r_[np.flatnonzero(row[:-1]!=row[1:])+1,w].astype('uint32');pairs=np.column_stack((ends,row[ends-1])).astype('<u4');chunks.append(pairs.tobytes());total+=len(ends);offsets.append(total)
 assert base.hexdigest()==m['sha256_uncompressed'];rb=np.array(offsets,dtype='<u4').tobytes();vb=b''.join(chunks)
 for name,raw in [('rows',rb),('runs',vb)]:(output/f'{name}.u32.gz').write_bytes(gzip.compress(raw,compresslevel=6,mtime=0))
 m.update(proposal_id='continent-20261031-v21',sha256_uncompressed=sha.hexdigest(),display_sha256_uncompressed=display.hexdigest(),water_rule_version='bounded-families-native-coast-12nm-v21');m['local_grid'].update(run_count=total,rows_sha256=hashlib.sha256(rb).hexdigest(),runs_sha256=hashlib.sha256(vb).hexdigest(),decoded_bytes=len(rb)+len(vb),compressed_bytes=sum((output/f'{x}.u32.gz').stat().st_size for x in ['rows','runs']))
 for g in m['groups']:g['cells']=int(counts[g['id']])
 audit={'land_water_mask_changes':0,'ocean_label_changes':0,'land_patches':land_audits,'water_patches':water_audits,'transitions':transitions,'reference_sha256':hashlib.sha256(reference.read_bytes()).hexdigest(),'method':'Mapped northern watershed continuation; terrain-corroborated published western Caucasus and Ural headwater ridges. Source joins use exact geometry intersections, and coastal endpoints use native shore intersections/alignment. Same continental conventions; no invented island or coastline.'};m['verified_connector_refinement']=audit;m['eurasia_boundary_audit']['current_reference_sha256']=audit['reference_sha256'];m['independent_review_repairs']['pending_convention_review']='Historical v20 audit: long northern, western Caucasus and Ural headwater shortcuts are superseded by verified_connector_refinement.';(output/'proposal.json').write_text(json.dumps(m,separators=(',',':'))+'\n');(output/'verified-connector-audit.json').write_text(json.dumps(audit,indent=2)+'\n');(output/'eurasia-boundary-reference.geojson').write_bytes(reference.read_bytes());print(json.dumps(audit),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('parent',type=Path);p.add_argument('reference',type=Path);p.add_argument('output',type=Path);a=p.parse_args();build(a.parent,a.reference,a.output)
