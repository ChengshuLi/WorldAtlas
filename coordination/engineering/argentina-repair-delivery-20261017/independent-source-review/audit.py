import json,gzip,hashlib,subprocess,pathlib,collections,re
W=pathlib.Path('argentina-repair-author-20261017/workspace.txt').read_text().strip();H='29500dfbc67532a3ef9e9f23ca76ebafed2670b2'; B='d4968ddc37aa3aa6105e9610c9e6fadbb368ba14';Q='b3914bbdd2b6fdcb5e4ae7c860494425fa2c27ea';P='coordination/engineering/argentina-repair-delivery-20261017/';R='coordination/engineering/global-current-cell-work-queue-20261014/'
inputs=[]
def read(p,h=H):
 b=subprocess.check_output(['git','-c','protocol.allow=never','-C',W,'show',h+':'+p]);inputs.append({'commit':h,'path':p,'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)});return json.loads(gzip.decompress(b)if p.endswith('.gz')else b)
rows=read(P+'original-scope/original-intervals.json.gz'); roster=read(R+'source-feature-roster.json.gz',Q);byidx={r['source_index']:r for r in roster};owners=read(P+'original-scope/screened-package.json')['owners']; byowner={r['index']:r for r in owners}; screen=read(P+'original-scope/preliminary-source-holds.json');scope=read(P+'source-stage-001/source-scope-assessment.json');mem=read(P+'source-stage-001/source-target-membership.json');native=read(P+'source-stage-001/original-native-patch.json');positive=read(P+'source-stage-001/positive-requested-native-patch.json');holds=read(P+'source-stage-001/identity-holds.json')
keys={}; foreign=set();caba=set();foreignfeatures=collections.Counter();kinds=collections.Counter()
for y,a,z,os,si,kind in rows:
 assert len(os)==1
 for x in range(a,z):
  k=y,x,os[0];assert k not in keys; keys[k]=kind;kinds[kind]+=1
  if os[0]==7:caba.add(k)
  for i in si:
   r=byidx[i]
   if not r['source_id'].startswith('gb:ARG:'):
    foreign.add(k);foreignfeatures[i]+=1;assert r['owners']==[]
def unpack(v):return {(r['y'],x,o) for r in v['rows'] for a,z,o in r['runs'] for x in range(a,z)}
assert unpack(native)==set(keys) and unpack(positive)==set(keys)-caba
assert {(r['y'],x,r['pixelIndex'])for r in holds for x in range(r['start'],r['end'])}==caba
print('foreign key sample:',screen['foreign_keys'][:2]);print('CABA sample:',screen['CABA_keys'][:2])
assert {(r['y'],r['x'],r['pixelIndex'])for r in screen['foreign_keys']}==foreign
assert {(r['y'],r['x'],r['pixelIndex'])for r in screen['CABA_keys']}==caba
assert len(foreign)==1025 and len(caba)==32 and len(foreign|caba)==1057 and not foreign&caba
assert len(foreignfeatures)==36 and set(foreignfeatures)=={r['source_index']for r in screen['foreign_features']}
assert all(foreignfeatures[r['source_index']]==r['original_contact_cells']for r in screen['foreign_features'])
family=collections.Counter()
for i,n in foreignfeatures.items():family[':'.join(byidx[i]['source_id'].split(':')[:3])]+=n
assert dict(family)==screen['foreign_family_instance_counts']
assert len(mem)==131 and len({r['source_id']for r in mem})==131
for r in mem: assert r['source_id']in byowner[r['pixelIndex']]['source_atoms'] and r['target_id']==byowner[r['pixelIndex']]['id']
historical={}
for n in [937,949,942,943,951,928,1614]:
 d=json.load(open(f'argentina-repair-author-20261017/issue-evidence/issue-{n}.json'));ids=set(re.findall(r'gb:ARG:ADM2:\d+B\d+',d['body']));matched=[{'id':o['id'],'name':o['name'],'cells':sum(k[2]==o['index']for k in keys)}for o in owners if o['id']in ids];historical[str(n)]={'matched':matched,'cells':sum(o['cells']for o in matched),'issue_listed_ids':len(ids)}
fit=read('research/geography/argentina-gap-source-fitness-20261007/vintages/argentina-run-replay-20261007154702696203-8d548285/source-fit.json',B)
components=read(P+'source-review/prior-family-001/candidate-components.geojson');canon=lambda v:(json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n').encode(); fc={f['id']:f for f in components['features']}
for r in fit['complete_component_source_rows_in_family_order']:
 f=fc[r['component']];assert hashlib.sha256(canon(f)).hexdigest()==r['full_component_feature_sha256'];assert hashlib.sha256(canon(f['geometry'])).hexdigest()==r['component_geometry_sha256']
result={'head':H,'original_keys':len(keys),'intervals':len(rows),'owners':len(byowner),'classes':dict(kinds),'foreign_keys':len(foreign),'foreign_features':len(foreignfeatures),'foreign_family_counts':dict(family),'caba_keys':len(caba),'union_keys':len(foreign|caba),'intersection_keys':len(foreign&caba),'source_members':len(mem),'historical_applicability':historical,'prior_components':[{'id':r['component'],'status':r['status'],'surface_status':r['surface_status'],'cause_status':r['cause_status'],'assignment':r['administrative_assignment']}for r in fit['complete_component_source_rows_in_family_order']],'inputs':inputs,'limits':['Census set reconciliation only, no independent full-corpus geometry screen or physical production.','Final foreign and retained-fitness hold union is pending author rational probe and qualification.']}
pathlib.Path('argentina-independent-source-review-20261017/review-stage.json').write_text(json.dumps(result,indent=2)+'\n'); print(json.dumps(result,indent=2))
