import importlib.util,pathlib,json,gzip,hashlib
p=pathlib.Path(__file__).with_name('inputs.py');s=importlib.util.spec_from_file_location('draftinput',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);passed=[]
def rejects(name,fn,fragment):
 try:fn()
 except ValueError as e:
  assert fragment in str(e);passed.append(name);return
 raise AssertionError(name+' unexpectedly accepted')
for path in ['/absolute','../escape','a/../escape','a//b','a/./b','a\\b']:
 rejects('unsafe-path:'+path,lambda path=path:m.safe_path(path),'Unsafe')
raw=gzip.compress(b'complete-body',mtime=0);d={'bytes':len(raw),'sha256':m.digest(raw),'uncompressed_bytes':13,'uncompressed_sha256':m.digest(b'complete-body')}
assert m.checked_decoded(raw,d)==b'complete-body';passed.append('whole-encoded-decoded-positive')
rejects('changed-encoded-body',lambda:m.checked_decoded(raw+b'x',d),'Encoded whole')
rejects('changed-declared-decoded-body',lambda:m.checked_decoded(raw,{**d,'uncompressed_sha256':'0'*64}),'Decoded whole')
rejects('declared-decoded-bound',lambda:m.checked_decoded(raw,{**d,'uncompressed_bytes':m.LIMIT+1}),'Declared decoded')
rejects('encoded-size-bound-before-reading',lambda:m.checked_encoded(raw,{**d,'bytes':m.LIMIT+1}),'Encoded ordinary')
r={'kind':'directed actual bounded reader and existing complete reconstruction controls','draft_sha256':m.digest(p.read_bytes()),'controls_sha256':m.digest(pathlib.Path(__file__).read_bytes()),'passed':passed,'count':len(passed)}
p.with_name('input-controls-result.json').write_text(json.dumps(r,sort_keys=True,separators=(',',':'))+'\n');print(json.dumps(r))
import subprocess
repo=pathlib.Path.cwd();commit='c6a26e1caba54e1b81a89fbda3a64fff56da323d';path='scripts/worldwide_gap_successor.py';expected='13da93f262d5fef68685d0cdc172ca568b836843cca833028f218da28a9031e1'
source=subprocess.check_output(['git','show',commit+':'+path]);desc={'bytes':30481,'sha256':expected}
assert m.ordinary_git(repo,commit,path,desc)==source;passed.append('actual-complete-immutable-existing-source-read')
for invalid_commit in ['main',commit[:8],commit.upper()]:
 rejects('immutable-commit-guard:'+invalid_commit,lambda invalid_commit=invalid_commit:m.ordinary_git(repo,invalid_commit,path,desc),'Exact lowercase40hex')
import tempfile,os
with tempfile.TemporaryDirectory(prefix='1261-real-symlink-control-') as tmp:
 fixture_repo=pathlib.Path(tmp);subprocess.check_call(['git','init','-q',tmp])
 os.symlink('ordinary-target',fixture_repo/'symlink-input');subprocess.check_call(['git','-C',tmp,'add','symlink-input'])
 env={**os.environ,'GIT_AUTHOR_NAME':'1261 directed control','GIT_AUTHOR_EMAIL':'control@example.invalid','GIT_COMMITTER_NAME':'1261 directed control','GIT_COMMITTER_EMAIL':'control@example.invalid'}
 tree=subprocess.check_output(['git','-C',tmp,'write-tree']).decode().strip();fixture=subprocess.check_output(['git','-C',tmp,'commit-tree',tree],input=b'actual ordinary-file mode negative control\n',env=env).decode().strip()
 rejects('actual-retained-Git-symlink-reader',lambda:m.ordinary_git(fixture_repo,fixture,'symlink-input',{'bytes':1,'sha256':'0'*64}),'ordinary committed')
def canonical(value):return (json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n').encode()
reconstruct,contact_key,bindings=m.existing_reconstructor(source,expected,canonical)
old=[{'id':'a','value':1},{'id':'b','value':2}];current=[{'id':'b','value':2},{'id':'c','value':3}]
delta={'original_count':2,'original_records_sha256':m.digest(canonical(old)),'current_count':2,'current_records_sha256':m.digest(canonical(current)),'removed_ids':['a'],'retained_count':1,'retained_ids_sha256':m.digest(canonical(['b'])),'upsert_records':[current[1]]}
assert reconstruct(old,delta)==current;passed.append('actual-existing-pure-lossless-reconstruction-positive')
rejects('complete-original-omission',lambda:reconstruct(old[:1],delta),'Original delta roster')
rejects('complete-original-duplicate',lambda:reconstruct(old+[old[0]],delta),'Original delta roster')
rejects('current-upsert-duplicate',lambda:reconstruct(old,{**delta,'upsert_records':[current[0]]}),'Duplicate reconstructed')
rejects('current-full-record-change',lambda:reconstruct(old,{**delta,'upsert_records':[{'id':'c','value':4}]}),'Current full record')
rejects('changed-complete-function-source',lambda:m.existing_reconstructor(source+b'\n',expected,canonical),'complete reconstruction source')
assert contact_key({'fragments':['f1','f2'],'dateline':False,'kind':'shared-edge','other':1})==m.digest(canonical([['f1','f2'],False,'shared-edge']));passed.append('exact-existing-contact-identity-semantics')
r.update(controls_sha256=m.digest(pathlib.Path(__file__).read_bytes()),passed=passed,count=len(passed),existing_executed_function_bindings=bindings,retained_real_symlink_fixture=fixture)
p.with_name('input-controls-result.json').write_text(json.dumps(r,sort_keys=True,separators=(',',':'))+'\n');print(json.dumps(r))
