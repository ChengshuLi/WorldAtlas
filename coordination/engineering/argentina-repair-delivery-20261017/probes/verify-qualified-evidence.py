"""Verify qualified positive coverage preserves all whole original operands.
Usage: python verify-qualified-evidence.py REPO EXACT_METHOD_COMMIT FRESH_OUTPUT
"""
import collections,gzip,hashlib,json,os,pathlib,subprocess,sys,time
assert len(sys.argv)==4 and __debug__
W=pathlib.Path(sys.argv[1]).absolute();C=sys.argv[2];O=pathlib.Path(sys.argv[3]).absolute();H='d4968ddc37aa3aa6105e9610c9e6fadbb368ba14';P='coordination/engineering/argentina-repair-delivery-20261017'
assert len(C)==40 and all(c in '0123456789abcdef'for c in C)and O.parent.is_dir()and not O.exists()and all(not p.is_symlink()for root in(W,O)for p in(root,*root.parents))
sha=lambda b:hashlib.sha256(b).hexdigest();inputs={};started=time.monotonic();total=0;PHASE_BYTES=512*1024*1024;OUTPUT_BYTES=64*1024*1024
env={**os.environ,'GIT_NO_LAZY_FETCH':'1','GIT_NO_REPLACE_OBJECTS':'1','GIT_TERMINAL_PROMPT':'0'}
def git(*args):return subprocess.check_output(['git','-c','protocol.allow=never','-C',str(W),*args],env=env,timeout=30)
def read(p,c=C):
 global total
 assert not p.startswith('/')and all(x not in('','.','..')for x in p.split('/'))and time.monotonic()-started<300
 row=git('ls-tree','-z',c,'--',p).rstrip(b'\0');meta,name=row.split(b'\t');mode,kind,oid=meta.decode().split();assert mode=='100644'and kind=='blob'and name.decode()==p
 size=int(git('cat-file','-s',oid));assert 0<size<=128*1024*1024;b=git('cat-file','blob',oid);assert len(b)==size and hashlib.sha1(b'blob '+str(size).encode()+b'\0'+b).hexdigest()==oid
 pin={'path':p,'commit':c,'mode':mode,'git_blob_oid':oid,'bytes':size,'sha256':sha(b)}
 if p.endswith('.gz'):
  import io
  with gzip.GzipFile(fileobj=io.BytesIO(b))as f:d=f.read(128*1024*1024+1)
  assert len(d)<=128*1024*1024;pin.update(decoded_bytes=len(d),decoded_sha256=sha(d));b=d
 if(c,p)not in inputs:total+=size+pin.get('decoded_bytes',0)
 assert total<=PHASE_BYTES;inputs[c,p]=pin;return b
js=lambda p,c=C:json.loads(read(p,c))
def pin(p,c=C):read(p,c);return inputs[c,p]
assert read(P+'/probes/verify-qualified-evidence.py')==pathlib.Path(__file__).read_bytes()
a=js(P+'/native-inputs-001/source-evidence.json');b=js(P+'/native-inputs-002/source-evidence.json');old={t['id']:t for t in a['targets']};new={t['id']:t for t in b['targets']};assert len(old)==len(a['targets'])==111 and len(new)==len(b['targets'])==110 and set(new)<=set(old)
assert {k:v for k,v in a.items()if k!='targets'}=={k:v for k,v in b.items()if k!='targets'}
for ident,t in new.items():assert {k:v for k,v in t.items()if k!='coverage_rows'}=={k:v for k,v in old[ident].items()if k!='coverage_rows'}
patch=js(P+'/native-config-002/native-qualified-patch.json');expected={(r['y'],x,o)for r in patch['rows']for u,v,o in r['runs']for x in range(u,v)};actual=set();classes={}
for t in new.values():
 for r in t.get('coverage_rows',[]):
  for u,v,c in r['runs']:
   for x in range(u,v):
    k=(r['y'],x,t['pixelIndex']);assert k not in actual;actual.add(k);classes[k]=c
assert actual==expected and len(actual)==22697
physical=js(P+'/physical-001/whole-target-support.json');assert len(physical['results'])==131
rows=[]
for ident,t in old.items():
 before=t['territorial_exclusions'];after=new.get(ident,{}).get('territorial_exclusions',[])
 if ident in new:assert before==after
 rows.append({'id':ident,'pixelIndex':t['pixelIndex'],'old_negative_instances':len(before),'new_negative_instances':len(after),'whole_original_negative_fields_equal':ident not in new or before==after,'positive_target_retained':ident in new})
result={'kind':'Argentina-exact-qualified-source-evidence-preservation','whole_document_non_target_fields_equal':True,'all_surviving_target_non_coverage_fields_equal':True,'all_surviving_whole_negative_instances_equal':True,'old_positive_targets':len(old),'new_positive_targets':len(new),'removed_positive_targets':sorted(set(old)-set(new)),'original_negative_instances':sum(len(t['territorial_exclusions'])for t in old.values()),'qualified_negative_instances':sum(len(t['territorial_exclusions'])for t in new.values()),'complete_foreign_families':[f['source_id']for f in b['territorial_exclusion_sources']],'qualified_coverage_cells':len(actual),'coverage_classes':dict(collections.Counter(classes.values())),'whole_physical_members':len(physical['results']),'whole_physical_issues':sum(len(r['issues'])for r in physical['results']),'whole_physical_members_with_issues':sum(bool(r['issues'])for r in physical['results']),'targets':rows,'inputs':list(inputs.values()),'limits':['Only positive requested coverage was narrowed and one held-only positive target removed. The old whole evidence is retained unchanged.','Complete domestic cohort, original source families, whole physical evidence and every surviving whole foreign negative remain literal.','Actual source/native authority and selected delivery remain separate gates.']}
body=(json.dumps(result,separators=(',',':'))+'\n').encode();assert len(body)<4*1024*1024 and not O.exists();O.mkdir()
with(O/'qualified-evidence-preservation.json').open('xb')as f:f.write(body)
print(json.dumps({k:result[k]for k in ['old_positive_targets','new_positive_targets','original_negative_instances','qualified_negative_instances','qualified_coverage_cells','whole_physical_members','whole_physical_issues']}))
