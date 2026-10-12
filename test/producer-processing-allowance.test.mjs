import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {processingAllowance,ImmutableReader} from '../scripts/check-effective-geographic-regression.mjs';
import {prepareCurrentRebindDestination,writeCurrentRebindProducts} from '../coordination/engineering/additive-native-composition-20261009/capture-current-rebind.mjs';
import {validateCurrentRebindLimits,currentRebindLogLimits,valueBytes,admitCurrentRebindOutputFrame} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
const MiB=1024**2,GiB=1024**3,root=path.resolve(import.meta.dirname,'..');
const grant=()=>processingAllowance({availableBytes:8*GiB,concurrentReservedBytes:GiB,phaseBytes:512*MiB,rssBytes:GiB});
const reader=allowance=>new ImmutableReader(root,'a'.repeat(40),{runtimeBytes:1,executionBytes:1,metadataBytes:300*MiB,outputBytes:1,allowance});
test('larger finite output allowance preserves actual scientific/result bytes and whole-member bounds',t=>{
 const cache=path.join(root,'.cache');fs.mkdirSync(cache,{recursive:true});const dir=fs.mkdtempSync(path.join(cache,'processing-budget-'));t.after(()=>fs.rmSync(dir,{recursive:true}));
 const products={request:{payload:'x'.repeat(13*MiB)},result:{rows:[{component:'unchanged',cells:97}]},facts:{},publication:{}};
 const original=valueBytes(products.result);
 for(const output_bytes of [14*MiB,16*MiB]){
  const r=reader(grant());admitCurrentRebindOutputFrame(r,{output_bytes,complete_phase_bytes:r.phaseLimit});
  const target=path.join(dir,String(output_bytes));writeCurrentRebindProducts(prepareCurrentRebindDestination(root,target),products,output_bytes);
  assert.deepEqual(fs.readFileSync(path.join(target,'result.json')),original);
 }
 assert.throws(()=>admitCurrentRebindOutputFrame(reader(grant()),{output_bytes:100*MiB,complete_phase_bytes:512*MiB}),/complete phase/);
});
test('real Python admission honors requested RAM, concurrent reservations, cgroups and measured disk growth',()=>{
 const code=`import pathlib,importlib.util,copy
from unittest.mock import patch
p=pathlib.Path(${JSON.stringify(path.join(root,'coordination/engineering/additive-native-composition-20261009'))})
def load(name):
 spec=importlib.util.spec_from_file_location(name.replace('-','_'),p/(name+'.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
s=load('supervise-current-rebind');issuer=load('issue-current-rebind-execution');G=1024**3;M=1024**2
e={'meminfo':'MemAvailable: 8388608 kB\\nMemTotal: 10485760 kB\\n','concurrent_reserved_bytes':G,'observed_aggregate_rss_bytes':G,'ancestors':[], 'limits':'Max address space unlimited unlimited bytes\\nMax data size unlimited unlimited bytes\\n','status':'VmSize: 1000 kB\\nVmData: 1000 kB\\n'}
q=s.evaluate_linux_supply(e,2*G+768*M);assert q['required_bytes']==2*G+768*M
limits=issuer.automatic_limits(q);assert limits['complete_phase_bytes']>256*M and limits['output_bytes']>8*M
assert s.contract.runtime_logs(limits)['samples.jsonl']==4*M
legacy={k:v for k,v in limits.items() if k not in ('stdout_bytes','stderr_bytes','monitor_bytes')}
assert s.contract.retained_output(legacy)==legacy['output_bytes']+4*M
expanded=dict(legacy,stdout_bytes=16384,stderr_bytes=M,monitor_bytes=8*M,wall_seconds=3600)
assert s.contract.runtime_logs(expanded)['samples.jsonl']==8*M
assert s.contract.retained_output(expanded)>=expanded['output_bytes']+9*M+16384+2*M
try:s.contract.execution_limits(dict(expanded,monitor_bytes=32*M+1))
except AssertionError:pass
else:raise AssertionError('whole runtime log security bound ignored')
vm='Mach Virtual Memory Statistics: (page size of 4096 bytes)\\nPages free: 2097152.\\nPages inactive: 0.\\nPages speculative: 0.\\n'
with patch.object(s.sys,'platform','darwin'),patch.object(s.subprocess,'check_output',return_value=vm):
 d=s.fresh_host_supply({'WORLDATLAS_CONCURRENT_RESERVED_BYTES':str(G)},2*G+768*M)
 assert d['residual_reported_bytes']==5*G
 assert issuer.automatic_limits(d)['rss_bytes']==(5*G-768*M)//2
for bad in [dict(e,concurrent_reserved_bytes=7*G),dict(e,ancestors=[{'path':'cgroup','maximum':str(2*G),'current':str(G)}])]:
 try:s.evaluate_linux_supply(bad,2*G+768*M)
 except AssertionError:pass
 else:raise AssertionError('unsafe memory admitted')
stock={'limits':{'minimumFree':10*G},'freeBytes':14*G,'entries':[{'path':'/owned','slot':'work','status':'ready','reservation':G},{'path':'/other','slot':'work','status':'ready','reservation':2*G}], 'worktrees':[{'path':'/owned','managed':True,'bytes':3*G},{'path':'/other','managed':True,'bytes':G}]}
s.require_stock_growth(stock,pathlib.Path('/owned'),32*M)
for bad in [dict(stock,freeBytes=10*G+16*M),dict(stock,freeBytes=11*G)]:
 try:s.require_stock_growth(bad,pathlib.Path('/owned'),32*M)
 except AssertionError:pass
 else:raise AssertionError('other reservation or disk growth ignored')
for bad in [True,0,-1,1.5,9007199254740992]:
 x=dict(limits,output_bytes=bad)
 try:s.contract.execution_limits(x)
 except AssertionError:pass
 else:raise AssertionError('invalid issued limit accepted')
`;
 const result=spawnSync('python3',['-I','-B','-c',code],{encoding:'utf8',timeout:10000});assert.equal(result.status,0,result.stderr);
});

test('issued runtime log and monitoring budgets retain legacy defaults and accept finite configuration',()=>{
 const old={complete_phase_bytes:512*MiB,descriptors:512,output_bytes:8*MiB,rss_bytes:MiB*768,sampled_stop_bytes:MiB*672,wall_seconds:1200};
 assert.equal(validateCurrentRebindLimits(old),old);assert.deepEqual(currentRebindLogLimits(old),{stdout:8192,stderr:40960,monitor:MiB});
 const larger={...old,wall_seconds:3600,stdout_bytes:16384,stderr_bytes:MiB,monitor_bytes:8*MiB};
 assert.equal(validateCurrentRebindLimits(larger),larger);assert.equal(currentRebindLogLimits(larger).monitor,8*MiB);
 for(const monitor_bytes of [0,-1,Infinity,32*MiB+1])assert.throws(()=>validateCurrentRebindLimits({...larger,monitor_bytes}));
 assert.throws(()=>validateCurrentRebindLimits({...larger,unissued:1}));
});
