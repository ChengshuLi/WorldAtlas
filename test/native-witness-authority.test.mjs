import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {deriveSourceTargetNativeDelta,nativeRowLatitudes,nativePolygonIntervals,polygonParts,witnessCellEffects,validateWitnessGeometry} from '../src/native-grid.js';
import {ImmutableReader} from '../scripts/check-effective-geographic-regression.mjs';
import {constructOriginalAuthority} from '../scripts/delivery-handoff-advance.mjs';

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
  const reader=()=>new FixtureReader('.',version);
  const locators={source_evidence:{commit:version,path:evidence.path},native_patch:{commit:version,path:patch.path}};
  return {run:()=>constructOriginalAuthority(reader(),locators),files,byBlob,membership,reader,state};
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
