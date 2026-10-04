import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {gzipSync, gunzipSync} from 'node:zlib';
import {packageReferenceBundle} from '../scripts/package-reference-bundle.mjs';
import {loadReferenceBundle} from '../src/reference-bundle.js';
import {decodeReferences, decodeReferenceContext} from '../src/reference-records.js';

const footprints='a'.repeat(64), digest=bytes=>createHash('sha256').update(bytes).digest('hex');
async function fixture(run) {
  const root=await fs.mkdtemp(path.join(os.tmpdir(),'atlas-reference-bundle-test-'));
  try {
    const source=path.join(root,'source');await fs.mkdir(source);
    const index={version:2,footprints_sha256:footprints,parts:['one.json.gz','two.json.gz'],values:['Cfb','Af'],types:[
      {attribute:'climate',valid_from:2026,valid_to:2027,method:'reference',status:'reference',source:'Original source',metadata:{normal_period:'1991-2020'}}
    ]};
    const parts=[[['location:A',[[0,0,0.75,0.9]]]], [['location:B',[[0,1,0.8,1]]]]];
    await fs.writeFile(path.join(source,'index.json'),JSON.stringify(index));
    for(let i=0;i<parts.length;i++)await fs.writeFile(path.join(source,index.parts[i]),gzipSync(JSON.stringify(parts[i])));
    const one=await packageReferenceBundle({source,destination:path.join(root,'one'),expectedFootprints:footprints});
    const bytes=await fs.readFile(path.join(root,'one/startup-bundle.json.gz'));
    await run({root,source,index,parts,bytes,proof:one.descriptor,sources:one.sources});
  } finally { await fs.rm(root,{recursive:true,force:true}); }
}

test('bundle preserves complete records, supported intervals, source context and original bytes',async()=>fixture(async({source,index,parts,bytes,proof,sources})=>{
  for(const payload of [bytes,gunzipSync(bytes)]) {
    const loaded=await loadReferenceBundle(proof,footprints,async()=>new Response(payload));
    assert.deepEqual(loaded,{index,parts});
    for(const year of [-1,1,2020,2026])assert.deepEqual(decodeReferences(loaded.parts,loaded.index,year),decodeReferences(parts,index,year));
    assert.deepEqual(decodeReferenceContext(loaded.parts,loaded.index),decodeReferenceContext(parts,index));
  }
  for(const input of sources)assert.equal(digest(await fs.readFile(path.join(source,input.path))),input.sha256);
}));

test('separate bundle runs are byte-identical and cannot overwrite an earlier output',async()=>fixture(async({root,source,bytes})=>{
  await packageReferenceBundle({source,destination:path.join(root,'two'),expectedFootprints:footprints});
  assert.deepEqual(await fs.readFile(path.join(root,'two/startup-bundle.json.gz')),bytes);
  await assert.rejects(packageReferenceBundle({source,destination:path.join(root,'one'),expectedFootprints:footprints}),{code:'EEXIST'});
}));

test('proof rejects mixed footprints, unsafe routes and oversized declarations before any fetch',async()=>fixture(async({proof})=>{
  let calls=0;const fetcher=async()=>{calls++;throw Error('Unexpected read');};
  for(const changed of [{footprints_sha256:'b'.repeat(64)},{path:'../source'},{bytes:8*1024*1024+1},{decoded_bytes:32*1024*1024+1},{part_count:0}]) {
    await assert.rejects(loadReferenceBundle({...proof,...changed},footprints,fetcher),/Invalid reference/);
  }
  assert.equal(calls,0);
}));

test('bad hashes, truncated data and unavailable bundles fail closed',async()=>fixture(async({proof,bytes})=>{
  const bad=Buffer.from(bytes);bad[20]^=1;
  for(const payload of [bad,bytes.subarray(0,bytes.length-1),Buffer.from('{}')])await assert.rejects(loadReferenceBundle(proof,footprints,async()=>new Response(payload)),/checksum/);
  await assert.rejects(loadReferenceBundle(proof,footprints,async()=>new Response('',{status:404})),/unavailable/);
  await assert.rejects(loadReferenceBundle({...proof,decoded_sha256:'b'.repeat(64)},footprints,async()=>new Response(bytes)),/decoded checksum/);
}));

test('an internally incomplete roster is rejected even with matching transport hashes',async()=>fixture(async({proof,bytes})=>{
  const object=JSON.parse(gunzipSync(bytes));object.parts.pop();
  const raw=Buffer.from(JSON.stringify(object)),compressed=gzipSync(raw);
  const changed={...proof,bytes:compressed.length,sha256:digest(compressed),decoded_bytes:raw.length,decoded_sha256:digest(raw)};
  await assert.rejects(loadReferenceBundle(changed,footprints,async()=>new Response(compressed)),/roster/);
}));

test('packaging refuses unsafe source rosters and mismatched source footprints',async()=>fixture(async({root,source,index})=>{
  await assert.rejects(packageReferenceBundle({source,destination:path.join(root,'bad'),expectedFootprints:'b'.repeat(64)}),/Invalid reference/);
  await fs.writeFile(path.join(source,'index.json'),JSON.stringify({...index,parts:['../other.json']}));
  await assert.rejects(packageReferenceBundle({source,destination:path.join(root,'bad'),expectedFootprints:footprints}),/Invalid reference/);
}));
