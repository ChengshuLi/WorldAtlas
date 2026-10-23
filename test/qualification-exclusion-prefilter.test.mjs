import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import path from 'node:path';
import {pathToFileURL} from 'node:url';

const moduleUrl=(root,name)=>root?pathToFileURL(path.resolve(root,name)):new URL('../'+name,import.meta.url);
async function load(root){
 const [reader,flow,native,policy]=await Promise.all([
  import(moduleUrl(root,'scripts/check-effective-geographic-regression.mjs')),
  import(moduleUrl(root,'scripts/delivery-handoff-advance.mjs')),
  import(moduleUrl(root,'src/native-grid.js')),
  import(moduleUrl(root,'coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs'))]);
 return {ImmutableReader:reader.ImmutableReader,constructOriginalAuthority:flow.constructOriginalAuthority,
  nativeRowLatitudes:native.nativeRowLatitudes,diagnose:policy.diagnoseSourceTargetNativeAuthority};
}
const engine=await load(process.env.QUALIFICATION_TEST_ROOT);
// Optional task-local differential: ordinary checkout tests require no old tree.
const reference=process.env.OLD_QUALIFICATION_TEST_ROOT?await load(process.env.OLD_QUALIFICATION_TEST_ROOT):null;
const {nativeRowLatitudes}=engine;
// Existing native-witness-authority fixture: complete tiny original/member,
// physical, class and custody bodies; only Git responses are in memory.
const rectangle=(left,right,bottom=-40,top=40)=>({type:'Polygon',coordinates:[[[left,bottom],[right,bottom],[right,top],[left,top],[left,bottom]]]});
const feature=(id,pixelIndex,geometry,target_id)=>({id,pixelIndex,geometry,...(target_id?{target_id}:{})});
const version='a'.repeat(40),family='gb:TST:ADM2',a=family+':A',b=family+':B',c=family+':C';
const size=262166,latitudes=nativeRowLatitudes(size),latitudeBytes=Buffer.alloc(size*8);
for(let i=0;i<size;i++)latitudeBytes.writeDoubleLE(latitudes[i],i*8);
const digest=raw=>createHash('sha256').update(raw).digest('hex');
const blob=raw=>createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex');
const collection=features=>({type:'FeatureCollection',features});
const rawFeature=(id,geometry)=>({type:'Feature',properties:{shapeID:id},geometry});
function constructorFixture(change=()=>{},implementation=engine){
  const first=rectangle(-.03,.006,-.02,.02),second=rectangle(.004,.03,-.02,.02);
  const cityGeometry={type:'MultiPolygon',coordinates:[first.coordinates,second.coordinates]};
  const direct=rectangle(.015,.06,-.02,.02);
  const state={originals:[rawFeature('A',first),rawFeature('B',second),rawFeature('C',direct)],
    roster:[{id:'city',index:1},{id:c,index:2},{id:'other-city',index:3}],
    lineage:{changes:[{id:'city',replaces:[a,b]},{id:'irrelevant-split-1',replaces:['unrelated']},{id:'irrelevant-split-2',replaces:['unrelated']}]},
    index:{parts:['geography/part-0.json']},
    accepted:collection([{type:'Feature',id:'city',geometry:cityGeometry,properties:{metadata:{source_member_ids:[a,b]}}}]),
    targets:[{id:a,target_id:'city',pixelIndex:1,source_family:family,base_geometry:cityGeometry,coverage_classes:['mapped_land_support'],territorial_exclusions:[]},
      {id:b,target_id:'city',pixelIndex:1,source_family:family,base_geometry:cityGeometry,coverage_classes:['mapped_land_support'],territorial_exclusions:[]}],
    physical:{results:[{target:a,issues:[],support:{mapped_land_support:first}},{target:b,issues:[],support:{mapped_land_support:second}}]},
    measured:[{target:a,consumed:{geometry:first},selected:{id:'city',geometry:cityGeometry}},
      {target:b,consumed:{geometry:second},selected:{id:'city',geometry:cityGeometry}}],
    proposed:{rows:[{y:size/2,runs:[[Math.floor(size/2-.02/360*size),Math.floor(size/2-.02/360*size)+1,1]]}]},
    membership:true};
  change(state);
  const files=new Map(),byBlob=new Map();
  const put=(name,value)=>{
    let raw=Buffer.isBuffer(value)?value:Buffer.from(JSON.stringify(value));
    if(name==='source-evidence.json'&&state.rawEvidence)raw=state.rawEvidence(raw);
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
  class FixtureReader extends implementation.ImmutableReader{
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
  const runDiagnostic=()=>{
    const binding={version:1,kind:'source-target-native-custody-v1',source_evidence:evidence,native_patch:patch};
    return implementation.diagnose(reader(),{...binding,kind:'source-target-native-rule-v1'},binding);
  };
  return {run:()=>implementation.constructOriginalAuthority(reader(),locators),runDiagnostic,files,byBlob,membership,reader,state};
}
function directTarget(state,{membership=true,overlap=false}={}){
  const geometry=state.originals[2].geometry;
  state.targets=[{id:c,pixelIndex:2,source_family:family,base_geometry:geometry,coverage_classes:['mapped_land_support'],territorial_exclusions:[]}];
  state.physical.results=[{target:c,issues:[],support:{mapped_land_support:geometry}}];
  state.measured=[{target:c,consumed:{geometry},selected:{id:c,geometry}}];
  const x=Math.floor(size/2+(overlap?.02:.05)/360*size);
  state.proposed.rows=[{y:size/2,runs:[[x,x+1,2]]}];state.membership=membership;
  if(!membership)state.originals[2].geometry=rectangle(.04,.06,-.02,.02);
}
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
function exactBoundaryTarget(state){
  directTarget(state,{membership:false});
  const geometry=rectangle(-90.03,-89.97,-.02,.02);
  state.originals[2].geometry=geometry;state.targets[0].base_geometry=geometry;
  state.physical.results[0].support.mapped_land_support=geometry;
  state.measured[0].consumed.geometry=geometry;state.measured[0].selected.geometry=geometry;
  state.proposed.rows=[{y:size/2,runs:[[(size/2-1)/2,(size/2-1)/2+1,2]]}];
}
const y=size/2,x=(size/2-1)/2,latitude=latitudes[y];
function query(r){r.source_id_queries=[7];r.query_relations=[{source_id:7,periodic_offset:0,status:'checked',source_covers_candidate:true,candidate_covers_source:false,intersects:true,disjoint:false,witness:'complete-candidate-reconstruction'}];return r;}
function conflict(s,reason,g,member=0){const r=withResiduals(s,[],member);if(reason.startsWith('L'))r.support.hierarchy_disagreements[reason]=g;else r.support[reason]=g;r.issues=[{reason,geometry:g}];return query(r);}

// Authority equality is the criterion. The old unfiltered kernel can report
// different counts outside every reviewed coverage part without authorizing it.
function compareQualification(change,failure=null,expectedCells=1){
 const current=constructorFixture(change),before=new Map([...current.files].map(([k,v])=>[k,Buffer.from(v.raw)]));
 let actual;
 if(failure)assert.throws(()=>current.run(),failure);
 else {actual=current.run();assert.equal(actual.ledger_rows.reduce((n,r)=>n+r.native_cells,0),expectedCells);}
 if(reference){
  const prior=constructorFixture(change,reference);
  if(failure)assert.throws(()=>prior.run(),failure);
  else assert.deepEqual(actual,prior.run(),'actual old and new complete authority outputs agree');
 }
 for(const [name,raw]of before)assert.deepEqual(current.files.get(name).raw,raw,'whole input bytes remain untouched');
 return current;
}
const excluded=s=>s.targets[0].territorial_exclusions;
const outside=s=>{
 exactBoundaryTarget(s);s.proposed.rows[0].runs=[[x+100,x+101,2]];
 s.targets[0].territorial_exclusions=[rectangle(-89.87,-89.85,-.01,.01)];
};
const missingCoverage=/lack unique source-target coverage/;

test('a complete remote exclusion preserves the exact actual qualified authority',()=>{
 compareQualification(s=>{exactBoundaryTarget(s);s.targets[0].territorial_exclusions=[rectangle(10,11,50,51)];});
});
test('outside every reviewed coverage part but inside a remote exclusion remains refused',()=>{
 compareQualification(outside,missingCoverage);
});
test('an intersecting complete exclusion vetoes otherwise clean positive coverage',()=>{
 compareQualification(s=>{exactBoundaryTarget(s);s.targets[0].territorial_exclusions=[rectangle(-90.01,-89.99,-.01,.01)];},missingCoverage);
});
test('touching coverage and exclusion bounds retain the shared native-boundary refusal',()=>{
 compareQualification(s=>{exactBoundaryTarget(s);
  s.physical.results[0].support.mapped_land_support=rectangle(-90.03,-90,-.02,.02);
  s.targets[0].territorial_exclusions=[rectangle(-90,-89.99,-.01,.01)];
 },missingCoverage);
});
test('every exclusion MultiPolygon part participates when a later part contacts the centre',()=>{
 compareQualification(s=>{exactBoundaryTarget(s);s.targets[0].territorial_exclusions=[{type:'MultiPolygon',coordinates:[
  rectangle(10,11,50,51).coordinates,rectangle(-90.01,-89.99,-.01,.01).coordinates]}];
 },missingCoverage);
});
test('every reviewed coverage part participates when a later part carries the excluded centre',()=>{
 compareQualification(s=>{exactBoundaryTarget(s);
  const geometry={type:'MultiPolygon',coordinates:[rectangle(10,11,-.02,.02).coordinates,s.targets[0].base_geometry.coordinates]};
  s.originals[2].geometry=geometry;s.targets[0].base_geometry=geometry;
  s.physical.results[0].support.mapped_land_support=geometry;
  s.measured[0].consumed.geometry=geometry;s.measured[0].selected.geometry=geometry;
  s.targets[0].territorial_exclusions=[rectangle(-90.01,-89.99,-.01,.01)];
 },missingCoverage);
});
test('a conservative exclusion shell bound cannot turn its actual hole into a veto',()=>{
 compareQualification(s=>{exactBoundaryTarget(s);s.targets[0].territorial_exclusions=[{type:'Polygon',coordinates:[
  rectangle(-90.02,-89.98,-.015,.015).coordinates[0],rectangle(-90.005,-89.995,-.005,.005).coordinates[0]]}];});
});
test('a seam-spanning original exclusion retains the unchanged original polygon veto',()=>{
 compareQualification(s=>{exactBoundaryTarget(s);s.targets[0].territorial_exclusions=[{type:'Polygon',coordinates:[
  [[170,-10],[-170,-10],[-170,10],[170,10],[170,-10]]]}];
 },missingCoverage);
});
test('an exclusion owned by another selected target retains its global boundary tie',()=>{
 const setup=s=>{
  const geometry=rectangle(-90.03,-89.97,-.02,.02);s.originals[2].geometry=geometry;
  s.targets.push({id:c,pixelIndex:2,source_family:family,base_geometry:geometry,
   coverage_classes:['mapped_land_support'],territorial_exclusions:[]});
  s.physical.results.push({target:c,issues:[],support:{mapped_land_support:geometry}});
  s.measured.push({target:c,consumed:{geometry},selected:{id:c,geometry}});
  const cityX=Math.floor(size/2-.02/360*size);
  s.proposed.rows=[{y,runs:[[x,x+1,2],[cityX,cityX+1,1]]}];
 };
 compareQualification(setup,null,2);
 compareQualification(s=>{setup(s);s.targets[0].territorial_exclusions=[rectangle(-90.01,-90,-.01,.01)];},missingCoverage);
});
test('same-owner second original member cannot lose its exclusion through first-member bounds',()=>{
 compareQualification(s=>{
  s.originals[2].geometry=rectangle(.04,.06,-.02,.02);
  const xx=Math.floor(size/2+.02/360*size);s.proposed.rows=[{y,runs:[[xx,xx+1,1]]}];
  s.targets[1].territorial_exclusions=[rectangle(.019,.021,-.01,.01)];
 },missingCoverage);
});
function mixed(s){
 exactBoundaryTarget(s);const r=withResiduals(s,[]);
 r.support.mapped_inland_water_support=r.support.mapped_land_support;
 r.support.mapped_land_support=rectangle(-89.99,-89.98,-.02,.02);
 s.targets[0].coverage_classes=['mapped_land_support','mapped_inland_water_support'];
 s.targets[0].coverage_rows=[{y,runs:[[x,x+1,'mapped_inland_water_support']]}];
 s.targets[0].territorial_exclusions=[rectangle(10,11,50,51)];
}
test('mixed original land/water classes preserve the actual correct water authority',()=>compareQualification(mixed));
test('a remote exclusion cannot make a wrong declared class borrow water support',()=>{
 compareQualification(s=>{mixed(s);s.targets[0].coverage_rows[0].runs[0][2]='mapped_land_support';},/lack declared land\/water class support/);
});
test('a complete exclusion intersecting only water support remains a veto',()=>{
 compareQualification(s=>{mixed(s);s.targets[0].territorial_exclusions=[rectangle(-90.01,-89.99,-.01,.01)];},missingCoverage);
});
test('a malformed disjoint ring is rejected despite providing no useful coverage contact',()=>{
 compareQualification(s=>{exactBoundaryTarget(s);const g=rectangle(10,11,50,51);g.coordinates[0].pop();s.targets[0].territorial_exclusions=[g];},/ring|Ring/);
});
test('a disjoint primitive with an extra own field retains input refusal',()=>{
 compareQualification(s=>{exactBoundaryTarget(s);s.targets[0].territorial_exclusions=[{...rectangle(10,11,50,51),foreign:true}];},/primitive|Primitive/);
});
test('literal negative-zero closure retains the old accepted numeric closure semantics',()=>{
 compareQualification(s=>{exactBoundaryTarget(s);s.targets[0].territorial_exclusions=[rectangle(0,1,60,61)];
  s.rawEvidence=raw=>{
   const text=raw.toString(),needle='"coordinates":[[[0,60],[1,60],[1,61],[0,61],[0,60]]]';
   assert.equal(text.split(needle).length,2,'bind exactly the intended complete exclusion literal');
   return Buffer.from(text.replace(needle,'"coordinates":[[[-0,60],[1,60],[1,61],[0,61],[0,60]]]'));
  };
 });
});
test('diagnostic output remains identical for requested points outside coverage inside an exclusion',()=>{
 const current=constructorFixture(outside).runDiagnostic();
 assert.equal(current.requested_cells,1);assert.equal(current.held_cells,1);
 if(reference)assert.deepEqual(current,constructorFixture(outside,reference).runDiagnostic());
});
