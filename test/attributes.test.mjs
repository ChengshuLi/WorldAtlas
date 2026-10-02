import {test} from 'node:test';
import assert from 'node:assert/strict';
import {resolveAttributes} from '../src/attributes.js';
import {environmentalClassification} from '../src/environment-classifications.js';
import {openDatabase,importRecords} from '../database.mjs';
const features=[{id:'l',properties:{reference_owner:'Modern owner'}}];
const r=(id,attribute,value,extra={})=>({id,location_id:'l',attribute,value,valid_from:1000,valid_to:1100,method:'direct',source:'Fixture',...extra});
test('attributes resolve independently with direct evidence ahead of spatial derivations and examples',()=>{
 const records=[r('derived','owner','Derived',{method:'majority-area',category_id:'owner:d'}),r('owner','owner','Direct',{category_id:'owner:fixed'}),r('population','population',0),r('example','religion','Example',{is_example:1})];
 const at=year=>resolveAttributes(features,year,{records,examples:true}).get('l');
 assert.equal(at(1050).owner,'Direct');assert.equal(at(1050).population,0);assert.equal(at(1050).category_ids.owner,'owner:fixed');assert.equal(at(1050).culture,null);assert.equal(at(1100).owner,null);assert.equal(at(2026).owner,'Modern owner');assert.equal(at(1050).rank,'unsettled');assert.equal(at(1050).provenance.rank.metadata.supporting_record_id,'population');
 const unknown=resolveAttributes(features,1050,{records:[r('unknown','owner',null),records[0]]}).get('l');assert.equal(unknown.owner,null);assert.equal(unknown.provenance.owner.method,'direct');
});
test('field evidence does not erase an independently supported attribute and examples do not mask modern reference',()=>{
 const state={id:1,location_id:'l',valid_from:1000,valid_to:1100,owner:'Legacy',religion:'Faith',is_example:0,source:'Legacy fixture'};
 const result=resolveAttributes(features,1050,{states:[state],records:[r('new','owner','Specific')]}).get('l');assert.equal(result.owner,'Specific');assert.equal(result.religion,'Faith');
});
test('typed imports reject overlapping field records and preserve stable category IDs',()=>{
 const db=openDatabase(':memory:');
 try{
 importRecords(db,{units:[{id:'c',name:'c',level:'continent'},{id:'s',name:'s',level:'subcontinent',parent_id:'c'},{id:'r',name:'r',level:'region',parent_id:'s'},{id:'a',name:'a',level:'area',parent_id:'r'},{id:'p',name:'p',level:'province',parent_id:'a'}],locations:[{id:'l',name:'l',parent_id:'p',geometry:{type:'Polygon',coordinates:[[[0,0],[1,0],[1,1],[0,0]]]}}],attribute_entities:[{id:'owner:fixed',name:'Owner',kind:'owner',source:'Fixture'}],attribute_records:[r('first','owner','Owner',{category_id:'owner:fixed'})]});
 assert.throws(()=>importRecords(db,{attribute_records:[r('second','owner','Other',{category_id:'owner:fixed'})]}),/Overlapping/);
 assert.throws(()=>importRecords(db,{attribute_records:[r('negative','population',-1)]}),/population/);
 assert.throws(()=>importRecords(db,{attribute_records:[r('array','culture',['A','B'])]}),/scalar/);
 assert.throws(()=>importRecords(db,{attribute_records:[r('missing-id','owner','Owner')]}),/Stable category_id/);
 assert.throws(()=>db.prepare('INSERT INTO attribute_records VALUES (?,?,?,?,?,?,?,?,?,?,?,?)').run('raw-array','l','climate','["A","B"]',null,1100,1200,'direct','sourced','Fixture',0,'{}'),/scalar|CHECK/);
 const raw=(id,attribute,value,extra={})=>db.prepare('INSERT INTO attribute_records VALUES (?,?,?,?,?,?,?,?,?,?,?,?)').run(id,'l',attribute,JSON.stringify(value),extra.category_id??null,1100,1200,'direct','sourced',extra.source??'Fixture',0,JSON.stringify(extra.metadata??{}));
 assert.throws(()=>raw('numeric-climate','climate',5),/scalar|CHECK/);
 assert.throws(()=>raw(null,'climate','Oceanic'),/identity|NOT NULL/);
 assert.throws(()=>db.prepare('INSERT INTO attribute_entities VALUES (?,?,?,?)').run(null,'owner','Owner','Fixture'),/identity|NOT NULL/);
 assert.throws(()=>db.prepare('INSERT INTO attribute_records VALUES (?,?,?,?,?,?,?,?,?,?,?,?)').run('fractional-date','l','climate','"Oceanic"',null,1100.5,1200,'direct','sourced','Fixture',0,'{}'),/date interval|CHECK/);
 assert.throws(()=>raw('unsafe-population','population',9007199254740992),/population|CHECK/);
 assert.throws(()=>raw('empty-source','climate','Oceanic',{source:' '}),/source|CHECK/);
 assert.throws(()=>raw('whitespace-source','climate','Oceanic',{source:'\n\t\u00a0'}),/source|CHECK/);
 assert.throws(()=>raw('whitespace-value','climate','\n\t\u00a0'),/empty|scalar|CHECK/);
 assert.throws(()=>importRecords(db,{attribute_records:[r('missing-value','climate',undefined)]}),/Invalid attribute/);
 assert.throws(()=>raw('metadata-array','climate','Oceanic',{metadata:[]}),/metadata/);
 assert.throws(()=>raw('wrong-kind','culture','Culture',{category_id:'owner:fixed'}),/kind/);
 assert.throws(()=>raw('unknown-category','owner',null,{category_id:'owner:fixed'}),/known categorical/);
 assert.throws(()=>db.prepare("DELETE FROM attribute_records WHERE id='first'").run(),/append-only/);
 assert.throws(()=>db.prepare("UPDATE attribute_records SET value='null' WHERE id='first'").run(),/append-only/);
 assert.throws(()=>db.prepare("UPDATE attribute_entities SET id='owner:changed' WHERE id='owner:fixed'").run(),/immutable/);
 assert.equal(db.prepare('SELECT count(*) n FROM attribute_records').get().n,1);
 importRecords(db,{entities:[{id:'l',name:'l',kind:'location',valid_from:1000,valid_to:1200,source:'Dated footprint evidence'}]});
 assert.throws(()=>importRecords(db,{entities:[{id:'l',name:'l',kind:'location',valid_from:1050,valid_to:1200,source:'Conflicting lifetime'}]}),/invalidate attribute/);
 assert.equal(db.prepare("SELECT valid_from FROM entities WHERE id='l'").get().valid_from,1000);
 assert.throws(()=>importRecords(db,{attribute_records:[r('before-existence','climate','Oceanic',{valid_from:900})]}),/lifetime/);
 assert.throws(()=>db.prepare('INSERT INTO attribute_records VALUES (?,?,?,?,?,?,?,?,?,?,?,?)').run('outside','l','topography','"Flatland"',null,1200,1300,'direct','sourced','Fixture',0,'{}'),/lifetime/);
 importRecords(db,{attribute_records:[r('uninhabited','habitation','uninhabited')]});
 assert.throws(()=>importRecords(db,{attribute_records:[r('fake-city','rank','city')]}),/Uninhabited/);
 }finally{db.close();}
});

test('no-year-zero resolution, exclusive interval ends and opt-in examples remain deterministic',()=>{
 const records=[r('bc','climate','climate:Cfb',{valid_from:-1,valid_to:1,method:'reference'}),r('ad','climate','climate:Af',{valid_from:1,valid_to:2,method:'reference'}),r('example-owner','owner','Example',{valid_from:2026,valid_to:2027,is_example:1,category_id:'owner:example'})];
 assert.equal(resolveAttributes(features,-1,{records}).get('l').climate,environmentalClassification('climate','climate:Cfb').label);
 assert.equal(resolveAttributes(features,1,{records}).get('l').climate,environmentalClassification('climate','climate:Af').label);
 assert.throws(()=>resolveAttributes(features,0,{records}),/excluding zero/);
 assert.equal(resolveAttributes(features,2026,{records,examples:true}).get('l').owner,'Modern owner');
 const forward=resolveAttributes(features,1050,{records:[r('b','vegetation','vegetation:mangroves',{method:'derived'}),r('a','vegetation','vegetation:farmlands',{method:'derived'})]}).get('l');
 const reverse=resolveAttributes(features,1050,{records:[r('a','vegetation','vegetation:farmlands',{method:'derived'}),r('b','vegetation','vegetation:mangroves',{method:'derived'})]}).get('l');
 assert.equal(forward.vegetation,reverse.vegetation);
 assert.equal(forward.category_ids.vegetation,'vegetation:farmlands');
});

test('compact references preserve supported dates and field provenance',async()=>{
 const {decodeReferences}=await import('../src/reference-records.js');
 const index={version:2,values:['Cfb oceanic'],types:[{attribute:'climate',valid_from:1901,valid_to:1931,method:'reference',status:'reference',source:'Climate normals',metadata:{normal_period:[1901,1930]}}]};
 const parts=[[['l',[[0,0,.7,1]]]]];
 assert.deepEqual(decodeReferences(parts,index,1000),[]);assert.deepEqual(decodeReferences(parts,index,1931),[]);
 const r=decodeReferences(parts,index,1920)[0];assert.equal(r.value,'Cfb oceanic');assert.equal(r.metadata.share,.7);assert.deepEqual(r.metadata.normal_period,[1901,1930]);
});


test('reference territories resolve to their political owner without changing geographic identity',()=>{
 const data=[{id:'hong-kong',properties:{reference_owner:'Hong Kong S.A.R.',metadata:{reference_polity:'China',reference_owner_id:'owner:Q148',reference_polity_status:'reference'}}},{id:'reef',properties:{reference_owner:'Scarborough Reef',metadata:{reference_polity:null,reference_polity_status:'disputed'}}}];
 const result=resolveAttributes(data,2026);assert.equal(result.get('hong-kong').owner,'China');assert.equal(result.get('hong-kong').category_ids.owner,'owner:Q148');assert.equal(data[0].properties.reference_owner,'Hong Kong S.A.R.');assert.equal(result.get('reef').owner,null);assert.equal(result.get('reef').provenance.owner.status,'disputed');
 assert.equal(resolveAttributes(data,1000).get('hong-kong').owner,null);
});
