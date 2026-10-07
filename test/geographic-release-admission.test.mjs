import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {gzipSync} from 'node:zlib';
import {splitGeographicReleaseBatch,admitGeographicReleaseBatches} from '../scripts/geographic-release-admission.mjs';
import {publishGeographicReleases} from '../scripts/bootstrap-geographic-release.mjs';
import {stageGeographicRelease} from '../hosted/geographic-releases.js';
import {buildCases,assertPreservedRequests,combinedRows,wireBytes} from './fixtures/geographic-admission/independent-boundaries.mjs';

const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const descriptor = (bytes, path = '7-memberships-test.json', route = '/api/geography/stage') => ({path,route,sha256:sha(bytes)});

test('independent combined-row and UTF8 fixtures split with complete raw preservation', async () => {
  const cases=buildCases();
  for(const payload of [cases.row250,cases.row251,cases.mixed250,cases.mixed251,cases.unicode,cases.exact,cases.idOverflow,
    {release:cases.release,memberships:cases.memberships,changes:cases.mixed250.changes}]){
    const bytes=Buffer.from(JSON.stringify(payload)),part=descriptor(bytes);
    const first=splitGeographicReleaseBatch(bytes,part),again=splitGeographicReleaseBatch(bytes,part);
    assert.deepEqual(first,again,'Exact replay bodies must be deterministic');
    const outputs=first.map(bytes=>JSON.parse(bytes));assertPreservedRequests([payload],outputs);
    if(combinedRows(payload)>250)assert.ok(outputs.length>1);
    // Replacing an oversized original2000-character ID may itself make a
    // byte-boundary request fit; request count is not the conservation oracle.
    if(wireBytes(payload)>1048576)assert.notEqual(outputs[0].ingestion_id,payload.ingestion_id);
    for(const body of outputs)if(body.release){
      const db=new Proxy({}, {get(){throw Error('DB sentinel');}});
      await assert.rejects(stageGeographicRelease(db,body),/DB sentinel/,'Real consumer accepts combined row/byte admission');
    }
  }
});

test('input-bound replay IDs differ for changed meaningful bytes and parent identities', () => {
  const payload=buildCases().row251,bytes=Buffer.from(JSON.stringify(payload)),part=descriptor(bytes);
  const original=splitGeographicReleaseBatch(bytes,part).map(b=>JSON.parse(b).ingestion_id);
  payload.memberships[0].reference_name='Changed actual name';
  const changed=splitGeographicReleaseBatch(Buffer.from(JSON.stringify(payload)),part).map(b=>JSON.parse(b).ingestion_id);
  assert.ok(changed.every(id=>!original.includes(id)));
  const other=splitGeographicReleaseBatch(bytes,{...part,path:'7-memberships-other.json'}).map(b=>JSON.parse(b).ingestion_id);
  assert.ok(other.every(id=>!original.includes(id)));
});

test('bounded originals retain exact bytes and ingestion IDs; duplicate raw IDs cannot hide behind sets', () => {
  const payload=buildCases().row250,bytes=Buffer.from(JSON.stringify(payload)+'\n');
  assert.deepEqual(splitGeographicReleaseBatch(bytes,descriptor(bytes)),[bytes]);
  payload.memberships.push(payload.memberships[0]);
  assert.throws(()=>splitGeographicReleaseBatch(Buffer.from(JSON.stringify(payload)),descriptor(bytes)),/duplicate/);
});

test('complete admission authenticates compressed and decoded bytes and captures once for execution', async () => {
  const payload=buildCases().unicode,decoded=Buffer.from(JSON.stringify(payload)),encoded=gzipSync(decoded);
  const part={...descriptor(encoded,'7-memberships-test.json.gz'),encoding:'gzip',payload_sha256:sha(decoded)};
  let reads=0;const {plan}=await admitGeographicReleaseBatches([part],{readBatch:()=>{reads++;return encoded;}});
  encoded.fill(0);assert.equal(reads,1);
  assertPreservedRequests([payload],plan.get(part.path).map(b=>JSON.parse(b)));
  await assert.rejects(admitGeographicReleaseBatches([part],{readBatch:()=>encoded}),/hash mismatch/);
  const correct=gzipSync(decoded);
  await assert.rejects(admitGeographicReleaseBatches([{...part,sha256:sha(correct),payload_sha256:'f'.repeat(64)}],{readBatch:()=>correct}),/payload hash/);
});

test('encoded plus decoded plus derived bytes all count; admission budgets cannot be raised', async () => {
  const bytes=Buffer.from(JSON.stringify(buildCases().row250)),part=descriptor(bytes);
  const {admittedBytes}=await admitGeographicReleaseBatches([part],{readBatch:()=>bytes});
  assert.equal(admittedBytes,bytes.length*3);
  await assert.rejects(admitGeographicReleaseBatches([part],{readBatch:()=>bytes,phaseBytes:admittedBytes-1}),/complete phase budget/);
  await assert.rejects(admitGeographicReleaseBatches([part],{readBatch:()=>bytes,phaseBytes:256*1024*1024+1}),/Invalid.*budget/);
});

test('real publisher entrypoint performs zero writes for late malformed, missing or duplicate inputs', async () => {
  const c=buildCases(),source=Buffer.from(JSON.stringify({sources:[{id:c.release.source_id}]})),definition=Buffer.from(JSON.stringify({release:c.release}));
  for(const kind of ['malformed','missing','duplicate','conflicting-release']){
    const late=kind==='malformed'?c.admissionInputs.at(-1).bytes:Buffer.from(JSON.stringify({release_id:kind==='conflicting-release'?'other':c.release.id,
      memberships:kind==='duplicate'?[c.memberships[0],c.memberships[0]]:[c.memberships[0]]}));
    const bytes=new Map([['sources.json',source],['release-7.json',definition],['7-memberships-final.json',late]]);
    const manifest={releases:[c.release],batches:[descriptor(source,'sources.json','/api/records/import'),descriptor(definition,'release-7.json'),descriptor(late,'7-memberships-final.json')]};
    let writes=0,reads=0;
    const reason={malformed:/JSON|Unexpected|Expected.*property/,missing:/Missing final input/,duplicate:/duplicate.*identity/, 'conflicting-release':/batch release ID mismatch/}[kind];
    await assert.rejects(publishGeographicReleases({manifest,mode:'stage',request:async()=>{reads++;return Response.json(null);},
      batch:async()=>{writes++;},readBatch:p=>{if(kind==='missing'&&p.path==='7-memberships-final.json')throw Error('Missing final input');return bytes.get(p.path);}}),reason);
    assert.equal(writes,0,kind);assert.equal(reads,1);
  }
});

test('independent raw-record oracle rejects coherent missing, reordered and invented output records', () => {
  const c=buildCases();for(const altered of Object.values(c.alteredOutput))assert.throws(()=>assertPreservedRequests(c.partitions,altered));
});
