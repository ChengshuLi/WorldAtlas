import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {admitPhase,authenticateAdmittedBody,readAdmittedBody} from './phase-admission.mjs';
import {joinPixelAccounting} from './pixel-accounting-join.mjs';
import {sumCompleteOwnerRuns,nativeRowArea} from './pixel-area-order.mjs';
const sha=body=>createHash('sha256').update(body).digest('hex');
export function producePixelAccountingJoin(plan,outputValue) {
 assert(typeof outputValue==='string'&&!outputValue.split(path.sep).includes('..'));
 const output=path.resolve(outputValue);assert(output.startsWith(path.join(process.cwd(),'.cache')+path.sep));
 for(let p=output;;p=path.dirname(p)) {
  try {const s=fs.lstatSync(p);assert(!s.isSymbolicLink());assert.notEqual(p,output,'Fresh output required');assert(s.isDirectory());}
  catch(e){if(e.code!=='ENOENT')throw e;}if(p===path.dirname(p))break;
 }
 assert.equal(plan.kind,'complete-original-order-two-target-pixel-accounting');
 assert.equal(plan.source_head,process.env.WORLDATLAS_SELECTED_NATIVE_HEAD);
 assert.equal(sha(JSON.stringify(plan)),process.env.WORLDATLAS_SELECTED_NATIVE_PLAN_SHA256);
 assert.equal(process.execPath,plan.runtime.path);assert.equal(process.version,plan.runtime.version);
 assert.deepEqual(process.execArgv,[]);assert(!process.env.NODE_OPTIONS&&!process.env.NODE_PATH);
 assert.equal(plan.groups.length,28);assert(plan.output_reserve>=262144);
 const admission=admitPhase({inputs:plan.inputs,runtime:plan.runtime,
  outputReserve:plan.output_reserve,metadataBytes:plan.metadata_bytes});
 const sources=plan.code.map(pin=>readAdmittedBody(admission,pin.path).toString());
 const functions=[producePixelAccountingJoin,joinPixelAccounting,sumCompleteOwnerRuns,nativeRowArea,
  admitPhase,authenticateAdmittedBody,readAdmittedBody];
 const fingerprints=functions.map(fn=>Function.prototype.toString.call(fn));
 const guard=()=>{
  assert.deepEqual(functions.map(fn=>Function.prototype.toString.call(fn)),fingerprints);
  for(const body of fingerprints)assert(sources.some(source=>source.includes(body)));
  for(const pin of plan.code)authenticateAdmittedBody(admission,pin.path);
  authenticateAdmittedBody(admission,plan.runtime.path);
 };
 guard();const started=new Date().toISOString();
 const groups=plan.groups.map(group=>Object.fromEntries(['before','after'].map(side=>
  [side,JSON.parse(readAdmittedBody(admission,group[side].path))])));
 const pixel=JSON.parse(readAdmittedBody(admission,plan.original_pixel.path));
 const result=joinPixelAccounting(groups,pixel),raw=Buffer.from(JSON.stringify(result)+'\n');
 assert(raw.length<=131072);
 for(const pin of plan.inputs)authenticateAdmittedBody(admission,pin.path);guard();
 const execution=Buffer.from(JSON.stringify({source_head:plan.source_head,started_at:started,
  completed_at:new Date().toISOString(),phase_bytes:admission.bytes,descriptors:admission.descriptors,
  output:{path:'pixel-accounting.json',bytes:raw.length,sha256:sha(raw)},
  original_pixel_sha256:plan.original_pixel.sha256,grid_rows_computed:0,activated:false})+'\n');
 assert(raw.length+execution.length<=plan.output_reserve);
 fs.mkdirSync(output,{recursive:true});fs.writeFileSync(path.join(output,'pixel-accounting.json'),raw,{flag:'wx',mode:0o644});
 fs.writeFileSync(path.join(output,'execution.json'),execution,{flag:'wx',mode:0o644});return JSON.parse(execution);
}
