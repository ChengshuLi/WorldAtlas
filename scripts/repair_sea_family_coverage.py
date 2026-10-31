"""Audit all source subdivisions and fill bounded-parent coverage gaps.

Only ocean-coded water in explicit constituent masks is changed. Existing
continental divisions and every land cell retain their reviewed assignment.
"""
import argparse,gzip,hashlib,json
from pathlib import Path
import numpy as np,shapefile
from scipy.ndimage import binary_erosion
from scipy.spatial import cKDTree
from rasterio.features import rasterize
from rasterio.transform import from_origin
from correct_suez import xyz
from sea_families import child_rules,OPEN_WATERS
from rebuild_northern_indian import malacca_side

def build(parent,output,shelikof):
 output.mkdir(parents=True,exist_ok=True);m=json.loads((parent/'proposal.json').read_text());w,h,step=m['width'],m['height'],m['step']
 rows=np.frombuffer(gzip.decompress((parent/m['local_grid']['rows']).read_bytes()),'<u4');runs=np.frombuffer(gzip.decompress((parent/m['local_grid']['runs']).read_bytes()),'<u4').reshape(-1,2)
 def decode(y):
  r=runs[rows[y]:rows[y+1]];return np.repeat(r[:,1],np.diff(np.r_[0,r[:,0]])).astype('uint8')
 coords=[];groups=[]
 for y in range(0,h,128):
  ya=max(0,y-1);yb=min(h,y+129);a=np.array([decode(z) for z in range(ya,yb)]);land=a>=16
  edge=land&~binary_erosion(np.pad(land,((0,0),(1,1)),mode='wrap'))[:,1:-1];edge[[0,-1]]=False
  rr,cc=np.where(edge);coords.append(np.column_stack((-180+(cc+.5)*step,90-(rr+ya+.5)*step)));groups.append(a[rr,cc]&15)
 coords=np.concatenate(coords);groups=np.concatenate(groups);tree=cKDTree(xyz(coords[:,0],coords[:,1]));print('coast ready',len(coords),flush=True)
 rules=child_rules();source=Path(__file__).resolve().parents[2]/'worldatlas-continent-review/sources/ne_10m_geography_marine_polys/ne_10m_geography_marine_polys.shp'
 marine=[];catalog=[]
 parents=set(m.get('shared_seas',[]))|{n for ns in m.get('continent_seas',{}).values() for n in ns}
 for i,sr in enumerate(shapefile.Reader(str(source)).iterShapeRecords()):
  name=sr.record.as_dict()['name'];rule=rules.get(name)
  disposition='bounded constituent' if rule else 'open/coastal rule' if name in OPEN_WATERS else 'existing parent rule' if name in parents else 'unchanged; additional review'
  catalog.append({'source_record':i,'name':name,'bounds':sr.shape.bbox,'disposition':disposition,'family':rule['family'] if rule else None})
  if rule:marine.append((name,sr.shape.__geo_interface__,sr.shape.bbox,rule['group']))
 # NOAA names this bounded mainland/island passage explicitly. Its coastal
 # forecast polygon supplies the passage footprint; this is not a legal limit.
 ref=shelikof
 if ref.exists():
  f=json.loads(ref.read_text());marine.append(('Shelikof Strait',f['geometry'],[-155.781,57.273,-152.534,58.856],4))
 offsets=[0];chunks=[];total=0;sha=hashlib.sha256();display=hashlib.sha256();base=hashlib.sha256();counts=np.zeros(11,dtype='int64');changes={};lon=-180+(np.arange(w)+.5)*step
 for y in range(0,h,64):
  end=min(y+64,h);a=np.array([decode(z) for z in range(y,end)]);old=a.copy();lat=90-(np.arange(y,end)+.5)*step;transform=from_origin(-180,90-y*step,step,step)
  for name,geom,b,code in marine:
   if b[3]<lat[-1]-step or b[1]>lat[0]+step:continue
   mask=rasterize([(geom,1)],out_shape=a.shape,transform=transform,fill=0,dtype='uint8')>0
   if name=='Strait of Malacca':
    mask &= ~malacca_side(lon[None,:],lat[:,None])
   rr,cc=np.where(mask&(a>=7)&(a<=10))
   if not len(rr):continue
   if code==99:
    _,idx=tree.query(xyz(lon[cc],lat[rr]),workers=4);a[rr,cc]=groups[idx]
   else:a[rr,cc]=code
   changes[name]=changes.get(name,0)+len(rr)
  assert np.array_equal(a[old>=16],old[old>=16]);assert np.array_equal(a[old<=6],old[old<=6])
  for j in range(end-y):
   row=a[j];base.update((old[j]&15).tobytes());display.update(row.tobytes());ids=row&15;sha.update(ids.tobytes());counts+=np.bincount(ids,minlength=11)
   ends=np.r_[np.flatnonzero(row[:-1]!=row[1:])+1,w].astype('uint32');pairs=np.column_stack((ends,row[ends-1])).astype('<u4');chunks.append(pairs.tobytes());total+=len(ends);offsets.append(total)
  if y%2048==0:print('rows',end,'changes',sum(changes.values()),flush=True)
 assert base.hexdigest()==m['sha256_uncompressed']
 rb=np.array(offsets,dtype='<u4').tobytes();vb=b''.join(chunks)
 for name,raw in [('rows',rb),('runs',vb)]:(output/f'{name}.u32.gz').write_bytes(gzip.compress(raw,compresslevel=6,mtime=0))
 m.update(proposal_id='continent-20261031-v15',sha256_uncompressed=sha.hexdigest(),display_sha256_uncompressed=display.hexdigest());m['local_grid'].update(run_count=total,rows_sha256=hashlib.sha256(rb).hexdigest(),runs_sha256=hashlib.sha256(vb).hexdigest(),decoded_bytes=len(rb)+len(vb),compressed_bytes=sum((output/f'{x}.u32.gz').stat().st_size for x in ['rows','runs']))
 for g in m['groups']:g['cells']=int(counts[g['id']])
 audit={'changed_water_cells':sum(changes.values()),'land_cells_changed':0,'existing_continental_water_cells_changed':0,'by_constituent':changes,'source':'https://www.naturalearthdata.com/downloads/10m-physical-vectors/10m-physical-labels/','method':'Explicit bounded-parent constituent coverage. Shared constituents use nearest represented coast; existing assignments retained. Open named embayments not automatically promoted.'}
 m['sea_family_audit']=audit;(output/'proposal.json').write_text(json.dumps(m,separators=(',',':'))+'\n');(output/'sea-family-audit.json').write_text(json.dumps(audit,indent=2)+'\n');(output/'marine-source-coverage.json').write_text(json.dumps(catalog,indent=2)+'\n');print(json.dumps(audit),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('parent',type=Path);p.add_argument('output',type=Path);p.add_argument('shelikof',type=Path);a=p.parse_args();build(a.parent,a.output,a.shelikof)
