"""Northern Eurasian landmass affiliations and their existing coastal waters.

Keep the accepted land/water mask. Yamal is Asian; named European Arctic
archipelagos remain European. Offshore components inherit a named geographic
region or their nearest mainland, rather than a global longitude cutoff.
"""
import argparse,json,gzip,hashlib
from pathlib import Path
import numpy as np,shapefile
from scipy.ndimage import label,binary_erosion,find_objects
from scipy.spatial import cKDTree
from rasterio.features import rasterize
from rasterio.transform import from_origin
from correct_suez import xyz

def build(parent,output):
 output.mkdir(parents=True,exist_ok=True);m=json.loads((parent/'proposal.json').read_text());w,h,st=m['width'],m['height'],m['step'];r=np.frombuffer(gzip.decompress((parent/'rows.u32.gz').read_bytes()),'<u4');v=np.frombuffer(gzip.decompress((parent/'runs.u32.gz').read_bytes()),'<u4').reshape(-1,2)
 def decode(y,x0=0,x1=None):
  rr=v[r[y]:r[y+1]];return rr[np.searchsorted(rr[:,0],np.arange(x0,w if x1 is None else x1),side='right'),1].astype('uint8')
 x0,x1=int(230/st),int(270/st)+1;y0,y1=int(6/st),int(26/st)+1
 a=np.array([decode(y,x0,x1) for y in range(y0,y1)]);old=a.copy();lo=-180+(x0+np.arange(a.shape[1])+.5)*st;la=90-(y0+np.arange(a.shape[0])+.5)*st;land=a>=16
 shapes=[];yamal=None;regions=[]
 src=Path(__file__).resolve().parents[2]/'worldatlas-continent-review/sources/ne_10m_geography_regions_polys/ne_10m_geography_regions_polys.shp'
 for sr in shapefile.Reader(str(src)).iterShapeRecords():
  d=sr.record.as_dict();b=sr.shape.bbox;name=d['NAME_EN']
  if b[2]<50 or b[0]>90 or b[3]<64 or b[1]>84 or d['REGION'] not in ['Europe','Asia']:continue
  if d['FEATURECLA'] not in ['Island','Island group','Pen/cape']:continue
  code=3 if d['REGION']=='Europe' else 2;geom=sr.shape.__geo_interface__;shapes.append((geom,code));regions.append({'name':name,'group':code})
  if name=='Yamal Peninsula':yamal=geom
 transform=from_origin(-180+x0*st,90-y0*st,st,st)
 named=rasterize(shapes,out_shape=a.shape,transform=transform,fill=0,dtype='uint8');ym=rasterize([(yamal,1)],out_shape=a.shape,transform=transform,fill=0,dtype='uint8')>0
 a[land&ym]=18
 # Recover the complete accepted northern peninsula shoreline, including source
 # coastline differences. The 69N processing cut separates Yamal from the
 # mainland across Baydaratskaya Bay; it is not a continental boundary.
 north=land&(la[:,None]>=69);cl,_=label(north);sy=int((90-70)/st)-y0;sx=int((70+180)/st)-x0;cid=cl[sy,sx];assert cid>0;a[cl==cid]=18;del north,cl
 components,n=label(land);main_ids=np.unique(components[-1]);main_ids=main_ids[main_ids>0]
 mainland=np.isin(components,main_ids);shore=mainland&~binary_erosion(mainland);shore[[0,-1]]=False;shore[:,[0,-1]]=False;rr,cc=np.where(shore);main_groups=a[rr,cc]&15;tree=cKDTree(xyz(lo[cc],la[rr]));islands=[]
 for i,bounds in enumerate(find_objects(components),1):
  if bounds is None or i in main_ids:continue
  yy,xx=bounds;mask=components[yy,xx]==i;ns=named[yy,xx][mask];nonzero=ns[ns>0]
  if len(nonzero):code=int(np.bincount(nonzero).argmax());method='named geographic landmass'
  else:
   ys,xs=np.where(mask);mid=len(ys)//2;y=ys[mid]+yy.start;x=xs[mid]+xx.start;_,k=tree.query(xyz(np.array([lo[x]]),np.array([la[y]])));code=int(main_groups[k[0]]);method='nearest mainland'
  region=a[yy,xx];before=region[mask].copy();region[mask]=16+code
  changed=int(np.count_nonzero(before!=region[mask]))
  if changed:islands.append({'native_bounds':[x0+xx.start,y0+yy.start,x0+xx.stop,y0+yy.stop],'group':code,'changed_land_cells':changed,'method':method})
 del components,mainland,tree
 # Geometry stays fixed, so old and new nearest-shore identities share a tree.
 shore=land&~binary_erosion(land);shore[[0,-1]]=False;shore[:,[0,-1]]=False;rr,cc=np.where(shore);old_groups=old[rr,cc]&15;new_groups=a[rr,cc]&15;tree=cKDTree(xyz(lo[cc],la[rr]));water_changes=0
 for start in range(0,len(a),64):
  band=a[start:start+64];rr,cc=np.where(np.isin(band,[2,3]));rr+=start
  if not len(rr):continue
  _,k=tree.query(xyz(lo[cc],la[rr]),workers=4);affected=old_groups[k]!=new_groups[k];rr=rr[affected];cc=cc[affected];target=new_groups[k[affected]];water_changes+=int(np.count_nonzero(a[rr,cc]!=target));a[rr,cc]=target
 assert np.array_equal(a>=16,land)
 audit={'land_water_mask_changes':0,'land_affiliation_changes':int(np.count_nonzero(land&(a!=old))),'water_affiliation_changes':water_changes,'changed_island_components':islands,'region_sources':regions,'method':'Named peninsula/archipelago identity and nearest mainland for unnamed offshore components; existing continental-water cells change only where their nearest represented shore changes affiliation. All ocean cells and the land/water mask remain unchanged.'}
 offsets=[0];chunks=[];total=0;sha=hashlib.sha256();display=hashlib.sha256();counts=np.zeros(11,dtype='int64')
 for y in range(h):
  row=decode(y)
  if y0<=y<y1:row[x0:x1]=a[y-y0]
  display.update(row.tobytes());ids=row&15;sha.update(ids.tobytes());counts+=np.bincount(ids,minlength=11);ends=np.r_[np.flatnonzero(row[:-1]!=row[1:])+1,w].astype('uint32');pairs=np.column_stack((ends,row[ends-1])).astype('<u4');chunks.append(pairs.tobytes());total+=len(ends);offsets.append(total)
 rb=np.array(offsets,dtype='<u4').tobytes();vb=b''.join(chunks)
 for name,raw in [('rows',rb),('runs',vb)]:(output/f'{name}.u32.gz').write_bytes(gzip.compress(raw,compresslevel=6,mtime=0))
 m.update(proposal_id='continent-20261031-v17',sha256_uncompressed=sha.hexdigest(),display_sha256_uncompressed=display.hexdigest());m['local_grid'].update(run_count=total,rows_sha256=hashlib.sha256(rb).hexdigest(),runs_sha256=hashlib.sha256(vb).hexdigest(),decoded_bytes=len(rb)+len(vb),compressed_bytes=sum((output/f'{x}.u32.gz').stat().st_size for x in ['rows','runs']))
 for g in m['groups']:g['cells']=int(counts[g['id']])
 m['northern_eurasia_audit']=audit;(output/'proposal.json').write_text(json.dumps(m,separators=(',',':'))+'\n');(output/'northern-eurasia-audit.json').write_text(json.dumps(audit,indent=2)+'\n');print(json.dumps(audit),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('parent',type=Path);p.add_argument('output',type=Path);v=p.parse_args();build(v.parent,v.output)
