import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {deriveSourceTargetNativeDelta,nativeRowLatitudes,nativePolygonIntervals,polygonParts} from '../src/native-grid.js';
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
for(const [name,change,pattern]of [
  ['duplicate original ID',i=>i.sourceFeatures.push(i.sourceFeatures[0]),/source owner roster/],
  ['out-of-range native owner',i=>{i.sourceFeatures.forEach(f=>f.pixelIndex=2**32);i.targets[0].pixelIndex=2**32;},/source owner roster/],
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
test('actual constructor supports an aggregation retaining an original member owner ID',()=>{
  const fixture=constructorFixture(s=>{
    s.roster[0].id=a;s.lineage.changes[0].id=a;s.accepted.features[0].id=a;
    s.targets.forEach(target=>target.target_id=a);s.measured.forEach(input=>input.selected.id=a);
  });
  assert.equal(fixture.run().ledger_rows[0].target_id,a);
  assert.equal(fixture.run().ledger_rows[0].native_cells,1);
});
for(const [name,mutate,pattern]of [
  ['omitted sibling',s=>s.originals.splice(1,1),/complete source aggregation member/],
  ['coherently wrong survivor base',s=>{const geometry=rectangle(0,1);s.targets[0].base_geometry=geometry;s.measured[0].selected.geometry=geometry;},/aggregate base geometry/],
])test('surviving original owner cannot bypass '+name,()=>{
  const fixture=constructorFixture(s=>{
    s.roster[0].id=a;s.lineage.changes[0].id=a;s.accepted.features[0].id=a;
    s.targets=s.targets.slice(0,1);s.targets[0].target_id=a;
    s.measured=s.measured.slice(0,1);s.measured[0].selected.id=a;
    s.physical.results=s.physical.results.slice(0,1);mutate(s);
  });
  assert.throws(()=>fixture.run(),pattern);
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

const emptyPolygon=()=>({type:'Polygon',coordinates:[]});
function withResiduals(state,witnesses,member=0){
  const result=state.physical.results[member];
  result.support={mapped_land_support:result.support.mapped_land_support,
    mapped_inland_water_support:emptyPolygon(),outside_mapped_L1_context:emptyPolygon(),
    hierarchy_disagreements:Object.fromEntries(['L2-outside-L1','L3-outside-L2','L4-outside-L3']
      .map(key=>[key,emptyPolygon()])),missing_reconstruction:emptyPolygon(),
    extra_reconstruction:emptyPolygon(),contradictory_land_water_support:emptyPolygon()};
  result.issues=witnesses.map(([reason,geometry])=>{result.support[reason]=geometry;return {reason,geometry};});
  return result;
}
const disjointResidual=()=>rectangle(-.01,.005,-.01,.01);
for(const reasons of [['missing_reconstruction'],['extra_reconstruction'],['missing_reconstruction','extra_reconstruction']])
  test('actual constructor retains requested cells outside complete '+reasons.join(' and ')+' witnesses',()=>{
    const fixture=constructorFixture(s=>withResiduals(s,reasons.map(reason=>[reason,disjointResidual()])));
    const result=fixture.run();
    assert.deepEqual(result.ledger_rows[0].native_rows,fixture.state.proposed.rows);
    assert.equal(result.ledger_rows[0].native_cells,1);
    assert.equal(result.ledger_rows[0].source_receipt_sha256,fixture.files.get('physical.json').pin.sha256);
    assert.equal(fixture.state.physical.results[0].issues.length,reasons.length);
  });
test('residual exception accepts exact empty multipolygon and collection operations',()=>{
  const fixture=constructorFixture(s=>{
    const result=withResiduals(s,[['extra_reconstruction',disjointResidual()]]);
    result.support.missing_reconstruction={type:'MultiPolygon',coordinates:[]};
    result.support.contradictory_land_water_support={type:'GeometryCollection',geometries:[]};
  });
  assert.equal(fixture.run().ledger_rows[0].native_cells,1);
});
test('residual hole interior passes without erasing its nonvacuous outer pointset',()=>{
  const outer=rectangle(-.03,.005,-.01,.01),hole=rectangle(-.025,-.015,-.005,.005);
  const residual={type:'Polygon',coordinates:[outer.coordinates[0],hole.coordinates[0]]};
  const fixture=constructorFixture(s=>withResiduals(s,[['missing_reconstruction',residual]]));
  assert.equal(fixture.run().ledger_rows[0].native_cells,1);
});
test('one affected centre rejects a whole requested interval rather than shrinking it',()=>{
  const fixture=constructorFixture(s=>{
    const run=s.proposed.rows[0].runs[0],longitude=(run[0]+1.5)/size*360-180;
    run[1]=run[0]+3;
    withResiduals(s,[['extra_reconstruction',rectangle(longitude-.0002,longitude+.0002,-.01,.01)]]);
  });
  assert.throws(()=>fixture.run(),/intersect a physical reconstruction residual/);
  assert.equal(fixture.state.proposed.rows[0].runs[0][1]-fixture.state.proposed.rows[0].runs[0][0],3);
});
test('a same-owner sibling residual veto cannot be bypassed through clean member coverage',()=>{
  const fixture=constructorFixture(s=>withResiduals(s,[['missing_reconstruction',rectangle(-.025,-.015,-.01,.01)]],1));
  assert.throws(()=>fixture.run(),/intersect a physical reconstruction residual/);
});
test('multipart residuals check every retained part',()=>{
  const geometry={type:'MultiPolygon',coordinates:[disjointResidual().coordinates,
    rectangle(-.025,-.015,-.01,.01).coordinates]};
  assert.throws(()=>constructorFixture(s=>withResiduals(s,[['extra_reconstruction',geometry]])).run(),
    /intersect a physical reconstruction residual/);
});

function exactBoundaryTarget(state){
  directTarget(state,{membership:false});
  const geometry=rectangle(-90.03,-89.97,-.02,.02);
  state.originals[2].geometry=geometry;state.targets[0].base_geometry=geometry;
  state.physical.results[0].support.mapped_land_support=geometry;
  state.measured[0].consumed.geometry=geometry;state.measured[0].selected.geometry=geometry;
  state.proposed.rows=[{y:size/2,runs:[[(size/2-1)/2,(size/2-1)/2+1,2]]}];
}
for(const [name,geometry,kind]of [
  ['vertical upper endpoint',()=>rectangle(-90.01,-90,-.01,.01),'native-intersection-on-cell-centre'],
  ['sloping intersection',()=>({type:'Polygon',coordinates:[[[-90-2**-10,latitudes[size/2]-2**-16],
    [-90+2**-10,latitudes[size/2]+2**-16],[-90-2**-10,latitudes[size/2]+2**-16],
    [-90-2**-10,latitudes[size/2]-2**-16]]]}),'native-intersection-on-cell-centre'],
  ['horizontal lower edge',()=>rectangle(-90.01,-89.99,latitudes[size/2],.01),'horizontal-native-boundary-centres'],
  ['excluded lower vertex',()=>({type:'Polygon',coordinates:[[[-90,latitudes[size/2]],
    [-90.01,.01],[-89.99,.01],[-90,latitudes[size/2]]]]}),'excluded-native-lower-vertex-centre'],
  ['hole boundary',()=>({type:'Polygon',coordinates:[rectangle(-90.02,-89.98,-.02,.02).coordinates[0],
    rectangle(-90,-89.99,-.01,.01).coordinates[0]]}),'native-intersection-on-cell-centre'],
])test('actual constructor rejects exact residual '+name+' contact',()=>{
  const residual=geometry(),x=(size/2-1)/2,y=size/2;
  const scan=nativePolygonIntervals([{index:2,polygons:polygonParts(residual).map(p=>p.map(ring=>ring.flat()))}],
    {size,latitudes,rowStart:y,rowEnd:y+1});
  assert.equal((scan.rows.get(y)??[]).some(span=>span.start<=x&&x<span.end),false);
  assert.ok(scan.ties.some(tie=>tie.kind===kind&&tie.y===y&&(tie.start??tie.x)<=x&&x<(tie.end??tie.x+1)));
  const fixture=constructorFixture(s=>{exactBoundaryTarget(s);withResiduals(s,[['extra_reconstruction',residual]]);});
  assert.throws(()=>fixture.run(),/intersect a physical reconstruction residual/);
});
test('every requested native row block is checked against complete residuals',()=>{
  const fixture=constructorFixture(s=>{
    exactBoundaryTarget(s);const geometry=rectangle(-90.03,-89.97,-20,20);
    s.originals[2].geometry=geometry;s.targets[0].base_geometry=geometry;
    s.physical.results[0].support.mapped_land_support=geometry;
    s.measured[0].consumed.geometry=geometry;s.measured[0].selected.geometry=geometry;
    const y=size/2+5000;s.proposed.rows.push({y,runs:s.proposed.rows[0].runs.map(run=>[...run])});
    withResiduals(s,[['extra_reconstruction',rectangle(-90.01,-89.99,latitudes[y]-.001,latitudes[y]+.001)]]);
  });
  assert.throws(()=>fixture.run(),/intersect a physical reconstruction residual/);
});
test('a residual for another owner does not veto clean requested owner cells',()=>{
  const fixture=constructorFixture(s=>{
    const geometry=s.originals[2].geometry;
    s.targets.push({id:c,pixelIndex:2,source_family:family,base_geometry:geometry,coverage_classes:['mapped_land_support']});
    s.physical.results.push({target:c,issues:[],support:{mapped_land_support:geometry}});
    s.measured.push({target:c,consumed:{geometry},selected:{id:c,geometry}});
    const x=Math.floor(size/2+.05/360*size);s.proposed.rows[0].runs.push([x,x+1,2]);
    withResiduals(s,[['missing_reconstruction',rectangle(-.025,-.015,-.01,.01)]],2);
  });
  assert.equal(fixture.run().ledger_rows.length,2);
});

for(const [name,change,pattern]of [
  ['omitted witness',r=>r.issues=[],/Missing or mismatched complete physical residual witness/],
  ['duplicate witness',r=>r.issues.push(r.issues[0]),/duplicate physical residual issue/],
  ['unknown reason',r=>r.issues[0].reason='container-chain',/Unknown or duplicate physical residual issue/],
  ['unknown issue field',r=>r.issues[0].source=0,/Unknown or duplicate physical residual issue/],
  ['mismatched geometry',r=>r.issues[0].geometry=rectangle(0,1),/mismatched complete physical residual witness/],
  ['omitted operation',r=>delete r.support.missing_reconstruction,/Incomplete physical residual operation roster/],
  ['unknown operation',r=>r.support.foreign=emptyPolygon(),/Incomplete physical residual operation roster/],
  ['omitted hierarchy operation',r=>delete r.support.hierarchy_disagreements['L4-outside-L3'],/Incomplete physical residual operation roster/],
  ['unknown hierarchy operation',r=>r.support.hierarchy_disagreements.foreign=emptyPolygon(),/Incomplete physical residual operation roster/],
  ['empty issued operation',r=>{r.support.extra_reconstruction=emptyPolygon();r.issues[0].geometry=r.support.extra_reconstruction;},/Empty physical residual/],
  ['null operation',r=>{r.support.extra_reconstruction=null;r.issues[0].geometry=null;},/Unsupported original native geometry/],
  ['malformed empty operation',r=>r.support.missing_reconstruction={type:'Polygon',coordinates:[[]]},/Incomplete footprint ring/],
  ['extra empty geometry field',r=>r.support.missing_reconstruction.foreign=true,/Primitive geometry/],
  ['nonpolygon witness',r=>{r.support.extra_reconstruction={type:'LineString',coordinates:[[0,0],[1,1]]};r.issues[0].geometry=r.support.extra_reconstruction;},/Unsupported original native geometry/],
  ['nonempty collection witness',r=>{r.support.extra_reconstruction={type:'GeometryCollection',geometries:[disjointResidual()]};r.issues[0].geometry=r.support.extra_reconstruction;},/Unsupported original native geometry/],
  ['hidden contradiction',r=>r.support.contradictory_land_water_support=rectangle(0,1),/Unresolved contradictory or hierarchy/],
  ['hidden hierarchy disagreement',r=>r.support.hierarchy_disagreements['L2-outside-L1']=rectangle(0,1),/Unresolved contradictory or hierarchy/],
])test('residual constructor rejects '+name+' after coherent evidence rehashing',()=>{
  const fixture=constructorFixture(s=>change(withResiduals(s,[['extra_reconstruction',disjointResidual()]])));
  assert.throws(()=>fixture.run(),pattern);
});
for(const key of ['contradictory_land_water_support','L2-outside-L1'])
  test('deleting every issue cannot hide observed '+key,()=>{
    const fixture=constructorFixture(s=>{
      const result=withResiduals(s,[]);
      if(key==='contradictory_land_water_support')result.support[key]=rectangle(0,1);
      else result.support.hierarchy_disagreements[key]=rectangle(0,1);
    });
    assert.throws(()=>fixture.run(),/Unresolved contradictory or hierarchy/);
  });
test('deleting one of two residual witnesses cannot omit the other operation',()=>{
  const fixture=constructorFixture(s=>{
    const result=withResiduals(s,[['missing_reconstruction',disjointResidual()],['extra_reconstruction',disjointResidual()]]);
    result.issues.pop();
  });
  assert.throws(()=>fixture.run(),/Missing or mismatched complete physical residual witness/);
});
