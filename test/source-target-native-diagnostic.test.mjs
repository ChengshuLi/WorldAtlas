import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {deriveSourceTargetNativeDelta,nativeRowLatitudes,nativePolygonIntervals,polygonParts,witnessCellEffects,validateWitnessGeometry} from '../src/native-grid.js';
import {ImmutableReader} from '../scripts/check-effective-geographic-regression.mjs';
import {qualifySourceTargetNativeAuthority,diagnoseSourceTargetNativeAuthority} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';

const rectangle=(left,right,bottom=-40,top=40)=>({type:'Polygon',coordinates:[[[left,bottom],[right,bottom],[right,top],[left,top],[left,bottom]]]});
const feature=(id,pixelIndex,geometry,target_id)=>({id,pixelIndex,geometry,...(target_id?{target_id}:{})});
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
  const reader=()=>new FixtureReader('.',version,{runtimeBytes:0,metadataBytes:0,outputBytes:16*1024*1024,
    allowance:{phaseBytes:128*1024*1024,rssBytes:1024*1024*1024}});
  const locators={source_evidence:{commit:version,path:evidence.path},native_patch:{commit:version,path:patch.path}};
  const operands={source_evidence:files.get(evidence.path).pin,native_patch:files.get(patch.path).pin};
  const preimage={version:1,kind:'source-target-native-rule-v1',...operands};
  const binding={version:1,kind:'source-target-native-custody-v1',...operands};
  return {run:()=>qualifySourceTargetNativeAuthority(reader(),preimage,binding),
    diagnose:()=>diagnoseSourceTargetNativeAuthority(reader(),preimage,binding),
    preimage,binding,files,byBlob,membership,reader,state};
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
const off={type:'Point',coordinates:[-89.99,latitude]};
function assertPartition(result) {
 const expand=rows=>rows.flatMap(r=>r.runs.flatMap(([a,b,o])=>Array.from({length:b-a},(_,i)=>r.y+':'+(a+i)+':'+o)));
 const requested=expand(result.requested_rows),supported=expand(result.supported_rows),held=expand(result.held_rows);
 assert.equal(new Set([...supported,...held]).size,requested.length);
 assert.deepEqual([...supported,...held].sort(),requested.sort());
 assert.equal(result.supported_cells,supported.length);assert.equal(result.held_cells,held.length);
 assert.equal('source_rows' in result,false);assert.equal('native_proof' in result,false);
}
test('diagnostic preserves default successful qualification and returns only screening data',()=>{
 const f=constructorFixture();assert.equal(f.run().source_rows[0].native_cells,1);
 const d=f.diagnose();assertPartition(d);assert.equal(d.supported_cells,1);assert.equal(d.first_failure,null);
});
for(const mode of ['source','coverage','territory','outside'])test('actual authority diagnostic identifies '+mode+' without relaxing default refusal',()=>{
 const f=constructorFixture(s=>{exactBoundaryTarget(s);const r=conflict(s,'contradictory_land_water_support',off);
  if(mode==='source'){s.originals[2].geometry=rectangle(-89.99,-89.97,-.02,.02);s.measured[0].consumed.geometry=s.originals[2].geometry;}
  if(mode==='coverage')r.support.mapped_land_support=rectangle(-89.99,-89.97,-.02,.02);
  if(mode==='territory')s.targets[0].territorial_exclusions=[rectangle(-90.01,-89.99,-.01,.01)];
  if(mode==='outside')r.support.outside_mapped_L1_context=rectangle(-90.01,-89.99,-.01,.01);
 });
 assert.throws(()=>f.run(),/lack unique source-target coverage|intersect a physical reconstruction residual or conflict witness/);
 const d=f.diagnose();assertPartition(d);assert.equal(d.held_cells,1);
 assert.equal(d.decision_rows[0].runs[0][3],{source:'no-target-source-domain',coverage:'unsupported_coverage_cells',territory:'territorial_exclusion_cells',outside:'physical-reconstruction-residual-or-conflict'}[mode]);
});
test('physical residual has first-predicate precedence over source coverage failure',()=>{
 const f=constructorFixture(s=>{exactBoundaryTarget(s);conflict(s,'contradictory_land_water_support',{type:'Point',coordinates:[-90,latitude]});s.physical.results[0].support.mapped_land_support=rectangle(-89.99,-89.97,-.02,.02);});
 assert.throws(()=>f.run(),/residual or conflict witness/);const d=f.diagnose();assertPartition(d);
 assert.equal(d.first_failure.predicate,'physical-reconstruction-residual-or-conflict');
});
function waterSetup(s){exactBoundaryTarget(s);const r=withResiduals(s,[]);r.support.mapped_inland_water_support=r.support.mapped_land_support;r.support.mapped_land_support=rectangle(-89.99,-89.98,-.02,.02);s.targets[0].coverage_classes=['mapped_land_support','mapped_inland_water_support'];s.targets[0].coverage_rows=[{y,runs:[[x,x+1,'mapped_land_support']]}];}
test('declared physical class cannot borrow another class in diagnostic or qualifier',()=>{
 const f=constructorFixture(waterSetup);assert.throws(()=>f.run(),/declared land\/water/);
 const d=f.diagnose();assertPartition(d);assert.equal(d.decision_rows[0].runs[0][3],'declared-land-water-class-support');
});
test('unknown whole witness/query still aborts diagnostic instead of emitting partial partition',()=>{
 const f=constructorFixture(s=>{exactBoundaryTarget(s);conflict(s,'contradictory_land_water_support',off).query_relations[0].status='unknown';});
 assert.throws(()=>f.diagnose(),/Unknown or missing/);
 const g=constructorFixture();g.binding.native_patch={...g.binding.native_patch,sha256:'0'.repeat(64)};
 assert.throws(()=>g.diagnose(),/inputs differ/);
});
function smallInput(){const a=feature('A',1,rectangle(-89,89));return {targets:[{id:'A',pixelIndex:1}],sourceFeatures:[a],coverageFeatures:[a],
 size:8,latitudes:nativeRowLatitudes(8),rowStart:0,rowEnd:8,ownerRows:Array.from({length:8},(_,y)=>({y,complete_owner_intervals:[]})),diagnosticRows:[{y:3,runs:[[0,8,1]]},{y:4,runs:[[0,8,1]]}]};}
for(const mode of ['source','coverage','overlap','territory','owned','tie'])test('same native scan records nonvacuous '+mode+' decisions and preserves default result',()=>{
 const v=smallInput();if(mode==='source')v.sourceFeatures[0].geometry=rectangle(-89,-1);
 if(mode==='coverage')v.coverageFeatures=[feature('A',1,rectangle(-89,-1))];
 if(mode==='overlap')v.sourceFeatures.push(feature('B',2,rectangle(-1,89)));
 if(mode==='territory')v.territorialExclusions=[feature('A',1,rectangle(-1,89))];
 if(mode==='owned')v.ownerRows[3].complete_owner_intervals=[[2,3,2]];
 if(mode==='tie')v.territorialExclusions=[feature('A',1,rectangle(-67.5,0))];
 const d=deriveSourceTargetNativeDelta(v),plain=deriveSourceTargetNativeDelta({...v,diagnosticRows:undefined});
 const {diagnostic_rows,...same}=d;assert.deepEqual(same,plain);
 const reasons=new Set(diagnostic_rows.flatMap(r=>r.runs.map(run=>run[3])));
 const expected={source:'no-target-source-domain',coverage:'unsupported_coverage_cells',overlap:'ambiguous_owner_cells',territory:'territorial_exclusion_cells',owned:'already_owned_cells',tie:'boundary_cells'}[mode];assert.ok(reasons.has(expected),JSON.stringify(diagnostic_rows));
 assert.equal(diagnostic_rows.reduce((n,r)=>n+r.runs.reduce((m,v)=>m+v[1]-v[0],0),0),16);
});
test('source membership cannot borrow a same-owner sibling coverage geometry',()=>{
 const v=smallInput();v.sourceFeatures=[feature('A',1,rectangle(-89,-1),'city'),feature('B',1,rectangle(1,89),'city')];v.targets=[{id:'city',pixelIndex:1}];v.coverageFeatures=[{...feature('city',1,rectangle(-89,89)),source_id:'A'}];
 const d=deriveSourceTargetNativeDelta(v);assert.ok(d.diagnostic_rows.flatMap(r=>r.runs).some(r=>r[3]==='unsupported_coverage_cells'));
});
test('diagnostic trace requires complete nonoverlapping valid requested owner rows',()=>{
 const v=smallInput();v.diagnosticRows[0].runs.push([1,2,1]);assert.throws(()=>deriveSourceTargetNativeDelta(v),/diagnostic interval/);
});
test('first held run does not skip later requested blocks or another owner',()=>{
 const f=constructorFixture(s=>{
  const left=rectangle(-.03,.03,-10,10),right=rectangle(.04,.07,-10,10);
  s.originals=[rawFeature('A',left),rawFeature('C',right)];s.membership=false;
  s.roster=[{id:a,index:1},{id:c,index:2}];
  s.targets=[{id:a,pixelIndex:1,source_family:family,base_geometry:left,coverage_classes:['mapped_land_support'],territorial_exclusions:[left]},
   {id:c,pixelIndex:2,source_family:family,base_geometry:right,coverage_classes:['mapped_land_support'],territorial_exclusions:[]}];
  s.physical.results=[{target:a,issues:[],support:{mapped_land_support:left}},{target:c,issues:[],support:{mapped_land_support:right}}];
  s.measured=[{target:a,consumed:{geometry:left},selected:{id:a,geometry:left}},{target:c,consumed:{geometry:right},selected:{id:c,geometry:right}}];
  const xx=Math.floor(size/2+.05/360*size),first=Math.floor(size/2-.02/360*size);
  s.proposed.rows=[{y,runs:[[first,first+1,1],[xx,xx+1,2]]},{y:y+5000,runs:[[first,first+1,1],[xx,xx+1,2]]}];
 });
 assert.throws(()=>f.run(),/unique source-target coverage/);const d=f.diagnose();assertPartition(d);
 assert.equal(d.requested_cells,4);assert.equal(d.held_cells,2);assert.equal(d.supported_cells,2);
 assert.equal(d.decision_rows.length,2);assert.equal(d.first_failure.y,y);
});
test('a contiguous request spanning a real veto has exact permitted flanks and held centre',()=>{
 const v=smallInput();v.diagnosticRows=[{y:3,runs:[[2,6,1]]}];
 // Only centre x=3 lies inside this mask; neither edge is a native centre.
 v.territorialExclusions=[feature('A',1,rectangle(-40,-5))];
 const d=deriveSourceTargetNativeDelta(v);
 assert.deepEqual(d.diagnostic_rows,[{y:3,runs:[[2,3,1,'assigned_cells'],[3,4,1,'territorial_exclusion_cells'],[4,6,1,'assigned_cells']]}]);
});
test('diagnostic refuses output and trace budgets rather than returning unaccounted observations',()=>{
 const f=constructorFixture(),r=f.reader();r.outputBytes=1;
 assert.throws(()=>diagnoseSourceTargetNativeAuthority(r,f.preimage,f.binding),/output exceeds allowance/);
 const g=constructorFixture(),tight=g.reader();
 // Immutable inputs still fit, but prospective retained trace must also fit.
 const used=g.reader();qualifySourceTargetNativeAuthority(used,g.preimage,g.binding);
 tight.allowance.phaseBytes=used.used+100;
 assert.throws(()=>diagnoseSourceTargetNativeAuthority(tight,g.preimage,g.binding),/exceeds phase|exceeds allowance/);
});
