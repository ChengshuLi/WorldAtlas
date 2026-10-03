import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,readdirSync} from 'node:fs';
import {DatabaseSync} from 'node:sqlite';
import {performance} from 'node:perf_hooks';
import {importBatch,attributesAt,namesAt,entityProfile} from '../hosted/records.js';
import {mapSnapshotPage,hydrateMapSnapshotPage,mapSnapshotQueries} from '../hosted/map-snapshots.js';
import {resolveAttributes,locationAttributes} from '../src/attributes.js';
import {resolveTemporal} from '../src/temporal.js';
import {mergePreparedEvidence} from '../src/prepared-evidence.js';

class D1{
 constructor(){this.sqlite=new DatabaseSync(':memory:');this.sqlite.exec('PRAGMA foreign_keys=ON');for(const file of readdirSync(new URL('../drizzle/',import.meta.url)).filter(f=>f.endsWith('.sql')).sort())this.sqlite.exec(readFileSync(new URL(`../drizzle/${file}`,import.meta.url),'utf8'));this.calls=[];this.onQuery=null;}
 prepare(sql){const db=this;let args=[];return {bind(...values){args=values;return this;},async all(){db.calls.push(sql);const rows=db.sqlite.prepare(sql).all(...args);db.onQuery?.(sql);return {results:rows};},async first(){db.calls.push(sql);const row=db.sqlite.prepare(sql).get(...args)??null;db.onQuery?.(sql);return row;},run(){return {meta:{changes:Number(db.sqlite.prepare(sql).run(...args).changes)}};}};}
 async batch(statements){this.sqlite.exec('BEGIN IMMEDIATE');try{const result=statements.map(s=>s.run());this.sqlite.exec('COMMIT');return result;}catch(error){this.sqlite.exec('ROLLBACK');throw error;}}
}
const source=(id,status='historical',metadata={})=>({id,name:`Source ${id}`,url:'https://example.org/source',license:'CC0',vintage:'2026',supported_from:-3000,supported_to:2027,status,metadata});
const record=(id,attribute,value,extra={})=>({id,location_id:'L0000',attribute,value,valid_from:1000,valid_to:1100,source_id:'historical',...extra});
const name=(id,entity_id='L0000',extra={})=>({id,entity_id,name:id,language:'en',valid_from:1000,valid_to:1100,source_id:'historical',...extra});
const feature=id=>({id,properties:{name:id}});
async function fixture(){const db=new D1();await importBatch(db,JSON.parse(readFileSync(new URL('../data/hosted-type-catalog.json',import.meta.url))));const tiers=['continent','subcontinent','region','area','province'];await importBatch(db,{sources:[source('historical'),source('reference','reference'),source('example','example')],entities:[...tiers.map((kind,i)=>({id:`z-${kind}`,kind,name:kind,parent_id:i?`z-${tiers[i-1]}`:null})),{id:'L0000',kind:'location',name:'Modern location',parent_id:'z-province'},{id:'z-settlement',kind:'settlement',name:'Settlement',parent_id:'L0000'},{id:'person',kind:'person',name:'Person'}],categories:['owner','culture','religion'].map(kind=>({id:`${kind}:a`,kind,name:`${kind} A`,source_id:'historical'}))});return db;}
const close=fn=>async()=>{const db=await fixture();try{await fn(db);}finally{db.sqlite.close();}};

test('evidence-only pages omit empty identities but retain withdrawal-only subjects and complete claims',close(async db=>{
 await importBatch(db,{entities:[{id:'empty',kind:'location',name:'Empty',parent_id:'z-province'}],records:[record('withdrawn-only','population',50),record('tier-value','population',60,{location_id:'empty'})],names:[name('withdrawn-name','z-province'),name('preferred','z-area'),name('alias','z-area',{role:'alias'}),name('example-only','z-settlement',{source_id:'example',is_example:1})]});
 await importBatch(db,{retirements:[{id:'withdraw-pop',collection:'records',target_id:'withdrawn-only',source_id:'historical',reason:'Withdrawn without replacement'},{id:'withdraw-name',collection:'names',target_id:'withdrawn-name',source_id:'historical',reason:'Withdrawn without replacement'}]});
 const full=hydrateMapSnapshotPage(await mapSnapshotPage(db,1000));
 const pages=[];let cursor='';do{const page=hydrateMapSnapshotPage(await mapSnapshotPage(db,1000,{evidenceOnly:true,limit:1,cursor}));pages.push(page);cursor=page.next_cursor??'';}while(cursor);
 assert.deepEqual(pages.flatMap(p=>p.entities.map(e=>e.id)),['L0000','empty','z-area','z-province']);
 for(const key of ['records','names','retirements'])assert.deepEqual(pages.flatMap(p=>p[key]).sort((a,b)=>a.id.localeCompare(b.id)),full[key].sort((a,b)=>a.id.localeCompare(b.id)));
 const retired=pages.find(p=>p.entities[0].id==='L0000');assert.equal(retired.records.length,0);assert.equal(retired.retirements[0].target_id,'withdrawn-only');
 assert.equal(mergePreparedEvidence([],[],{records:[record('withdrawn-only','population',50)],names:[]},{retirements:retired.retirements}).records.length,0);
 assert.ok((await mapSnapshotPage(db,1000,{evidenceOnly:true,examples:true})).entities.some(e=>e.id==='z-settlement'));
 const empty=await mapSnapshotPage(db,1100,{evidenceOnly:true});assert.deepEqual(empty.entities,[]);assert.equal(empty.next_cursor,null);
}));

test('entity pages return exactly shared whole-location winners, source dictionaries and all-tier preferred names',close(async db=>{
 await importBatch(db,{records:[record('a-owner-derived','owner','owner A',{category_id:'owner:a',method:'majority-area',metadata:{winning_share:.6}}),record('z-owner-explicit-unknown','owner',null),record('a-religion-ref','religion','religion A',{category_id:'religion:a',method:'reference',source_id:'reference'}),record('z-religion-direct','religion','religion A',{category_id:'religion:a'}),record('a-climate-estimate','climate','oceanic',{method:'estimate'}),record('z-climate-disputed','climate',null,{status:'disputed'}),record('population','population',42054),record('habitation','habitation','inhabited'),record('rank','rank','city'),record('topography','topography','flat'),record('vegetation','vegetation','farmlands'),record('example-owner','owner','owner A',{category_id:'owner:a',is_example:1,source_id:'example'})],names:[...['L0000','z-province','z-area','z-region','z-subcontinent','z-continent','z-settlement'].map(id=>name(`historic-${id}`,id,{language:id==='L0000'?'und':'en'})),name('a-reference','L0000',{language:'en',source_id:'reference'}),name('z-direct-local','L0000',{language:'zh'}),name('person-name','person')]});
 const page=await mapSnapshotPage(db,1000,{examples:true}),hydrated=hydrateMapSnapshotPage(page),full=(await attributesAt(db,1000,{examples:true})).records;
 assert.equal(page.entities.length,7);assert.equal(page.names.length,7);assert.ok(!page.names.some(row=>row.entity_id==='person'));assert.ok(!page.records.some(row=>Object.hasOwn(row,'source_metadata')));assert.equal(Object.keys(page.sources).length,1);
 assert.equal(new Set(page.records.map(row=>`${row.location_id}/${row.attribute}`)).size,page.records.length);
 assert.equal(page.records.find(row=>row.attribute==='owner').id,'z-owner-explicit-unknown');assert.equal(page.records.find(row=>row.attribute==='climate').value,null);
 assert.deepEqual(resolveAttributes([feature('L0000')],1000,{records:hydrated.records,examples:true}),resolveAttributes([feature('L0000')],1000,{records:full,examples:true}));
 const allNames=(await namesAt(db,1000,{examples:true,mapOnly:true})).records;
 const temporal={entities:page.entities.map(e=>({...e,name:e.id})),history:allNames,links:[]},reference={units:[],features:[feature('L0000')],temporal};
 const compact=resolveTemporal({...reference,temporal:{...temporal,history:hydrated.names}},1000,true),complete=resolveTemporal(reference,1000,true);
 for(const e of page.entities)assert.equal(compact.entities.get(e.id).display_name,complete.entities.get(e.id).display_name);
 assert.equal((await mapSnapshotPage(db,1100)).records.length,0);await assert.rejects(mapSnapshotPage(db,0),/year/);
}));

test('entity cursor pages never split an attribute set and preserve aliases, examples, lifetimes and end sentinels',close(async db=>{
 await importBatch(db,{entities:[{id:'expired',kind:'settlement',name:'Expired',parent_id:'L0000',valid_from:900,valid_to:1000,source_id:'historical'},{id:'example-settlement',kind:'settlement',name:'Example',parent_id:'L0000',is_example:1}],records:[record('pop','population',1)],names:[...Array.from({length:7},(_,i)=>name(`alias-${i}`,'L0000',{role:'alias'})),name('example-name','z-settlement',{is_example:1,source_id:'example'})]});
 const gathered=[],records=[];let cursor='';do{const page=await mapSnapshotPage(db,1000,{limit:1,cursor});gathered.push(...page.entities.map(e=>e.id));records.push(...page.records);if(page.entities[0]?.id==='L0000'){assert.equal(page.names.length,5);assert.deepEqual(page.aliases_truncated,['L0000']);}cursor=page.next_cursor??'';}while(cursor);
 assert.equal(gathered.length,7);assert.equal(new Set(gathered).size,7);assert.ok(!gathered.includes('expired'));assert.ok(!gathered.includes('example-settlement'));assert.equal(records.length,1);
 const examples=await mapSnapshotPage(db,1000,{examples:true,aliasLimit:0});assert.ok(examples.entities.some(e=>e.id==='example-settlement'));assert.ok(examples.names.some(n=>n.id==='example-name'));assert.ok(examples.aliases_truncated.includes('L0000'));
 for(const options of [{limit:0},{limit:1001},{aliasLimit:6},{cursor:3}])await assert.rejects(mapSnapshotPage(db,1000,options),/limit|cursor/);
 await assert.rejects(mapSnapshotPage(db,0),/year/);assert.equal((await mapSnapshotPage(db,-1)).year,-1);assert.equal((await mapSnapshotPage(db,2026)).year,2026);
}));

test('inactive archived identities stay inspectable without inflating fixed-geography map pages',close(async db=>{
 await importBatch(db,{entities:[{id:'archived',kind:'location',name:'Archived territory',parent_id:'z-province',active:0}],records:[record('archived-pop','population',20,{location_id:'archived'})],names:[name('archived-name','archived')]});
 const page=await mapSnapshotPage(db,1000);assert.ok(!page.entities.some(row=>row.id==='archived'));assert.ok(!page.records.some(row=>row.location_id==='archived'));assert.ok(!page.names.some(row=>row.entity_id==='archived'));
 assert.equal((await entityProfile(db,'archived',1000)).display_name,'archived-name');assert.ok((await namesAt(db,1000,{mapOnly:true})).records.some(row=>row.entity_id==='archived'));assert.equal(db.sqlite.prepare("SELECT count(*) n FROM atlas_attribute_records WHERE id='archived-pop'").get().n,1);
}));

test('page withdrawals suppress prepared fallback claims for attributes and names with no wrong truncation',close(async db=>{
 const withdrawn=record('withdrawn','population',50),oldName=name('old-name');await importBatch(db,{records:[withdrawn],names:[oldName]});
 await importBatch(db,{records:[record('replacement','population',40)],names:[name('replacement-name')],retirements:[{id:'retire-pop',collection:'records',target_id:'withdrawn',source_id:'historical',reason:'Corrected observation',replacement_id:'replacement'},{id:'retire-name',collection:'names',target_id:'old-name',source_id:'historical',reason:'Corrected attestation',replacement_id:'replacement-name'}]});
 const hydrated=hydrateMapSnapshotPage(await mapSnapshotPage(db,1000,{limit:1}));assert.equal(hydrated.retirements.length,2);assert.equal(hydrated.records[0].id,'replacement');assert.equal(hydrated.names[0].id,'replacement-name');
 const merged=mergePreparedEvidence(hydrated.records,hydrated.names,{records:[withdrawn],names:[{...oldName,field:'name',value:oldName.name}]},{retirements:hydrated.retirements});
 assert.deepEqual(merged.records.map(row=>row.id),['replacement']);assert.deepEqual(merged.names.map(row=>row.id),['replacement-name']);assert.equal((await mapSnapshotPage(db,1100)).retirements.length,0);
}));

test('metadata summarization preserves all no-inhabitants proof semantics and points to original evidence',close(async db=>{
 const data={details:'x'.repeat(2000),precision:'c'.repeat(700)+' approximate',modeled:true};
 await importBatch(db,{records:[record('modeled-zero','population',0,{metadata:data}),record('vegetation','vegetation','farmlands')],sources:[source('huge-source','historical',{description:'x'.repeat(3000)})],names:[name('large-name','L0000',{source_id:'huge-source',metadata:{description:'x'.repeat(2000)}})]});
 const compact=hydrateMapSnapshotPage(await mapSnapshotPage(db,1000)),full=(await attributesAt(db,1000)).records;
 const claim=compact.records.find(r=>r.id==='modeled-zero');assert.equal(claim.metadata_truncated,1);assert.match(claim.evidence_url,/\/api\/evidence\/records\/modeled-zero/);assert.ok(claim.metadata.modeled);assert.match(claim.metadata.precision,/approximate/);assert.equal(compact.names[0].source_metadata_truncated,true);
 assert.equal(resolveAttributes([feature('L0000')],1000,{records:compact.records}).get('L0000').rank,resolveAttributes([feature('L0000')],1000,{records:full}).get('L0000').rank);
 await importBatch(db,{retirements:[{id:'retire-model',collection:'records',target_id:'modeled-zero',source_id:'historical',reason:'New explicit observation'}],records:[record('observed-zero','population',0,{metadata:{details:'x'.repeat(2000),precision:{approximate:'this object is not a text precision'}}})]});
 const zero=hydrateMapSnapshotPage(await mapSnapshotPage(db,1000));assert.equal(resolveAttributes([feature('L0000')],1000,{records:zero.records}).get('L0000').rank,'unsettled');
}));

test('mid-page writes reject the entire map page with a retryable revision conflict',close(async db=>{
 let changed=false;db.onQuery=sql=>{if(!changed&&sql===mapSnapshotQueries.entities){changed=true;db.sqlite.prepare('INSERT INTO atlas_ingestions(id,fingerprint,counts,created_at) VALUES(?,?,?,?)').run('concurrent','a'.repeat(64),'{}',1);}};
 await assert.rejects(mapSnapshotPage(db,1000),error=>error.status===409&&error.retryable===true);db.onQuery=null;const stable=await mapSnapshotPage(db,1000);assert.equal(stable.revision,3);
}));

test('priority ties use the shared UTF-16 identity order instead of SQLite UTF-8 collation',close(async db=>{
 const bmp='\uE000',astral='\u{10000}';await importBatch(db,{records:[record(`${bmp}-claim`,'owner','owner A',{category_id:'owner:a',method:'majority-area'}),record(`${astral}-claim`,'owner',null,{method:'derived'})],names:[name(`${bmp}-name`,'L0000',{language:'ja'}),name(`${astral}-name`,'L0000',{language:'zh'})]});
 const page=hydrateMapSnapshotPage(await mapSnapshotPage(db,1000));assert.equal(page.records[0].id,`${astral}-claim`);assert.equal(page.names[0].id,`${astral}-name`);
 const full=(await attributesAt(db,1000)).records;assert.deepEqual(resolveAttributes([feature('L0000')],1000,{records:page.records}),resolveAttributes([feature('L0000')],1000,{records:full}));
}));

test('the shared browser format rejects incomplete, duplicated, mismatched and unscoped response pages',close(async db=>{
 await importBatch(db,{records:[record('value','population',50)],names:[name('label')]});const original=await mapSnapshotPage(db,1000);
 const corrupt=fn=>{const page=structuredClone(original);fn(page);assert.throws(()=>hydrateMapSnapshotPage(page),/Invalid map snapshot/);};
 corrupt(page=>{page.records={};});corrupt(page=>{page.revision='1';});corrupt(page=>{page.year=0;});corrupt(page=>{page.sources={};});corrupt(page=>{page.sources.historical.metadata=[];});corrupt(page=>{page.sources.historical.id='other';});corrupt(page=>{page.records.push({...page.records[0]});});corrupt(page=>{page.names.push({...page.names[0]});});corrupt(page=>{page.records[0].valid_from=1001;});corrupt(page=>{page.records[0].location_id='person';});corrupt(page=>{page.aliases_truncated=['person'];});corrupt(page=>{page.entities.push({...page.entities[0]});});corrupt(page=>{page.next_cursor='';});
 assert.equal(hydrateMapSnapshotPage(original).records[0].value,50);
}));

test('1000 locations and 9000 attributes use seven bounded indexed queries instead of claim pages',close(async db=>{
 const locations=Array.from({length:999},(_,i)=>({id:`L${String(i+1).padStart(4,'0')}`,kind:'location',name:'Location',parent_id:'z-province'}));for(let i=0;i<locations.length;i+=200)await importBatch(db,{entities:locations.slice(i,i+200)});
 const values={owner:'owner A',population:100,culture:'culture A',religion:'religion A',rank:'town',topography:'flat',vegetation:'farmlands',climate:'oceanic',habitation:'inhabited'},claims=[];
 for(let i=0;i<1000;i++){const id=`L${String(i).padStart(4,'0')}`;for(const attribute of locationAttributes)claims.push(record(`${id}:${attribute}`,attribute,values[attribute],{location_id:id,...(['owner','culture','religion'].includes(attribute)?{category_id:`${attribute}:a`}:{})}));}
 for(let i=0;i<claims.length;i+=200)await importBatch(db,{records:claims.slice(i,i+200)});
 const names=Array.from({length:1000},(_,i)=>name(`name-${i}`,`L${String(i).padStart(4,'0')}`));for(let i=0;i<names.length;i+=200)await importBatch(db,{names:names.slice(i,i+200)});
 db.calls=[];const start=performance.now(),page=await mapSnapshotPage(db,1000),elapsed=performance.now()-start;
 assert.equal(page.entities.length,1000);assert.equal(page.records.length,9000);assert.equal(page.names.length,1000);assert.equal(Object.keys(page.sources).length,1);assert.equal(db.calls.length,7);assert.equal(page.next_cursor,'L0999');const measuredQueries=db.calls.length;
 await assert.rejects(mapSnapshotPage(db,1000,{limit:1001}),error=>error.status===400);
 await assert.rejects(mapSnapshotPage(db,1000,{evidenceOnly:true,limit:4097}),error=>error.status===400);
 const sparse=await mapSnapshotPage(db,1000,{evidenceOnly:true,limit:4096});
 assert.equal(sparse.entities.length,1000);assert.equal(sparse.next_cursor,null);
 for(const key of ['records','names','retirements','sources'])assert.deepEqual(sparse[key],page[key]);
 const bytes=Buffer.byteLength(JSON.stringify(page));assert.ok(bytes<8*1024*1024);assert.equal(new Set(page.records.map(r=>`${r.location_id}/${r.attribute}`)).size,9000);
 const entityPlan=db.sqlite.prepare(`EXPLAIN QUERY PLAN ${mapSnapshotQueries.entities}`).all('',0,1000,1000,1001).map(r=>r.detail).join('\n'),attributesPlan=db.sqlite.prepare(`EXPLAIN QUERY PLAN ${mapSnapshotQueries.attributes}`).all(JSON.stringify(['L0000']),1000,1000,0).map(r=>r.detail).join('\n'),namesPlan=db.sqlite.prepare(`EXPLAIN QUERY PLAN ${mapSnapshotQueries.names}`).all(JSON.stringify(['L0000']),1000,1000,0,6).map(r=>r.detail).join('\n');
 assert.match(entityPlan,/SEARCH atlas_entities USING INDEX entities_kind_id \(kind=\? AND active=\? AND id>\?\)/);
 assert.match(attributesPlan,/SEARCH r USING INDEX attributes_location_dates \(location_id=\? AND attribute=\? AND valid_from<\?\)/);assert.match(namesPlan,/SEARCH n USING INDEX names_entity_dates \(entity_id=\? AND valid_from<\?\)/);
 console.log(JSON.stringify({fixture:'1000-locations-9000-attributes',queries:measuredQueries,page_bytes:bytes,elapsed_ms:Math.round(elapsed*100)/100,attribute_index:'attributes_location_dates',name_index:'names_entity_dates'}));
 const aliases=[];for(let i=0;i<1000;i++)for(let a=0;a<5;a++)aliases.push(name(`alias-L${String(i).padStart(4,'0')}-${a}`,`L${String(i).padStart(4,'0')}`,{name:'A'.repeat(1000),role:'alias'}));
 for(let i=0;i<aliases.length;i+=200)await importBatch(db,{names:aliases.slice(i,i+200)});
 await assert.rejects(mapSnapshotPage(db,1000),error=>error.status===413&&error.retryable===true&&error.suggested_limit===500);
 const smaller=await mapSnapshotPage(db,1000,{limit:500});assert.equal(smaller.entities.length,500);assert.ok(Buffer.byteLength(JSON.stringify(smaller))<8*1024*1024);assert.equal(smaller.names.length,3000);
}));
