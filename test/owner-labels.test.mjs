import test from 'node:test';
import assert from 'node:assert/strict';
import {readOwnerLabels,ownerDisplayName} from '../src/owner-labels.js';
import {resolveAttributes} from '../src/attributes.js';
import {presentedAttribute} from '../src/reference-context.js';
import {categoryPresentationKey} from '../src/category-presentation.js';

const snapshot=()=>({version:1,kind:'neon-owner-label-replica-v1',revision:41,
 capture_reference:{id:'published-capture',hierarchy_sha256:'a'.repeat(64),footprints_sha256:'b'.repeat(64)},
 owners:[{id:'owner:Q1045',kind:'owner',name:'Somalia',source_id:'canonical'},
 {id:'owner:Q34754',kind:'owner',name:'Somaliland',source_id:'canonical'}]});

test('generated owner replica has a closed, unique identity and revision envelope',()=>{
 const body=snapshot(),labels=readOwnerLabels(body);
 assert.equal(labels.get('owner:Q34754').name,'Somaliland');
 body.owners[1].name='Mutated after parsing';assert.equal(labels.get('owner:Q34754').name,'Somaliland');
 for(const mutate of [x=>x.version=2,x=>x.revision=-1,x=>x.revision=1.2,x=>x.unknown=true,
  x=>delete x.capture_reference.id,x=>x.capture_reference.hierarchy_sha256='wrong',
  x=>x.owners.push({...x.owners[0]}),x=>x.owners[0].kind='religion',x=>x.owners[0].name=' ',
  x=>x.owners[0].source_id=null,x=>x.owners[0].alias='Wrong']){
  const bad=snapshot();mutate(bad);assert.throws(()=>readOwnerLabels(bad),/Invalid canonical owner-label snapshot/);
 }
 const general=snapshot();general.owners[0].id='existing-nonprefixed-id';
 assert.equal(readOwnerLabels(general).get('existing-nonprefixed-id').name,'Somalia','Do not invent a new category-ID grammar');
});

test('the exact owner dated name precedes the replica, including an owner created after capture',()=>{
 const labels=readOwnerLabels(snapshot());
 assert.equal(ownerDisplayName('owner:Q34754',{labels}),'Somaliland');
 assert.equal(ownerDisplayName('owner:Q34754',{labels,nameRecord:{entity_id:'location',value:'Location name'}}),'Somaliland');
 assert.equal(ownerDisplayName('owner:Q34754',{labels,nameRecord:{entity_id:'owner:Q34754',value:'Dated owner name'}}),'Dated owner name');
 assert.equal(ownerDisplayName('new-owner',{labels,nameRecord:{entity_id:'new-owner',value:'New dated owner'}}),'New dated owner');
 assert.equal(ownerDisplayName('new-owner',{labels}),null);
 assert.equal(ownerDisplayName(null,{labels}),null);
});

test('one canonical owner lookup replaces source aliases without changing assignments or uncertainty',()=>{
 const feature=(id,owner='owner:Q34754',status='reference')=>({id,properties:{reference_owner:'Source label',metadata:{reference_polity:'Somalia',reference_owner_id:owner,reference_polity_status:status}}});
 const features=[feature('known'),feature('unlabelled','owner:not-captured'),feature('disputed','owner:Q34754','disputed')],original=structuredClone(features);
 const result=resolveAttributes(features,2026,{ownerLabels:readOwnerLabels(snapshot())});
 assert.equal(result.get('known').owner,'Somaliland');assert.equal(result.get('known').category_ids.owner,'owner:Q34754');
 const missing=result.get('unlabelled');assert.equal(missing.owner,null);assert.equal(missing.category_ids.owner,'owner:not-captured');
 const shown=presentedAttribute(missing,'owner');assert.equal(shown.category_id,'owner:not-captured');assert.equal(shown.value,null);
 assert.equal(categoryPresentationKey('owner',shown),'owner:not-captured');
 const disputed=presentedAttribute(result.get('disputed'),'owner');assert.equal(disputed.value,null);assert.equal(disputed.category_id,null);
 assert.equal(categoryPresentationKey('owner',disputed),null);assert.deepEqual(features,original);
 const noReplica=resolveAttributes([features[0]],2026).get('known');assert.equal(noReplica.owner,null,'No source-label fallback');assert.equal(noReplica.category_ids.owner,'owner:Q34754');
});
