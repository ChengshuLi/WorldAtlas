"""Apply source-checked bounded-sea limits, preserving native coasts and ocean parents."""
import argparse,gzip,json,hashlib
from pathlib import Path
import numpy as np,shapefile
from scipy.spatial import cKDTree
from shapely.geometry import shape,Polygon,box,mapping
from shapely.ops import split
from rasterio.features import rasterize
from rasterio.transform import from_origin
from correct_suez import xyz
from sea_families import child_rules,OPEN_WATERS
from shapely.geometry import LineString,Point

def keep_side(geom,a,b,inside):
 a=np.array(a);b=np.array(b);d=(b-a)*100;line=LineString([a-d,b+d]);parts=split(geom,line);return next(p for p in parts.geoms if p.covers(Point(inside)))

def build(parent,output,source,iho,coasts,baseline):
 output.mkdir(parents=True,exist_ok=True);m=json.loads((parent/'proposal.json').read_text());s=m['step'];w=m['width'];h=m['height'];R=np.frombuffer(gzip.decompress((parent/'rows.u32.gz').read_bytes()),'<u4');V=np.frombuffer(gzip.decompress((parent/'runs.u32.gz').read_bytes()),'<u4').reshape(-1,2)
 def row(y):
  a=V[R[y]:R[y+1]];return np.repeat(a[:,1],np.diff(np.r_[0,a[:,0]])).astype('uint8')
 C=np.load(coasts);coords=C['coordinates'];cells=C['cells'];groups=np.empty(len(cells),dtype='uint8')
 # Coast geometry is unchanged; read affiliations from the actual current grid.
 ys=cells[:,1];assert np.all(ys[1:]>=ys[:-1]);cuts=np.r_[0,np.flatnonzero(ys[1:]!=ys[:-1])+1,len(ys)]
 for start,end in zip(cuts[:-1],cuts[1:]):groups[start:end]=row(int(ys[start]))[cells[start:end,0]]&15
 tree=cKDTree(xyz(coords[:,0],coords[:,1]));limit=2*np.sin(22.224/(2*6371.0088));marine={}
 for sr in shapefile.Reader(str(source/'ne_10m_geography_marine_polys/ne_10m_geography_marine_polys.shp')).iterShapeRecords():marine[sr.record.as_dict()['name']]=shape(sr.shape.__geo_interface__)
 corrected={};refs=[]
 for name,a,b,inside in [('Gulf of Kutch',(69+4/60,22+29/60),(69+13/60,22+50/60),(69.8,22.7)),('Gulf of Khambhät',(72+7/60,21+12/60),(72+38/60,21+5/60),(72.5,21.7))]:
  corrected[name]=keep_side(marine[name],a,b,inside);refs.append({'name':name,'endpoints':[a,b],'source':'NGA Sailing Directions Pub173, sections1.10 and2.9','source_url':'https://msi.nga.mil/api/publications/download?key=16694491%2FSFH00000%2FPub173bk.pdf'})
 g=marine['Palk Strait'];c=list(g.exterior.coords);i=max(range(len(c)-1),key=lambda i:np.linalg.norm(np.array(c[i+1])-c[i]));assert c[i][1]>10 and c[i+1][1]<10;c[i]=(79+52/60,10+17/60);c[i+1]=(80+15/60,9+50/60);corrected['Palk Strait']=Polygon(c);assert corrected['Palk Strait'].is_valid;refs.append({'name':'Palk Strait','endpoints':[c[i],c[i+1]],'source':'NGA Pub173 sections4.57,4.59,6.2'})
 for name,file in [('East China Sea','eastern-china-sea.geojson'),('Andaman Sea','andaman-or-burma-sea.geojson')]:
  raw=(iho/file).read_bytes();f=json.loads(raw);g=shape(f['geometry']);assert g.is_valid;corrected[name]=g;refs.append({'name':name,'source':'Flanders Marine Institute (2018), IHO Sea Areas v3, based on IHO S23 named geographic limits','source_url':'https://doi.org/10.14284/323','source_sha256':hashlib.sha256(raw).hexdigest(),'terms_url':'https://www.marineregions.org/disclaimer.php','raw_source_not_redistributed':True})
 allbounded=(set(m['shared_seas'])|{n for ns in m['continent_seas'].values() for n in ns}|set(child_rules()))-OPEN_WATERS
 patches=[];audits=[]
 for name,new in corrected.items():
  old=marine[name];union=old.union(new);we,so,ea,no=union.bounds;x0=max(0,int((we+180)/s)-2);x1=min(w,int((ea+180)/s)+3);y0=max(0,int((90-no)/s)-2);y1=min(h,int((90-so)/s)+3);a=np.array([row(y)[x0:x1] for y in range(y0,y1)]);before=a.copy();lon=-180+(np.arange(x0,x1)+.5)*s;lat=90-(np.arange(y0,y1)+.5)*s
  others=[g for n,g in marine.items() if n in allbounded and n!=name and g.intersects(box(we,so,ea,no))];ocean=8 if name=='East China Sea' else 9;count=0
  for start in range(0,len(a),64):
   end=min(start+64,len(a));tf=from_origin(-180+x0*s,90-(y0+start)*s,s,s);shape2=(end-start,len(lon));target=rasterize([(mapping(union),1)],out_shape=shape2,transform=tf,dtype='uint8')>0;bounded=rasterize([(mapping(new),1)]+[(mapping(g),1) for g in others],out_shape=shape2,transform=tf,dtype='uint8')>0;band=a[start:end];rr,cc=np.where(target&(band<16));q=xyz(lon[cc],lat[start+rr]);d,ix=tree.query(q,distance_upper_bound=limit,workers=4);near=np.isfinite(d);desired=np.full(len(rr),ocean,dtype='uint8');desired[bounded[rr,cc]]=2;desired[near]=groups[ix[near]];band[rr,cc]=desired;count+=len(rr)
  assert np.array_equal(a>=16,before>=16);audits.append({'name':name,'water_cells_audited':count,'changed':int(np.count_nonzero(a!=before))});patches.append((x0,y0,a));print(audits[-1],flush=True)
 # Remove the newly introduced equator/130E fallback, using prior verified ocean labels.
 B=json.loads((baseline/'proposal.json').read_text());BR=np.frombuffer(gzip.decompress((baseline/'rows.u32.gz').read_bytes()),'<u4');BV=np.frombuffer(gzip.decompress((baseline/'runs.u32.gz').read_bytes()),'<u4').reshape(-1,2)
 def baseline_row(y):
  z=BV[BR[y]:BR[y+1]];return np.repeat(z[:,1],np.diff(np.r_[0,z[:,0]])).astype('uint8')
 fallback_fixed=0;offsets=[0];chunks=[];total=0;sha=hashlib.sha256();display=hashlib.sha256();base=hashlib.sha256();counts=np.zeros(11,dtype='int64');lon=-180+(np.arange(w)+.5)*s
 for y in range(h):
  old=row(y);a=old.copy();la=90-(y+.5)*s
  for x0,y0,patch in patches:
   if y0<=y<y0+len(patch):a[x0:x0+patch.shape[1]]=patch[y-y0]
  if -3<=la<=3:
   original=baseline_row(y);wrong=(lon>=125)&(lon<=135)&(a==9)&(original==8);fallback_fixed+=int(wrong.sum());a[wrong]=8
  assert np.array_equal(a>=16,old>=16);assert np.array_equal(a[old>=16],old[old>=16]);base.update((old&15).tobytes());display.update(a.tobytes());ids=a&15;sha.update(ids.tobytes());counts+=np.bincount(ids,minlength=11);ends=np.r_[np.flatnonzero(a[:-1]!=a[1:])+1,w].astype('uint32');pairs=np.column_stack((ends,a[ends-1])).astype('<u4');chunks.append(pairs.tobytes());total+=len(ends);offsets.append(total)
 assert base.hexdigest()==m['sha256_uncompressed'];rb=np.array(offsets,dtype='<u4').tobytes();vb=b''.join(chunks)
 for n,data in [('rows',rb),('runs',vb)]:(output/f'{n}.u32.gz').write_bytes(gzip.compress(data,compresslevel=6,mtime=0))
 m.update(proposal_id='continent-20261031-v23',sha256_uncompressed=sha.hexdigest(),display_sha256_uncompressed=display.hexdigest(),water_rule_version='bounded-families-native-coast-12nm-v23');m['local_grid'].update(run_count=total,rows_sha256=hashlib.sha256(rb).hexdigest(),runs_sha256=hashlib.sha256(vb).hexdigest(),decoded_bytes=len(rb)+len(vb),compressed_bytes=sum((output/f'{n}.u32.gz').stat().st_size for n in ['rows','runs']))
 for g in m['groups']:g['cells']=int(counts[g['id']])
 audit={'boundaries':audits,'ocean_fallback_cells_fixed':fallback_fixed,'land_changes':0,'references':refs,'remaining_scope':'Worldwide non-22.224km continental-water boundary audit continues; this is the reported Indian/East Asian correction batch.'};m['verified_sea_boundary_refinement']=audit;(output/'proposal.json').write_text(json.dumps(m,separators=(',',':'))+'\n');(output/'sea-boundary-audit.json').write_text(json.dumps(audit,indent=2)+'\n');print(json.dumps(audit),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('parent',type=Path);p.add_argument('output',type=Path);p.add_argument('source',type=Path);p.add_argument('iho',type=Path);p.add_argument('coasts',type=Path);p.add_argument('baseline',type=Path);v=p.parse_args();build(v.parent,v.output,v.source,v.iho,v.coasts,v.baseline)
