"""Rebuild shared archipelagic waters from reviewed whole-island memberships."""
import argparse,gzip,hashlib,json
from pathlib import Path
import numpy as np,shapefile
from scipy.ndimage import binary_erosion,label,find_objects
from scipy.spatial import cKDTree
from rasterio.features import rasterize
from rasterio.transform import from_origin
from shapely.geometry import shape,mapping
from correct_suez import xyz

def build(parent,output,reference,source,scope_bounds=(120,-14.5,158,35.5)):
 output.mkdir(parents=True,exist_ok=True);m=json.loads((parent/'proposal.json').read_text());s=m['step'];w=m['width'];h=m['height'];rows=np.frombuffer(gzip.decompress((parent/'rows.u32.gz').read_bytes()),'<u4');runs=np.frombuffer(gzip.decompress((parent/'runs.u32.gz').read_bytes()),'<u4').reshape(-1,2)
 def decode(y,x0=0,x1=w):
  r=runs[rows[y]:rows[y+1]];return r[np.searchsorted(r[:,0],np.arange(x0,x1),side='right'),1].astype('uint8')
 # Generous coast-search padding: no changed cell is near the search crop edge.
 x0,x1=int(290/s),int(345/s);y0,y1=int(54/s),int(110/s);a=np.array([decode(y,x0,x1) for y in range(y0,y1)]);old=a.copy();lo=-180+(np.arange(x0,x1)+.5)*s;la=90-(np.arange(y0,y1)+.5)*s
 ref=json.loads(reference.read_text());land_audit=[]
 print('native region decoded',a.shape,flush=True)
 for entry in ref['land_groups']:
  west,south,east,north=entry['bounds'];xx=np.where((lo>=west)&(lo<=east))[0];yy=np.where((la>=south)&(la<=north))[0];sub=a[yy[0]:yy[-1]+1,xx[0]:xx[-1]+1];land=sub>=16
  boundary=np.r_[sub[0],sub[-1],sub[:,0],sub[:,-1]];assert np.all(boundary[boundary>=16]==16+entry['group']),entry['name']
  nchanged=int(np.count_nonzero(land&(sub!=(16+entry['group']))));before={str(int(k)):int(v) for k,v in zip(*np.unique(sub[land],return_counts=True))};sub[land]=16+entry['group'];land_audit.append(dict(entry,land_cells=int(land.sum()),changed=nchanged,previous_values=before))
 print('land assignments',land_audit,flush=True)
 edge=(a>=16)&~binary_erosion(a>=16);edge[[0,-1]]=False;edge[:,[0,-1]]=False;rr,cc=np.where(edge);coastgroups=a[rr,cc]&15;coastxyz=xyz(lo[cc],la[rr]);tree=cKDTree(coastxyz);trees={g:cKDTree(coastxyz[coastgroups==g]) for g in (2,6)}
 del edge,rr,cc
 # Stream source masks in small bands; do not retain full-region mask copies.
 names={'Banda Sea','Arafura Sea','Timor Sea','Molucca Sea','Ceram Sea','Halmahera Sea','Selat Dampier','Gulf of Buli','Gulf of Kau','Savu Sea','Flores Sea','Celebes Sea','Makassar Strait'}
 replacements={f['properties']['name']:f['geometry'] for f in ref['features']};originals=[];geoms=[];philippine=[]
 for sr in shapefile.Reader(str(source/'ne_10m_geography_marine_polys/ne_10m_geography_marine_polys.shp')).iterShapeRecords():
  n=sr.record.as_dict()['name'];g=sr.shape.__geo_interface__;b=sr.shape.bbox
  if n in names or n=='Philippine Sea':originals.append((g,b))
  if n in names:geoms.append((replacements.get(n,g),b))
  if n=='Philippine Sea':philippine.append((g,b))
 limit=2*np.sin(22.224/(2*6371.0088));auditcount=0;mismatches=0;changes=0;transitions={};phi_count=0
 def mask(items,start,end):
  shapes=[(g,1) for g,b in items if b[3]>=la[end-1]-.2 and b[1]<=la[start]+.2]
  return rasterize(shapes,out_shape=(end-start,len(lo)),transform=from_origin(-180+x0*s,90-(y0+start)*s,s,s),dtype='uint8')>0 if shapes else np.zeros((end-start,len(lo)),dtype=bool)
 for start in range(0,len(a),64):
  if start%1024==0:print('water rows',start,'/',len(a),flush=True)
  end=min(start+64,len(a));band=a[start:end];original=old[start:end]
  protected=mask(geoms,start,end);oldprotected=mask(originals,start,end);phi=mask(philippine,start,end)
  retained=(original<7)&~oldprotected;bounded=protected|retained
  west,south,east,north=scope_bounds
  scope=(lo[None,:]>=west)&(lo[None,:]<=east)&(la[start:end,None]>=south)&(la[start:end,None]<=north)
  nearby=np.zeros(band.shape,dtype=bool)
  for e in ref['land_groups']:
   we,so,ea,no=e['bounds'];nearby|=(lo[None,:]>=we-.3)&(lo[None,:]<=ea+.3)&(la[start:end,None]>=so-.3)&(la[start:end,None]<=no+.3)
  target=(band<16)&scope&(protected|oldprotected|nearby|retained)
  rr,cc=np.where(target)
  if not len(rr):continue
  q=xyz(lo[cc],la[start+rr]);bound=bounded[rr,cc];phi_count+=int(np.count_nonzero(phi[rr,cc]))
  new=np.where((la[start+rr]<0)&(lo[cc]<130),9,8).astype('uint8')
  expected=new.copy()
  for is_bound in (False,True):
   sel=bound==is_bound
   if not sel.any():continue
   cap=np.inf if is_bound else limit;d,ix=tree.query(q[sel],distance_upper_bound=cap,workers=4);hit=np.isfinite(d);dest=np.where(sel)[0][hit];new[dest]=coastgroups[ix[hit]]
   ds=np.stack([trees[g].query(q[sel],distance_upper_bound=cap,workers=4)[0] for g in (2,6)]);hit2=np.isfinite(ds.min(axis=0));dest2=np.where(sel)[0][hit2];expected[dest2]=np.array([2,6],dtype='uint8')[ds[:,hit2].argmin(axis=0)]
  mismatches+=int(np.count_nonzero(new!=expected));previous=band[rr,cc];changed=previous!=new;changes+=int(changed.sum());auditcount+=len(rr)
  for z,t in zip(*np.unique(previous[changed].astype('int32')*32+new[changed],return_counts=True)):
   key=f'{int(z)//32}->{int(z)%32}';transitions[key]=transitions.get(key,0)+int(t)
  band[rr,cc]=new
  assert np.array_equal(band>=16,original>=16)
  assert np.all(np.isin(band[protected&(band<16)],(2,6)))
 assert mismatches==0
 assert not np.any(a[0]!=old[0]) and not np.any(a[-1]!=old[-1]) and not np.any(a[:,0]!=old[:,0]) and not np.any(a[:,-1]!=old[:,-1])
 audit={'land_groups':land_audit,'philippine_open_water_cells_audited':phi_count,'water_cells_audited':auditcount,'water_cells_changed':changes,'water_transitions':transitions,'independent_rule_mismatches':mismatches,'land_mask_changes':0,'reference_sha256':hashlib.sha256(reference.read_bytes()).hexdigest(),'shared_seas':sorted(names),'buffer_km':22.224,'method':'Whole named island groups, then one nearest-represented-coast partition for all selected shared seas. Philippine Sea uses the ordinary open-Pacific/coastal-buffer rule; Timor western entrance uses published headlands. Source coastlines and ordinary cell-center sampling remain unchanged.'}
 np.savez_compressed(output/'regional-preview.npz',old=old[::8,::8],new=a[::8,::8],bounds=[lo[0],lo[-1],la[-1],la[0]])
 offsets=[0];chunks=[];total=0;counts=np.zeros(11,dtype='int64');sha=hashlib.sha256();display=hashlib.sha256();base=hashlib.sha256()
 for y in range(h):
  row=decode(y);base.update((row&15).tobytes())
  if y0<=y<y1:row[x0:x1]=a[y-y0]
  display.update(row.tobytes());ids=row&15;sha.update(ids.tobytes());counts+=np.bincount(ids,minlength=11);ends=np.r_[np.flatnonzero(row[:-1]!=row[1:])+1,w].astype('uint32');pairs=np.column_stack((ends,row[ends-1])).astype('<u4');chunks.append(pairs.tobytes());total+=len(ends);offsets.append(total)
 assert base.hexdigest()==m['sha256_uncompressed'];rb=np.array(offsets,dtype='<u4').tobytes();vb=b''.join(chunks)
 for n,raw in [('rows',rb),('runs',vb)]:(output/f'{n}.u32.gz').write_bytes(gzip.compress(raw,compresslevel=6,mtime=0))
 m.update(proposal_id='continent-20261031-v22',sha256_uncompressed=sha.hexdigest(),display_sha256_uncompressed=display.hexdigest());m['local_grid'].update(run_count=total,rows_sha256=hashlib.sha256(rb).hexdigest(),runs_sha256=hashlib.sha256(vb).hexdigest(),decoded_bytes=len(rb)+len(vb),compressed_bytes=sum((output/f'{n}.u32.gz').stat().st_size for n in ['rows','runs']))
 for g in m['groups']:g['cells']=int(counts[g['id']])
 if 'asia_oceania_refinement' in m:m.setdefault('asia_oceania_refinement_history',[]).append(m['asia_oceania_refinement'])
 m['asia_oceania_refinement']=audit;m['water_rule_version']='bounded-families-native-coast-12nm-v22'
 for group in list(m['continent_seas']):m['continent_seas'][group]=[n for n in m['continent_seas'][group] if n not in names and n!='Philippine Sea']
 m['shared_seas']=sorted((set(m['shared_seas'])|names)-{'Philippine Sea'})
 m['ordinary_open_seas']=sorted(set(m.get('ordinary_open_seas',[]))|{'Philippine Sea'})
 (output/'proposal.json').write_text(json.dumps(m,separators=(',',':'))+'\n');(output/'asia-oceania-audit.json').write_text(json.dumps(audit,indent=2)+'\n');(output/'asia-oceania-reference.geojson').write_bytes(reference.read_bytes());print(json.dumps(audit),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('parent',type=Path);p.add_argument('output',type=Path);p.add_argument('reference',type=Path);p.add_argument('source',type=Path);p.add_argument('--scope',nargs=4,type=float,default=(120,-14.5,158,35.5));v=p.parse_args();build(v.parent,v.output,v.reference,v.source,v.scope)
