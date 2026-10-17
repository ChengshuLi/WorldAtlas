"""Apply complete reviewed source-applicability holds to all Argentina original keys.
Usage: python prepare-source-scope.py REPO EXACT_METHOD_COMMIT FRESH_OUTPUT
No source geometry is modified or physical/native qualification claimed.
"""
import collections,gzip,hashlib,json,os,re,subprocess,sys,time
from pathlib import Path
assert len(sys.argv)==4 and __debug__
R=Path(sys.argv[1]).absolute();C=sys.argv[2];O=Path(sys.argv[3]).absolute();H='d4968ddc37aa3aa6105e9610c9e6fadbb368ba14';P='coordination/engineering/argentina-repair-delivery-20261017'
assert len(C)==40 and all(c in '0123456789abcdef'for c in C)
assert O.parent.is_dir()and not O.exists()and not O.is_symlink()and all(not p.is_symlink()for p in [R,O,*R.parents,*O.parents])
sha=lambda b:hashlib.sha256(b).hexdigest()
canon=lambda v:(json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n').encode()
inputs={};total=0;start=time.monotonic();env={**os.environ,'GIT_NO_LAZY_FETCH':'1','GIT_NO_REPLACE_OBJECTS':'1','GIT_TERMINAL_PROMPT':'0'}
def read(h,p,decode=False):
 global total
 assert len(h)==40 and all(c in '0123456789abcdef'for c in h)and not p.startswith('/')and all(x not in ('','.','..')for x in p.split('/'))
 def git(*args):return subprocess.check_output(['git','-c','protocol.allow=never','-C',str(R),*args],env=env,timeout=30)
 row=git('ls-tree','-z',h,'--',p).rstrip(b'\0');meta,name=row.split(b'\t');mode,kind,oid=meta.decode().split();assert mode=='100644'and kind=='blob'and name.decode()==p
 n=int(git('cat-file','-s',oid));assert 0<n<=64*1024*1024
 b=git('cat-file','blob',oid);assert len(b)==n and hashlib.sha1(b'blob '+str(n).encode()+b'\0'+b).hexdigest()==oid
 pin={'commit':h,'path':p,'mode':mode,'git_blob_oid':oid,'bytes':n,'sha256':sha(b)}
 if decode:
  import io
  with gzip.GzipFile(fileobj=io.BytesIO(b))as f:d=f.read(64*1024*1024+1)
  assert len(d)<=64*1024*1024;pin.update(decoded_bytes=len(d),decoded_sha256=sha(d));b=d
 if(h,p)not in inputs:total+=n+pin.get('decoded_bytes',0)
 assert total<=256*1024*1024 and time.monotonic()-start<120;inputs[h,p]=pin;return b
assert read(C,P+'/probes/prepare-source-scope.py')==Path(__file__).read_bytes()
js=lambda p,h=C,decode=False:json.loads(read(h,p,decode))
original=js(P+'/original-scope/original-intervals.json.gz',decode=True)
screen=js(P+'/original-scope/screened-package.json');owners={o['index']:o for o in screen['owners']};assert len(owners)==len(screen['owners'])==115
witness=js(P+'/source-review/prior-family-keys-001/exact-prior-family-keys.json');stage=js(P+'/source-stage-001/source-scope-assessment.json');preliminary=js(P+'/original-scope/preliminary-source-holds.json');obligations=js(P+'/original-scope/existing-obligations.json')
law=js(P+'/source-review/tdf-law-001/capture.json');lawbody=read(C,P+'/source-review/tdf-law-001/official-law-1186.html');assert len(lawbody)==law['bytes']and sha(lawbody)==law['sha256']and law['observed_sanction_date']=='2017-10-27'and law['observed_official_publication_date']=='2017-11-14'
past='data/regional-review/regional-review-3e9f1d51da6b0a22/'
inventory=js(past+'source-inventory.json',H);comparisons=[json.loads(s)for s in read(H,past+'geometry-comparisons.jsonl').splitlines()];assessments=[json.loads(s)for s in read(H,past+'location-assessments.jsonl').splitlines()];read(H,past+'RESEARCH.md')
comparison={r['id']:r for r in comparisons};assessment={r['location_id']:r for r in assessments if r.get('record_type')=='location'}
assert next(s for s in inventory['sources']if s['id']=='argentina-law-1186')['vintage'].startswith('2017')
bykey={};byowner=collections.Counter();kindcounts=collections.Counter()
for y,a,z,ow,ss,k in original:
 assert len(ow)==1 and k in('land','inland-water')and ow[0]in owners
 for x in range(a,z):
  key=(y,x);assert key not in bykey;bykey[key]={'y':y,'x':x,'pixelIndex':ow[0],'physical_class':k};byowner[ow[0]]+=1;kindcounts[k]+=1
assert len(original)==10702 and len(bykey)==28846 and kindcounts=={'land':27774,'inland-water':1072}
tdf_ids={'gb:ARG:ADM2:61730980B7053808465014','gb:ARG:ADM2:61730980B87507155551581'}
tdf_owners={i for i,o in owners.items()if o['id']in tdf_ids};assert tdf_owners=={8100,8196}and sum(byowner[i]for i in tdf_owners)==5089
for sid in tdf_ids:assert assessment[sid]['disposition']=='correction-needed'and comparison[sid]['simplified_iou_0_001_degrees']<.85
held={}
def add(key,reason):
 assert key in bykey
 held.setdefault(key,{**bykey[key],'reasons':[]})['reasons'].append(reason)
for k in preliminary['foreign_keys']:add((k['y'],k['x']),'foreign-whole-original-contact')
for k in preliminary['CABA_keys']:add((k['y'],k['x']),'unresolved-CABA-membership')
for k in witness['prior_family_keys']:add((k['y'],k['x']),'unresolved-seven-component-source-fitness')
assert len(held)==1061 and set(held)=={(k['y'],k['x'])for k in witness['held_union_keys']}
old=set(held);tdf={key for key,k in bykey.items()if k['pixelIndex']in tdf_owners}
for key in tdf:add(key,'unresolved-pre-2020-Tierra-del-Fuego-unit-scope')
assert len(old&tdf)==1 and len(held)==6149
remaining={key:k for key,k in bykey.items()if key not in held};assert len(remaining)==22697 and set(remaining)|set(held)==set(bykey)and not set(remaining)&set(held)
issue_ids={o['number']:set(re.findall(r'(?:gb:ARG:ADM2|atlas:city):[A-Za-z0-9-]+',o['body']))for o in obligations};decisions=[]
for i,o in sorted(owners.items()):
 sid=o['id'];issues=sorted(n for n,ids in issue_ids.items()if sid in ids);notes=[]
 if i==7:assert 941 in issues
 if sid in tdf_ids:decision='held-unresolved-intended-department-scope';notes.append('The consumed product claims 2020, after the primary 2017 five-department law. Existing two subjects and low-IoU comparison do not provide an affirmative localized crosswalk. Hold every original key for these two owners, without asserting every key is wrong or creating/reparenting units.')
 elif i==7:decision='held-unresolved-CABA-membership';notes.append('Original17 whole members include15 communes plus Lanús and Avellaneda. The actual constructor selects by overlap or parent-name match and unions whole originals; it does not clip to the Federal District selection context. No city identity clearance is inferred.')
 else:decision='eligible-only-for-frozen-consumed-source-relative-restoration';notes.append('Exact source identity and whole consumed simplified pointset define the narrowly requested restoration. This does not establish current legal or historical department fitness. Complete source competitors and original physical class remain authoritative veto inputs.')
 if 937 in issues and sid not in tdf_ids:notes.append('Retained current IGN generalized topology comparison differs from the coarse selected reference. Restoring the frozen consumed pointset can address simplification loss; it does not resolve different-vintage topology, current identity, source completeness or the open correction issue.')
 if 949 in issues:notes.append('Keep the exact frozen consumed shapeID, name and parent. Current IGN name ambiguity/absence and parent-code disagreement remain unresolved; no inferred current-name join, province correction or history transfer is made.')
 if 942 in issues:notes.append('La Rioja parent-label obligation remains open; no parent relabeling is part of this source-relative owner repair.')
 if 943 in issues:notes.append('Regional area-purpose/membership review remains open; this repair does not certify a WGSRPD area or change the hierarchy.')
 decisions.append({'id':sid,'pixelIndex':i,'name':o['name'],'original_cells':byowner[i],'remaining_requested_cells':sum(k['pixelIndex']==i for k in remaining.values()),'held_cells':sum(k['pixelIndex']==i for k in held.values()),'source_atoms':o['source_atoms'],'applicable_retained_issues':issues,'disposition':decision,'reasoning':notes,'south_comparison':comparison.get(sid)if 937 in issues else None,'south_assessment':assessment.get(sid)if 937 in issues else None})
assert len([d for d in decisions if 937 in d['applicable_retained_issues']])==14
rows=collections.defaultdict(list)
for (y,x),k in sorted(remaining.items()):
 rr=rows[y]
 if rr and rr[-1][1]==x and rr[-1][2]==k['pixelIndex']:rr[-1][1]=x+1
 else:rr.append([x,x+1,k['pixelIndex']])
classes=lambda rs:dict(collections.Counter(k['physical_class']for k in rs))
summary={'kind':'complete-original-Argentina-source-applicability-reconciliation','original_cells':28846,'original_intervals':10702,'original_subjects':115,'original_classes':dict(kindcounts),'foreign_original_cells':1025,'CABA_cells':32,'prior_family_cells':4,'Tierra_del_Fuego_cells':5089,'Tierra_del_Fuego_overlap_with_prior_union':1,'held_union_cells':len(held),'held_classes':classes(held.values()),'remaining_requested_cells':len(remaining),'remaining_classes':classes(remaining.values()),'remaining_subjects':len({k['pixelIndex']for k in remaining.values()}),'whole_consumed_features':525,'advertised_consumed_features':526,'physical_forensic_members':131,'whole_source_scope':'Complete consumed geoBoundaries ARG ADM2 simplified product, not the distinct69,702,323-byte unsimplified source. Every relevant original negative remains required.','Tierra_del_Fuego_primary_source':law,'source_vintage_claim':'2020 represented;2023-01-19 source update;2023-12-12 build; product-specific retrieval time unknown','recorded_license':stage['recorded_metadata']['boundaryLicense'],'decisions':decisions,'inputs':list(inputs.values()),'input_encoded_decoded_bytes':total,'elapsed_seconds':time.monotonic()-start,'limits':['This is source-applicability accounting, not stock physical or native qualification and not selected acceptance.','Original115 subjects,28,846 keys and all original classes are retained; held keys remain an explicit unresolved remainder.','All known contrary original/source-history evidence is retained. No ID, parent, current boundary or source-vintage correction is implied.','Actual consumed525 versus advertised526 remains an unresolved catalogue completeness limit; no missing feature is fabricated.','The physical stage must retain all131 original members including held CABA and Tierra del Fuego as forensic evidence.','Complete ARG and foreign original negatives are mandatory; no selected-owner-only filter, clipping, truncation or source guessing is used.']}
products={'source-applicability.json':summary,'held-original-keys.json':sorted(held.values(),key=lambda k:(k['y'],k['x'])),'requested-native-patch.json':{'rows':[{'y':y,'runs':r}for y,r in sorted(rows.items())]}}
encoded={n:canon(v)for n,v in products.items()};assert sum(map(len,encoded.values()))<16*1024*1024
assert O.parent.is_dir()and not O.exists()and all(not p.is_symlink()for p in[O,*O.parents]);O.mkdir()
for n,b in encoded.items():
 with(O/n).open('xb')as f:f.write(b)
print(json.dumps({'original':28846,'held':6149,'remaining':22697,'classes':summary['remaining_classes'],'subjects':summary['remaining_subjects'],'output_bytes':sum(map(len,encoded.values())),'seconds':time.monotonic()-start}))
