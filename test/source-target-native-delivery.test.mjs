import test from 'node:test';
import assert from 'node:assert/strict';
import {deriveSourceTargetNativeDelta} from '../scripts/additive-gap-repair.mjs';
import {nativeRowLatitudes} from '../src/native-grid.js';
const polygon = (left, right) => ({type:'Polygon', coordinates:[[[left,-40],[right,-40],[right,40],[left,40],[left,-40]]]});
const feature = (id, pixelIndex, geometry) => ({id,pixelIndex,geometry});
function inputs() {
  const a = feature('source:A',1,polygon(-89,89));
  return {targets:[{id:a.id,pixelIndex:1}],sourceFeatures:[a],coverageFeatures:[a],
    ownerRows:Array.from({length:8},(_,y)=>({y,complete_owner_intervals:[]})),
    size:8,latitudes:nativeRowLatitudes(8),rowStart:0,rowEnd:8};
}
test('source-native assignments use the literal grid and need no gap polygons',()=>{
  const result=deriveSourceTargetNativeDelta(inputs());
  assert.deepEqual(result.rows,[{y:3,runs:[[2,6,1]]},{y:4,runs:[[2,6,1]]}]);
  assert.equal(result.assigned_cells,8); assert.equal(result.reassigned_cells,0);
});
test('every existing owner is preserved, including the same intended owner',()=>{
  const input=inputs(); input.ownerRows[3].complete_owner_intervals=[[2,3,2],[4,5,1]];
  const result=deriveSourceTargetNativeDelta(input);
  assert.deepEqual(result.rows[0],{y:3,runs:[[3,4,1],[5,6,1]]});
  assert.equal(result.already_owned_cells,2); assert.equal(result.assigned_cells,6);
});
test('competing source owners are withheld symmetrically',()=>{
  const input=inputs(); input.sourceFeatures.push(feature('source:B',2,polygon(-1,89)));
  const result=deriveSourceTargetNativeDelta(input);
  assert.equal(result.ambiguous_owner_cells,4); assert.equal(result.assigned_cells,4);
});
test('reviewed territorial exclusions are independent of physical water',()=>{
  const input=inputs(); input.territorialExclusions=[feature('source:A',1,polygon(-1,89))];
  const result=deriveSourceTargetNativeDelta(input);
  assert.equal(result.territorial_exclusion_cells,4); assert.equal(result.assigned_cells,4);
  // A physical label is not consumed as a territorial exclusion.
  const water=inputs(); water.physical_status='water-supported';
  assert.equal(deriveSourceTargetNativeDelta(water).assigned_cells,8);
});
test('unsupported coverage stays withheld',()=>{
  const input=inputs(); input.coverageFeatures=[feature('source:A',1,polygon(-89,-1))];
  const result=deriveSourceTargetNativeDelta(input);
  assert.equal(result.unsupported_coverage_cells,4); assert.equal(result.assigned_cells,4);
});
test('missing current rows and foreign target joins fail closed',()=>{
  const input=inputs();input.ownerRows.pop();assert.throws(()=>deriveSourceTargetNativeDelta(input),/extent/);
  const wrong=inputs();wrong.targets[0].id='invented';assert.throws(()=>deriveSourceTargetNativeDelta(wrong),/roster/);
});

test('native-only default and affected historical contexts retain exact cells and bounds',async()=>{
  const fs=await import('node:fs'), {gunzipSync}=await import('node:zlib'), {createHash}=await import('node:crypto');
  const {compileNativeRuntime}=await import('../src/native-runtime.js');
  const {compileNativeLocationContext}=await import('../src/native-location-context.js');
  const {nativeSourceDigest}=await import('../src/native-source-digest.js');
  const {pickOwnership}=await import('../src/pixel-ownership.js');
  const {applyAdditiveNativePatch,footprintValueSha256:hash,additiveReleaseFootprintDigest,
    effectiveFootprintBounds,nativeOnlyComponent,verifyAdditiveLedgerSelection}=await import('../src/effective-footprint.js');
  const size=262166, raw=gunzipSync(fs.readFileSync('coordination/engineering/native-grid-fidelity-1010-20261005-local15/results-v1/native-row-latitudes.f64le.gz'));
  const latitudes=Float64Array.from({length:size},(_,i)=>raw.readDoubleLE(i*8));
  const rectangle=(a,b,c,d)=>({type:'Polygon',coordinates:[[[a,b],[c,b],[c,d],[a,d],[a,b]]]});
  const a=feature('A',1,rectangle(0,0,1,1)), b=feature('B',2,rectangle(2,0,3,1));
  const base=await compileNativeRuntime([a,b],{size,latitudes});
  const baseReference={id:'geography:fixture-base',footprints_sha256:(await nativeSourceDigest([a,b])).sha256,hierarchy_sha256:'b'.repeat(64)};
  Object.assign(base,baseReference,{geographic_release:baseReference.id,reference_owner_sha256:createHash('sha256').update(JSON.stringify([[1,'A'],[2,'B']])).digest('hex')});
  const x=Math.floor((10+180)/360*size),y=latitudes.findIndex(latitude=>latitude<.5);
  const component={representation:'native-cells',component_id:'source-target:fixture',target_id:'A',pixelIndex:1,
    disposition:'assigned',base_geometry:a.geometry,base_geometry_sha256:hash(a.geometry),
    native_rows:[{y,runs:[[x,x+1,1]]}],native_bounds:[10,latitudes[y],10,latitudes[y]],native_cells:1,
    source_receipt_sha256:'c'.repeat(64),authority_sha256:'d'.repeat(64),rule_sha256:'e'.repeat(64)};
  assert.equal(nativeOnlyComponent(component),true);
  const {repairVisibilityWitnesses}=await import('../scripts/check-effective-geographic-regression.mjs');
  const witness=(before,after,candidates=[component])=>repairVisibilityWitnesses({candidates,size,latitudes,
    beforeRows:[{y,runs:before}],afterRows:[{y,runs:after}]});
  assert.equal(witness([],[[x,x+1,1]])[0].candidate_owner,1);
  assert.deepEqual(witness([],[]),[null]);
  assert.deepEqual(witness([],[[x,x+1,2]]),[null]);
  assert.deepEqual(witness([[x,x+1,2]],[[x,x+1,1]]),[null]);
  assert.deepEqual(witness([],[[x+1,x+2,1]]),[null]);
  assert.throws(()=>witness([],[],[component,component]),/Duplicate/);
  const sibling={component_id:'geometry:sibling',pixelIndex:1,geometry:rectangle(0,0,1,1)};
  assert.deepEqual(witness([],[[x,x+1,1]],[component,sibling]).map(v=>v?.component_id??null),[component.component_id,null]);

  const selected={...a,additiveFootprint:{version:2,kind:'retained-base-plus-additions',
    baseline_release_sha256:baseReference.footprints_sha256,base_geometry_sha256:hash(a.geometry),ledger_sha256:'f'.repeat(64),
    authority_registry_sha256:'d'.repeat(64),components:[component]}};
  const features=[selected,b],effectiveReference={...baseReference,id:'geography:fixture-selected',footprints_sha256:additiveReleaseFootprintDigest(baseReference,features)};
  const patch={version:2,kind:'unassigned-native-cells-v1',base_reference:baseReference,effective_reference:effectiveReference,
    ledger_sha256:'f'.repeat(64),authority_registry_sha256:'d'.repeat(64),rows:component.native_rows};
  const ledger={version:2,kind:'native-additive-repair-ledger-v2',authority_registry_sha256:'d'.repeat(64),
    parent_inventory:{components:0,report_sha256:'1'.repeat(64),roster_sha256:'2'.repeat(64)},scope_ids:[component.component_id],rows:[component]};
  assert.equal(verifyAdditiveLedgerSelection(ledger,features,patch).assigned_cells,1);
  const shifted=structuredClone(patch);shifted.rows[0].runs[0]=[x+10,x+11,1];
  assert.throws(()=>verifyAdditiveLedgerSelection(ledger,features,shifted),/intervals omitted/);
  const effective=applyAdditiveNativePatch(base,patch,{baseReference,effectiveReference,features});
  assert.equal(pickOwnership(effective,x,y),1);assert.equal(pickOwnership(base,x,y),0);
  assert.equal(effectiveFootprintBounds(selected)[2],10);
  const unchanged=await compileNativeLocationContext({referenceFeatures:features,features,base:effective,latitudes});
  assert.equal(unchanged.accounting.recomputedRows,0);assert.equal(pickOwnership(unchanged.grid,x,y),1);
  const changed=await compileNativeLocationContext({referenceFeatures:features,features:[selected],base:effective,latitudes});
  assert.ok(changed.accounting.recomputedRows>0);assert.equal(pickOwnership(changed.grid,x,y),1);
  const ax=Math.floor(180.5/360*size);assert.equal(pickOwnership(changed.grid,ax,y),1);
  assert.equal(pickOwnership(base,ax,y),1);
  const corrupt=structuredClone(component);corrupt.native_rows[0].runs[0][2]=2;
  assert.throws(()=>nativeOnlyComponent(corrupt),/interval/);
});

test('multiple territorial masks for one target combine without source-ID relaxation',()=>{
  const input=inputs();input.territorialExclusions=[feature('source:A',1,polygon(-89,-46)),feature('source:A',1,polygon(46,89))];
  assert.equal(deriveSourceTargetNativeDelta(input).territorial_exclusion_cells,4);
  const duplicate=inputs();duplicate.sourceFeatures.push(duplicate.sourceFeatures[0]);
  assert.throws(()=>deriveSourceTargetNativeDelta(duplicate),/source owner roster/);
});

test('trusted reader, source constructor and profile execute without installed npm packages',async()=>{
  const fs=await import('node:fs'),os=await import('node:os'),path=await import('node:path');
  const {execFileSync}=await import('node:child_process');
  const root=path.resolve('.'),cold=fs.mkdtempSync(path.join(os.tmpdir(),'worldatlas-native-cold-')),seen=new Set();
  const entries=['scripts/check-effective-geographic-regression.mjs','scripts/delivery-handoff-advance.mjs',
    'scripts/integration-profile.mjs','coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs'];
  const copy=relative=>{
    if(seen.has(relative))return;seen.add(relative);
    const source=fs.readFileSync(path.join(root,relative),'utf8'),target=path.join(cold,relative);
    fs.mkdirSync(path.dirname(target),{recursive:true});fs.writeFileSync(target,source);
    for(const match of source.matchAll(/\b(?:from\s*|import\s*)['"](\.[^'"]+)['"]/g))
      copy(path.relative(root,path.resolve(root,path.dirname(relative),match[1])));
  };
  try{
    entries.forEach(copy);fs.writeFileSync(path.join(cold,'package.json'),'{"type":"module"}');
    const script=`import assert from 'node:assert/strict';
      for(const entry of ${JSON.stringify(entries)})await import('./'+entry);
      const {deriveSourceTargetNativeDelta,nativeOnlyComponent}=await import('./src/native-grid.js');
      const {nativeRowLatitudes}=await import('./src/native-grid.js');
      const {valueSha}=await import('./coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs');
      const {repairVisibilityWitnesses}=await import('./scripts/check-effective-geographic-regression.mjs');
      const geometry=${JSON.stringify(polygon(-89,89))},feature={id:'source:A',pixelIndex:1,geometry};
      const result=deriveSourceTargetNativeDelta({targets:[feature],sourceFeatures:[feature],coverageFeatures:[feature],
        ownerRows:Array.from({length:8},(_,y)=>({y,complete_owner_intervals:[]})),size:8,latitudes:nativeRowLatitudes(8),rowStart:0,rowEnd:8});
      assert.equal(result.assigned_cells,8);
      const component={representation:'native-cells',component_id:'cold:A',target_id:feature.id,pixelIndex:1,disposition:'assigned',
        base_geometry:geometry,base_geometry_sha256:valueSha(geometry),native_rows:result.rows,native_bounds:[-89,-40,89,40],native_cells:8,
        source_receipt_sha256:'a'.repeat(64),authority_sha256:'b'.repeat(64),rule_sha256:'c'.repeat(64)};
      assert.equal(nativeOnlyComponent(component,valueSha),true);
      const witness=repairVisibilityWitnesses({candidates:[component],size:8,latitudes:nativeRowLatitudes(8),
        beforeRows:[{y:3,runs:[]}],afterRows:[result.rows[0]]})[0];
      assert.equal(witness.candidate_owner,1);console.log('cold native authority entries passed');`;
    fs.writeFileSync(path.join(cold,'probe.mjs'),script);
    assert.match(execFileSync(process.execPath,[path.join(cold,'probe.mjs')],
      {cwd:cold,encoding:'utf8',env:{...process.env,NODE_PATH:'',NODE_OPTIONS:''}}),/cold native authority entries passed/);
  }finally{fs.rmSync(cold,{recursive:true,force:true});}
});
