import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {valueBytes,valueSha,validateCurrentRebindLimits} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
import {deriveCoordinateDelta,projectSourceFeatures,projectNativeRows,qualifyTransition} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-checkpoint.mjs';
import {MODULE,PROGRAMME,CATALOGUE,CODE,polygon,feature,fixtures,addition,trustedFixture,appendNativeAuthority} from './fixtures/selected-checkpoint.mjs';

test('serialized lookalikes cannot mint state or projectors',()=>{
 const state={version:1,kind:'verified-selected-state-v1',certificate:fixtures().certificate};
 assert.throws(()=>projectSourceFeatures({state,ids:['A'],budget:{}}),/private qualified/);
 assert.throws(()=>projectNativeRows({state,rows:[0],budget:{}}),/private qualified/);
 assert.throws(()=>qualifyTransition({state,reader:{},budget:{}}),/private qualified/);
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
 const f=await trustedFixture(t), result=f.api.qualifyCheckpoint({reader:f.reader,budget:f.budget});
 assert.equal(result.available,true);const state=result.state;
 assert.equal(state.ledger.rows.length,2);assert.equal(state.ledger.rows[1].disposition,'rejected');
 const sources=f.api.projectSourceFeatures({state,ids:['A','B'],budget:f.budget});
 assert.deepEqual(sources.features.map(p=>p.id),['A','B']);assert.equal(sources.inverse.length,2);
 const native=f.api.projectNativeRows({state,rows:[1],budget:f.budget});
 assert.deepEqual(native.rows,[{y:1,runs:[[0,1,2]]}]);assert.deepEqual(native.acquired_rows,[]);
 const fresh=f.api.projectNativeRows({state,rows:[0,1,2,3],budget:f.budget});
 assert.deepEqual(fresh.rows,[{y:0,runs:[[0,1,1]]},{y:1,runs:[[0,1,2]]},{y:2,runs:[[1,2,3]]},{y:3,runs:[]}]);
 assert.deepEqual(fresh.acquired_rows,[0,2,3]);assert.ok(fresh.custody.new_whole_inputs.length>=2);
 assert.throws(()=>f.api.projectNativeRows({state:JSON.parse(JSON.stringify(state)),rows:[1],budget:f.budget}),/private qualified/);
 f.api.releaseCheckpoint(state);assert.throws(()=>f.api.projectSourceFeatures({state,ids:['A'],budget:f.budget}),/private qualified/);
});
test('unchanged actual selection at a newer commit reuses the original accepted checkpoint',async t=>{
 const f=await trustedFixture(t);f.save('unrelated.json',{new:true});const newer=f.commit();
 const reader=new f.native.ImmutableReader(f.root,newer,{allowance:f.reader.allowance}),budget={shared:reader.budget,carriedBytes:0};
 const result=f.api.qualifyCheckpoint({reader,budget});assert.equal(result.available,true);
 assert.equal(result.state.selected_commit,newer);assert.equal(result.state.accepted_execution.historical_selected_commit,f.selected);
 const transition=f.api.qualifyTransition({state:result.state,reader,budget});assert.equal(transition.available,true);
 assert.deepEqual(transition.changedIds,[]);assert.deepEqual(transition.changedNativeRows,[]);
 assert.deepEqual(transition.changedIds,[]);
});
test('committed qualifier edits need no manual catalogue fingerprint refresh',async t=>{
 const f=await trustedFixture(t), catalogue=fs.readFileSync(path.join(f.root,CATALOGUE));
 fs.appendFileSync(path.join(f.root,MODULE),'\n// reviewed non-scientific change\n');const newer=f.commit();
 const reader=new f.native.ImmutableReader(f.root,newer,{allowance:f.reader.allowance}),budget={shared:reader.budget,carriedBytes:0};
 assert.equal(f.api.qualifyCheckpoint({reader,budget}).available,true);
 assert.deepEqual(fs.readFileSync(path.join(f.root,CATALOGUE)),catalogue);
});
test('changed same-count source owners cannot reuse accepted custody, and undercharged shared budgets are rejected',async t=>{
 const f=await trustedFixture(t);f.save('data/source.json',{type:'FeatureCollection',features:[feature('B',0),feature('A',1),feature('C',5)]});const candidate=f.commit();
 const reader=new f.native.ImmutableReader(f.root,candidate,{allowance:f.reader.allowance}),budget={shared:reader.budget,carriedBytes:0};
 const result=f.api.qualifyCheckpoint({reader,budget});assert.equal(result.available,false);assert.match(result.reason,/routing alternative changed/);
 assert.throws(()=>f.api.qualifyCheckpoint({reader,budget:{shared:{},carriedBytes:0}}),/actual shared/);
 assert.throws(()=>f.api.qualifyCheckpoint({reader,budget:{shared:reader.budget,carriedBytes:-1}}),/caller-carried/);
});
test('corrupt accepted products and dirty executing code are rejected rather than treated as no change',async t=>{
 const f=await trustedFixture(t);f.rootRow.certificate.decoded_sha256='0'.repeat(64);
 f.save(CATALOGUE,{version:1,kind:'accepted-selected-checkpoints-v1',checkpoints:[f.rootRow]});f.commit();
 assert.throws(()=>f.api.qualifyCheckpoint({reader:f.reader,budget:f.budget}),/decoded output is corrupt/);
 f.save(MODULE,Buffer.concat([fs.readFileSync(path.join(f.root,MODULE)),Buffer.from('\n// drift\n')]));
 const reader=new f.native.ImmutableReader(f.root,f.selected,{allowance:f.reader.allowance});
 assert.throws(()=>f.api.qualifyCheckpoint({reader,budget:{shared:reader.budget,carriedBytes:0}}),/changed executing checkpoint method/);
});

test('native projection rejects an incomplete complete row partition despite matching encoded and decoded hashes',async t=>{
 const f=await trustedFixture(t,{incompleteNative:true}),result=f.api.qualifyCheckpoint({reader:f.reader,budget:f.budget});
 assert.equal(result.available,true);
 assert.throws(()=>f.api.projectNativeRows({state:result.state,rows:[2],budget:f.budget}),/row partition omitted/);
});
test('a forged candidate-selected checkpoint catalogue cannot replace trusted execution authority',async t=>{
 const f=await trustedFixture(t);const original=f.git('rev-parse','HEAD').toString().trim();
 f.save(CATALOGUE,{version:1,kind:'accepted-selected-checkpoints-v1',checkpoints:[]});const candidate=f.commit();
 f.git('checkout','-q',original);
 const reader=new f.native.ImmutableReader(f.root,candidate,{allowance:f.reader.allowance}),budget={shared:reader.budget,carriedBytes:0};
 assert.equal(f.api.qualifyCheckpoint({reader,budget}).available,true);
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
 const f=await trustedFixture(t), result=f.api.qualifyCheckpoint({reader:f.reader,budget:f.budget});
 const ledger={...f.ledger,scope_ids:['old'],rows:[f.ledger.rows[0]]};
 const candidate=candidateProducts(f,{ledger});
 const reader=new f.native.ImmutableReader(f.root,candidate,{allowance:f.reader.allowance,budget:f.reader.budget});
 assert.throws(()=>f.api.qualifyTransition({state:result.state,reader,budget:f.budget}),/Old complete ledger/);
 f.reader.used=0;
 assert.throws(()=>f.api.projectNativeRows({state:result.state,rows:[1],budget:f.budget}),/reset or undercharged/);
});
test('actual transition rejects same-count changed native ownership without reacquiring original science',async t=>{
 const f=await trustedFixture(t), result=f.api.qualifyCheckpoint({reader:f.reader,budget:f.budget});
 const candidate=candidateProducts(f,{patch:{...f.patch,rows:[{y:1,runs:[[2,3,2]]}]}});
 const reader=new f.native.ImmutableReader(f.root,candidate,{allowance:f.reader.allowance,budget:f.reader.budget});
 assert.throws(()=>f.api.qualifyTransition({state:result.state,reader,budget:f.budget}),/omitted, invented or reassigned/);
});
test('actual transition refuses a stale base and preserves the usable baseline for candidate-only cold validation',async t=>{
 const f=await trustedFixture(t), result=f.api.qualifyCheckpoint({reader:f.reader,budget:f.budget});
 f.save('candidate/sidecar.json',{...f.sidecar,base_selection:{...f.sidecar.base_selection,release_id:'geography:new'}});const a=f.commit(),p=f.pin('candidate/sidecar.json',a);
 f.save('data/ownership-selection.json',{...f.selection,release_id:'geography:new',additive_release:{path:p.path,bytes:p.bytes,sha256:p.sha256}});const candidate=f.commit();
 const reader=new f.native.ImmutableReader(f.root,candidate,{allowance:f.reader.allowance,budget:f.reader.budget});
 const transition=f.api.qualifyTransition({state:result.state,reader,budget:f.budget});
 assert.equal(transition.available,false);assert.equal(transition.cold,'candidate');assert.strictEqual(transition.baseline,result.state);
});

test('private source reuse snapshots caller scope and admits each external carry increase before returning',async t=>{
 const f=await trustedFixture(t),{state}=f.api.qualifyCheckpoint({reader:f.reader,budget:f.budget});
 const ids=['A'],projection=f.api.projectSourceFeatures({state,ids,budget:f.budget});
 ids[0]='B';assert.throws(()=>f.api.projectSourceFeatures({state,ids:['B'],budget:f.budget,reuse:projection}),/incomplete source projection reuse/);
 const initial=f.budget.carriedBytes;f.budget.carriedBytes+=4096;
 const used=f.reader.used;
 const reused=f.api.projectSourceFeatures({state,ids:['A'],budget:f.budget,reuse:projection});
 assert.equal(reused.features[0].id,'A');assert.equal(f.reader.used,used+4096);
 f.budget.carriedBytes=initial;
 assert.throws(()=>f.api.projectSourceFeatures({state,ids:['A'],budget:f.budget,reuse:projection}),/reset or undercharged/);
 f.budget.carriedBytes=f.reader.phaseLimit;
 assert.throws(()=>f.api.projectSourceFeatures({state,ids:['A'],budget:f.budget,reuse:projection}),/External carried-state increase/);
});
test('fast selection admission rejects unknown patch fields and malformed complete effective references',async t=>{
 const f=await trustedFixture(t),{state}=f.api.qualifyCheckpoint({reader:f.reader,budget:f.budget});
 const candidate=candidateProducts(f,{patch:{...f.patch,unexpected_permission:true}});
 const reader=new f.native.ImmutableReader(f.root,candidate,{allowance:f.reader.allowance,budget:f.reader.budget});
 assert.throws(()=>f.api.qualifyTransition({state,reader,budget:f.budget}),/complete native patch schema/);
});

test('an unchanged accepted current-rebind proof cannot excuse a coherently repinned omitted target roster',async t=>{
 const f=await trustedFixture(t),{state}=f.api.qualifyCheckpoint({reader:f.reader,budget:f.budget});
 const candidate=candidateProducts(f,{ledger:{...f.ledger,current_targets:[]}});
 const reader=new f.native.ImmutableReader(f.root,candidate,{allowance:f.reader.allowance,budget:f.reader.budget});
 assert.throws(()=>f.api.qualifyTransition({state,reader,budget:f.budget}),/Ledger complete current target roster differs/);
});
test('coherently copied malformed geography references still fail exact fast-path admission',async t=>{
 const f=await trustedFixture(t),{state}=f.api.qualifyCheckpoint({reader:f.reader,budget:f.budget});
 const effective={...f.patch.effective_reference};delete effective.id;
 f.envelope={...f.envelope,effective_reference:effective};
 const candidate=candidateProducts(f,{patch:{...f.patch,effective_reference:effective}});
 const reader=new f.native.ImmutableReader(f.root,candidate,{allowance:f.reader.allowance,budget:f.reader.budget});
 assert.throws(()=>f.api.qualifyTransition({state,reader,budget:f.budget}),/complete effective reference/);
});


test('consumer admission authenticates the private complete transition rather than a forged scope wrapper',async t=>{
 const f=await trustedFixture(t),{state}=f.api.qualifyCheckpoint({reader:f.reader,budget:f.budget});
 const reader=new f.native.ImmutableReader(f.root,f.selected,{allowance:f.reader.allowance,budget:f.reader.budget});
 const transition=f.api.qualifyTransition({state,reader,budget:f.budget});
 assert.equal(transition.available,true);
 assert.equal(f.api.authenticateTransition({transition,budget:f.budget}),transition);
 assert.throws(()=>transition.changedNativeRows.push(1),TypeError);
 assert.throws(()=>transition.changedIds.push('omitted-neighbor'),TypeError);
 for(const forged of [{...transition},{...transition,plan:{...transition.plan,required_ids:[],pairs:[]}},{...transition,changedNativeRows:[]},JSON.parse(JSON.stringify(transition))])
  assert.throws(()=>f.api.authenticateTransition({transition:forged,budget:f.budget}),/private qualified selected transition/);
 f.api.releaseCheckpoint(state);
 assert.throws(()=>f.api.authenticateTransition({transition,budget:f.budget}),/private qualified selected transition/);
});


test('trusted programme policy evolves independently of unchanged selected scientific routes',async t=>{
 const f=await trustedFixture(t), originalPolicy=JSON.parse(fs.readFileSync(path.join(f.root,PROGRAMME)));
 const extra=structuredClone(originalPolicy.programs.at(-1));extra.source_profile='reviewed-fixture-policy';
 f.save(PROGRAMME,{...originalPolicy,programs:[...originalPolicy.programs,extra]});const newer=f.commit();
 const reader=new f.native.ImmutableReader(f.root,newer,{allowance:f.reader.allowance}),budget={shared:reader.budget,carriedBytes:0};
 const result=f.api.qualifyCheckpoint({reader,budget});assert.equal(result.available,true);
 const forged=structuredClone(extra);forged.source_profile='candidate-only-unknown-producer';
 f.save(PROGRAMME,{...originalPolicy,programs:[...originalPolicy.programs,extra,forged]});const candidate=f.commit();
 f.git('checkout','-q',newer);
 const after=new f.native.ImmutableReader(f.root,candidate,{allowance:reader.allowance,budget:reader.budget});
 const transition=f.api.qualifyTransition({state:result.state,reader:after,budget});assert.equal(transition.available,true);
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
 assert.throws(()=>f.api.qualifyCheckpoint({reader:f.reader,budget:f.budget}),/Incomplete trusted present\/absent route census/);
 f.save(CATALOGUE,{version:1,kind:'accepted-selected-checkpoints-v1',
  checkpoints:[{...f.rootRow,routes:{...f.rootRow.routes,sha256:'0'.repeat(64)}}]});f.commit();
 const corruptReader=new f.native.ImmutableReader(f.root,f.selected,{allowance:f.reader.allowance});
 assert.throws(()=>f.api.qualifyCheckpoint({reader:corruptReader,budget:{shared:corruptReader.budget,carriedBytes:0}}),/Whole immutable input differs/);
 f.git('checkout','-q',original);
 f.save('data/owners.json',[{id:'B',index:1},{id:'A',index:2},{id:'C',index:3}]);const changed=f.commit();
 const reader=new f.native.ImmutableReader(f.root,changed,{allowance:f.reader.allowance}),budget={shared:reader.budget,carriedBytes:0};
 const result=f.api.qualifyCheckpoint({reader,budget});assert.equal(result.available,false);assert.match(result.reason,/routing alternative changed/);
});


test('removed or changed trusted producer eligibility cannot silently reuse accepted policy',async t=>{
 const f=await trustedFixture(t), original=f.git('rev-parse','HEAD').toString().trim();
 const policy=JSON.parse(fs.readFileSync(path.join(f.root,PROGRAMME)));
 for(const edit of [p=>p.programs.pop(),p=>p.current_rebind_migrations.pop(),p=>{p.programs[0].source_executed_code[0].sha256='0'.repeat(64);}]){
  f.git('checkout','-q',original);const changed=structuredClone(policy);edit(changed);f.save(PROGRAMME,changed);f.commit();
  const reader=new f.native.ImmutableReader(f.root,f.selected,{allowance:f.reader.allowance}),budget={shared:reader.budget,carriedBytes:0};
  const result=f.api.qualifyCheckpoint({reader,budget});assert.equal(result.available,false);assert.match(result.reason,/preserves accepted eligibility/);
 }
});


test('archived child custody is retained in its actual parent inventory without crossing invocations',async t=>{
 const f=await trustedFixture(t), first=f.api.qualifyCheckpoint({reader:f.reader,budget:f.budget});assert.equal(first.available,true);
 for(const p of [f.rootRow.facts,f.rootRow.certificate,f.rootRow.custody,f.rootRow.routes]){
  const actual=f.reader.inventory.get(p.commit+':'+p.path);assert.ok(actual?.whole_body_consumed);assert.equal(actual.sha256,p.sha256);
 }
 assert.ok([...f.reader.inventory.values()].some(p=>p.path===CATALOGUE&&p.whole_body_consumed));
 const secondReader=new f.native.ImmutableReader(f.root,f.selected,{allowance:f.reader.allowance});
 assert.notStrictEqual(secondReader.inventory,f.reader.inventory);assert.equal(secondReader.inventory.size,0);
 const secondBudget={shared:secondReader.budget,carriedBytes:0};
 const second=f.api.qualifyCheckpoint({reader:secondReader,budget:secondBudget});assert.equal(second.available,true);
 assert.notStrictEqual(secondReader.inventory,f.reader.inventory);
 f.api.releaseCheckpoint(first.state);assert.deepEqual(f.api.projectNativeRows({state:second.state,rows:[1],budget:secondBudget}).rows,[{y:1,runs:[[0,1,2]]}]);
});


test('accepted AUS producer limits retain canonical optional log bounds and reject nearby unsupported admission',()=>{
 // Exact limits from accepted40d792b2 request, pinned by the AUS advance-002
 // rebind certificate1b4e5c60. The ordinary output cap is checked at the call.
 const limits={complete_phase_bytes:536870912,descriptors:512,monitor_bytes:4194304,
  output_bytes:16777216,rss_bytes:805306368,sampled_stop_bytes:704643072,
  stderr_bytes:40960,stdout_bytes:8192,wall_seconds:1200};
 assert.strictEqual(validateCurrentRebindLimits(limits),limits);
 const legacy={...limits};delete legacy.monitor_bytes;delete legacy.stderr_bytes;delete legacy.stdout_bytes;
 assert.strictEqual(validateCurrentRebindLimits(legacy),legacy);
 for(const edit of [x=>{x.unreviewed_bytes=1;},x=>{delete x.complete_phase_bytes;},x=>{x.monitor_bytes=0;},
  x=>{x.stderr_bytes=33554433;},x=>{x.stdout_bytes=1.5;},x=>{x.descriptors=513;},
  x=>{x.sampled_stop_bytes=x.rss_bytes+1;},x=>{x.output_bytes=Number.MAX_SAFE_INTEGER;}]){
  const bad={...limits};edit(bad);assert.throws(()=>validateCurrentRebindLimits(bad));
 }
});

test('archived JavaScript execution roles can evolve while same-extension scientific inputs stay pinned',async t=>{
 const f=await trustedFixture(t,{codeRoutes:true});
 fs.appendFileSync(path.join(f.root,'src/native-grid.js'),'\n// Reviewed native-only support.\n');const newer=f.commit();
 const reader=new f.native.ImmutableReader(f.root,newer,{allowance:f.reader.allowance}),budget={shared:reader.budget,carriedBytes:0};
 const qualified=f.api.qualifyCheckpoint({reader,budget});assert.equal(qualified.available,true);
 const transition=f.api.qualifyTransition({state:qualified.state,reader,budget});assert.equal(transition.available,true);
 // A .js suffix alone does not exempt scientific bytes from the old census.
 f.save('data/scientific.js',{fixture:'changed scientific input'});const changed=f.commit();
 const candidate=new f.native.ImmutableReader(f.root,changed,{allowance:reader.allowance,budget:reader.budget});
 const rejected=f.api.qualifyTransition({state:qualified.state,reader:candidate,budget});
 assert.equal(rejected.available,false);assert.match(rejected.reason,/route changed/);
 fs.appendFileSync(path.join(f.root,'src/native-grid.js'),'\n// Uncommitted executable drift.\n');
 const dirty=new f.native.ImmutableReader(f.root,newer,{allowance:reader.allowance});
 assert.throws(()=>f.api.qualifyCheckpoint({reader:dirty,budget:{shared:dirty.budget,carriedBytes:0}}),/changed executing checkpoint method/);
 f.api.releaseCheckpoint(qualified.state);
});

test('actual appended authority survives complete checks, a subsequent transition and original native projection',async t=>{
 const f=await trustedFixture(t,{nativeAppend:true}),baseline=f.api.qualifyCheckpoint({reader:f.reader,budget:f.budget});
 const next=await appendNativeAuthority(f),reader=new f.native.ImmutableReader(f.root,next.candidate,{allowance:f.reader.allowance,budget:f.reader.budget});
 const transition=f.api.qualifyTransition({state:baseline.state,reader,budget:f.budget});
 assert.equal(transition.available,true);assert.deepEqual(transition.changedIds,['A']);assert.deepEqual(transition.changedNativeRows,[next.y]);
 assert.deepEqual(transition.candidate.ledger.rows,next.ledger.rows);assert.deepEqual(transition.candidate.patch.rows,next.patch.rows);
 assert.deepEqual(transition.candidate.additions.at(-1).native_rows,next.proof.original_ledger.rows[0].native_rows);
 assert.deepEqual(baseline.state.ledger.rows,f.ledger.rows);assert(Object.isFrozen(transition.candidate));
 f.save('later-unrelated.json',{later:true});const later=f.commit();
 const laterReader=new f.native.ImmutableReader(f.root,later,{allowance:f.reader.allowance,budget:f.reader.budget});
 const again=f.api.qualifyTransition({state:transition.candidate,reader:laterReader,budget:f.budget});
 assert.equal(again.available,true);assert.deepEqual(again.changedIds,[]);assert.deepEqual(again.changedNativeRows,[]);
 assert.deepEqual(again.candidate.patch.rows,next.patch.rows);
 const projected=f.api.projectNativeRows({state:again.candidate,rows:[next.y],budget:f.budget});
 assert.deepEqual(projected.rows,[{y:next.y,runs:[]}]);
 assert.equal(f.api.checkpointRouteCensus({transition:again,budget:f.budget}).candidate_commit,later);
 f.api.releaseCheckpoint(baseline.state);
});

for(const [name,options,expected] of [
 ['omitted appended scope',{mutateLedger:l=>{l.rows=l.rows.filter(p=>!p.component_id.startsWith('source-target:'));}},/omitted\/invented complete appended ledger scope/],
 ['invented appended exception',{mutateLedger:(l,p,e)=>{l.rows.push({component_id:'source-target:invented',disposition:'rejected',reason:'invented',authority_sha256:e.authority_sha256});}},/omitted\/invented complete appended ledger scope/],
 ['changed appended literal',{mutateLedger:l=>{l.rows.at(-1).source_receipt_sha256='0'.repeat(64);}},/changed original appended primitive or exception/],
 ['duplicate original component',{duplicateAuthority:true},/repeats original component/],
 ['changed complete native contract',{mutateEvidence:e=>{e.native_contract.coordinateBits++;}},/native contract or complete original source denominator/],
 ['changed original authority base',{mutateEvidence:e=>{e.base_reference={...e.base_reference,footprints_sha256:'0'.repeat(64)};}},/different selected base/],
 ['changed full source denominator',{mutateLedger:l=>{l.parent_inventory={...l.parent_inventory,components:3};}},/original source\/scope denominator/],
 ['changed old exception',{mutateLedger:l=>{l.rows.find(p=>p.component_id==='rejected').reason='changed old exception';}},/Old complete ledger primitive/],
 ['cumulative patch reassignment',{mutatePatch:p=>{p.rows.at(-1).runs[0][2]=2;}},/omitted, invented or reassigned original native intervals/]
])test('real appended authority refuses '+name,async t=>{
 const f=await trustedFixture(t,{nativeAppend:true}),{state}=f.api.qualifyCheckpoint({reader:f.reader,budget:f.budget});
 const next=await appendNativeAuthority(f,options),reader=new f.native.ImmutableReader(f.root,next.candidate,{allowance:f.reader.allowance,budget:f.reader.budget});
 assert.throws(()=>f.api.qualifyTransition({state,reader,budget:f.budget}),expected);
 assert.deepEqual(state.ledger.rows,f.ledger.rows);f.api.releaseCheckpoint(state);
});

test('failed complete literal check retires only dead proof charge and keeps baseline retry and caller carry honest',async t=>{
 const f=await trustedFixture(t,{nativeAppend:true}),{state}=f.api.qualifyCheckpoint({reader:f.reader,budget:f.budget});
 f.api.projectSourceFeatures({state,ids:[],budget:f.budget});const before=f.reader.metadataBytes;
 const next=await appendNativeAuthority(f,{mutateLedger:l=>{l.rows.at(-1).source_receipt_sha256='0'.repeat(64);}});
 const reader=new f.native.ImmutableReader(f.root,next.candidate,{allowance:f.reader.allowance,budget:f.reader.budget});
 assert.throws(()=>f.api.qualifyTransition({state,reader,budget:f.budget}),/changed original appended primitive/);
 const failedUsed=reader.used,failedCharged=reader.charged;
 assert(failedUsed>before);assert(failedCharged.size>0);
 const {normaliseRetainedRepairLedger}=await import(pathToFileURL(path.join(f.root,CODE[1])));
 const selected={selection:next.selection,sidecar:next.sidecar,registry:next.registry,ledger:next.ledger,patch:next.patch,envelope:next.envelope,
  normalized:normaliseRetainedRepairLedger(next.ledger,next.registry)};
 f.api.projectSourceFeatures({state,ids:[],budget:f.budget});
 assert.equal(f.reader.metadataBytes-before,7*valueBytes(selected).length+7*valueBytes({inverse:[],inputs:[],actualInputs:[]}).length,
  'full proof/expectedAdded charge must end after the failed helper frame; selected caller state remains conservatively retained');
 const carry=f.budget.carriedBytes;f.budget.carriedBytes=carry-1;
 assert.throws(()=>f.api.projectSourceFeatures({state,ids:[],budget:f.budget}),/reset or undercharged/);f.budget.carriedBytes=carry;
 const recovered=await appendNativeAuthority(f,{name:'recovered'}),retryReader=new f.native.ImmutableReader(f.root,recovered.candidate,{allowance:f.reader.allowance,budget:f.reader.budget});
 assert.equal(f.api.qualifyTransition({state,reader:retryReader,budget:f.budget}).available,true);
 f.api.releaseCheckpoint(state);
});

test('a second unfinished authority carries the first full proof until complete duplicate checks unwind',async t=>{
 const f=await trustedFixture(t,{nativeAppend:true}),{state}=f.api.qualifyCheckpoint({reader:f.reader,budget:f.budget});
 f.api.projectSourceFeatures({state,ids:[],budget:f.budget});const before=f.reader.metadataBytes;
 const next=await appendNativeAuthority(f,{duplicateAuthority:true}),seen=[],read=f.native.ImmutableReader.prototype.read;
 f.native.ImmutableReader.prototype.read=function(name,...args){
  if(name==='appended/evidence.json')seen.push(this.metadataBytes);
  return read.call(this,name,...args);
 };
 try {
  const reader=new f.native.ImmutableReader(f.root,next.candidate,{allowance:f.reader.allowance,budget:f.reader.budget});
  assert.throws(()=>f.api.qualifyTransition({state,reader,budget:f.budget}),/repeats original component/);
 } finally {f.native.ImmutableReader.prototype.read=read;}
 const first=next.registry.entries.find(p=>p.authority_sha256!==f.registry.entries[0].authority_sha256);
 const full={entry:first,nativeOnly:true,patches:next.proof.native_proof.native_patches,ledger:next.proof.original_ledger,
  contract:next.proof.native_proof.native_contract,source_scope_ids:next.proof.source_scope_ids};
 assert.equal(seen.length,2);assert.equal(seen[1]-seen[0],7*valueBytes(full).length,
  'the first full wrapper remains charged while a later appended proof and its complete duplicate checks are unfinished');
 const {normaliseRetainedRepairLedger}=await import(pathToFileURL(path.join(f.root,CODE[1])));
 const selected={selection:next.selection,sidecar:next.sidecar,registry:next.registry,ledger:next.ledger,patch:next.patch,envelope:next.envelope,
  normalized:normaliseRetainedRepairLedger(next.ledger,next.registry)};
 f.api.projectSourceFeatures({state,ids:[],budget:f.budget});
 assert.equal(f.reader.metadataBytes-before,7*valueBytes(selected).length+7*valueBytes({inverse:[],inputs:[],actualInputs:[]}).length);
 f.api.releaseCheckpoint(state);
});

test('completed authority keeps genuine live caller buffers admitted and refuses a tight next-phase overflow',async t=>{
 const f=await trustedFixture(t,{nativeAppend:true}),{state}=f.api.qualifyCheckpoint({reader:f.reader,budget:f.budget});
 const live={first:Buffer.alloc(65536,0x5a)};f.budget.carriedBytes+=live.first.byteLength;
 const next=await appendNativeAuthority(f),reader=new f.native.ImmutableReader(f.root,next.candidate,{allowance:f.reader.allowance,budget:f.reader.budget});
 const transition=f.api.qualifyTransition({state,reader,budget:f.budget});assert.equal(transition.available,true);
 f.api.projectSourceFeatures({state:transition.candidate,ids:[],budget:f.budget});
 const used=reader.used,charged=reader.charged,phase=reader.allowance.phaseBytes,carry=f.budget.carriedBytes;
 assert(reader.metadataBytes>=live.first.byteLength);assert(used<phase);
 live.second=Buffer.alloc(32768,0xa5);
 reader.allowance.phaseBytes=used+live.second.byteLength-1;f.budget.carriedBytes+=live.second.byteLength;
 assert.throws(()=>f.api.projectSourceFeatures({state:transition.candidate,ids:[],budget:f.budget}),/External carried-state increase exceeds current allowance/);
 assert.equal(reader.used,used);assert.strictEqual(reader.charged,charged);
 // Both buffers remain strongly reachable across the next-phase admission and
 // refusal, rather than declaring bytes for memory that has already gone away.
 assert.equal(live.first.reduce((n,v)=>n+v,0),65536*0x5a);
 assert.equal(live.second.reduce((n,v)=>n+v,0),32768*0xa5);
 reader.allowance.phaseBytes=phase;f.budget.carriedBytes=carry;f.api.releaseCheckpoint(state);
});
