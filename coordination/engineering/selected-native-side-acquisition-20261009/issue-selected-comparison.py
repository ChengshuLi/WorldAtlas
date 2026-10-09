"""Issue a frozen trusted program closure and read-only comparison command; never run it."""
import argparse,hashlib,json,pathlib,subprocess,sys,os
p=argparse.ArgumentParser();p.add_argument('--repo',required=True);p.add_argument('--code-head',required=True);p.add_argument('--baseline',required=True);p.add_argument('--candidate',required=True);p.add_argument('--destination',required=True);p.add_argument('--node',required=True);p.add_argument('--parent-runtime',required=True);a=p.parse_args()
for c in [a.code_head,a.baseline,a.candidate]:assert len(c)==40 and all(x in '0123456789abcdef' for x in c)
repo=pathlib.Path(a.repo).resolve();dest=pathlib.Path(a.destination).absolute();assert not dest.exists()
for ancestor in [dest,*dest.parents]:assert not ancestor.is_symlink()
paths=['package.json','scripts/check-effective-geographic-regression.mjs','scripts/run-geographic-check.py','scripts/check-geographic-regression.py','scripts/evidence/immutable.py','scripts/evidence/geometry.py','scripts/ellipsoidal_area.py','src/ownership-codec.js','requirements.txt','coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs','coordination/engineering/selected-geography-effective-prevention-20261009/selected-continuous-entry.mjs']
sha=lambda b:hashlib.sha256(b).hexdigest()
def git(*args):return subprocess.check_output(['git','-C',str(repo),*args])
plan=[]
for name in paths:
 row=git('ls-tree','-z',a.code_head,'--',name).decode();assert row.endswith('\t'+name+'\0');mode,kind,oid=row.split('\t')[0].split();assert mode=='100644' and kind=='blob'
 size=int(git('cat-file','-s',oid));assert 0<size<=32*1024*1024;plan.append({'path':name,'mode':mode,'git_blob_oid':oid,'bytes':size})
# This issuer retains only a small source-code output. Installed runtimes are
# independently stat-admitted whole bodies, not ordinary 32-MiB input members.
runtime=[]
for name in [a.node,a.parent_runtime]:
 path=pathlib.Path(name).resolve();st=path.stat();assert path.is_file() and st.st_size>0;runtime.append({'path':str(path),'bytes':st.st_size,'mode':st.st_mode&0o777})
assert sum(r['bytes'] for r in runtime)+sum(r['bytes'] for r in plan)*2+8*1024*1024+4*1024*1024<=256*1024*1024
for r in runtime:
 h=hashlib.sha256()
 with open(r['path'],'rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 r['sha256']=h.hexdigest()
dest.mkdir(parents=True)
for row in plan:
 body=git('cat-file','blob',row['git_blob_oid']);assert len(body)==row['bytes'];assert hashlib.sha1(('blob '+str(len(body))+'\0').encode()+body).hexdigest()==row['git_blob_oid'];row['sha256']=sha(body)
 file=dest/row['path'];file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(body);os.chmod(file,0o644)
request={'kind':'frozen-trusted-native-comparison-program','code_head':a.code_head,'baseline':a.baseline,'candidate':a.candidate,'repo':str(repo),'source_files':plan,'execution_runtimes':runtime,'command':[runtime[0]['path'],str(dest/'scripts/check-effective-geographic-regression.mjs'),str(repo),a.baseline,a.candidate,runtime[1]['path']],'report_reserve_bytes':4*1024*1024,'candidate_code_executed':False,'comparison_launched':False,'required_clean_environment':['NODE_OPTIONS','NODE_PATH'],'scope':'Full inspectSelected affected-row comparison, including all original selected ownership metadata/rows/containing members and unchanged interval comparison; not scientific reconstruction or continuous polygon requalification.','limits':['This file issues only authenticated trusted source and command; it is not execution, operating qualification, geographic approval or activation.','The checker independently admits actual Git implementation/runtime/code/custody/input/output per real phase at execution. Root must supervise the later run under an honestly issued local envelope and fresh capacity.']}
(dest/'issued-command.json').write_text(json.dumps(request,indent=2)+'\n');print(json.dumps({'destination':str(dest),'code_files':len(plan),'whole_code_bytes':sum(r['bytes'] for r in plan),'launched':False}))
