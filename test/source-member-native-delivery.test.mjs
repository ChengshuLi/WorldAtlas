import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {deriveSourceTargetNativeDelta,nativeRowLatitudes} from '../src/native-grid.js';
import {ImmutableReader} from '../scripts/check-effective-geographic-regression.mjs';
import {constructOriginalAuthority} from '../scripts/delivery-handoff-advance.mjs';

const rectangle=(left,right,bottom=-40,top=40)=>({type:'Polygon',coordinates:[[[left,bottom],[right,bottom],[right,top],[left,top],[left,bottom]]]});
const feature=(id,pixelIndex,geometry,target_id)=>({id,pixelIndex,geometry,...(target_id?{target_id}:{})});
function nativeInput(){
  const a=feature('source:A',1,rectangle(-89,1),'city'),b=feature('source:B',1,rectangle(-1,89),'city');
  return {targets:[{id:'city',pixelIndex:1}],sourceFeatures:[a,b],
    coverageFeatures:[{...feature('city',1,a.geometry),source_id:a.id},{...feature('city',1,b.geometry),source_id:b.id}],
    ownerRows:Array.from({length:8},(_,y)=>({y,complete_owner_intervals:[]})),
    size:8,latitudes:nativeRowLatitudes(8),rowStart:0,rowEnd:8};
}
test('accepted member parts union once without changing original source features',()=>{
  const input=nativeInput(),before=structuredClone(input),result=deriveSourceTargetNativeDelta(input);
  assert.deepEqual(result.rows,[{y:3,runs:[[2,6,1]]},{y:4,runs:[[2,6,1]]}]);
  assert.equal(result.assigned_cells,8);assert.equal(result.ambiguous_owner_cells,0);
  assert.equal(result.targets.length,1);assert.deepEqual(input,before);
});
test('same-owner overlap is a union, while a competing original remains ambiguous',()=>{
  const input=nativeInput();input.sourceFeatures[0].geometry=rectangle(-89,46);
  const overlap=deriveSourceTargetNativeDelta(input);assert.equal(overlap.assigned_cells,8);
  input.sourceFeatures.push(feature('source:C',2,rectangle(-1,89)));
  const conflict=deriveSourceTargetNativeDelta(input);
  assert.equal(conflict.assigned_cells,4);assert.equal(conflict.ambiguous_owner_cells,4);
});
test('mapped member support cannot borrow an unmeasured sibling original',()=>{
  const input=nativeInput();input.sourceFeatures[0].geometry=rectangle(-89,-1);
  input.coverageFeatures=[{...feature('city',1,rectangle(-89,89)),source_id:'source:A'}];
  const result=deriveSourceTargetNativeDelta(input);
  assert.equal(result.assigned_cells,4);assert.equal(result.unsupported_coverage_cells,4);
});
test('same-owner holes, islands and occupied/excluded cells preserve their separate meanings',()=>{
  const input=nativeInput();
  input.sourceFeatures[0].geometry={type:'Polygon',coordinates:[...rectangle(-89,89).coordinates,...rectangle(-46,46).coordinates]};
  input.coverageFeatures[0].geometry=rectangle(-89,89);
  input.sourceFeatures[1].geometry=rectangle(-10,10); // no cell centres in this island
  const holes=deriveSourceTargetNativeDelta(input);assert.equal(holes.assigned_cells,4);
  input.sourceFeatures[1].geometry=rectangle(-30,0); // an independent island fills only the left hole cell
  input.coverageFeatures[1].geometry=input.sourceFeatures[1].geometry;
  const island=deriveSourceTargetNativeDelta(input);assert.equal(island.assigned_cells,6);
  input.ownerRows[3].complete_owner_intervals=[[2,3,9]];
  input.territorialExclusions=[feature('city',1,rectangle(46,89))];
  const result=deriveSourceTargetNativeDelta(input);
  assert.equal(result.assigned_cells,3);assert.equal(result.already_owned_cells,1);
  assert.equal(result.territorial_exclusion_cells,2);assert.equal(result.reassigned_cells,0);
});
test('an original member boundary remains withheld inside a same-owner union',()=>{
  const input=nativeInput();input.sourceFeatures[0].geometry=rectangle(-89,22.5);
  input.sourceFeatures[1].geometry=rectangle(0,89);
  input.coverageFeatures=input.sourceFeatures.map(f=>({...feature('city',1,f.geometry),source_id:f.id}));
  const result=deriveSourceTargetNativeDelta(input);
  assert.equal(result.boundary_cells,2);assert.equal(result.assigned_cells,6);
});
for(const [name,change,pattern]of [
  ['duplicate original ID',i=>i.sourceFeatures.push(i.sourceFeatures[0]),/source owner roster/],
  ['one owner with two accepted IDs',i=>i.sourceFeatures[1].target_id='other-city',/Conflicting source owner/],
  ['one accepted ID with two owners',i=>i.sourceFeatures[1].pixelIndex=2,/Conflicting source owner/],
  ['missing member coverage identity',i=>delete i.coverageFeatures[0].source_id,/exact original source/],
  ['foreign member coverage',i=>i.coverageFeatures[0].source_id='source:foreign',/exact original source/],
])test('member native operator rejects '+name,()=>{
  const input=nativeInput();change(input);assert.throws(()=>deriveSourceTargetNativeDelta(input),pattern);
});

// Whole immutable in-memory Git bodies exercise the real constructor, reader
// admission and qualifier. Only the Git transport is substituted; geometry and
// every catalogue/membership/physical join are processed by production code.
const version='a'.repeat(40),family='gb:TST:ADM2',a=family+':A',b=family+':B',c=family+':C';
const size=262166,latitudes=nativeRowLatitudes(size),latitudeBytes=Buffer.alloc(size*8);
for(let i=0;i<size;i++)latitudeBytes.writeDoubleLE(latitudes[i],i*8);
const digest=raw=>createHash('sha256').update(raw).digest('hex');
const blob=raw=>createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex');
const collection=features=>({type:'FeatureCollection',features});
const rawFeature=(id,geometry)=>({type:'Feature',properties:{shapeID:id},geometry});
function constructorFixture(change=()=>{}){
  const first=rectangle(-.03,.006,-.02,.02),second=rectangle(.004,.03,-.02,.02);
  const cityGeometry={type:'MultiPolygon',coordinates:[first.coordinates,second.coordinates]};
  const direct=rectangle(.015,.06,-.02,.02);
  const state={originals:[rawFeature('A',first),rawFeature('B',second),rawFeature('C',direct)],
    roster:[{id:'city',index:1},{id:c,index:2},{id:'other-city',index:3}],
    lineage:{changes:[{id:'city',replaces:[a,b]},{id:'irrelevant-split-1',replaces:['unrelated']},{id:'irrelevant-split-2',replaces:['unrelated']}]},
    index:{parts:['geography/part-0.json']},
    accepted:collection([{type:'Feature',id:'city',geometry:cityGeometry,properties:{metadata:{source_member_ids:[a,b]}}}]),
    targets:[{id:a,target_id:'city',pixelIndex:1,source_family:family,base_geometry:cityGeometry,coverage_classes:['mapped_land_support']},
      {id:b,target_id:'city',pixelIndex:1,source_family:family,base_geometry:cityGeometry,coverage_classes:['mapped_land_support']}],
    physical:{results:[{target:a,issues:[],support:{mapped_land_support:first}},{target:b,issues:[],support:{mapped_land_support:second}}]},
    measured:[{target:a,consumed:{geometry:first},selected:{id:'city',geometry:cityGeometry}},
      {target:b,consumed:{geometry:second},selected:{id:'city',geometry:cityGeometry}}],
    proposed:{rows:[{y:size/2,runs:[[Math.floor(size/2-.02/360*size),Math.floor(size/2-.02/360*size)+1,1]]}]},
    membership:true};
  change(state);
  const files=new Map(),byBlob=new Map();
  const put=(name,value)=>{
    const raw=Buffer.isBuffer(value)?value:Buffer.from(JSON.stringify(value));
    const pin={commit:version,path:name,mode:'100644',git_blob_oid:blob(raw),bytes:raw.length,sha256:digest(raw)};
    files.set(name,{raw,pin});byBlob.set(pin.git_blob_oid,raw);return pin;
  };
  const source=put('original-source.json',collection(state.originals)),roster=put('owners.json',state.roster);
  const physical=put('physical.json',state.physical),measured=put('measured.json',state.measured);
  const catalogue=put('coordination/engineering/original-geography-source-corpus-20261006/catalogue.json',{
    products:[{key:family,parts:[{path:source.path,bytes:source.bytes,sha256:source.sha256}],
      feature_count:state.originals.length,original_bytes:source.bytes,original_sha256:source.sha256}]});
  const nativeLatitudes=put('latitudes.f64le',latitudeBytes);
  const membership={index:put('data/world-index.json',state.index),lineage:put('data/semantic-report.json',state.lineage),
    parts:[put('data/geography/part-0.json',state.accepted)]};
  const evidence=put('source-evidence.json',{version:1,kind:'source-target-native-evidence-v1',catalogue,
    owner_roster:roster,physical_evidence:physical,physical_input:measured,physical_reproduction:put('physical.py',Buffer.from('# retained fixture')),
    native_latitudes:nativeLatitudes,native_contract:{size,native_latitudes:nativeLatitudes,original_assets:{bounds:{sha256:roster.sha256}}},
    base_reference:{id:'fixture-base'},families:[{source_id:family,parts:[source]}],
    targets:state.targets.map(target=>({...target,source_receipt_sha256:physical.sha256})),
    ...(state.membership?{source_membership:membership}:{})});
  const patch=put('patch.json',state.proposed);
  class FixtureReader extends ImmutableReader{
    git(...args){
      if(args[0]==='ls-tree'){
        const name=args.at(-1),entry=files.get(name);assert.ok(entry,name);
        return Buffer.from(`100644 blob ${entry.pin.git_blob_oid}\t${name}\0`);
      }
      if(args[0]==='cat-file'&&args[1]==='-e')return Buffer.alloc(0);
      if(args[0]==='cat-file'&&args[1]==='-s')return Buffer.from(String(byBlob.get(args[2]).length));
      if(args[0]==='cat-file'&&args[1]==='blob')return byBlob.get(args[2]);
      throw Error('Unexpected fixture Git request: '+args.join(' '));
    }
  }
  const reader=()=>new FixtureReader('.',version,{runtimeBytes:0,metadataBytes:0,outputBytes:0,
    allowance:{phaseBytes:128*1024*1024,rssBytes:1024*1024*1024}});
  const locators={source_evidence:{commit:version,path:evidence.path},native_patch:{commit:version,path:patch.path}};
  return {run:()=>constructOriginalAuthority(reader(),locators),files,byBlob,membership,reader,state};
}
test('actual constructor joins original member evidence into one accepted owner ledger',()=>{
  const fixture=constructorFixture(),result=fixture.run();
  assert.equal(result.ledger_rows.length,1);assert.equal(result.ledger_rows[0].target_id,'city');
  assert.equal(result.ledger_rows[0].native_cells,1);assert.equal(result.ledger_rows[0].pixelIndex,1);
  assert.deepEqual(result.ledger_rows[0].base_geometry,fixture.state.accepted.features[0].geometry);
});
function directTarget(state,{membership=true,overlap=false}={}){
  const geometry=state.originals[2].geometry;
  state.targets=[{id:c,pixelIndex:2,source_family:family,base_geometry:geometry,coverage_classes:['mapped_land_support']}];
  state.physical.results=[{target:c,issues:[],support:{mapped_land_support:geometry}}];
  state.measured=[{target:c,consumed:{geometry},selected:{id:c,geometry}}];
  const x=Math.floor(size/2+(overlap?.02:.05)/360*size);
  state.proposed.rows=[{y:size/2,runs:[[x,x+1,2]]}];state.membership=membership;
  if(!membership)state.originals[2].geometry=rectangle(.04,.06,-.02,.02);
}
test('actual constructor maps merged competitors without inventing their physical results',()=>{
  const fixture=constructorFixture(s=>directTarget(s));
  assert.deepEqual(fixture.state.physical.results.map(r=>r.target),[c]);
  assert.equal(fixture.run().ledger_rows[0].target_id,c);
  assert.throws(()=>constructorFixture(s=>directTarget(s,{overlap:true})).run(),/lack unique source-target coverage/);
});
test('actual constructor retains the direct-owner evidence route without membership pins',()=>{
  const fixture=constructorFixture(s=>{
    directTarget(s,{membership:false});const geometry=s.originals[2].geometry;
    s.targets[0].base_geometry=geometry;s.physical.results[0].support.mapped_land_support=geometry;
    s.measured[0].consumed.geometry=geometry;s.measured[0].selected.geometry=geometry;
  });
  assert.equal(fixture.run().ledger_rows[0].target_id,c);
});
for(const [name,change,pattern]of [
  ['missing sibling from whole original product',s=>s.originals.splice(1,1),/complete source aggregation member/],
  ['duplicate original source ID',s=>s.originals.push(s.originals[0]),/original source feature identity/],
  ['omitted competing lineage owner',s=>s.lineage.changes.push({id:'other-city',replaces:[a]}),/ambiguous accepted source membership/],
  ['native owner also claimed as merged member',s=>s.roster.push({id:a,index:4}),/conflicts with a direct native owner/],
  ['incomplete canonical member set',s=>s.accepted.features[0].properties.metadata.source_member_ids=[a],/aggregation member set/],
  ['duplicate canonical member',s=>s.accepted.features[0].properties.metadata.source_member_ids.push(a),/aggregation member set/],
  ['missing membership proof',s=>s.membership=false,/accepted source membership/],
  ['foreign canonical containing part',s=>s.index.parts=['geography/elsewhere.json'],/membership part/],
  ['unsupported cross-family member',s=>{s.lineage.changes[0].replaces.push('gb:OTHER:A');s.accepted.features[0].properties.metadata.source_member_ids.push('gb:OTHER:A');},/complete source aggregation member/],
  ['wrong accepted target index',s=>s.targets[0].pixelIndex=2,/source-target identity/],
  ['conflicting accepted target bases',s=>s.targets[1].base_geometry=rectangle(0,1),/Conflicting accepted target base/],
  ['coherently changed physical selected base',s=>{const g=rectangle(0,1);s.targets.forEach(t=>t.base_geometry=g);s.measured.forEach(r=>r.selected.geometry=g);},/aggregate base geometry/],
  ['wrong consumed original geometry',s=>s.measured[0].consumed.geometry=rectangle(0,1),/measured whole inputs/],
  ['wrong measured accepted ID',s=>s.measured[0].selected.id='other-city',/measured whole inputs/],
  ['duplicated physical member result',s=>s.physical.results.push(s.physical.results[0]),/duplicate physical source member/],
  ['duplicated measured member input',s=>s.measured.push(s.measured[0]),/measured whole inputs/],
])test('actual constructor rejects '+name+' after coherent input rehashing',()=>{
  assert.throws(()=>constructorFixture(change).run(),pattern);
});
test('actual constructor does not apply oversized member A support to unmeasured member B',()=>{
  const fixture=constructorFixture(s=>{
    s.targets=s.targets.slice(0,1);s.physical.results=s.physical.results.slice(0,1);s.measured=s.measured.slice(0,1);
    s.physical.results[0].support.mapped_land_support=rectangle(-.03,.03,-.02,.02);
    const x=Math.floor(size/2+.02/360*size);s.proposed.rows=[{y:size/2,runs:[[x,x+1,1]]}];
    s.originals[2].geometry=rectangle(.04,.06,-.02,.02);
  });
  assert.throws(()=>fixture.run(),/lack unique source-target coverage/);
});
test('actual constructor rejects membership pins different from selected canonical bytes',()=>{
  const fixture=constructorFixture(),old=fixture.files.get(fixture.membership.lineage.path);
  const raw=Buffer.from(JSON.stringify({changes:[]}));
  fixture.byBlob.set(blob(raw),raw);fixture.files.set(fixture.membership.lineage.path,{raw,pin:{...old.pin,git_blob_oid:blob(raw),bytes:raw.length}});
  assert.throws(()=>fixture.run(),/membership differs from selected canonical bytes/);
});
