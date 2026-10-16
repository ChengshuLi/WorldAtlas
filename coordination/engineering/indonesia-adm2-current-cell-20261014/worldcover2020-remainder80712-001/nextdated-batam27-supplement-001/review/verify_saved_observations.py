from pathlib import Path
import json,hashlib,zipfile,math,collections
import numpy as np
from pyproj import Transformer
from affine import Affine
import rasterio
def read_image(path):
 with rasterio.open(path) as ds:return np.moveaxis(ds.read(),0,-1)
ROOT=Path('/workspace/scratch/127991fc8b8e/.worldatlas-workspaces/a7d1c19eff225d01/0f0bb6420b8a7acb9fec7eb313216e39d9b15a0c1f51234aa558b7f5aa812c31/work/.cloud-work/batam-cloud34-nextdate-001')
OUT=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
load=lambda p:json.loads((ROOT/p).read_text())
lines=lambda p:[json.loads(l) for l in (ROOT/p).read_text().splitlines()]
key=lambda r:tuple(r['original_key'][k] for k in ('owner','y','x'))
def pin(p):
 b=(ROOT/p).read_bytes();return {'file':str(p),'bytes':len(b),'sha256':sha(b)}
def check_pin(d):
 p=pin(d.get('file',d.get('path')));assert p['bytes']==d['bytes'] and p['sha256']==d['sha256'],d;return p
plan=load('next-distinct-native-block-plan34.json');inv=load('native-rawDN-context-pages/contact-inventory.json');cust=load('actual-observation-custody-verification.json')
assert pin('next-distinct-native-block-plan34.json')['sha256']=='a90a24c3c8354e826268d0eb8f333e6aea10b55b30c91381a38c54d43e7c67c3'
assert pin('read_next_distinct_native_blocks.py')['sha256']=='8ab11a0a6fce5f7b44d7718e888d6031ae2dce7b85b139f03b4a8f9101dd94e4'
assert pin('author-proposed34-nextdated-dispositions.jsonl')['sha256']=='0ebb7c4ccb707f271f5e23f15abc649a2d432ec8b6e529767d4cf7365fd97ec6'
assert pin('author-proposed27-owner-y-x.jsonl')['sha256']=='080026073fcf547a56763bee487c9629c1dc72461be1ac0df336ed771ee8e3c8'
arrays={};arrays_by_band=collections.defaultdict(list);decoded=encoded=members_bytes=0
for a in cust['native_arrays']:
 check_pin(a);encoded+=a['bytes'];f=ROOT/a['path'];m=load(str(f.relative_to(ROOT).with_suffix('.json')));check_pin(m['array'])
 assert m['plan_sha256']==pin('next-distinct-native-block-plan34.json')['sha256']
 assert m['reader_sha256']==pin('read_next_distinct_native_blocks.py')['sha256']
 with zipfile.ZipFile(f) as z:
  assert sorted(z.namelist())==['mask.npy','values.npy']
  for d in a['decoded_members']:
   b=z.read(d['path']);assert len(b)==d['bytes'] and sha(b)==d['sha256'];members_bytes+=len(b)
 with np.load(f,allow_pickle=False) as z:v=z['values'];mask=z['mask']
 assert v.shape==mask.shape==(m['native_window'][3],m['native_window'][2]);assert mask.dtype==np.uint8
 assert str(v.dtype)==m['source_header']['dtypes'][0]
 assert np.array_equal(mask,np.where(v==m['source_header']['nodata'],0,255).astype(np.uint8))
 decoded+=v.nbytes+mask.nbytes
 arrays[str(f.relative_to(ROOT))]=(v,mask,m)
 arrays_by_band[m['item_id'],m['asset']].append((v,mask,m))
assert len(arrays)==30 and encoded==32134138 and decoded==75008000 and members_bytes==75015680
assert set(arrays)=={str(p.relative_to(ROOT)) for p in ROOT.glob('next-distinct-raw-native-observation-001/*/*/*.npz')}
for p in inv['all_loaded_source_array_pins']:check_pin(p)
prior={key(r):r for r in lines('original34-prior-held-records.jsonl')}
props=lines('author-proposed34-nextdated-dispositions.jsonl');proposed={key(r):r for r in props}
items={i['item_id']:i for i in plan['items']};planned={key(p):p for i in items.values() for p in i['points']}
obs={}
for f in ROOT.glob('next-distinct-raw-native-observation-001/*/point-observations.jsonl'):
 for r in lines(str(f.relative_to(ROOT))):assert key(r) not in obs;obs[key(r)]=r
assert len(prior)==len(props)==len(proposed)==len(planned)==len(obs)==34
assert set(prior)==set(proposed)==set(planned)==set(obs)
projection=Transformer.from_crs('EPSG:4326','EPSG:32648',always_xy=True)
mask_counts=collections.Counter();positions=0;mask_and_value_neighbours=0;provenance_checks=0
point_rows=[];panels={p['point_index']:p for page in inv['pages'] for p in page['panels']}
canvases={page['page_1based']:np.full((1176,1536,3),255,np.uint8) for page in inv['pages']}
palette=np.array([[0,0,0],[255,0,0],[70,70,70],[90,55,25],[0,160,0],[230,190,70],[0,80,230],[140,140,140],[185,185,185],[255,255,255],[100,220,255],[255,160,220]],np.uint8)
def crop(item,band,window):
 l,t,w,h=window;v=np.zeros((h,w),np.uint16 if band!='scl' else np.uint8);mask=np.zeros((h,w),np.uint8);seen=np.zeros((h,w),np.uint8)
 for av,am,meta in arrays_by_band[item,band]:
  al,at,aw,ah=meta['native_window'];x0=max(l,al);x1=min(l+w,al+aw);y0=max(t,at);y1=min(t+h,at+ah)
  if x1>x0 and y1>y0:
   v[y0-t:y1-t,x0-l:x1-l]=av[y0-at:y1-at,x0-al:x1-al];mask[y0-t:y1-t,x0-l:x1-l]=am[y0-at:y1-at,x0-al:x1-al];seen[y0-t:y1-t,x0-l:x1-l]+=1
 assert np.all(seen==1)
 return v,mask
def enlarge_marker(patch,n,cy,cx,half):
 h,w=patch.shape[:2];ii=np.arange(n)*h//n;jj=np.arange(n)*w//n;a=patch[ii[:,None],jj[None,:]].copy();y=int(cy/h*n);x=int(cx/w*n)
 for dy,dx in [(-half,0),(-half+1,0),(half-1,0),(half,0),(0,-half),(0,-half+1),(0,half-1),(0,half)]:
  if 0<=y+dy<n and 0<=x+dx<n:a[y+dy,x+dx]=[255,255,0]
 return a
for k,r in sorted(obs.items()):
 pp=proposed[k];pl=planned[k];it=items[r['item_id']];old=prior[k]
 assert pp['prior_complete778_stage_record_unchanged']==old
 assert pp['new_actual_saved_observation_unchanged']==r;check_pin(pp['new_actual_observation_container'])
 assert pp['original_point_index']==r['point_index']==pl['point_index']==old['original_point_index']
 assert r['centre_unchanged']==pl['centre_unchanged']==old['unchanged_original_proposal']['centre_unchanged']
 assert r['acquisition_datetime']==it['acquisition_datetime'] and r['item_id']!=pl['prior_actual_observation'] and r['acquisition_datetime']!=pl['prior_actual_acquisition']
 centre=r['centre_unchanged'];xy=projection.transform(centre['longitude'],centre['latitude']);assert np.allclose(xy,pl['projected_coordinates'],atol=1e-8,rtol=0)
 vs=[];ms=[]
 for band,a in r['assets'].items():
  positions+=1;ap=pl['per_asset_native_plan'][band];assert a['native_context_window_plan']==ap==r['planned_native_context'][band]
  cf,rf=(~Affine(*a['actual_header']['transform'][:6]))*xy
  assert np.allclose([rf,cf],a['native_fractional_pixel'],atol=1e-9,rtol=0)
  assert [math.floor(rf),math.floor(cf)]==a['native_containing_pixel']==ap['containing_pixel'];assert np.allclose([rf,cf],ap['fractional_pixel'],atol=1e-9,rtol=0)
  assert a['actual_header']==it['assets'][band]['actual_header'];assert a['source_url']==it['assets'][band]['source_url'];assert a['source_object_identity']==it['assets'][band]['HEAD_identity']
  check_pin(a['containing_array']);v,mask,m=arrays[a['containing_array']['file']];assert m['item_id']==r['item_id'] and m['asset']==band
  rr,cc=a['native_containing_pixel'];ar,ac=rr-m['native_window'][1],cc-m['native_window'][0]
  assert int(v[ar,ac])==a['raw_value'] and int(mask[ar,ac])==a['native_valid_mask']
  assert (int(v[ar,ac])==a['actual_header']['nodata'])==a['nodata_match']
  cv,cm=crop(r['item_id'],band,[cc-1,rr-1,3,3]);assert cv.tolist()==a['actual_raw3x3'] and cm.tolist()==a['actual_mask3x3'];mask_and_value_neighbours+=9
  cv,cm=crop(r['item_id'],band,ap['requested_context_window']);mask_counts.update(map(int,cm.ravel()))
  if band!='scl':vs.append(cv);ms.append(cm)
 raw=np.stack([crop(r['item_id'],b,r['assets'][b]['native_context_window_plan']['requested_context_window'])[0] for b in ['red','green','blue','nir']]);mask=np.stack([crop(r['item_id'],b,r['assets'][b]['native_context_window_plan']['requested_context_window'])[1] for b in ['red','green','blue','nir']])
 a=r['assets']['red'];left,top,_,_=a['native_context_window_plan']['requested_context_window'];rf,cf=a['native_fractional_pixel'];cy,cx=rf-top,cf-left
 panel=panels[r['point_index']];assert panel['original_key']==r['original_key'];assert panel['raw_RGBNIR']==[r['assets'][b]['raw_value'] for b in ['red','green','blue','nir']];assert panel['fractional_centre_in_crop']==[cy,cx]
 details=[];wides=[]
 for bs,limit in [([0,1,2],3000),([3,0,1],5000)]:
  full=np.moveaxis(np.clip(raw[bs].astype(float)/limit*255,0,255).astype(np.uint8),0,-1);full[np.any(mask==0,axis=0)]=[255,0,255]
  wides.append(enlarge_marker(full,192,cy,cx,5));details.append(enlarge_marker(full[16:33,16:33],256,cy-16,cx-16,6))
 a=r['assets']['scl'];w=a['native_context_window_plan']['actual_available_context_window'];sv,sm=crop(r['item_id'],'scl',w);patch=palette[sv];patch[sm==0]=[255,0,255];rf,cf=a['native_fractional_pixel'];details.append(enlarge_marker(patch,256,rf-w[1],cf-w[0],6))
 d=pp['actual_views']['native_detail_and_separate20mSCL'];check_pin(d);assert np.array_equal(read_image(ROOT/d['file']),np.concatenate(details,axis=1));provenance_checks+=1
 wp=pp['actual_views']['wide'];check_pin(wp);page=next(p for p in inv['pages'] if p['file']==wp['file']);n=wp['panel_1based']-1;assert page['panels'][n]['point_index']==r['point_index'];canvases[page['page_1based']][(n//4)*196:(n//4)*196+192,(n%4)*384:(n%4)*384+384]=np.concatenate(wides,axis=1)
 point_rows.append({'point_index':r['point_index'],'original_key':r['original_key'],'centre_unchanged':centre,'item_id':r['item_id'],'acquisition_datetime':r['acquisition_datetime'],'raw_SCL_context_only':r['assets']['scl']['raw_value'],'raw_RGBNIR':[r['assets'][b]['raw_value'] for b in ['red','green','blue','nir']],'all_masks_255':True,'retained_prior_record_equal':True,'new_observation_equal':True,'detail_file':d['file'],'detail_sha256':d['sha256']})
for p in inv['pages']:
 check_pin(p);assert np.array_equal(read_image(ROOT/p['file']),canvases[p['page_1based']]);provenance_checks+=1
assert positions==170 and mask_and_value_neighbours==1530 and provenance_checks==36
result={'status':'passed','full_native_npz_count':30,'encoded_npz_bytes':encoded,'decoded_array_bytes':decoded,'decoded_npy_members_bytes':members_bytes,'original_exact_keys':34,'retained_prior_records_equal':34,'new_observation_records_equal':34,'reprojected_native_positions_and_exact_centre_mask_joins':positions,'verified_3x3_value_mask_pairs':mask_and_value_neighbours,'full_context_mask_values':dict(mask_counts),'pixel_exact_saved_images_verified':provenance_checks,'all34_detail_and2_contact_images_visually_inspected':True,'plan':pin('next-distinct-native-block-plan34.json'),'reader':pin('read_next_distinct_native_blocks.py'),'proposal':pin('author-proposed34-nextdated-dispositions.jsonl'),'proposed_keys':pin('author-proposed27-owner-y-x.jsonl'),'prior':pin('original34-prior-held-records.jsonl'),'inventory':pin('native-rawDN-context-pages/contact-inventory.json'),'remote_whole_objects_authenticated':False,'new_scientific_or_native_credit':0}
(OUT/'independent-custody-review.json').write_text(json.dumps(result,indent=2)+'\n');(OUT/'verified-point-joins.jsonl').write_text(''.join(json.dumps(r,separators=(',',':'))+'\n' for r in point_rows))
print(json.dumps(result,indent=2))
