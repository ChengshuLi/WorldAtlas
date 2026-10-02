import test from 'node:test';
import assert from 'node:assert/strict';
import {loadHostedTemporalGeography} from '../src/hosted-temporal-client.js';
const pins={release_id:'release:test',hierarchy_sha256:'a'.repeat(64),footprints_sha256:'b'.repeat(64)};
const source={id:'source:test',name:'Synthetic temporal test source',url:'https://example.test/evidence',license:'CC0 test fixture',vintage:'2026 test fixture',status:'historical',supported_from:-3000,supported_to:2027,metadata:{test_only:true}};
function claim(id,entity_id='location:a',collection='memberships',extra={}){
 return {id,entity_id,collection,valid_from:1000,valid_to:1100,source_id:source.id,method:'direct',status:'sourced',is_example:0,release_id:pins.release_id,validation_id:'validation:test',metadata:{test_only:true},reference_parent_id:'province:a',reference_active:1,entity_kind:'location',entity_valid_from:null,entity_valid_to:null,...(collection==='memberships'?{parent_id:'province:b',effective_parent_id:'province:b',parent_context:'historical',membership_status:'dated'}:{value:'exists'}),...extra};
}
const withdrawal=(id,target_id,collection='memberships')=>({id,target_id,collection,replacement_id:null,source_id:source.id,reason:'Synthetic test correction',release_id:pins.release_id,validation_id:'validation:test',metadata:{test_only:true}});
function page(stream,{records=[],withdrawals=[],revision=10,next_cursor=null,sources=(records.length||withdrawals.length)?[source]:[],year=1000,...extra}={}){
 return {year,stream,...pins,records,withdrawals,sources,next_cursor,revision,capability:{datedMembership:1,datedExistence:1,datedFootprints:0},...extra};
}
const options={year:1000,expectedGeography:pins,expectedRevision:10};
function routing(pages,calls=[]){return async(url,{signal})=>{assert.equal(signal instanceof AbortSignal,true);const parsed=new URL(url,'https://atlas.test');assert.equal(parsed.pathname,'/api/geography/temporal/snapshot');const stream=parsed.searchParams.get('stream'),cursor=parsed.searchParams.get('cursor');assert.ok(Number(parsed.searchParams.get('limit'))<=200);calls.push({stream,cursor,limit:Number(parsed.searchParams.get('limit')),examples:parsed.searchParams.get('examples'),year:parsed.searchParams.get('year')});const row=pages[stream][cursor];if(row instanceof Error)throw row;assert.ok(row,`No synthetic ${stream} page for ${cursor}`);return structuredClone(row);};}

test('both sparse streams complete under fixed pins/revision before legacy history becomes authoritative',async()=>{
 const old={id:'old-parent',entity_id:'location:a',field:'parent',value:'province:old',valid_from:950,valid_to:1050},name={id:'kept-name',entity_id:'location:a',field:'name',value:'Test label',valid_from:1000,valid_to:1100},legacy=[old,name];
 const calls=[],pages={records:{'':page('records',{records:[claim('new-parent')],next_cursor:'location:a'}),'location:a':page('records',{records:[claim('absent','location:b','existence',{value:'not_exists'})]})},withdrawals:{'':page('withdrawals',{withdrawals:[withdrawal('withdraw-old',old.id)],next_cursor:'withdraw-old'}),'withdraw-old':page('withdrawals')}};
 const result=await loadHostedTemporalGeography({...options,legacyHistory:legacy,apiGet:routing(pages,calls)});
 assert.equal(result.available,true);assert.equal(result.complete,true);assert.equal(result.revision,10);assert.equal(result.combinedSnapshot.next_cursor,null);assert.equal(result.combinedSnapshot.sources.length,1);assert.equal(result.combinedSnapshot.records.length,2);assert.equal(result.combinedSnapshot.withdrawals.length,1);
 assert.deepEqual(result.mergedHistory.map(row=>row.id),[name.id,'new-parent','absent']);assert.deepEqual(legacy,[old,name]);assert.equal(calls.length,4);assert.equal(calls[0].stream,'records');assert.equal(calls[1].stream,'withdrawals','Independent first requests start together');
});

test('a source-free year makes exactly two bounded requests and retains caller-owned unrelated history',async()=>{
 const calls=[],legacy=[{id:'name',field:'name',value:'Retained',entity_id:'location',valid_from:-3000,valid_to:2027}];const result=await loadHostedTemporalGeography({...options,year:-3000,legacyHistory:legacy,apiGet:routing({records:{'':page('records',{year:-3000})},withdrawals:{'':page('withdrawals',{year:-3000})}},calls)});
 assert.equal(calls.length,2);assert.equal(result.combinedSnapshot.records.length,0);assert.deepEqual(result.mergedHistory,legacy);assert.equal(legacy.length,1);assert.ok(calls.every(call=>call.limit===200&&call.year==='-3000'));
});

test('identical affected rows and sources across pages deduplicate without granting conflicting claims authority',async()=>{
 const row=claim('parent'),pages={records:{'':page('records',{records:[row],next_cursor:'first'}),first:page('records',{records:[row]})},withdrawals:{'':page('withdrawals')}};
 const result=await loadHostedTemporalGeography({...options,apiGet:routing(pages)});assert.equal(result.combinedSnapshot.records.length,1);assert.equal(result.combinedSnapshot.sources.length,1);
 pages.records.first.records[0]={...row,parent_id:'province:c',effective_parent_id:'province:c'};await assert.rejects(loadHostedTemporalGeography({...options,apiGet:routing(pages)}),/conflicting-claim/);
 pages.records.first=page('records',{records:[claim('different-id')]});await assert.rejects(loadHostedTemporalGeography({...options,apiGet:routing(pages)}),/duplicate winning field/);
 pages.records.first=page('records',{records:[row],sources:[{...source,name:'Different source observation'}]});await assert.rejects(loadHostedTemporalGeography({...options,apiGet:routing(pages)}),/conflicting-source/);
});

test('permanent withdrawals apply independently and cross-stream active/withdrawn contradictions reject completion',async()=>{
 const legacy=[{id:'withdrawn',entity_id:'location',field:'parent',value:'province',valid_from:1000,valid_to:1100}],pages={records:{'':page('records')},withdrawals:{'':page('withdrawals',{withdrawals:[withdrawal('withdraw','withdrawn')]})}};
 const result=await loadHostedTemporalGeography({...options,legacyHistory:legacy,apiGet:routing(pages)});assert.deepEqual(result.mergedHistory,[]);assert.equal(legacy.length,1);
 pages.records['']=page('records',{records:[claim('withdrawn')]});await assert.rejects(loadHostedTemporalGeography({...options,legacyHistory:legacy,apiGet:routing(pages)}),/withdrawn active claim/);
 pages.records['']=page('records');pages.withdrawals[''].sources=[];await assert.rejects(loadHostedTemporalGeography({...options,apiGet:routing(pages)}),/missing-page-source/);
});

test('expected scalar revision never silently repins or locally retries a partial snapshot',async()=>{
 const calls=[],pages={records:{'':page('records',{records:[claim('parent')],revision:11})},withdrawals:{'':page('withdrawals')}};
 await assert.rejects(loadHostedTemporalGeography({...options,apiGet:routing(pages,calls)}),error=>error.retryable===true&&error.status===409&&/revision-mismatch/.test(error.message));assert.equal(calls.length,2,'Whole-snapshot retry belongs to the caller');
 pages.records['']=page('records',{footprints_sha256:'c'.repeat(64)});await assert.rejects(loadHostedTemporalGeography({...options,apiGet:routing(pages)}),error=>error.retryable===true&&/pin-mismatch/.test(error.message));
 pages.records['']=Object.assign(Error('Retry consistent snapshot'),{status:409,retryable:true});await assert.rejects(loadHostedTemporalGeography({...options,apiGet:routing(pages)}),error=>error.retryable===true&&error.status===409);
});

test('unanchored standalone reads retry both streams within the bounded attempt budget',async()=>{
 let generation=0;const calls=[];const apiGet=async url=>{const stream=new URL(url,'https://atlas.test').searchParams.get('stream');if(stream==='records')generation++;calls.push({generation,stream});return stream==='records'?page('records',{revision:generation===1?10:12,records:[claim(generation===1?'discarded':'accepted')]}):page('withdrawals',{revision:generation===1?11:12});};
 const result=await loadHostedTemporalGeography({...options,expectedRevision:undefined,apiGet});assert.equal(result.revision,12);assert.deepEqual(result.combinedSnapshot.records.map(row=>row.id),['accepted']);assert.equal(calls.length,4);
 let count=0;await assert.rejects(loadHostedTemporalGeography({...options,expectedRevision:undefined,maxAttempts:2,apiGet:async url=>{count++;return page(new URL(url,'https://atlas.test').searchParams.get('stream'),{revision:count});}}),error=>error.retryable===true);assert.equal(count,4);
});

test('abort/cancellation preserves its reason and no completed or partial result escapes',async()=>{
 const before=new AbortController(),reason=Error('Selected another year');before.abort(reason);let requests=0;await assert.rejects(loadHostedTemporalGeography({...options,signal:before.signal,apiGet:()=>{requests++;}}),error=>error===reason);assert.equal(requests,0);
 const controller=new AbortController(),signals=[];let started;const ready=new Promise(resolve=>{started=resolve;});const loading=loadHostedTemporalGeography({...options,signal:controller.signal,apiGet:(_url,{signal})=>{signals.push(signal);if(signals.length===2)started();return new Promise(()=>{});}});await ready;controller.abort(reason);await assert.rejects(loading,error=>error===reason);assert.equal(signals.length,2);assert.ok(signals.every(signal=>signal.aborted));
});

test('retryable oversized pages reduce only that stream limit and keep the same cursor/revision',async()=>{
 const calls=[];let retry=true;const apiGet=async(url,{signal})=>{const parsed=new URL(url,'https://atlas.test'),stream=parsed.searchParams.get('stream');calls.push({stream,limit:Number(parsed.searchParams.get('limit')),cursor:parsed.searchParams.get('cursor')});if(stream==='records'&&retry){retry=false;throw Object.assign(Error('Page budget'),{status:413,retryable:true,suggested_limit:50});}assert.equal(signal.aborted,false);return page(stream);};
 const result=await loadHostedTemporalGeography({...options,apiGet});assert.equal(result.complete,true);assert.deepEqual(calls.filter(call=>call.stream==='records').map(call=>call.limit),[200,50]);assert.deepEqual(calls.filter(call=>call.stream==='withdrawals').map(call=>call.limit),[200]);assert.ok(calls.every(call=>call.cursor===''));
 await assert.rejects(loadHostedTemporalGeography({...options,apiGet:async()=>{throw Object.assign(Error('Bad limit'),{status:413,retryable:true,suggested_limit:200});}}),/invalid-suggested-limit/);
});

test('rows, cursors, response/aggregate budgets and malformed source/capability reject authority',async()=>{
 const pages={records:{'':page('records',{records:[claim('parent')],next_cursor:'next'}),next:page('records')},withdrawals:{'':page('withdrawals')}};
 await assert.rejects(loadHostedTemporalGeography({...options,maxPages:2,apiGet:routing(pages)}),/page-budget-exceeded/);
 pages.records[''].next_cursor=null;await assert.rejects(loadHostedTemporalGeography({...options,maxRows:0,apiGet:routing(pages)}),/row-budget-exceeded/);
 pages.records[''].sources=[{...source,metadata:{large:'x'.repeat(2000)}}];await assert.rejects(loadHostedTemporalGeography({...options,maxBytes:1024,apiGet:routing(pages)}),/byte-budget-exceeded/);
 pages.records['']=page('records',{records:[claim('parent')],next_cursor:'same'});pages.records.same=page('records',{next_cursor:'same'});await assert.rejects(loadHostedTemporalGeography({...options,apiGet:routing(pages)}),/repeated-cursor/);
 pages.records['']=page('records',{capability:{datedMembership:1,datedExistence:1,datedFootprints:1}});await assert.rejects(loadHostedTemporalGeography({...options,apiGet:routing(pages)}),/unsupported capability/);
 pages.records['']=page('records');delete pages.records[''].next_cursor;await assert.rejects(loadHostedTemporalGeography({...options,apiGet:routing(pages)}),/invalid-next-cursor/);
 await assert.rejects(loadHostedTemporalGeography({...options,limit:201,apiGet:routing(pages)}),/invalid-limit/);await assert.rejects(loadHostedTemporalGeography({...options,year:0,apiGet:routing(pages)}),/invalid-loader-options/);
});

test('explicit unknown parents and BC/AD boundaries retain source evidence and reference context',async()=>{
 const row=claim('unknown-parent','location:a','memberships',{parent_id:null,effective_parent_id:'province:a',parent_context:'reference',membership_status:'unknown',status:'unknown',valid_from:-1,valid_to:1}),pages={records:{'':page('records',{year:-1,records:[row]})},withdrawals:{'':page('withdrawals',{year:-1})}};
 const result=await loadHostedTemporalGeography({...options,year:-1,expectedGeography:{...pins,id:pins.release_id,release_id:undefined},apiGet:routing(pages)});assert.equal(result.mergedHistory[0].value,'province:a');assert.equal(result.mergedHistory[0].metadata.parent_context,'reference');assert.equal(result.mergedHistory[0].status,'unknown');assert.equal(result.mergedHistory[0].source,source.name);
 pages.records[''].year=1;pages.withdrawals[''].year=1;await assert.rejects(loadHostedTemporalGeography({...options,year:1,apiGet:routing(pages)}),/dated claim/);
});
