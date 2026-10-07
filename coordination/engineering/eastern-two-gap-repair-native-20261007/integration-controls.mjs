import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {authenticateSuccessorContextInventory} from './chained-context.mjs';
const ns='coordination/engineering/eastern-two-gap-repair-native-20261007',root='data/canonical-grid/eastern-v8',raw=fs.readFileSync(root+'/context-index.json'),image=JSON.parse(fs.readFileSync(root+'/context-transport/index.json')),comparison=fs.readFileSync(ns+'/native-selection-receipt.json');
const copy=x=>JSON.parse(JSON.stringify(x)),sha=b=>createHash('sha256').update(b).digest('hex');let passed=0;
assert.equal(authenticateSuccessorContextInventory(raw,image,comparison).locations,49625);passed++;
for(const mutate of [x=>{x.files.shift();},x=>{x.files.push(copy(x.files[0]));},x=>{x.files[0].mode='100755';},x=>{x.files[0].original_binding.scientific_execution_commit='0'.repeat(40);},x=>{x.files[0].sha256='0'.repeat(64);x.files[0].original_binding.original_product.sha256='0'.repeat(64);}]){
 const changed=copy(image);mutate(changed);assert.throws(()=>authenticateSuccessorContextInventory(raw,changed,comparison));passed++;
}
// Coherently rebinding the full index and image to a changed decoded-source claim
// cannot replace the immutable original complete native inventory.
const index=JSON.parse(raw),changedImage=copy(image);index.parts[0].decoded_sha256='0'.repeat(64);changedImage.files[0].original_binding.original_product=index.parts.find(p=>p.path===changedImage.files[0].path);
const changedRaw=Buffer.from(JSON.stringify(index)+'\n');assert.notEqual(sha(changedRaw),sha(raw));assert.throws(()=>authenticateSuccessorContextInventory(changedRaw,changedImage,comparison),/Original full context index changed|equal/);passed++;
const changedComparison=Buffer.from(JSON.stringify({...JSON.parse(comparison),arbitrary_rebinding:true}));assert.throws(()=>authenticateSuccessorContextInventory(raw,image,changedComparison),/Original complete native comparison binding changed/);passed++;
console.log(JSON.stringify({status:'PASS',controls:passed,all_original_context_bodies:image.files.length,original_index_sha256:sha(raw),original_native_comparison_sha256:sha(comparison)}));
