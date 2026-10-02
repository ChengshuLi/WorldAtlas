import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {gzipSync,gunzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {decodeDerived} from '../src/derived-records.js';
import {runtimeOwnershipBucket,runtimeOwnershipData} from '../src/runtime-ownership.js';

const hash=b=>createHash('sha256').update(b).digest('hex');
test('century transport preserves exact intervals, dated identities and contested provenance with deterministic assets',()=>{
 const work=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-runtime-test-'));
 try{
  const source=path.join(work,'source');fs.mkdirSync(source);
  const evidence=[[0,.61,.95,[[0,.61],[1,.34]],[0],0],[1,.52,.9,[[0,.52],[1,.38]],[1],0],[null,.5,1,[[0,.5],[1,.5]],[0,1],0],[null,.8,.99,[[0,.8],[1,.5]],[0,1],1]];
  const parts=[[['l',[[-150,-1,0,0,0],[-1,1,null,2,2],[1,101,0,0,0],[101,120,0,0,1],[120,201,null,1,3],[201,2025,0,0,1]]],['long',[[-150,2025,1,0,0]]]]];
  const write=(name,data)=>{const bytes=gzipSync(JSON.stringify(data));fs.writeFileSync(path.join(source,name),bytes);return {path:name,sha256:hash(bytes)};};
  const original={version:2,valid_from:-150,valid_to:2025,source:'Dated political source fixture',source_url:'https://example.org/fixture',footprints_sha256:'fixture-footprints',owner_ids:['owner:stable','owner:competitor'],labels:['Old label','New label'],source_ids:['early','late'],statuses_order:['derived','disputed','no-majority','unknown'],entities:{'owner:stable':{name:'Reference owner'},'owner:competitor':{name:'Competitor'}},parts:[write('part.json.gz',parts[0])],evidence_parts:[write('evidence.json.gz',evidence)],evidence_records:evidence.length,intervals:7};
  fs.writeFileSync(path.join(source,'index.json'),JSON.stringify(original));
  const run=output=>{execFileSync('python',[path.resolve(import.meta.dirname,'../scripts/prepare-ownership-runtime.py'),'--source',source,'--output',output],{encoding:'utf8'});return JSON.parse(fs.readFileSync(path.join(output,'index.json'),'utf8'));};
  const output=path.join(work,'runtime'),runtime=run(output);
  assert.equal(runtime.source_index_sha256,hash(fs.readFileSync(path.join(source,'index.json'))));
  assert.ok(runtime.buckets.every(b=>b.valid_from!==0&&b.valid_to!==0));
  assert.equal(runtimeOwnershipBucket(runtime,-1).valid_to,1);
  assert.equal(runtimeOwnershipBucket(runtime,1).valid_from,1);
  assert.equal(runtimeOwnershipBucket(runtime,100).valid_from,1);
  assert.equal(runtimeOwnershipBucket(runtime,101).valid_from,101);
  const baseline={...original,evidence};
  for(const year of [-150,-101,-100,-2,-1,1,100,101,119,120,200,201,2000,2001,2024]){
   const selected=runtimeOwnershipBucket(runtime,year),bytes=fs.readFileSync(path.join(output,selected.path));
   assert.equal(hash(bytes),selected.sha256);
   assert.equal(bytes.readUInt32LE(4),0,'gzip timestamps are reproducible');
   const bucket=JSON.parse(gunzipSync(bytes));const decoded=runtimeOwnershipData(runtime,bucket,year);
   assert.deepEqual(decodeDerived(decoded.parts,decoded.index,year),decodeDerived(parts,baseline,year),`exact source dates and evidence at ${year}`);
   assert.ok(bucket.parts.flat().flatMap(([,rows])=>rows).some(r=>r[0]===-150&&r[1]===2025),'long evidence retains its original dates');
  }
  assert.equal(runtimeOwnershipBucket(runtime,2025),null);assert.equal(runtimeOwnershipBucket(runtime,2026),null);
  assert.throws(()=>runtimeOwnershipBucket(runtime,0),/zero/);
  const selected=runtimeOwnershipBucket(runtime,101),bucket=JSON.parse(gunzipSync(fs.readFileSync(path.join(output,selected.path))));
  assert.throws(()=>runtimeOwnershipData(runtime,{...bucket,source_index_sha256:'wrong'},101),/manifest/);
  const again=run(path.join(work,'second'));
  assert.deepEqual(again.buckets,runtime.buckets,'fresh preparation produces identical hashes');
  original.source='Updated fixture provenance';fs.writeFileSync(path.join(source,'index.json'),JSON.stringify(original));
  const invalidated=run(output);assert.notEqual(invalidated.source_index_sha256,runtime.source_index_sha256);assert.equal(invalidated.shared.source,'Updated fixture provenance');
 }finally{fs.rmSync(work,{recursive:true,force:true});}
});
