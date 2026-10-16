from pathlib import Path
import json,hashlib,gzip,zipfile,io,subprocess,collections,datetime
import numpy as np
from PIL import Image
B=Path('/workspace/scratch/127991fc8b8e')
W=B/'.worldatlas-workspaces/a7d1c19eff225d01/0f0bb6420b8a7acb9fec7eb313216e39d9b15a0c1f51234aa558b7f5aa812c31/work'
D=W/'.cloud-work/batam-cloud91-wholeitem-001';O=B/'batam91-observation-independent-review'
sha=lambda b:hashlib.sha256(b).hexdigest()
key=lambda r:tuple(r[k] for k in ('owner','y','x'))
def rows(p):
 b=p.read_bytes();b=gzip.decompress(b) if p.suffix=='.gz' else b
 return [json.loads(l) for l in b.splitlines()]
def bykey(rs):
 out={key(r['original_key']):r for r in rs};assert len(rs)==len(out);return out
pins=[]
def pin(p,base=D):
 f=base/p.get('file',p.get('path'));b=f.read_bytes();assert len(b)==p['bytes'] and sha(b)==p['sha256'],str(f);pins.append({'file':str(f.relative_to(D)) if f.is_relative_to(D) else f.name,'bytes':len(b),'sha256':sha(b)});return b
def fpin(name):
 b=(D/name).read_bytes();return {'file':name,'bytes':len(b),'sha256':sha(b)}
expected={'author-proposed91-nextdated-dispositions.jsonl':(3801862,'92cd175798b299c75109addd4484a54dc7f427d373bdf96ea4cff6313a0b1430'),'author-proposed10-owner-y-x.jsonl':(220,'50056ceab2b3775f7911d1594c4b6ede16424cae9d6b8038a36145bebbcd9451'),'actual-observation-custody-verification.json':(38715,'19e3584c5d7517e060336c2c3663bea00b3be8d6fe458566f412f081bc04f7f3')}
for n,(sz,h) in expected.items():pin({'file':n,'bytes':sz,'sha256':h})
acq=json.loads((B/'batam91-independent-review/final-review.json').read_text());plan=json.loads(pin({'file':'next-distinct-native-block-plan91.json',**acq['plan']}));pin({'file':'read_next_distinct_native_blocks.py',**acq['reader']})
item=plan['items'][0];assert len(plan['items'])==1 and len(item['points'])==91
metaplan=json.loads(pin(plan['input_plan']));prior=bykey(rows(D/'original91-prior-held-records.jsonl'));scope=bykey(item['points']);assert len(prior)==len(scope)==91
orig=bykey([json.loads(l)for l in gzip.decompress(pin(plan['original778_inventory'])).splitlines()]);assert len(orig)==778
heldp=metaplan['current_public_held471'];heldb=pin(heldp,W);heldd=gzip.decompress(heldb);assert len(heldd)==heldp['decoded_bytes'] and sha(heldd)==heldp['decoded_sha256'];held={tuple(json.loads(l)) for l in heldd.splitlines()};assert len(held)==471
assert subprocess.run(['git','show',heldp['commit']+':'+heldp['publication_path']],cwd=W,check=True,capture_output=True).stdout==heldb
obsdir=D/'next-distinct-raw-native-observation-001'/item['item_id'];complete=json.loads((obsdir/'item-complete.json').read_text());obs=bykey(rows(obsdir/'point-observations.jsonl'));prop=bykey(rows(D/'author-proposed91-nextdated-dispositions.jsonl'))
assert len(complete['products'])==126 and complete['point_count']==91 and complete['asset_block_count']==60
for p in complete['products']:pin(p)
assert set(obs)==set(prop)==set(prior)==set(scope) and set(obs)<=held and set(obs)<=set(orig)
custody=json.loads((D/'actual-observation-custody-verification.json').read_text());assert custody['whole_item_product_bodies']==126
arrays={};encoded=decoded=npybytes=members=0
for p in custody['native_arrays']:
 data=pin(p);encoded+=len(data);q=Path(p['path']);band=q.parent.name;meta=json.loads(q.with_suffix('.json').read_text()) if q.is_absolute() else json.loads((D/q.with_suffix('.json')).read_text())
 with zipfile.ZipFile(io.BytesIO(data)) as z:
  assert len(z.namelist())==2 and set(z.namelist())=={'values.npy','mask.npy'}
  for m in p['decoded_members']:
   b=z.read(m['path']);assert len(b)==m['bytes'] and sha(b)==m['sha256'];npybytes+=len(b);members+=1
 with np.load(io.BytesIO(data),allow_pickle=False) as z:v=z['values'];m=z['mask']
 h=item['assets'][band]['actual_header'];l,t,w,hh=meta['native_window'];assert v.shape==m.shape==(hh,w) and v.dtype==np.dtype(h['dtypes'][0]) and m.dtype==np.uint8;assert set(np.unique(m))<={0,255};decoded+=v.nbytes+m.nbytes
 assert meta['source_header']==h and meta['source_url']==item['assets'][band]['source_url'] and meta['source_object_identity']==item['assets'][band]['HEAD_identity']
 arrays.setdefault(band,[]).append((l,t,w,hh,v,m))
assert len(custody['native_arrays'])==60 and members==120 and encoded==15589106 and decoded==157286400 and npybytes==157301760
assert custody['encoded_npz_bytes']==encoded and custody['decoded_values_and_masks_bytes']==decoded and custody['decoded_npy_members_including_headers_bytes']==npybytes

def crop(band,window):
 l,t,w,h=window;vals=np.zeros((h,w),dtype=item['assets'][band]['actual_header']['dtypes'][0]);mask=np.zeros((h,w),np.uint8);covered=np.zeros((h,w),bool)
 for al,at,aw,ah,v,m in arrays[band]:
  x0=max(l,al);x1=min(l+w,al+aw);y0=max(t,at);y1=min(t+h,at+ah)
  if x0>=x1 or y0>=y1:continue
  ys=slice(y0-t,y1-t);xs=slice(x0-l,x1-l);assert not covered[ys,xs].any();covered[ys,xs]=True;vals[ys,xs]=v[y0-at:y1-at,x0-al:x1-al];mask[ys,xs]=m[y0-at:y1-at,x0-al:x1-al]
 H=item['assets'][band]['actual_header']['height'];W=item['assets'][band]['actual_header']['width'];rs=np.arange(t,t+h)[:,None];cs=np.arange(l,l+w)[None,:];inside=(rs>=0)&(rs<H)&(cs>=0)&(cs<W);assert np.all(covered[inside]);assert not covered[~inside].any();assert not mask[~inside].any()
 return vals,mask
inv=json.loads((D/'native-rawDN-context-pages/contact-inventory.json').read_text());panels={p['point_index']:p for pg in inv['pages'] for p in pg['panels']};assert len(panels)==91
palette=np.array([[0,0,0],[255,0,0],[70,70,70],[90,55,25],[0,160,0],[230,190,70],[0,80,230],[140,140,140],[185,185,185],[255,255,255],[100,220,255],[255,160,220]],np.uint8)
def enlarge(patch,size,cy,cx,gap):
 h,w,_=patch.shape;ri=np.arange(size)*h//size;ci=np.arange(size)*w//size;im=patch[ri[:,None],ci[None,:]].copy();y=int(cy/h*size);x=int(cx/w*size)
 for d in (-gap-1,-gap,gap,gap+1):
  if 0<=y+d<size and 0<=x<size:im[y+d,x]=[255,255,0]
  if 0<=y<size and 0<=x+d<size:im[y,x+d]=[255,255,0]
 return im
valid=[];nodata=[];edges=[];pos=0;rgbwides={};detail_count=0
for k,o in obs.items():
 pp=prop[k];sp=scope[k];assert pp['prior_complete778_stage_record_unchanged']==prior[k] and pp['new_actual_saved_observation_unchanged']==o
 assert o['centre_unchanged']==sp['centre_unchanged']==orig[k]['centre_unchanged'];assert o['point_index']==sp['point_index']==pp['original_point_index'];assert o['item_id']==item['item_id'] and o['acquisition_datetime']==item['acquisition_datetime'];assert o['planned_native_context']==sp['per_asset_native_plan']
 for band,a in o['assets'].items():
  pos+=1;assert a['native_context_window_plan']==sp['per_asset_native_plan'][band];r,c=a['native_containing_pixel'];v,m=crop(band,[c-1,r-1,3,3]);assert v.tolist()==a['actual_raw3x3'] and m.tolist()==a['actual_mask3x3'];assert int(v[1,1])==a['raw_value'] and int(m[1,1])==a['native_valid_mask'];assert a['actual_header']==item['assets'][band]['actual_header'];pin(a['containing_array'])
 idx=o['point_index'];validity=[o['assets'][b]['native_valid_mask'] for b in ('red','green','blue','nir')];assert len(set(validity))==1
 (valid if validity[0] else nodata).append(idx)
 raw=[];masks=[]
 for band in ('red','green','blue','nir'):
  v,m=crop(band,o['assets'][band]['native_context_window_plan']['requested_context_window']);raw.append(v);masks.append(m)
 raw=np.stack(raw);masks=np.stack(masks);a=o['assets']['red'];l,t,w,h=a['native_context_window_plan']['requested_context_window'];cy,cx=a['native_fractional_pixel'][0]-t,a['native_fractional_pixel'][1]-l
 if not a['native_context_window_plan']['context_complete_within_source_frame']:edges.append(idx)
 p=panels[idx];assert p['original_key']==o['original_key'] and p['raw_RGBNIR']==[o['assets'][b]['raw_value']for b in ('red','green','blue','nir')] and p['raw_masks']==validity and p['fractional_centre_in_crop']==[cy,cx]
 wide=[];detail=[]
 for bands,hi in [([0,1,2],3000),([3,0,1],5000)]:
  patch=(np.clip(raw[bands].transpose(1,2,0).astype(float)/hi*255,0,255)).astype(np.uint8);patch[np.any(masks==0,axis=0)]=[255,0,255];wide.append(enlarge(patch,192,cy,cx,4));detail.append(enlarge(patch[16:33,16:33],256,cy-16,cx-16,5))
 a=o['assets']['scl'];l,t,w,h=a['native_context_window_plan']['requested_context_window'];v,m=crop('scl',[l,t,w,h]);patch=palette[v];patch[m==0]=[255,0,255];detail.append(enlarge(patch,256,a['native_fractional_pixel'][0]-t,a['native_fractional_pixel'][1]-l,5))
 expected_image=np.concatenate(detail,axis=1);actual_image=np.asarray(Image.open(D/f'native-rawDN-context-pages/point-{idx}-native17-RGB-FCC-SCL25.png'));assert np.array_equal(actual_image,expected_image),idx;detail_count+=1;rgbwides[idx]=np.concatenate(wide,axis=1)
 for vw in pp['actual_views'].values():
  if isinstance(vw,dict) and 'file'in vw:pin(vw)
 assert pp['author_proposed_disposition']['all_original_independent_source_owner_parent_portion_territorial_holds_retained'] and pp['author_proposed_disposition']['adopted_or_native_credit']==0
for pg in inv['pages']:
 pin(pg);actual=np.asarray(Image.open(D/pg['file']));expected_image=np.full((1176,1536,3),255,np.uint8)
 for p in pg['panels']:
  n=p['panel_1based']-1;expected_image[(n//4)*196:(n//4)*196+192,(n%4)*384:(n%4)*384+384]=rgbwides[p['point_index']]
 assert np.array_equal(actual,expected_image)
assert pos==455 and len(valid)==18 and len(nodata)==73 and sorted(edges)==[15862,15863]
accepted=[tuple(json.loads(l)) for l in (D/'author-proposed10-owner-y-x.jsonl').read_text().splitlines()];assert len(set(accepted))==len(accepted)==10
assert set(accepted)=={k for k,p in prop.items() if p['author_proposed_disposition']['answer'] is not None};assert all(obs[k]['point_index']in valid for k in accepted)
# Execute the reviewed renderer's SCL padding section with synthetic nonzero native arrays at both true edges.
renderer=(D/'render_saved_next91_rawDN.py').read_text();start=renderer.index(" a=p['assets']['scl'];lefts");end=renderer.index(' detail_images.append(im);detail=',start)
snippet='\n'.join(line[1:] if line.startswith(' ') else line for line in renderer[start:end].splitlines());controls=[]
for idx in edges:
 p=next(o for o in obs.values() if o['point_index']==idx);a=dict(p['assets']['scl']);r,c=a['native_containing_pixel'];a['raw_value']=4;a['native_valid_mask']=255;p={**p,'assets':{**p['assets'],'scl':a}}
 synthetic={}
 for l,t,w,h,v,m in arrays['scl']:synthetic[(t//512,l//512)]=(np.full((h,w),4,np.uint8),np.full((h,w),255,np.uint8),[l,t,w,h])
 env={'p':p,'item':item,'arrays':{'scl':synthetic},'np':np};exec(snippet,env)
 assert np.all(env['sm'][:9]==0) and np.all(env['sv'][:9]==0) and np.all(env['sm'][9:]==255) and np.all(env['sv'][9:]==4)
 assert np.all(env['im'][:92]==[255,0,255]);assert int(env['sv'][r+9,c-a['native_context_window_plan']['requested_context_window'][0]])==4
 controls.append({'point_index':idx,'absent_top_rows':9,'available_rows':16,'absent_mask_zero':True,'available_data_unchanged':True,'magenta_absence':True,'fractional_marker_unchanged':True})
result={'status':'PASS_SAVED_CUSTODY_SCOPE_AND_RENDERING','reviewer':'review_batam91_observations','reviewed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':91,'whole_item_product_bodies':126,'native_npz_arrays':60,'decoded_members':members,'encoded_npz_bytes':encoded,'decoded_values_masks_bytes':decoded,'decoded_npy_members_with_headers_bytes':npybytes,'point_asset_positions_and_raw3x3_joins':pos,'prior_records_preserved':91,'current_held471_exact_keys':91,'current_held_commit':heldp['commit'],'valid_centres':valid,'nodata_centres':nodata,'incomplete_frame_edges':edges,'detail_images_pixel_equal_to_independent_renderer':detail_count,'contact_pages_pixel_equal_to_independent_renderer':4,'synthetic_renderer_controls':controls,'proposal_literal_keys_exact':10,'source_replay_calls':0,'scope_note':'Local saved bytes and pixels only. No whole remote TIFF authentication claim. No reflectance normalization, indices, native authority, whole-cell ground truth or adoption credit.'}
(O/'verification.json').write_text(json.dumps(result,indent=2)+'\n');(O/'verified-pins.json').write_text(json.dumps(list({p['file']:p for p in pins}.values()),indent=2)+'\n');print(json.dumps(result,indent=2))
