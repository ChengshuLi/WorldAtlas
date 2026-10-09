"""Preserve authenticated original executed code/module bodies and Git path proofs.
Read sealed actual journals/facts; never run the old producers or import their code.
"""
import pathlib,json,gzip,hashlib,subprocess,base64,stat
W=pathlib.Path('/Users/chengshuli/world-atlas-workspace/.worldatlas-workspaces/8c86b01772c1c827/8f37144f48568734be4c4d84e67e369ea25708759c9cd4f3ba8016200850ca79/work')
P=W/'coordination/engineering/additive-native-gap-repair-20261008'
O=pathlib.Path('/Users/chengshuli/world-atlas-workspace/.cache/root1523-original-execution-code-custody-20261008');assert not O.exists();O.mkdir()
can=lambda v:(json.dumps(v,sort_keys=True,separators=(',',':'))+'\n').encode()
sha=lambda v:hashlib.sha256(v).hexdigest()
def git(*args):return subprocess.check_output(['git','-C',str(W),*args])
objects={};code={};modules={};records=[];runtime_refs=set()
def obj(kind,oid):
 key=(kind,oid)
 if key not in objects:
  raw=git('cat-file',kind,oid);assert hashlib.sha1((kind+' '+str(len(raw))).encode()+b'\0'+raw).hexdigest()==oid
  objects[key]={'type':kind,'oid':oid,'bytes':len(raw),'sha256':sha(raw),'body_base64':base64.b64encode(raw).decode()}
 return objects[key]
def path_proof(commit,path):
 cr=obj('commit',commit);raw=base64.b64decode(cr['body_base64']);tree=raw.splitlines()[0].decode().split(' ',1)[1];proof=[]
 parts=path.split('/');assert parts and all(p and p not in ['.','..'] for p in parts)
 for i,name in enumerate(parts):
  obj('tree',tree);row=git('ls-tree','-z',tree,'--',name);assert row.count(b'\0')==1
  fields,actual=row[:-1].split(b'\t',1);mode,kind,oid=fields.decode().split();assert actual.decode()==name
  proof.append({'tree':tree,'name':name,'mode':mode,'type':kind,'oid':oid})
  if i<len(parts)-1:assert kind=='tree';tree=oid
  else:assert kind=='blob' and mode in ['100644','100755'];blob=obj('blob',oid);return proof,blob,mode
journal_raw=(P/'complete-inventory-operating-journals.json.gz').read_bytes();journal=json.loads(gzip.decompress(journal_raw));rows=[r for phase in journal['phases'] for r in phase['journal']['completed']];assert len(rows)==160
for r in rows:
 assert r['qualified'] and r['exit']=={'code':0,'signal':None} and not r['owned_processes_remaining'] and r['refusal'] is None
 dest=W/r['destination'];pub=json.loads((dest/'publication.json').read_bytes());facts_raw=(dest/'facts.json').read_bytes();facts=json.loads(facts_raw)
 assert pub['complete'] and len(facts_raw)==pub['facts']['bytes'] and sha(facts_raw)==pub['facts']['sha256']
 assert facts['execution_commit']==r['execution_commit'];commit=facts['execution_commit'];runtime_refs.add((facts['runtime']['bytes'],facts['runtime']['sha256']))
 entries=[]
 for pin in facts['executed_code']:
  key=(commit,pin['path'])
  if key not in code:
   proof,blob,mode=path_proof(*key);assert blob['bytes']==pin['bytes'] and blob['sha256']==pin['sha256']
   code[key]={'commit':commit,'path':pin['path'],'mode':mode,'blob':blob['oid'],'bytes':pin['bytes'],'sha256':pin['sha256'],'git_path_proof':proof}
  value=code[key];assert value['bytes']==pin['bytes'] and value['sha256']==pin['sha256'];entries.append({'path':pin['path'],'blob':value['blob'],'sha256':pin['sha256']})
 for pin in facts['installed_modules']:
  key=(pin['path'],pin['sha256']);file=W/pin['path'];st=file.lstat();assert stat.S_ISREG(st.st_mode) and not file.is_symlink();raw=file.read_bytes();assert len(raw)==pin['bytes'] and sha(raw)==pin['sha256'];value={'path':pin['path'],'bytes':len(raw),'sha256':sha(raw),'observed_mode':oct(stat.S_IMODE(st.st_mode)),'body_base64':base64.b64encode(raw).decode()};assert key not in modules or modules[key]==value;modules[key]=value
 records.append({'destination':r['destination'],'execution_commit':commit,'facts_bytes':len(facts_raw),'facts_sha256':sha(facts_raw),'code':entries,'modules':facts['installed_modules'],'runtime':facts['runtime']})
assert len({r['destination'] for r in records})==160
runtime=pathlib.Path('/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node');h=hashlib.sha256()
with runtime.open('rb') as f:
 for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
assert runtime_refs=={(runtime.stat().st_size,h.hexdigest())};version=subprocess.check_output([str(runtime),'--version'],text=True).strip()
archive={'version':1,'kind':'complete-original-execution-code-and-module-custody','journal_sha256':sha(journal_raw),'execution_count':160,'execution_heads':sorted({r['execution_commit'] for r in records}),'code_bindings':list(code.values()),'git_objects':list(objects.values()),'installed_module_bodies':list(modules.values()),'executions':records,'runtime_restoration':{'bytes':runtime.stat().st_size,'sha256':h.hexdigest(),'observed_matching_version':version,'ordinary_evidence_body_included':False,'restoration':'External exact-version distribution must match full runtime byte/hash before reproduction.'},'limits':['Actual complete code/module bodies and Git commit/tree/blob path proofs preserved; no old producer was executed.','Merkle path objects preserve original private commit/code bindings; unrelated whole tree blobs and all parent history are not included here. Other original source/data inputs remain separately required.','This is archival reproducibility custody, not source authority, installed geography, or a worldwide repair.']}
raw=can(archive);assert len(raw)<33554432;packed=gzip.compress(raw,mtime=0);(O/'original-execution-code.json.gz').write_bytes(packed)
# Whole-body inverse for every alias, not sampled hashes.
v=json.loads(gzip.decompress(packed));assert v==archive
for o in v['git_objects']:
 body=base64.b64decode(o['body_base64'],validate=True);assert len(body)==o['bytes'] and sha(body)==o['sha256'] and hashlib.sha1((o['type']+' '+str(len(body))).encode()+b'\0'+body).hexdigest()==o['oid']
for m in v['installed_module_bodies']:
 body=base64.b64decode(m['body_base64'],validate=True);assert len(body)==m['bytes'] and sha(body)==m['sha256']
receipt={'version':1,'executions':160,'execution_heads':archive['execution_heads'],'unique_code_commit_path_bindings':len(code),'unique_git_objects':len(objects),'unique_module_bodies':len(modules),'whole_member_inverses_pass':True,'archive':{'path':'original-execution-code.json.gz','bytes':len(packed),'sha256':sha(packed),'uncompressed_bytes':len(raw),'uncompressed_sha256':sha(raw)},'runtime':archive['runtime_restoration'],'producer':{'bytes':pathlib.Path(__file__).stat().st_size,'sha256':sha(pathlib.Path(__file__).read_bytes())}}
(O/'receipt.json').write_bytes(can(receipt));print(json.dumps(receipt))
