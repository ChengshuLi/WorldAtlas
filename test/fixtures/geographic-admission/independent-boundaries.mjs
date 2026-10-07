// Reviewer-supplied inputs/oracles, not a proposed splitter interface.
// Import buildCases/assertPreservedRequests in a future test adapter, or run this
// with Node24 from an owned pinned review checkout to check the existing consumer.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL,fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
const sha=b=>createHash('sha256').update(b).digest('hex');
export const wireBytes=p=>Buffer.byteLength(JSON.stringify(p),'utf8');
export const combinedRows=p=>(p.memberships??[]).length+(p.changes??[]).length+Number(Boolean(p.release));
export function releaseDefinition(){return {id:'release:review:1266',source_id:'source:review:1266',version:7,reference_date:'2026-10-07',hierarchy_sha256:'a'.repeat(64),footprints_sha256:'b'.repeat(64),membership_sha256:'c'.repeat(64),location_ids_sha256:'d'.repeat(64),changes_sha256:'e'.repeat(64),expected_counts:{continent:6,subcontinent:1,region:1,area:1,province:1,location:495},metadata:{fixture:true,original_source:'原資料',unknown:null,order:[2,1]}};}
export const membership=i=>({entity_id:`territory:界:${String(i).padStart(4,'0')}`,parent_id:null,reference_name:`Original 名 ${i}`,active:1,source_id:'source:review:1266',evidence:{source_record_id:`原:${i}`,sequence:[2,1],supported:null,metadata:{z:1,a:'unchanged'}}});
export function buildCases(){
 const r=releaseDefinition(),ms=Array.from({length:505},(_,i)=>membership(i));
 const change={id:'change:review:1',old_entity_id:ms[0].entity_id,new_entity_id:ms[1].entity_id,change_type:'rename',source_id:r.source_id,evidence:{note:'original change'}};
 const hugeEvidence={note:'界'.repeat(16373)};
 assert.equal(JSON.stringify(hugeEvidence).length,16384);
 const unicode={ingestion_id:'unicode-valid-records',release:r,memberships:ms.slice(0,24).map(row=>({...row,evidence:structuredClone(hugeEvidence)}))};
 assert.ok(wireBytes(unicode)>1048576);assert.ok(JSON.stringify(unicode).length<1048576);
 // Complete envelope bytes, including the2000-character ingestion ID, are counted.
 const exact={ingestion_id:'i'.repeat(2000),release:r,memberships:[...ms.slice(0,21).map(row=>({...row,evidence:structuredClone(hugeEvidence)})),{...ms[21],evidence:{note:''}}]};
 const padding=1048576-wireBytes(exact);assert.ok(padding>=0&&padding<=16373,padding);
 exact.memberships.at(-1).evidence.note='A'.repeat(padding);assert.equal(wireBytes(exact),1048576);
 const idOverflow=structuredClone(exact);idOverflow.ingestion_id='é'+idOverflow.ingestion_id.slice(1);
 assert.equal(idOverflow.ingestion_id.length,2000);assert.equal(wireBytes(idOverflow),1048577);assert.equal(JSON.stringify(idOverflow).length,JSON.stringify(exact).length);
 const partitions=[ms.slice(0,250),ms.slice(250,500),ms.slice(500)].map((memberships,i)=>({ingestion_id:`independent-partial-replay-${i}`,release_id:r.id,memberships}));
 const lateMalformed=Buffer.from('{"memberships":[{"entity_id":"late"}');
 return {release:r,memberships:ms,partitions,unicode,exact,idOverflow,
  row250:{ingestion_id:'row250',release:r,memberships:ms.slice(0,249)},
  row251:{ingestion_id:'row251',release:r,memberships:ms.slice(0,250)},
  mixed250:{ingestion_id:'mixed250',release:r,memberships:ms.slice(0,248),changes:[change]},
  mixed251:{ingestion_id:'mixed251',release:r,memberships:ms.slice(0,249),changes:[change]},
  admissionInputs:[{name:'early-valid.json',bytes:Buffer.from(JSON.stringify({release:r}))},{name:'middle-valid.json',bytes:Buffer.from(JSON.stringify({release_id:r.id,memberships:ms.slice(0,250)}))},{name:'late-malformed.json',bytes:lateMalformed,sha256:sha(lateMalformed)}],
  alteredOutput:{missing:partitions.map((p,i)=>({...p,memberships:i===1?p.memberships.slice(1):p.memberships})),reordered:partitions.map((p,i)=>({...p,memberships:i===0?[p.memberships[1],p.memberships[0],...p.memberships.slice(2)]:p.memberships})),metadata:partitions.map((p,i)=>({...p,memberships:i===2?p.memberships.map((row,j)=>j===0?{...row,evidence:{...row.evidence,supported:'invented'}}:row):p.memberships}))}};
}
// Adapt candidate outputs to actual complete request payloads before using this oracle.
// This does not prescribe planning/function names, chunk counts, or an ID formula.
export function assertPreservedRequests(originalPayloads,emittedPayloads){
 for(const p of emittedPayloads){assert.ok(combinedRows(p)<=250);assert.ok(wireBytes(p)<=1048576);assert.ok(typeof p.ingestion_id==='string'&&p.ingestion_id.length&&p.ingestion_id.length<=2000);}
 assert.equal(new Set(emittedPayloads.map(p=>p.ingestion_id)).size,emittedPayloads.length,'Distinct emitted bodies need distinct replay identities');
 for(const field of ['memberships','changes'])assert.deepEqual(emittedPayloads.flatMap(p=>(p[field]??[]).map(row=>JSON.stringify(row))),originalPayloads.flatMap(p=>(p[field]??[]).map(row=>JSON.stringify(row))),'Full raw record/key order, sequence and metadata differ: '+field);
 assert.deepEqual(emittedPayloads.filter(p=>p.release).map(p=>JSON.stringify(p.release)),originalPayloads.filter(p=>p.release).map(p=>JSON.stringify(p.release)),'Release definitions/predecessor metadata changed');
}
async function selfCheck(){
 const {stageGeographicRelease}=await import(pathToFileURL(path.resolve('hosted/geographic-releases.js')));
 const c=buildCases();let controls=0;
 for(const[p,message,status]of[[c.row251,/250/,400],[c.mixed251,/250/,400],[c.unicode,/1 MiB/,413],[c.idOverflow,/1 MiB/,413]]){
  let reads=0;const db=new Proxy({}, {get(){reads++;throw Error('DB sentinel');}});
  await assert.rejects(stageGeographicRelease(db,p),e=>e.status===status&&message.test(e.message));assert.equal(reads,0);controls++;
 }
 for(const p of[c.row250,c.mixed250,c.exact]){
  let reads=0;const db=new Proxy({}, {get(){reads++;throw Error('DB sentinel');}});
  await assert.rejects(stageGeographicRelease(db,p),/DB sentinel/);assert.equal(reads,1);controls++;
 }
 assertPreservedRequests(c.partitions,c.partitions);controls++;
 for(const p of Object.values(c.alteredOutput)){assert.throws(()=>assertPreservedRequests(c.partitions,p));controls++;}
 assert.throws(()=>JSON.parse(c.admissionInputs.at(-1).bytes));assert.equal(sha(c.admissionInputs.at(-1).bytes),c.admissionInputs.at(-1).sha256);controls++;
 console.log({consumer_controls:controls,unicode_metadata_js_length:JSON.stringify(c.unicode.memberships[0].evidence).length,unicode_metadata_utf8_bytes:wireBytes(c.unicode.memberships[0].evidence),unicode_payload_utf8_bytes:wireBytes(c.unicode),unicode_payload_js_length:JSON.stringify(c.unicode).length,exact_envelope_bytes:wireBytes(c.exact),changed_id_only_bytes:wireBytes(c.idOverflow),late_malformed_digest_coherent:true,limits:'Positive sentinel proves pre-SQL admission only; future planner zero-write/replay tests have not run.'});
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url))await selfCheck();
