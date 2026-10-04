import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {gunzipSync} from 'node:zlib';
import { validateHierarchy } from '../hierarchy.mjs';
import { openDatabase, seedDatabase, snapshot, importRecords, validateGeometry, geography } from '../database.mjs';
import { parseYear, validYear, yearToTick, tickToYear, categoryColor, populationColor, levels } from '../src/model.js';
let db;
const createdSourceIds=new Set(JSON.parse(gunzipSync(fs.readFileSync('data/macro-improvements/combined-restoration/aggregate-source-receipt.json.gz'))).added_ids);
before(()=>{ db=openDatabase(':memory:'); seedDatabase(db); });
after(()=>db.close());
test('new source land retains unknown owners and its original source metadata',()=>{
  const parts=JSON.parse(fs.readFileSync('data/world-index.json')).parts;
  const source=parts.flatMap(p=>JSON.parse(fs.readFileSync('data/'+p)).features).filter(f=>createdSourceIds.has(f.id));
  assert.equal(source.length,createdSourceIds.size);
  for(const feature of source){
    const row=db.prepare('SELECT reference_owner,metadata FROM locations WHERE id=?').get(feature.id);
    assert.equal(row.reference_owner,feature.properties.reference_owner??null);
    assert.equal(JSON.parse(row.metadata).reference_version,feature.properties.metadata.reference_version);
  }
});
test('year parsing supports BC/BCE/AD/CE and rejects invalid or out-of-range dates',()=>{
  for (const [input,want] of [['3000 BC',-3000],['44 bce',-44],['2026 AD',2026],['1 CE',1],['-1',-1],['1444',1444],['0',null],['3001 BC',null],['2027',null],['1.5',null],['-20 AD',null],['abc',null],['1e3',null]]) assert.equal(parseYear(input),want,input);
  for (let tick=0;tick<=5025;tick++) assert.equal(yearToTick(tickToYear(tick)),tick);
  assert.equal(tickToYear(yearToTick(-1)+1),1);
  assert.equal(validYear(0),false);
});
test('every location has exactly all six hierarchy levels',()=>{
  const data=geography(db), units=new Map(data.units.map(u=>[u.id,u]));
  validateHierarchy(data.units,data.features.map(f=>f.properties));
  assert.ok(data.features.length>20000 && data.features.length<60000);
  assert.equal(new Set(data.features.map(f=>f.id)).size,data.features.length);
  assert.equal(data.units.filter(u=>u.level==='continent').length,6);
  assert.ok(!data.units.some(u=>u.level==='continent' && u.name==='Antarctica'));
  for (const feature of data.features) {
    validateGeometry(feature.geometry);
    let p=feature.properties.parent_id;
    let previous=0;
    while(p){const parent=units.get(p);assert.ok(parent,feature.id);const order=levels.indexOf(parent.level);assert.equal(order,previous+1,feature.id);previous=order;p=parent.parent_id;}
    assert.ok(feature.properties.metadata.source_name || createdSourceIds.has(feature.id));assert.ok(!('generated' in feature.properties));
    assert.equal(p,null);
  }
  const london=data.features.find(f=>f.id==='atlas:city:GBR-Greater London'); const names=[london.properties.name];
  for (let p=units.get(london.properties.parent_id);p;p=units.get(p.parent_id)) names.push(p.name);
  assert.deepEqual(names,['London','Greater London','London and South East England','Britain','Northern Europe','Europe']);
  assert.match(london.properties.metadata.location_basis,/metropolitan territory/);
  assert.equal(london.properties.metadata.source_member_ids.length,33);
});
test('seed is idempotent and missing history stays missing',()=>{
  seedDatabase(db); assert.ok(db.prepare('SELECT count(*) n FROM locations').get().n>20000);
  for (const year of [-3000,-1,1,1444,2026]) assert.equal(snapshot(db,year).states.length,0);
  assert.throws(()=>snapshot(db,0),/Year must/);
});
test('example intervals are opt-in and end-exclusive, including ownership changes',()=>{
  const owner=(year)=>snapshot(db,year,true).states.find(s=>s.location_id==='atlas:city:GBR-Greater London')?.owner;
  assert.equal(owner(1065),undefined);assert.equal(owner(1706),'England');assert.equal(owner(1707),'Great Britain');assert.equal(owner(1801),undefined);
  const london=snapshot(db,1444,true).states.find(s=>s.location_id==='atlas:city:GBR-Greater London');
  assert.equal(london.population,42054); assert.equal(london.rank,'city'); assert.equal(london.is_example,1);
});
test('atomic imports reject overlapping records, invalid populations, ranks, and parents',()=>{
  const base={location_id:'atlas:city:GBR-Greater London',valid_from:-100,valid_to:1,source:'Test source'};
  for (const values of [{population:-1},{population:1.5},{rank:'village'},{source:''},{valid_from:0},{valid_to:-100}]) assert.throws(()=>importRecords(db,{states:[{...base,...values}]}));
  assert.throws(()=>importRecords(db,{states:[base,base]}),/Overlapping/);
  assert.equal(snapshot(db,-50).states.length,0,'the first record must also roll back');
  assert.throws(()=>importRecords(db,{states:[{...base,location_id:'missing'}]}),/FOREIGN KEY/);
  assert.throws(()=>importRecords(db,{units:[{id:'bad',name:'Bad',level:'province',parent_id:null}]}),/Invalid hierarchy/);
  assert.throws(()=>importRecords(db,{units:[{id:'bad',name:'Bad',level:'continent',parent_id:'self'}]}),/Invalid hierarchy/);
});
test('real records take precedence over examples, with no population interpolation',()=>{
  importRecords(db,{states:[{location_id:'atlas:city:GBR-Greater London',valid_from:1440,valid_to:1445,owner:'Source-backed test owner',population:0,source:'Test fixture source'}]});
  const record=snapshot(db,1444,true).states.find(s=>s.location_id==='atlas:city:GBR-Greater London');
  assert.equal(record.owner,'Source-backed test owner'); assert.equal(record.population,0); assert.equal(record.culture,null);
  assert.equal(snapshot(db,1445).states.length,0);
});
test('boundary versions require polygons and sources, and resolve by date',()=>{
  const geometry={type:'Polygon',coordinates:[[[0,0],[1,0],[1,1],[0,0]]]};
  const row={location_id:'atlas:city:GBR-Greater London',valid_from:-1,valid_to:2,geometry,source:'Test boundary'};
  importRecords(db,{boundaries:[row]});
  assert.equal(snapshot(db,-1).boundaries.length,1); assert.deepEqual(snapshot(db,1).boundaries[0].geometry,geometry); assert.equal(snapshot(db,2).boundaries.length,0);
  assert.throws(()=>importRecords(db,{boundaries:[row]}),/Overlapping/);
  for (const invalid of [{type:'Point',coordinates:[1,2]},{type:'Polygon',coordinates:[]},{type:'Polygon',coordinates:[[[0,0],[1,0],[1,1],[0,1]]]},{type:'Polygon',coordinates:[[[0,0],[181,0],[1,1],[0,0]]]}]) assert.throws(()=>validateGeometry(invalid));
});
test('unknown, zero population, and category colors have stable, distinct semantics',()=>{
  assert.notEqual(populationColor(null,100),populationColor(0,100));
  assert.notEqual(populationColor(0,100),populationColor(100,100));
  assert.equal(categoryColor('England'),categoryColor('England'));
  const owners=new Set(geography(db).features.map(f=>f.properties.reference_owner));
  assert.equal(new Set([...owners].map(categoryColor)).size,owners.size,'modern owners must have distinct colors');
});

test('historical political records are dated, sourced, and do not extend into 2025',()=>{
  const medieval=snapshot(db,1444,false,true).polities;assert.ok(medieval.length>50);assert.ok(medieval.every(f=>f.properties.valid_from<=1444 && f.properties.valid_to>1444 && f.properties.source.includes('Cliopatria')));
  assert.equal(snapshot(db,2025).polities.length,0);assert.equal(snapshot(db,2026).polities.length,0);assert.ok(snapshot(db,-3000,false,true).polities.length>0);
});

test('both Huidong counties have complete, distinct geographical parents',()=>{
  const data=geography(db), units=new Map(data.units.map(u=>[u.id,u]));
  const huidong=data.features.filter(f=>f.properties.name==='Huidongxian');
  assert.equal(huidong.length,2);
  const chains=huidong.map(f=>{const out=[];for(let p=units.get(f.properties.parent_id);p;p=units.get(p.parent_id))out.push(p.name);return out;});
  assert.ok(chains.some(c=>JSON.stringify(c)===JSON.stringify(['Liangshan Yi Autonomous Prefecture','Sichuan','Southwest China','Eastern Asia','Asia'])));
  assert.ok(chains.some(c=>JSON.stringify(c)===JSON.stringify(['Huizhou','Guangdong','South China','Eastern Asia','Asia'])));
});

test('inserts and updates cannot skip hierarchy levels',()=>{
  const region=db.prepare("SELECT id FROM units WHERE level='region' LIMIT 1").get().id;
  const area=db.prepare("SELECT id FROM units WHERE level='area' LIMIT 1").get().id;
  assert.throws(()=>importRecords(db,{units:[{id:'skipped-area',name:'Invalid',level:'province',parent_id:region}]}),/levels cannot be skipped/);
  assert.throws(()=>db.prepare('UPDATE locations SET parent_id=? WHERE id=?').run(area,'atlas:city:GBR-Greater London'),/province parent/);
  const province=db.prepare("SELECT id FROM units WHERE level='province' LIMIT 1").get().id;
  assert.throws(()=>db.prepare('UPDATE units SET parent_id=? WHERE id=?').run(region,province),/levels cannot be skipped/);
  assert.throws(()=>db.prepare("UPDATE units SET level='area' WHERE id=?").run(province),/immutable/);
});






test('geographic regions cross ownership borders and subdivide large countries',()=>{
 const data=geography(db),units=new Map(data.units.map(u=>[u.id,u]));
 const region=f=>{let u=units.get(f.properties.parent_id);while(u.level!=='region')u=units.get(u.parent_id);return u;};
 const macau=data.features.find(f=>f.id==='atlas:territory:MAC');assert.equal(region(macau).name,'South China');assert.notEqual(region(macau).name,macau.properties.reference_owner);
 for(const owner of ['United States','Russia'])assert.ok(new Set(data.features.filter(f=>f.properties.reference_owner?.includes(owner)).map(f=>region(f).id)).size>1,owner);
 const sameRegion=data.features.filter(f=>region(f).id===region(macau).id);assert.ok(new Set(sameRegion.map(f=>f.properties.reference_owner)).size>1);
 const roma=data.features.find(f=>f.id==='atlas:location:ITA:SLL:1209');assert.ok(roma);assert.equal(units.get(roma.properties.parent_id).name,'Roma');assert.ok(!data.features.some(f=>f.properties.name==='Lazio'));assert.ok(roma.properties.metadata.search_aliases.includes('Rome'));
 const report=JSON.parse(fs.readFileSync('data/granularity-report.json'));assert.equal(report.selections.find(x=>x.boundaryISO==='DEU').boundaryType,'ADM3');
});



test('non-Latin municipalities remain distinct and city memberships contain all districts',()=>{
 const data=geography(db),byId=new Map(data.features.map(f=>[f.id,f]));
 for(const [id,name] of [['gb:TWN:ADM2:52511910B4802898208422','線西鄉'],['gb:TWN:ADM2:52511910B24462040337349','永靖鄉'],['gb:TWN:ADM2:52511910B36549244443661','泰安鄉'],['gb:TWN:ADM2:52511910B52234359951443','埔心鄉']])assert.equal(byId.get(id)?.properties.name,name);
 for(const [id,count] of [['atlas:city:KOR-11',25],['atlas:city:TWN-1166',12],['atlas:city:TWN-1167',29],['atlas:city:TWN-1156',38],['atlas:city:TWN-1164',7]]){
  const members=byId.get(id).properties.metadata.source_member_ids;assert.equal(members.length,count,id);
  for(const member of members)assert.ok(!byId.has(member),`${member} remains active within ${id}`);
 }
});
