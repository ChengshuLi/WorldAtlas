from pathlib import Path
import hashlib,json,zipfile,io,collections
import numpy as np
P=Path(__file__).resolve().parent; S=P/'source-snapshot'
def sha(b): return hashlib.sha256(b).hexdigest()
def load(f): return json.loads((S/f).read_text())
def lines(f):return [json.loads(x) for x in (S/f).read_text().splitlines()]
checks=collections.Counter(); pins={}
def pin(d):
 f=d.get('file',d.get('path'));b=(S/f).read_bytes();assert len(b)==d['bytes'],f;assert sha(b)==d['sha256'],f;pins[f]={'file':f,'bytes':len(b),'sha256':sha(b)}; checks['hash_pin_references']+=1
 return b
prereq=json.loads((P.parent/'batam72-independent-review/final-review.json').read_text())
for fn,k in [('next-distinct-native-block-plan72.json','plan'),('read_next_distinct_native_blocks.py','reader')]:pin(dict(prereq[k],file=fn))
plan=load('next-distinct-native-block-plan72.json');item=plan['items'][0]; assert len(plan['items'])==1
obsbase='next-distinct-raw-native-observation-001';ibase=obsbase+'/'+item['item_id']; complete=load(ibase+'/item-complete.json');status=load(obsbase+'/execution-status.json'); execution=load(obsbase+'/attempt-001.execution.json');custody=load('actual-observation-custody-verification.json');inventory=load('native-rawDN-context-pages/contact-inventory.json')
assert complete['plan_sha256']==prereq['plan']['sha256']==execution['plan_sha256']==status['plan_sha256'];assert complete['reader_sha256']==prereq['reader']['sha256']==execution['reader']['sha256']==status['reader']['sha256']
assert complete['asset_block_count']==55 and complete['point_count']==72
assert status['complete_items']==[complete]
for f in ['author-proposed72-nextdated-dispositions.jsonl','author-proposed49-owner-y-x.jsonl','actual-observation-custody-verification.json',obsbase+'/attempt-001.execution.json',obsbase+'/attempt-001.started.json',obsbase+'/execution-status.json',ibase+'/item-complete.json','original72-prior-held-records.jsonl','render_saved_next72_rawDN.py']:
 b=(S/f).read_bytes();pin({'file':f,'bytes':len(b),'sha256':sha(b)})
pin(plan['input_plan'])
assert status['state']=='complete' and status['failures']==execution['failures']==[]
assert status['remote_value_block_calls']==execution['remote_data_block_calls']==55
assert status['remote_mask_block_calls']==execution['remote_mask_block_calls']==55
assert execution==custody['actual_execution'];assert execution['complete_points']==72 and execution['reused_blocks']==0
for prod in complete['products']:pin(prod)
assert len(complete['products'])==116
arrays={};decoded=0;encoded=0;members=0
for a in custody['native_arrays']:
 b=pin(a);encoded+=len(b)
 with zipfile.ZipFile(io.BytesIO(b)) as z:
  assert set(z.namelist())=={'values.npy','mask.npy'}
  for m in a['decoded_members']:
   mb=z.read(m['path']);assert len(mb)==m['bytes'] and sha(mb)==m['sha256'];members+=len(mb)
 with np.load(io.BytesIO(b),allow_pickle=False) as z:
  ar={k:z[k] for k in z.files};arrays[a['path']]=ar;decoded+=sum(v.nbytes for v in ar.values())
 checks['native_npz_and_member_sets']+=1
assert len(arrays)==55 and encoded==66860828==custody['encoded_npz_bytes'];assert decoded==144179200==custody['decoded_values_and_masks_bytes'];assert members==144193280==custody['decoded_npy_members_including_headers_bytes']
receipts={}
for band, asset in item['assets'].items():
 done=load(ibase+'/'+band+'/asset-complete.json');assert done['status']=='raw-native-blocks-complete';assert done['complete_point_records']==72;assert len(done['native_blocks'])==len(asset['native_blocks'])==11
 assert done['source_object_identity']==asset['HEAD_identity']
 for b in asset['native_blocks']:
  br,bc=b['block'];f=ibase+'/'+band+('/block-%02d-%02d.json'%(br,bc));r=load(f);receipts[r['array']['file']]=r
  assert r['plan_sha256']==prereq['plan']['sha256'] and r['reader_sha256']==prereq['reader']['sha256']
  assert r['native_window']==b['native_window'];assert r['native_block']==b['block'];assert r['source_url']==asset['source_url'];assert r['source_object_identity']==asset['HEAD_identity'];assert r['source_header']==asset['actual_header'];assert r['whole_remote_object_authenticated'] is False
  a=arrays[r['array']['file']];assert a['values'].shape==a['mask'].shape==(r['native_window'][3],r['native_window'][2]);assert str(a['values'].dtype)==asset['actual_header']['dtypes'][0];assert str(a['mask'].dtype)=='uint8';pin(r['array']); checks['block_receipt_plan_joins']+=1
rows=lines(ibase+'/point-observations.jsonl');prior=lines('original72-prior-held-records.jsonl');proposal=lines('author-proposed72-nextdated-dispositions.jsonl');keys=lines('author-proposed49-owner-y-x.jsonl')
def key(x):return tuple(x['original_key'][k] for k in ('owner','y','x'))
byid={x['point_index']:x for x in rows};priorbyid={x['original_point_index']:x for x in prior};planbyid={x['point_index']:x for x in item['points']};panels={x['point_index']:x for page in inventory['pages'] for x in page['panels']}
assert len(byid)==len(priorbyid)==len(planbyid)==len(panels)==len(proposal)==72
assert set(byid)==set(priorbyid)==set(planbyid)==set(panels)=={x['original_point_index'] for x in proposal}
assert len({key(x) for x in rows})==72;assert set(key(x) for x in rows)==set(key(x) for x in prior)==set(key(x) for x in proposal)==set(key(x) for x in item['points'])
for page in inventory['pages']:pin(page)
for p in inventory['all_loaded_source_array_pins']:pin(p)
for p in proposal:
 id=p['original_point_index'];r=byid[id];prev=priorbyid[id];planned=planbyid[id];panel=panels[id]
 assert p['prior_complete778_stage_record_unchanged']==prev;assert p['new_actual_saved_observation_unchanged']==r
 assert r['centre_unchanged']==planned['centre_unchanged']==prev['unchanged_original_proposal']['centre_unchanged'];assert p['original_key']==r['original_key']==planned['original_key']==panel['original_key']
 assert p['author_proposed_disposition']['original_remaining_question']==prev['dated_stage_outcome']['remaining_question'];assert p['author_proposed_disposition']['adopted_or_native_credit']==0
 for v in p['actual_views'].values():pin(v)
 pin(p['new_actual_observation_container'])
 assert r['acquisition_datetime']==panel['acquisition_datetime']==item['acquisition_datetime'];assert r['item_id']==panel['item_id']==item['item_id']
 for band,a in r['assets'].items():
  pin(a['containing_array']);rec=receipts[a['containing_array']['file']];ar=arrays[a['containing_array']['file']];l,t,w,h=rec['native_window'];row,col=a['native_containing_pixel'];y,x=row-t,col-l
  assert int(ar['values'][y,x])==a['raw_value'];assert int(ar['mask'][y,x])==a['native_valid_mask'];assert ar['values'][y-1:y+2,x-1:x+2].tolist()==a['actual_raw3x3'];assert ar['mask'][y-1:y+2,x-1:x+2].tolist()==a['actual_mask3x3']
  assert a['native_context_window_plan']==planned['per_asset_native_plan'][band];assert a['source_object_identity']==item['assets'][band]['HEAD_identity'];assert a['source_url']==item['assets'][band]['source_url'];checks['point_asset_value_mask_3x3_receipt_joins']+=1
 assert panel['raw_RGBNIR']==[r['assets'][b]['raw_value'] for b in ['red','green','blue','nir']];assert panel['raw_masks']==[r['assets'][b]['native_valid_mask'] for b in ['red','green','blue','nir']];assert panel['raw_SCL_value']==r['assets']['scl']['raw_value'];assert panel['raw_SCL_mask']==r['assets']['scl']['native_valid_mask']
 assert panel['fractional_centre_in_crop']==[r['assets']['red']['native_fractional_pixel'][0]-panel['native_requested_window'][1],r['assets']['red']['native_fractional_pixel'][1]-panel['native_requested_window'][0]]
 checks['exact_original_prior_plan_observation_panel_proposal_joins']+=1
assert {tuple(k) for k in keys}=={key(p) for p in proposal if p['author_proposed_disposition']['answer'] is not None};assert len(keys)==49
out={'status':'PASS_LOCAL_CUSTODY_AND_EXACT_JOINS','prerequisite_review':{'file':str(P.parent/'batam72-independent-review/final-review.json'),'sha256':sha((P.parent/'batam72-independent-review/final-review.json').read_bytes()),'scope':'Reuse independently verified source/projection/frozen197 metadata selection. No new source reads.'},'source_snapshot':str(S),'checks':dict(checks),'unique_hash_pinned_local_files':len(pins),'whole_item_product_bodies':len(complete['products']),'native_arrays':len(arrays),'encoded_npz_bytes':encoded,'decoded_values_masks_bytes':decoded,'decoded_npy_members_with_headers_bytes':members,'actual_execution':execution,'original_key_count':72,'literal_author_answer_keys':49,'prior_original_records_unchanged':True,'scientific_interpretation_automatically_inferred':False,'raster_acquisition_or_render_replay':False,'new_source_value_mask_calls':0,'authority_or_repair_credit':0}
(P/'custody-review.json').write_text(json.dumps(out,indent=2)+'\n');(P/'verified-file-pins.json').write_text(json.dumps(sorted(pins.values(),key=lambda x:x['file']),indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='actual_execution'},indent=2))
