"""Conserve every original Argentina key and narrow only positive coverage.
Usage: python prepare-qualified-scope.py REPO EXACT_METHOD_COMMIT FRESH_OUTPUT
No original geometry, physical measurement, class or negative is modified.
"""
import collections,gzip,hashlib,json,os,pathlib,subprocess,sys,time
assert len(sys.argv)==4 and __debug__
W=pathlib.Path(sys.argv[1]).absolute();C=sys.argv[2];O=pathlib.Path(sys.argv[3]).absolute();H='d4968ddc37aa3aa6105e9610c9e6fadbb368ba14';P='coordination/engineering/argentina-repair-delivery-20261017'
assert len(C)==40 and all(c in '0123456789abcdef'for c in C)and O.parent.is_dir()and not O.exists()and all(not p.is_symlink()for root in(W,O)for p in(root,*root.parents))
sha=lambda b:hashlib.sha256(b).hexdigest();inputs={};started=time.monotonic();total=0
env={**os.environ,'GIT_NO_LAZY_FETCH':'1','GIT_NO_REPLACE_OBJECTS':'1','GIT_TERMINAL_PROMPT':'0'}
def git(*args):return subprocess.check_output(['git','-c','protocol.allow=never','-C',str(W),*args],env=env,timeout=30)
def read(p,c=C):
 global total
 assert not p.startswith('/')and all(x not in('','.','..')for x in p.split('/'))and time.monotonic()-started<300
 row=git('ls-tree','-z',c,'--',p).rstrip(b'\0');meta,name=row.split(b'\t');mode,kind,oid=meta.decode().split();assert mode=='100644'and kind=='blob'and name.decode()==p
 size=int(git('cat-file','-s',oid));assert 0<size;b=git('cat-file','blob',oid);assert len(b)==size and hashlib.sha1(b'blob '+str(size).encode()+b'\0'+b).hexdigest()==oid
 pin={'path':p,'commit':c,'mode':mode,'git_blob_oid':oid,'bytes':size,'sha256':sha(b)}
 if p.endswith('.gz'):
  import io
  with gzip.GzipFile(fileobj=io.BytesIO(b))as f:d=f.read()
  pin.update(decoded_bytes=len(d),decoded_sha256=sha(d));b=d
 if(c,p)not in inputs:total+=size+pin.get('decoded_bytes',0)
 inputs[c,p]=pin;return b
js=lambda p,c=C:json.loads(read(p,c))
def pin(p,c=C):read(p,c);return inputs[c,p]
assert read(P+'/probes/prepare-qualified-scope.py')==pathlib.Path(__file__).read_bytes()
d=js(P+'/native-diagnostic-001/native-diagnostic.json');source=js(P+'/source-review/complete-scope-002/held-original-keys.json');scope=js(P+'/original-scope/screened-package.json');original=js(P+'/original-scope/original-intervals.json.gz');config=js(P+'/native-config-001/source-evidence-config.json');old_evidence=js(P+'/native-inputs-001/source-evidence.json')
def keys(rows):
 result=set();count=0
 for r in rows:
  for a,z,o in r['runs']:
   assert a<z
   for x in range(a,z):
    key=(r['y'],x,o);assert key not in result;result.add(key);count+=1
 assert count==len(result);return result
original_keys={(y,x,ow[0])for y,a,z,ow,si,c in original for x in range(a,z)};classes={(y,x,ow[0]):c for y,a,z,ow,si,c in original for x in range(a,z)}
supported=keys(d['supported_rows']);held_native=keys(d['held_rows']);requested=keys(d['requested_rows']);sourcekeys={(r['y'],r['x'],r['pixelIndex'])for r in source};foreign_only={(r['y'],r['x'],r['pixelIndex'])for r in source if r['reasons']==['foreign-whole-original-contact']}
assert len(original)==10702 and len(original_keys)==28846 and len(sourcekeys)==len(source)==6149
assert held_native==foreign_only and len(held_native)==1024 and len(supported)==22697 and len(requested)==23721 and not supported&held_native and requested==supported|held_native
assert original_keys==supported|sourcekeys and not supported&sourcekeys
keepowners={k[2]for k in supported};old_targets=config['source_evidence']['targets'];changed=[];removed=[];targets=[]
for old in old_targets:
 if old['pixelIndex']not in keepowners:removed.append(old);continue
 t=dict(old)
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
assert len(keepowners)==len(targets)==110 and len(removed)==1
for t in targets:
 original_target=next(old for old in old_targets if old['id']==t['id'])
 assert {k:v for k,v in t.items()if k!='coverage_rows'}=={k:v for k,v in original_target.items()if k!='coverage_rows'}
byowner=[]
for o in scope['owners']:
 own=o['index'];a={k for k in original_keys if k[2]==own};q=a&supported;s=a&sourcekeys;assert q|s==a and not q&s
 byowner.append({'id':o['id'],'pixelIndex':own,'name':o['name'],'original_cells':len(a),'qualified_candidate_cells':len(q),'source_hold_cells':len(s),'status':'held-only'if not q else'qualified-candidate-with-holds'if s else'qualified-candidate','source_atoms':o['source_atoms']})
report={'kind':'Argentina-complete-original-to-supported-and-held-reconciliation','original_cells':28846,'original_intervals':len(original),'original_subjects':115,'native_requested_cells':23721,'native_supported_cells':22697,'native_held_cells':1024,'exact_native_held_equals_independent_foreign_only_keys':True,'source_hold_cells':6149,'new_native_hold_cells':0,'held_cells':6149,'supported_physical_classes':dict(collections.Counter(classes[k]for k in supported)),'held_physical_classes':dict(collections.Counter(classes[k]for k in sourcekeys)),'positive_owners':110,'positive_source_members':110,'wholly_held_owners':5,'coverage_owners_narrowed':len(changed),'coverage_owners_removed':len(removed),'changed_coverage_owners':changed,'removed_positive_owners':[t['pixelIndex']for t in removed],'complete_original_partition':True,'owners':byowner,'held_keys':source,'inputs':list(inputs.values()),'limits':['Supported diagnostic keys still require genuine stock source/native authority.','No current selected owner-zero, selected-bank conservation or emitted-consumer acceptance is claimed.','All whole original source families and full measured physical input/evidence remain unchanged; held owners are removed only from the positive request.','CABA, prior seven-component source fitness, Tierra del Fuego scope, foreign contacts and other original source/vintage obligations remain explicitly unresolved.']}
preservation={'kind':'Argentina-qualified-coverage-only-adaptation','changed_coverage_owners':changed,'removed_positive_owners':[t['pixelIndex']for t in removed],'all_other_surviving_fields_equal':True,'unchanged_fields':['catalogue','families','physical_evidence','physical_input','physical_reproduction','source_membership'],'source_evidence_old_pin':inputs[C,P+'/native-inputs-001/source-evidence.json'],'old_negative_instances':sum(len(t['territorial_exclusions'])for t in old_evidence['targets']),'source_hold_foreign_equality':True,'limits':['Final generated source-evidence negatives must still compare exactly for every surviving target before native authority handoff.','Complete original physical body and all source-family descriptors are preserved, including wholly held forensic members.']}
products={'source-evidence-config.json':config,'native-qualified-patch.json':{'rows':d['supported_rows']},'complete-original-accounting.json':report,'coverage-preservation.json':preservation};encoded={n:(json.dumps(v,separators=(',',':'),ensure_ascii=False)+'\n').encode()for n,v in products.items()};assert not O.exists()and all(not p.is_symlink()for p in(O,*O.parents));O.mkdir()
for n,b in encoded.items():
 with(O/n).open('xb')as f:f.write(b)
print(json.dumps({'supported':22697,'held':6149,'exact1024_foreign_equality':True,'owners':110,'source_members':110,'original_subjects':115,'outputs':{n:{'bytes':len(b),'sha256':sha(b)}for n,b in encoded.items()}}))
