import {test,before,after} from 'node:test';
import assert from 'node:assert/strict';
import {openDatabase,importRecords,geography} from '../database.mjs';
import {resolveTemporal} from '../src/temporal.js';
let db;
const geometry={type:'Polygon',coordinates:[[[0,0],[1,0],[1,1],[0,0]]]};
const record=(id,entity_id,field,value,from=1000,to=1100,extra={})=>({id,entity_id,field,value,valid_from:from,valid_to:to,source:'Explicit test fixture',...extra});
before(()=>{
 db=openDatabase(':memory:');
 importRecords(db,{units:[{id:'c',name:'Continent',level:'continent'},{id:'s',name:'Subcontinent',level:'subcontinent',parent_id:'c'},{id:'r',name:'Region',level:'region',parent_id:'s'},{id:'a',name:'Area',level:'area',parent_id:'r'},{id:'p',name:'Province',level:'province',parent_id:'a'},{id:'p2',name:'Other Province',level:'province',parent_id:'a'}],locations:[{id:'l',name:'Modern municipal name',parent_id:'p',geometry}]});
});
after(()=>db.close());
const at=(year,examples=false)=>resolveTemporal(geography(db),year,examples);
test('direct dated names precede reference attestations in any language, with stable ties and examples last',()=>{
 const base=geography(db),rows=[record('a-reference','l','name','Modern English attestation',1000,1100,{method:'reference',source_status:'reference',language:'en'}),record('z-direct','l','name','Dated local name',1000,1100,{language:'zh'}),record('a-example','l','name','Example',1000,1100,{language:'en',is_example:1})];
 const reference={...base,temporal:{...base.temporal,history:rows}};
 assert.equal(resolveTemporal(reference,1050,true).entities.get('l').display_name,'Dated local name');
 assert.equal(resolveTemporal({...reference,temporal:{...reference.temporal,history:[...rows].reverse()}},1050,true).entities.get('l').display_name,'Dated local name');
 const same=[record('z','l','name','Later ID'),record('a','l','name','Earlier ID')];
 assert.equal(resolveTemporal({...reference,temporal:{...reference.temporal,history:same}},1050).entities.get('l').display_name,'Earlier ID');
 assert.equal(resolveTemporal(reference,1100).entities.get('l').display_name,null);
});
test('unknown historical name and habitation do not imply an absent or rural settlement',()=>{
 const e=at(900).entities.get('l');assert.equal(e.display_name,null);assert.equal(e.status,'unknown');assert.deepEqual(e.attributes,{});assert.equal(at(2026).entities.get('l').display_name,'Modern municipal name');
});
test('dated names at every level retain stable identity; aliases remain searchable outside their dates',()=>{
 importRecords(db,{entity_history:[record('name-old','l','name','Old name'),record('name-new','l','name','New name',1100,1200),record('province-name','p','name','Old province'),record('alias','l','name','Alternate spelling',1000,1200,{name_role:'alias',language:'la'}),record('example-name','l','name','Example name',1000,1100,{is_example:1})]});
 assert.equal(at(1050,true).entities.get('l').display_name,'Old name');assert.equal(at(1100).entities.get('l').display_name,'New name');assert.equal(at(1200).entities.get('l').display_name,null);
 assert.equal(at(1050).units.find(u=>u.id==='p').display_name,'Old province');assert.ok(at(2026).entities.get('l').search_names.includes('Alternate spelling'));assert.equal(at(1050).features[0].id,'l');
});
test('dated membership changes the hierarchy used by map colors and province borders',()=>{
 importRecords(db,{entity_history:[record('parent','l','parent','p2')]});
 assert.equal(at(999).features[0].properties.parent_id,'p');assert.equal(at(1000).features[0].properties.parent_id,'p2');assert.equal(at(1100).features[0].properties.parent_id,'p');
 assert.throws(()=>importRecords(db,{entity_history:[record('skip','l','parent','r',1200,1300)]}),/adjacent/);
 assert.throws(()=>importRecords(db,{entity_history:[record('parent-overlap','l','parent','p',1050,1150)]}),/Overlapping/);
});
test('settlement attributes and existence are separate from a location and successor links keep distinct IDs',()=>{
 importRecords(db,{entities:[{id:'town',kind:'settlement',name:'Town',parent_id:'l',valid_from:1300,valid_to:1400,source:'Test founding and dissolution evidence'},{id:'city',kind:'settlement',name:'City',parent_id:'l',valid_from:1400,source:'Test successor evidence'}],entity_history:[record('town-rank','town','attributes',{rank:'town',habitation:'inhabited'},1300,1400),record('city-rank','city','attributes',{rank:'city',habitation:'inhabited'},1400,1500)],entity_links:[{id:'town-city',predecessor_id:'town',successor_id:'city',kind:'successor',year:1400,source:'Test reconstitution, not a mere rename'}]});
 assert.equal(at(1299).entities.get('town').status,'not_exists');assert.equal(at(1350).entities.get('town').attributes.rank,'town');assert.equal(at(1400).entities.get('town').status,'not_exists');assert.equal(at(1400).entities.get('city').attributes.rank,'city');assert.equal(at(1400).entities.get('l').attributes.rank,undefined);assert.equal(at(1400).links[0].successor_id,'city');
 assert.throws(()=>importRecords(db,{entity_history:[record('before-life','town','attributes',{rank:'city'},1200,1250)]}),/lifetime/);
});
test('explicit uninhabited differs from unknown, and sourced states beat examples',()=>{
 importRecords(db,{entity_history:[record('uninhabited','l','attributes',{habitation:'uninhabited',population:0},1500,1600),record('fake-city','l','attributes',{habitation:'inhabited',rank:'metropolis'},1500,1600,{is_example:1})]});
 assert.equal(at(1500,true).entities.get('l').attributes.habitation,'uninhabited');assert.equal(at(1500).entities.get('l').attributes.population,0);assert.equal(at(1600).entities.get('l').attributes.habitation,undefined);
 assert.throws(()=>importRecords(db,{entity_history:[record('contradiction','l','attributes',{habitation:'uninhabited',rank:'city'},1600,1700)]}),/Uninhabited/);
});
test('broken dated parent chains, invalid dates and interval overlaps roll back atomically',()=>{
 for(const value of [0,2027,-3001])assert.throws(()=>importRecords(db,{entity_history:[record('date','l','name','Invalid',value,2027)]}));
 assert.throws(()=>importRecords(db,{entity_history:[record('atomic','p','name','Temporary',1600,1700),record('absent-parent','p','existence','not_exists',1600,1700)]}),/absent parent/);
 assert.equal(at(1650).entities.get('p').display_name,null);
 assert.throws(()=>importRecords(db,{entity_history:[record('overlap','l','name','Collision',1099,1150)]}),/Overlapping/);
 const json=JSON.parse(JSON.stringify(geography(db)));assert.deepEqual(resolveTemporal(json,1050).features,at(1050).features,'static JSON and server catalogs resolve identically');
});

test('future historical graph entities do not enter geographic grouping tiers',()=>{
 const reference=geography(db);
 const graphKinds=['person','event','army','route','artifact','place','polity','culture','religion'];
 reference.temporal.entities.push(...graphKinds.map(kind=>({id:`graph:${kind}`,kind,name:`Reference ${kind}`,is_example:0})));
 const resolved=resolveTemporal(reference,1000);
 for(const kind of graphKinds){assert.ok(resolved.entities.has(`graph:${kind}`));assert.ok(!resolved.units.some(unit=>unit.id===`graph:${kind}`));}
 assert.equal(resolved.features.length,reference.features.length);
 assert.ok(resolved.units.every(unit=>['province','area','region','subcontinent','continent'].includes(unit.level)));
});
