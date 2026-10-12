import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {performance} from 'node:perf_hooks';
const [root,scratch]=process.argv.slice(2);
assert(root&&scratch,'Provide repository and directory containing the five exact pinned input bodies');
const sha=b=>createHash('sha256').update(b).digest('hex');
const pins=[
 ['baseline_result',scratch+'/baseline-result',3200420,'80420ed4cd173fc975f795cf9790bde6d4c32b0dd9c1331921eb3d1f2a615e22','894c9d7a79345bf85a8469325162cd6bdddfecbc'],
 ['candidate_result',scratch+'/candidate-result',3923538,'1a8b08dadb704d2dccf1dd657ba3da00d77cf5f6d1411fcce4166f0c54feefc5','659f479a6ed32157396ef70be1e1e7d34d923d3b'],
 ['baseline_request',scratch+'/baseline-request',1877418,'f105a3069c2d6caca5ce89f4c1ae7e197d40e9c0ae198604cd2ea7877bfa01c3','07ec865ed6617e51b4e50e54afa5fe4be1bc4887'],
 ['candidate_request',scratch+'/candidate-request',2467782,'fcd3654f3f611bc7620dbcb0c64a65598ba7fa949a46328ea9b05b654250ba78','ba7c04c749f6411eabe291d0251a732dbd24097b'],
 ['owners_encoded',scratch+'/owners.gz',2663523,'b33f44b882b4a0c9b89c79fb079b766505a18f2ba0089fe2945ac9b5120fb78f','9c44513df64995d417dd3832ae604c703e84a506']
];
const bodies={},verified=[];
for(const [name,file,bytes,hash,oid]of pins){const b=fs.readFileSync(file);assert.equal(b.length,bytes);assert.equal(sha(b),hash);assert.equal(createHash('sha1').update(Buffer.concat([Buffer.from(`blob ${bytes}\0`),b])).digest('hex'),oid);bodies[name]=b;verified.push({name,bytes,sha256:hash,git_blob_oid:oid});}
const old=JSON.parse(bodies.baseline_result),next=JSON.parse(bodies.candidate_result),oldq=JSON.parse(bodies.baseline_request),nextq=JSON.parse(bodies.candidate_request);
const ownersRaw=gunzipSync(bodies.owners_encoded,{maxOutputLength:11096191});assert.equal(ownersRaw.length,11096191);assert.equal(sha(ownersRaw),'a8086008b7a072dd86483720a2a166785229753422769dbbe0749497d870f428');
const owners=JSON.parse(ownersRaw);assert.equal(owners.length,49625);assert.equal(new Set(owners.map(o=>o.id)).size,owners.length);owners.forEach((o,i)=>{assert.equal(o.index,i+1);assert.equal(typeof o.province_id,'string');assert(Number.isSafeInteger(o.province_index));});
assert.deepEqual(old.base_selection,next.base_selection);assert.deepEqual(oldq.base_selection,nextq.base_selection);assert.equal(oldq.acquisition.manifest_sha256,nextq.acquisition.manifest_sha256);assert.equal(oldq.size,nextq.size);
const normalize=input=>{const x=structuredClone(input);if(x.custody.kind==='selected-native-transport')for(const f of x.custody.fragments){if(Object.hasOwn(f.pin,'sha256'))assert.equal(f.pin.sha256,f.sha256);if(Object.hasOwn(f.pin,'whole_body_consumed'))assert.equal(f.pin.whole_body_consumed,true);delete f.pin.sha256;delete f.pin.whole_body_consumed;}return x;};
const inputs=new Map(nextq.acquisition.native_inputs.map(x=>[x.logical_path,normalize(x)]));for(const x of oldq.acquisition.native_inputs)assert.deepEqual(normalize(x),inputs.get(x.logical_path));
assert.equal(oldq.acquisition.native_inputs.filter(x=>x.asset.kind==='rows').length,1);
const before=new Map(old.native.effective_rows.map(r=>[r.y,r])),after=new Map(next.native.effective_rows.map(r=>[r.y,r]));const oldbase=new Map(old.native.current_rows.map(r=>[r.y,r])),newbase=new Map(next.native.current_rows.map(r=>[r.y,r]));
for(const [y,r]of oldbase)assert.deepEqual(r,newbase.get(y));
const union=[...new Set([...before.keys(),...after.keys()])].sort((a,b)=>a-b);let filledBefore=0,filledAfter=0;
for(const y of union){if(!before.has(y)){assert(newbase.has(y));before.set(y,newbase.get(y));filledBefore++;}if(!after.has(y)){assert(oldbase.has(y));after.set(y,oldbase.get(y));filledAfter++;}}
const beforeRows=union.map(y=>before.get(y)),afterRows=union.map(y=>after.get(y));
const file=root+'/scripts/check-effective-geographic-regression.mjs',codeBefore=fs.readFileSync(file),codeHash=sha(codeBefore);
const {deriveEffectiveNativeRowDelta,compareEffectiveNativeRows}=await import(file);
const opts={size:oldq.size,ownersBefore:owners,ownersAfter:owners};
const deriveStart=performance.now();const delta=deriveEffectiveNativeRowDelta(beforeRows,afterRows,opts);const deriveMs=performance.now()-deriveStart;
const selectedBefore=delta.map(y=>before.get(y)),selectedAfter=delta.map(y=>after.get(y));
const compareStart=performance.now();const result=compareEffectiveNativeRows(selectedBefore,selectedAfter,{...opts,rows:delta});const compareMs=performance.now()-compareStart;
assert.equal(sha(fs.readFileSync(file)),codeHash);assert.equal(delta.length,18);assert.equal(result.lost_or_reassigned_cells,0);
const report={version:1,role:'measured-projection-proof',kind:'bounded-real-retained-native-interval-comparison',baseline:'ad300bd5ffa73c226e591f037980d67d40f6acf3',candidate:'c753c65a72e51718b453883a941fc22e148b5fbb',node:process.version,code:{path:'scripts/check-effective-geographic-regression.mjs',bytes:codeBefore.length,sha256:codeHash,unchanged_during_run:true},data_pins:verified,owners:{decoded_bytes:ownersRaw.length,decoded_sha256:sha(ownersRaw),rows:owners.length},scope:{union_rows:union.length,original_before_rows:old.native.effective_rows.length,original_after_rows:next.native.effective_rows.length,filled_before_from_authenticated_common_base:filledBefore,filled_after_from_authenticated_common_base:filledAfter,delta_rows:delta,shared_native_input_identities:oldq.acquisition.native_inputs.length},result,timing:{derive_ms:deriveMs,compare_ms:compareMs,algorithm_total_ms:deriveMs+compareMs,repetitions:1,excludes:'downloads, JSON parsing, owner decode, module import and provenance assertions'},limitations:['Retained interval numerical comparison only; no selected full-entry or original external operating custody replay.','Immutable artifact body checks and common declared native custody identity equality do not themselves authenticate present runtime transport availability/absence.','No native/source operator rerun; no hosted speedup or full-gate elapsed claim.']};
process.stdout.write(JSON.stringify(report,null,2)+'\n');
