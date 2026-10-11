#!/usr/bin/env bash
# Independent bounded resource controls only, not scientific or whole-delivery proof.
# Run: bash coordination/engineering/admitted-processing-limits-20261011/current-ci-allowance-controls.sh /absolute/path/to/WorldAtlas
# Imports the actual Python consumer, stubs only its upstream scientific operand
# producer/comparator and runtime file size, and executes its real Node admission.
# Exercises the exact on-disk cold guard source with bounded filesystem/Git stubs.
set -euo pipefail
cd "${1:?Provide the WorldAtlas checkout path}"
export GIT_NO_LAZY_FETCH=1 GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_TERMINAL_PROMPT=0 PYTHONDONTWRITEBYTECODE=1
python3 - <<'PY'
import os,pathlib,subprocess,json,gzip,hashlib,importlib.util,sys
from unittest.mock import patch
from types import SimpleNamespace
repo=pathlib.Path.cwd()
spec=importlib.util.spec_from_file_location('review_geography',repo/'scripts/run-geographic-check.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
real_check=subprocess.check_output;real_stat=pathlib.Path.stat;real_read=pathlib.Path.read_bytes
baseline='a'*40;candidate='b'*40;runtime=pathlib.Path(sys.executable).resolve();calls=[];reads=[]
def encode(v):return json.dumps(v,separators=(',',':')).encode()
def pin(name,b,**kw):return {'path':name,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),**kw}
def child(args,**kwargs):
 calls.append(args)
 if len(args)>2 and args[2]=='continuous':
  dest=pathlib.Path(args[7]);dest.mkdir()
  facts=encode({'executing_commit':baseline,'baseline_commit':baseline,'candidate_commit':candidate,'candidate_code_executed':False,'inverse':[]})
  decoded=encode({'kind':'complete-selected-continuous-operands-v1','plan':{'required_ids':[],'changed_ids':[],'source_bindings':[]},'baseline':{},'candidate':{}});body=gzip.compress(decoded)
  pub={'complete':True,'facts':pin('facts.json',facts),'operands':pin('operands.json.gz',body,decoded_bytes=len(decoded),decoded_sha256=hashlib.sha256(decoded).hexdigest())}
  for name,raw in [('publication.json',encode(pub)),('facts.json',facts),('operands.json.gz',body)]:
   f=dest/name;f.write_bytes(raw);f.chmod(0o644)
  return encode({'kind':'trusted-selected-continuous-comparison-v1','candidate_code_executed':False,'publication':pub,'changed_ids':[],'complete_owners':0})
 return real_check(args,**kwargs)
def stat(path,*a,**kw):
 if path==runtime:return SimpleNamespace(st_size=300*1024**2)
 return real_stat(path,*a,**kw)
def read(path,*a,**kw):
 if 'trusted-selected-footprints-' in str(path):reads.append(str(path))
 return real_read(path,*a,**kw)
detector=SimpleNamespace(compare=lambda before,after:{'changed_location_ids':[],'status':'no-new-regression','regressions':0})
with patch.object(subprocess,'check_output',side_effect=child),patch.object(pathlib.Path,'stat',stat),patch.object(pathlib.Path,'read_bytes',read):
 result=m.selected_continuous(repo,baseline,candidate,detector)
 assert result['status']=='no-new-regression' and len(reads)==3 and len(calls)==2
 print('PASS actual selected_continuous: simulated 300 MiB runtime; real fresh Node admission; bounded fixture consumed')
 reads.clear();calls.clear()
 with patch.dict(os.environ,{'WORLDATLAS_CONCURRENT_RESERVED_BYTES':'9007199254740991'}):
  try:m.selected_continuous(repo,baseline,candidate,detector);raise AssertionError('accepted exhausted resource')
  except subprocess.CalledProcessError:pass
 assert reads==[] and len(calls)==2
 print('PASS actual selected_continuous: exhausted concurrent headroom refuses before output body reads')
PY
node --input-type=module <<'JS'
import fs from 'node:fs';import vm from 'node:vm';import assert from 'node:assert/strict';
const text=fs.readFileSync('coordination/engineering/selected-geography-effective-prevention-20261009/selected-continuous-entry.mjs','utf8');
const guard=text.slice(text.indexOf('function guard('),text.indexOf('\nexport async function coordinateStage'));
const GiB=1024**3,MiB=1024**2,head='a'.repeat(40);
const run=(phaseBytes,reserved='0')=>{
 let crossed=false;
 const sandbox={repo:'/repo',trusted:head,ROOT:'/repo',CODE:['one.mjs'],FILE:32*MiB,path:{join:(...p)=>p.join('/')},commit:()=>true,ordinaryParents:()=>{},demand:(v,m)=>{if(!v)throw Error(m)},process:{execPath:'/node',env:{WORLDATLAS_CONCURRENT_RESERVED_BYTES:reserved},availableMemory:()=>2*phaseBytes+2*GiB+768*MiB},fs:{realpathSync:p=>p,lstatSync:()=>({isFile:()=>true,isSymbolicLink:()=>false,size:MiB}),statSync:()=>({size:300*MiB})},execFileSync:(cmd,args)=>{if(args.includes('rev-parse'))return Buffer.from(head);crossed=true;throw Error('reached immutable body authentication');}};
 try{vm.runInNewContext(`(${guard})(repo,trusted)`,sandbox);throw Error('unexpected completion')}catch(e){return {message:e.message,crossed}}
};
assert.deepEqual(run(512*MiB),{message:'reached immutable body authentication',crossed:true});
assert.deepEqual(run(256*MiB),{message:'Cold code/runtime admission before code body opens',crossed:false});
assert.deepEqual(run(512*MiB,String(512*MiB)),{message:'Cold code/runtime admission before code body opens',crossed:false});
assert.deepEqual(run(512*MiB,'-1'),{message:'Invalid cold current resource observations',crossed:false});
console.log('PASS actual cold guard: >256 MiB frame admitted under 512; small/concurrent/invalid supply refuses before body authentication');
JS
