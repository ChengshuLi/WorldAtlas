"""Bind literal author decisions to complete retained prior/current dated observations. Offline only."""
from pathlib import Path
import json,hashlib,zipfile,collections
r=Path(__file__).resolve().parent
plan=json.loads((r/'next-distinct-native-block-plan33.json').read_bytes())
def pin(p):
 b=p.read_bytes();return {'file':str(p.relative_to(r)),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
prior=[json.loads(x)for x in(r/'original33-prior-complete-dated-stage-records.jsonl').read_text().splitlines()]
d=json.loads((r/'author-native-view-decisions-in-progress.json').read_text());inv=json.loads((r/'native-rawDN-context-pages/contact-inventory.json').read_text())
obs={};containers={};product_count=0
for item in plan['items']:
 f=r/'next-distinct-raw-native-observation-001'/item['item_id']/'point-observations.jsonl'
 receipt=json.loads((f.parent/'item-complete.json').read_text());assert receipt['point_count']==len(item['points'])
 for prod in receipt['products']:
  assert pin(r/prod['file'])==prod
 product_count+=len(receipt['products'])
 for line in f.read_text().splitlines():
  row=json.loads(line);i=row['point_index'];assert i not in obs;obs[i]=row;containers[i]=pin(f)
views={p['point_index']:(page,p)for page in inv['pages']for p in page['panels']}
assert len(prior)==len(obs)==len(d)==len(views)==plan['exact_original_scope']
assert set(map(int,d))==set(obs)==set(views)
ans={'vegetation':'dated_visible_vegetation_cover','ground':'dated_visible_exposed_or_constructed_ground_like_body','water':'dated_visible_open_water_like_body','hold':None};rows=[]
for old in prior:
 i=old['original_point_index'];c,why=d[str(i)];page,p=views[i];o=obs[i];assert old['original_key']==o['original_key']==p['original_key'];assert c in ans and why
 v={'wide':dict(pin(r/page['file']),panel_1based=p['panel_1based']),'native_detail_and_separate20mSCL':dict(pin(r/f'native-rawDN-context-pages/point-{i}-native17-RGB-FCC-SCL25.png'),panels_left_to_right=['17-native10m-RGB','17-native10m-NIR-R-G','25-native20m-SCL-context-only']),'contact_inventory':pin(r/'native-rawDN-context-pages/contact-inventory.json')}
 rows.append({'original_key':old['original_key'],'original_point_index':i,'prior_complete_dated_stage_record_unchanged':old,'new_actual_saved_observation_unchanged':o,'new_actual_observation_container':containers[i],'actual_views':v,'author_proposed_disposition':{'status':'held_specific_physical_question'if c=='hold'else'author_proposed_bounded_dated_answer_not_adopted','answer':ans[c],'actual_source_reason':why,'original_remaining_question':old['next_dated_stage_outcome']['remaining_question'],'remaining_question':why if c=='hold'else None,'PB05_qualitative_only':str(o['processing_baseline']).startswith('05'),'all_original_independent_source_owner_parent_portion_territorial_holds_retained':True,'adopted_or_native_credit':0}})
p=r/'author-proposed33-nextdated-dispositions.jsonl';p.write_text(''.join(json.dumps(x,separators=(',',':'))+'\n'for x in rows))
keys=sorted((a['original_key']for a in rows if a['author_proposed_disposition']['answer']),key=lambda a:(a['owner'],a['y'],a['x']))
q=r/f'author-proposed{len(keys)}-owner-y-x.jsonl';q.write_text(''.join(json.dumps([a['owner'],a['y'],a['x']],separators=(',',':'))+'\n'for a in keys))
arrays=[];decoded=0;values=0
for p2 in sorted(r.glob('next-distinct-raw-native-observation-001/*/*/*.npz')):
 a=dict(pin(p2));a['path']=a.pop('file');a['decoded_members']=[]
 with zipfile.ZipFile(p2)as z:
  assert z.namelist()==['values.npy','mask.npy']
  for n in z.namelist():
   b=z.read(n);decoded+=len(b);a['decoded_members'].append({'path':n,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
 arrays.append(a)
assert len(arrays)==plan['total_asset_native_block_windows']
values=plan['complete_item_resource_declaration']['exact_all_native_decoded_values_masks_bytes'];assert decoded>=values
cust={'status':'whole-local-native-array-and-products-verified','whole_item_product_bodies':product_count,'native_array_count':len(arrays),'encoded_npz_bytes':sum(a['bytes']for a in arrays),'decoded_values_and_masks_bytes':values,'decoded_npy_members_including_headers_bytes':decoded,'actual_execution':json.loads((r/'next-distinct-raw-native-observation-001/attempt-001.execution.json').read_text()),'native_arrays':arrays,'reused_previous_block_count':len(plan.get('compatible_previously_observed_block_reuse',{}).get('blocks',[])),'original_custody_in_compatibility_sidecars_preserved':True,'new_adopted_or_native_credit':0};save(r/'actual-observation-custody-verification.json',cust)
save(r/'author-review-summary.json',{'complete_scope':len(rows),'proposed_bounded_answers':len(keys),'class_counts':dict(collections.Counter(a[0]for a in d.values())),'holds':len(rows)-len(keys),'proposal':pin(p),'proposed_literal_keys':pin(q),'custody_verification':pin(r/'actual-observation-custody-verification.json'),'PB05_qualitative_only_count':sum(a['author_proposed_disposition']['PB05_qualitative_only']for a in rows),'limitations':'Dated visible facets only. All original observations, SCL contradictions, cloud/shadow/fringe, incomplete native frame, source/owner/parent/portion/territorial questions retained. Raw fixed display has no normalization or indices. No adoption or native credit.'})
for p2 in(p,q,r/'actual-observation-custody-verification.json',r/'author-review-summary.json'):print(json.dumps(pin(p2)))
