import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync,readdirSync,mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {resolveAttributes} from '../src/attributes.js';
import {openDatabase,importRecords} from '../database.mjs';
import {importBatch,attributesAt,evidenceHistory} from '../hosted/records.js';
const features=[{id:'l',properties:{}}];
const record=(id,attribute,value,extra={})=>({id,location_id:'l',attribute,value,valid_from:1000,valid_to:1100,method:'direct',status:'sourced',source:'Explicit source',...extra});
const resolved=records=>resolveAttributes(features,1050,{records}).get('l');
const geometry={type:'Polygon',coordinates:[[[0,0],[1,0],[1,1],[0,0]]]};
const units=[{id:'c',name:'c',level:'continent'},{id:'s',name:'s',level:'subcontinent',parent_id:'c'},{id:'r',name:'r',level:'region',parent_id:'s'},{id:'a',name:'a',level:'area',parent_id:'r'},{id:'p',name:'p',level:'province',parent_id:'a'}];
class D1{
 constructor({beforeRank=false,beforePrecision=false,beforeSourceClass=false}={}){this.sqlite=new DatabaseSync(':memory:');this.sqlite.exec('PRAGMA foreign_keys=ON');for(const f of readdirSync(new URL('../drizzle/',import.meta.url)).filter(f=>f.endsWith('.sql')&&(!beforeRank||Number(f.slice(0,4))<3)&&(!beforePrecision||Number(f.slice(0,4))<4)&&(!beforeSourceClass||Number(f.slice(0,4))<5)).sort())this.sqlite.exec(readFileSync(new URL(`../drizzle/${f}`,import.meta.url),'utf8'));}
 prepare(sql){const sqlite=this.sqlite;let args=[];return {bind(...values){args=values;return this;},async all(){return {results:sqlite.prepare(sql).all(...args)};},async first(){return sqlite.prepare(sql).get(...args)??null;},run(){return {meta:{changes:Number(sqlite.prepare(sql).run(...args).changes)}};}};}
 async batch(statements){this.sqlite.exec('BEGIN IMMEDIATE');try{const result=statements.map(s=>s.run());this.sqlite.exec('COMMIT');return result;}catch(error){this.sqlite.exec('ROLLBACK');throw error;}}
}
async function hostedFixture(options){const db=new D1(options);await importBatch(db,JSON.parse(readFileSync(new URL('../data/hosted-type-catalog.json',import.meta.url))));await importBatch(db,{sources:[{id:'history',name:'Observed historical evidence',url:'https://example.org/census',license:'CC0',vintage:'1000 observed source',supported_from:1000,supported_to:1100,status:'historical'},{id:'review',name:'Review',url:'https://example.org/review',license:'CC0',vintage:'2026',supported_from:2026,supported_to:2027,status:'reference'}],entities:[...units].reverse().map(u=>({id:u.id,kind:u.level,name:u.name,parent_id:u.parent_id??null})).concat([{id:'l',kind:'location',name:'l',parent_id:'p'}])});return db;}
const hosted=r=>({...r,source_id:'history',source:undefined});

test('explicit no-inhabitant evidence produces unsettled with its supported interval and source record provenance',()=>{const habitation=record('none','habitation','uninhabited'),r=resolved([habitation]);assert.equal(r.rank,'unsettled');assert.equal(r.habitation,'uninhabited');assert.equal(r.population,null);assert.equal(r.provenance.rank.method,'derived');assert.equal(r.provenance.rank.metadata.supporting_record_id,'none');assert.equal(r.provenance.rank.valid_from,1000);assert.equal(resolveAttributes(features,1100,{records:[habitation]}).get('l').rank,null);const literal=resolved([record('zero','population',0)]);assert.equal(literal.rank,'unsettled');assert.equal(literal.habitation,null,'habitation remains an independently resolved attribute');assert.equal(literal.provenance.rank.metadata.supporting_attribute,'population');assert.equal(resolved([record('explicit-rank','rank','unsettled')]).provenance.rank.method,'direct');});

test('unknown, reference, modeled, rounded and untyped legacy zeros never imply unsettled',()=>{const cases=[{method:'estimate',status:'estimate'},{method:'reference',status:'reference'},{status:'unknown'},{status:'disputed'},{metadata:{estimate:true}},{metadata:{estimated:true}},{metadata:{modeled:true}},{metadata:{rounded:true}},{metadata:{rounding:'nearest hundred'}},{metadata:{precision:'rounded integer model'}},{metadata:{legacy_snapshot:true}}];for(const extra of cases)assert.equal(resolved([record('zero','population',0,extra)]).rank,null,JSON.stringify(extra));assert.equal(resolved([]).rank,null);assert.equal(resolved([record('unsupported-rank','rank','unsettled',{status:'unknown'})]).rank,null);assert.equal(resolved([record('unsupported-rank','rank','unsettled',{source:null})]).rank,null);assert.equal(resolved([record('unknown-pop','population',null)]).rank,null);assert.equal(resolveAttributes(features,1050,{states:[{id:1,location_id:'l',population:0,source:'Unclassified legacy count',valid_from:1000,valid_to:1100}]}).get('l').rank,null);});

test('settlement contradictions obey cross-field precedence and tied evidence remains disputed',()=>{let r=resolved([record('uninhabited','habitation','uninhabited'),record('city','rank','city',{method:'derived',status:'derived'}),record('estimated-pop','population',100,{method:'estimate',status:'estimate'})]);assert.equal(r.rank,'unsettled');assert.equal(r.population,null);assert.equal(r.provenance.population.status,'disputed');r=resolved([record('population','population',100),record('uninhabited','habitation','uninhabited',{method:'derived',status:'derived'})]);assert.equal(r.rank,null);assert.equal(r.habitation,null);assert.equal(r.population,100);r=resolved([record('city','rank','city'),record('zero','population',0)]);assert.equal(r.rank,null);assert.equal(r.population,null);assert.equal(r.provenance.rank.status,'disputed');const reverse=resolved([record('zero','population',0),record('city','rank','city')]);assert.deepEqual(reverse,r);});

test('local imports accept canonical unsettled, reject both orders of direct contradictions and retain unknown/model-zero behavior',()=>{const db=openDatabase(':memory:');try{importRecords(db,{units,locations:[{id:'l',name:'l',parent_id:'p',geometry}],attribute_records:[record('unsettled','rank','unsettled'),record('habitation','habitation','uninhabited'),record('zero','population',0)]});assert.throws(()=>importRecords(db,{attribute_records:[record('inhabited','habitation','inhabited')]}),/Uninhabited|unsettled/);assert.throws(()=>importRecords(db,{attribute_records:[record('positive','population',1)]}),/Overlapping|Uninhabited|unsettled/);assert.throws(()=>importRecords(db,{states:[{location_id:'l',valid_from:1100,valid_to:1200,rank:'unsettled',population:1,source:'Invalid'}]}),/Unsettled/);assert.throws(()=>importRecords(db,{entity_history:[{id:'bad-history',entity_id:'l',field:'attributes',value:{rank:'unsettled',habitation:'inhabited'},valid_from:1100,valid_to:1200,source:'Invalid'}]}),/Unsettled/);assert.throws(()=>db.prepare('INSERT INTO entity_history(id,entity_id,field,valid_from,valid_to,value,source) VALUES(?,?,?,?,?,?,?)').run('raw-bad','l','attributes',1100,1200,JSON.stringify({rank:'unsettled',population:2}),'Invalid'),/Uninhabited|unsettled/);}finally{db.close();}const other=openDatabase(':memory:');try{importRecords(other,{units,locations:[{id:'l',name:'l',parent_id:'p',geometry}],attribute_records:[record('inhabited','habitation','inhabited')]});assert.throws(()=>importRecords(other,{attribute_records:[record('unset','rank','unsettled')]}),/Uninhabited|unsettled/);importRecords(other,{attribute_records:[record('rounded-zero','population',0,{metadata:{rounded:true}})]});assert.equal(resolved([record('rounded-zero','population',0,{metadata:{rounded:true}})]).rank,null);}finally{other.close();}});

test('hosted imports and shared resolver agree; corrections exclude retired negative claims',async()=>{const db=await hostedFixture();await importBatch(db,{records:[hosted(record('unsettled','rank','unsettled')),hosted(record('habitation','habitation','uninhabited')),hosted(record('zero','population',0))]});let raw=await attributesAt(db,1050);assert.equal(resolveAttributes(features,1050,{records:raw.records}).get('l').rank,'unsettled');await assert.rejects(importBatch(db,{records:[hosted(record('inhabited','habitation','inhabited'))]}),/Overlapping|Uninhabited|unsettled/);const onlyRank=await hostedFixture();await importBatch(onlyRank,{records:[hosted(record('unsettled','rank','unsettled'))]});await assert.rejects(importBatch(onlyRank,{records:[hosted(record('inhabited','habitation','inhabited'))]}),/Uninhabited|unsettled/);await importBatch(db,{retirements:['unsettled','habitation','zero'].map(id=>({id:`retire:${id}`,collection:'records',target_id:id,source_id:'review',reason:'Corrected source',replacement_id:null})),records:[hosted(record('city','rank','city')),hosted(record('positive','population',10)),hosted(record('inhabited','habitation','inhabited'))]});raw=await attributesAt(db,1050);assert.equal(resolveAttributes(features,1050,{records:raw.records}).get('l').rank,'city');assert.equal((await evidenceHistory(db,'records','unsettled')).claim.value,'unsettled');assert.equal((await evidenceHistory(db,'records','unsettled')).status,'withdrawn');});

test('0003 migration preserves all old claim fields, retirement pointers, indexes and triggers',async()=>{const db=await hostedFixture({beforeRank:true});await importBatch(db,{records:[hosted(record('old-pop','population',42)),hosted(record('old-rank','rank','city'))]});await importBatch(db,{retirements:[{id:'retire-old-rank',collection:'records',target_id:'old-rank',source_id:'review',reason:'Audit'}]});const before=JSON.stringify(db.sqlite.prepare('SELECT * FROM atlas_attribute_records ORDER BY id').all()),retirements=JSON.stringify(db.sqlite.prepare('SELECT * FROM atlas_evidence_retirements ORDER BY id').all()),triggers=db.sqlite.prepare("SELECT name FROM sqlite_master WHERE type='trigger' ORDER BY name").all().map(r=>r.name),indexes=db.sqlite.prepare("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='atlas_attribute_records' ORDER BY name").all().map(r=>r.name);db.sqlite.exec(readFileSync(new URL('../drizzle/0003_unsettled_location_rank.sql',import.meta.url),'utf8'));assert.equal(JSON.stringify(db.sqlite.prepare('SELECT * FROM atlas_attribute_records ORDER BY id').all()),before);assert.equal(JSON.stringify(db.sqlite.prepare('SELECT * FROM atlas_evidence_retirements ORDER BY id').all()),retirements);assert.deepEqual(db.sqlite.prepare("SELECT name FROM sqlite_master WHERE type='trigger' ORDER BY name").all().map(r=>r.name),triggers);assert.deepEqual(db.sqlite.prepare("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='atlas_attribute_records' ORDER BY name").all().map(r=>r.name),indexes);assert.deepEqual(db.sqlite.prepare('PRAGMA foreign_key_check').all(),[]);assert.throws(()=>db.sqlite.exec("UPDATE atlas_attribute_records SET value='1' WHERE id='old-pop'"),/append-only/);assert.throws(()=>db.sqlite.exec("DELETE FROM atlas_attribute_records WHERE id='old-pop'"),/retained/);assert.equal((await evidenceHistory(db,'records','old-rank')).status,'withdrawn');});

test('existing local enum migration preserves snapshots/history and enables new rank without touching geometry',()=>{const directory=mkdtempSync(join(tmpdir(),'atlas-rank-')),file=join(directory,'legacy.sqlite');try{const original=new DatabaseSync(file);original.exec(readFileSync(new URL('../data/schema.sql',import.meta.url),'utf8').replaceAll("('unsettled','rural settlement','town','city','metropolis')","('rural settlement','town','city','metropolis')"));importRecords(original,{units,locations:[{id:'l',name:'l',parent_id:'p',geometry}],states:[{location_id:'l',valid_from:1000,valid_to:1100,population:42,rank:'city',source:'Legacy snapshot'}],attribute_records:[record('old','population',42)],entity_history:[{id:'old-name',entity_id:'l',field:'name',value:'Historical label',valid_from:1000,valid_to:1100,source:'Old evidence'}]});const before=Object.fromEntries(['states','attribute_records','entity_history','locations'].map(table=>[table,JSON.stringify(original.prepare(`SELECT * FROM ${table}`).all())]));original.close();const reopened=openDatabase(file);for(const [table,expected] of Object.entries(before))assert.equal(JSON.stringify(reopened.prepare(`SELECT * FROM ${table}`).all()),expected);importRecords(reopened,{attribute_records:[record('new-rank','rank','unsettled',{valid_from:1100,valid_to:1200})],states:[{location_id:'l',valid_from:1100,valid_to:1200,population:0,rank:'unsettled',source:'Explicit no inhabitants'}]});assert.deepEqual(reopened.prepare('PRAGMA foreign_key_check').all(),[]);assert.throws(()=>reopened.exec("UPDATE attribute_records SET value='1' WHERE id='old'"),/append-only/);reopened.close();const again=openDatabase(file);assert.equal(again.prepare("SELECT value FROM attribute_records WHERE id='new-rank'").get().value,'"unsettled"');again.close();}finally{rmSync(directory,{recursive:true,force:true});}});

test('precision flags prevent false habitation conflicts in both local and hosted import orders',async()=>{
 for(const metadata of [{estimate:true},{rounded:true}])for(const zeroFirst of [true,false]){
  const claims=[record('model-zero','population',0,{metadata}),record('inhabited','habitation','inhabited')];
  if(!zeroFirst)claims.reverse();
  const local=openDatabase(':memory:');
  try{
   importRecords(local,{units,locations:[{id:'l',name:'l',parent_id:'p',geometry}]});
   for(const claim of claims)importRecords(local,{attribute_records:[claim]});
   assert.equal(resolved(claims).rank,null);assert.equal(resolved(claims).habitation,'inhabited');
  }finally{local.close();}
  const remote=await hostedFixture();
  try{
   for(const claim of claims)await importBatch(remote,{records:[hosted(claim)]});
   const result=resolveAttributes(features,1050,{records:(await attributesAt(remote,1050)).records}).get('l');
   assert.equal(result.rank,null);assert.equal(result.habitation,'inhabited');
  }finally{remote.sqlite.close();}
 }
 for(const zeroFirst of [true,false]){
  const claims=[record('literal-zero','population',0),record('inhabited','habitation','inhabited')];if(!zeroFirst)claims.reverse();
  const local=openDatabase(':memory:');try{importRecords(local,{units,locations:[{id:'l',name:'l',parent_id:'p',geometry}],attribute_records:[claims[0]]});assert.throws(()=>importRecords(local,{attribute_records:[claims[1]]}),/Uninhabited|unsettled/);}finally{local.close();}
  const remote=await hostedFixture();try{await importBatch(remote,{records:[hosted(claims[0])]});await assert.rejects(importBatch(remote,{records:[hosted(claims[1])]}),/Uninhabited|unsettled/);}finally{remote.sqlite.close();}
 }
});

test('0004 precision migration preserves claims, retirements, indexes and all other triggers',async()=>{
 const db=await hostedFixture({beforePrecision:true});
 try{
  await importBatch(db,{records:[hosted(record('original-pop','population',42)),hosted(record('original-rank','rank','city'))]});
  await importBatch(db,{retirements:[{id:'retire-rank',collection:'records',target_id:'original-rank',source_id:'review',reason:'Correction'}]});
  const rows=table=>JSON.stringify(db.sqlite.prepare(`SELECT * FROM ${table} ORDER BY id`).all()),before=rows('atlas_attribute_records'),retirements=rows('atlas_evidence_retirements');
  const definitions=()=>db.sqlite.prepare("SELECT type,name,sql FROM sqlite_master WHERE type IN ('index','trigger') ORDER BY type,name").all();
  const objects=definitions();
  db.sqlite.exec(readFileSync(new URL('../drizzle/0004_population_precision_guard.sql',import.meta.url),'utf8'));
  assert.equal(rows('atlas_attribute_records'),before);assert.equal(rows('atlas_evidence_retirements'),retirements);
  const after=definitions();assert.deepEqual(after.map(({type,name})=>({type,name})),objects.map(({type,name})=>({type,name})));
  assert.deepEqual(after.filter(row=>row.name!=='atlas_attribute_contract'),objects.filter(row=>row.name!=='atlas_attribute_contract'));
  const trigger=after.find(row=>row.name==='atlas_attribute_contract').sql;assert.match(trigger,/NEW\.metadata,'\$\.estimate'/);assert.match(trigger,/r\.metadata,'\$\.estimate'/);assert.match(trigger,/atlas_evidence_retirements/);
  assert.deepEqual(db.sqlite.prepare('PRAGMA foreign_key_check').all(),[]);
  await importBatch(db,{retirements:[{id:'retire-pop',collection:'records',target_id:'original-pop',source_id:'review',reason:'Correction'}],records:[hosted(record('model-zero','population',0,{metadata:{estimate:true}})),hosted(record('inhabited','habitation','inhabited'))]});
  assert.equal(resolveAttributes(features,1050,{records:(await attributesAt(db,1050)).records}).get('l').rank,null);
  await importBatch(db,{retirements:['model-zero','inhabited'].map(id=>({id:`retire:${id}`,collection:'records',target_id:id,source_id:'review',reason:'Correction'})),records:[hosted(record('literal-zero','population',0))]});
  assert.equal(resolveAttributes(features,1050,{records:(await attributesAt(db,1050)).records}).get('l').rank,'unsettled');
  assert.equal((await evidenceHistory(db,'records','original-rank')).status,'withdrawn');
  assert.throws(()=>db.sqlite.exec("UPDATE atlas_attribute_records SET value='1' WHERE id='original-pop'"),/append-only/);
 }finally{db.sqlite.close();}
});

test('source classes protect literal-zero evidence and example opt-in at the SQL boundary',async()=>{
 const db=await hostedFixture();try{
  await importBatch(db,{sources:['estimate','reference','example'].map(status=>({id:`class:${status}`,name:`${status} source`,url:'https://example.org/source-class',license:'CC0',vintage:'Test source',supported_from:1000,supported_to:1100,status}))});
  for(const sourceClass of ['estimate','reference'])await assert.rejects(importBatch(db,{records:[{...hosted(record(`bad:${sourceClass}`,'population',0)),source_id:`class:${sourceClass}`}]}),/Source class/);
  const claim={...hosted(record('example-zero','population',0)),source_id:'class:example'};
  await assert.rejects(importBatch(db,{records:[claim]}),/opt-in/);
  assert.throws(()=>db.sqlite.prepare('INSERT INTO atlas_attribute_records(id,location_id,attribute,value,valid_from,valid_to,method,status,source_id,is_example,metadata) VALUES(?,?,?,?,?,?,?,?,?,?,?)').run('raw-example','l','population','0',1000,1100,'direct','sourced','class:example',0,'{}'),/opt-in/);
  await assert.rejects(importBatch(db,{names:[{id:'example-name',entity_id:'l',name:'Fictional name',valid_from:1000,valid_to:1100,source_id:'class:example',is_example:0}]}),/opt-in/);
  await importBatch(db,{records:[{...claim,is_example:1}]});
  assert.equal((await attributesAt(db,1050)).records.length,0);
  const rows=(await attributesAt(db,1050,{examples:true})).records;
  assert.equal(rows[0].source_status,'example');assert.equal(resolveAttributes(features,1050,{records:rows,examples:true}).get('l').rank,null);
  await importBatch(db,{records:[{...hosted(record('example-city','rank','city')),source_id:'class:example',is_example:1}]});
  assert.equal(resolveAttributes(features,1050,{records:(await attributesAt(db,1050,{examples:true})).records,examples:true}).get('l').rank,'city');
 }finally{db.sqlite.close();}
 const reverse=await hostedFixture();try{
  await importBatch(reverse,{sources:[{id:'class:example',name:'Example source',url:'https://example.org/source-class',license:'CC0',vintage:'Test source',supported_from:1000,supported_to:1100,status:'example'}],records:[{...hosted(record('example-city','rank','city')),source_id:'class:example',is_example:1}]});
  await importBatch(reverse,{records:[{...hosted(record('example-zero','population',0)),source_id:'class:example',is_example:1}]});
  assert.equal(resolveAttributes(features,1050,{records:(await attributesAt(reverse,1050,{examples:true})).records,examples:true}).get('l').rank,'city');
 }finally{reverse.sqlite.close();}
});

test('0005 source-class migration preserves claims and retirement-aware contracts while matching example-zero resolution',async()=>{
 const db=await hostedFixture({beforeSourceClass:true});try{
  await importBatch(db,{sources:[{id:'class:example',name:'Example source',url:'https://example.org/source-class',license:'CC0',vintage:'Test source',supported_from:1000,supported_to:1100,status:'example'}],records:[hosted(record('original-pop','population',42)),hosted(record('original-rank','rank','city'))]});
  await importBatch(db,{retirements:[{id:'retire-original-rank',collection:'records',target_id:'original-rank',source_id:'review',reason:'Correction fixture'}]});
  const rows=table=>JSON.stringify(db.sqlite.prepare(`SELECT * FROM ${table} ORDER BY id`).all()),before=rows('atlas_attribute_records'),retirements=rows('atlas_evidence_retirements');
  const definitions=()=>db.sqlite.prepare("SELECT type,name,sql FROM sqlite_master WHERE type IN ('index','trigger') ORDER BY type,name").all(),objects=definitions();
  db.sqlite.exec(readFileSync(new URL('../drizzle/0005_population_source_class_guard.sql',import.meta.url),'utf8'));
  assert.equal(rows('atlas_attribute_records'),before);assert.equal(rows('atlas_evidence_retirements'),retirements);
  const after=definitions();assert.deepEqual(after.map(({type,name})=>({type,name})),objects.map(({type,name})=>({type,name})));
  assert.deepEqual(after.filter(row=>row.name!=='atlas_attribute_contract'),objects.filter(row=>row.name!=='atlas_attribute_contract'));
  assert.deepEqual(db.sqlite.prepare('PRAGMA foreign_key_check').all(),[]);
  const example={source_id:'class:example',is_example:1};
  await importBatch(db,{records:[{...hosted(record('example-zero','population',0)),...example},{...hosted(record('example-city','rank','city')),...example}]});
  assert.equal(resolveAttributes(features,1050,{records:(await attributesAt(db,1050,{examples:true})).records,examples:true}).get('l').rank,'city');
  await importBatch(db,{retirements:[{id:'retire-original-pop',collection:'records',target_id:'original-pop',source_id:'review',reason:'Correction fixture'}],records:[hosted(record('literal-zero','population',0))]});
  assert.equal(resolveAttributes(features,1050,{records:(await attributesAt(db,1050)).records}).get('l').rank,'unsettled');
  assert.equal((await evidenceHistory(db,'records','original-rank')).status,'withdrawn');
  assert.throws(()=>db.sqlite.exec("UPDATE atlas_attribute_records SET value='1' WHERE id='original-pop'"),/append-only/);
 }finally{db.sqlite.close();}
});
