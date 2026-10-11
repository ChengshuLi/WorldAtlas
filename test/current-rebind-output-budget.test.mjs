import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
import {ImmutableReader} from '../scripts/check-effective-geographic-regression.mjs';
import {prepareCurrentRebindDestination,writeCurrentRebindProducts,boundedCurrentRebindProductBytes} from '../coordination/engineering/additive-native-composition-20261009/capture-current-rebind.mjs';
import {valueBytes,admitCurrentRebindOutputFrame,retainCurrentRebindPhasePeak} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
const root=path.resolve(fileURLToPath(new URL('../',import.meta.url))),MiB=1048576;
const reader=()=>new ImmutableReader(root,'a'.repeat(40),{runtimeBytes:11,executionBytes:13,metadataBytes:17,outputBytes:4*MiB,allowance:{phaseBytes:256*MiB,rssBytes:1024*MiB}});
function fixture(t){
 const cache=path.join(root,'.cache');fs.mkdirSync(cache,{recursive:true});
 const dir=fs.mkdtempSync(path.join(cache,'rebind-output-control-'));t.after(()=>fs.rmSync(dir,{recursive:true}));
 const destination=path.join(dir,'products');return {dir,destination,token:prepareCurrentRebindDestination(root,destination)};
}
const products=n=>({request:{payload:'x'.repeat(n)},result:{native:[]},facts:{acquisition:[]},publication:{kind:'synthetic-writer-control'}});
const size=b=>Object.values(b).reduce((n,v)=>n+valueBytes(v).length,0);

test('complete output frame charges seven representations before production',()=>{
 for(const output of [4*MiB,8*MiB]){
  const r=reader(),expected=11+13+17+7*output;
  assert.equal(admitCurrentRebindOutputFrame(r,{output_bytes:output,complete_phase_bytes:expected}),expected);
  assert.equal(r.outputBytes,7*output);assert.equal(r.metadataBytes,17);
  assert.throws(()=>admitCurrentRebindOutputFrame(reader(),{output_bytes:output,complete_phase_bytes:expected-1}),/before products/);
 }
 for(const output of [0,-1,1.5,Infinity,Number.MAX_SAFE_INTEGER])assert.throws(()=>admitCurrentRebindOutputFrame(reader(),{output_bytes:output,complete_phase_bytes:256*MiB}),/Bounded/);
 const r=reader();r.metadataBytes=256*MiB-7*8*MiB;
 assert.throws(()=>admitCurrentRebindOutputFrame(r,{output_bytes:8*MiB,complete_phase_bytes:256*MiB}),/complete phase/);
});
test('consumer keeps final-result peak after a smaller or larger reopen-frame reset',()=>{
 for(const reopen of [1,80*MiB]){
  const r=reader(),outputPeak=admitCurrentRebindOutputFrame(r,{output_bytes:8*MiB,complete_phase_bytes:256*MiB});
  r.outputBytes=1;r.metadataBytes=reopen;r.phase();const reopened=r.used;
  const phases=[{complete_phase_bytes:19*MiB}];
  assert.equal(retainCurrentRebindPhasePeak(r,23*MiB,outputPeak,phases),Math.max(outputPeak,reopened));
  assert.equal(outputPeak,56*MiB+41);assert.equal(r.used>=outputPeak,true);
 }
});
test('bounded counter matches canonical Unicode, escapes, numbers and nested products',()=>{
 const b={request:{'é\u0000': ['quote"', '\\', '\b\f\n\r\t', '\u0001', '雪😀', '\ud800', '\udfff', -0, 1e21, true, null]},result:{z:[],a:{}} ,facts:{},publication:{}};
 const exact=size(b);assert.equal(boundedCurrentRebindProductBytes(b,exact),exact);
 assert.throws(()=>boundedCurrentRebindProductBytes(b,exact-1),/before writes/);
 for(const value of [NaN,Infinity,undefined])assert.throws(()=>boundedCurrentRebindProductBytes({request:value},1024),/canonical product value/);
});
test('actual writer accepts a four-product union above the former 4 MiB ceiling',t=>{
 const f=fixture(t),b=products(4*MiB+1024),total=size(b);
 admitCurrentRebindOutputFrame(reader(),{output_bytes:8*MiB,complete_phase_bytes:256*MiB});
 assert.equal(writeCurrentRebindProducts(f.token,b,8*MiB),total);
 assert.deepEqual(fs.readdirSync(f.destination).sort(),['facts.json','publication.json','request.json','result.json']);
 for(const [name,v] of Object.entries(b))assert.deepEqual(fs.readFileSync(path.join(f.destination,name+'.json')),valueBytes(v));
});
test('union boundary is exact and over-limit failure preserves an absent destination',t=>{
 const base=products(0),overhead=size(base),b=products(8*MiB-overhead),exact=fixture(t);
 assert.equal(size(b),8*MiB);assert.equal(writeCurrentRebindProducts(exact.token,b,8*MiB),8*MiB);
 const tooSmall=fixture(t);
 assert.throws(()=>writeCurrentRebindProducts(tooSmall.token,b,8*MiB-1),/before writes/);
 assert.equal(fs.existsSync(tooSmall.destination),false);
 const old=fixture(t);assert.throws(()=>writeCurrentRebindProducts(old.token,b,4*MiB),/before writes/);
 assert.equal(fs.existsSync(old.destination),false);
});
test('all four products contribute and collision or symlink never changes originals',t=>{
 const f=fixture(t),b=products(64),total=size(b);
 assert.throws(()=>writeCurrentRebindProducts(f.token,b,valueBytes(b.request).length),/before writes/);
 assert.equal(fs.existsSync(f.destination),false);
 fs.mkdirSync(f.destination);fs.writeFileSync(path.join(f.destination,'sentinel'),'original');
 assert.throws(()=>writeCurrentRebindProducts(f.token,b,total),/Destination appeared/);
 assert.equal(fs.readFileSync(path.join(f.destination,'sentinel'),'utf8'),'original');
 const s=fixture(t);fs.symlinkSync(f.destination,s.destination);
 assert.throws(()=>writeCurrentRebindProducts(s.token,b,total),/Destination appeared/);
 assert.equal(fs.readFileSync(path.join(f.destination,'sentinel'),'utf8'),'original');
 assert.throws(()=>writeCurrentRebindProducts({},b,total),/prepared/);
 assert.throws(()=>writeCurrentRebindProducts(f.token,{request:{}},total),/Complete bounded/);
});
test('actual supervisor reads bounded products only after complete union admission',t=>{
 const base=path.join(root,'coordination/engineering/additive-native-composition-20261009'),f=fixture(t),b=products(4*MiB+1024);
 writeCurrentRebindProducts(f.token,b,8*MiB);
 assert.match(fs.readFileSync(path.join(base,'run-current-rebind.mjs'),'utf8'),/plan\.limits\.output_bytes>0&&plan\.limits\.output_bytes<=8388608/);
 const code=`import pathlib,importlib.util,hashlib
from unittest.mock import patch
p=pathlib.Path(${JSON.stringify(base)})
spec=importlib.util.spec_from_file_location('rebind_supervisor',p/'supervise-current-rebind.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
output=pathlib.Path(${JSON.stringify(f.destination)})
actual=m.current_rebind_product_hashes(output,8*1048576)
assert actual=={name:hashlib.sha256((output/(name+'.json')).read_bytes()).hexdigest() for name in ['request','facts','result','publication']}
for bound in [4*1048576,True,0,8*1048576+1]:
 with patch.object(pathlib.Path,'read_bytes',side_effect=RuntimeError('opened before admission')):
  try: m.current_rebind_product_hashes(output,bound)
  except AssertionError: pass
  else: raise AssertionError('bad bound accepted')
assert m.contract.OUTPUT==12*1048576 and m.contract.PHASE==256*1048576
`;
 const result=spawnSync(process.env.PYTHON??'python3',['-I','-B','-c',code],{encoding:'utf8',timeout:10000});
 assert.equal(result.status,0,result.stderr);
});
