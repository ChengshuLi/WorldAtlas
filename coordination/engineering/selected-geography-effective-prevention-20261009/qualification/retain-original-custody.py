import pathlib,json,subprocess,hashlib,base64,gzip
ROOT=pathlib.Path.cwd();P=ROOT/'coordination/engineering/selected-geography-effective-prevention-20261009/qualification'
def git(*args):return subprocess.check_output(['git',*args])
def sha(b):return hashlib.sha256(b).hexdigest()
head=git('rev-parse','HEAD').decode().strip();current={}
for line in git('ls-tree','-rz',head).split(b'\0'):
 if not line:continue
 meta,path=line.split(b'\t');mode,kind,oid=meta.decode().split()
 if kind=='blob':current.setdefault(oid,[]).append({'commit':head,'path':path.decode(),'mode':mode,'git_blob_oid':oid})
objects={};bindings=[]
def retain(kind,oid):
 if oid in objects:return
 raw=git('cat-file',kind,oid);assert hashlib.sha1((kind+' '+str(len(raw))+'\0').encode()+raw).hexdigest()==oid
 objects[oid]={'kind':kind,'bytes':len(raw),'sha256':sha(raw),'base64':base64.b64encode(raw).decode()}
def pin(p,role):
 version=p['commit'];name=p['path'];line=git('ls-tree','-z',version,'--',name);meta,found=line.rstrip(b'\0').split(b'\t');mode,kind,oid=meta.decode().split();assert found.decode()==name and kind=='blob' and mode==p['mode'] and oid==p['git_blob_oid']
 raw=git('cat-file','blob',oid);assert len(raw)==p['bytes'];assert 'sha256' not in p or sha(raw)==p['sha256']
 retain('commit',version);tree=git('rev-parse',version+'^{tree}').decode().strip();retain('tree',tree);proof=[tree];parts=name.split('/')
 for i in range(len(parts)-1):
  tree=git('rev-parse',version+':'+ '/'.join(parts[:i+1])).decode().strip();retain('tree',tree);proof.append(tree)
 # Every executing code body and every private data body is retained literally.
 # Published complete data originals use exact whole-blob aliases, never samples.
 aliases=[a for a in current.get(oid,[]) if a['mode']==mode]
 if role=='execution-code' or not aliases:retain('blob',oid);custody={'whole_object':oid}
 else:custody={'published_whole_alias':aliases[0]}
 bindings.append({'role':role,'original_pin':p,'merkle_tree_path':proof,**custody})
for run in ['bare-v8','effective-v8']:
 facts=json.loads((P/run/'facts.json').read_bytes())
 for p in facts['execution_code']:pin(p,'execution-code')
 for p in facts['inputs']:pin(p,'consumed-input' if p.get('whole_body_consumed') else 'declared-descriptor')
value={'version':1,'kind':'complete-qualified-coordinate-execution-custody','authoring_commit':head,'objects':objects,'bindings':bindings,'limits':['Git tree/commit objects prove each original path; unrelated history/tree member payloads are not retained.','Published whole-source bodies remain complete immutable Git data aliases; this archive does not claim to duplicate the world source bank.','Installed complete Node/Git executable identities remain in original runtime facts; runtime binaries are not ordinary evidence descriptors.','No original producer or geography method was rerun.']}
raw=(json.dumps(value,separators=(',',':'),sort_keys=True)+'\n').encode();assert len(raw)<=33554432
encoded=gzip.compress(raw,mtime=0);assert len(encoded)<=33554432;(P/'original-execution-custody.json.gz').write_bytes(encoded)
(P/'original-execution-custody-receipt.json').write_text(json.dumps({'kind':value['kind'],'authoring_commit':head,'bindings':len(bindings),'whole_objects':len(objects),'encoded_bytes':len(encoded),'encoded_sha256':sha(encoded),'decoded_bytes':len(raw),'decoded_sha256':sha(raw),'retained_original_object_bytes':sum(o['bytes'] for o in objects.values()),'limits':value['limits']},indent=2)+'\n')
print(json.dumps({'bindings':len(bindings),'objects':len(objects),'encoded':len(encoded),'decoded':len(raw)}))
