"""Bind the genuine Argentina stock authority to every original key and explicit hold.
Usage: python reconcile-authority.py REPO EXACT_INPUT_COMMIT FRESH_OUTPUT
No source, physical or native science is replayed by this accounting method.
"""
import json,gzip,pathlib,subprocess,hashlib,collections,sys,os
assert len(sys.argv)==4 and __debug__
W=pathlib.Path(sys.argv[1]).absolute();C=sys.argv[2];O=pathlib.Path(sys.argv[3]).absolute();P='coordination/engineering/argentina-repair-delivery-20261017';assert len(C)==40 and all(c in '0121106789abcdef'for c in C)
assert O.parent.is_dir()and not O.exists()and all(not p.is_symlink()for p in(O,*O.parents));inputs=[]
def pin(p,c=C):
 row=subprocess.check_output(['git','-c','protocol.allow=never','-C',str(W),'ls-tree','-z',c,'--',p],env={**os.environ,'GIT_NO_LAZY_FETCH':'1'},timeout=30).rstrip(b'\0');meta,name=row.split(b'\t');mode,kind,oid=meta.decode().split();assert mode=='100644'and kind=='blob'and name.decode()==p
 b=subprocess.check_output(['git','-c','protocol.allow=never','-C',str(W),'cat-file','blob',oid],env={**os.environ,'GIT_NO_LAZY_FETCH':'1'},timeout=30);assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==oid
 return {'path':p,'commit':c,'mode':mode,'git_blob_oid':oid,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()},b

def js(name):
 p,b=pin(P+'/'+name);inputs.append(p);return json.loads(gzip.decompress(b)if name.endswith('.gz')else b)
def expand(rows):
 keys=set();count=0
 for r in rows:
  for a,z,o in r['runs']:
   assert isinstance(o,int)and 0<=a<z
   for x in range(a,z):keys.add((r['y'],x,o));count+=1
 assert len(keys)==count;return keys
assert pin(P+'/probes/reconcile-authority.py')[1]==pathlib.Path(__file__).read_bytes()
rows=js('original-scope/original-intervals.json.gz');scope=js('original-scope/screened-package.json');original={}
for y,a,z,ow,si,kind in rows:
 for x in range(a,z):assert(y,x,ow[0])not in original;original[y,x,ow[0]]=kind
assert len(original)==28846 and len(rows)==10702 and len({k[2]for k in original})==115
subjects=sorted(o['id']for o in scope['owners']);assert len(subjects)==len(set(subjects))==115
account=js('native-config-002/complete-original-accounting.json');holds={(r['y'],r['x'],r['pixelIndex']):r for r in account['held_keys']};assert len(holds)==6149 and holds.keys()<=original.keys()
diagnostic=js('native-diagnostic-001/native-diagnostic.json');qualified=expand(js('native-config-002/native-qualified-patch.json')['rows']);assert qualified==expand(diagnostic['supported_rows'])and len(qualified)==22697 and not qualified&holds.keys()and qualified|holds.keys()==original.keys()
authority=js('native-authority-001/constructor-result.json');binding=js('native-authority-001/authority-binding.json');preimage=js('native-authority-001/original-rule-preimage.json');rulepin,rulebytes=pin(P+'/native-authority-001/original-rule-preimage.json');assert authority['kind']=='existing-source-target-native-constructor-result'and authority['rule_sha256']==hashlib.sha256(rulebytes).hexdigest()and {**binding,'kind':'source-target-native-rule-v1'}==preimage
assert authority['component_ids']==[r['component_id']for r in authority['ledger_rows']];componentkeys=set();components=set();targets=set()
for row in authority['ledger_rows']:
 assert row['disposition']=='assigned'and row['component_id']not in components;components.add(row['component_id']);targets.add(row['target_id']);kk=expand(row['native_rows']);assert len(kk)==row['native_cells']and {k[2]for k in kk}=={row['pixelIndex']}and not componentkeys&kk;componentkeys|=kk
assert componentkeys==qualified and len(components)==len(targets)==110 and targets<=set(subjects)
for role in['native_patch','source_evidence']:
 actual,b=pin(binding[role]['path'],binding[role]['commit']);assert actual==binding[role]
 if role=='native_patch':assert expand(json.loads(b)['rows'])==qualified
before=js('native-inputs-001/source-evidence.json');after=js('native-inputs-002/source-evidence.json');old={t['id']:t for t in before['targets']};assert all(before[k]==after[k]for k in before if k!='targets')
assert all({k:v for k,v in old[t['id']].items()if k!='coverage_rows'}=={k:v for k,v in t.items()if k!='coverage_rows'}for t in after['targets'])
negative_before=sum(len(t['territorial_exclusions'])for t in before['targets']);negative_after=sum(len(t['territorial_exclusions'])for t in after['targets']);assert negative_before==194 and negative_after==192
physical=js('physical-001/whole-target-support.json');source_stage=js('source-stage-001/source-scope-assessment.json');provenance=js('native-inputs-002/territorial-exclusion-provenance.json');negative_features=sum(f['feature_count']for f in provenance['complete_sources']if f['source_family']in provenance['negative_families']);assert negative_features==117
owner_rows=[]
for r in account['owners']:
 r=dict(r);r['qualified_cells']=r.pop('qualified_candidate_cells');r['status']=r['status'].replace('qualified-candidate','qualified');owner_rows.append(r)
quartet={'rule_preimage':rulepin,'source_authority':pin(P+'/native-authority-001/authority-binding.json')[0],'ledger':pin(P+'/native-authority-001/constructor-result.json')[0],'native_patch':binding['native_patch']}
classes=lambda kk:dict(sorted(collections.Counter(original[k]for k in kk).items()))
assert classes(qualified)=={'inland-water':1065,'land':21632}and classes(holds)=={'inland-water':7,'land':6142}
limits=['Genuine source/native qualification is not actual current-owner-zero, selected-bank conservation, emitted-consumer acceptance or accepted repair credit.','All115 original subjects,28846 original cells and10702 original intervals are retained. Five wholly held owners remain in exact accounting.','The source hold union retains CABA32, prior seven-component source fitness4, Tierra del Fuego5089 and foreign1025, including one foreign/Tierra-del-Fuego overlap; union6149.','Conservative whole-owner Tierra del Fuego holds do not assert every affected key is wrong; later narrowing needs an affirmative localized scope/crosswalk proof.','All131 whole physical members and58 geometric issues remain retained, even for held owners. Native support does not establish present physical truth.','Complete consumed525 versus advertised526, represented2020 metadata, current topology/name/parent limits and earlier source/history obligations remain unresolved.','No legal boundary, regional certificate, publication or historical import approval.']
result={'kind':'complete-original-Argentina-native-authority-accounting','version':1,'input_commit':C,'original_cells':len(original),'original_intervals':len(rows),'original_subjects':len(subjects),'qualified_cells':len(qualified),'qualified_components':len(components),'held_cells':len(holds),'source_hold_cells':6149,'new_native_hold_cells':0,'foreign_Tierra_del_Fuego_overlap_cells':1,'qualified_physical_classes':classes(qualified),'held_physical_classes':classes(holds),'original_physical_classes':classes(original),'exact_native_held_equals_independent_foreign_only_keys':account['exact_native_held_equals_independent_foreign_only_keys'],'original_keys_exactly_partitioned':True,'subject_ids':subjects,'owners':owner_rows,'held_keys':account['held_keys'],'original_negative_instances_preserved':negative_before,'qualified_positive_negative_instances':negative_after,'surviving_whole_negative_bindings_exact':True,'complete_negative_source_features':negative_features,'full_physical_members':len(physical['results']),'physical_issues':sum(len(r['issues'])for r in physical['results']),'physical_members_with_issues':sum(bool(r['issues'])for r in physical['results']),'full_primary_source_features':source_stage['whole_source_feature_count'],'qualified_source_members':len(after['targets']),'whole_held_owners':5,'inputs':inputs,'limits':limits}
handoff={'kind':'qualified-Argentina-original-native-authority-handoff','version':1,'input_commit':C,'original_cells':28846,'original_intervals':10702,'qualified_cells':22697,'explicit_held_cells':6149,'subject_ids':subjects,'authorities':[quartet],'qualified_owners':110,'limits':limits}
encoded={n:(json.dumps(v,separators=(',',':'))+'\n').encode()for n,v in {'complete-native-authority-accounting.json':result,'qualified-authority-handoff.json':handoff}.items()};assert sum(map(len,encoded.values()))<4*1024*1024 and not O.exists();O.mkdir()
for n,b in encoded.items():
 with(O/n).open('xb')as f:f.write(b)
print(json.dumps({k:result[k]for k in ['original_cells','original_intervals','original_subjects','qualified_cells','qualified_components','held_cells','qualified_physical_classes','held_physical_classes','original_keys_exactly_partitioned']}))
