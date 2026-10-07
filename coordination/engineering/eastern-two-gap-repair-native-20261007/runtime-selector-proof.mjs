import fs from 'node:fs';
import zlib from 'node:zlib';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import {runtimeOwnershipBucket,runtimeOwnershipData} from '../../../src/runtime-ownership.js';
const [directory,output]=process.argv.slice(2);
const runtime=JSON.parse(fs.readFileSync(`${directory}/index.json`));
const selectorYears=[];
for(let year=-3000;year<=2026;year++){
 if(year===0)continue;
 const actual=runtimeOwnershipBucket(runtime,year);
 const expected=runtime.buckets.filter(b=>b.valid_from<=year&&year<b.valid_to);
 assert.ok(expected.length<=1);
 assert.deepEqual(actual,expected[0]??null);
 selectorYears.push({year,bucket_index:actual?runtime.buckets.indexOf(actual):null,path:actual?.path??null});
}
assert.throws(()=>runtimeOwnershipBucket(runtime,0),/year zero/);
assert.throws(()=>runtimeOwnershipBucket(runtime,1.5),/year zero/);
assert.throws(()=>runtimeOwnershipBucket({...runtime,encoding:'forged'},1901),/encoding/);
let headerChecks=0;
for(const entry of runtime.buckets){
 const raw=fs.readFileSync(`${directory}/${entry.path}`);
 assert.equal(crypto.createHash('sha256').update(raw).digest('hex'),entry.sha256);
 const data=JSON.parse(zlib.gunzipSync(raw));
 const year=entry.valid_from===0?1:entry.valid_from;
 const actual=runtimeOwnershipData(runtime,data,year);
 assert.equal(actual.parts,data.parts);
 assert.equal(actual.index.evidence,data.evidence);
 assert.deepEqual(actual.index.owner_ids,runtime.shared.owner_ids);
 for(const bad of [{...data,source_index_sha256:'0'.repeat(64)},
                  {...data,valid_from:data.valid_from+1},{...data,valid_to:data.valid_to-1},
                  {...data,parts:null},{...data,evidence:null}]){
  assert.throws(()=>runtimeOwnershipData(runtime,bad,year),/does not match/);
 }
 headerChecks++;
}
fs.writeFileSync(output,JSON.stringify({runtime_index_sha256:crypto.createHash('sha256').update(fs.readFileSync(`${directory}/index.json`)).digest('hex'),
 production_selector:'src/runtime-ownership.js',all_valid_years:selectorYears,
 actual_bucket_header_checks:headerChecks,directed_invalid_header_checks:headerChecks*5,
 source_tuple_equivalence_requires_complete_validator:true})+'\n');
console.log(JSON.stringify({all_valid_years:selectorYears.length,bucket_headers:headerChecks,negative_headers:headerChecks*5}));
