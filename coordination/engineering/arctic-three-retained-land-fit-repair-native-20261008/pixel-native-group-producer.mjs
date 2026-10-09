import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {admitPhase,authenticateAdmittedBody,readAdmittedBody} from './phase-admission.mjs';
import {pixelNativeGroup} from './pixel-native-group.mjs';
import {selectedOwnerRuns} from './pixel-area-order.mjs';
import {decodeInstalledWords,decodePinnedGzip} from './selected-native-inputs.mjs';
import {unshuffleOwnershipBytes} from '../../../src/ownership-codec.js';
const sha=b=>createHash('sha256').update(b).digest('hex');
export function producePixelNativeGroup(plan,outputValue) {
 assert(typeof outputValue==='string'&&!outputValue.split(path.sep).includes('..'));
 const output=path.resolve(outputValue);assert(output.startsWith(path.join(process.cwd(),'.cache')+path.sep));assert(!fs.existsSync(output));
 for(let p=output;;p=path.dirname(p)){try{const s=fs.lstatSync(p);assert(!s.isSymbolicLink());if(p!==output)assert(s.isDirectory());}catch(e){if(e.code!=='ENOENT')throw e;}if(p===path.dirname(p))break;}
 assert.equal(plan.kind,'complete-native-target-run-accounting-group');
 assert.equal(plan.source_head,process.env.WORLDATLAS_SELECTED_NATIVE_HEAD);
 assert.equal(sha(JSON.stringify(plan)),process.env.WORLDATLAS_SELECTED_NATIVE_PLAN_SHA256);
 assert.equal(process.execPath,plan.runtime.path);assert.equal(process.version,plan.runtime.version);
 assert.deepEqual(process.execArgv,[]);assert(!process.env.NODE_OPTIONS&&!process.env.NODE_PATH);
 const distinct=new Map();for(const pin of [plan.rows,...plan.parts.flatMap(p=>[p.before,p.after])]){
  const existing=distinct.get(pin.path);if(existing)for(const k of ['bytes','sha256','decoded_bytes','decoded_sha256'])assert.equal(existing[k],pin[k]);else distinct.set(pin.path,pin);
 }
 assert.equal(plan.canonical_unshuffle_bytes,[...distinct.values()].reduce((n,p)=>n+p.decoded_bytes,0));
 const admission=admitPhase({inputs:plan.inputs,runtime:plan.runtime,reservedInputBytes:plan.canonical_unshuffle_bytes,
  outputReserve:plan.output_reserve,metadataBytes:plan.metadata_bytes});
 const sources=plan.code.map(p=>readAdmittedBody(admission,p.path).toString());
 const functions=[producePixelNativeGroup,pixelNativeGroup,selectedOwnerRuns,decodeInstalledWords,decodePinnedGzip,
  admitPhase,authenticateAdmittedBody,readAdmittedBody,unshuffleOwnershipBytes];
 const fingerprints=functions.map(fn=>Function.prototype.toString.call(fn));
 const guard=()=>{assert.deepEqual(functions.map(fn=>Function.prototype.toString.call(fn)),fingerprints);
  for(const fingerprint of fingerprints)assert(sources.some(s=>s.includes(fingerprint)));
  for(const p of plan.code)authenticateAdmittedBody(admission,p.path);authenticateAdmittedBody(admission,plan.runtime.path);};
 guard();const started=new Date().toISOString(),report=pixelNativeGroup(admission,plan);
 const raw=Buffer.from(JSON.stringify(report)+'\n');assert(raw.length<=32*1024*1024);
 for(const p of plan.inputs)authenticateAdmittedBody(admission,p.path);guard();
 const execution=Buffer.from(JSON.stringify({kind:plan.kind,source_head:plan.source_head,started_at:started,completed_at:new Date().toISOString(),
  phase_bytes:admission.bytes,descriptors:admission.descriptors,scientific_output_sha256:sha(raw),grid_rows_computed:0,activated:false})+'\n');
 assert(raw.length+execution.length<=plan.output_reserve);
 fs.mkdirSync(output,{recursive:true});fs.writeFileSync(path.join(output,'target-runs.json'),raw,{flag:'wx',mode:0o644});
 fs.writeFileSync(path.join(output,'execution.json'),execution,{flag:'wx',mode:0o644});return JSON.parse(execution);
}
