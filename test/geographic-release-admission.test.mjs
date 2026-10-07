import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {gzipSync} from 'node:zlib';
import {splitGeographicReleaseBatch,admitGeographicReleaseBatches} from '../scripts/geographic-release-admission.mjs';
import {publishGeographicReleases} from '../scripts/bootstrap-geographic-release.mjs';
import {stageGeographicRelease,geographicMembershipHash,geographicLocationIdsHash,geographicChangesHash} from '../hosted/geographic-releases.js';
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
  let reads=0;const {plan}=await admitGeographicReleaseBatches([part],{releases:[buildCases().release],readBatch:()=>{reads++;return encoded;}});
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
  const c=buildCases(),source=Buffer.from(JSON.stringify({sources:[{id:c.release.source_id,name:'Isolated reference fixture',url:'https://example.invalid/source',license:'CC0 fixture',vintage:'2026',status:'reference',supported_from:2026,supported_to:2027}]})),definition=Buffer.from(JSON.stringify({release:c.release}));
  for(const kind of ['malformed','missing','duplicate','conflicting-release']){
    const late=kind==='malformed'?c.admissionInputs.at(-1).bytes:Buffer.from(JSON.stringify({release_id:kind==='conflicting-release'?'other':c.release.id,
      memberships:kind==='duplicate'?[c.memberships[0],c.memberships[0]]:[c.memberships[0]]}));
    const bytes=new Map([['sources.json',source],['release-7.json',definition],['7-memberships-final.json',late]]);
    const manifest={releases:[c.release],batches:[descriptor(source,'sources.json','/api/records/import'),descriptor(definition,'release-7.json'),descriptor(late,'7-memberships-final.json')]};
    let writes=0,reads=0;
    const reason={malformed:/JSON|Unexpected|Expected.*property/,missing:/Missing final input/,duplicate:/duplicate.*identity/, 'conflicting-release':/Unknown staged release/}[kind];
    await assert.rejects(publishGeographicReleases({manifest,mode:'stage',request:async()=>{reads++;return Response.json(null);},
      batch:async()=>{writes++;},readBatch:p=>{if(kind==='missing'&&p.path==='7-memberships-final.json')throw Error('Missing final input');return bytes.get(p.path);}}),reason);
    assert.equal(writes,0,kind);assert.equal(reads,1);
  }
});

test('independent raw-record oracle rejects coherent missing, reordered and invented output records', () => {
  const c=buildCases();for(const altered of Object.values(c.alteredOutput))assert.throws(()=>assertPreservedRequests(c.partitions,altered));
});

test('later source field failures and entity cycles are rejected before any earlier prerequisite writes', async () => {
  const source={id:'reference',name:'Fixture',license:'CC0',vintage:'2026',status:'reference',supported_from:2026,supported_to:2027};
  const early=Buffer.from(JSON.stringify({sources:[source]})),release=buildCases().release,definition=Buffer.from(JSON.stringify({release}));
  for(const [late,path,reason] of [
    [{sources:[{...source,id:'later',license:''}]},'sources-7.json',/source license/],
    [{sources:[{...source,id:'later',supported_from:0}]},'sources-7.json',/date interval/],
    [{entities:[{id:'first',kind:'location',name:'First',parent_id:'second'},{id:'second',kind:'province',name:'Second',parent_id:'first'}]},'entities-location-0.json',/parent cycle/]]){
    const bytes=Buffer.from(JSON.stringify(late)),parts=[descriptor(early,'sources.json','/api/records/import'),descriptor(bytes,path,'/api/records/import'),descriptor(definition,'release-7.json')];
    let writes=0;
    await assert.rejects(publishGeographicReleases({manifest:{releases:[release],batches:parts,sources_batches:path.startsWith('sources-')?['sources.json',path]:['sources.json']},mode:'stage',
      request:async()=>Response.json(null),readBatch:p=>p.path==='sources.json'?early:p.path==='release-7.json'?definition:bytes,batch:async()=>{writes++;}}),reason);
    assert.equal(writes,0);
  }
});

test('empty release inventory cannot produce a vacuous completed stage', async () => {
  let calls=0;await assert.rejects(publishGeographicReleases({manifest:{releases:[],batches:[{path:'sources.json'}]},batch:async()=>calls++,request:async()=>calls++}),/Nonempty/);assert.equal(calls,0);
});

test('independent coherently pinned invalid staging fields reject before prerequisite writes', async () => {
for(const kind of ['member-reference-name','change-type','release-calendar-date']){
 const c=buildCases(),release=structuredClone(c.release),members=[structuredClone(c.memberships[0])],changes=[];
 if(kind==='member-reference-name')members[0].reference_name='x'.repeat(2001);
 if(kind==='change-type')changes.push({id:'bad-change',change_type:37,source_id:release.source_id,evidence:{}});
 if(kind==='release-calendar-date')release.reference_date='2026-02-30';
 release.membership_sha256=await geographicMembershipHash(members);
 release.location_ids_sha256=await geographicLocationIdsHash(members);
 release.changes_sha256=await geographicChangesHash(changes);
 const payloads=[['sources.json','/api/records/import',{sources:[{id:release.source_id,name:'fixture',license:'CC0',vintage:'2026',status:'reference',supported_from:2026,supported_to:2027}]}],['release-7.json','/api/geography/stage',{release}],['7-memberships-late.json','/api/geography/stage',{release_id:release.id,memberships:members,changes}]];
 const inputs=new Map(payloads.map(([p,r,v])=>[p,Buffer.from(JSON.stringify(v))]));
 const parts=payloads.map(([path,route])=>({path,route,sha256:sha(inputs.get(path))}));
 const writes=[];
 const db={prepare(sql){return {bind(){return this;},async first(){return sql.includes('atlas_geographic_releases')?{...release,status:'staged'}:null;}};},async batch(){return [];}};
 let error;
 try{await publishGeographicReleases({manifest:{releases:[release],batches:parts},mode:'stage',concurrency:1,request:async()=>Response.json(null),readBatch:p=>inputs.get(p.path),batch:async(p,b)=>{writes.push(p.path);if(p.route==='/api/geography/stage')return stageGeographicRelease(db,JSON.parse(b));}});}catch(e){error=e.message;}
 assert.match(error, /Invalid reference name|Invalid change type|ISO calendar date/);assert.deepEqual(writes,[]);

}

});

test('independent delayed parent transports preserve global source order at default concurrency', async () => {
const c=buildCases(),members=c.memberships,release={...c.release,membership_sha256:await geographicMembershipHash(members),location_ids_sha256:await geographicLocationIdsHash(members),changes_sha256:await geographicChangesHash([])};
const rows=[['sources.json','/api/records/import',{sources:[{id:release.source_id,name:'fixture',license:'CC0',vintage:'2026',status:'reference',supported_from:2026,supported_to:2027}]}],['release-7.json','/api/geography/stage',{release}],['7-memberships-a.json','/api/geography/stage',{release_id:release.id,memberships:members.slice(0,251)}],['7-memberships-b.json','/api/geography/stage',{release_id:release.id,memberships:members.slice(251)}]];
const bytes=new Map(rows.map(([p,r,b])=>[p,Buffer.from(JSON.stringify(b))]));const manifest={releases:[release],batches:rows.map(([path,route])=>({path,route,sha256:createHash('sha256').update(bytes.get(path)).digest('hex')}))};
for(const concurrency of [1,6]){
 const observed=[],dispatch=[];
 await publishGeographicReleases({manifest,mode:'stage',concurrency,request:async()=>Response.json(null),readBatch:p=>bytes.get(p.path),batch:async(p,b)=>{const value=JSON.parse(b);if(!value.memberships)return;dispatch.push({path:p.path,first:value.memberships[0].entity_id});if(p.path.endsWith('a.json'))await new Promise(r=>setTimeout(r,30));observed.push(...value.memberships);}});

 assert.equal(observed.length,members.length);assert.deepEqual(observed,members);
}

});

test('complete descriptor admission rejects oversized inventory before reading any inputs', async () => {
 let reads=0;
 await assert.rejects(admitGeographicReleaseBatches(Array.from({length:513},()=>({})),{readBatch:()=>{reads++;}}),/complete phase descriptor budget/);
 assert.equal(reads,0);
});
