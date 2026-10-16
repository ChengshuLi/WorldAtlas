import json,pathlib,hashlib,zipfile,collections
r=pathlib.Path(__file__).resolve().parent
def pin(p):
 b=p.read_bytes();return {'file':str(p.relative_to(r)),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
prior=[json.loads(x) for x in (r/'original72-prior-held-records.jsonl').read_text().splitlines()]
d=json.load(open(r/'author-native-view-decisions-in-progress.json')); inv=json.load(open(r/'native-rawDN-context-pages/contact-inventory.json'))
obsfile=r/'next-distinct-raw-native-observation-001/S2A_48NUG_20200106_0_L2A/point-observations.jsonl';obs={a['point_index']:a for a in map(json.loads,obsfile.read_text().splitlines())}
views={p['point_index']:(page,p) for page in inv['pages'] for p in page['panels']}
assert len(prior)==len(obs)==len(d)==len(views)==72
ans={'vegetation':'dated_visible_vegetation_cover','ground':'dated_visible_exposed_or_constructed_ground_like_strip','water':'dated_visible_open_water_like_body','hold':None}
rows=[]
for old in prior:
 i=old['original_point_index']; c,why=d[str(i)]; page,p=views[i]; o=obs[i];assert old['original_key']==o['original_key']==p['original_key']
 v={'wide':dict(pin(r/page['file']),panel_1based=p['panel_1based']),'native_detail_and_separate20mSCL':dict(pin(r/f'native-rawDN-context-pages/point-{i}-native17-RGB-FCC-SCL25.png'),panels_left_to_right=['17-native10m-RGB','17-native10m-NIR-R-G','25-native20m-SCL-context-only']),'contact_inventory':pin(r/'native-rawDN-context-pages/contact-inventory.json')}
 rows.append({'original_key':old['original_key'],'original_point_index':i,'prior_complete778_stage_record_unchanged':old,'new_actual_saved_observation_unchanged':o,'new_actual_observation_container':pin(obsfile),'actual_views':v,'author_proposed_disposition':{'status':'held_specific_physical_question' if c=='hold' else 'author_proposed_bounded_dated_answer_not_adopted','answer':ans[c],'actual_source_reason':why,'original_remaining_question':old['dated_stage_outcome']['remaining_question'],'remaining_question':why if c=='hold' else None,'PB05_qualitative_only':False,'all_original_independent_source_owner_parent_portion_territorial_holds_retained':True,'adopted_or_native_credit':0}})
p=r/'author-proposed72-nextdated-dispositions.jsonl';p.write_text(''.join(json.dumps(x,separators=(',',':'))+'\n' for x in rows))
keys=[a['original_key'] for a in rows if a['author_proposed_disposition']['answer']]; keys.sort(key=lambda a:(a['owner'],a['y'],a['x']))
q=r/'author-proposed49-owner-y-x.jsonl';q.write_text(''.join(json.dumps([a['owner'],a['y'],a['x']],separators=(',',':'))+'\n' for a in keys))
item=json.load(open(obsfile.parent/'item-complete.json'))
for prod in item['products']:
 b=(r/prod['file']).read_bytes();assert len(b)==prod['bytes'] and hashlib.sha256(b).hexdigest()==prod['sha256']
arrays=[];decoded=0;values=0
for p2 in sorted(r.glob('next-distinct-raw-native-observation-001/*/*/*.npz')):
 a=dict(pin(p2));a['path']=a.pop('file');a['decoded_members']=[]
 with zipfile.ZipFile(p2) as z:
  assert z.namelist()==['values.npy','mask.npy']
  for n in z.namelist():
   b=z.read(n);decoded+=len(b);a['decoded_members'].append({'path':n,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
 arrays.append(a)
assert len(arrays)==55
values=144179200;assert decoded==values+55*256
cust={'status':'whole-local-native-array-and-products-verified','whole_item_product_bodies':len(item['products']),'native_array_count':len(arrays),'encoded_npz_bytes':sum(a['bytes'] for a in arrays),'decoded_values_and_masks_bytes':values,'decoded_npy_members_including_headers_bytes':decoded,'actual_execution':json.load(open(r/'next-distinct-raw-native-observation-001/attempt-001.execution.json')),'native_arrays':arrays,'new_adopted_or_native_credit':0}
save(r/'actual-observation-custody-verification.json',cust)
save(r/'author-review-summary.json',{'complete_scope':72,'proposed_bounded_answers':49,'class_counts':dict(collections.Counter(a[0] for a in d.values())),'holds':23,'author_viewed_all_three_contact_pages_and_all72_native_details':True,'proposal':pin(p),'proposed_literal_keys':pin(q),'custody_verification':pin(r/'actual-observation-custody-verification.json'),'limitations':'Dated visible facets only. All original observations, SCL contradictions, cloud/shadow/fringe and source/owner/parent/portion/territorial questions retained. Raw fixed display has no normalization or indices. No adoption or native credit.'})
for p2 in [p,q,r/'actual-observation-custody-verification.json',r/'author-review-summary.json']:print(pin(p2))
