import assert from 'node:assert/strict';
import {geographicMembershipHash} from '../../../hosted/geographic-releases.js';
import {hashCompleteMemberships} from './release-successor.mjs';
const records=[{entity_id:'a😀',kind:'location',parent_id:'p',reference_name:'é',active:1,source_id:'s',evidence:{z:[1,{nested:'雪'}],a:null}},{id:'a\uE000',level:'province',source_id:'s',evidence:'{"reason":"retained","date":null}'},{entity_id:'a',kind:'continent',parent_id:null,active:0,source_id:'s',evidence:{}}];
for(const value of [[],records,records.toReversed()])assert.equal(hashCompleteMemberships(value),await geographicMembershipHash(value));
const hash=hashCompleteMemberships(records);let negative=0;
for(const patch of [{source_id:'foreign'},{parent_id:'foreign'},{active:1},{evidence:{foreign:true}},{reference_name:'foreign'}]){const changed=records.map((r,i)=>i===2?{...r,...patch}:r);assert.notEqual(hashCompleteMemberships(changed),hash);negative++;}
assert.throws(()=>hashCompleteMemberships([{entity_id:'a',evidence:'[]'}]));negative++;
assert.throws(()=>hashCompleteMemberships([{entity_id:'a',evidence:{large:'x'.repeat(16384)}}]));negative++;
console.log(JSON.stringify({positive:3,negative,exact_original_stock_canonical_array_bytes:true,non_bmp_binary_order:true,limit:'Hash equivalence controls; real complete v8 ledger/source proof still required'}));
