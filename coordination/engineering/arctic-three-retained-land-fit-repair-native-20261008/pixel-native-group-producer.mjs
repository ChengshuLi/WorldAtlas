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
 assert(plan.parts.length>=1&&plan.parts.length<=2);
 for(const pair of plan.parts)assert(Number.isSafeInteger(pair.before.words)&&pair.before.words>0&&pair.before.words<=1048576&&pair.before.words%2===0);
 // Each [run,row,length] has at most25 JSON bytes including its delimiter;
 // the two complete side files each remain below32MiB before source reads.
 const maximumSideBytes=plan.parts.reduce((n,p)=>n+p.before.words/2,0)*25+131072;
 assert(maximumSideBytes<=32*1024*1024);assert(maximumSideBytes*2+262144<=plan.output_reserve);
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
 const bodies=['before','after'].map(side=>({name:`target-runs-${side}.json`,raw:Buffer.from(JSON.stringify({...report,side,parts:report.parts.map(p=>({offset:p.offset,words:p.words,targets:p[side]}))})+'\n')}));
 const metadata=Buffer.from(JSON.stringify({...report,parts:report.parts.map(({before,after,...p})=>p)})+'\n');
 for(const body of bodies)assert(body.raw.length<=32*1024*1024);assert(metadata.length<=131072);
 const outputBytes=bodies.reduce((n,b)=>n+b.raw.length,metadata.length);
 for(const p of plan.inputs)authenticateAdmittedBody(admission,p.path);guard();
 const execution=Buffer.from(JSON.stringify({kind:plan.kind,source_head:plan.source_head,started_at:started,completed_at:new Date().toISOString(),
  phase_bytes:admission.bytes,descriptors:admission.descriptors,scientific_outputs:bodies.map(b=>({path:b.name,bytes:b.raw.length,sha256:sha(b.raw)})),metadata_sha256:sha(metadata),grid_rows_computed:0,activated:false})+'\n');
 assert(outputBytes+execution.length<=plan.output_reserve);
 const remaining=Number(process.env.WORLDATLAS_NATIVE_ACCOUNTING_OUTPUT_REMAINING);
 assert(Number.isSafeInteger(remaining)&&remaining>=0&&outputBytes+execution.length+131072<=remaining,
  'Complete retained output allowance must cover this writer before writes');
 fs.mkdirSync(output,{recursive:true});for(const body of bodies)fs.writeFileSync(path.join(output,body.name),body.raw,{flag:'wx',mode:0o644});fs.writeFileSync(path.join(output,'group-index.json'),metadata,{flag:'wx',mode:0o644});
 fs.writeFileSync(path.join(output,'execution.json'),execution,{flag:'wx',mode:0o644});return JSON.parse(execution);
}
