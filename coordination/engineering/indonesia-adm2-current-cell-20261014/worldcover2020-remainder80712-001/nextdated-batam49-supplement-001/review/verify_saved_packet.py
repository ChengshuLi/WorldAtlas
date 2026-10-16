"""Read-only, offline verification of the January 6 Batam81 saved evidence."""
from pathlib import Path
import hashlib, json, gzip, zipfile, collections, datetime
import numpy as np
from PIL import Image

ROOT=Path('/workspace/scratch/127991fc8b8e/worldatlas-indonesia-cloud-proof-20261016/batam-january6-81-complete-author-review-001')
OUT=Path(__file__).resolve().parent
ACC=Path('/workspace/scratch/127991fc8b8e/worldatlas-indonesia-cloud-proof-20261016/author-continuation-preserved-0644/.cloud-work/physical-batam10-packet-001/accounting')
def sha(b): return hashlib.sha256(b).hexdigest()
def pin(p):
 b=p.read_bytes();return {'file':str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else p.name,'bytes':len(b),'sha256':sha(b)}
def check(p,claim):
 b=p.read_bytes(); assert len(b)==claim['bytes'] and sha(b)==claim['sha256'],str(p)
 if 'git_blob_oid' in claim: assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==claim['git_blob_oid']
 return b
def rows(p): return [json.loads(x) for x in (gzip.open(p,'rt') if p.suffix=='.gz' else p.open())]
def key(r):
 d=r.get('original_key',r) if isinstance(r,dict) else r
 return tuple(d[k] for k in ('owner','y','x')) if isinstance(d,dict) else tuple(d)
def dates(o):
 if isinstance(o,dict):
  return ([o['acquisition_datetime'][:10]] if 'acquisition_datetime' in o else []) + [s for v in o.values() for s in dates(v)]
 if isinstance(o,list): return [s for v in o for s in dates(v)]
 return []
manifest=[pin(p) for p in sorted(ROOT.rglob('*')) if p.is_file()]
assert len(manifest)==279 and sum(p['bytes']for p in manifest)==88759996
plan=json.loads((ROOT/'next-distinct-native-block-plan81.json').read_text())
assert pin(ROOT/'next-distinct-native-block-plan81.json')['sha256']=='e4507671448b253aefe5e3b6277d9720e124722c69b82eaf5e99689ebd049254'
assert pin(ROOT/'read_next_distinct_native_blocks.py')['sha256']=='959a9355f3e137a6b14e6f8d2a4a907c587411b49a2e593ebbb72ddf48e43564'
assert pin(ROOT/'author-proposed81-nextdated-dispositions.jsonl')['sha256']=='90c5719cafc9ba938464e4ab9f42747ed663f6e0ea917324734bc4d7fc97e76f'
assert pin(ROOT/'author-proposed52-owner-y-x.jsonl')['sha256']=='d89f9d5ef953cfbb795a66b644fe93511959a6b9996fb89d988baa7f90c5f78a'
status=json.loads((ROOT/'next-distinct-raw-native-observation-001/execution-status.json').read_text())
custody=json.loads((ROOT/'actual-observation-custody-verification.json').read_text())
items={i['item_id']:i for i in plan['items']}
planned_points={p['point_index']:p for i in plan['items']for p in i['points']}
product_paths=set()
obs=[]
for c in status['complete_items']:
 assert c==json.loads((ROOT/'next-distinct-raw-native-observation-001'/c['item_id']/'item-complete.json').read_text())
 for p in c['products']:check(ROOT/p['file'],p);product_paths.add(p['file'])
 obs+=rows(ROOT/'next-distinct-raw-native-observation-001'/c['item_id']/'point-observations.jsonl')
assert len(product_paths)==152
arrays={}; encoded=decoded=npy_bytes=0
for n in custody['native_arrays']:
 p=ROOT/n['path'];b=check(p,n);encoded+=len(b)
 with zipfile.ZipFile(p) as z:
  assert sorted(z.namelist())==['mask.npy','values.npy']
  for m in n['decoded_members']:
   bb=z.read(m['path']);assert len(bb)==m['bytes'] and sha(bb)==m['sha256'];npy_bytes+=len(bb)
 with np.load(p,allow_pickle=False) as z: values=z['values'];mask=z['mask']
 md=json.loads(p.with_suffix('.json').read_text());w=md['native_window']
 assert values.shape==mask.shape==(w[3],w[2]);assert mask.dtype==np.uint8
 assert values.dtype==(np.uint8 if md['asset']=='scl' else np.uint16)
 assert md['source_url']==items[md['item_id']]['assets'][md['asset']]['source_url']
 assert md['source_header']==items[md['item_id']]['assets'][md['asset']]['actual_header']
 assert md['source_object_identity']==items[md['item_id']]['assets'][md['asset']]['HEAD_identity']
 decoded+=values.nbytes+mask.nbytes
 arrays[(md['item_id'],md['asset'],*md['native_block'])]=(values,mask,w)
assert (len(arrays),encoded,decoded,npy_bytes)==(70,76629469,172595200,172613120)
reuse=[]
for r in plan['compatible_previously_observed_block_reuse']['blocks']:
 md=json.loads((ROOT/(r['current_relative_stem']+'.json')).read_text())
 orig=Path(r['local_original_metadata']); check(orig,r['original_whole_metadata'])
 assert md['original_observation_custody_body_unchanged']==json.loads(orig.read_text())
 assert md['original_whole_metadata_pin']==r['original_whole_metadata']
 assert md['original_whole_array_pin']==r['original_whole_array']
 check(ROOT/(r['current_relative_stem']+'.npz'),r['original_whole_array'])
 assert md['compatibility_binding_only'] is True
 for field in ('source_url','source_object_identity','source_header','native_window','native_block','saved_utc','array'):
  assert md[field]==md['original_observation_custody_body_unchanged'][field]
 reuse.append(r['original_whole_array'])
assert len(reuse)==15
proposals=rows(ROOT/'author-proposed81-nextdated-dispositions.jsonl')
prior={key(r):r for r in rows(ROOT/'original81-prior-complete-dated-stage-records.jsonl')}
observations={key(o):o for o in obs}
scope={key(r) for r in proposals};assert len(scope)==len(proposals)==len(obs)==81
held={key(r) for r in rows(ACC/'specific-residual461-owner-y-x.jsonl.gz')}
accepted10={key(r) for r in rows(ACC/'adopted10-owner-y-x.jsonl.gz')}
accepted_union={key(r) for r in rows(ACC/'known-exact-adopted-union133385-owner-y-x.jsonl.gz')}
assert len(held)==461 and len(accepted10)==10 and len(accepted_union)==133385
assert scope<=held and not scope&accepted10 and not scope&accepted_union
proposalkeys={key(r) for r in proposals if r['author_proposed_disposition']['answer'] is not None}
assert proposalkeys=={key(r) for r in rows(ROOT/'author-proposed52-owner-y-x.jsonl')} and len(proposalkeys)==52
for r in proposals:
 k=key(r);assert r['prior_complete_dated_stage_record_unchanged']==prior[k]
 assert r['new_actual_saved_observation_unchanged']==observations[k]
 assert set(dates(prior[k]))=={'2020-01-01','2020-01-03'}
 assert observations[k]['acquisition_datetime'][:10]=='2020-01-06'
 check(ROOT/r['new_actual_observation_container']['file'],r['new_actual_observation_container'])
 for v in r['actual_views'].values():check(ROOT/v['file'],v)
inventory=json.loads((ROOT/'native-rawDN-context-pages/contact-inventory.json').read_text())
palette=np.array([[0,0,0],[255,0,0],[70,70,70],[90,55,25],[0,160,0],[230,190,70],[0,80,230],[140,140,140],[185,185,185],[255,255,255],[100,220,255],[255,160,220]],np.uint8)
panels={};native_checks=[]
def crop(o,b):
 a=o['assets'][b];header=items[o['item_id']]['assets'][b]['actual_header'];left,top,width,height=a['native_context_window_plan']['requested_context_window']
 v=np.zeros((height,width),np.uint8 if b=='scl' else np.uint16);m=np.zeros((height,width),np.uint8)
 bh,bw=header['block_shapes'][0]
 for rr in range(height):
  for cc in range(width):
   sr,sc=top+rr,left+cc
   if 0<=sr<header['height'] and 0<=sc<header['width']:
    vals,mask,w=arrays[(o['item_id'],b,sr//bh,sc//bw)];v[rr,cc]=vals[sr-w[1],sc-w[0]];m[rr,cc]=mask[sr-w[1],sc-w[0]]
 nr,nc=a['native_containing_pixel'];assert int(v[nr-top,nc-left])==a['raw_value'];assert int(m[nr-top,nc-left])==a['native_valid_mask']==255
 planned=planned_points[o['point_index']];assert planned['centre_unchanged']==o['centre_unchanged'];assert planned['per_asset_native_plan'][b]==a['native_context_window_plan']
 x,y=planned['projected_coordinates'];t=header['transform'];assert t[1]==t[3]==0;col,row=(x-t[2])/t[0],(y-t[5])/t[4];assert np.allclose([row,col],a['native_fractional_pixel'],rtol=0,atol=1e-8)
 assert [int(np.floor(row)),int(np.floor(col))]==a['native_containing_pixel']
 return v,m,(row-top,col-left)
def enlarge(p,n,cy,cx,arm):
 size=p.shape[0];ii=np.arange(n)*size//n;im=p[ii[:,None],ii[None,:]].copy();yy,xx=int(cy/size*n),int(cx/size*n)
 for d in (-arm,-arm+1,arm-1,arm):
  for dy,dx in ((d,0),(0,d)):
   if 0<=yy+dy<n and 0<=xx+dx<n:im[yy+dy,xx+dx]=[255,255,0]
 return im
for o in obs:
 cs=[crop(o,b) for b in ('red','green','blue','nir')];raw=np.stack([c[0]for c in cs]);mask=np.stack([c[1]for c in cs]);cy,cx=cs[0][2]
 detail=[];wide=[]
 for bands,hi in (([0,1,2],3000),([3,0,1],5000)):
  p=np.moveaxis(np.clip(raw[bands].astype(float)/hi*255,0,255).astype(np.uint8),0,-1);p[np.any(mask==0,axis=0)]=[255,0,255]
  wide.append(enlarge(p,192,cy,cx,5));detail.append(enlarge(p[16:33,16:33],256,cy-16,cx-16,6))
 sv,sm,(sy,sx)=crop(o,'scl');sp=palette[sv];sp[sm==0]=[255,0,255];detail.append(enlarge(sp,256,sy,sx,6))
 f=ROOT/'native-rawDN-context-pages'/f"point-{o['point_index']}-native17-RGB-FCC-SCL25.png"
 assert np.array_equal(np.array(Image.open(f)),np.concatenate(detail,axis=1)),f
 panels[o['point_index']]=np.concatenate(wide,axis=1)
 native_checks.append({'point_index':o['point_index'],'original_key':o['original_key'],'all5_native_centres_valid_and_recomputed':True,'native_detail_pixels_reproduced':True,'SCL_value':o['assets']['scl']['raw_value']})
for page in inventory['pages']:
 canvas=np.full((1176,1536,3),255,np.uint8)
 for n,p in enumerate(page['panels']):canvas[(n//4)*196:(n//4)*196+192,(n%4)*384:(n%4)*384+384]=panels[p['point_index']]
 assert np.array_equal(np.array(Image.open(ROOT/page['file'])),canvas)
assert (ROOT/'failed-startup-001.value-read.stdout.jsonl').stat().st_size==0
assert 'AssertionError' in (ROOT/'failed-startup-001.value-read.stderr.log').read_text()
summary={'verification':'PASS','verified_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'offline_only_no_source_operations':True,'input_whole_file_count':279,'input_whole_file_bytes':88759996,'producer_whole_product_bodies_verified':152,'npz_count':70,'encoded_npz_bytes':encoded,'decoded_array_bytes':decoded,'decoded_npy_member_bytes_with_headers':npy_bytes,'original_reuse_arrays_and_custody_verified':15,'native_detail_pixels_reproduced':81,'contact_page_pixels_reproduced':4,'exact_native_affine_and_marker_placements_recomputed_from_approved_projected_coordinates':81,'fresh_geographic_projection_or_predicate':False,'all_five_centre_assets_valid':81,'all_prior_January1_January3_records_structurally_unchanged':81,'new_date_per_exact_key':'2020-01-06','scope_subset_current_held461':True,'scope_disjoint_accepted10_and_union133385':True,'accounting_inputs':[pin(ACC/f)for f in ('specific-residual461-owner-y-x.jsonl.gz','adopted10-owner-y-x.jsonl.gz','known-exact-adopted-union133385-owner-y-x.jsonl.gz')],'failed_startup_empty_stdout_preserved':True,'adoption_or_native_credit':0,'scientific_visual_judgments':'Separate independent review. Mechanical validity does not classify a surface.'}
(OUT/'whole-input279-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
(OUT/'native-centre-verification81.json').write_text(json.dumps(native_checks,indent=2)+'\n')
(OUT/'custody-and-scope-verification.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
