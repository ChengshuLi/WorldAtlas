import test from 'node:test';
import assert from 'node:assert/strict';
import {hydrateHostedTemporalGeographyPage,hostedTemporalHistory,mergeHostedTemporalHistory} from '../src/hosted-temporal-geography.js';
import {resolveTemporal} from '../src/temporal.js';

const tiers=['continent','subcontinent','region','area','province','location'];
const release={id:'release:test',status:'published',hierarchy_sha256:'a'.repeat(64),footprints_sha256:'b'.repeat(64)};
const pin={release_id:release.id,hierarchy_sha256:release.hierarchy_sha256,footprints_sha256:release.footprints_sha256};
const source={id:'source:test',name:'Test-only dated source',url:'https://example.org/test-only',license:'CC0',vintage:'2026',status:'historical',supported_from:900,supported_to:1100,metadata:{source_hash:'c'.repeat(64)}};
function snapshot(year=1000){return {year,revision:1,release,entities:tiers.map((kind,i)=>({id:kind,entity_id:kind,kind,present:true,parent_id:i?tiers[i-1]:null,reference_parent_id:i?tiers[i-1]:null,historical_parent_id:null,membership_status:'reference',parent_context:'reference',existence_status:'unknown',membership_record:null,existence_record:null})),claims:[],withdrawals:[],excluded_entity_ids:[],sources:{[source.id]:source},footprints:{status:'reference',historical:false,footprints_sha256:release.footprints_sha256},capability:{datedMembership:1,datedExistence:1,datedFootprints:0}};}
const claim=(id,collection,extra={})=>({id,collection,entity_id:'location',source_id:source.id,validation_id:'validation:test',release_id:release.id,valid_from:1000,valid_to:1001,method:'direct',status:'sourced',is_example:0,metadata:{original:'Source language'},...(collection==='memberships'?{parent_id:'province'}:{value:'exists'}),...extra});
function attach(page,row){page.claims.push(row);const entity=page.entities.find(entity=>entity.id===row.entity_id);if(row.collection==='memberships'){entity.membership_record=row;entity.historical_parent_id=row.parent_id;entity.parent_id=row.parent_id??entity.reference_parent_id;entity.membership_status=row.parent_id==null?'unknown':'dated';entity.parent_context=row.parent_id==null?'reference':'historical';}else{entity.existence_record=row;entity.existence_status=row.value;if(row.value==='not_exists'){entity.present=false;page.excluded_entity_ids.push(entity.id);}}return page;}

test('dated parent bridge preserves stable identity, source support and effective complete chains',()=>{
 const page=snapshot(),extra={...page.entities.find(row=>row.id==='province'),id:'province:new',entity_id:'province:new'};page.entities.push(extra);attach(page,claim('parent:dated','memberships',{parent_id:extra.id}));
 const hydrated=hydrateHostedTemporalGeographyPage(page,{expectedGeography:pin});assert.equal(hydrated.claims[0].source,source.name);assert.deepEqual(hydrated.claims[0].source_metadata,source.metadata);
 const history=hostedTemporalHistory(page,{year:1000,expectedGeography:pin});assert.equal(history[0].field,'parent');assert.equal(history[0].value,extra.id);assert.equal(history[0].source_from,900);assert.equal(history[0].metadata.reference_parent_id,'province');assert.match(history[0].evidence_url,/evidence\/memberships/);
 const reference={units:page.entities.filter(row=>row.kind!=='location').map(row=>({id:row.id,level:row.kind,name:row.id,parent_id:row.reference_parent_id})),features:[{id:'location',properties:{name:'Location',parent_id:'province'}}],temporal:{entities:page.entities.map(row=>({id:row.id,kind:row.kind,name:row.id,parent_id:row.reference_parent_id})),history,links:[]}};
 assert.equal(resolveTemporal(reference,1000).features[0].properties.parent_id,extra.id);assert.equal(resolveTemporal(reference,1001).features[0].properties.parent_id,'province','Unsupported years retain separately reference membership');
});
test('explicit unknown membership keeps the reference chain and original uncertainty rather than adopting a weaker claim',()=>{
 const page=snapshot(),derived=claim('derived:parent','memberships',{method:'derived',status:'derived'}),unknown=claim('direct:unknown','memberships',{parent_id:null,status:'unknown',metadata:'{ "reason" : "No supported historical parent" }'});page.claims.push(derived);attach(page,unknown);
 const history=hostedTemporalHistory(page);assert.equal(history.length,1);assert.equal(history[0].id,unknown.id);assert.equal(history[0].value,'province');assert.equal(history[0].status,'unknown');assert.equal(history[0].metadata.historical_parent_id,null);assert.equal(history[0].metadata.parent_context,'reference');assert.equal(history[0].metadata.reason,'No supported historical parent');assert.equal(unknown.metadata,'{ "reason" : "No supported historical parent" }','Bridge never rewrites source input');
});
test('existence exclusions survive adaptation, including sourced unknown and BC/AD reference exclusions without year zero',()=>{
 const page=attach(snapshot(),claim('not-existing','existence',{value:'not_exists'}));const history=hostedTemporalHistory(page);assert.equal(history[0].field,'existence');assert.equal(history[0].value,'not_exists');
 const unknown=attach(snapshot(),claim('existence-unknown','existence',{value:'unknown',status:'unknown'}));assert.equal(hostedTemporalHistory(unknown)[0].value,'unknown');
 const bc=snapshot(-1);bc.entities.at(-1).present=false;bc.entities.at(-1).existence_status='not_exists';bc.excluded_entity_ids=['location'];const exclusion=hostedTemporalHistory(bc)[0];assert.equal(exclusion.valid_from,-1);assert.equal(exclusion.valid_to,1);assert.equal(exclusion.metadata.resolution_only,true);assert.equal(exclusion.metadata.reference_context,true);
});
test('bridge rejects wrong release, unsupported source/year, examples, withdrawn winners and unvetted footprints',()=>{
 const fresh=()=>attach(snapshot(),claim('dated','memberships'));
 assert.throws(()=>hydrateHostedTemporalGeographyPage(fresh(),{expectedGeography:{...pin,release_id:'wrong'}}),/pinned/);
 let page=fresh();page.year=1001;assert.throws(()=>hostedTemporalHistory(page),/dated claim/);
 page=fresh();page.sources[source.id]={...source,supported_from:1001};assert.throws(()=>hostedTemporalHistory(page),/source support/);
 page=fresh();page.footprints.historical=true;assert.throws(()=>hostedTemporalHistory(page),/footprint/);
 page=fresh();page.claims[0].is_example=1;assert.throws(()=>hostedTemporalHistory(page),/dated claim/);assert.equal(hostedTemporalHistory(page,{examples:true}).length,1);
 page=fresh();page.withdrawals=[{id:'withdraw',collection:'memberships',target_id:'dated',replacement_id:null,source_id:source.id,reason:'Test-only correction',release_id:release.id,validation_id:'validation:test',metadata:{}}];assert.throws(()=>hostedTemporalHistory(page),/withdrawn active/);
 page=fresh();page.entities.at(-1).parent_id='area';assert.throws(()=>hostedTemporalHistory(page),/disagrees/);
 page=snapshot();page.entities.at(-1).present=false;assert.throws(()=>hostedTemporalHistory(page),/missing exclusion/);
});
test('joined-source snapshots hydrate exact JSON text metadata without requiring a duplicate source dictionary',()=>{
 const page=snapshot(),row=claim('joined','memberships',{source:source.name,source_url:source.url,source_license:source.license,source_vintage:source.vintage,source_status:source.status,source_from:source.supported_from,source_to:source.supported_to,source_metadata:'{ "source_hash" : "retained" }',metadata:'{ "original" : "verbatim" }'});delete page.sources;attach(page,row);
 const hydrated=hydrateHostedTemporalGeographyPage(page);assert.deepEqual(hydrated.claims[0].metadata,{original:'verbatim'});assert.deepEqual(hydrated.claims[0].source_metadata,{source_hash:'retained'});assert.equal(row.metadata,'{ "original" : "verbatim" }');assert.equal(row.source_metadata,'{ "source_hash" : "retained" }');
});
test('shared temporal parent/existence resolution matches direct/derived/reference/example precedence independently of language and IDs',()=>{
 const reference={units:[{id:'province',level:'province',name:'Province',parent_id:'area'},{id:'other',level:'province',name:'Other',parent_id:'area'}],features:[{id:'location',properties:{name:'Location',parent_id:'province'}}],temporal:{entities:[{id:'location',kind:'location',name:'Location',parent_id:'province'},{id:'province',kind:'province',name:'Province',parent_id:'area'},{id:'other',kind:'province',name:'Other',parent_id:'area'}],history:[],links:[]}};
 const row=(id,field,value,method,extra={})=>({id,entity_id:'location',field,value,method,valid_from:1000,valid_to:1001,source:'Test-only evidence',language:'en',...extra});
 reference.temporal.history=[row('a-reference','parent','other','reference'),row('b-derived','parent','other','derived'),row('z-unknown-direct','parent','province','direct',{status:'unknown',language:'und',metadata:{historical_membership_status:'unknown',parent_context:'reference'}}),row('a-fiction','parent','other','direct',{is_example:1}),row('a-existence-reference','existence','not_exists','reference'),row('z-existence-direct','existence','unknown','direct',{language:'und'})];
 const resolved=resolveTemporal(reference,1000,true),location=resolved.entities.get('location');assert.equal(location.parent_id,'province');assert.equal(location.parent_record.id,'z-unknown-direct');assert.equal(location.parent_record.status,'unknown');assert.equal(location.status,'unknown');assert.equal(resolved.features.length,1);
 reference.temporal.history=reference.temporal.history.filter(row=>row.id!=='z-unknown-direct');assert.equal(resolveTemporal(reference,1000,true).entities.get('location').parent_record.id,'b-derived');
 reference.temporal.history=reference.temporal.history.filter(row=>row.id!=='b-derived');assert.equal(resolveTemporal(reference,1000,true).entities.get('location').parent_record.id,'a-reference');
});
test('complete hosted snapshot authority removes withdrawn legacy IDs and overridden fields without reviving excluded entities',()=>{
 const page=attach(snapshot(),claim('new-parent','memberships',{parent_id:null,status:'unknown'}));attach(page,claim('new-absence','existence',{value:'not_exists'}));page.withdrawals=[{id:'withdraw-old',collection:'memberships',target_id:'old-parent',replacement_id:null,source_id:source.id,reason:'Test-only correction',release_id:release.id,validation_id:'validation:test',metadata:{}}];
 const legacy=[{id:'old-parent',entity_id:'location',field:'parent',value:'other',valid_from:950,valid_to:1050},{id:'old-existence',entity_id:'location',field:'existence',value:'exists',valid_from:950,valid_to:1050},{id:'later-parent',entity_id:'location',field:'parent',value:'other',valid_from:1050,valid_to:1100},{id:'name-preserved',entity_id:'location',field:'name',value:'Recorded name',valid_from:950,valid_to:1050}];
 assert.throws(()=>mergeHostedTemporalHistory(legacy,page),/complete snapshot/);assert.throws(()=>mergeHostedTemporalHistory(legacy,{...page,next_cursor:'unfinished'},{complete:true}),/complete snapshot/);
 const merged=mergeHostedTemporalHistory(legacy,page,{complete:true,expectedGeography:pin});assert.deepEqual(merged.map(row=>row.id),['later-parent','name-preserved','new-parent','new-absence']);assert.equal(legacy.length,4,'Original archive input stays intact');
 const cleared=snapshot();cleared.withdrawals=page.withdrawals;assert.equal(mergeHostedTemporalHistory(legacy,cleared,{complete:true}).some(row=>row.id==='old-parent'),false,'A withdrawal remains authoritative even without a replacement winner');
});
function bounded(records=[],withdrawals=[],stream='records'){
 return {year:1000,stream,release_id:release.id,hierarchy_sha256:release.hierarchy_sha256,footprints_sha256:release.footprints_sha256,records:records.map(row=>({...row,reference_parent_id:'province',reference_active:1,entity_kind:'location',entity_valid_from:null,entity_valid_to:null,...(row.collection==='memberships'?{effective_parent_id:row.parent_id??'province',parent_context:row.parent_id==null?'reference':'historical',membership_status:row.parent_id==null?'unknown':'dated'}:{})})),withdrawals,sources:records.length||withdrawals.length?[source]:[],next_cursor:null,revision:1,capability:{datedMembership:1,datedExistence:1,datedFootprints:0}};
}
test('bounded production pages hydrate source-deduplicated winners and generate histories/exclusions without a full reference registry',()=>{
 const page=bounded([claim('parent-null','memberships',{parent_id:null,status:'unknown'}),claim('absent','existence',{value:'not_exists'})]);
 const hydrated=hydrateHostedTemporalGeographyPage(page,{expectedGeography:pin});assert.equal(hydrated.sources.length,1);assert.equal(hydrated.records[0].source,source.name);assert.equal(hydrated.entities.length,1);assert.deepEqual(hydrated.excluded_entity_ids,['location']);
 const history=hostedTemporalHistory(hydrated,{expectedGeography:pin});assert.deepEqual(history.map(row=>row.field),['parent','existence']);assert.equal(history[0].value,'province');assert.equal(history[0].status,'unknown');
 assert.deepEqual(hostedTemporalHistory(bounded()),[],'Source-free years need no reference registry read');
 const legacy=[{id:'old',entity_id:'location',field:'parent',value:'other',valid_from:1000,valid_to:1001}];assert.equal(mergeHostedTemporalHistory(legacy,page,{complete:true}).some(row=>row.id==='old'),false);
});
test('bounded withdrawals remain authoritative independently of selected-year claims; malformed stream/context cannot become history',()=>{
 const withdrawal={id:'withdraw',collection:'memberships',target_id:'old',replacement_id:null,source_id:source.id,reason:'Correction',release_id:release.id,validation_id:'validation:test',metadata:{}},page=bounded([], [withdrawal],'withdrawals'),legacy=[{id:'old',entity_id:'location',field:'parent',value:'other',valid_from:1000,valid_to:1001}];
 assert.deepEqual(mergeHostedTemporalHistory(legacy,page,{complete:true}),[]);
 let bad=bounded([claim('parent','memberships')]);bad.records[0].effective_parent_id='area';assert.throws(()=>hostedTemporalHistory(bad),/effective parent/);
 bad=bounded([claim('parent','memberships')]);bad.sources[0]={...source,id:'wrong-source'};assert.throws(()=>hostedTemporalHistory(bad),/claim source/);
 bad=bounded([claim('parent','memberships'),claim('duplicate-parent','memberships')]);assert.throws(()=>hostedTemporalHistory(bad),/duplicate winning/);
 bad=bounded([claim('parent','memberships')],[],'withdrawals');assert.throws(()=>hostedTemporalHistory(bad),/withdrawal stream/);
});
test('source IDs are ordinary stable identities even when their spelling matches JavaScript object properties',()=>{
 const page=bounded([claim('parent','memberships',{source_id:'__proto__'})]);page.sources=[{...source,id:'__proto__'}];assert.equal(hostedTemporalHistory(page)[0].source_id,'__proto__');
 const joined=snapshot(),row=claim('joined-constructor','memberships',{source_id:'constructor',source:source.name,source_license:source.license,source_vintage:source.vintage,source_status:source.status,source_from:900,source_to:1100,source_metadata:{}});delete joined.sources;attach(joined,row);assert.equal(hostedTemporalHistory(joined)[0].source_id,'constructor');
});
