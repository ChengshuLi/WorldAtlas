import {nativeLiteral} from './helpers/native-literal.mjs';
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {pathToFileURL} from 'node:url';
import {nativeRowLatitudes} from '../src/native-grid.js';
import {valueSha,mergeCompletedNativePatches} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
import {deriveCoordinateDelta,projectSourceFeatures,projectNativeRows,qualifyTransition} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-checkpoint.mjs';
import {MODULE,PROGRAMME,CATALOGUE,CODE,polygon,feature,fixtures,addition,trustedFixture,appendNativeAuthority} from './fixtures/selected-checkpoint.mjs';

test('serialized lookalikes cannot mint state or projectors',async ()=>{
 const state={version:1,kind:'verified-selected-state-v1',certificate:fixtures().certificate};
 assert.throws(()=>projectSourceFeatures({state,ids:['A']}),/private qualified/);
 assert.throws(()=>projectNativeRows({state,rows:[0]}),/private qualified/);
 await assert.rejects(async()=>(await qualifyTransition({state,reader:{}})),/private qualified/);
});
test('append arithmetic retains all owners and authenticates changed literal additions',async ()=>{
 const {certificate}=fixtures(), a=addition('a','A',1,certificate.entries[0][7],1.05), b=addition('b','C',3,certificate.entries[2][7],1.1);
 const result=deriveCoordinateDelta({certificate,oldAdditions:[],additions:[a,b],selection:{next:true}});
 assert.equal(result.certificate.entries.length,3);
 assert.strictEqual(result.certificate.entries[1],certificate.entries[1]);
 assert.deepEqual(result.changedIds,['A','C']);
 assert.equal(result.certificate.entries[0][8],valueSha({base_geometry_sha256:certificate.entries[0][7],additions:[a]}));
 assert.deepEqual(result.certificate.entries[0][9],[[0,0,1.25,.2]]);
 assert.deepEqual(result.certificate.binding.selection,{next:true});
});
test('delta arithmetic rejects omitted old primitives, same-count owner swaps and stale base hashes',async ()=>{
 const {certificate}=fixtures(), old=addition('old','A',1,certificate.entries[0][7],.3);
 const before=deriveCoordinateDelta({certificate,oldAdditions:[],additions:[old],selection:{}}).certificate;
 assert.throws(()=>deriveCoordinateDelta({certificate:before,oldAdditions:[old],additions:[],selection:{}}),/Old effective/);
 assert.throws(()=>deriveCoordinateDelta({certificate:before,oldAdditions:[old],additions:[{...old,pixelIndex:2}],selection:{}}),/Old effective/);
 assert.throws(()=>deriveCoordinateDelta({certificate,oldAdditions:[],additions:[{...old,base_geometry_sha256:'0'.repeat(64)}],selection:{}}),/stale base/);
 assert.throws(()=>deriveCoordinateDelta({certificate,oldAdditions:[],additions:[{...old,geometry:polygon(20)}],selection:{}}),/changed geometry/);
 assert.throws(()=>deriveCoordinateDelta({certificate,oldAdditions:[],additions:[old,old],selection:{}}),/Duplicate/);
});

test('native-only append uses exact native bounds and identity without an addition polygon',async ()=>{
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
 const f=await trustedFixture(t), result=(await f.api.qualifyCheckpoint({reader:f.reader}));
 assert.equal(result.available,true);const state=result.state;
 assert.equal(state.ledger.rows.length,2);assert.equal(state.ledger.rows.at(1).disposition,'rejected');
 const sources=f.api.projectSourceFeatures({state,ids:['A','B']});
 assert.deepEqual(sources.features.map(p=>p.id),['A','B']);assert.equal(sources.inverse.length,2);
 const native=f.api.projectNativeRows({state,rows:[1]});
 assert.deepEqual(nativeLiteral(native.rows),[{y:1,runs:[[0,1,2]]}]);assert.deepEqual(native.acquired_rows,[]);
 const fresh=f.api.projectNativeRows({state,rows:[0,1,2,3]});
 assert.deepEqual(nativeLiteral(fresh.rows),[{y:0,runs:[[0,1,1]]},{y:1,runs:[[0,1,2]]},{y:2,runs:[[1,2,3]]},{y:3,runs:[]}]);
 assert.deepEqual(fresh.acquired_rows,[0,2,3]);assert.ok(fresh.custody.new_whole_inputs.length>=2);
 assert.throws(()=>f.api.projectNativeRows({state:JSON.parse(JSON.stringify(state)),rows:[1]}),/private qualified/);
 f.api.releaseCheckpoint(state);assert.throws(()=>f.api.projectSourceFeatures({state,ids:['A']}),/private qualified/);
});
test('unchanged actual selection at a newer commit reuses the original accepted checkpoint',async t=>{
 const f=await trustedFixture(t);f.save('unrelated.json',{new:true});const newer=f.commit();
 const reader=new f.native.ImmutableReader(f.root,newer);
 const result=(await f.api.qualifyCheckpoint({reader}));assert.equal(result.available,true);
 assert.equal(result.state.selected_commit,newer);assert.equal(result.state.accepted_execution.historical_selected_commit,f.selected);
 const transition=(await f.api.qualifyTransition({state:result.state,reader}));assert.equal(transition.available,true);
 assert.deepEqual(transition.changedIds,[]);assert.deepEqual(transition.changedNativeRows,[]);
 assert.deepEqual(transition.changedIds,[]);
});
test('committed qualifier edits need no manual catalogue fingerprint refresh',async t=>{
 const f=await trustedFixture(t), catalogue=fs.readFileSync(path.join(f.root,CATALOGUE));
 fs.appendFileSync(path.join(f.root,MODULE),'\n// reviewed non-scientific change\n');const newer=f.commit();
 const reader=new f.native.ImmutableReader(f.root,newer);
 assert.equal((await f.api.qualifyCheckpoint({reader})).available,true);
 assert.deepEqual(fs.readFileSync(path.join(f.root,CATALOGUE)),catalogue);
});
test('changed same-count source owners cannot reuse accepted custody',async t=>{
 const f=await trustedFixture(t);f.save('data/source.json',{type:'FeatureCollection',features:[feature('B',0),feature('A',1),feature('C',5)]});const candidate=f.commit();
 const reader=new f.native.ImmutableReader(f.root,candidate);
 const result=(await f.api.qualifyCheckpoint({reader}));assert.equal(result.available,false);assert.match(result.reason,/routing alternative changed/);
});
test('corrupt accepted products and dirty executing code are rejected rather than treated as no change',async t=>{
 const f=await trustedFixture(t);f.rootRow.certificate.decoded_sha256='0'.repeat(64);
 f.save(CATALOGUE,{version:1,kind:'accepted-selected-checkpoints-v1',checkpoints:[f.rootRow]});f.commit();
 await assert.rejects(async()=>(await f.api.qualifyCheckpoint({reader:f.reader})),/decoded output is corrupt/);
 f.save(MODULE,Buffer.concat([fs.readFileSync(path.join(f.root,MODULE)),Buffer.from('\n// drift\n')]));
 const reader=new f.native.ImmutableReader(f.root,f.selected);
 await assert.rejects(async()=>(await f.api.qualifyCheckpoint({reader})),/changed executing checkpoint method/);
});

test('native projection rejects an incomplete complete row partition despite matching encoded and decoded hashes',async t=>{
 const f=await trustedFixture(t,{incompleteNative:true}),result=(await f.api.qualifyCheckpoint({reader:f.reader}));
 assert.equal(result.available,true);
 assert.throws(()=>f.api.projectNativeRows({state:result.state,rows:[2]}),/row partition omitted/);
});
test('a forged candidate-selected checkpoint catalogue cannot replace trusted execution authority',async t=>{
 const f=await trustedFixture(t);const original=f.git('rev-parse','HEAD').toString().trim();
 f.save(CATALOGUE,{version:1,kind:'accepted-selected-checkpoints-v1',checkpoints:[]});const candidate=f.commit();
 f.git('checkout','-q',original);
 const reader=new f.native.ImmutableReader(f.root,candidate);
 assert.equal((await f.api.qualifyCheckpoint({reader})).available,true);
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
 const f=await trustedFixture(t), result=(await f.api.qualifyCheckpoint({reader:f.reader}));
 const ledger={...f.ledger,scope_ids:['old'],rows:[f.ledger.rows[0]]};
 const candidate=candidateProducts(f,{ledger});
 const reader=new f.native.ImmutableReader(f.root,candidate,{invocation:f.reader.invocation});
 await assert.rejects(async()=>(await f.api.qualifyTransition({state:result.state,reader})),/Old complete ledger/);
 assert.deepEqual(nativeLiteral(f.api.projectNativeRows({state:result.state,rows:[1]}).rows),[{y:1,runs:[[0,1,2]]}]);
});
test('actual transition rejects same-count changed native ownership without reacquiring original science',async t=>{
 const f=await trustedFixture(t), result=(await f.api.qualifyCheckpoint({reader:f.reader}));
 const candidate=candidateProducts(f,{patch:{...f.patch,rows:[{y:1,runs:[[2,3,2]]}]}});
 const reader=new f.native.ImmutableReader(f.root,candidate,{invocation:f.reader.invocation});
 await assert.rejects(async()=>(await f.api.qualifyTransition({state:result.state,reader})),/omitted, invented or reassigned/);
});
test('actual transition refuses a stale base and preserves the usable baseline for candidate-only cold validation',async t=>{
 const f=await trustedFixture(t), result=(await f.api.qualifyCheckpoint({reader:f.reader}));
 f.save('candidate/sidecar.json',{...f.sidecar,base_selection:{...f.sidecar.base_selection,release_id:'geography:new'}});const a=f.commit(),p=f.pin('candidate/sidecar.json',a);
 f.save('data/ownership-selection.json',{...f.selection,release_id:'geography:new',additive_release:{path:p.path,bytes:p.bytes,sha256:p.sha256}});const candidate=f.commit();
 const reader=new f.native.ImmutableReader(f.root,candidate,{invocation:f.reader.invocation});
 const transition=(await f.api.qualifyTransition({state:result.state,reader}));
 assert.equal(transition.available,false);assert.equal(transition.cold,'candidate');assert.strictEqual(transition.baseline,result.state);
});

test('private source reuse snapshots exact caller scope and rejects altered projections',async t=>{
 const f=await trustedFixture(t),{state}=(await f.api.qualifyCheckpoint({reader:f.reader}));
 const ids=['A'],projection=f.api.projectSourceFeatures({state,ids});
 ids[0]='B';assert.throws(()=>f.api.projectSourceFeatures({state,ids:['B'],reuse:projection}),/incomplete source projection reuse/);
 const reused=f.api.projectSourceFeatures({state,ids:['A'],reuse:projection});
 assert.equal(reused.features[0].id,'A');
 assert.throws(()=>f.api.projectSourceFeatures({state,ids:['A'],reuse:{...projection}}),/source projection reuse/);
 f.api.releaseCheckpoint(state);
});test('fast selection admission rejects unknown patch fields and malformed complete effective references',async t=>{
 const f=await trustedFixture(t),{state}=(await f.api.qualifyCheckpoint({reader:f.reader}));
 const candidate=candidateProducts(f,{patch:{...f.patch,unexpected_permission:true}});
 const reader=new f.native.ImmutableReader(f.root,candidate,{invocation:f.reader.invocation});
 await assert.rejects(async()=>(await f.api.qualifyTransition({state,reader})),/complete native patch schema/);
});

test('an unchanged accepted current-rebind proof cannot excuse a coherently repinned omitted target roster',async t=>{
 const f=await trustedFixture(t),{state}=(await f.api.qualifyCheckpoint({reader:f.reader}));
 const candidate=candidateProducts(f,{ledger:{...f.ledger,current_targets:[]}});
 const reader=new f.native.ImmutableReader(f.root,candidate,{invocation:f.reader.invocation});
 await assert.rejects(async()=>(await f.api.qualifyTransition({state,reader})),/Ledger complete current target roster differs/);
});
test('coherently copied malformed geography references still fail exact fast-path admission',async t=>{
 const f=await trustedFixture(t),{state}=(await f.api.qualifyCheckpoint({reader:f.reader}));
 const effective={...f.patch.effective_reference};delete effective.id;
 f.envelope={...f.envelope,effective_reference:effective};
 const candidate=candidateProducts(f,{patch:{...f.patch,effective_reference:effective}});
 const reader=new f.native.ImmutableReader(f.root,candidate,{invocation:f.reader.invocation});
 await assert.rejects(async()=>(await f.api.qualifyTransition({state,reader})),/complete effective reference/);
});


test('consumer admission authenticates the private complete transition rather than a forged scope wrapper',async t=>{
 const f=await trustedFixture(t),{state}=(await f.api.qualifyCheckpoint({reader:f.reader}));
 const reader=new f.native.ImmutableReader(f.root,f.selected,{invocation:f.reader.invocation});
 const transition=(await f.api.qualifyTransition({state,reader}));
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
 const result=(await f.api.qualifyCheckpoint({reader}));assert.equal(result.available,true);
 const forged=structuredClone(extra);forged.source_profile='candidate-only-unknown-producer';
 f.save(PROGRAMME,{...originalPolicy,programs:[...originalPolicy.programs,extra,forged]});const candidate=f.commit();
 f.git('checkout','-q',newer);
 const after=new f.native.ImmutableReader(f.root,candidate,{invocation:reader.invocation});
 const transition=(await f.api.qualifyTransition({state:result.state,reader:after}));assert.equal(transition.available,true);
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
 await assert.rejects(async()=>(await f.api.qualifyCheckpoint({reader:f.reader})),/Incomplete trusted present\/absent route census/);
 f.save(CATALOGUE,{version:1,kind:'accepted-selected-checkpoints-v1',
  checkpoints:[{...f.rootRow,routes:{...f.rootRow.routes,sha256:'0'.repeat(64)}}]});f.commit();
 const corruptReader=new f.native.ImmutableReader(f.root,f.selected);
 await assert.rejects(async()=>(await f.api.qualifyCheckpoint({reader:corruptReader})),/Whole immutable input differs/);
 f.git('checkout','-q',original);
 f.save('data/owners.json',[{id:'B',index:1},{id:'A',index:2},{id:'C',index:3}]);const changed=f.commit();
 const reader=new f.native.ImmutableReader(f.root,changed);
 const result=(await f.api.qualifyCheckpoint({reader}));assert.equal(result.available,false);assert.match(result.reason,/routing alternative changed/);
});


test('removed or changed trusted producer eligibility cannot silently reuse accepted policy',async t=>{
 const f=await trustedFixture(t), original=f.git('rev-parse','HEAD').toString().trim();
 const policy=JSON.parse(fs.readFileSync(path.join(f.root,PROGRAMME)));
 for(const edit of [p=>p.programs.pop(),p=>p.current_rebind_migrations.pop(),p=>{p.programs[0].source_executed_code[0].sha256='0'.repeat(64);}]){
  f.git('checkout','-q',original);const changed=structuredClone(policy);edit(changed);f.save(PROGRAMME,changed);f.commit();
  const reader=new f.native.ImmutableReader(f.root,f.selected);
  const result=(await f.api.qualifyCheckpoint({reader}));assert.equal(result.available,false);assert.match(result.reason,/preserves accepted eligibility/);
 }
});


test('archived child custody is retained in its actual parent inventory without crossing invocations',async t=>{
 const f=await trustedFixture(t), first=(await f.api.qualifyCheckpoint({reader:f.reader}));assert.equal(first.available,true);
 for(const p of [f.rootRow.facts,f.rootRow.certificate,f.rootRow.custody,f.rootRow.routes]){
  const actual=f.reader.inventory.get(p.commit+':'+p.path);assert.ok(actual?.whole_body_consumed);assert.equal(actual.sha256,p.sha256);
 }
 assert.ok([...f.reader.inventory.values()].some(p=>p.path===CATALOGUE&&p.whole_body_consumed));
 const secondReader=new f.native.ImmutableReader(f.root,f.selected);
 assert.notStrictEqual(secondReader.inventory,f.reader.inventory);assert.equal(secondReader.inventory.size,0);
 const second=(await f.api.qualifyCheckpoint({reader:secondReader}));assert.equal(second.available,true);
 assert.notStrictEqual(secondReader.inventory,f.reader.inventory);
 f.api.releaseCheckpoint(first.state);assert.deepEqual(nativeLiteral(f.api.projectNativeRows({state:second.state,rows:[1]}).rows),[{y:1,runs:[[0,1,2]]}]);
});


test('archived JavaScript execution roles can evolve while same-extension scientific inputs stay pinned',async t=>{
 const f=await trustedFixture(t,{codeRoutes:true});
 fs.appendFileSync(path.join(f.root,'src/native-grid.js'),'\n// Reviewed native-only support.\n');const newer=f.commit();
 const reader=new f.native.ImmutableReader(f.root,newer);
 const qualified=(await f.api.qualifyCheckpoint({reader}));assert.equal(qualified.available,true);
 const transition=(await f.api.qualifyTransition({state:qualified.state,reader}));assert.equal(transition.available,true);
 // A .js suffix alone does not exempt scientific bytes from the old census.
 f.save('data/scientific.js',{fixture:'changed scientific input'});const changed=f.commit();
 const candidate=new f.native.ImmutableReader(f.root,changed,{invocation:reader.invocation});
 const rejected=(await f.api.qualifyTransition({state:qualified.state,reader:candidate}));
 assert.equal(rejected.available,false);assert.match(rejected.reason,/route changed/);
 fs.appendFileSync(path.join(f.root,'src/native-grid.js'),'\n// Uncommitted executable drift.\n');
 const dirty=new f.native.ImmutableReader(f.root,newer);
 await assert.rejects(async()=>(await f.api.qualifyCheckpoint({reader:dirty})),/changed executing checkpoint method/);
 f.api.releaseCheckpoint(qualified.state);
});

for(const completedConstructor of [false,true])test('actual appended authority survives complete checks, a subsequent transition and original native projection, completed='+completedConstructor,async t=>{
 const f=await trustedFixture(t,{nativeAppend:true}),baseline=(await f.api.qualifyCheckpoint({reader:f.reader}));
 const next=await appendNativeAuthority(f,{completedConstructor}),reader=new f.native.ImmutableReader(f.root,next.candidate,{invocation:f.reader.invocation});
 const transition=(await f.api.qualifyTransition({state:baseline.state,reader}));
 assert.equal(transition.available,true);assert.deepEqual(transition.changedIds,['A']);assert.deepEqual(transition.changedNativeRows,[next.y]);
 assert.deepEqual(nativeLiteral(transition.candidate.ledger.rows),next.ledger.rows);assert.deepEqual(nativeLiteral(transition.candidate.patch.rows),next.patch.rows);
 assert.deepEqual(nativeLiteral(transition.candidate.additions.at(-1).native_rows),next.proof.original_ledger.rows[0].native_rows);
 assert.deepEqual(nativeLiteral(baseline.state.ledger.rows),f.ledger.rows);assert(Object.isFrozen(transition.candidate));
 f.save('later-unrelated.json',{later:true});const later=f.commit();
 const laterReader=new f.native.ImmutableReader(f.root,later,{invocation:f.reader.invocation});
 const again=(await f.api.qualifyTransition({state:transition.candidate,reader:laterReader}));
 assert.equal(again.available,true);assert.deepEqual(again.changedIds,[]);assert.deepEqual(again.changedNativeRows,[]);
 assert.deepEqual(nativeLiteral(again.candidate.patch.rows),next.patch.rows);
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
 const f=await trustedFixture(t,{nativeAppend:true}),{state}=(await f.api.qualifyCheckpoint({reader:f.reader}));
 const next=await appendNativeAuthority(f,options),reader=new f.native.ImmutableReader(f.root,next.candidate,{invocation:f.reader.invocation});
 await assert.rejects(async()=>(await f.api.qualifyTransition({state,reader})),expected);
 assert.deepEqual(nativeLiteral(state.ledger.rows),f.ledger.rows);f.api.releaseCheckpoint(state);
});

test('failed complete literal check preserves authenticated baseline and permits a corrected retry',async t=>{
 const f=await trustedFixture(t,{nativeAppend:true}),{state}=(await f.api.qualifyCheckpoint({reader:f.reader}));
 const next=await appendNativeAuthority(f,{mutateLedger:l=>{l.rows.at(-1).source_receipt_sha256='0'.repeat(64);}});
 const reader=new f.native.ImmutableReader(f.root,next.candidate,{invocation:f.reader.invocation});
 await assert.rejects(async()=>(await f.api.qualifyTransition({state,reader})),/changed original appended primitive/);
 assert.deepEqual(nativeLiteral(state.ledger.rows),f.ledger.rows);
 assert.deepEqual(f.api.projectSourceFeatures({state,ids:[]}).features,[]);
 const recovered=await appendNativeAuthority(f,{name:'recovered'}),retryReader=new f.native.ImmutableReader(f.root,recovered.candidate,{invocation:f.reader.invocation});
 assert.equal((await f.api.qualifyTransition({state,reader:retryReader})).available,true);
 f.api.releaseCheckpoint(state);
});

test('an unconsumed logical source shadowed by the exact accepted override does not replay science',async t=>{
 const f=await trustedFixture(t,{sourceOverride:true});
 f.save('data/source.json',{unselected:'different ordinary source'});const baseline=f.commit();
 const reader=new f.native.ImmutableReader(f.root,baseline),qualified=(await f.api.qualifyCheckpoint({reader}));
 assert.equal(qualified.available,true);
 f.save('data/source.json',{unselected:'changed again'});const candidate=f.commit();
 const after=new f.native.ImmutableReader(f.root,candidate,{invocation:reader.invocation});
 const transition=(await f.api.qualifyTransition({state:qualified.state,reader:after}));
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
 const qualified=(await f.api.qualifyCheckpoint({reader:f.reader}));assert.equal(qualified.available,true);
 f.save('data/source.json',{changed:'actually consumed elsewhere'});const candidate=f.commit();
 const after=new f.native.ImmutableReader(f.root,candidate,{invocation:f.reader.invocation});
 const transition=(await f.api.qualifyTransition({state:qualified.state,reader:after}));
 assert.equal(transition.available,false);assert.match(transition.reason,/present\/absent route changed/);
 f.api.releaseCheckpoint(qualified.state);
});

test('a wrong override logical mapping cannot exempt an ordinary source route',async t=>{
 const f=await trustedFixture(t,{sourceOverride:true,overrideLogicalPath:'data/somewhere-else.json'});
 f.save('data/source.json',{changed:'unmatched logical path'});const candidate=f.commit();
 const result=(await f.api.qualifyCheckpoint({reader:new f.native.ImmutableReader(f.root,candidate)}));
 assert.equal(result.available,false);assert.match(result.reason,/routing alternative changed/);
});

test('physical override bytes and native source routes remain binding',async t=>{
 for(const name of ['data/selected-source.json.gz','data/native/runs.bin.gz']){
  const f=await trustedFixture(t,{sourceOverride:true}),qualified=(await f.api.qualifyCheckpoint({reader:f.reader}));
  f.save(name,Buffer.from('different physical bytes'));const candidate=f.commit();
  const after=new f.native.ImmutableReader(f.root,candidate,{invocation:f.reader.invocation});
  const transition=(await f.api.qualifyTransition({state:qualified.state,reader:after}));
  assert.equal(transition.available,false);assert.match(transition.reason,/present\/absent route changed/);
  f.api.releaseCheckpoint(qualified.state);
 }
});

test('new actual physical use of a shadowed source revokes its next-transition exemption',async t=>{
 const f=await trustedFixture(t,{nativeAppend:true,sourceOverride:true});
 const qualified=(await f.api.qualifyCheckpoint({reader:f.reader}));assert.equal(qualified.available,true);
 const appended=await appendNativeAuthority(f,{membershipPath:'data/source.json'});
 const reader=new f.native.ImmutableReader(f.root,appended.candidate,{invocation:f.reader.invocation});
 const transition=(await f.api.qualifyTransition({state:qualified.state,reader}));assert.equal(transition.available,true);
 assert.ok([...reader.inventory.values()].some(p=>p.path==='data/source.json'&&p.whole_body_consumed));
 const census=f.api.checkpointRouteCensus({transition});
 assert.equal(census.routes.find(p=>p.path==='data/source.json').tree,f.git('ls-tree','-z',appended.candidate,'--','data/source.json').toString());
 f.save('data/source.json',{changed:'now a real physical dependency'});const next=f.commit();
 const after=new f.native.ImmutableReader(f.root,next,{invocation:f.reader.invocation});
 const rejected=(await f.api.qualifyTransition({state:transition.candidate,reader:after}));
 assert.equal(rejected.available,false);assert.match(rejected.reason,/present\/absent route changed/);
 f.api.releaseCheckpoint(qualified.state);
});


test('checkpoint admission, transition and census share one complete route tree',async t=>{
 const f=await trustedFixture(t),git=f.reader.git.bind(f.reader),calls=[],layers=[],streamed=[];
 f.reader.git=(...args)=>{calls.push(args);return git(...args);};
 const stream=f.reader.stream.bind(f.reader);f.reader.stream=(name,...args)=>{streamed.push(name);return stream(name,...args);};
 const readPinned=f.reader.readPinned.bind(f.reader);
 f.reader.readPinned=pins=>{layers.push(pins.map(p=>p.path));return readPinned(pins);};
 const qualified=(await f.api.qualifyCheckpoint({reader:f.reader}));assert.equal(qualified.available,true);
 const transition=(await f.api.qualifyTransition({state:qualified.state,reader:f.reader}));assert.equal(transition.available,true);
 const census=f.api.checkpointRouteCensus({transition});
 for(const row of census.routes)assert.equal(row.tree,f.git('ls-tree','-z',f.selected,'--',row.path).toString());
 assert.equal(calls.filter(args=>args[0]==='ls-tree'&&args[1]==='-rtz').length,1);
 assert.deepEqual(layers,[
  ['data/registry.json','data/envelope.json','data/manifest.json'],
  ['original/binding.json'],['data/registry.json','data/envelope.json','data/manifest.json']]);
 assert.deepEqual([...new Set(streamed)].sort(),['accepted-rebind/request.json','accepted-rebind/result.json','data/ledger.json','data/patch.json','original/patch-one.json']);
 for(const name of streamed)assert([...f.reader.inventory.values()].some(p=>p.path===name&&p.whole_body_consumed===true),name+' retains actual whole-stream custody');
 f.api.releaseCheckpoint(qualified.state);
});

test('real checkpoint admission cannot accept a corrupted known-pin body batch',async t=>{
 const f=await trustedFixture(t),batch=f.reader.gitBatch.bind(f.reader);let altered=false;
 f.reader.gitBatch=(args,...rest)=>{
  const output=batch(args,...rest);
  if(args[1]==='--batch'&&!altered){altered=true;output[output.indexOf(10)+1]^=1;}
  return output;
 };
 await assert.rejects(async()=>(await f.api.qualifyCheckpoint({reader:f.reader})),/Whole immutable input differs/);
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
  const result=(await f.api.qualifyCheckpoint({reader}));assert.equal(result.available,false,kind);
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
 const result=(await f.api.qualifyCheckpoint({reader:s.reader()}));
 assert.equal(result.available,true);assert.equal(result.state.ledger.rows.length,2);
 assert.deepEqual(nativeLiteral(f.api.projectNativeRows({state:result.state,rows:[1]}).rows),[{y:1,runs:[[0,1,2]]}]);
 assert.doesNotMatch(s.tracing(),remoteAttempt);
 f.api.releaseCheckpoint(result.state);
});

for(const packed of [false,true])test('complete native authority authenticates retained source aliases without fetching unavailable originals, packed='+packed,async t=>{
 const f=await trustedFixture(t,{nativeAppend:true});
 const absent=['1','2','3'].map(value=>value.repeat(40));
 for(const commit of absent)assert.throws(()=>f.git('cat-file','-e',commit),'Original must genuinely be absent');
 const next=await appendNativeAuthority(f,{mutateEvidence:evidence=>{evidence.catalogue.commit=absent[0];}});
 const {readRetainedRegistryAuthority}=await import(pathToFileURL(path.join(f.root,CODE[1])));
 const binding=JSON.parse(f.git('show',next.entry.source_authority.commit+':'+next.entry.source_authority.path));
 binding.source_evidence.commit=absent[1];
 const rule=JSON.parse(f.git('show',next.entry.rule_preimage.commit+':'+next.entry.rule_preimage.path));
 rule.source_evidence.commit=absent[1];
 f.save(next.entry.source_authority.path,binding);f.save(next.entry.rule_preimage.path,rule);
 const candidate=f.commit(),entry={...next.entry,
  source_authority:{...f.pin(next.entry.source_authority.path,candidate),commit:absent[2]},
  rule_preimage:{...f.pin(next.entry.rule_preimage.path,candidate),commit:absent[2]}};
 entry.rule_sha256=entry.rule_preimage.sha256;delete entry.authority_sha256;entry.authority_sha256=valueSha(entry);
 if(packed)f.git('repack','-ad');
 const s=scalarPromisor(f),proof=readRetainedRegistryAuthority(s.reader(candidate),entry);
 assert.deepEqual(proof.original_ledger,next.proof.original_ledger);
 assert.deepEqual(proof.native_proof.native_patches,next.proof.native_proof.native_patches);
 assert.doesNotMatch(s.tracing(),remoteAttempt);
 for(const commit of absent)assert.throws(()=>f.git('cat-file','-e',commit),'No original was fetched');
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
 const left=(await a.api.qualifyCheckpoint({reader:a.reader})),right=(await b.api.qualifyCheckpoint({reader:b.reader}));
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
 await assert.rejects(async()=>(await first.api.qualifyCheckpoint({reader:first.reader})),/decoded output is corrupt/);
 const later=await trustedFixture(t),qualified=(await later.api.qualifyCheckpoint({reader:later.reader}));
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


test('real appended overlap qualification does not search the complete baseline array per interval',async t=>{
 const f=await trustedFixture(t,{nativeAppend:true}),{state}=(await f.api.qualifyCheckpoint({reader:f.reader}));
 const next=await appendNativeAuthority(f),reader=new f.native.ImmutableReader(f.root,next.candidate,{invocation:f.reader.invocation});
 const original=Array.prototype.find;
 Array.prototype.find=function(...args){
  assert.notStrictEqual(this,state.patch.rows,'Repeated full baseline row search');
  return Reflect.apply(original,this,args);
 };
 try {
  const transition=(await f.api.qualifyTransition({state,reader}));
  assert.equal(transition.available,true);
  assert.deepEqual(nativeLiteral(transition.candidate.patch.rows),next.patch.rows);
  assert.deepEqual(transition.changedNativeRows,[next.y]);
 } finally {Array.prototype.find=original;f.api.releaseCheckpoint(state);}
});

for(const [name,shift,overlap] of [
 ['same-owner overlap',0,true],['left boundary touch',-1,false],['right boundary touch',1,false],['disjoint interval',3,false]
])test('indexed append guard preserves '+name,async t=>{
 const size=262166,y=nativeRowLatitudes(size).findIndex(v=>v<.1),x=Math.floor((.1+180)/360*size);
 const originalPatchRows=[{y,runs:[[x+shift,x+shift+1,1]]}];
 const f=await trustedFixture(t,{nativeAppend:true,originalPatchRows}),{state}=(await f.api.qualifyCheckpoint({reader:f.reader}));
 const next=await appendNativeAuthority(f,{mutatePatch:patch=>{patch.rows=overlap?structuredClone(originalPatchRows):mergeCompletedNativePatches(patch.rows.map(row=>({rows:[row]})),size);}});
 const reader=new f.native.ImmutableReader(f.root,next.candidate,{invocation:f.reader.invocation});
 try {
  if(overlap)await assert.rejects(async()=>(await f.api.qualifyTransition({state,reader})),/New native assignment overlaps a previously selected owner/);
  else {
   const transition=(await f.api.qualifyTransition({state,reader}));
   assert.equal(transition.available,true);
   assert.deepEqual(nativeLiteral(transition.candidate.patch.rows),next.patch.rows);
   assert.deepEqual(transition.changedNativeRows,[y]);
  }
  assert.deepEqual(nativeLiteral(state.patch.rows),originalPatchRows);
 } finally {f.api.releaseCheckpoint(state);}
});


for(const [name,originalPatchRows] of [
 ['duplicate',[{y:1,runs:[[2,3,1]]},{y:1,runs:[[3,4,1]]}]],
 ['decreasing',[{y:2,runs:[[2,3,1]]},{y:1,runs:[[3,4,1]]}]]
])test('checkpoint admission rejects '+name+' baseline native row identities before indexing',async t=>{
 const f=await trustedFixture(t,{originalPatchRows});
 await assert.rejects(async()=>(await f.api.qualifyCheckpoint({reader:f.reader})),/Duplicate, unordered or foreign native row/);
});


test('miniature seed snapshots custom original patch rows and separates their histories',async t=>{
 const originalPatchRows=[{y:2,runs:[[2,3,1]]}],expected=structuredClone(originalPatchRows);
 const first=await trustedFixture(t,{originalPatchRows});
 originalPatchRows[0].runs[0][0]=1;
 assert.deepEqual(first.patch.rows,expected,'The caller cannot mutate the returned consumer');
 first.patch.rows[0].runs[0][0]=0;
 const same=await trustedFixture(t,{originalPatchRows:structuredClone(expected)});
 const different=await trustedFixture(t,{originalPatchRows});
 assert.deepEqual(same.patch.rows,expected,'Neither caller nor consumer mutation reaches the private seed');
 assert.deepEqual(different.patch.rows,originalPatchRows,'Different row content gets its own history');
 assert.notEqual(first.root,same.root);
 assert.equal(first.selected,same.selected);
 assert.notEqual(same.selected,different.selected);
 const omitted=await trustedFixture(t),nullish=await trustedFixture(t,{originalPatchRows:null});
 const explicit=await trustedFixture(t,{originalPatchRows:[{y:1,runs:[[2,3,1]]}]});
 assert.equal(omitted.selected,nullish.selected);
 assert.equal(omitted.selected,explicit.selected);
 assert.notEqual(same.selected,omitted.selected);
 assert.deepEqual(omitted.patch.rows,[{y:1,runs:[[2,3,1]]}]);
});

test('bounded native visitation preserves exact rows and custody without retaining new triples',async t=>{
 const f=await trustedFixture(t),state=(await f.api.qualifyCheckpoint({reader:f.reader})).state;
 const visited=[];
 const result=f.api.visitNativeRows({state,rows:[0,1,2,3],visit:rows=>visited.push(...rows)});
 assert.deepEqual(nativeLiteral(visited),[{y:0,runs:[[0,1,1]]},{y:1,runs:[[0,1,2]]},{y:2,runs:[[1,2,3]]},{y:3,runs:[]}]);
 assert.deepEqual(result.reused_rows,[1]);assert.deepEqual(result.acquired_rows,[0,2,3]);
 const next=f.api.projectNativeRows({state,rows:[0,1,2,3]});
 assert.deepEqual(nativeLiteral(next.rows),nativeLiteral(visited));assert.deepEqual(next.acquired_rows,[0,2,3]);
 assert.deepEqual(next.custody,result.custody);
 assert.throws(()=>f.api.visitNativeRows({state,rows:[1,1],visit(){}}),/native row scope/);
 assert.throws(()=>f.api.visitNativeRows({state:structuredClone(state),rows:[],visit(){}}),/private qualified/);
 f.api.releaseCheckpoint(state);
 assert.throws(()=>f.api.visitNativeRows({state,rows:[],visit(){}}),/private qualified|expired/);
});

test('throwing native visitor releases transient rows and packed-container cache',async t=>{
 const f=await trustedFixture(t),state=(await f.api.qualifyCheckpoint({reader:f.reader})).state;
 assert.throws(()=>f.api.visitNativeRows({state,rows:[0,1,2,3],visit(){throw Error('consumer failed');}}),/consumer failed/);
 const next=f.api.visitNativeRows({state,rows:[0,1,2,3],visit(){}});
 assert.deepEqual(next.reused_rows,[1]);assert.deepEqual(next.acquired_rows,[0,2,3]);
});

test('actual appended native consumer retains the eager conservation and exact first visibility witness',async t=>{
 const f=await trustedFixture(t,{nativeAppend:true});
 f.save('scripts/selected-checkpoint-native.mjs',fs.readFileSync('scripts/selected-checkpoint-native.mjs'));f.commit();
 const baseline=(await f.api.qualifyCheckpoint({reader:f.reader}));
 const next=await appendNativeAuthority(f),reader=new f.native.ImmutableReader(f.root,next.candidate,{invocation:f.reader.invocation});
 const transition=(await f.api.qualifyTransition({state:baseline.state,reader}));assert.equal(transition.available,true);
 const consumer=await import(pathToFileURL(path.join(f.root,'scripts/selected-checkpoint-native.mjs')));
 const {newVisibleRepairCandidates,repairVisibilityWitnesses}=f.native;
 const owners=baseline.state.certificate.entries.map(row=>({id:row[0],index:row[1]})),size=baseline.state.manifest.size;
 const projection=f.api.projectNativeRows({state:transition.candidate,rows:transition.changedNativeRows});
 const before=consumer.applyNativeAdditiveRows(projection.rows,transition.baseline.patch,{size,owners});
 const after=consumer.applyNativeAdditiveRows(projection.rows,transition.candidate.patch,{size,owners});
 const expected=repairVisibilityWitnesses({candidates:newVisibleRepairCandidates(nativeLiteral(transition.baseline.additions),nativeLiteral(transition.candidate.additions)),size,
   latitudes:f.api.projectVisibilityLatitudes({state:transition.candidate}),beforeRows:before,afterRows:after});
 const actual=await consumer.compareSelectedCheckpointNative({transition});
 assert.equal(actual.status,'no-new-native-loss');assert.equal(actual.affected_rows,1);
 assert.deepEqual(actual.repair_visibility.witnesses,expected);assert.equal(expected.length,1);assert(expected[0]);
});

test('authenticated interval visit preserves complete rows without populating expanded-row caches',async t=>{
 const f=await trustedFixture(t),{state}=(await f.api.qualifyCheckpoint({reader:f.reader})),actual=[];
 const projection=await f.api.visitNativeIntervals({state,rows:[0,1,2,3],visit:async ({y,runs})=>{
  const values=[];for await(const run of runs)values.push(run);actual.push({y,runs:values});
 }});
 assert.deepEqual(actual,[{y:0,runs:[[0,1,1]]},{y:1,runs:[[0,1,2]]},{y:2,runs:[[1,2,3]]},{y:3,runs:[]}]);
 assert.deepEqual(projection.reused_rows,[1]);assert.deepEqual(projection.acquired_rows,[0,2,3]);
 const again=await f.api.visitNativeIntervals({state,rows:[0,1,2,3],visit:async ({runs})=>{for await(const run of runs)void run;}});
 assert.deepEqual(again.acquired_rows,[0,2,3]);
 await assert.rejects(f.api.visitNativeIntervals({state,rows:[0],visit(){}}),/omitted complete row/);
 await assert.rejects(f.api.visitNativeIntervals({state,rows:[0],visit(){throw Error('consumer failure');}}),/consumer failure/);
 await f.api.visitNativeIntervals({state,rows:[0],visit:async ({runs})=>{for await(const run of runs)void run;}});
 f.api.releaseCheckpoint(state);
 await assert.rejects(f.api.visitNativeIntervals({state,rows:[],visit(){}}),/private qualified|expired/);
});

test('streamed authority union preserves coalescing, empty row presence and overlap refusal',async()=>{
 const {equalMergedPatchRows}=await import('../coordination/engineering/selected-geography-effective-prevention-20261009/selected-checkpoint.mjs');
 const a={rows:[{y:0,runs:[[0,2,1],[4,5,2]]},{y:2,runs:[]}]},b={rows:[{y:0,runs:[[1,3,1],[5,6,2]]}]};
 const expected=[{y:0,runs:[[0,3,1],[4,6,2]]},{y:2,runs:[]}];
 assert.equal(equalMergedPatchRows(expected,[a,b],8,2),true);
 assert.equal(equalMergedPatchRows(expected.slice(0,1),[a,b],8,2),false);
 assert.equal(equalMergedPatchRows([{y:0,runs:[[0,2,1],[4,6,2]]},{y:2,runs:[]}],[a,b],8,2),false);
 assert.throws(()=>equalMergedPatchRows(expected,[a,{rows:[{y:0,runs:[[1,3,2]]}]}],8,2),/reassigns/);
 assert.deepEqual(a.rows[0].runs,[[0,2,1],[4,5,2]]);
});

test('selected gzip ledger admission joins producers, rejects late errors and releases only candidate stores',async t=>{
 const {gzipSync}=await import('node:zlib');
 const {valueBytes,normaliseRetainedRepairLedger}=await import('../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs');
 const f=await trustedFixture(t),{state}=await f.api.qualifyCheckpoint({reader:f.reader});
 const roots=[],mkdtemp=fs.mkdtempSync;
 t.mock.method(fs,'mkdtempSync',(...args)=>{const root=mkdtemp(...args);if(String(args[0]).includes('native-intervals-'))roots.push(root);return root;});
 function candidate({badHash=false,badSyntax=false}={}){
  const body=Buffer.concat([valueBytes(f.ledger),Buffer.from(badSyntax?'trailing-invalid':'')]);
  f.save('compressed/ledger.json.gz',gzipSync(body));const l=f.commit();
  const ledger={...f.pin('compressed/ledger.json.gz',l),decoded_bytes:body.length,decoded_sha256:badHash?'0'.repeat(64):f.native.visibilityDigest(f.ledger)};
  if(badSyntax){const {createHash}=requireHash;ledger.decoded_sha256=createHash('sha256').update(body).digest('hex');}
  const reference={...f.envelope.effective_reference,footprints_sha256:valueSha({domain:'worldatlas-effective-native-footprints:v2',
    base_reference:f.envelope.base_reference,authority_registry_sha256:valueSha(f.registry),ledger_sha256:ledger.sha256,
    components:[...normaliseRetainedRepairLedger(f.ledger,f.registry).rows.values()]})};
  f.save('compressed/patch.json',{...f.patch,ledger_sha256:ledger.sha256,effective_reference:reference});const p=f.commit();
  const assets={...f.sidecar.logical_asset_map,ledger,patch:f.pin('compressed/patch.json',p)};
  f.save('compressed/envelope.json',{...f.envelope,...assets,effective_reference:reference});const e=f.commit();
  f.save('compressed/sidecar.json',{...f.sidecar,logical_asset_map:assets,runtime_envelope:f.pin('compressed/envelope.json',e)});const s=f.commit();
  const side=f.pin('compressed/sidecar.json',s);f.save('data/ownership-selection.json',{...f.selection,additive_release:{path:side.path,bytes:side.bytes,sha256:side.sha256}});
  return new f.native.ImmutableReader(f.root,f.commit(),{invocation:f.reader.invocation});
 }
 const requireHash=await import('node:crypto');
 for(const options of [{badHash:true},{badSyntax:true}]){
  const reader=candidate(options),stream=reader.stream.bind(reader);let active=0;
  reader.stream=async function*(...args){active++;try{yield* stream(...args);}finally{await new Promise(resolve=>setTimeout(resolve,5));active--;}};
  await assert.rejects(f.api.qualifyTransition({state,reader}),/identity|JSON/);
  assert.equal(active,0,'rejected admission must join physical reader cleanup');
  assert(roots.every(root=>!fs.existsSync(root)),'failed candidate scratch remains');
  assert.deepEqual(nativeLiteral(state.patch.rows),f.patch.rows);
 }
 const result=await f.api.qualifyTransition({state,reader:candidate()});
 assert.equal(result.available,true);assert.deepEqual(result.changedNativeRows,[]);
 assert.deepEqual(nativeLiteral(result.candidate.ledger),f.ledger);
 f.api.releaseCheckpoint(state);assert(roots.every(root=>!fs.existsSync(root)));
});

for(const [name,mutate,message]of [
 ['scope',value=>value.component_ids.pop(),/scope\/rule\/patch/],
 ['rows',value=>value.ledger_rows.pop(),/scope\/rule\/patch/],
 ['intervals',value=>value.ledger_rows[0].native_rows[0].runs[0][1]++,/intervals differ/],
 ['receipt',value=>value.ledger_rows[0].source_receipt_sha256='0'.repeat(64),/original source target\/owner\/receipt/]
])test('stored completed authority rejects coherently pinned changed '+name,async t=>{
 const f=await trustedFixture(t,{nativeAppend:true}),baseline=await f.api.qualifyCheckpoint({reader:f.reader});
 const next=await appendNativeAuthority(f,{completedConstructor:true,mutateConstructor:mutate});
 const reader=new f.native.ImmutableReader(f.root,next.candidate,{invocation:f.reader.invocation});
 await assert.rejects(()=>f.api.qualifyTransition({state:baseline.state,reader}),message);
 assert.deepEqual(nativeLiteral(baseline.state.ledger.rows),f.ledger.rows);
});
