import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {gzipSync} from 'node:zlib';
import {deriveSourceTargetNativeDelta,nativeRowLatitudes,nativePolygonIntervals,polygonParts} from '../src/native-grid.js';
import {ImmutableReader} from '../scripts/check-effective-geographic-regression.mjs';
import {constructOriginalAuthority} from '../scripts/delivery-handoff-advance.mjs';
import {diagnoseSourceTargetNativeAuthority,valueSha} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';

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
  const extraSources=(state.extraFamilies??[]).map(f=>({...f,pin:put(f.source_id+'.json',collection(f.features))}));
  const catalogue=put('coordination/engineering/original-geography-source-corpus-20261006/catalogue.json',{
    products:[{key:family,parts:[{path:source.path,bytes:source.bytes,sha256:source.sha256}],
      feature_count:state.originals.length,original_bytes:source.bytes,original_sha256:source.sha256},
      ...extraSources.map(f=>({key:f.source_id,parts:[{path:f.pin.path,bytes:f.pin.bytes,sha256:f.pin.sha256}],
        feature_count:f.features.length,original_bytes:f.pin.bytes,original_sha256:f.pin.sha256}))]});
  const nativeLatitudes=put('latitudes.f64le',latitudeBytes);
  const membership={index:put('data/world-index.json',state.index),lineage:put('data/semantic-report.json',state.lineage),
    parts:[put('data/geography/part-0.json',state.accepted)]};
  if(state.cohort){
    const decoded=Buffer.from(JSON.stringify(state.cohort.rows)),raw=gzipSync(decoded);
    const part={...put('data/macro-foundation/world-review-locations-0.json.gz',raw),
      decoded_bytes:decoded.length,decoded_sha256:digest(decoded)};
    membership.cohort_inventory={index:put('data/macro-foundation/world-review-projection.json',{
      version:1,kind:'current-membership-projection',locations:state.cohort.rows.length,
      current_pins:{location_index_sha256:membership.index.sha256},
      location_parts:['macro-foundation/world-review-locations-0.json.gz'],...state.cohort.index}),parts:[part]};
    state.cohort.mutate?.(membership.cohort_inventory);
  }
  if(state.external){
    const raw=Buffer.from(JSON.stringify(collection(state.external.features)));
    membership.negative_natural_earth={registry:put('data/sources.json',{
      hashes:{ne_10m_admin_1_states_provinces:state.external.registryHash??digest(raw)}}),source:put('whole-ne.json',raw),
      atoms:state.external.atoms??[{source_id:'TST-1',feature_ordinal:0,geometry_sha256:valueSha(state.external.features[0].geometry)}]};
    state.external.mutate?.(membership.negative_natural_earth);
  }
  const evidence=put('source-evidence.json',{version:1,kind:'source-target-native-evidence-v1',catalogue,
    owner_roster:roster,physical_evidence:physical,physical_input:measured,physical_reproduction:put('physical.py',Buffer.from('# retained fixture')),
    native_latitudes:nativeLatitudes,native_contract:{size,native_latitudes:nativeLatitudes,original_assets:{bounds:{sha256:roster.sha256}}},
    base_reference:{id:'fixture-base'},families:[{source_id:family,parts:[source]},...extraSources.map(f=>({source_id:f.source_id,parts:[f.pin]}))],
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
  const reader=()=>new FixtureReader('.',version);
  const locators={source_evidence:{commit:version,path:evidence.path},native_patch:{commit:version,path:patch.path}};
  const binding={version:1,kind:'source-target-native-custody-v1',source_evidence:evidence,native_patch:patch};
  const preimage={...binding,kind:'source-target-native-rule-v1'};
  return {run:()=>constructOriginalAuthority(reader(),locators),
    diagnose:()=>diagnoseSourceTargetNativeAuthority(reader(),preimage,binding),files,byBlob,membership,reader,state};
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


function splitCompetitorFixture(change=()=>{}) {
  return constructorFixture(state=>{
    directTarget(state);
    state.originals[0].geometry=rectangle(.015,.035,-.02,.02);
    state.originals[1].geometry=rectangle(-.06,-.05,-.02,.02);
    state.roster.push({id:b,index:4});
    state.roster[0].province_id='province:left';
    state.roster[2].province_id='province:right';
    const basis='Published geographic subdivision within a source rural district';
    const source='https://example.org/retained-subdivision';
    state.lineage.changes=['city','other-city'].map(id=>({id,replaces:[a],basis,source}));
    state.accepted.features=['city','other-city'].map((id,i)=>({type:'Feature',id,
      geometry:rectangle(.015+i*.01,.025+i*.01,-.02,.02),properties:{id,
        parent_id:i?'province:right':'province:left',metadata:{source_member_ids:[a],
          original_id:'A',location_basis:basis,source_url:source}}}));
    change(state);
  });
}
test('complete split original stays a veto-only competitor across distinct accepted parents',()=>{
  const fixture=splitCompetitorFixture(),proof=fixture.run(),diagnostic=fixture.diagnose();
  assert.equal(proof.ledger_rows.length,1);
  assert.equal(proof.ledger_rows[0].target_id,c);
  assert.equal(proof.ledger_rows[0].native_cells,1);
  assert.deepEqual(proof.split_source_competitors,[{
    source_id:a,geometry_sha256:digest(Buffer.from(JSON.stringify({coordinates:fixture.state.originals[0].geometry.coordinates,
      type:fixture.state.originals[0].geometry.type})+'\n')),
    descendants:[{target_id:'city',pixelIndex:1,parent_id:'province:left'},
      {target_id:'other-city',pixelIndex:3,parent_id:'province:right'}]}]);
  assert.equal(diagnostic.supported_cells,1);
  assert.deepEqual(diagnostic.split_source_competitors,proof.split_source_competitors);
  assert.deepEqual(fixture.state.physical.results.map(row=>row.target),[c]);
});
for(const [name,change,pattern]of [
  ['missing membership',s=>s.membership=false,/accepted source membership/],
  ['omitted semantic descendant',s=>s.lineage.changes.pop(),/split-source descendant inventory/],
  ['omitted canonical descendant',s=>s.accepted.features.pop(),/split-source descendant/],
  ['duplicate semantic descendant',s=>s.lineage.changes.push(s.lineage.changes[0]),/split-source descendant/],
  ['duplicate descendant under foreign source',s=>s.lineage.changes.push({...s.lineage.changes[0],replaces:['gb:TST:ADM2:FOREIGN']}),/split-source descendant/],
  ['duplicate descendant with malformed replacement',s=>s.lineage.changes.push({...s.lineage.changes[0],replaces:'gb:TST:ADM2:FOREIGN'}),/split-source descendant/],
  ['duplicate descendant without replacement',s=>s.lineage.changes.push({id:s.lineage.changes[0].id}),/split-source descendant/],
  ['foreign semantic descendant',s=>s.lineage.changes.push({id:'missing',replaces:[a]}),/split-source descendant/],
  ['ambiguous child source membership',s=>s.accepted.features[0].properties.metadata.source_member_ids.push(b),/split-source descendant/],
  ['wrong original source ID',s=>s.accepted.features[0].properties.metadata.original_id='B',/split-source descendant/],
  ['wrong canonical identity',s=>s.accepted.features[0].properties.id='elsewhere',/split-source descendant/],
  ['wrong canonical parent',s=>s.accepted.features[0].properties.parent_id='other-province',/parent or source identity/],
  ['missing native parent',s=>delete s.roster[0].province_id,/parent or source identity/],
  ['wrong subdivision basis',s=>s.accepted.features[0].properties.metadata.location_basis='other basis',/parent or source identity/],
  ['wrong subdivision source',s=>s.accepted.features[0].properties.metadata.source_url='https://other.example/',/parent or source identity/],
  ['split source requested positively',s=>{
    const geometry=s.originals[0].geometry;
    s.targets=[{id:a,target_id:'city',pixelIndex:1,source_family:family,base_geometry:geometry,
      coverage_classes:['mapped_land_support']}];
    s.measured=[{target:a,consumed:{geometry},selected:{id:'city',geometry}}];
    s.physical.results=[{target:a,issues:[],support:{mapped_land_support:geometry}}];
    s.proposed.rows[0].runs[0][2]=1;
  },/ambiguous accepted source membership/],
])test('split source rejects '+name+' after coherent body rehashing',()=>{
  const fixture=splitCompetitorFixture(change);
  assert.throws(()=>fixture.run(),pattern);
  assert.throws(()=>fixture.diagnose(),pattern);
});
for(const [name,geometry,reason]of [
  ['interior',()=>rectangle(.04,.06,-.02,.02),'territorial_exclusion_cells'],
  ['boundary',()=>rectangle(.04,.06,latitudes[size/2],.02),'boundary_cells'],
])test('whole split original '+name+' contact vetoes outside all child geometries',()=>{
  const fixture=splitCompetitorFixture(state=>{
    const x=state.proposed.rows[0].runs[0][0];
    state.originals[0].geometry=geometry((x+.5)/size*360-180);
  });
  assert.throws(()=>fixture.run(),/lack unique source-target coverage/);
  const result=fixture.diagnose();
  assert.equal(result.supported_cells,0);
  assert.equal(result.held_cells,1);
  assert.equal(result.decision_rows[0].runs[0][3],reason);
});

function complexCompetitorFixture(change=()=>{},transitive=false){
 return constructorFixture(state=>{
  directTarget(state);
  state.originals[0].geometry=rectangle(.015,.035,-.02,.02);
  state.originals[1].geometry=rectangle(.018,.038,-.02,.02);
  const source='https://example.org/complete-physical-source',basis='Original source intersection witnesses';
  state.roster[0].province_id='province:left';state.roster[2].province_id='province:right';
  state.lineage.changes=[{id:'city',replaces:transitive?['retired-region']:[a,b],basis,source},
   {id:'other-city',replaces:[a,b],basis,source}];
  if(transitive)state.lineage.changes.push({id:'retired-region',replaces:[a,b],basis:'Retained intermediate',source});
  state.accepted.features=['city','other-city'].map((id,i)=>({type:'Feature',id,
   geometry:rectangle(-.06+i*.005,-.055+i*.005,-.02,.02),properties:{id,
    parent_id:i?'province:right':'province:left',reference_owner:'Test cohort',metadata:{source_member_ids:i?[a,b]:transitive?['retired-region']:[a,b],
     location_basis:basis,source_url:source}}}));
  state.accepted.features.push({type:'Feature',id:c,geometry:state.originals[2].geometry,
   properties:{id:c,reference_owner:'Test cohort',metadata:{}}});
  state.cohort={rows:state.accepted.features.map(feature=>({id:feature.id,owner:feature.properties.reference_owner}))};
  change(state);
 });
}
for(const transitive of [false,true])test('complete '+(transitive?'transitive':'many-member')+' ancestry supplies only whole-original negative vetoes',()=>{
 const f=complexCompetitorFixture(()=>{},transitive),result=f.run(),diagnostic=f.diagnose();
 assert.equal(result.ledger_rows.length,1);assert.equal(result.ledger_rows[0].target_id,c);
 assert.equal(result.ledger_rows[0].native_cells,1);
 assert.deepEqual(result.split_source_competitors.map(x=>[x.source_id,x.descendants]),[a,b].map(id=>[id,
  [{target_id:'city',pixelIndex:1,parent_id:'province:left'},{target_id:'other-city',pixelIndex:3,parent_id:'province:right'}]]));
 assert.deepEqual(diagnostic.split_source_competitors,result.split_source_competitors);
 assert.deepEqual(f.state.physical.results.map(x=>x.target),[c]);
 assert.equal(diagnostic.supported_cells,1);assert.equal(diagnostic.held_cells,0);
});
test('one descendant with shared complete source atoms remains a negative rather than an inferred positive owner',()=>{
 const f=complexCompetitorFixture(s=>{
  s.lineage.changes[1].replaces=[b];s.accepted.features[1].properties.metadata.source_member_ids=[b];
 });
 const result=f.run();assert.equal(result.split_source_competitors.find(x=>x.source_id===a).descendants.length,1);
 assert.equal(result.ledger_rows[0].target_id,c);
});
for(const [name,change,pattern]of [
 ['missing intermediary',s=>s.lineage.changes.pop(),/complex|split-source|source membership/],
 ['removed terminal semantic change',s=>s.lineage.changes.splice(0,1),/complex/],
 ['unresolved same-cohort foreign member',s=>{
  const f=structuredClone(s.accepted.features[1]);f.id='foreign-current';f.properties.id='foreign-current';
  f.properties.metadata.source_member_ids=['unresolved-foreign'];
  s.roster.push({id:'foreign-current',index:4,province_id:'province:right'});s.accepted.features.push(f);
  s.cohort.rows.push({id:f.id,owner:'Test cohort'});
  s.lineage.changes.push({id:'foreign-current',replaces:['unresolved-foreign'],basis:f.properties.metadata.location_basis,source:f.properties.metadata.source_url});
 },/complex/],
 ['duplicate intermediate identity',s=>s.lineage.changes.push({...s.lineage.changes[2]}),/complex/],
 ['duplicate intermediate edge',s=>s.lineage.changes[2].replaces.push(a),/complex/],
 ['cycle through retired intermediates',s=>{
  s.lineage.changes[2].replaces.push('cycle-node');
  s.lineage.changes.push({id:'cycle-node',replaces:['retired-region'],basis:'Cycle',source:s.lineage.changes[2].source});
 },/Cyclic|complex/],
 ['foreign complete-family leaf',s=>s.lineage.changes[2].replaces.push('gb:OTHER:ADM2:UNKNOWN'),/complex/],
 ['omitted original sibling',s=>s.originals.splice(1,1),/complex/],
 ['removed current descendant',s=>s.accepted.features.splice(1,1),/complex/],
 ['extra current canonical descendant',s=>{
  const f=structuredClone(s.accepted.features[1]);f.id='extra-city';f.properties.id='extra-city';
  s.roster.push({id:'extra-city',index:4,province_id:'province:right'});s.accepted.features.push(f);
  s.cohort.rows.push({id:f.id,owner:'Test cohort'});
 },/canonical descendant inventory|complex/],
 ['canonical omitted full member',s=>s.accepted.features[1].properties.metadata.source_member_ids.pop(),/canonical member inventory/],
 ['canonical duplicate member',s=>s.accepted.features[1].properties.metadata.source_member_ids.push(a),/canonical member inventory/],
 ['canonical changed member',s=>s.accepted.features[1].properties.metadata.source_member_ids[1]='gb:FOREIGN:ADM2:X',/canonical member inventory/],
 ['duplicate terminal semantic identity',s=>s.lineage.changes.push({...s.lineage.changes[0],replaces:['foreign']}),/complex/],
 ['wrong canonical ID',s=>s.accepted.features[0].properties.id='foreign',/canonical member inventory/],
 ['wrong canonical parent',s=>s.accepted.features[0].properties.parent_id='foreign-parent',/parent or source identity/],
 ['wrong original owner parent',s=>s.roster[0].province_id='foreign-parent',/parent or source identity/],
 ['missing original owner parent',s=>delete s.roster[0].province_id,/parent or source identity/],
 ['wrong terminal source',s=>s.accepted.features[0].properties.metadata.source_url='https://different.example/',/parent or source identity/],
 ['wrong terminal basis',s=>s.accepted.features[0].properties.metadata.location_basis='Different claim',/parent or source identity/],
 ['wrong intermediate source',s=>s.lineage.changes[2].source='https://different.example/',/intermediate provenance/],
 ['false original shape identity',s=>s.accepted.features[0].properties.metadata.original_id='A',/original identity/],
 ['empty semantic members',s=>s.lineage.changes[2].replaces=[],/complex|source membership|split-source/],
 ['phantom current terminal',s=>{
  s.roster[0].id='unrelated-current';s.accepted.features=s.accepted.features.filter(f=>f.id!=='city');
 },/complex|cohort/],
])test('complex negative rejects '+name+' through constructor and diagnostic after coherent repinning',()=>{
 const f=complexCompetitorFixture(change,true);assert.throws(()=>f.run(),pattern);assert.throws(()=>f.diagnose(),pattern);
});
for(const transitive of [false,true])test('complex '+(transitive?'transitive':'many-member')+' membership cannot become positive coverage',()=>{
 const f=complexCompetitorFixture(s=>{
  const geometry=s.originals[0].geometry,selected=s.accepted.features[0].geometry;
  s.targets=[{id:a,target_id:'city',pixelIndex:1,source_family:family,base_geometry:selected,coverage_classes:['mapped_land_support']}];
  s.measured=[{target:a,consumed:{geometry},selected:{id:'city',geometry:selected}}];
  s.physical.results=[{target:a,issues:[],support:{mapped_land_support:geometry}}];s.proposed.rows[0].runs[0][2]=1;
 },transitive);
 assert.throws(()=>f.run(),/ambiguous accepted source membership/);assert.throws(()=>f.diagnose(),/ambiguous accepted source membership/);
});
for(const [name,geometry,reason]of [
 ['interior',()=>rectangle(.04,.06,-.02,.02),'territorial_exclusion_cells'],
 ['boundary',()=>rectangle(.04,.06,latitudes[size/2],.02),'boundary_cells'],
])test('complete complex original '+name+' contact vetoes outside all descendant geometries',()=>{
 const f=complexCompetitorFixture(s=>{s.originals[0].geometry=geometry();},true);
 assert.throws(()=>f.run(),/lack unique source-target coverage/);
 const result=f.diagnose();assert.equal(result.supported_cells,0);assert.equal(result.held_cells,1);
 assert.equal(result.decision_rows[0].runs[0][3],reason);
});

test('direct original-to-canonical joins preserve complete cohort checking without a positive seed record',()=>{
 const f=complexCompetitorFixture(s=>{
  s.accepted.features=s.accepted.features.filter(feature=>feature.id!==c);s.lineage.changes.pop();
 },true);
 assert.throws(()=>f.run(),/complex/);assert.throws(()=>f.diagnose(),/complex/);
});

for(const [name,change]of [
 ['missing complete cohort role',s=>delete s.cohort],
 ['missing metadata partition',s=>s.cohort.mutate=role=>role.parts=[]],
 ['duplicate metadata partition',s=>s.cohort.mutate=role=>role.parts.push(role.parts[0])],
 ['wrong fixed projection path',s=>s.cohort.mutate=role=>role.index.path='data/world-review.json'],
 ['stale world-index join',s=>s.cohort.index={current_pins:{location_index_sha256:'f'.repeat(64)}}],
 ['wrong complete location count',s=>s.cohort.index={locations:4}],
 ['unlisted metadata partition',s=>s.cohort.index={location_parts:['macro-foundation/missing.json.gz']}],
 ['duplicate complete owner identity',s=>s.cohort.rows.push(s.cohort.rows[0])],
 ['missing complete native owner',s=>s.cohort.rows.pop()],
 ['foreign complete native owner',s=>s.cohort.rows[0].id='foreign'],
 ['cohort label differs',s=>s.cohort.rows[0].owner='Foreign cohort'],
 ['missing decoded metadata identity',s=>s.cohort.mutate=role=>delete role.parts[0].decoded_sha256],
 ['wrong decoded metadata identity',s=>s.cohort.mutate=role=>role.parts[0].decoded_sha256='0'.repeat(64)],
 ['wrong encoded metadata identity',s=>s.cohort.mutate=role=>role.parts[0].sha256='0'.repeat(64)],
 ['coordinated removed canonical descendant and semantic edge',s=>{
   s.accepted.features.splice(1,1);s.lineage.changes.splice(1,1);
 }],
])test('complex negative requires '+name+' to fail closed',()=>{
 const f=complexCompetitorFixture(change,true);
 assert.throws(()=>f.run(),/cohort|projection|bytes|body|immutable input/);assert.throws(()=>f.diagnose(),/cohort|projection|bytes|body|immutable input/);
});

function externalCompetitorFixture(change=()=>{}){
 return complexCompetitorFixture(s=>{
  s.external={features:[{type:'Feature',properties:{adm1_code:'TST-1',name:'Same display name'},geometry:rectangle(.02,.03,-.02,.02)},
   {type:'Feature',properties:{adm1_code:'TST-2',name:'Same display name'},geometry:rectangle(1,2,1,2)}]};
  s.lineage.changes[2].replaces.push('TST-1');change(s);
 },true);
}
test('complete external Natural Earth atom joins only negative ancestry with whole original geometry',()=>{
 const f=externalCompetitorFixture(),proof=f.run(),diagnostic=f.diagnose();
 assert.equal(proof.ledger_rows[0].target_id,c);assert.equal(proof.ledger_rows[0].native_cells,1);
 const external=proof.split_source_competitors.find(x=>x.source_id==='TST-1');
 assert.deepEqual(external,{source_id:'TST-1',geometry_sha256:valueSha(f.state.external.features[0].geometry),
  descendants:[{target_id:'city',pixelIndex:1,parent_id:'province:left'}],source_family:'natural-earth:adm1',feature_ordinal:0});
 assert.deepEqual(diagnostic.split_source_competitors,proof.split_source_competitors);
});
for(const [name,geometry,reason]of [
 ['interior',()=>rectangle(.04,.06,-.02,.02),'territorial_exclusion_cells'],
 ['boundary',()=>rectangle(.04,.06,latitudes[size/2],.02),'boundary_cells'],
])test('complete external original '+name+' remains a native veto outside every descendant',()=>{
 const f=externalCompetitorFixture(s=>s.external.features[0].geometry=geometry());
 assert.throws(()=>f.run(),/lack unique source-target coverage/);
 const d=f.diagnose();assert.equal(d.supported_cells,0);assert.equal(d.held_cells,1);
 assert.equal(d.decision_rows[0].runs[0][3],reason);
});
for(const [name,change,pattern]of [
 ['missing explicit bridge',s=>delete s.external,/complex/],
 ['empty atoms',s=>s.external.atoms=[],/Natural Earth source role/],
 ['duplicate atom',s=>s.external.mutate=r=>r.atoms.push(r.atoms[0]),/duplicate negative/],
 ['wrong native identity',s=>s.external.mutate=r=>r.atoms[0].source_id='natural-earth:adm1:TST-1',/original identity/],
 ['same-name distinct identity',s=>s.external.mutate=r=>r.atoms[0].source_id='TST-2',/original identity/],
 ['wrong ordinal',s=>s.external.mutate=r=>r.atoms[0].feature_ordinal=1,/original identity/],
 ['wrong geometry hash',s=>s.external.mutate=r=>r.atoms[0].geometry_sha256='0'.repeat(64),/original identity/],
 ['missing ordinal',s=>s.external.mutate=r=>delete r.atoms[0].feature_ordinal,/negative Natural Earth atom/],
 ['foreign role key',s=>s.external.mutate=r=>r.guessed_owner='city',/Natural Earth source role/],
 ['wrong registry path',s=>s.external.mutate=r=>r.registry.path='foreign-registry.json',/Natural Earth source role/],
 ['corrupt whole source hash',s=>s.external.mutate=r=>r.source.sha256='0'.repeat(64),/hash differs|bytes differ|immutable input differs/],
 ['corrupt registry hash',s=>s.external.mutate=r=>r.registry.sha256='0'.repeat(64),/hash differs|bytes differ|immutable input differs/],
 ['complete source differs from selected registry',s=>s.external.registryHash='0'.repeat(64),/whole source differs/],
 ['external leaf shadows an accepted intermediary',s=>s.lineage.changes.push({id:'TST-1',replaces:[b],source:'retained',basis:'retained'}),/shadows/],
 ['duplicate unbound original',s=>s.external.features.push(s.external.features[1]),/duplicate negative Natural Earth native identity/],
 ['missing unbound original identity',s=>delete s.external.features[1].properties.adm1_code,/native identity/],
 ['invalid unbound whole geometry',s=>s.external.features[1].geometry.coordinates[0][0][0]=200,/coordinate/],
 ['unclosed unbound whole ring',s=>s.external.features[1].geometry.coordinates[0].pop(),/ring/],
 ['foreign unbound leaf',s=>s.lineage.changes[2].replaces.push('TST-2'),/complex/],
 ['unused atom',s=>s.lineage.changes[2].replaces.pop(),/Unused negative/],
 ['missing external semantic edge',s=>s.lineage.changes[2].replaces=['TST-2'],/complex/],
 ['omitted complete canonical member',s=>s.accepted.features[0].properties.metadata.source_member_ids=[],/canonical member/],
 ['removed current descendant',s=>s.accepted.features.splice(0,1),/cohort/],
 ['external original as current owner',s=>s.roster.push({id:'TST-1',index:4}),/positive native owner/],
 ['external original as positive source',s=>s.targets[0].id='TST-1',/positive native owner/],
])test('negative external source rejects '+name+' through real constructor and diagnostic',()=>{
 const f=externalCompetitorFixture(change);assert.throws(()=>f.run(),pattern);assert.throws(()=>f.diagnose(),pattern);
});
test('explicit external original never grants positive mixed-source ownership',()=>{
 const f=externalCompetitorFixture(s=>{
  s.lineage.changes[0].replaces=[a,'TST-1'];s.accepted.features[0].properties.metadata.source_member_ids=[a,'TST-1'];
  s.lineage.changes[1].replaces=[b];s.accepted.features[1].properties.metadata.source_member_ids=[b];
  s.lineage.changes.pop();
  const geometry=s.originals[0].geometry,base=s.accepted.features[0].geometry;
  s.targets=[{id:a,target_id:'city',pixelIndex:1,source_family:family,base_geometry:base,coverage_classes:['mapped_land_support']}];
  s.measured=[{target:a,consumed:{geometry},selected:{id:'city',geometry:base}}];
  s.physical.results=[{target:a,issues:[],support:{mapped_land_support:geometry}}];s.proposed.rows[0].runs[0][2]=1;
 });
 assert.throws(()=>f.run(),/Missing or conflicting complete source aggregation member/);
 assert.throws(()=>f.diagnose(),/Missing or conflicting complete source aggregation member/);
});

test('external registry must match the actual selected immutable body',()=>{
 const f=externalCompetitorFixture(),entry=f.files.get('data/sources.json'),raw=Buffer.from('{"hashes":{}}');
 f.byBlob.set(blob(raw),raw);f.files.set('data/sources.json',{raw,pin:{...entry.pin,git_blob_oid:blob(raw),bytes:raw.length}});
 assert.throws(()=>f.run(),/selected canonical bytes/);assert.throws(()=>f.diagnose(),/selected canonical bytes/);
});

test('authenticated external whole original veto also covers targets in another source family',()=>{
 const f=externalCompetitorFixture(s=>{
  const secondFamily='gb:OTHER:ADM2',id=secondFamily+':D',geometry=rectangle(.04,.06,-.02,.02),y=size/2+1;
  s.extraFamilies=[{source_id:secondFamily,features:[rawFeature('D',geometry)]}];
  s.roster.push({id,index:4});s.accepted.features.push({type:'Feature',id,geometry,
   properties:{id,reference_owner:'Other cohort',metadata:{}}});s.cohort.rows.push({id,owner:'Other cohort'});
  s.targets.push({id,pixelIndex:4,source_family:secondFamily,base_geometry:geometry,coverage_classes:['mapped_land_support']});
  s.measured.push({target:id,consumed:{geometry},selected:{id,geometry}});
  s.physical.results.push({target:id,issues:[],support:{mapped_land_support:geometry}});
  s.proposed.rows.push({y,runs:[[...s.proposed.rows[0].runs[0].slice(0,2),4]]});
  s.external.features[0].geometry=rectangle(.04,.06,latitudes[y]-.0001,latitudes[y]+.0001);
 });
 assert.throws(()=>f.run(),/lack unique source-target coverage/);
 const d=f.diagnose();assert.equal(d.supported_cells,1);assert.equal(d.held_cells,1);
 assert.deepEqual(d.decision_rows.map(row=>row.runs[0].slice(2)),[[2,'assigned_cells'],[4,'territorial_exclusion_cells']]);
});
