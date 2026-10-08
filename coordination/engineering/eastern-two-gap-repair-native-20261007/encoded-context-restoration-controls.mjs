// Full retained byte-operator fixtures; no scientific computation or recompression.
import fs from 'node:fs';import path from 'node:path';import assert from 'node:assert/strict';
import {gunzipSync} from 'node:zlib';import{createHash}from'node:crypto';
import{applyBytePatch,verifyWholeBytes}from'./byte-patch.mjs';
const root=path.resolve(process.argv[2]),sha=b=>createHash('sha256').update(b).digest('hex');
const original=fs.readFileSync(path.join(root,'before.gz'));
assert.equal(sha(original),'ea4835ae6e3ea9eddf4444a7040b1a6345d99d2ea9ad73f0f0ed93f3ba5e4c87');
const plan=JSON.parse(gunzipSync(fs.readFileSync(path.join(root,'encoded-patch.json.gz')),{maxOutputLength:32*1024*1024}));
verifyWholeBytes(original,plan.original_source);
const result=applyBytePatch(plan.commands,plan.current_member,name=>{assert.equal(name,'original');return original;});
assert(result.equals(fs.readFileSync(path.join(root,'after.gz'))));
assert.equal(sha(result),'aa2dc4ef06fba0f25a675c5c9d61ac6aeee95d766cc3c58055f837019e36a953');
assert.equal(sha(gunzipSync(result,{maxOutputLength:32*1024*1024})),plan.after_decoded_sha256);
const whole=fs.readFileSync(path.join(root,'outer-whole.bin'));
const outer=JSON.parse(gunzipSync(fs.readFileSync(path.join(root,'outer-patches.json.gz')),{maxOutputLength:32*1024*1024}));
assert.equal(whole.length,outer.whole_bytes);assert.equal(sha(whole),outer.whole_sha256);
for(const row of outer.parts){const encoded=applyBytePatch(row.commands,{...row.part,mode:'100644'},name=>{assert.equal(name,'whole');return whole;});assert(encoded.equals(fs.readFileSync(path.join(root,row.part.path))));assert(gunzipSync(encoded,{maxOutputLength:32*1024*1024}).equals(whole.subarray(row.part.offset,row.part.offset+row.part.decoded_bytes)));}
assert.throws(()=>applyBytePatch(plan.commands.slice(1),plan.current_member,()=>original));
const altered=Buffer.from(original);altered[100]^=1;assert.throws(()=>verifyWholeBytes(altered,plan.original_source));
assert.throws(()=>applyBytePatch([{copy:['original',original.length,1]}],plan.current_member,()=>original));
assert.throws(()=>applyBytePatch(plan.commands,{...plan.current_member,sha256:'0'.repeat(64)},()=>original));
assert.throws(()=>applyBytePatch(plan.commands,plan.current_member,name=>{assert.equal(name,'foreign');return original;}));
assert.throws(()=>applyBytePatch(plan.commands,{...plan.current_member,bytes:32*1024*1024+1},()=>original));
console.log(JSON.stringify({status:'PASS',node:process.version,executable:process.execPath,complete_encoded_member_inverse:true,complete_outer_transport_inverse:2,negative_controls:6,compression_encoder_invoked:false,scientific_generators_invoked:false}));
