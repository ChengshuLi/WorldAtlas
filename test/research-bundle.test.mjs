import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {DatabaseSync} from 'node:sqlite';
import {compileResearchInput,prepareResearchBundle,researchHash} from '../scripts/prepare-research-bundle.mjs';
import {readResearchBundle,importResearchBundle} from '../scripts/import-research-bundle.mjs';
import {importBatch,attributesAt,evidenceHistory} from '../hosted/records.js';

const release={id:'geography:test-only',status:'published',footprints_sha256:'a'.repeat(64),hierarchy_sha256:'b'.repeat(64)};
const source={id:'source:test-only',name:'Test-only source',url:'https://example.org/test-only',license:'CC0',vintage:'2026',supported_from:1000,supported_to:1100,status:'historical'};
const claim=(id,value=42)=>({id,location_id:'location',attribute:'population',value,valid_from:1000,valid_to:1100,source_id:source.id});
function fixture(input){const root=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-research-'));const inputPath=path.join(root,'input.json'),output=path.join(root,'bundle');fs.writeFileSync(inputPath,JSON.stringify(input,null,3)+'\n');return {root,inputPath,output,build:options=>prepareResearchBundle({input:inputPath,geography:release,output,...options}),close:()=>fs.rmSync(root,{recursive:true,force:true})};}
class D1 {
 constructor(){this.sqlite=new DatabaseSync(':memory:');this.sqlite.exec('PRAGMA foreign_keys=ON');for(const file of fs.readdirSync(new URL('../drizzle/',import.meta.url)).filter(file=>file.endsWith('.sql')).sort())this.sqlite.exec(fs.readFileSync(new URL(`../drizzle/${file}`,import.meta.url),'utf8'));}
 prepare(sql){const sqlite=this.sqlite;let args=[];return {bind(...values){args=values;return this;},async all(){return {results:sqlite.prepare(sql).all(...args)};},async first(){return sqlite.prepare(sql).get(...args)??null;},run(){return {meta:{changes:Number(sqlite.prepare(sql).run(...args).changes)}};}};}
 async batch(statements){this.sqlite.exec('BEGIN IMMEDIATE');try{const result=statements.map(statement=>statement.run());this.sqlite.exec('COMMIT');return result;}catch(error){this.sqlite.exec('ROLLBACK');throw error;}}
}
test('research compiler produces deterministic bounded batches and preserves exact input/source bytes',()=>{
 const input={sources:[source],names:Array.from({length:410},(_,i)=>({id:`name:${String(i).padStart(3,'0')}`,entity_id:'location',name:`Attested ${i}`,source_id:source.id,valid_from:1000,valid_to:1100}))},f=fixture(input);
 try{fs.writeFileSync(path.join(f.root,'licensed.txt'),'Original source bytes\n');const result=f.build({sourceFiles:[{path:'licensed.txt',source_id:source.id,license:'CC0',redistribution_permitted:true}]});assert.equal(result.batches.length,3);assert.ok(result.batches.every(batch=>batch.rows<=200&&batch.bytes<=1048576));assert.equal(result.input.sha256,researchHash(fs.readFileSync(f.inputPath)));assert.deepEqual(fs.readFileSync(path.join(f.output,'input.json')),fs.readFileSync(f.inputPath));assert.deepEqual(fs.readFileSync(path.join(f.output,result.source_files[0].path)),fs.readFileSync(path.join(f.root,'licensed.txt')));assert.deepEqual(compileResearchInput(input,release).batches.map(batch=>batch.sha256),compileResearchInput({names:[...input.names].reverse(),sources:[source]},release).batches.map(batch=>batch.sha256));assert.equal(readResearchBundle(f.output).batches.length,3);assert.throws(()=>f.build(),/already exists/);}finally{f.close();}
});
test('compiler rejects unsupported classifications, unsupported dates, source classes, cycles and geographic writes',()=>{
 assert.throws(()=>compileResearchInput({sources:[source],records:[{...claim('bad'),attribute:'climate',value:'pleasant'}]},release),/classification/);
 assert.throws(()=>compileResearchInput({sources:[source],records:[{...claim('bad'),valid_from:999}]},release),/source interval/);
 assert.throws(()=>compileResearchInput({sources:[{...source,status:'estimate'}],records:[claim('bad')]},release),/Source class/);
 assert.throws(()=>compileResearchInput({records:[{...claim('bad'),valid_from:0}]},release),/year zero/);
 assert.throws(()=>compileResearchInput({entities:[{id:'b',kind:'person',name:'B',parent_id:'a'},{id:'a',kind:'person',name:'A',parent_id:'b'}]},release),/cycle/);
 assert.throws(()=>compileResearchInput({entities:[{id:'loc',kind:'location',name:'New territory'}]},release),/geographic entities/);
 assert.throws(()=>compileResearchInput({boundaries:[]},release),/Unsupported/);
});
test('parent entities precede child entities and atomic correction groups stay together at batch boundaries',()=>{
 const records=Array.from({length:199},(_,i)=>({...claim(`normal:${i}`),location_id:`location:${i}`})),replacement=claim('replacement'),retirement={id:'withdraw',collection:'records',target_id:'old',replacement_id:'replacement',source_id:source.id,reason:'Test-only sourced correction'};
 const compiled=compileResearchInput({records:[...records,replacement],retirements:[retirement],entities:[{id:'child',kind:'person',name:'Child',parent_id:'parent'},{id:'parent',kind:'person',name:'Parent'}]},release);
 const allEntities=compiled.batches.flatMap(batch=>batch.payload.entities??[]);assert.deepEqual(allEntities.map(row=>row.id),['parent','child']);
 const correction=compiled.batches.find(batch=>batch.payload.retirements);assert.equal(correction.payload.retirements[0].id,'withdraw');assert.ok(correction.payload.records.some(row=>row.id==='replacement'));assert.ok(compiled.batches.every(batch=>batch.rows<=200));
});
test('dry-run rejects tampering and performs zero network requests',async()=>{
 const f=fixture({sources:[source],records:[claim('test')]});try{f.build();const result=await importResearchBundle({directory:f.output,origin:'https://example.org/',dryRun:true,request:()=>{throw Error('Must not request');}});assert.equal(result.network_requests,0);const part=readResearchBundle(f.output).manifest.batches[0];fs.appendFileSync(path.join(f.output,part.path),' ');await assert.rejects(importResearchBundle({directory:f.output,origin:'https://example.org/',dryRun:true}),/bytes changed/);}finally{f.close();}
});
test('import refuses mismatched geography before writes and rejects unsafe origins',async()=>{
 const f=fixture({sources:[source],records:[claim('test')]});try{f.build();let writes=0;await assert.rejects(importResearchBundle({directory:f.output,origin:'https://example.org/',token:'private-token',request:async(url,init)=>{if(init.method)writes++;return Response.json({...release,id:'other'});}}),/does not match/);assert.equal(writes,0);for(const origin of ['http://example.org/','https://user:password@example.org/','https://example.org/path'])await assert.rejects(importResearchBundle({directory:f.output,origin,dryRun:true}),/HTTPS/);}finally{f.close();}
});
test('partial successful receipts survive failure, resumable retry skips committed batches and never logs credentials',async()=>{
 const input={sources:[source],names:Array.from({length:401},(_,i)=>({id:`name:${i}`,entity_id:'location',name:'Attested',source_id:source.id,valid_from:1000,valid_to:1100}))},f=fixture(input),token='private-credential-that-must-not-appear';
 try{f.build();let writes=0;const request=async(url,init)=>{if(url.endsWith('/api/geography/release'))return Response.json(release);writes++;const payload=JSON.parse(init.body);if(writes===2)return new Response(token,{status:409});return Response.json({ingestion_id:payload.ingestion_id,counts:{names:payload.names?.length??0,sources:payload.sources?.length??0},revision:writes,expected_geography:payload.expected_geography});};await assert.rejects(importResearchBundle({directory:f.output,origin:'https://example.org/',token,request}),/\[redacted\]/);const file=path.join(f.output,'import-receipts.json'),partial=JSON.parse(fs.readFileSync(file));assert.equal(partial.batches.length,1);assert.equal(partial.complete,false);assert.equal(fs.readFileSync(file,'utf8').includes(token),false);const result=await importResearchBundle({directory:f.output,origin:'https://example.org/',token,request});assert.equal(result.complete,true);assert.equal(result.committed_batches,3);assert.equal(writes,4,'Failed batch and final batch retry; first committed batch skipped');assert.equal(JSON.parse(fs.readFileSync(file)).complete,true);}finally{f.close();}
});
test('network/transient failures retry an identical ingestion within a bounded budget',async()=>{
 const f=fixture({sources:[source],records:[claim('test')]});try{f.build();let attempts=0;const bodies=[],waits=[];const result=await importResearchBundle({directory:f.output,origin:'https://example.org/',token:'secret',wait:async ms=>waits.push(ms),request:async(url,init)=>{if(url.endsWith('/api/geography/release'))return Response.json(release);bodies.push(init.body.toString());if(++attempts===1)throw Error('Lost network response');if(attempts===2)return new Response('',{status:503});return Response.json({ingestion_id:JSON.parse(init.body).ingestion_id,counts:{sources:1,records:1},revision:1,duplicate:true,expected_geography:JSON.parse(init.body).expected_geography});}});assert.equal(result.complete,true);assert.equal(attempts,3);assert.deepEqual(waits,[500,1000]);assert.equal(new Set(bodies).size,1);}finally{f.close();}
});
test('compiled content imports against actual frozen hosted SQL and preserves corrected evidence immutably',async()=>{
 const db=new D1();try{await importBatch(db,JSON.parse(fs.readFileSync(new URL('../data/hosted-type-catalog.json',import.meta.url))));const tiers=['continent','subcontinent','region','area','province','location'];await importBatch(db,{sources:[source],entities:tiers.map((kind,i)=>({id:kind,kind,name:kind,parent_id:i?tiers[i-1]:null})),records:[claim('old',10)]});const bundle=compileResearchInput({records:[claim('new',20)],retirements:[{id:'retirement',collection:'records',target_id:'old',replacement_id:'new',source_id:source.id,reason:'Test-only correction'}]},release);for(const batch of bundle.batches){assert.equal((await importBatch(db,batch.payload)).duplicate,false);assert.equal((await importBatch(db,batch.payload)).duplicate,true);}assert.equal((await attributesAt(db,1000)).records[0].value,20);assert.equal((await evidenceHistory(db,'records','old')).claim.value,10);assert.equal(db.sqlite.prepare('PRAGMA foreign_key_check').all().length,0);}finally{db.sqlite.close();}
});
test('targets first introduced by a campaign commit before its retirement transaction',async()=>{
 const db=new D1();try{await importBatch(db,JSON.parse(fs.readFileSync(new URL('../data/hosted-type-catalog.json',import.meta.url))));const tiers=['continent','subcontinent','region','area','province','location'];await importBatch(db,{entities:tiers.map((kind,i)=>({id:kind,kind,name:kind,parent_id:i?tiers[i-1]:null}))});const bundle=compileResearchInput({sources:[source],records:[claim('original',10),claim('replacement',20)],retirements:[{id:'retirement',collection:'records',target_id:'original',replacement_id:'replacement',source_id:source.id,reason:'Test-only correction'}]},release);assert.equal(bundle.batches.length,2);assert.equal(bundle.batches[0].payload.records[0].id,'original');assert.equal(bundle.batches[1].payload.retirements[0].target_id,'original');for(const batch of bundle.batches)await importBatch(db,batch.payload);assert.equal((await attributesAt(db,1000)).records[0].value,20);}finally{db.sqlite.close();}
});
test('shared replacements stay atomic and chained corrections respect target availability',()=>{
 const retire=(id,target,replacement)=>({id,collection:'records',target_id:target,replacement_id:replacement,source_id:source.id,reason:'Test-only correction'});
 const result=compileResearchInput({records:[claim('middle'),claim('final')],retirements:[retire('z-first','old','middle'),retire('a-second','middle','final'),retire('b-shared','other','middle')]},release);
 assert.equal(result.batches.length,2);assert.equal(result.batches[0].payload.records[0].id,'middle');assert.equal(result.batches[0].payload.retirements.length,2);assert.equal(result.batches[1].payload.records[0].id,'final');
 assert.throws(()=>compileResearchInput({records:[claim('a'),claim('b')],retirements:[retire('one','a','b'),retire('two','b','a')]},release),/dependency cycle/);
});
test('each research batch carries its geographic pin and a conflict preserves prior receipts',async()=>{
 const f=fixture({sources:[source],names:Array.from({length:201},(_,i)=>({id:`dated:${i}`,entity_id:'location',name:'Test',source_id:source.id,valid_from:1000,valid_to:1100}))});
 try{f.build();let writes=0;const pins=[],request=async(url,init)=>{if(url.endsWith('/api/geography/release'))return Response.json(release);const payload=JSON.parse(init.body);pins.push(payload.expected_geography);if(++writes===2)return Response.json({error:'Published geography changed'}, {status:409});return Response.json({ingestion_id:payload.ingestion_id,expected_geography:payload.expected_geography,counts:{names:payload.names?.length??0},revision:1});};await assert.rejects(importResearchBundle({directory:f.output,origin:'https://example.org/',token:'private',request}),/geography changed/);
  assert.deepEqual(pins,[pins[0],pins[0]]);assert.deepEqual(pins[0],{release_id:release.id,hierarchy_sha256:release.hierarchy_sha256,footprints_sha256:release.footprints_sha256});
  const ledger=JSON.parse(fs.readFileSync(path.join(f.output,'import-receipts.json')));assert.equal(ledger.complete,false);assert.equal(ledger.batches.length,1);assert.deepEqual(ledger.batches[0].expected_geography,pins[0]);assert.match(ledger.batches[0].request_ingestion_id,/:geo:[a-f0-9]{64}$/);
 }finally{f.close();}
});
test('unpinned server receipts are rejected and legacy receipts are preserved while newly pinned transactions verify them',async()=>{
 const f=fixture({sources:[source],records:[claim('test')]});
 try{f.build();const manifest=readResearchBundle(f.output),part=manifest.manifest.batches[0],old={ingestion_id:part.ingestion_id,path:part.path,sha256:part.sha256,rows:part.rows,status:'committed',counts:{sources:1,records:1},revision:7};
  fs.writeFileSync(path.join(f.output,'import-receipts.json'),JSON.stringify({version:1,origin:'https://example.org',manifest_sha256:manifest.manifest_sha256,geography:manifest.manifest.geography,batches:[old],complete:true}));let payload;
  const request=async(url,init)=>{if(url.endsWith('/api/geography/release'))return Response.json(release);payload=JSON.parse(init.body);return Response.json({ingestion_id:payload.ingestion_id,counts:old.counts,revision:8});};await assert.rejects(importResearchBundle({directory:f.output,origin:'https://example.org/',token:'private',request}),/unpinned/);
  assert.deepEqual(JSON.parse(fs.readFileSync(path.join(f.output,'import-receipts.json'))).batches,[old]);
  const good=async(url,init)=>{const response=await request(url,init);if(init.method)return Response.json({ingestion_id:payload.ingestion_id,expected_geography:payload.expected_geography,counts:old.counts,revision:8,duplicate:true});return response;};await importResearchBundle({directory:f.output,origin:'https://example.org/',token:'private',request:good});
  const entry=JSON.parse(fs.readFileSync(path.join(f.output,'import-receipts.json'))).batches[0];assert.deepEqual(entry.previous_unpinned_receipt,old);assert.equal(entry.revision,8);assert.notEqual(entry.request_ingestion_id,part.ingestion_id);
 }finally{f.close();}
});
