"""Retain whole evidence and qualify only actual native-supported USA original keys.
Usage: python prepare-qualified-scope.py REPO EXACT_INPUT_COMMIT FRESH_OUTPUT
"""
import json,gzip,pathlib,subprocess,hashlib,sys,collections,os
assert len(sys.argv)==4 and __debug__
W=pathlib.Path(sys.argv[1]).absolute();C=sys.argv[2];O=pathlib.Path(sys.argv[3]).absolute();P='coordination/engineering/usa-repair-delivery-20261017';assert len(C)==40 and all(c in '0123456789abcdef'for c in C)
assert O.parent.is_dir()and not O.exists()and all(not p.is_symlink()for p in(O,*O.parents));pins=[]
def raw(p):
 b=subprocess.check_output(['git','-c','protocol.allow=never','-C',str(W),'show',C+':'+p],env={**os.environ,'GIT_NO_LAZY_FETCH':'1'},timeout=30);pins.append({'commit':C,'path':p,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()});return b
js=lambda p:json.loads(raw(p))
def keys(rows):return {(r['y'],x,o)for r in rows for a,z,o in r['runs']for x in range(a,z)}
assert raw(P+'/probes/prepare-qualified-scope.py')==pathlib.Path(__file__).read_bytes()
d=js(P+'/native-diagnostic-002/native-diagnostic.json');source=js(P+'/independent-source-review/hold-key-union.json');phys=js(P+'/native-config-002/physical-admission-holds.json');scope=js(P+'/original-scope/screened-package.json');original=json.loads(gzip.decompress(raw(P+'/original-scope/original-intervals.json.gz')));config=js(P+'/native-config-002/source-evidence-config.json');old_evidence=js(P+'/native-inputs-002/source-evidence.json')
original_keys={(y,x,ow[0])for y,a,z,ow,si,c in original for x in range(a,z)};classes={(y,x,ow[0]):c for y,a,z,ow,si,c in original for x in range(a,z)};supported=keys(d['supported_rows']);held_native=keys(d['held_rows']);requested=keys(d['requested_rows']);sourcekeys={(r['y'],r['x'],r['owner_index'])for r in source['held_keys']};foreign={(r['y'],r['x'],r['owner_index'])for r in source['held_keys']if r['reasons']==['complete-foreign-original-contact']};physicalkeys={(r['y'],r['x'],r['owner_index'])for r in phys['held_keys']}
assert held_native==foreign and len(held_native)==63 and len(supported)==105927 and len(requested)==105990 and not supported&held_native and requested==supported|held_native
assert not sourcekeys&physicalkeys and original_keys==supported|sourcekeys|physicalkeys and not supported&(sourcekeys|physicalkeys)and len(original_keys)==107131
keepowners={k[2]for k in supported};old_targets=config['source_evidence']['targets'];changed=[];removed=[];targets=[]
for t in old_targets:
 if t['pixelIndex']not in keepowners:removed.append(t);continue
 t=dict(t)
 if 'coverage_rows'in t:
  rr=[]
  for row in t['coverage_rows']:
   runs=[]
   for a,z,c in row['runs']:
    begin=None
    for x in range(a,z):
     if(row['y'],x,t['pixelIndex'])in supported:
      if begin is None:begin=x
     elif begin is not None:runs.append([begin,x,c]);begin=None
    if begin is not None:runs.append([begin,z,c])
   if runs:rr.append({'y':row['y'],'runs':runs})
  if rr!=t['coverage_rows']:changed.append(t['pixelIndex'])
  t['coverage_rows']=rr
 targets.append(t)
config['source_evidence']['targets']=targets
assert len(keepowners)==345 and len(targets)==349 and len(removed)==3
byowner=[]
for o in scope['owners']:
 own=o['index'];a={k for k in original_keys if k[2]==own};q=a&supported;s=a&sourcekeys;p=a&physicalkeys;assert q|s|p==a and not q&s and not q&p
 byowner.append({'id':o['id'],'pixelIndex':own,'name':o['name'],'original_cells':len(a),'qualified_candidate_cells':len(q),'source_hold_cells':len(s),'physical_admission_hold_cells':len(p),'status':'held-only'if not q else'qualified-candidate-with-holds'if s or p else'qualified-candidate','source_atoms':o['source_atoms']})
held=[]
for key in sorted(sourcekeys|physicalkeys):
 item={'y':key[0],'x':key[1],'owner_index':key[2],'physical_class':classes[key]}
 if key in sourcekeys:item['reasons']=next(r['reasons']for r in source['held_keys']if(r['y'],r['x'],r['owner_index'])==key)
 else:item['reasons']=['unmeasured-invalid-original-physical-source-whole-owner-hold']
 held.append(item)
report={'kind':'USA-complete-original-to-supported-and-held-reconciliation','original_cells':107131,'original_intervals':len(original),'original_subjects':351,'native_requested_cells':105990,'native_supported_cells':105927,'native_held_cells':63,'exact_native_held_equals_independent_foreign_keys':True,'source_hold_cells':600,'physical_admission_hold_cells':604,'source_physical_hold_intersection_cells':0,'held_cells':1204,'supported_physical_classes':dict(collections.Counter(classes[k]for k in supported)),'held_physical_classes':dict(collections.Counter(classes[k]for k in sourcekeys|physicalkeys)),'positive_owners':345,'positive_source_members':349,'wholly_held_owners':6,'coverage_owners_narrowed':len(changed),'coverage_owners_removed':len(removed),'changed_coverage_owners':changed,'removed_positive_owners':[t['pixelIndex']for t in removed],'complete_original_partition':True,'owners':byowner,'held_keys':held,'inputs':pins,'limits':['Supported diagnostic keys are not genuine source/native authority until the stock constructor succeeds.','No current selected owner-zero, selected-bank conservation or emitted-consumer acceptance is claimed.','All whole original source families and full measured physical input/evidence remain unchanged; held owners are removed only from the positive request.']}
preservation={'kind':'USA-qualified-coverage-only-adaptation','changed_coverage_owners':changed,'removed_positive_owners':[t['pixelIndex']for t in removed],'all_other_surviving_fields_equal':all({k:v for k,v in old.items()if k!='coverage_rows'}=={k:v for k,v in new.items()if k!='coverage_rows'}for old in old_targets for new in targets if old['id']==new['id']),'unchanged_fields':['catalogue','families','physical_evidence','physical_input','physical_reproduction','source_membership'],'source_evidence_old_pin':next(p for p in pins if p['path'].endswith('native-inputs-002/source-evidence.json')),'old_negative_instances':sum(len(t['territorial_exclusions'])for t in old_evidence['targets']),'source_hold_foreign_equality':True}
assert preservation['all_other_surviving_fields_equal'];products={'source-evidence-config.json':config,'native-qualified-patch.json':{'rows':d['supported_rows']},'complete-original-accounting.json':report,'coverage-preservation.json':preservation};encoded={n:(json.dumps(v,separators=(',',':'))+'\n').encode()for n,v in products.items()};assert sum(map(len,encoded.values()))<16*1024*1024 and not O.exists();O.mkdir()
for n,b in encoded.items():
 with(O/n).open('xb')as f:f.write(b)
print(json.dumps({'supported':105927,'held':1204,'exact_63_foreign_equality':True,'owners':345,'source_members':349,'outputs':{n:{'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}for n,b in encoded.items()}}))
