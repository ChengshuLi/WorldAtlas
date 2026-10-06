// Normalize control headers only; retain the original experiments and vintages.
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {requirePlainExecution,committedPreparationFiles,candidateBudget} from '../../../scripts/native-ownership/native-preparation-guards.mjs';

requirePlainExecution();assert.equal(process.argv.length,2,'No arguments: fixed immutable original control proof');
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../..');
const prefix='coordination/engineering/iran-pakistan-offline-integration-991-20261006-local22';
const head=execFileSync('git',['-C',root,'rev-parse','HEAD'],{encoding:'utf8'}).trim();
const producer=committedPreparationFiles(root,head,[prefix+'/normalize-repack-controls.mjs','scripts/native-ownership/native-preparation-guards.mjs','package.json','package-lock.json']);
const ledger=candidateBudget([]),inputs=new Map(),MAX=32*1024*1024;
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const originalExecution='2188a6bf9a6702fccce719f36a7e40f3f53aa932';
const originalProofCommit='99e75a1fe5836fcb26e1fad0c505170ad8464111';
const proofPath=prefix+'/repacked-release-v2/verification.json';
function read(commit,name,pin,{actual=false}={}){
  assert.match(commit,/^[a-f0-9]{40}$/);assert.ok(!path.posix.isAbsolute(name)&&name.split('/').every(p=>/^[a-zA-Z0-9._-]+$/.test(p)&&p!=='.'&&p!=='..'));
  const key=commit+':'+name,tree=execFileSync('git',['-C',root,'ls-tree','-z',commit,'--',name],{encoding:'utf8'});
  assert.ok(/^100644 blob /.test(tree)&&tree.slice(tree.indexOf('\t')+1)===name+'\0','Ordinary committed input required');
  const size=Number(execFileSync('git',['-C',root,'cat-file','-s',key],{encoding:'utf8'}));assert.ok(size<=MAX);
  const raw=execFileSync('git',['-C',root,'show',key],{maxBuffer:MAX});assert.equal(raw.length,size);
  const descriptor={commit,path:name,bytes:size,sha256:sha(raw)};
  if(pin){assert.equal(size,pin.bytes);assert.equal(descriptor.sha256,pin.sha256);}
  if(inputs.has(key))assert.deepEqual(inputs.get(key),descriptor);else{ledger.add(descriptor);inputs.set(key,descriptor);}
  if(actual){const filename=path.join(root,name),stat=fs.lstatSync(filename);assert.ok(stat.isFile()&&fs.realpathSync(filename)===filename);assert.ok(fs.readFileSync(filename).equals(raw),'Actual original input differs: '+name);
    const current=execFileSync('git',['-C',root,'show',head+':'+name],{maxBuffer:MAX});assert.ok(current.equals(raw),'Current committed original differs: '+name);}
  return {raw,pin:descriptor};
}
for(const pin of producer)read(head,pin.path,pin,{actual:true});
const proofInput=read(originalProofCommit,proofPath,{bytes:283719,sha256:'c33bc34c9c5957cbe663c5ea558d827a170b64602d45a131d38cacab7535bd45'},{actual:true});
const proof=JSON.parse(proofInput.raw);assert.equal(proof.execution_commit,originalExecution);
assert.equal(proof.memberships,84833);assert.equal(proof.ordered_membership_rows_sha256,'3b50aeb11833d8a5a4088d5a520b36eb7f0c0764814e713a794598b86b80cc85');
// Bind the historical executed code closure without rerunning those experiments.
for(const pin of proof.producer)read(originalExecution,pin.path,pin);
const artifacts=new Map();
for(const pin of proof.outputs){
  assert.ok(!pin.path.includes('/')&&!artifacts.has(pin.path));
  const artifact=read(originalProofCommit,prefix+'/repacked-release-v2/'+pin.path,pin,{actual:true});artifacts.set(pin.path,artifact);
}
const specifications=[
  {original:'positive-control.json',output:'repack-positive-control-v1.json',oldKind:'positive',kind:'positive-control',bytes:302,sha256:'bc3008ec1542ef40774b551d8bac0b2a5af8d8657ca3aa87b81ca044b44ee6d8'},
  {original:'negative-control.json',output:'repack-negative-control-v1.json',oldKind:'negative',kind:'negative-control',bytes:339,sha256:'55fb8ea7a8ee0d086ee4edcf6b9f38e5b6e9983f4cdb0f14ad39b7cc88cf246b'}
];
const receipts=specifications.map(spec=>{
  const artifact=artifacts.get(spec.original);assert.ok(artifact);assert.equal(artifact.pin.bytes,spec.bytes);assert.equal(artifact.pin.sha256,spec.sha256);
  const original=JSON.parse(artifact.raw);assert.equal(original.method_id,'lossless-release-transport-repack');assert.equal(original.kind,spec.oldKind);assert.equal(original.outcome,'passed');
  if(spec.oldKind==='positive'){assert.equal(original.memberships,proof.memberships);assert.equal(original.ordered_membership_rows_sha256,proof.ordered_membership_rows_sha256);assert.match(original.release_membership_sha256,/^[a-f0-9]{64}$/);}
  else assert.ok(Array.isArray(original.controls)&&original.controls.length===3&&original.controls.every(c=>typeof c==='string'&&c.length));
  const filename=path.join(root,prefix,spec.output);assert.ok(!fs.existsSync(filename),'Preserve any existing typed control vintage');
  const receipt={...original,kind:spec.kind,execution_commit:originalExecution,
    underlying_outcome:artifact.pin,underlying_proof:proofInput.pin,
    normalization:{version:1,execution_commit:head,producer,operation:'Control kind header spelling only: '+spec.oldKind+' -> '+spec.kind,
      experiments_reexecuted:false,original_outcome_preserved:true,original_experiment_execution_commit:originalExecution,
      metric_vintage:'Original release-v2 experiments; no new measurement vintage',
      scope:'Schema header normalization only; no new experiment, scientific approval, geography change, installation or publication.'},
    verified_inputs:[...inputs.values()],budget:ledger.snapshot()};
  const comparable={...receipt};for(const key of ['execution_commit','underlying_outcome','underlying_proof','normalization','verified_inputs','budget'])delete comparable[key];comparable.kind=spec.oldKind;
  assert.deepEqual(comparable,original,'All underlying result fields must remain exact');
  return {filename,receipt,raw:Buffer.from(JSON.stringify(receipt)+'\n')};
});
// Include both output receipts in the same reserved byte/descriptor budget.
for(let pass=0;pass<6;pass++){
  const snapshot=ledger.snapshot(),total=receipts.reduce((n,r)=>n+r.raw.length,0);
  let stable=true;
  for(const item of receipts){item.receipt.budget={...snapshot,accounted_bytes:snapshot.accounted_bytes+total,accounted_descriptors:snapshot.accounted_descriptors+receipts.length};const raw=Buffer.from(JSON.stringify(item.receipt)+'\n');if(raw.length!==item.raw.length)stable=false;item.raw=raw;}
  if(stable)break;
}
for(const item of receipts){assert.ok(item.raw.length<=MAX);ledger.add({bytes:item.raw.length});}
for(const item of receipts){assert.equal(item.receipt.budget.accounted_bytes,ledger.snapshot().accounted_bytes);assert.equal(item.receipt.budget.accounted_descriptors,ledger.snapshot().accounted_descriptors);fs.writeFileSync(item.filename,item.raw,{flag:'wx'});assert.ok(fs.readFileSync(item.filename).equals(item.raw));}
// Original control/proof/artifact bytes remain unchanged after normalization.
for(const input of [proofInput,...artifacts.values()])assert.equal(sha(fs.readFileSync(path.join(root,input.pin.path))),input.pin.sha256);
console.log(JSON.stringify({operation:'control-header-normalization-only',original_execution_commit:originalExecution,outputs:receipts.map(r=>({path:path.relative(root,r.filename),bytes:r.raw.length,sha256:sha(r.raw)})),budget:ledger.snapshot()}));
