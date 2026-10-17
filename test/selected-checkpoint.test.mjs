import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {pathToFileURL} from 'node:url';
import {valueSha} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
import {deriveCoordinateDelta,projectSourceFeatures,projectNativeRows,qualifyTransition} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-checkpoint.mjs';
import {MODULE,PROGRAMME,CATALOGUE,CODE,polygon,feature,fixtures,addition,trustedFixture,appendNativeAuthority} from './fixtures/selected-checkpoint.mjs';

test('serialized lookalikes cannot mint state or projectors',()=>{
 const state={version:1,kind:'verified-selected-state-v1',certificate:fixtures().certificate};
 assert.throws(()=>projectSourceFeatures({state,ids:['A']}),/private qualified/);
 assert.throws(()=>projectNativeRows({state,rows:[0]}),/private qualified/);
 assert.throws(()=>qualifyTransition({state,reader:{}}),/private qualified/);
});
test('append arithmetic retains all owners and authenticates changed literal additions',()=>{
 const {certificate}=fixtures(), a=addition('a','A',1,certificate.entries[0][7],1.05), b=addition('b','C',3,certificate.entries[2][7],1.1);
 const result=deriveCoordinateDelta({certificate,oldAdditions:[],additions:[a,b],selection:{next:true}});
 assert.equal(result.certificate.entries.length,3);
 assert.strictEqual(result.certificate.entries[1],certificate.entries[1]);
 assert.deepEqual(result.changedIds,['A','C']);
 assert.equal(result.certificate.entries[0][8],valueSha({base_geometry_sha256:certificate.entries[0][7],additions:[a]}));
 assert.deepEqual(result.certificate.entries[0][9],[[0,0,1.25,.2]]);
 assert.deepEqual(result.certificate.binding.selection,{next:true});
});
test('delta arithmetic rejects omitted old primitives, same-count owner swaps and stale base hashes',()=>{
 const {certificate}=fixtures(), old=addition('old','A',1,certificate.entries[0][7],.3);
 const before=deriveCoordinateDelta({certificate,oldAdditions:[],additions:[old],selection:{}}).certificate;
 assert.throws(()=>deriveCoordinateDelta({certificate:before,oldAdditions:[old],additions:[],selection:{}}),/Old effective/);
 assert.throws(()=>deriveCoordinateDelta({certificate:before,oldAdditions:[old],additions:[{...old,pixelIndex:2}],selection:{}}),/Old effective/);
 assert.throws(()=>deriveCoordinateDelta({certificate,oldAdditions:[],additions:[{...old,base_geometry_sha256:'0'.repeat(64)}],selection:{}}),/stale base/);
 assert.throws(()=>deriveCoordinateDelta({certificate,oldAdditions:[],additions:[{...old,geometry:polygon(20)}],selection:{}}),/changed geometry/);
 assert.throws(()=>deriveCoordinateDelta({certificate,oldAdditions:[],additions:[old,old],selection:{}}),/Duplicate/);
});

test('native-only append uses exact native bounds and identity without an addition polygon',()=>{
 const {features,certificate}=fixtures();
 const row={representation:'native-cells',component_id:'source-target:A',target_id:'A',pixelIndex:1,
  disposition:'assigned',base_geometry:features[0].geometry,base_geometry_sha256:certificate.entries[0][7],
  native_rows:[{y:2,runs:[[3,5,1]]}],native_bounds:[10,20,11,21],native_cells:2,
  source_receipt_sha256:'a'.repeat(64),authority_sha256:'b'.repeat(64),rule_sha256:'c'.repeat(64)};
 const result=deriveCoordinateDelta({certificate,oldAdditions:[],additions:[row],selection:{native:true}});
 assert.deepEqual(result.changedIds,['A']);
 assert.deepEqual(result.certificate.entries[0][9],[[0,0,11,21]]);
 assert.equal(result.certificate.entries[0][8],valueSha({base_geometry_sha256:certificate.entries[0][7],additions:[row]}));
 for(const invalid of [{...row,native_rows:[{y:2,runs:[[3,5,2]]}]},{...row,native_cells:1},
  {...row,base_geometry:polygon(30)},{...row,native_bounds:[10,20,181,21]}, {...row,geometry:polygon(10)}])
  assert.throws(()=>deriveCoordinateDelta({certificate,oldAdditions:[],additions:[invalid],selection:{}}),
   /native component interval|cell count|current base changed|component bounds|foreign fields/i);
 const changed={...row,native_rows:[{y:2,runs:[[4,6,1]]}]};
 assert.throws(()=>deriveCoordinateDelta({certificate:result.certificate,oldAdditions:[row],additions:[changed],selection:{}}),/Old effective/);
});

test('real catalogue entry qualifies a complete state, retains exceptions and projects exact feature/native rows',async t=>{
 const f=await trustedFixture(t), result=f.api.qualifyCheckpoint({reader:f.reader});
 assert.equal(result.available,true);const state=result.state;
 assert.equal(state.ledger.rows.length,2);assert.equal(state.ledger.rows[1].disposition,'rejected');
 const sources=f.api.projectSourceFeatures({state,ids:['A','B']});
 assert.deepEqual(sources.features.map(p=>p.id),['A','B']);assert.equal(sources.inverse.length,2);
 const native=f.api.projectNativeRows({state,rows:[1]});
 assert.deepEqual(native.rows,[{y:1,runs:[[0,1,2]]}]);assert.deepEqual(native.acquired_rows,[]);
 const fresh=f.api.projectNativeRows({state,rows:[0,1,2,3]});
 assert.deepEqual(fresh.rows,[{y:0,runs:[[0,1,1]]},{y:1,runs:[[0,1,2]]},{y:2,runs:[[1,2,3]]},{y:3,runs:[]}]);
 assert.deepEqual(fresh.acquired_rows,[0,2,3]);assert.ok(fresh.custody.new_whole_inputs.length>=2);
 assert.throws(()=>f.api.projectNativeRows({state:JSON.parse(JSON.stringify(state)),rows:[1]}),/private qualified/);
 f.api.releaseCheckpoint(state);assert.throws(()=>f.api.projectSourceFeatures({state,ids:['A']}),/private qualified/);
});
test('unchanged actual selection at a newer commit reuses the original accepted checkpoint',async t=>{
 const f=await trustedFixture(t);f.save('unrelated.json',{new:true});const newer=f.commit();
 const reader=new f.native.ImmutableReader(f.root,newer);
 const result=f.api.qualifyCheckpoint({reader});assert.equal(result.available,true);
 assert.equal(result.state.selected_commit,newer);assert.equal(result.state.accepted_execution.historical_selected_commit,f.selected);
 const transition=f.api.qualifyTransition({state:result.state,reader});assert.equal(transition.available,true);
 assert.deepEqual(transition.changedIds,[]);assert.deepEqual(transition.changedNativeRows,[]);
 assert.deepEqual(transition.changedIds,[]);
});
test('committed qualifier edits need no manual catalogue fingerprint refresh',async t=>{
 const f=await trustedFixture(t), catalogue=fs.readFileSync(path.join(f.root,CATALOGUE));
 fs.appendFileSync(path.join(f.root,MODULE),'\n// reviewed non-scientific change\n');const newer=f.commit();
 const reader=new f.native.ImmutableReader(f.root,newer);
 assert.equal(f.api.qualifyCheckpoint({reader}).available,true);
 assert.deepEqual(fs.readFileSync(path.join(f.root,CATALOGUE)),catalogue);
});
test('changed same-count source owners cannot reuse accepted custody',async t=>{
 const f=await trustedFixture(t);f.save('data/source.json',{type:'FeatureCollection',features:[feature('B',0),feature('A',1),feature('C',5)]});const candidate=f.commit();
 const reader=new f.native.ImmutableReader(f.root,candidate);
 const result=f.api.qualifyCheckpoint({reader});assert.equal(result.available,false);assert.match(result.reason,/routing alternative changed/);
});
test('corrupt accepted products and dirty executing code are rejected rather than treated as no change',async t=>{
 const f=await trustedFixture(t);f.rootRow.certificate.decoded_sha256='0'.repeat(64);
 f.save(CATALOGUE,{version:1,kind:'accepted-selected-checkpoints-v1',checkpoints:[f.rootRow]});f.commit();
 assert.throws(()=>f.api.qualifyCheckpoint({reader:f.reader}),/decoded output is corrupt/);
 f.save(MODULE,Buffer.concat([fs.readFileSync(path.join(f.root,MODULE)),Buffer.from('\n// drift\n')]));
 const reader=new f.native.ImmutableReader(f.root,f.selected);
 assert.throws(()=>f.api.qualifyCheckpoint({reader}),/changed executing checkpoint method/);
});

test('native projection rejects an incomplete complete row partition despite matching encoded and decoded hashes',async t=>{
 const f=await trustedFixture(t,{incompleteNative:true}),result=f.api.qualifyCheckpoint({reader:f.reader});
 assert.equal(result.available,true);
 assert.throws(()=>f.api.projectNativeRows({state:result.state,rows:[2]}),/row partition omitted/);
});
test('a forged candidate-selected checkpoint catalogue cannot replace trusted execution authority',async t=>{
 const f=await trustedFixture(t);const original=f.git('rev-parse','HEAD').toString().trim();
 f.save(CATALOGUE,{version:1,kind:'accepted-selected-checkpoints-v1',checkpoints:[]});const candidate=f.commit();
 f.git('checkout','-q',original);
 const reader=new f.native.ImmutableReader(f.root,candidate);
 assert.equal(f.api.qualifyCheckpoint({reader}).available,true);
});

function candidateProducts(f,{ledger=f.ledger,patch=f.patch}={}){
 f.save('candidate/ledger.json',ledger);const l=f.commit();
 patch={...patch,ledger_sha256:f.pin('candidate/ledger.json',l).sha256};f.save('candidate/patch.json',patch);const p=f.commit();
 const assets={...f.sidecar.logical_asset_map,ledger:f.pin('candidate/ledger.json',l),patch:f.pin('candidate/patch.json',p)};
 f.save('candidate/envelope.json',{...f.envelope,...assets});const e=f.commit();
 f.save('candidate/sidecar.json',{...f.sidecar,logical_asset_map:assets,runtime_envelope:f.pin('candidate/envelope.json',e)});const sc=f.commit();
 const side=f.pin('candidate/sidecar.json',sc);
 f.save('data/ownership-selection.json',{...f.selection,additive_release:{path:side.path,bytes:side.bytes,sha256:side.sha256}});return f.commit();
}
test('actual transition rejects missing complete exception records and native owner reassignment',async t=>{
 const f=await trustedFixture(t), result=f.api.qualifyCheckpoint({reader:f.reader});
 const ledger={...f.ledger,scope_ids:['old'],rows:[f.ledger.rows[0]]};
 const candidate=candidateProducts(f,{ledger});
 const reader=new f.native.ImmutableReader(f.root,candidate,{invocation:f.reader.invocation});
 assert.throws(()=>f.api.qualifyTransition({state:result.state,reader}),/Old complete ledger/);
 assert.deepEqual(f.api.projectNativeRows({state:result.state,rows:[1]}).rows,[{y:1,runs:[[0,1,2]]}]);
});
test('actual transition rejects same-count changed native ownership without reacquiring original science',async t=>{
 const f=await trustedFixture(t), result=f.api.qualifyCheckpoint({reader:f.reader});
 const candidate=candidateProducts(f,{patch:{...f.patch,rows:[{y:1,runs:[[2,3,2]]}]}});
 const reader=new f.native.ImmutableReader(f.root,candidate,{invocation:f.reader.invocation});
 assert.throws(()=>f.api.qualifyTransition({state:result.state,reader}),/omitted, invented or reassigned/);
});
test('actual transition refuses a stale base and preserves the usable baseline for candidate-only cold validation',async t=>{
 const f=await trustedFixture(t), result=f.api.qualifyCheckpoint({reader:f.reader});
 f.save('candidate/sidecar.json',{...f.sidecar,base_selection:{...f.sidecar.base_selection,release_id:'geography:new'}});const a=f.commit(),p=f.pin('candidate/sidecar.json',a);
 f.save('data/ownership-selection.json',{...f.selection,release_id:'geography:new',additive_release:{path:p.path,bytes:p.bytes,sha256:p.sha256}});const candidate=f.commit();
 const reader=new f.native.ImmutableReader(f.root,candidate,{invocation:f.reader.invocation});
 const transition=f.api.qualifyTransition({state:result.state,reader});
 assert.equal(transition.available,false);assert.equal(transition.cold,'candidate');assert.strictEqual(transition.baseline,result.state);
});

test('private source reuse snapshots exact caller scope and rejects altered projections',async t=>{
 const f=await trustedFixture(t),{state}=f.api.qualifyCheckpoint({reader:f.reader});
 const ids=['A'],projection=f.api.projectSourceFeatures({state,ids});
 ids[0]='B';assert.throws(()=>f.api.projectSourceFeatures({state,ids:['B'],reuse:projection}),/incomplete source projection reuse/);
 const reused=f.api.projectSourceFeatures({state,ids:['A'],reuse:projection});
 assert.equal(reused.features[0].id,'A');
 assert.throws(()=>f.api.projectSourceFeatures({state,ids:['A'],reuse:{...projection}}),/source projection reuse/);
 f.api.releaseCheckpoint(state);
});test('fast selection admission rejects unknown patch fields and malformed complete effective references',async t=>{
 const f=await trustedFixture(t),{state}=f.api.qualifyCheckpoint({reader:f.reader});
 const candidate=candidateProducts(f,{patch:{...f.patch,unexpected_permission:true}});
 const reader=new f.native.ImmutableReader(f.root,candidate,{invocation:f.reader.invocation});
 assert.throws(()=>f.api.qualifyTransition({state,reader}),/complete native patch schema/);
});

test('an unchanged accepted current-rebind proof cannot excuse a coherently repinned omitted target roster',async t=>{
 const f=await trustedFixture(t),{state}=f.api.qualifyCheckpoint({reader:f.reader});
 const candidate=candidateProducts(f,{ledger:{...f.ledger,current_targets:[]}});
 const reader=new f.native.ImmutableReader(f.root,candidate,{invocation:f.reader.invocation});
 assert.throws(()=>f.api.qualifyTransition({state,reader}),/Ledger complete current target roster differs/);
});
test('coherently copied malformed geography references still fail exact fast-path admission',async t=>{
 const f=await trustedFixture(t),{state}=f.api.qualifyCheckpoint({reader:f.reader});
 const effective={...f.patch.effective_reference};delete effective.id;
 f.envelope={...f.envelope,effective_reference:effective};
 const candidate=candidateProducts(f,{patch:{...f.patch,effective_reference:effective}});
 const reader=new f.native.ImmutableReader(f.root,candidate,{invocation:f.reader.invocation});
 assert.throws(()=>f.api.qualifyTransition({state,reader}),/complete effective reference/);
});


test('consumer admission authenticates the private complete transition rather than a forged scope wrapper',async t=>{
 const f=await trustedFixture(t),{state}=f.api.qualifyCheckpoint({reader:f.reader});
 const reader=new f.native.ImmutableReader(f.root,f.selected,{invocation:f.reader.invocation});
 const transition=f.api.qualifyTransition({state,reader});
 assert.equal(transition.available,true);
 assert.equal(f.api.authenticateTransition({transition}),transition);
 assert.throws(()=>transition.changedNativeRows.push(1),TypeError);
 assert.throws(()=>transition.changedIds.push('omitted-neighbor'),TypeError);
 for(const forged of [{...transition},{...transition,plan:{...transition.plan,required_ids:[],pairs:[]}},{...transition,changedNativeRows:[]},JSON.parse(JSON.stringify(transition))])
  assert.throws(()=>f.api.authenticateTransition({transition:forged}),/private qualified selected transition/);
 f.api.releaseCheckpoint(state);
 assert.throws(()=>f.api.authenticateTransition({transition}),/private qualified selected transition/);
});


test('trusted programme policy evolves independently of unchanged selected scientific routes',async t=>{
 const f=await trustedFixture(t), originalPolicy=JSON.parse(fs.readFileSync(path.join(f.root,PROGRAMME)));
 const extra=structuredClone(originalPolicy.programs.at(-1));extra.source_profile='reviewed-fixture-policy';
 f.save(PROGRAMME,{...originalPolicy,programs:[...originalPolicy.programs,extra]});const newer=f.commit();
 const reader=new f.native.ImmutableReader(f.root,newer);
 const result=f.api.qualifyCheckpoint({reader});assert.equal(result.available,true);
 const forged=structuredClone(extra);forged.source_profile='candidate-only-unknown-producer';
 f.save(PROGRAMME,{...originalPolicy,programs:[...originalPolicy.programs,extra,forged]});const candidate=f.commit();
 f.git('checkout','-q',newer);
 const after=new f.native.ImmutableReader(f.root,candidate,{invocation:reader.invocation});
 const transition=f.api.qualifyTransition({state:result.state,reader:after});assert.equal(transition.available,true);
 assert.deepEqual(transition.changedIds,[]);
 const helper=await import(pathToFileURL(path.join(f.root,CODE[1])));
 assert.throws(()=>helper.readSupportedProgrammeAuthority(after,{preimageVersion:forged.preimage_version,
  sourceProfile:forged.source_profile,sourceCode:forged.source_executed_code,nativeCode:forged.native_executed_code}),/Unknown\/ambiguous/);
});
test('policy-route exception never permits an incomplete archived census or adjacent input drift',async t=>{
 const f=await trustedFixture(t), original=f.git('rev-parse','HEAD').toString().trim();
 const routes=JSON.parse(f.git('show',f.rootRow.routes.commit+':'+f.rootRow.routes.path));
 f.save('accepted/routes.json',routes.filter(p=>p.path!==PROGRAMME));const incomplete=f.commit();
 f.save(CATALOGUE,{version:1,kind:'accepted-selected-checkpoints-v1',
  checkpoints:[{...f.rootRow,routes:f.pin('accepted/routes.json',incomplete)}]});f.commit();
 assert.throws(()=>f.api.qualifyCheckpoint({reader:f.reader}),/Incomplete trusted present\/absent route census/);
 f.save(CATALOGUE,{version:1,kind:'accepted-selected-checkpoints-v1',
  checkpoints:[{...f.rootRow,routes:{...f.rootRow.routes,sha256:'0'.repeat(64)}}]});f.commit();
 const corruptReader=new f.native.ImmutableReader(f.root,f.selected);
 assert.throws(()=>f.api.qualifyCheckpoint({reader:corruptReader}),/Whole immutable input differs/);
 f.git('checkout','-q',original);
 f.save('data/owners.json',[{id:'B',index:1},{id:'A',index:2},{id:'C',index:3}]);const changed=f.commit();
 const reader=new f.native.ImmutableReader(f.root,changed);
 const result=f.api.qualifyCheckpoint({reader});assert.equal(result.available,false);assert.match(result.reason,/routing alternative changed/);
});


test('removed or changed trusted producer eligibility cannot silently reuse accepted policy',async t=>{
 const f=await trustedFixture(t), original=f.git('rev-parse','HEAD').toString().trim();
 const policy=JSON.parse(fs.readFileSync(path.join(f.root,PROGRAMME)));
 for(const edit of [p=>p.programs.pop(),p=>p.current_rebind_migrations.pop(),p=>{p.programs[0].source_executed_code[0].sha256='0'.repeat(64);}]){
  f.git('checkout','-q',original);const changed=structuredClone(policy);edit(changed);f.save(PROGRAMME,changed);f.commit();
  const reader=new f.native.ImmutableReader(f.root,f.selected);
  const result=f.api.qualifyCheckpoint({reader});assert.equal(result.available,false);assert.match(result.reason,/preserves accepted eligibility/);
 }
});


test('archived child custody is retained in its actual parent inventory without crossing invocations',async t=>{
 const f=await trustedFixture(t), first=f.api.qualifyCheckpoint({reader:f.reader});assert.equal(first.available,true);
 for(const p of [f.rootRow.facts,f.rootRow.certificate,f.rootRow.custody,f.rootRow.routes]){
  const actual=f.reader.inventory.get(p.commit+':'+p.path);assert.ok(actual?.whole_body_consumed);assert.equal(actual.sha256,p.sha256);
 }
 assert.ok([...f.reader.inventory.values()].some(p=>p.path===CATALOGUE&&p.whole_body_consumed));
 const secondReader=new f.native.ImmutableReader(f.root,f.selected);
 assert.notStrictEqual(secondReader.inventory,f.reader.inventory);assert.equal(secondReader.inventory.size,0);
 const second=f.api.qualifyCheckpoint({reader:secondReader});assert.equal(second.available,true);
 assert.notStrictEqual(secondReader.inventory,f.reader.inventory);
 f.api.releaseCheckpoint(first.state);assert.deepEqual(f.api.projectNativeRows({state:second.state,rows:[1]}).rows,[{y:1,runs:[[0,1,2]]}]);
});


test('archived JavaScript execution roles can evolve while same-extension scientific inputs stay pinned',async t=>{
 const f=await trustedFixture(t,{codeRoutes:true});
 fs.appendFileSync(path.join(f.root,'src/native-grid.js'),'\n// Reviewed native-only support.\n');const newer=f.commit();
 const reader=new f.native.ImmutableReader(f.root,newer);
 const qualified=f.api.qualifyCheckpoint({reader});assert.equal(qualified.available,true);
 const transition=f.api.qualifyTransition({state:qualified.state,reader});assert.equal(transition.available,true);
 // A .js suffix alone does not exempt scientific bytes from the old census.
 f.save('data/scientific.js',{fixture:'changed scientific input'});const changed=f.commit();
 const candidate=new f.native.ImmutableReader(f.root,changed,{invocation:reader.invocation});
 const rejected=f.api.qualifyTransition({state:qualified.state,reader:candidate});
 assert.equal(rejected.available,false);assert.match(rejected.reason,/route changed/);
 fs.appendFileSync(path.join(f.root,'src/native-grid.js'),'\n// Uncommitted executable drift.\n');
 const dirty=new f.native.ImmutableReader(f.root,newer);
 assert.throws(()=>f.api.qualifyCheckpoint({reader:dirty}),/changed executing checkpoint method/);
 f.api.releaseCheckpoint(qualified.state);
});

test('actual appended authority survives complete checks, a subsequent transition and original native projection',async t=>{
 const f=await trustedFixture(t,{nativeAppend:true}),baseline=f.api.qualifyCheckpoint({reader:f.reader});
 const next=await appendNativeAuthority(f),reader=new f.native.ImmutableReader(f.root,next.candidate,{invocation:f.reader.invocation});
 const transition=f.api.qualifyTransition({state:baseline.state,reader});
 assert.equal(transition.available,true);assert.deepEqual(transition.changedIds,['A']);assert.deepEqual(transition.changedNativeRows,[next.y]);
 assert.deepEqual(transition.candidate.ledger.rows,next.ledger.rows);assert.deepEqual(transition.candidate.patch.rows,next.patch.rows);
 assert.deepEqual(transition.candidate.additions.at(-1).native_rows,next.proof.original_ledger.rows[0].native_rows);
 assert.deepEqual(baseline.state.ledger.rows,f.ledger.rows);assert(Object.isFrozen(transition.candidate));
 f.save('later-unrelated.json',{later:true});const later=f.commit();
 const laterReader=new f.native.ImmutableReader(f.root,later,{invocation:f.reader.invocation});
 const again=f.api.qualifyTransition({state:transition.candidate,reader:laterReader});
 assert.equal(again.available,true);assert.deepEqual(again.changedIds,[]);assert.deepEqual(again.changedNativeRows,[]);
 assert.deepEqual(again.candidate.patch.rows,next.patch.rows);
 const projected=f.api.projectNativeRows({state:again.candidate,rows:[next.y]});
 assert.deepEqual(projected.rows,[{y:next.y,runs:[]}]);
 assert.equal(f.api.checkpointRouteCensus({transition:again}).candidate_commit,later);
 f.api.releaseCheckpoint(baseline.state);
});

for(const [name,options,expected] of [
 ['omitted appended scope',{mutateLedger:l=>{l.rows=l.rows.filter(p=>!p.component_id.startsWith('source-target:'));}},/omitted\/invented complete appended ledger scope/],
 ['invented appended exception',{mutateLedger:(l,p,e)=>{l.rows.push({component_id:'source-target:invented',disposition:'rejected',reason:'invented',authority_sha256:e.authority_sha256});}},/omitted\/invented complete appended ledger scope/],
 ['changed appended literal',{mutateLedger:l=>{l.rows.at(-1).source_receipt_sha256='0'.repeat(64);}},/changed original appended primitive or exception/],
 ['second authority without its complete original row',{duplicateAuthority:true},/omitted\/invented complete appended ledger scope/],
 ['changed complete native contract',{mutateEvidence:e=>{e.native_contract.coordinateBits++;}},/native contract or complete original source denominator/],
 ['changed original authority base',{mutateEvidence:e=>{e.base_reference={...e.base_reference,footprints_sha256:'0'.repeat(64)};}},/different selected base/],
 ['changed full source denominator',{mutateLedger:l=>{l.parent_inventory={...l.parent_inventory,components:3};}},/original source\/scope denominator/],
 ['changed old exception',{mutateLedger:l=>{l.rows.find(p=>p.component_id==='rejected').reason='changed old exception';}},/Old complete ledger primitive/],
 ['cumulative patch reassignment',{mutatePatch:p=>{p.rows.at(-1).runs[0][2]=2;}},/omitted, invented or reassigned original native intervals/]
])test('real appended authority refuses '+name,async t=>{
 const f=await trustedFixture(t,{nativeAppend:true}),{state}=f.api.qualifyCheckpoint({reader:f.reader});
 const next=await appendNativeAuthority(f,options),reader=new f.native.ImmutableReader(f.root,next.candidate,{invocation:f.reader.invocation});
 assert.throws(()=>f.api.qualifyTransition({state,reader}),expected);
 assert.deepEqual(state.ledger.rows,f.ledger.rows);f.api.releaseCheckpoint(state);
});

test('failed complete literal check preserves authenticated baseline and permits a corrected retry',async t=>{
 const f=await trustedFixture(t,{nativeAppend:true}),{state}=f.api.qualifyCheckpoint({reader:f.reader});
 const next=await appendNativeAuthority(f,{mutateLedger:l=>{l.rows.at(-1).source_receipt_sha256='0'.repeat(64);}});
 const reader=new f.native.ImmutableReader(f.root,next.candidate,{invocation:f.reader.invocation});
 assert.throws(()=>f.api.qualifyTransition({state,reader}),/changed original appended primitive/);
 assert.deepEqual(state.ledger.rows,f.ledger.rows);
 assert.deepEqual(f.api.projectSourceFeatures({state,ids:[]}).features,[]);
 const recovered=await appendNativeAuthority(f,{name:'recovered'}),retryReader=new f.native.ImmutableReader(f.root,recovered.candidate,{invocation:f.reader.invocation});
 assert.equal(f.api.qualifyTransition({state,reader:retryReader}).available,true);
 f.api.releaseCheckpoint(state);
});

test('an unconsumed logical source shadowed by the exact accepted override does not replay science',async t=>{
 const f=await trustedFixture(t,{sourceOverride:true});
 f.save('data/source.json',{unselected:'different ordinary source'});const baseline=f.commit();
 const reader=new f.native.ImmutableReader(f.root,baseline),qualified=f.api.qualifyCheckpoint({reader});
 assert.equal(qualified.available,true);
 f.save('data/source.json',{unselected:'changed again'});const candidate=f.commit();
 const after=new f.native.ImmutableReader(f.root,candidate,{invocation:reader.invocation});
 const transition=f.api.qualifyTransition({state:qualified.state,reader:after});
 assert.equal(transition.available,true);assert.deepEqual(transition.changedNativeRows,[]);
 const census=f.api.checkpointRouteCensus({transition});
 assert.equal(census.routes.find(p=>p.path==='data/source.json').tree,f.git('ls-tree','-z',candidate,'--','data/source.json').toString());
 assert.equal(f.api.projectSourceFeatures({state:transition.candidate,ids:['A']}).features[0].id,'A');
 assert.ok(![...after.inventory.values()].some(p=>p.path==='data/source.json'));
 assert.ok(![...after.inventory.values()].some(p=>p.path.startsWith('data/native/')),'Unchanged rows do not acquire native bodies');
 f.api.releaseCheckpoint(qualified.state);
});

test('a shadowed logical path that was also a physical input remains protected',async t=>{
 const f=await trustedFixture(t,{sourceOverride:true,physicalLogicalSource:true});
 const qualified=f.api.qualifyCheckpoint({reader:f.reader});assert.equal(qualified.available,true);
 f.save('data/source.json',{changed:'actually consumed elsewhere'});const candidate=f.commit();
 const after=new f.native.ImmutableReader(f.root,candidate,{invocation:f.reader.invocation});
 const transition=f.api.qualifyTransition({state:qualified.state,reader:after});
 assert.equal(transition.available,false);assert.match(transition.reason,/present\/absent route changed/);
 f.api.releaseCheckpoint(qualified.state);
});

test('a wrong override logical mapping cannot exempt an ordinary source route',async t=>{
 const f=await trustedFixture(t,{sourceOverride:true,overrideLogicalPath:'data/somewhere-else.json'});
 f.save('data/source.json',{changed:'unmatched logical path'});const candidate=f.commit();
 const result=f.api.qualifyCheckpoint({reader:new f.native.ImmutableReader(f.root,candidate)});
 assert.equal(result.available,false);assert.match(result.reason,/routing alternative changed/);
});

test('physical override bytes and native source routes remain binding',async t=>{
 for(const name of ['data/selected-source.json.gz','data/native/runs.bin.gz']){
  const f=await trustedFixture(t,{sourceOverride:true}),qualified=f.api.qualifyCheckpoint({reader:f.reader});
  f.save(name,Buffer.from('different physical bytes'));const candidate=f.commit();
  const after=new f.native.ImmutableReader(f.root,candidate,{invocation:f.reader.invocation});
  const transition=f.api.qualifyTransition({state:qualified.state,reader:after});
  assert.equal(transition.available,false);assert.match(transition.reason,/present\/absent route changed/);
  f.api.releaseCheckpoint(qualified.state);
 }
});

test('new actual physical use of a shadowed source revokes its next-transition exemption',async t=>{
 const f=await trustedFixture(t,{nativeAppend:true,sourceOverride:true});
 const qualified=f.api.qualifyCheckpoint({reader:f.reader});assert.equal(qualified.available,true);
 const appended=await appendNativeAuthority(f,{membershipPath:'data/source.json'});
 const reader=new f.native.ImmutableReader(f.root,appended.candidate,{invocation:f.reader.invocation});
 const transition=f.api.qualifyTransition({state:qualified.state,reader});assert.equal(transition.available,true);
 assert.ok([...reader.inventory.values()].some(p=>p.path==='data/source.json'&&p.whole_body_consumed));
 const census=f.api.checkpointRouteCensus({transition});
 assert.equal(census.routes.find(p=>p.path==='data/source.json').tree,f.git('ls-tree','-z',appended.candidate,'--','data/source.json').toString());
 f.save('data/source.json',{changed:'now a real physical dependency'});const next=f.commit();
 const after=new f.native.ImmutableReader(f.root,next,{invocation:f.reader.invocation});
 const rejected=f.api.qualifyTransition({state:transition.candidate,reader:after});
 assert.equal(rejected.available,false);assert.match(rejected.reason,/present\/absent route changed/);
 f.api.releaseCheckpoint(qualified.state);
});


test('checkpoint admission, transition and census share one complete route tree',async t=>{
 const f=await trustedFixture(t),git=f.reader.git.bind(f.reader),calls=[],layers=[];
 f.reader.git=(...args)=>{calls.push(args);return git(...args);};
 const readPinned=f.reader.readPinned.bind(f.reader);
 f.reader.readPinned=pins=>{layers.push(pins.map(p=>p.path));return readPinned(pins);};
 const qualified=f.api.qualifyCheckpoint({reader:f.reader});assert.equal(qualified.available,true);
 const transition=f.api.qualifyTransition({state:qualified.state,reader:f.reader});assert.equal(transition.available,true);
 const census=f.api.checkpointRouteCensus({transition});
 for(const row of census.routes)assert.equal(row.tree,f.git('ls-tree','-z',f.selected,'--',row.path).toString());
 assert.equal(calls.filter(args=>args[0]==='ls-tree'&&args[1]==='-rtz').length,1);
 assert.deepEqual(layers.slice(0,4),[
  ['data/registry.json','data/ledger.json','data/patch.json','data/envelope.json'],
  ['original/binding.json'],['original/publication.json'],['original/patch-one.json']]);
 f.api.releaseCheckpoint(qualified.state);
});

test('real checkpoint admission cannot accept a corrupted known-pin body batch',async t=>{
 const f=await trustedFixture(t),batch=f.reader.gitBatch.bind(f.reader);let altered=false;
 f.reader.gitBatch=(args,...rest)=>{
  const output=batch(args,...rest);
  if(args[1]==='--batch'&&!altered){altered=true;output[output.indexOf(10)+1]^=1;}
  return output;
 };
 assert.throws(()=>f.api.qualifyCheckpoint({reader:f.reader}),/Whole immutable input differs/);
 assert.equal(altered,true,'The actual admitted body transport must execute');
});

test('checkpoint route comparison refuses disappeared files, directories, symlinks and executable-mode drift',async t=>{
 const f=await trustedFixture(t),original=fs.readFileSync(path.join(f.root,'data/source.json'));
 const file=path.join(f.root,'data/source.json');
 for(const kind of ['absent','directory','symlink','executable']){
  fs.rmSync(file,{recursive:true,force:true});
  if(kind==='directory'){fs.mkdirSync(file);fs.writeFileSync(path.join(file,'child'),'present directory');}
  if(kind==='symlink')fs.symlinkSync('owners.json',file);
  if(kind==='executable'){fs.writeFileSync(file,original);fs.chmodSync(file,0o755);}
  const candidate=f.commit(),reader=new f.native.ImmutableReader(f.root,candidate);
  const result=f.api.qualifyCheckpoint({reader});assert.equal(result.available,false,kind);
  assert.match(result.reason,/routing alternative changed/);
 }
});

// Scalar consumers must exercise a real promisor: a plain missing commit does
// not reveal Git's implicit remote fetch before the exact current-alias path.
function scalarPromisor(f,{populated=false}={}) {
 const executable=execFileSync('which',['git'],{encoding:'utf8'}).trim(),remote=path.join(f.root,'.git','promisor.git');
 if(populated)execFileSync(executable,['clone','--bare','--quiet','--no-local',f.root,remote]);
 else execFileSync(executable,['init','--bare','--quiet',remote]);
 for(const [key,value]of [['uploadpack.allowAnySHA1InWant','true'],['uploadpack.allowFilter','true']])
  execFileSync(executable,['--git-dir',remote,'config',key,value]);
 f.git('config','extensions.partialClone','origin');f.git('config','remote.origin.url',remote);
 f.git('config','remote.origin.promisor','true');f.git('config','remote.origin.partialclonefilter','blob:none');
 const trace=path.join(f.root,'.git','scalar.trace'),wrapper=path.join(f.root,'.git','scalar-git');
 fs.writeFileSync(wrapper,`#!/bin/sh\nGIT_NO_LAZY_FETCH=0 GIT_TRACE=${JSON.stringify(trace)} exec ${JSON.stringify(executable)} "$@"\n`,{mode:0o755});
 const reader=(version=f.selected)=>new f.native.ImmutableReader(f.root,version,{gitExecutable:wrapper});
 const readSource=(p,r=reader())=>f.native.SelectedGeometrySources.prototype.readPinned.call({reader:r,
  checkPin:f.native.SelectedGeometrySources.prototype.checkPin},p);
 const tracing=()=>fs.existsSync(trace)?fs.readFileSync(trace,'utf8'):'';
 return {reader,readSource,trace,tracing,remote,executable,wrapper};
}
const remoteAttempt=/fetch .*origin|upload-pack/;

test('scalar source aliases use no promisor transport and still reject incomplete or changed pins',async t=>{
 const f=await trustedFixture(t),p={...f.pin('data/source.json',f.selected),commit:'77be56dd849d1351b82f0e79d7d306c1080b2562'},s=scalarPromisor(f);
 assert.deepEqual(s.readSource(p),f.git('show',f.selected+':'+p.path));
 for(const changed of [{...p,mode:'100755'},{...p,bytes:p.bytes+1},{...p,git_blob_oid:'f'.repeat(40)},
  {...p,sha256:'0'.repeat(64)},{...p,path:'missing.json'}])
  assert.throws(()=>s.readSource(changed),/Incomplete whole selected source pin|original mode\/OID\/body differs|Whole immutable input differs|Require whole ordinary/);
 assert.doesNotMatch(s.tracing(),remoteAttempt);
});

test('scalar local originals take precedence and their missing paths never fall back',async t=>{
 const f=await trustedFixture(t),p=f.pin('data/source.json',f.selected),s=scalarPromisor(f);
 f.save(p.path,{different:true});f.save('new.json',{new:true});const current=f.commit();
 assert.deepEqual(s.readSource(p,s.reader(current)),f.git('show',p.commit+':'+p.path));
 assert.throws(()=>s.readSource({...f.pin(p.path,current),commit:p.commit},s.reader(current)),/original mode\/OID\/body differs/);
 assert.throws(()=>s.readSource({...f.pin('new.json',current),commit:p.commit},s.reader(current)),/Require whole ordinary/);
 assert.doesNotMatch(s.tracing(),remoteAttempt);
});

test('scalar availability rechecks a remote-only original after explicit acquisition',async t=>{
 const f=await trustedFixture(t),s=scalarPromisor(f,{populated:true});
 const remote=(args,input)=>execFileSync(s.executable,['--git-dir',s.remote,...args],{input,encoding:'utf8'}).trim();
 const blob=remote(['hash-object','-w','--stdin'],'different original');
 const dir=remote(['mktree'],`100644 blob ${blob}\tsource.json\n`),tree=remote(['mktree'],`040000 tree ${dir}\tdata\n`);
 const original=remote(['-c','user.name=Scalar test','-c','user.email=scalar@example.invalid','commit-tree',tree],'Remote original\n');
 const p={...f.pin('data/source.json',f.selected),commit:original},reader=s.reader();
 assert.deepEqual(s.readSource(p,reader),f.git('show',f.selected+':'+p.path));
 assert.doesNotMatch(s.tracing(),remoteAttempt);assert.equal(reader.inventory.has(original+':'+p.path),false);
 f.git('fetch','--quiet','--no-tags',s.remote,original);
 assert.throws(()=>s.readSource(p,reader),/original mode\/OID\/body differs/);
});

for(const populated of [true,false])test('scalar actual body acquisition remains '+(populated?'authenticated':'a failure, never an alias fallback'),async t=>{
 const f=await trustedFixture(t),p=f.pin('data/source.json',f.selected),expected=f.git('show',p.commit+':'+p.path),s=scalarPromisor(f,{populated});
 fs.unlinkSync(path.join(f.root,'.git','objects',p.git_blob_oid.slice(0,2),p.git_blob_oid.slice(2)));
 if(populated){assert.deepEqual(s.readSource(p),expected);assert.throws(()=>s.readSource({...p,sha256:'0'.repeat(64)}),/Whole immutable input differs/);}
 else assert.throws(()=>s.readSource(p),/Command failed|Require whole ordinary/);
 assert.match(s.tracing(),remoteAttempt);
});

test('complete checkpoint qualification uses exact rebind aliases without implicit promisor fetches',async t=>{
 const f=await trustedFixture(t),certificate=f.ledger.current_rebind,body=JSON.parse(f.git('show',certificate.commit+':'+certificate.path));
 const commits=new Set([certificate.commit,...['request','facts','publication','operating','result'].map(k=>body[k].commit)]);
 const s=scalarPromisor(f);
 for(const commit of commits)fs.unlinkSync(path.join(f.root,'.git','objects',commit.slice(0,2),commit.slice(2)));
 const result=f.api.qualifyCheckpoint({reader:s.reader()});
 assert.equal(result.available,true);assert.equal(result.state.ledger.rows.length,2);
 assert.deepEqual(f.api.projectNativeRows({state:result.state,rows:[1]}).rows,[{y:1,runs:[[0,1,2]]}]);
 assert.doesNotMatch(s.tracing(),remoteAttempt);
 f.api.releaseCheckpoint(result.state);
});

test('complete native authority authenticates retained source aliases without fetching unavailable originals',async t=>{
 const f=await trustedFixture(t,{nativeAppend:true}),next=await appendNativeAuthority(f);
 const {readRetainedRegistryAuthority}=await import(pathToFileURL(path.join(f.root,CODE[1])));
 const binding=JSON.parse(f.git('show',next.entry.source_authority.commit+':'+next.entry.source_authority.path));
 const evidence=JSON.parse(f.git('show',binding.source_evidence.commit+':'+binding.source_evidence.path));
 const commits=new Set([next.entry.source_authority.commit,binding.source_evidence.commit,evidence.catalogue.commit]);
 const s=scalarPromisor(f);
 for(const commit of commits)fs.unlinkSync(path.join(f.root,'.git','objects',commit.slice(0,2),commit.slice(2)));
 const proof=readRetainedRegistryAuthority(s.reader(next.candidate),next.entry);
 assert.deepEqual(proof.original_ledger,next.proof.original_ledger);
 assert.deepEqual(proof.native_proof.native_patches,next.proof.native_proof.native_patches);
 assert.doesNotMatch(s.tracing(),remoteAttempt);
});

function miniatureInventory(root,prefix=''){
 return fs.readdirSync(path.join(root,prefix),{withFileTypes:true}).flatMap(entry=>{
  const name=path.join(prefix,entry.name),file=path.join(root,name),stat=fs.lstatSync(file);
  assert.equal(stat.isSymbolicLink(),false,`No shared symlink: ${name}`);
  if(entry.isDirectory())return miniatureInventory(root,name);
  assert.equal(stat.isFile(),true,`Ordinary copied file: ${name}`);
  return [{name,mode:stat.mode,bytes:fs.readFileSync(file),device:stat.dev,inode:stat.ino}];
 }).sort((a,b)=>a.name.localeCompare(b.name));
}
const miniatureBytes=inventory=>inventory.map(({device,inode,...file})=>file);

for(const options of [{},{nativeAppend:true}])test(`miniature seed copies isolate all files and mutable state ${JSON.stringify(options)}`,async t=>{
 const [a,b]=await Promise.all([trustedFixture(t,options),trustedFixture(t,options)]);
 const original=miniatureInventory(a.root),other=miniatureInventory(b.root);
 assert.deepEqual(miniatureBytes(original),miniatureBytes(other));
 assert.ok(original.some(file=>/^\.git\/objects\/[a-f0-9]{2}\/[a-f0-9]{38}$/.test(file.name)));
 assert.equal(fs.existsSync(path.join(a.root,'.git/objects/info/alternates')),false);
 for(let i=0;i<original.length;i++)
  assert.notEqual(`${original[i].device}:${original[i].inode}`,`${other[i].device}:${other[i].inode}`,original[i].name);
 for(const key of ['api','native','reader','ledger','patch','sidecar','envelope','selection','rootRow','manifest','features','registry'])
  assert.notStrictEqual(a[key],b[key],key);
 assert.notStrictEqual(a.native.ImmutableReader,b.native.ImmutableReader);
 assert.notStrictEqual(a.reader.invocation,b.reader.invocation);
 const left=a.api.qualifyCheckpoint({reader:a.reader}),right=b.api.qualifyCheckpoint({reader:b.reader});
 assert.equal(left.available,true);assert.equal(right.available,true);
 assert.throws(()=>b.api.projectSourceFeatures({state:left.state,ids:['A']}),/private qualified/);
 assert.throws(()=>a.api.projectNativeRows({state:right.state,rows:[1]}),/private qualified/);
 a.api.releaseCheckpoint(left.state);
 assert.throws(()=>a.api.projectSourceFeatures({state:left.state,ids:['A']}),/private qualified/);
 assert.equal(b.api.projectSourceFeatures({state:right.state,ids:['A']}).features[0].id,'A');
 b.api.releaseCheckpoint(right.state);
 const originalData=structuredClone(Object.fromEntries(['ledger','patch','sidecar','envelope','selection','rootRow','manifest','features','registry'].map(key=>[key,b[key]])));
 a.features[0].properties.id='only the first consumer';a.ledger.rows[0].target_id='wrong owner';
 a.rootRow.certificate.decoded_sha256='0'.repeat(64);a.manifest.parts[0].sha256='0'.repeat(64);
 const object=original.find(file=>/^\.git\/objects\/[a-f0-9]{2}\/[a-f0-9]{38}$/.test(file.name));
 fs.chmodSync(path.join(a.root,object.name),0o644);
 fs.writeFileSync(path.join(a.root,object.name),'corrupt only the first object');
 fs.appendFileSync(path.join(a.root,'.git/config'),'\n# first consumer only\n');
 a.save('data/source.json',{changed:'first consumer only'});
 const c=await trustedFixture(t,options),third=miniatureInventory(c.root);
 assert.deepEqual(miniatureBytes(miniatureInventory(b.root)),miniatureBytes(other));
 assert.deepEqual(miniatureBytes(third),miniatureBytes(original),'The private seed remains pristine');
 for(let i=0;i<third.length;i++)
  assert.equal(new Set([original[i],other[i],third[i]].map(file=>`${file.device}:${file.inode}`)).size,3,third[i].name);
 for(const key of Object.keys(originalData)){
  assert.deepEqual(b[key],originalData[key],`Second metadata: ${key}`);
  assert.deepEqual(c[key],originalData[key],`Fresh metadata: ${key}`);
 }
});

test('miniature seed catalogue forgery in the first consumer cannot poison a later consumer',async t=>{
 const first=await trustedFixture(t);
 first.rootRow.certificate.decoded_sha256='0'.repeat(64);
 first.save(CATALOGUE,{version:1,kind:'accepted-selected-checkpoints-v1',checkpoints:[first.rootRow]});first.commit();
 assert.throws(()=>first.api.qualifyCheckpoint({reader:first.reader}),/decoded output is corrupt/);
 const later=await trustedFixture(t),qualified=later.api.qualifyCheckpoint({reader:later.reader});
 assert.equal(qualified.available,true);
 assert.equal(later.api.projectSourceFeatures({state:qualified.state,ids:['A']}).features[0].id,'A');
 later.api.releaseCheckpoint(qualified.state);
});

test('miniature seed keys retain every fixture option and normalize default option ordering',async t=>{
 const configurations=[{},{incompleteNative:true},{codeRoutes:true},{nativeAppend:true},{sourceOverride:true},
  {sourceOverride:true,physicalLogicalSource:true},{sourceOverride:true,overrideLogicalPath:'data/somewhere-else.json'},
  {nativeAppend:true,sourceOverride:true}];
 const heads=[];
 for(const options of configurations){
  const first=await trustedFixture(t,options);
  const reversed=Object.fromEntries(Object.entries(options).reverse());
  const again=await trustedFixture(t,{overrideLogicalPath:'data/source.json',physicalLogicalSource:false,
   sourceOverride:false,nativeAppend:false,codeRoutes:false,incompleteNative:false,...reversed});
  const head=first.git('rev-parse','HEAD').toString().trim();heads.push(head);
  assert.equal(again.git('rev-parse','HEAD').toString().trim(),head);
  assert.deepEqual(again.rootRow,first.rootRow);
 }
 assert.equal(new Set(heads).size,configurations.length,'Distinct option effects must not share a seed');
});
