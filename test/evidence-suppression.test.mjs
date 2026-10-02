import test from 'node:test';
import assert from 'node:assert/strict';
import {resolveAttributes,locationAttributes} from '../src/attributes.js';

test('unverified withdrawals suppress every attribute source and modern owner fallback without modifying content',()=>{
 const features=[{id:'location',properties:{reference_owner:'Reference owner',metadata:{reference_polity:'Reference polity',reference_owner_id:'owner:reference'}}}];
 const record=(attribute,value)=>({id:`record:${attribute}`,location_id:'location',attribute,value,valid_from:2026,valid_to:2027,method:'direct',status:'sourced',source:'Sourced fixture'});
 const states=[{id:1,location_id:'location',rank:'city',valid_from:2026,valid_to:2027,source:'Legacy fixture'}];
 const records=[record('owner','Direct polity'),record('population',0)];
 const entity={id:'location',kind:'location',attributes:{source:'Temporal fixture',religion:'Religion',culture:'Culture'},attribute_record:{valid_from:2026,valid_to:2027}},temporal={entities:new Map([['location',entity]])};
 const original=JSON.stringify({features,states,records,entity});
 const unavailable=resolveAttributes(features,2026,{states,records,temporal,examples:true,evidenceAvailable:false}).get('location');
 for(const attribute of locationAttributes){assert.equal(unavailable[attribute],null,attribute);assert.equal(unavailable.provenance[attribute].status,'unknown',attribute);}
 assert.equal(unavailable.category_ids.owner,null);assert.equal(unavailable.rank,null,'an unavailable literal zero cannot infer unsettled');
 assert.equal(JSON.stringify({features,states,records,entity}),original,'availability handling cannot discard the source content');
 assert.equal(resolveAttributes(features,2026,{records}).get('location').owner,'Direct polity');
 assert.equal(resolveAttributes(features,2026,{records}).get('location').rank,'unsettled');
 assert.equal(resolveAttributes(features,2026).get('location').owner,'Reference polity');
});
