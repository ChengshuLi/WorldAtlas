import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {gunzipSync} from 'node:zlib';
import {packageTemporalBundle} from '../scripts/package-temporal-bundle.mjs';
import {loadTemporalBundle} from '../src/temporal-bundle.js';

test('temporal transport preserves complete identities, parent chains and original history with both host encodings',async()=>{
 const root=await fs.mkdtemp(path.join(os.tmpdir(),'atlas-temporal-bundle-test-'));
 try {
  const release={footprints_sha256:'a'.repeat(64),hierarchy_sha256:'b'.repeat(64)};
  const entities=[{id:'original:location',kind:'location',parent_id:'original:province',attributes:{name:'Original name',source:'Original source',metadata:{source_date:'2021'}}}];
  const history=[{id:'original:membership',entity_id:'original:location',parent_id:'original:province',valid_from:-1,valid_to:1,source:'Original historical source',metadata:{uncertainty:'retained'}}];
  const before=JSON.stringify({entities,history});
  const options={entities,history,footprints:release.footprints_sha256,hierarchy:release.hierarchy_sha256};
  const proof=await packageTemporalBundle({...options,destination:path.join(root,'one')});
  const repeated=await packageTemporalBundle({...options,destination:path.join(root,'two')});
  assert.deepEqual(repeated,proof);
  const bytes=await fs.readFile(path.join(root,'one/startup-temporal.json.gz'));
  assert.deepEqual(await fs.readFile(path.join(root,'two/startup-temporal.json.gz')),bytes);
  for(const body of [bytes,gunzipSync(bytes)])assert.deepEqual(await loadTemporalBundle(proof,release,async()=>new Response(body)),{entities,history});
  assert.equal(JSON.stringify({entities,history}),before);
  let reads=0;const unexpected=async()=>{reads++;throw Error('Unexpected read');};
  for(const changed of [{footprints_sha256:'c'.repeat(64)},{hierarchy_sha256:'c'.repeat(64)}])await assert.rejects(loadTemporalBundle(proof,{...release,...changed},unexpected),/Invalid reference/);
  assert.equal(reads,0);
  await assert.rejects(loadTemporalBundle({...proof,entities:2},release,async()=>new Response(bytes)),/roster/);
  await assert.rejects(loadTemporalBundle(proof,release,async()=>new Response('',{status:404})),/unavailable/);
  await assert.rejects(loadTemporalBundle(proof,release,async()=>new Response(bytes.subarray(1))),/checksum/);
  await assert.rejects(packageTemporalBundle({...options,destination:path.join(root,'one')}),{code:'EEXIST'});
 } finally { await fs.rm(root,{recursive:true,force:true}); }
});
