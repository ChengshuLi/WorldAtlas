import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {deriveSourceTargetNativeDelta,nativeRowLatitudes,nativePolygonIntervals,polygonParts,witnessCellEffects,validateWitnessGeometry} from '../src/native-grid.js';
import {ImmutableReader} from '../scripts/check-effective-geographic-regression.mjs';
import {constructOriginalAuthority} from '../scripts/delivery-handoff-advance.mjs';
import {valueSha,diagnoseSourceTargetNativeAuthority} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';

const rectangle=(left,right,bottom=-40,top=40)=>({type:'Polygon',coordinates:[[[left,bottom],[right,bottom],[right,top],[left,top],[left,bottom]]]});
const feature=(id,pixelIndex,geometry,target_id)=>({id,pixelIndex,geometry,...(target_id?{target_id}:{})});
const version='a'.repeat(40),family='gb:TST:ADM2',a=family+':A',b=family+':B',c=family+':C';
const size=262166,latitudes=nativeRowLatitudes(size),latitudeBytes=Buffer.alloc(size*8);
for(let i=0;i<size;i++)latitudeBytes.writeDoubleLE(latitudes[i],i*8);
const digest=raw=>createHash('sha256').update(raw).digest('hex');
const blob=raw=>createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex');
const collection=features=>({type:'FeatureCollection',features});
const rawFeature=(id,geometry)=>({type:'Feature',properties:{shapeID:id},geometry});
const executingHead=execFileSync('git',['-c','protocol.allow=never','rev-parse','HEAD'],{encoding:'utf8'}).trim();
function constructorFixture(change=()=>{},{changeAdoption=()=>{},forgeAdoption}={}){
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
  const put=(name,value,commit=version)=>{
    const raw=Buffer.isBuffer(value)?value:Buffer.from(JSON.stringify(value));
    const pin={commit,path:name,mode:'100644',git_blob_oid:blob(raw),bytes:raw.length,sha256:digest(raw)};
    files.set(commit+':'+name,{raw,pin});byBlob.set(pin.git_blob_oid,raw);return pin;
  };
  const source=put('original-source.json',collection(state.originals)),roster=put('owners.json',state.roster);
  const physical=put('physical.json',state.physical),measured=put('measured.json',state.measured);
  const catalogue=put('coordination/engineering/original-geography-source-corpus-20261006/catalogue.json',{
    products:[{key:family,parts:[{path:source.path,bytes:source.bytes,sha256:source.sha256}],
      feature_count:state.originals.length,original_bytes:source.bytes,original_sha256:source.sha256}]});
  const nativeLatitudes=put('latitudes.f64le',latitudeBytes);
  const membership={index:put('data/world-index.json',state.index),lineage:put('data/semantic-report.json',state.lineage),
    parts:[put('data/geography/part-0.json',state.accepted)]};
  let adoption,provider,adopted,providerFamilies;
  if(state.provider){
    providerFamilies=(state.providers??[state.provider]).map((family,i)=>({family,
      pin:put(i?'whole-provider-'+i+'.json':'whole-provider.json',collection(family.features))}));
    provider=providerFamilies[0].pin;
    adopted={version:1,kind:'adopted-provider-source-families-v1',families:providerFamilies.map(({family, pin})=>({
      source_id:family.family,product:pin,feature_count:family.features.length,
      id_property:family.id_property??'OBJECTID',id_prefix:family.id_prefix??family.family+':OBJECTID:',
      bindings:family.bound.map(ordinal=>{
        const feature=family.features[ordinal],property=feature.properties[family.id_property??'OBJECTID'];
        const target_id=family.target_id??'city',pixelIndex=family.pixelIndex??1;
        return {source_id:(family.id_prefix??family.family+':OBJECTID:')+property,
          feature_ordinal:ordinal,source_property:property,
          properties_sha256:valueSha(feature.properties),geometry_sha256:valueSha(feature.geometry),
          target_id,pixelIndex,base_geometry_sha256:valueSha(state.accepted.features.find(f=>f.id===target_id).geometry),
          decision:'Adopt this provider member for only these existing-target native keys; no native credit.',
          scope:state.proposed.rows.flatMap(row=>row.runs.filter(run=>run[2]===pixelIndex)
            .flatMap(run=>Array.from({length:run[1]-run[0]},(_,i)=>({y:row.y,x:run[0]+i}))))};
      })}))};
    changeAdoption(adopted,state);
    adoption=put('adopted-provider-families.json',adopted);
    put(adoption.path,adopted,executingHead);
    if(forgeAdoption){const forged=structuredClone(adopted);forgeAdoption(forged);adoption=put(adoption.path,forged,'b'.repeat(40));}
  }
  let territorial;
  if(state.territorial){
    const decision=put('territorial-decision.json',{decision:'This original negative is contextual at only the adopted key.'});
    const scope=put('territorial-scope.json',{record:{owner:1,y:state.proposed.rows[0].y,x:state.proposed.rows[0].runs[0][0]}});
    const body={version:1,kind:'adopted-native-territorial-applicability-v1',provenance:[
      {id:'decision',role:'adoption',pin:decision},{id:'scope',role:'scope',pin:scope},
      {id:'original',role:'original-source',parts:[source]}],records:state.targets.map(target=>({
       role:'contextual',source_id:target.id,target_id:'city',pixelIndex:1,y:state.proposed.rows[0].y,
       x:state.proposed.rows[0].runs[0][0],negative_ordinal:0,geometry_sha256:valueSha(state.originals[0].geometry),
       original_source:{id:'original',pointer:'/features/0/geometry'},adoption:{id:'decision',pointer:'/decision'},
       scope:{id:'scope',pointer:'/record',owner_pointer:'/owner'}}))};
    territorial=put('territorial-applicability.json',body);put(territorial.path,body,executingHead);
  }
  const evidence=put('source-evidence.json',{version:1,kind:'source-target-native-evidence-v1',catalogue,
    owner_roster:roster,physical_evidence:physical,physical_input:measured,physical_reproduction:put('physical.py',Buffer.from('# retained fixture')),
    native_latitudes:nativeLatitudes,native_contract:{size,native_latitudes:nativeLatitudes,original_assets:{bounds:{sha256:roster.sha256}}},
    base_reference:{id:'fixture-base'},families:providerFamilies?.map(({family,pin})=>({source_id:family.family,parts:[pin]}))
      ??[{source_id:family,parts:[source]}],
    targets:state.targets.map(target=>({...target,source_receipt_sha256:physical.sha256})),
    ...(state.membership?{source_membership:membership}:{}),...(adoption?{adopted_provider_families:adoption}:{}),
    ...(territorial?{territorial_applicability:territorial}:{})});
  const patch=put('patch.json',state.proposed);
  class FixtureReader extends ImmutableReader{
    git(...args){
      if(args[0]==='ls-tree'){
        const name=args.at(-1),entry=files.get(args[2]+':'+name);assert.ok(entry,name);
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
  return {run:(inputReader=reader())=>constructOriginalAuthority(inputReader,locators),files,byBlob,membership,reader,state,adopted,provider,
    diagnose:()=>diagnoseSourceTargetNativeAuthority(reader(),{...binding,kind:'source-target-native-rule-v1'},binding)};
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
for(const [name,g]of [
 ['horizontal line',{type:'LineString',coordinates:[[-90.01,latitude],[-89.99,latitude]]}],
 ['vertical endpoint',{type:'LineString',coordinates:[[-90,latitude],[-90,latitude+.01]]}],
 ['point',{type:'Point',coordinates:[-90,latitude]}],
 ['collection',{type:'GeometryCollection',geometries:[{type:'Point',coordinates:[-90,latitude]}]}],
 ['hierarchy',{type:'Polygon',coordinates:[[[-90,latitude],[-90.01,.01],[-89.99,.01],[-90,latitude]]]}],
])test('actual constructor vetoes '+name+' contact',()=>assert.throws(()=>constructorFixture(s=>{exactBoundaryTarget(s);conflict(s,name==='hierarchy'?'L2-outside-L1':'contradictory_land_water_support',g);}).run(),/intersect a physical reconstruction residual or conflict witness/));
test('off-centre conflict preserves original witnesses and positive evidence',()=>{const f=constructorFixture(s=>{exactBoundaryTarget(s);const r=conflict(s,'contradictory_land_water_support',off);const g=rectangle(-89.99,-89.98,.001,.002);r.support.hierarchy_disagreements['L2-outside-L1']=g;r.issues.push({reason:'L2-outside-L1',geometry:g});});assert.equal(f.run().ledger_rows[0].native_cells,1);assert.equal(f.state.physical.results[0].issues.length,2);});
for(const [name,change,pattern]of [
 ['unknown query',r=>r.query_relations[0].status='unknown',/Unknown or missing/],
 ['missing query',r=>delete r.query_relations,/query roster/],
 ['shortcut precedence',r=>{r.query_relations[0].candidate_covers_source=true;r.query_relations[0].witness='complete-source-record-reconstruction';},/precedence/],
 ['shortcut fabricated geometry',r=>r.query_relations[0].witness_geometry=emptyPolygon(),/foreign physical source query fields/],
 ['omitted issue',r=>r.issues=[],/Missing or mismatched/],
 ['omitted operation',r=>delete r.support.extra_reconstruction,/operation roster/],
 ['unsupported frame',r=>r.query_relations[0].periodic_offset=360,/Unqualified periodic/],
])test('actual constructor refuses '+name+' with zero contacts',()=>assert.throws(()=>constructorFixture(s=>{exactBoundaryTarget(s);change(conflict(s,'contradictory_land_water_support',off));}).run(),pattern));
test('present unknown issue-free query cannot use legacy fast return',()=>assert.throws(()=>constructorFixture(s=>{query(s.physical.results[0]).query_relations[0].status='unknown';}).run(),/Unknown or missing/));
test('source coverage takes precedence when both covers predicates are true',()=>assert.equal(constructorFixture(s=>query(s.physical.results[0]).query_relations[0].candidate_covers_source=true).run().ledger_rows[0].native_cells,1));
test('same-owner sibling line veto applies through clean member coverage',()=>assert.throws(()=>constructorFixture(s=>conflict(s,'contradictory_land_water_support',{type:'LineString',coordinates:[[-.03,latitude],[0,latitude]]},1)).run(),/intersect a physical reconstruction residual or conflict witness/));
test('different owner witness cannot veto requested clean owner',()=>{const f=constructorFixture(s=>{const g=s.originals[2].geometry;s.targets.push({id:c,pixelIndex:2,source_family:family,base_geometry:g,coverage_classes:['mapped_land_support'],territorial_exclusions:[]});s.physical.results.push({target:c,issues:[],support:{mapped_land_support:g}});s.measured.push({target:c,consumed:{geometry:g},selected:{id:c,geometry:g}});const xx=Math.floor(size/2+.05/360*size);s.proposed.rows[0].runs.push([xx,xx+1,2]);conflict(s,'contradictory_land_water_support',{type:'LineString',coordinates:[[-.03,latitude],[0,latitude]]},2);});assert.equal(f.run().ledger_rows.length,2);});
for(const mode of ['source','coverage','territory','outside'])test('new conflict route retains independent '+mode+' exclusion',()=>{const f=constructorFixture(s=>{exactBoundaryTarget(s);const r=conflict(s,'contradictory_land_water_support',off);if(mode==='source'){s.originals[2].geometry=rectangle(-89.99,-89.97,-.02,.02);s.measured[0].consumed.geometry=s.originals[2].geometry;}if(mode==='coverage')r.support.mapped_land_support=rectangle(-89.99,-89.97,-.02,.02);if(mode==='territory')s.targets[0].territorial_exclusions=[rectangle(-90.01,-89.99,-.01,.01)];if(mode.endsWith('outside'))r.support.outside_mapped_L1_context=rectangle(-90.01,-89.99,-.01,.01);});assert.throws(()=>f.run(),/lack unique source-target coverage|intersect a physical reconstruction residual or conflict witness/);});
function waterSetup(s){exactBoundaryTarget(s);const r=withResiduals(s,[]);r.support.mapped_inland_water_support=r.support.mapped_land_support;r.support.mapped_land_support=rectangle(-89.99,-89.98,-.02,.02);s.targets[0].coverage_classes=['mapped_land_support','mapped_inland_water_support'];s.targets[0].coverage_rows=[{y,runs:[[x,x+1,'mapped_inland_water_support']]}];}
test('declared land cannot borrow water support',()=>assert.throws(()=>constructorFixture(s=>{waterSetup(s);s.targets[0].coverage_rows[0].runs[0][2]='mapped_land_support';}).run(),/lack declared land\/water class support/));
test('class partition cannot introduce unrequested cells',()=>assert.throws(()=>constructorFixture(s=>{waterSetup(s);s.targets[0].coverage_rows[0].runs[0][1]++;}).run(),/differ from complete requested owner cells/));
test('new mixed conflict requires class partition',()=>assert.throws(()=>constructorFixture(s=>{waterSetup(s);const r=conflict(s,'contradictory_land_water_support',off);r.support.mapped_inland_water_support=s.targets[0].base_geometry;delete s.targets[0].coverage_rows;}).run(),/explicit native class rows/));
const effects=(g,rows,n=2,l=[1,-1])=>witnessCellEffects(g,{size:n,latitudes:l,requestedRows:rows,nativePolygonIntervals});
const rows2=[{y:0,runs:[[0,2,1]]},{y:1,runs:[[0,2,1]]}];
test('exact vertical/reversed/zero-length/horizontal endpoints',()=>{for(const coords of [[[-90,1],[-90,-1]],[[-90,-1],[-90,1]]])assert.deepEqual(effects({type:'LineString',coordinates:coords},rows2).hits.map(h=>[h.y,h.x]),[[0,0],[1,0]]);assert.equal(effects({type:'LineString',coordinates:[[-90,1],[-90,1]]},rows2).counts.cells,1);assert.equal(effects({type:'LineString',coordinates:[[-180,1],[180,1]]},rows2).counts.cells,2);});
test('binary64 equality has no epsilon or rounded rational longitude',()=>{assert.equal(effects({type:'Point',coordinates:[-90,1]},rows2).counts.cells,1);assert.equal(effects({type:'Point',coordinates:[-90+2**-46,1]},rows2).counts.cells,0);const n=7,xx=1,longitude=(xx+.5)/n*360-180;assert.equal(effects({type:'Point',coordinates:[longitude,0]},[{y:3,runs:[[xx,xx+1,1]]}],n,[3,2,1,0,-1,-2,-3]).counts.cells,0);});
test('mixed duplicates preserve kinds and unique union',()=>{const g={type:'GeometryCollection',geometries:[{type:'Point',coordinates:[-90,1]},{type:'LineString',coordinates:[[-180,1],[0,1]]},{type:'Point',coordinates:[-90,1]}]};const r=effects(g,rows2);assert.equal(r.counts.cells,1);assert.equal(r.counts.point,1);assert.equal(r.counts.line,1);assert.equal(effects({type:'GeometryCollection',geometries:[]},rows2).counts.cells,0);});
test('malformed unknown and cyclic witnesses fail before scan',()=>{for(const g of [{type:'Unknown',coordinates:[]},{type:'Point',coordinates:[NaN,0]},{type:'Point',coordinates:[0,0,1]},{type:'MultiLineString',coordinates:[[]]},{type:'Polygon',coordinates:[[[0,0],[1,0],[1,1],[0,1]]]}])assert.throws(()=>effects(g,rows2));const cyclic={type:'GeometryCollection',geometries:[]};cyclic.geometries.push(cyclic);assert.throws(()=>effects(cyclic,rows2),/Cyclic/);for(const rows of [[{y:0,runs:[[0,1,0]]}],[{y:0,runs:[[0,2,1],[1,2,1]]}],[rows2[0],rows2[0]]])assert.throws(()=>effects(emptyPolygon(),rows));});
test('explicit single-land partition admits land and refuses absent water class',()=>{
 const setup=s=>{exactBoundaryTarget(s);conflict(s,'contradictory_land_water_support',off);s.targets[0].coverage_rows=[{y,runs:[[x,x+1,'mapped_land_support']]}];};
 assert.equal(constructorFixture(setup).run().ledger_rows[0].native_cells,1);
 assert.throws(()=>constructorFixture(s=>{setup(s);s.targets[0].coverage_rows[0].runs[0][2]='mapped_inland_water_support';}).run(),/lack declared land\/water class support/);
});
test('new mixed conflict retains correct water partition and original issues',()=>{
 const f=constructorFixture(s=>{exactBoundaryTarget(s);const r=conflict(s,'contradictory_land_water_support',off);
 r.support.mapped_inland_water_support=r.support.mapped_land_support;r.support.mapped_land_support=rectangle(-89.99,-89.98,-.02,.02);
 s.targets[0].coverage_classes=['mapped_land_support','mapped_inland_water_support'];s.targets[0].coverage_rows=[{y,runs:[[x,x+1,'mapped_inland_water_support']]}];});
 assert.equal(f.run().ledger_rows[0].native_cells,1);assert.equal(f.state.physical.results[0].issues.length,1);
});
for(const contact of [false,true])test('legacy three-support exterior context '+(contact?'vetoes contact':'preserves irrelevant witness'),()=>{
 const f=constructorFixture(s=>{exactBoundaryTarget(s);const r=s.physical.results[0];
 r.support.mapped_inland_water_support=emptyPolygon();r.support.outside_mapped_L1_context=contact?rectangle(-90.01,-89.99,-.01,.01):rectangle(-89.99,-89.98,-.01,.01);});
 if(contact)assert.throws(()=>f.run(),/intersect a physical reconstruction residual or conflict witness/);
 else assert.equal(f.run().ledger_rows[0].native_cells,1);
 assert.equal(Object.keys(f.state.physical.results[0].support).length,3);
});
test('exact diagonal ideal-rational native centres and reversed segments',()=>{
 const rows=[{y:0,runs:[[0,3,1]]},{y:1,runs:[[0,3,1]]},{y:2,runs:[[0,3,1]]}];
 for(const coordinates of [[[-120,1],[120,-1]],[[120,-1],[-120,1]]])
 assert.deepEqual(effects({type:'LineString',coordinates},rows,3,[1,0,-1]).hits.map(h=>[h.y,h.x]),[[0,0],[1,1],[2,2]]);
});
test('polygon interior and every stock boundary tie remain veto effects',()=>{
 const request=[{y,runs:[[x,x+1,1]]}];
 const interior=rectangle(-90.01,-89.99,-.01,.01);assert.equal(effects(interior,request,size,latitudes).counts.interior,1);
 for(const g of [rectangle(-90.01,-90,-.01,.01),rectangle(-90,-89.99,-.01,.01),
 rectangle(-90.01,-89.99,latitude,.01),rectangle(-90.01,-89.99,-.01,latitude),
 {type:'Polygon',coordinates:[[[-90,latitude],[-90.01,.01],[-89.99,.01],[-90,latitude]]]}])
 assert.equal(effects(g,request,size,latitudes).counts.boundary,1);
 const hole={type:'Polygon',coordinates:[interior.coordinates[0],rectangle(-90.005,-89.995,-.005,.005).coordinates[0]]};
 assert.equal(effects(hole,request,size,latitudes).counts.cells,0);
});


for(const contact of [false,true])test('unselected retained measured sibling '+(contact?'vetoes owner contact':'retains off-centre evidence'),()=>{
 const f=constructorFixture(s=>{s.targets=s.targets.slice(0,1);
 conflict(s,'contradictory_land_water_support',{type:'LineString',coordinates:[[-.03,latitude+(contact?0:.001)],[0,latitude+(contact?0:.001)]]},1);});
 if(contact)assert.throws(()=>f.run(),/intersect a physical reconstruction residual or conflict witness/);
 else assert.equal(f.run().ledger_rows[0].native_cells,1);
 assert.equal(f.state.measured.length,2);assert.equal(f.state.physical.results.length,2);
});
for(const defect of ['missing','duplicate','unknown','wrong-base'])test('unselected measured sibling '+defect+' refuses owner scope',()=>{
 const f=constructorFixture(s=>{s.targets=s.targets.slice(0,1);query(s.physical.results[1]);
 if(defect==='missing')s.physical.results.pop();
 if(defect==='duplicate')s.physical.results.push(s.physical.results[1]);
 if(defect==='unknown')s.physical.results[1].query_relations[0].status='unknown';
 if(defect==='wrong-base')s.measured[1].selected.geometry=rectangle(0,1);
 });assert.throws(()=>f.run(),/sibling physical interpretation|Unknown or missing|Measured sibling differs/);
});
test('unselected general sibling cannot bypass receiving owner mixed-class partition',()=>{
 const setup=s=>{s.targets=s.targets.slice(0,1);const r=withResiduals(s,[]);r.support.mapped_inland_water_support=r.support.mapped_land_support;s.targets[0].coverage_classes=['mapped_land_support','mapped_inland_water_support'];conflict(s,'contradictory_land_water_support',{type:'Point',coordinates:[.05,latitude]},1);};
 assert.throws(()=>constructorFixture(setup).run(),/explicit native class rows/);
 const f=constructorFixture(s=>{setup(s);s.targets[0].coverage_rows=s.proposed.rows.map(r=>({y:r.y,runs:r.runs.map(run=>[run[0],run[1],'mapped_land_support'])}));});
 assert.equal(f.run().ledger_rows[0].native_cells,1);
});
for(const branch of ['candidate','disjoint','operation'])test('actual constructor admits original '+branch+' query branch',()=>{
 const f=constructorFixture(s=>{const r=query(s.physical.results[0]),q=r.query_relations[0];
 q.source_covers_candidate=false;
 if(branch==='candidate'){q.candidate_covers_source=true;q.witness='complete-source-record-reconstruction';}
 if(branch==='disjoint'){q.intersects=false;q.disjoint=true;q.witness='disjoint-after-explicit-predicate';}
 if(branch==='operation'){q.witness='complete-operation-pointset';q.witness_geometry={type:'Point',coordinates:[0,0]};}
 });assert.equal(f.run().ledger_rows[0].native_cells,1);
});
test('missing source identity and duplicate source frame refuse zero-contact authority',()=>{
 for(const mode of ['identity','duplicate'])assert.throws(()=>constructorFixture(s=>{const r=query(s.physical.results[0]);
 if(mode==='identity')r.source_id_queries.push(8);else r.query_relations.push({...r.query_relations[0]});}).run(),/source query identity join|Duplicate physical source query frame/);
});

for(const mode of ['missing','null'])test('new general conflict refuses '+mode+' territorial context',()=>{
 assert.throws(()=>constructorFixture(s=>{exactBoundaryTarget(s);conflict(s,'contradictory_land_water_support',off);
 if(mode==='missing')delete s.targets[0].territorial_exclusions;else s.targets[0].territorial_exclusions=null;
 }).run(),/requires explicit territorial exclusions/);
});

// A complete, synthetic government family. Provider IDs have no original native
// owners; only two explicitly adopted members share the existing canonical city.
const providerFamily='government:TST:district',providerA=providerFamily+':OBJECTID:7',providerB=providerFamily+':OBJECTID:19';
function providerSetup(s,{single=false,full=false}={}){
 const geometry=rectangle(-90.03,-89.97,-.02,.02),base=rectangle(-90.02,-89.98,-.02,.02);
 const sourceFamily=full?'gb-full:TST:ADM2:variant':providerFamily;
 const id=ordinal=>full?sourceFamily+':'+['A','B','C'][ordinal]:sourceFamily+':OBJECTID:'+([7,19,32][ordinal]);
 const features=[geometry,structuredClone(geometry),rectangle(-89.9,-89.8,-.02,.02)]
  .map((geometry,i)=>full?rawFeature(['A','B','C'][i],geometry):
   {type:'Feature',id:[7,19,32][i],properties:{OBJECTID:[7,19,32][i],name:['one','duplicate sibling','unmapped neighbor'][i]},geometry});
 s.provider={family:sourceFamily,features,bound:[0,1],...(full?{id_property:'shapeID',id_prefix:sourceFamily+':'}:{})};
 s.targets=[0,1].map(i=>({id:id(i),target_id:'city',pixelIndex:1,source_family:sourceFamily,
  base_geometry:base,coverage_classes:['mapped_land_support'],territorial_exclusions:[]}));
 s.accepted=collection([{type:'Feature',id:'city',geometry:base,properties:{metadata:{source_member_ids:[a,b]}}}]);
 s.physical.results=[0,1].map(i=>({target:id(i),issues:[],support:{mapped_land_support:features[i].geometry}}));
 s.measured=[0,1].map(i=>({target:id(i),consumed:features[i],selected:{id:'city',geometry:base}}));
 s.proposed.rows=[{y,runs:[[x,x+1,1]]}];
 if(single)s.targets=s.targets.slice(0,1);
}
test('actual constructor admits distinct provider and full-variant IDs only through adopted current canonical bindings',()=>{
 for(const full of [false,true]){
  const f=constructorFixture(s=>providerSetup(s,{full})),before=structuredClone(f.state),reader=f.reader();
  const result=f.run();assert.equal(result.ledger_rows[0].target_id,'city');assert.equal(result.ledger_rows[0].native_cells,1);
  assert.deepEqual(f.state,before);
  const report=f.diagnose();assert.equal(report.supported_cells,1);
  assert.deepEqual(report.provider_competitors.map(item=>[item.source_id,item.feature_ordinal,item.veto_targets]),
   [[full?'gb-full:TST:ADM2:variant:C':providerFamily+':OBJECTID:32',2,[{target_id:'city',pixelIndex:1}]]]);
  // Whole provider, canonical part and adopted decision are real consumed roles.
  f.run(reader);
  for(const path of ['whole-provider.json','adopted-provider-families.json','data/geography/part-0.json'])
   assert.equal(reader.inventory.get(version+':'+path).whole_body_consumed,true,path);
 }
 assert.throws(()=>constructorFixture(s=>{providerSetup(s);s.membership=false;}).run(),/canonical target/);
 assert.throws(()=>constructorFixture(s=>{providerSetup(s);for(const target of s.targets)target.base_geometry=s.provider.features[0].geometry;
  for(const input of s.measured)input.selected.geometry=s.provider.features[0].geometry;}).run(),/base geometry/);
});
for(const [name,change]of Object.entries({
 'wrong source':b=>b.source_id=providerFamily+':OBJECTID:99',
 'wrong ordinal':b=>b.feature_ordinal=2,
 'wrong source property':b=>b.source_property=8,
 'wrong properties':b=>b.properties_sha256='0'.repeat(64),
 'wrong geometry':b=>b.geometry_sha256='0'.repeat(64),
 'wrong target':b=>b.target_id='other-city',
 'wrong owner':b=>b.pixelIndex=3,
 'wrong canonical geometry':b=>b.base_geometry_sha256='0'.repeat(64),
 'empty decision':b=>b.decision=' ',
 'unadopted key':b=>b.scope[0].x++,
 'duplicate key':b=>b.scope.push({...b.scope[0]}),
 'extra scope field':b=>b.scope[0].owner=1
}))test('adopted provider refuses '+name,()=>{
 assert.throws(()=>constructorFixture(providerSetup,{changeAdoption:d=>change(d.families[0].bindings[0])}).run(),
  /adopted provider|Adopted provider|canonical target/i);
});
test('accepted provider decision cannot be coherently forged through the caller reader version',()=>{
 assert.throws(()=>constructorFixture(providerSetup,{forgeAdoption:d=>d.families[0].bindings[0].scope[0].x++}).run(),
  /executing accepted input/);
});
test('complete provider member count, product read role and source identity are mandatory',()=>{
 for(const mutate of [
  d=>d.families[0].feature_count--,
  d=>d.families[0].product={...d.families[0].product,path:'subset.json'},
  d=>d.families[0].source_id=family,
  d=>d.families[0].id_prefix='invented:',
  d=>d.families[0].bindings.push({...d.families[0].bindings[0]})
 ])assert.throws(()=>constructorFixture(providerSetup,{changeAdoption:mutate}).run(),/provider|family|read role/i);
 const missing=constructorFixture(providerSetup),raw=Buffer.from(JSON.stringify(collection(missing.state.provider.features.slice(0,2))));
 missing.byBlob.set(missing.provider.git_blob_oid,raw);
 assert.throws(()=>missing.run(),/whole|identity|body|hash|length/i);
 assert.throws(()=>constructorFixture(s=>{providerSetup(s);s.provider.features[2].properties.OBJECTID=7;}).run(),/Duplicate adopted provider source identity/);
 assert.throws(()=>constructorFixture(s=>{providerSetup(s);s.measured[0].consumed=structuredClone(s.measured[0].consumed);
  s.measured[0].consumed.properties.name='wrong consumed member';}).run(),/measured whole inputs/);
});
for(const boundary of [false,true])test('unmapped whole provider member retains '+(boundary?'boundary':'interior')+' veto and its real source identity',()=>{
 const f=constructorFixture(s=>{providerSetup(s);s.provider.features[2].geometry=rectangle(boundary?-90:-90.01,-89.99,-.01,.01);});
 assert.throws(()=>f.run(),/unique source-target coverage/);
 const report=f.diagnose();assert.equal(report.held_cells,1);
 assert.equal(report.provider_competitors[0].source_id,providerFamily+':OBJECTID:32');
 assert.equal(report.decision_rows[0].runs[0][3],boundary?'boundary_cells':'territorial_exclusion_cells');
});
test('both duplicate provider siblings remain measured when one is omitted from positive evidence',()=>{
 const clean=constructorFixture(s=>providerSetup(s,{single:true}));assert.equal(clean.run().ledger_rows[0].native_cells,1);
 for(const defect of ['both-physical-roles','result','input','unbound']){
  const f=constructorFixture(s=>{providerSetup(s,{single:true});
   if(defect==='both-physical-roles'){s.physical.results.pop();s.measured.pop();}
   if(defect==='result')s.physical.results.pop();if(defect==='input')s.measured.pop();
   if(defect==='unbound')s.provider.bound.pop();
  });assert.throws(()=>f.run(),/sibling physical interpretation|unique source-target coverage/);
 }
 const veto=constructorFixture(s=>{providerSetup(s,{single:true});
  conflict(s,'contradictory_land_water_support',{type:'MultiLineString',coordinates:[[[-90.01,latitude],[-89.99,latitude]]]},1);
 });assert.throws(()=>veto.run(),/physical reconstruction residual or conflict witness/);
 const residual=constructorFixture(s=>{providerSetup(s);withResiduals(s,[['extra_reconstruction',rectangle(-90.01,-89.99,-.01,.01)]]);});
 assert.throws(()=>residual.run(),/physical reconstruction residual or conflict witness/);
 const noBorrow=constructorFixture(s=>{providerSetup(s,{single:true});s.provider.features[0].geometry=rectangle(-89.99,-89.97,-.02,.02);});
 assert.throws(()=>noBorrow.run(),/unique source-target coverage/);
});

test('a contextual original negative cannot clear an identical unmapped provider competitor',()=>{
 const setup=s=>{providerSetup(s);s.territorial=true;
  s.originals[0].geometry=rectangle(-90.01,-89.99,-.01,.01);
  for(const target of s.targets)target.territorial_exclusions=[s.originals[0].geometry];
 };
 const clean=constructorFixture(setup);assert.equal(clean.run().ledger_rows[0].native_cells,1);
 const held=constructorFixture(s=>{setup(s);s.provider.features[2].geometry=structuredClone(s.originals[0].geometry);});
 assert.throws(()=>held.run(),/unique source-target coverage/);
 const diagnostic=held.diagnose();assert.equal(diagnostic.held_cells,1);
 const contacts=diagnostic.territorial_contacts.filter(hit=>hit.provider_source_id===providerFamily+':OBJECTID:32');
 assert.ok(contacts.length>0);assert.ok(contacts.every(hit=>hit.resolution==='retained-territorial-veto'&&hit.negative_ordinal===null));
});

function twoProviderFamilies(s){
 providerSetup(s);s.provider.features[2].geometry=rectangle(-89.7,-89.6,-.02,.02);
 const family='government:TST:other',geometry=rectangle(-89.88,-89.82,-.02,.02);
 const features=[geometry,rectangle(-89.4,-89.3,-.02,.02)].map((geometry,i)=>({type:'Feature',id:201+i,
  properties:{OBJECTID:201+i},geometry}));
 const other={family,features,bound:[0],target_id:'other-city',pixelIndex:3};s.providers=[s.provider,other];
 s.accepted.features.push({type:'Feature',id:'other-city',geometry,properties:{}});
 const id=family+':OBJECTID:201';
 s.targets.push({id,target_id:'other-city',pixelIndex:3,source_family:family,base_geometry:geometry,
  coverage_classes:['mapped_land_support'],territorial_exclusions:[]});
 s.measured.push({target:id,consumed:features[0],selected:{id:'other-city',geometry}});
 s.physical.results.push({target:id,issues:[],support:{mapped_land_support:geometry}});
 const xx=Math.floor((-89.85+180)/360*size);s.proposed.rows[0].runs.push([xx,xx+1,3]);
}
test('complete provider vetoes cross family boundaries without fabricating a competing owner',()=>{
 const clean=constructorFixture(twoProviderFamilies);assert.equal(clean.run().ledger_rows.length,2);
 for(const bound of [false,true]){
  const held=constructorFixture(s=>{twoProviderFamilies(s);const other=s.providers[1],contact=rectangle(-90.01,-89.99,-.01,.01);
   other.features[bound?0:1].geometry=bound?{type:'MultiPolygon',coordinates:[other.features[0].geometry.coordinates,contact.coordinates]}:contact;
  });assert.throws(()=>held.run(),/unique source-target coverage/);
  const report=held.diagnose(),id='government:TST:other:OBJECTID:'+(bound?201:202);
  assert.equal(report.held_cells,1);assert.equal(report.supported_cells,1);
  assert.ok(report.provider_competitors.find(member=>member.source_id===id).veto_targets.some(t=>t.target_id==='city'));
 }
});
