import test from 'node:test';
import assert from 'node:assert/strict';
import {resolveAttributes} from '../src/attributes.js';
import {referenceContextByLocation,presentedAttribute} from '../src/reference-context.js';
import {decodeReferences,decodeReferenceContext} from '../src/reference-records.js';
import {categoryColor} from '../src/model.js';

const features=[{id:'location',properties:{name:'Present-day location'}}];
const reference=(attribute,value,extra={})=>({
 id:`reference:location:${attribute}:2026`,location_id:'location',attribute,value,
 valid_from:2026,valid_to:2027,method:'reference',status:'reference',
 source:'Documented modern reference',source_id:'modern-source',metadata:{source_year:2017},...extra,
});
const dated=(attribute,value,extra={})=>({
 id:`dated:${attribute}`,location_id:'location',attribute,value,
 valid_from:1000,valid_to:1100,method:'direct',status:'sourced',
 source:'Documented historical evidence',source_id:'historical-source',...extra,
});
const baselines=[
 reference('topography','flatland'),
 reference('vegetation','Temperate Broadleaf & Mixed Forests',{metadata:{source_year:2017,note:'Potential natural biome, not observed land cover'}}),
 reference('climate','Cfb',{metadata:{normal_period:[1991,2020],note:'A climatological reference, not an annual observation'}}),
];
const at=(year,options={})=>resolveAttributes(features,year,{referenceBaselines:baselines,...options}).get('location');

test('environmental context can be displayed without inventing historical field evidence',()=>{
 const original=JSON.stringify(baselines);
 for(const year of [-3000,1000,2025]){
  const state=at(year);
  for(const [attribute,label,id] of [
   ['topography','Flatland','topography:flat'],
   ['vegetation','Temperate Broadleaf & Mixed Forests','vegetation:temperate-broadleaf-mixed-forest'],
   ['climate','Cfb oceanic','climate:Cfb'],
  ]){
   assert.equal(state[attribute],null,`${year}: raw ${attribute} must remain unsupported`);
   assert.equal(state.category_ids[attribute],null);
   assert.equal(state.provenance[attribute].status,'unknown');
   const shown=presentedAttribute(state,attribute);
   assert.equal(shown.value,label);assert.equal(shown.category_id,id);
   assert.equal(shown.reference_context,true);assert.equal(shown.provenance.context_only,true);
   assert.equal(shown.provenance.valid_from,2026);assert.equal(shown.provenance.valid_to,2027);
   assert.equal(shown.provenance.source_id,'modern-source');
  }
 }
 assert.equal(JSON.stringify(baselines),original,'Presenting context must not rewrite evidence');
});

test('modern supported records and historical reference context share a category and map color',()=>{
 const modern=at(2026,{records:baselines}),earlier=at(2025,{records:baselines});
 for(const attribute of ['topography','vegetation','climate']){
  const now=presentedAttribute(modern,attribute),then=presentedAttribute(earlier,attribute);
  assert.equal(modern[attribute],now.value);assert.equal(earlier[attribute],null);
  assert.equal(now.provenance.context_only,undefined);
  assert.equal(then.provenance.context_only,true);
  assert.equal(now.value,then.value);assert.equal(now.category_id,then.category_id);
  assert.equal(categoryColor(now.category_id),categoryColor(then.category_id));
 }
});

test('dated historical observations override modern context until their exclusive interval end',()=>{
 const claim=dated('climate','Af',{metadata:{observation_year:1000}});
 const supported=at(1000,{records:[claim]}),expired=at(1100,{records:[claim]});
 const shown=presentedAttribute(supported,'climate');
 assert.equal(shown.value,'Af tropical rainforest');assert.equal(shown.category_id,'climate:Af');
 assert.equal(shown.provenance.id,claim.id);assert.equal(shown.reference_context,false);
 assert.equal(expired.climate,null);
 assert.equal(presentedAttribute(expired,'climate').category_id,'climate:Cfb');
});

test('explicit dated uncertainty and unmapped source text cannot be replaced by a baseline',()=>{
 for(const status of ['unknown','disputed','no-majority']){
  const state=at(1050,{records:[dated('climate',status==='unknown'?null:'Af',{status})]});
  const shown=presentedAttribute(state,'climate');
  assert.equal(shown.value,null);assert.equal(shown.category_id,null);
  assert.equal(shown.reference_context,false);assert.equal(shown.provenance.status,status);
 }
 const rejected=at(1050,{records:[dated('vegetation','Unapproved poetic forest description')]});
 const shown=presentedAttribute(rejected,'vegetation');
 assert.equal(shown.value,null);assert.equal(shown.reference_context,false);
 assert.equal(shown.provenance.metadata.unmapped_source_value,'Unapproved poetic forest description');
});

test('only supported environmental references can supply presentation context',()=>{
 const rejected=[
  reference('owner','Modern owner'),reference('population',100),reference('rank','city'),
  reference('topography','flatland',{method:'direct'}),
  reference('topography','flatland',{is_example:1}),
  reference('vegetation','unapproved vegetation'),reference('climate',null),
 ];
 assert.equal(referenceContextByLocation(rejected).size,0);
 for(const status of ['unknown','disputed','no-majority']){
  assert.equal(referenceContextByLocation([reference('climate','Cfb',{status})]).size,0,`${status} is not a supported baseline`);
 }
});

test('invalidated geography cannot retain environmental context or restore a dated field',()=>{
 const metadata={invalidated_footprint:true,reason:'Prepared assignments require regeneration'};
 for(const value of [null,'Cfb'])assert.equal(referenceContextByLocation([reference('climate',value,{metadata})]).size,0);
 const state=at(1050,{records:[dated('climate',null,{status:'unknown',metadata})]});
 const shown=presentedAttribute(state,'climate');
 assert.equal(shown.value,null);assert.equal(shown.reference_context,false);
 assert.equal(shown.provenance.metadata.invalidated_footprint,true);
});

test('reference source dates and environmental caveats survive display unchanged',()=>{
 const state=at(1000);
 assert.deepEqual(presentedAttribute(state,'climate').provenance.metadata.normal_period,[1991,2020]);
 assert.equal(presentedAttribute(state,'vegetation').provenance.metadata.source_year,2017);
 assert.equal(presentedAttribute(state,'vegetation').provenance.metadata.note,'Potential natural biome, not observed land cover');
 assert.equal(presentedAttribute(state,'climate').provenance.source_value,'Cfb');
 assert.equal(presentedAttribute(state,'topography').provenance.source_value,'flatland');
});

test('an evidence outage leaves historical fields unknown while immutable reference context remains available',()=>{
 const state=at(1050,{records:[dated('climate','Af')],evidenceAvailable:false});
 assert.equal(state.climate,null);assert.equal(state.provenance.climate.status,'unknown');
 const shown=presentedAttribute(state,'climate');
 assert.equal(shown.value,'Cfb oceanic');assert.equal(shown.reference_context,true);
 assert.equal(shown.provenance.source_id,'modern-source');
 assert.equal(shown.provenance.context_only,true);
});

test('missing baselines remain unknown and non-environmental fields never acquire environmental context',()=>{
 const state=at(1000,{referenceBaselines:[]});
 for(const attribute of ['topography','vegetation','climate','owner','culture','religion','population','rank']){
  const shown=presentedAttribute(state,attribute);
  assert.equal(shown.value,null);assert.equal(shown.category_id,null);assert.equal(shown.reference_context,false);
 }
});

test('baseline selection is deterministic and keeps the chosen source interval rather than extending it',()=>{
 const older=reference('climate','Af',{id:'older',valid_from:2020,valid_to:2021});
 const later=reference('climate','Cfb',{id:'z'}),tie=reference('climate','Am',{id:'a'});
 const forward=referenceContextByLocation([older,later,tie]).get('location').climate;
 const reverse=referenceContextByLocation([tie,later,older]).get('location').climate;
 assert.deepEqual(forward,reverse);assert.equal(forward.category_id,'climate:Am');
 assert.equal(forward.provenance.id,'a');assert.equal(forward.provenance.valid_from,2026);
});

test('compact and legacy context decoding preserve original supported intervals and source metadata',()=>{
 const index={version:2,values:['Cfb','Af','flatland'],types:[
  {attribute:'climate',valid_from:2026,valid_to:2027,method:'reference',status:'reference',source:'Climate normals',metadata:{normal_period:[1991,2020]}},
  {attribute:'climate',valid_from:1901,valid_to:1931,method:'reference',status:'reference',source:'Earlier climate normals',metadata:{normal_period:[1901,1930]}},
  {attribute:'topography',valid_from:2026,valid_to:2027,method:'direct',status:'sourced',source:'Dated terrain evidence',metadata:{}},
  {attribute:'climate',valid_from:2026,valid_to:2027,method:'reference',status:'example',is_example:1,source:'Example',metadata:{}},
 ]};
 const parts=[[['location',[[0,0,.7,1],[1,1,.8,.9],[2,2,1,1],[3,1,1,1]]]]];
 const input=JSON.stringify({parts,index}),context=decodeReferenceContext(parts,index);
 assert.equal(context.length,1);assert.equal(context[0].value,'Cfb');
 assert.equal(context[0].valid_from,2026);assert.equal(context[0].valid_to,2027);
 assert.deepEqual(context[0].metadata.normal_period,[1991,2020]);
 assert.equal(context[0].metadata.share,.7);assert.equal(context[0].metadata.coverage,1);
 assert.equal(decodeReferences(parts,index,2025).length,0);
 assert.equal(decodeReferences(parts,index,1920)[0].source,'Earlier climate normals');
 assert.equal(JSON.stringify({parts,index}),input);
 const legacy=[...context,reference('climate','Af',{id:'old',valid_from:1901,valid_to:1931}),reference('climate','Am',{is_example:1})];
 assert.deepEqual(decodeReferenceContext([legacy],{version:1}),context);
 const state=at(1000,{referenceBaselines:context});
 assert.equal(state.climate,null);assert.equal(presentedAttribute(state,'climate').category_id,'climate:Cfb');
});
