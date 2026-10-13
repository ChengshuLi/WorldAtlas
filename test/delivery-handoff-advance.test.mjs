import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {ImmutableReader} from '../scripts/check-effective-geographic-regression.mjs';
import {valueBytes} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
import {constructOriginalAuthority, constructAuthorityRegistry} from '../scripts/delivery-handoff-advance.mjs';
import {materializeRecipe, modelRequestBudget, recheckNativeRequest} from '../scripts/delivery-handoff-advance.mjs';
import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {locate, readPreparedStage, nativeConfigFromStages} from '../scripts/delivery-handoff-advance.mjs';
const digest = raw => createHash('sha256').update(raw).digest('hex');
const commit = 'a'.repeat(40), later = 'b'.repeat(40);
function fixture() {
  const files = new Map(), pins = new Map();
  function add(version, name, value) {
    const raw = Buffer.from(JSON.stringify(value) + '\n');
    const pin = {commit: version, path: name, mode: '100644', git_blob_oid: digest(raw).slice(0, 40), bytes: raw.length, sha256: digest(raw)};
    files.set(version + ':' + name, raw); pins.set(version + ':' + name, pin); return pin;
  }
  function stage(version, prefix, phase, values) {
    const outputs = {};
    for (const [name, value] of Object.entries(values)) { const pin = add(version, prefix + '/' + name, value); outputs[name] = {bytes: pin.bytes, sha256: pin.sha256}; }
    add(version, prefix + '/preparation.json', {version: 1, binding: {phase, config_sha256: 'c'.repeat(64)}, outputs});
    return {commit: version, path: prefix + '/preparation.json'};
  }
  const reader = {pin: (version, name) => {const pin = pins.get(version + ':' + name); assert.ok(pin, name); return pin;},
    read: pin => files.get(pin.commit + ':' + pin.path), json: pin => JSON.parse(files.get(pin.commit + ':' + pin.path))};
  return {reader, files, pins, add, stage};
}
test('locators derive descriptors and refuse handwritten hashes', () => {
  const f = fixture(); const pin = f.add(commit, 'one.json', {real: true});
  assert.deepEqual(locate(f.reader, {commit, path: 'one.json'}), pin);
  assert.throws(() => locate(f.reader, {commit, path: 'one.json', sha256: pin.sha256}), /handwritten/);
  assert.throws(() => locate(f.reader, {commit, path: '../one.json'}), /locator/);
});
test('committed completion inventory authenticates whole bytes and phase', () => {
  const f = fixture(), locator = f.stage(commit, 'phase', 'requests', {'request.json': {one: true}});
  assert.equal(readPreparedStage(f.reader, locator, 'requests').outputs['request.json'].sha256, f.pins.get(commit + ':phase/request.json').sha256);
  assert.throws(() => readPreparedStage(f.reader, locator, 'retain'), /phase/);
  f.files.set(commit + ':phase/request.json', Buffer.from('drift'));
  assert.throws(() => readPreparedStage(f.reader, locator, 'requests'), /differs/);
});
test('native transition takes original request identity and group order from saved index', () => {
  const f = fixture(), request = {source_rule: {expected_ids: ['b', 'a']}};
  const requests = f.stage(commit, 'issued', 'requests', {'g-source-request.json': request,
    'requests.json': {version: 1, groups: [{id: 'g', request: 'g-source-request.json', component_ids: ['b', 'a']}]}});
  const original = f.reader.pin(commit, 'issued/g-source-request.json');
  const retained = {g: f.stage(later, 'retained', 'retain', {'request.json': request, 'facts.json': {request: original},
    'terminal.json': {qualified: true}, 'publication.json': {complete: true}, 'inventory.jsonl.gz': {opaque: true}})};
  f.add(commit, 'native-template.json', {operation: 'placeholder-for-existing-constructor'});
  const templates = {g: {locator: {commit, path: 'native-template.json'}, destination: '.cache/native-grid-candidates/g-native'}};
  const config = nativeConfigFromStages(f.reader, {requests, retained, templates});
  assert.deepEqual(config.groups[0].source.request, original);
  assert.equal(config.groups[0].source.facts.commit, later);
  assert.deepEqual(nativeConfigFromStages(f.reader, {requests, retained, templates}), config);
  assert.throws(() => nativeConfigFromStages(f.reader, {requests, retained: {}, templates}), /group binding/);
  const alias = f.stage(later, 'issued', 'requests', {'g-source-request.json': request,
    'requests.json': {version: 1, groups: [{id: 'g', request: 'g-source-request.json', component_ids: ['b', 'a']}]}});
  assert.deepEqual(nativeConfigFromStages(f.reader, {requests: alias, retained, templates}).groups[0].source.request, original);
});

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {openAdvanceJournal, withAdvanceLock, prepareAdvanceStage, readAdvanceStatus, observeAdvance, advanceQueue} from '../scripts/delivery-handoff-advance.mjs';
function journal(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'delivery-advance-'));
  t.after(() => fs.rmSync(root, {recursive: true, force: true}));
  let time = 1000;
  const value = openAdvanceJournal(root, '.cache/delivery-handoff/one', {commit, path: 'recipe.json'}, {now: () => time});
  return {...value, tick: ms => { time += ms; }};
}
test('package receipts bind immutable input and preserve interrupted legacy receipt bytes', async t => {
  const j=journal(t), config={version:1, scope:'ordinary'}, products={'package-roles.json':Buffer.from('{}\n')};
  await withAdvanceLock(j,()=>prepareAdvanceStage(j,'package','package',config,()=>products));
  const filename=path.join(j.target,'package','preparation.json'), receipt=JSON.parse(fs.readFileSync(filename));
  assert.deepEqual(receipt.input,config);
  const changed=structuredClone(receipt);changed.input.scope='foreign';fs.writeFileSync(filename,JSON.stringify(changed)+'\n');
  assert.throws(()=>readAdvanceStatus(j),/inventory differs/);
  delete receipt.input;
  // Reproduce the canonical old producer format, including nested bindings.
  const canonical=v=>Array.isArray(v)?v.map(canonical):v&&typeof v==='object'?Object.fromEntries(Object.keys(v).sort().map(k=>[k,canonical(v[k])])):v;
  const legacy=Buffer.from(JSON.stringify(canonical(receipt))+'\n');fs.writeFileSync(filename,legacy);
  fs.unlinkSync(path.join(j.stateTarget,'package.completed.json'));
  await withAdvanceLock(j,()=>prepareAdvanceStage(j,'package','package',config,()=>products));
  assert.deepEqual(fs.readFileSync(filename),legacy);
  assert.deepEqual(readAdvanceStatus(j).completed,['package']);
});

test('interrupted metadata resumes identical postimages and only completes once', async t => {
  const j = journal(t), products = {'a.json': Buffer.from('{}\n'), 'b.json': Buffer.from('[]\n')};
  let stopped = false;
  await assert.rejects(withAdvanceLock(j, () => prepareAdvanceStage(j, 'requests', 'requests', {one: 1}, () => products,
    {interrupt: name => { if (name === 'a.json' && !stopped) { stopped = true; throw Error('interrupted'); } }})), /interrupted/);
  assert.deepEqual(readAdvanceStatus(j).completed, []);
  assert.equal(fs.existsSync(path.join(j.target, 'requests', 'preparation.json')), false);
  await withAdvanceLock(j, () => prepareAdvanceStage(j, 'requests', 'requests', {one: 1}, () => products));
  const before = fs.readFileSync(path.join(j.stateTarget, 'requests.completed.json'));
  const repeated = await withAdvanceLock(j, () => prepareAdvanceStage(j, 'requests', 'requests', {one: 1}, () => { throw Error('completed stage reran'); }));
  assert.equal(repeated.resumed, true);
  assert.deepEqual(fs.readFileSync(path.join(j.stateTarget, 'requests.completed.json')), before);
  assert.deepEqual(readAdvanceStatus(j).completed, ['requests']);
  await assert.rejects(prepareAdvanceStage(j, 'requests', 'requests', {one: 2}, () => products), /Changed stage inputs/);
});
test('partial collision, changed bytes, symlink and foreign recipe refuse without replacement', async t => {
  const j = journal(t), products = {'a.json': Buffer.from('{}\n')};
  await assert.rejects(prepareAdvanceStage(j, 'requests', 'requests', {}, () => products, {interrupt: () => { throw Error('stop'); }}), /stop/);
  const sentinel = Buffer.from('foreign'); fs.writeFileSync(path.join(j.target, 'requests', 'a.json'), sentinel);
  await assert.rejects(prepareAdvanceStage(j, 'requests', 'requests', {}, () => products), /foreign\/changed/);
  assert.deepEqual(fs.readFileSync(path.join(j.target, 'requests', 'a.json')), sentinel);
  assert.throws(() => openAdvanceJournal(j.root, j.destination, {commit: later, path: 'recipe.json'}, {resume: true}), /Foreign/);
  assert.throws(() => openAdvanceJournal(j.root, j.destination, j.intent.recipe), /Occupied/);
  fs.symlinkSync(j.target, path.join(j.root, 'link'));
  assert.throws(() => openAdvanceJournal(j.root, 'link/run', j.intent.recipe), /bounded/);
});
test('status validates completed bytes and observations distinguish wait from preparation', async t => {
  const j = journal(t); observeAdvance(j, {status: 'waiting', kind: 'commit', stage: 'requests'}); j.tick(5000);
  observeAdvance(j, {status: 'waiting', kind: 'commit', stage: 'requests'});
  assert.equal(readAdvanceStatus(j).timing.external_observations.length, 1);
  await prepareAdvanceStage(j, 'requests', 'requests', {}, () => ({'a.json': Buffer.from('{}\n')}));
  const s = readAdvanceStatus(j); assert.equal(s.timing.overall_wall_ms, 5000); assert.ok(s.timing.preparation_ms >= 0);
  fs.writeFileSync(path.join(j.target, 'requests', 'a.json'), 'drift');
  assert.throws(() => readAdvanceStatus(j), /changed/);
});
test('direct Actions identity is durable before uncertain submit and resume cannot redispatch', async t => {
  const j = journal(t), packet = {repo: 'ChengshuLi/WorldAtlas', pr_number: 1, head_sha: commit};
  let calls = 0, identity;
  const checkReview = async () => ({...packet, review_comment_id: 123});
  const submit = async options => {
    const saved = JSON.parse(fs.readFileSync(path.join(j.stateTarget, 'queue-submission.json')));
    assert.equal(saved.request_id, options.requestId); identity = options.requestId;
    calls++; throw Error('uncertain POST');
  };
  let pr = {merged: false, head: {sha: commit}};
  const api = async route => {assert.equal(route, '/repos/ChengshuLi/WorldAtlas/pulls/1'); return pr;};
  assert.equal((await advanceQueue(j, packet, {checkReview})).status, 'ready-for-queue');
  assert.equal(fs.existsSync(path.join(j.stateTarget, 'queue-submission.json')), false);
  await assert.rejects(advanceQueue(j, packet, {authorizeSubmission: true, checkReview, submit, api}), /uncertain/);
  const pending = await advanceQueue(j, packet, {authorizeSubmission: true, checkReview, submit, api});
  assert.equal(pending.status, 'pending'); assert.equal(pending.request_id, identity);
  assert.match(pending.next, /gh run list\/view\/watch/); assert.match(pending.next, /100 pending/);
  assert.match(pending.next, /failed\/canceled/); assert.equal(calls, 1);
  pr = {merged: true, head: {sha: commit}, merge_commit_sha: later};
  assert.equal((await advanceQueue(j, packet, {api})).accepted, true);
  pr.merge_commit_sha = null;
  assert.equal((await advanceQueue(j, packet, {api})).accepted, false);
  pr.head.sha = later;
  await assert.rejects(advanceQueue(j, packet, {api}), /head changed/);
  await assert.rejects(advanceQueue(j, {...packet, head_sha: later}, {api}), /another target/);
  assert.equal(calls, 1);
});
test('missing independent acceptance never writes a queue identity', async t => {
  const j = journal(t);
  await assert.rejects(advanceQueue(j, {repo: 'ChengshuLi/WorldAtlas', pr_number: 1, head_sha: commit},
    {authorizeSubmission: true, checkReview: async () => { throw Error('stale review'); }}), /stale review/);
  assert.equal(fs.existsSync(path.join(j.stateTarget, 'queue-submission.json')), false);
});

// recipe constructor controls
{
const commit='a'.repeat(40),hash=x=>createHash('sha256').update(x).digest('hex');
const clone=x=>structuredClone(x);
function fixture({physicalBytes=2000,decodedBytes=5000,phase=4*1024*1024,legacy=false}={}){
 const files=new Map();
 const pin=(path,bytes=123,extra={})=>({commit,path,mode:'100644',blob:hash(path).slice(0,40),bytes,sha256:hash(path),...extra});
 const put=(path,body)=>{const raw=Buffer.from(JSON.stringify(body)+'\n');const p={...pin(path,raw.length),sha256:hash(raw)};files.set(path,{raw,body,pin:p});return {commit,path};};
 const reader={pin(c,path){assert.equal(c,commit);assert.ok(files.has(path),path);const p=files.get(path).pin;return {...p,git_blob_oid:p.blob};},read(p){const f=files.get(p.path);assert.ok(f,p.path);assert.equal(p.sha256,f.pin.sha256);return f.raw;},json(p){this.read(p);return clone(files.get(p.path).body);}};
 const oldCode={path:'code.mjs',bytes:50,sha256:hash('code')};
 const support=[{path:'scripts/local-workspace.mjs',bytes:50,sha256:hash('local')},{path:'scripts/worker-identity.mjs',bytes:50,sha256:hash('worker')}];
 const runtime={version:1,platform:'linux',runtime:['git','node','process-inspector','time'].map(role=>({role,path:'/bin/'+role,mode:493,bytes:1000,sha256:hash(role)})),supervisor:{path:'coordination/engineering/melanesia363-additive-delivery-20261010/supervise-source-native-linux.mjs',bytes:1000,sha256:hash('supervisor')},...(!legacy?{support_code:support}:{})};
 const resources={processing_allowance:{phaseBytes:phase,rssBytes:8*1024*1024},output_reserve:131072,operating_limits:{rss_bytes:8*1024*1024,wall_seconds:30,output_bytes:262144,retained_bytes:600000,log_bytes:1000,monitor_bytes:1000,receipt_bytes:1000}};
 const common={version:1,executed_code:[oldCode],installed_modules:[{...oldCode,path:'node_modules/module.js'}],report:pin('report.json'),parent:{components:3},baseline:{pins:[pin('selection.json')]},output_reserve:131072,operating_runtime:runtime,...(!legacy?{operating_profile:'source-native-v2',...resources}:{})};
 const componentIds=['c-a','c-b','c-c'],targetIds=['t-one'];
 const physicalPins=componentIds.map((id,i)=>pin('retained/components-00'+i+'.jsonl.gz',physicalBytes));
 const sourceMeta=pin('retained/sources-000.jsonl.gz',100);
 const admin=pin('admin.gz',100,{uncompressed_bytes:1000,uncompressed_sha256:hash('decoded-admin')});
 const locator=put('locators.json',Object.fromEntries(componentIds.map((id,i)=>[id,{path:'components-00'+i+'.jsonl.gz'}])));
 const handoff={scopeIds:componentIds,candidate_source_native_bindings:componentIds.map(component_id=>({component_id,retained_payload:{target_stable_location_id:'t-one'}})),
  original_physical_comparison_bindings:componentIds.map(component_id=>({component_id,physical_comparison:{row:{component_id}},original_queried_source_metadata:[]})),
  original_gap_membership:{members:componentIds.map((component_id,i)=>({component_id,original_batch_id:'unrelated-'+i}))},
  consumed_inputs:[files.get(locator.path).pin,...physicalPins,sourceMeta],
  consumed_source_bindings:[{source_id:'admin',catalogue_record:{parts:[{path:admin.path,bytes:admin.bytes,sha256:admin.sha256,uncompressed_bytes:admin.uncompressed_bytes,uncompressed_sha256:admin.uncompressed_sha256}]}}],
  physical_restoration:{restorations:[...physicalPins.map((p,i)=>({path:'components-00'+i+'.jsonl.gz',whole_original_bytes:p.bytes,whole_original_sha256:p.sha256,decoded_bytes:decodedBytes,decoded_sha256:hash('decoded-'+i),rows:1})),{path:'sources-000.jsonl.gz',whole_original_bytes:100,whole_original_sha256:sourceMeta.sha256,decoded_bytes:500,decoded_sha256:hash('source-decoded'),rows:3}]}};
 const handoffLocator=put('handoff.json',handoff),hp=files.get(handoffLocator.path).pin;
 const {commit:_,...entrySource}=hp;
 const registry=put('registry.json',{version:1,kind:'accepted-administrative-handoffs-v1',entries:[{id:'accepted-whole',accepted_source_commit:commit,source:entrySource,cohort_ids:componentIds,target_ids:targetIds}]});
 const rp=files.get(registry.path).pin,bank=pin('bank.json'),manifest=pin('manifest.json'),bounds=pin('bounds.gz',100,{uncompressed_bytes:1000,uncompressed_sha256:hash('bounds')}),catalogue=pin('catalogue.json');
 const source={...clone(common),operation:'retained-land-source-premises-v1',destination:'.cache/native-grid-candidates/old-source',source_rule:{version:1,profile:'retained-consumed-administrative-source',geometry_scope:'full-component',cohort_ids:componentIds,expected_ids:componentIds,registry_path:rp.path,
  ...Object.fromEntries(['cases_path','outcomes_path','payloads_path','simplified_comparison_path','generalized_comparison_path','remainders_path'].map(k=>[k,hp.path])),
  administrative_products:[admin],original_products:[],target_banks:[bank.path],manifest_path:manifest.path,bounds_path:bounds.path,source_catalogue_path:catalogue.path,inputs:[hp,rp,admin,bank,manifest,bounds,catalogue]}};
 const sourceTemplate=put('source-template.json',source),slots={source_request_path:files.get(sourceTemplate.path).pin,operating_path:pin('operating.json'),publication_path:pin('publication.json'),facts_path:pin('facts.json'),inventory_path:pin('inventory.gz',100,{uncompressed_bytes:1000,uncompressed_sha256:hash('inventory')})};
 const owner=pin('native-owner.gz',200,{uncompressed_bytes:1000,uncompressed_sha256:hash('owner')}),lat=pin('latitudes.gz',50,{uncompressed_bytes:100,uncompressed_sha256:hash('lat')});
 const native={...clone(common),operation:'unactivated-additive-native-batch-v1',destination:'.cache/native-grid-candidates/old-native',additive:{source_profile:source.source_rule.profile,scope_ids:componentIds,source_execution_commit:commit,source_runtime:{bytes:1000,sha256:hash('node')},manifest_path:manifest.path,bounds_path:bounds.path,latitudes_path:lat.path,original_bounds:{sha256:bounds.sha256},owner_parts:[{path:owner.path,manifest_path:'owner.bin',manifest_descriptor:{bytes:owner.bytes}}],...Object.fromEntries(Object.entries(slots).map(([k,p])=>[k,p.path])),inputs:[...source.source_rule.inputs,owner,lat,...Object.values(slots)]}};
 const nativeTemplate=put('native-template.json',native);
 const selection={handoff_id:'accepted-whole',source_template:sourceTemplate,source_resources:clone(resources),native_resources:clone(resources),physical_locator:{input:locator,format:'keyed-path'},targets:[{target_id:'t-one',bank_path:bank.path,native_template:nativeTemplate}],
  predecessor_allowance:Object.fromEntries(Object.keys(slots).map(k=>[k,{bytes:k==='source_request_path'?131072:1000,...(k==='inventory_path'?{uncompressed_bytes:10000}:{})}])),native_request_bytes_bound:131072};
 const recipe={version:1,id:'delivery',mode:'greedy-model',registry,destination_prefix:'.cache/native-grid-candidates/delivery',handoffs:[selection]};
 return {reader,recipe,files,put,pin,selection,resources,source,native,sourceTemplate,nativeTemplate,componentIds,handoff,locator,registry};
}

// Exact metadata excerpts from the accepted AUS handoff. No geometry/body reads
// or new scientific acceptance are represented by this constructor fixture.
const ausCustody=JSON.parse(fs.readFileSync(new URL('./fixtures/delivery-aus-custody.json',import.meta.url)));
function ausCustodyFixture(){
 const f=fixture({phase:128*1024*1024}),h=f.files.get('handoff.json').body;
 h.consumed_source_bindings=clone(ausCustody.consumed_source_bindings);
 h.reused_whole_product_inputs=clone(ausCustody.reused_whole_product_inputs);
 h.consumed_inputs=h.consumed_inputs.filter(p=>p.path==='locators.json');
 h.physical_restoration.restorations=clone(ausCustody.restorations);
 const componentProducts=ausCustody.restorations.filter(p=>p.path.startsWith('components-'));
 f.put('locators.json',Object.fromEntries(f.componentIds.map((id,i)=>[id,{path:componentProducts[i].path}])));
 h.consumed_inputs=[f.files.get('locators.json').pin];
 const part=h.consumed_source_bindings[0].original_source_custody.catalogue_record.parts[0];
 const admin={...f.pin(part.path,part.bytes),sha256:part.sha256,
  uncompressed_bytes:part.uncompressed_bytes,uncompressed_sha256:part.uncompressed_sha256};
 for(const request of [f.source,f.native]){
  const stage=request.source_rule??request.additive;
  stage.inputs=stage.inputs.filter(p=>p.path!=='admin.gz');stage.inputs.push(admin);
 }
 f.source.source_rule.administrative_products=[admin];
 for(const resources of [f.selection.source_resources,f.selection.native_resources]){
  resources.processing_allowance.rssBytes=256*1024*1024;
  resources.operating_limits.rss_bytes=256*1024*1024;
 }
 return {...f,h,admin,componentProducts};
}

test('accepted AUS custody schema resolves complete administrative and reused physical identities without mutation',()=>{
 const f=ausCustodyFixture(),before=clone(f.h),out=materializeRecipe(f.recipe,f.reader);
 const source=JSON.parse(out.products[out.groups[0].source_template]);
 assert.deepEqual(source.source_rule.administrative_products,[f.admin]);
 const physical=out.acquisition_plan.products.filter(p=>p.uses.includes('physical-product'));
 const wanted=[...f.componentProducts.slice(0,f.componentIds.length).map(p=>p.path),'sources-000.jsonl.gz'];
 assert.equal(physical.length,wanted.length);
 for(const name of wanted){
  const restoration=ausCustody.restorations.find(p=>p.path===name);
  const original=ausCustody.reused_whole_product_inputs.find(p=>p.sha256===restoration.whole_original_sha256);
  const planned=physical.find(p=>p.destinations.some(d=>d.endsWith('/'+name)));
  const {consumption_basis,whole_body_consumed,...pin}=original;
  assert.deepEqual(planned.source,pin);
  assert.equal(whole_body_consumed,false);assert.ok(consumption_basis);
  const input=source.source_rule.inputs.find(p=>p.original_product_path===name);
  assert.equal(input.uncompressed_bytes,restoration.decoded_bytes);
  assert.equal(input.uncompressed_sha256,restoration.decoded_sha256);
 }
 assert.deepEqual(f.h,before);
});

test('equal direct and nested catalogue aliases preserve the same complete request bytes',()=>{
 const f=ausCustodyFixture(),nested=materializeRecipe(f.recipe,f.reader);
 const record=f.h.consumed_source_bindings[0];
 record.catalogue_record=clone(record.original_source_custody.catalogue_record);
 assert.deepEqual(materializeRecipe(f.recipe,f.reader).products,nested.products);
 delete record.original_source_custody;
 assert.deepEqual(materializeRecipe(f.recipe,f.reader).products,nested.products);
});

test('catalogue normalization refuses malformed, missing and conflicting aliases or source identities',()=>{
 const changes=[
  r=>{delete r.original_source_custody;},
  r=>{r.original_source_custody=null;},
  r=>{r.original_source_custody.catalogue_record=null;},
  r=>{r.original_source_custody.catalogue_record.parts=[];},
  r=>{r.original_source_custody.catalogue_record.parts=[null];},
  r=>{r.catalogue_record=clone(r.original_source_custody.catalogue_record);delete r.original_source_custody.catalogue_record;},
  r=>{r.catalogue_record={...clone(r.original_source_custody.catalogue_record),recorded_license:'foreign'};},
  r=>{r.catalogue_record=null;},
  r=>{r.original_source_custody.source_id='foreign';},
  r=>{r.original_source_custody.catalogue_record.key='foreign';},
  r=>{r.whole_sha256='0'.repeat(64);},
  r=>{r.whole_bytes++;},
  r=>{delete r.source_id;},
  r=>{r.original_source_custody.catalogue_record.parts[0].uncompressed_sha256='0'.repeat(64);},
 ];
 for(const change of changes){const f=ausCustodyFixture();change(f.h.consumed_source_bindings[0]);
  assert.throws(()=>materializeRecipe(f.recipe,f.reader),/administrative/);}
});

test('reused physical custody refuses missing, malformed and contradictory product identities',()=>{
 const changes=[
  h=>{delete h.reused_whole_product_inputs;},
  h=>{h.reused_whole_product_inputs={};},
  h=>{h.reused_whole_product_inputs[0].whole_body_consumed=true;},
  h=>{h.reused_whole_product_inputs[0].bytes++;},
  h=>{h.reused_whole_product_inputs[0].uncompressed_sha256='0'.repeat(64);},
  h=>{h.consumed_inputs.push({...h.reused_whole_product_inputs[0],commit:'b'.repeat(40)});},
  h=>{h.consumed_inputs.push({...h.reused_whole_product_inputs[0],sha256:'b'.repeat(64)});},
  h=>{h.reused_whole_product_inputs[0].git_blob_oid='b'.repeat(40);},
 ];
 for(const change of changes){const f=ausCustodyFixture();change(f.h);
  assert.throws(()=>materializeRecipe(f.recipe,f.reader),/physical|Conflicting input path/);}
});

test('existing exact physical transport aliases remain valid without erasing reuse provenance',()=>{
 const f=ausCustodyFixture(),before=materializeRecipe(f.recipe,f.reader);
 const original=f.h.reused_whole_product_inputs[0],{whole_body_consumed,consumption_basis,...pin}=original;
 f.h.consumed_inputs.push(pin);
 assert.deepEqual(materializeRecipe(f.recipe,f.reader).products,before.products);
 f.h.consumed_inputs.push({...pin,path:'another/exact-physical-alias.gz'});
 assert.deepEqual(materializeRecipe(f.recipe,f.reader).products,before.products);
 assert.equal(original.whole_body_consumed,false);
});

test('derives ordered scopes across original batch boundaries and real templates without component lists',()=>{
 const f=fixture(),out=materializeRecipe(f.recipe,f.reader);assert.equal(out.groups.length,1);assert.deepEqual(out.groups[0].component_ids,f.componentIds);
 const s=JSON.parse(out.products[out.groups[0].source_template]),n=JSON.parse(out.products[out.groups[0].native_template]);
 assert.deepEqual(s.source_rule.expected_ids,f.componentIds);assert.deepEqual(n.additive.scope_ids,f.componentIds);assert.equal(s.source_rule.original_products.length,4);assert.ok(out.groups[0].models.native.predecessor_allowance);
 assert.ok(n.additive.inputs.some(p=>p.path==='native-owner.gz'));assert.ok(n.additive.inputs.some(p=>p.path==='latitudes.gz'));
 assert.deepEqual(materializeRecipe(f.recipe,f.reader).products,out.products);assert.equal(out.index.mode,'greedy-model');
});

test('models constructed encoded and decoded input closure before greedy split; transport alone deduplicates',()=>{
 const f=fixture({physicalBytes:200000,decodedBytes:700000,phase:2400000});const out=materializeRecipe(f.recipe,f.reader);
 assert.ok(out.groups.length>1);assert.deepEqual(out.groups.flatMap(g=>g.component_ids),f.componentIds);
 assert.ok(out.groups.every(g=>g.models.source.fits&&g.models.native.fits));
 const sourceMetadata=out.acquisition_plan.products.filter(p=>p.destinations.some(d=>d.endsWith('/sources-000.jsonl.gz')));assert.equal(sourceMetadata.length,1);
 // The shared physical source is still charged in every independent group.
 for(const g of out.groups){const s=JSON.parse(out.products[g.source_template]);assert.ok(s.source_rule.inputs.some(p=>p.original_product_path==='sources-000.jsonl.gz'));}
});

test('singleton overflow fails rather than silently narrowing scope or raising allowance',()=>{
 const f=fixture({physicalBytes:200000,decodedBytes:700000,phase:1000000});assert.throws(()=>materializeRecipe(f.recipe,f.reader),/Singleton exceeds/);
});

test('the request body is charged twice and runtime/log/monitor/receipt/support are counted',()=>{
 const f=fixture(),m=modelRequestBudget(f.source);const expectedRuntime=4000+1000+1000+1000+1000+200;
 assert.equal(m.reserved_bytes,1000+131072+131072+(3000+1000+m.request_bytes+1000+1000+1000+200));
 const larger=clone(f.source);larger.extra='x'.repeat(1234);assert.equal(modelRequestBudget(larger).total_bytes-m.total_bytes,2*(modelRequestBudget(larger).request_bytes-m.request_bytes));
 assert.ok(expectedRuntime>0);
});

test('native reservations include encoded and decoded predecessor bytes; real output is exactly re-admitted',()=>{
 const f=fixture();const a=modelRequestBudget(f.native,{predecessor_allowance:f.selection.predecessor_allowance,request_bytes_bound:131072});
 const bigger=clone(f.selection.predecessor_allowance);bigger.inventory_path.uncompressed_bytes+=12345;
 const b=modelRequestBudget(f.native,{predecessor_allowance:bigger,request_bytes_bound:131072});assert.equal(b.total_bytes-a.total_bytes,12345);
 assert.ok(recheckNativeRequest(f.native).fits);const fail=clone(f.native);fail.additive.inputs.push(f.pin('huge.gz',1000000,{uncompressed_bytes:3000000,uncompressed_sha256:hash('large')}));assert.throws(()=>recheckNativeRequest(fail),/exceeds admission/);
});

test('requires genuine pinned locator join, exact mapping and handoff roster',()=>{
 let f=fixture();f.recipe.handoffs[0].physical_locator.input=f.put('foreign.json',Object.fromEntries(f.componentIds.map(id=>[id,{path:'components-000.jsonl.gz'}])));assert.throws(()=>materializeRecipe(f.recipe,f.reader),/exact consumed/);
 f=fixture();delete f.selection.physical_locator;assert.throws(()=>materializeRecipe(f.recipe,f.reader),/per-case physical-product locator/);
 f=fixture();f.selection.targets=[];assert.throws(()=>materializeRecipe(f.recipe,f.reader),/target mapping/);
 f=fixture();f.selection.component_ids=['invented'];assert.throws(()=>materializeRecipe(f.recipe,f.reader),/not new recipe inputs/);
 f=fixture();const h=f.files.get('handoff.json').body;h.scopeIds=[...h.scopeIds].reverse();assert.throws(()=>materializeRecipe(f.recipe,f.reader),/scope\/order/);
});

test('supports keyed metadata and components comparison-product metadata without product reads',()=>{
 const f=fixture();const body={components:f.componentIds.map((component_id,i)=>({component_id,comparison_product:'components-00'+i+'.jsonl.gz'}))};
 const input=f.put('components-inputs.json',body);f.files.get('handoff.json').body.consumed_inputs.push(f.files.get(input.path).pin);f.selection.physical_locator={input,format:'components-comparison-product'};
 assert.equal(materializeRecipe(f.recipe,f.reader).groups.length,1);
});

test('retained replay preserves literal scopes and rejects incomplete handoff coverage',()=>{
 const f=fixture({legacy:true});const recipe={version:1,id:'replay',mode:'retained-groups',compatibility:'literal-historical-v1',registry:f.registry,destination_prefix:'.cache/native-grid-candidates/replay',groups:[{id:'original',handoff_id:'accepted-whole',source_template:f.sourceTemplate,native_template:f.nativeTemplate}]};
 const out=materializeRecipe(recipe,f.reader);assert.deepEqual(out.groups[0].component_ids,f.componentIds);assert.deepEqual(JSON.parse(out.products['original-source-template.json']),f.source);assert.equal(out.index.compatibility,'literal-historical-v1');assert.equal(out.groups[0].source_destination,f.source.destination);assert.equal(out.groups[0].native_destination,f.native.destination);assert.deepEqual(out.groups[0].source_locator,f.sourceTemplate);assert.deepEqual(out.groups[0].native_locator,f.nativeTemplate);
 f.files.get(f.sourceTemplate.path).body.source_rule.expected_ids=f.componentIds.slice(0,2);f.files.get(f.nativeTemplate.path).body.additive.scope_ids=f.componentIds.slice(0,2);assert.throws(()=>materializeRecipe(recipe,f.reader),/omitted accepted/);
});

test('explicit v2 groups admit a genuine disjoint ordered subset without exhaustive handoff coverage', () => {
 const f=fixture(), subset=f.componentIds.slice(1);
 f.source.source_rule.expected_ids=subset;f.native.additive.scope_ids=subset;
 const recipe={version:1,id:'subset',mode:'explicit-groups',registry:f.registry,
  destination_prefix:'.cache/native-grid-candidates/subset',groups:[{id:'north',handoff_id:'accepted-whole',
   component_ids:subset,target_ids:['t-one'],source_template:f.sourceTemplate,native_template:f.nativeTemplate}]};
 const original=clone(recipe),out=materializeRecipe(recipe,f.reader);
 assert.deepEqual(out.groups[0].component_ids,subset);assert.equal(out.index.compatibility,undefined);
 assert.equal(JSON.parse(out.products['north-source-template.json']).operating_profile,'source-native-v2');
 assert.deepEqual(recipe,original);assert.deepEqual(out.groups[0].source_locator,f.sourceTemplate);
 for(const mutate of [r=>r.groups.push({...r.groups[0],id:'overlap'}),r=>r.groups[0].component_ids.reverse(),
  r=>r.groups[0].target_ids=['foreign-target'],r=>r.compatibility='literal-historical-v1']){
  const bad=clone(recipe);mutate(bad);assert.throws(()=>materializeRecipe(bad,f.reader));
 }
 delete f.source.operating_profile;
 assert.throws(()=>materializeRecipe(recipe,f.reader),/genuine v2/);
});

test('candidate request serialization can force a split before publication',()=>{
 const f=fixture();const whole=materializeRecipe(f.recipe,f.reader);f.selection.native_request_bytes_bound=whole.groups[0].models.native.request_bytes-200;
 const split=materializeRecipe(f.recipe,f.reader);assert.ok(split.groups.length>1);assert.ok(split.groups.every(g=>g.models.native.request_bytes<=f.selection.native_request_bytes_bound));
});
}

// authority constructor controls
{

const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const HEAD = execFileSync('git', ['rev-parse', 'HEAD'], {cwd: REPO, encoding: 'utf8'}).trim();
const RETAINED = '5735ce1e6d91fba7d8b3b8e1efcf09a0f7ef4dc4';
const ACCEPTED = '9e7b93f43f8a2dccffc23cb1c9e6cd60613f3b9c';
const PREFIX = 'coordination/engineering/nor-grc-congo-delivery-20261011/';
const env = {...process.env, GIT_NO_LAZY_FETCH: '1', GIT_CONFIG_NOSYSTEM: '1', GIT_CONFIG_GLOBAL: '/dev/null', GIT_TERMINAL_PROMPT: '0',
  GIT_AUTHOR_NAME: 'Authority test', GIT_AUTHOR_EMAIL: 'test@example.invalid', GIT_COMMITTER_NAME: 'Authority test', GIT_COMMITTER_EMAIL: 'test@example.invalid'};
const git = (root, args, input) => execFileSync('git', ['-c', 'core.hooksPath=/dev/null', '-C', root, ...args], {env, input, maxBuffer: 33554433, stdio: ['pipe', 'pipe', 'pipe']});
class OfflineReader extends ImmutableReader {
  git(...args) { return git(this.repo, args); }
}
const reader = (repo = REPO) => new OfflineReader(repo, HEAD);
const realFixture = process.env.WORLDATLAS_DELIVERY_FIXTURE === '1';
function deriveCurrent13Fixture(repo = REPO) {
  const env = {...process.env, GIT_NO_LAZY_FETCH: '1', GIT_CONFIG_NOSYSTEM: '1', GIT_CONFIG_GLOBAL: '/dev/null', GIT_TERMINAL_PROMPT: '0'};
  const read = p => JSON.parse(execFileSync('git', ['-C', repo, 'show', p.commit + ':' + p.path], {env, maxBuffer: 33554433, stdio: ['pipe', 'pipe', 'pipe']}));
  const locate = p => ({commit: p.commit, path: p.path});
  const config = read({commit: HEAD, path: 'coordination/engineering/delivery-handoff-20261011/current13-compose.json'});
  if (config.registries.length !== 1) throw Error('Expected the single accepted current13 registry');
  const registry = locate(config.registries[0]), accepted = read(registry);
  const prefix = 'coordination/engineering/nor-grc-congo-delivery-20261011/combined-selected/authorities/';
  const entries = accepted.entries.filter(e => e.source_authority.path.startsWith(prefix));
  if (entries.length !== 5) throw Error('Expected all five historical current13 authority groups');
  const authorities = entries.map(entry => {
    const binding = read(entry.source_authority), request = read(binding.original_pins.native_request), spec = request.additive;
    const matches = spec.inputs.filter(p => p.path === spec.publication_path);
    if (matches.length !== 1) throw Error('Ambiguous original SOURCE publication');
    const aliases = (binding.source_output_aliases ?? []).filter(a => a.original.path === matches[0].path);
    if (aliases.length > 1) throw Error('Ambiguous retained SOURCE publication alias');
    const source = aliases.length ? aliases[0].published : matches[0];
    return {observations: {source_publication: locate(source), native_publication: locate(binding.native_proof.publication),
      native_operating: locate(binding.native_proof.operating)},
    committed: {rule_preimage: locate(entry.rule_preimage), source_authority: locate(entry.source_authority)}};
  });
  return {registry, authorities};
}
const current13 = realFixture ? deriveCurrent13Fixture() : null;
// Retained offline metadata is an explicit suite, not skipped default-CI work.
const fixtureTest = (name, fn) => { if (realFixture) test(name, fn); };
const byGroup = group => {
  const item = current13.authorities.find(a => a.committed.source_authority.path.includes('/' + group.toUpperCase() + '/'));
  assert.ok(item); return structuredClone(item);
};
const locators = group => byGroup(group).observations;
const read = (name, commit = ACCEPTED) => git(REPO, ['show', commit + ':' + name]);
const registryLocators = group => byGroup(group).committed;

function fixture(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'authority-fixture-'));
  t.after(() => fs.rmSync(root, {recursive: true, force: true}));
  git(root, ['init', '-q']);
  const objects = git(REPO, ['rev-parse', '--path-format=absolute', '--git-path', 'objects']).toString().trim();
  fs.mkdirSync(path.join(root, '.git/objects/info'), {recursive: true});
  fs.writeFileSync(path.join(root, '.git/objects/info/alternates'), objects + '\n');
  return {root, commit(files) {
    const rows = Object.entries(files).map(([name, raw]) => {
      assert.ok(!name.includes('/'));
      const oid = git(root, ['hash-object', '-w', '--stdin'], Buffer.isBuffer(raw) ? raw : valueBytes(raw)).toString().trim();
      return '100644 blob ' + oid + '\t' + name + '\n';
    });
    const tree = git(root, ['mktree'], rows.sort().join('')).toString().trim();
    return git(root, ['commit-tree', tree], 'Bounded adverse fixture\n').toString().trim();
  }};
}

fixtureTest('real GRC-001 authority bytes replay exactly from three locators using unchanged custody qualifiers', () => {
  const r = reader(), result = constructOriginalAuthority(r, locators('grc-001'));
  for (const [name, raw] of Object.entries(result.products))
    assert.deepEqual(raw, read(PREFIX + 'combined-selected/authorities/GRC-001/' + name));
  const ledger = JSON.parse(read(result.ledger.path, result.ledger.commit));
  assert.deepEqual(result.component_ids, ledger.scope_ids);
  assert.equal(result.rule_sha256, ledger.rule_sha256);
  assert.ok(result.limitations.every(s => !s.includes('approved')));
  const readPaths = [...r.inventory.values()].map(p => p.path);
  assert.ok(!readPaths.some(p => p.includes('/payloads/') || p.includes('/assets-bank/') || p.startsWith('data/geography/')),
    'Constructor must not hydrate original GIS/scientific operands');
});

fixtureTest('same immutable inputs replay deterministic authority output on a fresh reader', () => {
  const a = constructOriginalAuthority(reader(), locators('grc-001'));
  const b = constructOriginalAuthority(reader(), locators('grc-001'));
  assert.deepEqual(a, b);
});

fixtureTest('registry derives exact accepted entry after the generated authority bodies are committed', () => {
  const pair = registryLocators('GRC-001');
  const result = JSON.parse(constructAuthorityRegistry(reader(), [pair])['authority-registry.json']);
  const expected = JSON.parse(read(PREFIX + 'combined-selected/authority-registry.json')).entries
    .find(e => e.source_authority.path === pair.source_authority.path);
  assert.deepEqual(result.entries, [expected]);
});

fixtureTest('wrong real SOURCE/NATIVE joins and wrong qualified operating proof fail', () => {
  const wrongSource = locators('grc-001'); wrongSource.source_publication = locators('grc-002').source_publication;
  assert.throws(() => constructOriginalAuthority(reader(), wrongSource), /alias.*differ|predecessor|source receipt/i);
  const wrongNative = locators('grc-001'); wrongNative.native_publication = locators('grc-002').native_publication;
  assert.throws(() => constructOriginalAuthority(reader(), wrongNative), /alias.*differ|predecessor|source receipt/i);
  const wrongTerminal = locators('grc-001'); wrongTerminal.native_operating = locators('grc-002').native_operating;
  assert.throws(() => constructOriginalAuthority(reader(), wrongTerminal), /Unqualified original native operating/);
});

fixtureTest('missing inputs, handwritten derived fields and uncommitted or partial bodies fail', t => {
  for (const mutate of [x => delete x.native_operating, x => x.extra = x.native_publication,
    x => x.native_publication.sha256 = '0'.repeat(64), x => x.native_publication.component_ids = ['fabricated'],
    x => x.native_publication.path = '../publication.json', x => x.native_publication.commit = '0'.repeat(40)]) {
    const inputs = locators('grc-001'); mutate(inputs);
    assert.throws(() => constructOriginalAuthority(reader(), inputs));
  }
  const f = fixture(t), publication = JSON.parse(read(locators('grc-001').source_publication.path, RETAINED));
  const commit = f.commit({'publication.json': publication});
  const inputs = locators('grc-001'); inputs.source_publication = {commit, path: 'publication.json'};
  assert.throws(() => constructOriginalAuthority(reader(f.root), inputs), /whole ordinary Git input/);
});

fixtureTest('coherently committed failed terminal cannot produce an authority', t => {
  const f = fixture(t), inputs = locators('grc-001');
  const terminal = JSON.parse(read(inputs.native_operating.path, RETAINED));
  terminal.exit.code = 1;
  const commit = f.commit({'terminal.json': terminal}); inputs.native_operating = {commit, path: 'terminal.json'};
  assert.throws(() => constructOriginalAuthority(reader(f.root), inputs), /Unqualified original native operating/);
});

fixtureTest('registry rejects duplicate, cross-rule and coherently drifted source-authority joins', t => {
  const pair = registryLocators('GRC-001');
  assert.throws(() => constructAuthorityRegistry(reader(), [pair, pair]), /Duplicate committed/);
  assert.throws(() => constructAuthorityRegistry(reader(), [{...pair, source_authority: registryLocators('GRC-002').source_authority}]), /relabelled original/);
  const f = fixture(t), binding = JSON.parse(read(pair.source_authority.path, pair.source_authority.commit));
  const other = JSON.parse(read(registryLocators('GRC-002').source_authority.path, pair.source_authority.commit));
  binding.original_pins.source_facts = other.original_pins.source_facts;
  const commit = f.commit({'binding.json': binding});
  assert.throws(() => constructAuthorityRegistry(reader(f.root), [{...pair, source_authority: {commit, path: 'binding.json'}}]), /facts rebound|predecessor|source receipt/i);
});

fixtureTest('all five current13 authorities replay exact bodies and registry from discovered accepted locators', () => {
  assert.deepEqual(deriveCurrent13Fixture(), current13);
  let total = 0;
  for (const item of current13.authorities) {
    const result = constructOriginalAuthority(reader(), item.observations);
    assert.deepEqual(result.products['original-rule-preimage.json'], read(item.committed.rule_preimage.path, item.committed.rule_preimage.commit));
    assert.deepEqual(result.products['authority-binding.json'], read(item.committed.source_authority.path, item.committed.source_authority.commit));
    total += result.component_ids.length;
  }
  assert.equal(total, 13);
  const pairs = current13.authorities.map(a => a.committed).reverse();
  const actual = JSON.parse(constructAuthorityRegistry(reader(), pairs)['authority-registry.json']);
  const paths = new Set(pairs.map(a => a.source_authority.path));
  const expected = JSON.parse(read(current13.registry.path, current13.registry.commit)).entries.filter(e => paths.has(e.source_authority.path));
  assert.deepEqual(actual.entries, expected);
});

fixtureTest('registry phase transitions preserve another live reader shared-budget reservation', () => {
  const peer = reader();
  peer.metadataBytes += 32 * 1024 * 1024; peer.phase();
  const entryUsed = peer.used;
  const shared = new OfflineReader(REPO, HEAD, {allowance: peer.allowance, budget: peer.budget});
  constructAuthorityRegistry(shared, current13.authorities.map(a => a.committed));
  assert.ok(peer.used >= entryUsed, 'A registry transition must not release another reader’s charged live graph');
});
}

test('unowned empty stage directories and foreign root inventory are never adopted', async t => {
  const j = journal(t); fs.mkdirSync(path.join(j.target, 'requests'));
  await assert.rejects(prepareAdvanceStage(j, 'requests', 'requests', {}, () => ({'a.json': Buffer.from('{}\n')})), /Unowned stage/);
  assert.equal(fs.existsSync(path.join(j.stateTarget, 'requests.intent.json')), false);
  assert.throws(() => readAdvanceStatus(j), /Foreign advance inventory/);
});

import {candidateBudget} from '../scripts/native-ownership/native-preparation-guards.mjs';
test('completed stages resolve their wait and subsequent successful preparation resolves refusal', async t => {
  const j = journal(t); observeAdvance(j, {status: 'waiting', kind: 'commit', stage: 'requests'}); j.tick(10);
  await prepareAdvanceStage(j, 'requests', 'requests', {}, () => ({'one.json': Buffer.from('{}\n')}));
  assert.equal(readAdvanceStatus(j).waiting, null); assert.equal(readAdvanceStatus(j).timing.waits[0].ongoing, false);
  observeAdvance(j, {status: 'refused', reason: 'actual interrupted transition'}); j.tick(10);
  assert.ok(readAdvanceStatus(j).last_refusal);
  await prepareAdvanceStage(j, 'native-requests', 'native-requests', {}, () => ({'one.json': Buffer.from('{}\n')}));
  assert.equal(readAdvanceStatus(j).last_refusal, null);
});
test('advance publisher includes whole receipt in finite aggregate accounting without a fixed4KiB cap', async t => {
  const j = journal(t);
  j.budget = candidateBudget([{bytes: 4000}], {reserveBytes: 0, reserveDescriptors: 0,
    allowance: {phaseBytes: 5000, rssBytes: 1024 ** 3}});
  await assert.rejects(prepareAdvanceStage(j, 'requests', 'requests', {}, () => ({'large.json': Buffer.alloc(2000)})), /Aggregate/);
  assert.equal(fs.existsSync(path.join(j.target, 'requests')), false);
  const other = journal(t);
  await prepareAdvanceStage(other, 'recipe', 'recipe', {}, () => Object.fromEntries(
    Array.from({length: 50}, (_, i) => ['product-' + i + '.json', Buffer.from('{}\n')])));
  assert.ok(fs.statSync(path.join(other.target, 'recipe', 'preparation.json')).size > 4096);
  assert.deepEqual(readAdvanceStatus(other).completed, ['recipe']);
});
test('status charges complete journal reads against the same admitted phase', async t => {
  const j = journal(t);
  await prepareAdvanceStage(j, 'requests', 'requests', {}, () => ({'one.json': Buffer.alloc(2000)}));
  j.chargedJournalFiles = new Set();
  j.budget = candidateBudget([{bytes: 4000}], {reserveBytes: 0, reserveDescriptors: 0,
    allowance: {phaseBytes: 5000, rssBytes: 1024 ** 3}});
  assert.throws(() => readAdvanceStatus(j), /Aggregate/);
});

// Actual accepted13 new-partition model; bulk scientific products are not read.
async function current13GreedyProbe({root,scratch,writeResult=false}) {
const implementationFile=path.join(root,'scripts/delivery-handoff-advance.mjs');
const implementationWorktreeSha=createHash('sha256').update(fs.readFileSync(implementationFile)).digest('hex');
const {materializeRecipe}=await import(implementationFile);
const env={...process.env,GIT_NO_LAZY_FETCH:'1',GIT_CONFIG_NOSYSTEM:'1',GIT_CONFIG_GLOBAL:'/dev/null',GIT_TERMINAL_PROMPT:'0'};
const git=(cwd,...args)=>execFileSync('git',['-c','core.hooksPath=/dev/null',...args],{cwd,env,maxBuffer:4*1024*1024});
const sha=raw=>createHash('sha256').update(raw).digest('hex');
const canonical=v=>Array.isArray(v)?v.map(canonical):v&&typeof v==='object'?Object.fromEntries(Object.keys(v).sort().map(k=>[k,canonical(v[k])])):v;
const json=v=>Buffer.from(JSON.stringify(canonical(v))+'\n');
const exact=(a,b)=>json(a).equals(json(b));
const production='512c100efbb4c6334b39cefaabac2d30ec2c7823',dataCommit='dbda60ac426e30e430f8157794e5e7161f01a453';
const templateCommit=git(root,'rev-parse','HEAD').toString().trim();
const fixture=fs.mkdtempSync(scratch+'/greedy-fixture-');git(fixture,'init','--template=','--quiet');
const fixtureCommits=new Set(),cache=new Map(),readLog=[],cachedPaths=new Map();
function put(name,value){fs.writeFileSync(path.join(fixture,name),json(value),{flag:'wx'});}
function commit(){git(fixture,'add','--all');git(fixture,'-c','user.name=Metadata fixture','-c','user.email=metadata-fixture@example.invalid','commit','--quiet','-m','Metadata-only recipe fixture');const c=git(fixture,'rev-parse','HEAD').toString().trim();fixtureCommits.add(c);return c;}
function descriptor(commit,name){const repo=fixtureCommits.has(commit)?fixture:root;const line=git(repo,'ls-tree','-z',commit,'--',name).toString();const m=/^100644 blob ([a-f0-9]{40})\t([^\0]+)\0$/.exec(line);assert.ok(m&&m[2]===name,'Missing ordinary metadata path '+name);return {repo,commit,path:name,mode:'100644',git_blob_oid:m[1]};}
function body(pin){if(cache.has(pin.git_blob_oid))return cache.get(pin.git_blob_oid);const local=cachedPaths.get(pin.git_blob_oid);let raw;
 if(local)raw=fs.readFileSync(local);else {const size=Number(git(pin.repo,'cat-file','-s',pin.git_blob_oid));assert.ok(size<=1048576,'Metadata cap '+pin.path);raw=git(pin.repo,'cat-file','blob',pin.git_blob_oid);}
 assert.equal(createHash('sha1').update(Buffer.from('blob '+raw.length+'\0')).update(raw).digest('hex'),pin.git_blob_oid);
 readLog.push({commit:pin.commit,path:pin.path,bytes:raw.length,sha256:sha(raw),source:local?'verified prior literal':'warm Git metadata'});assert.ok(readLog.reduce((n,p)=>n+p.bytes,0)<20*1048576);cache.set(pin.git_blob_oid,raw);return raw;
}
const reader={pin(commit,path){const d=descriptor(commit,path),raw=body(d);const {repo,...p}=d;return {...p,bytes:raw.length,sha256:sha(raw)};},read(p){const actual=this.pin(p.commit,p.path);assert.equal(actual.git_blob_oid,p.git_blob_oid??p.blob);assert.equal(actual.bytes,p.bytes);assert.equal(actual.sha256,p.sha256);return cache.get(actual.git_blob_oid);},json(p){return JSON.parse(this.read(p));}};
const load=(commit,path)=>reader.json(reader.pin(commit,path));
const prefix='coordination/engineering/nor-grc-congo-delivery-20261011/';
const current='coordination/engineering/delivery-handoff-20261011/';
const sourceConfig=load(templateCommit,current+'current13-requests.json'),nativeConfig=load(templateCommit,current+'current13-native-requests.json');
const registryPin=sourceConfig.registry,registry=reader.json(registryPin),ids=[...new Set(sourceConfig.groups.map(g=>g.handoff_id))];
const entries=ids.map(id=>registry.entries.find(e=>e.id===id));
const handoffs=entries.map(e=>({entry:e,pin:{commit:e.accepted_source_commit,...e.source},body:load(e.accepted_source_commit,e.source.path)}));
const locatorPins=[];
for(const h of handoffs){const pins=h.body.consumed_inputs.filter(p=>p.path.endsWith('/physical-locators.json')||p.path.endsWith('/physical-inputs.json'));assert.equal(pins.length,1);const p=pins[0];
 const original=descriptor(p.commit,p.path);assert.equal(original.git_blob_oid,p.blob);const raw=body(original);assert.equal(raw.length,p.bytes);assert.equal(sha(raw),p.sha256);locatorPins.push(p);}
const v2Source=load(templateCommit,prefix+'resource-budget-controls-001/templates/a-source-template.json'),v2Native=load(templateCommit,prefix+'resource-budget-controls-001/templates/a-native-template.json');
const code=v2Source.executed_code.map(p=>{const actual=reader.pin(production,p.path);return {path:p.path,bytes:actual.bytes,sha256:actual.sha256};});
const operating=structuredClone(v2Source.operating_runtime);
for(const item of [operating.supervisor,...operating.support_code]){const actual=reader.pin(production,item.path);item.bytes=actual.bytes;item.sha256=actual.sha256;}
const replaceRuntime=request=>({...structuredClone(request),operating_profile:'source-native-v2',executed_code:code,installed_modules:structuredClone(v2Source.installed_modules),operating_runtime:structuredClone(operating)});
const sourceRequests=new Map(sourceConfig.groups.map(g=>[g.id,reader.json(g.template)]));
const nativeRequests=new Map(nativeConfig.groups.map(g=>[g.id,reader.json(g.template)]));
const resources=request=>({processing_allowance:{phaseBytes:384*1024*1024,rssBytes:640*1024*1024},output_reserve:request.output_reserve,operating_limits:structuredClone(v2Source.operating_limits)});
const physicalChecks=[],selectionDrafts=[];
const locator=(commit,path)=>({commit,path});
for(const [hi,h] of handoffs.entries()){
 const sameHandoff=sourceConfig.groups.filter(g=>g.handoff_id===h.entry.id);assert.ok(sameHandoff.length);
 const source=replaceRuntime(sourceRequests.get(sameHandoff[0].id));Object.assign(source,resources(source));put('source-'+hi+'.json',source);
 const targetRows=[];
 for(const [ti,targetId] of h.entry.target_ids.entries()){
  const components=h.body.candidate_source_native_bindings.filter(r=>r.retained_payload.target_stable_location_id===targetId).map(r=>r.component_id);
  const oldGroups=sameHandoff.filter(g=>sourceRequests.get(g.id).source_rule.expected_ids.some(id=>components.includes(id)));
  assert.ok(oldGroups.length);const exemplar=replaceRuntime(nativeRequests.get(oldGroups[0].id));Object.assign(exemplar,resources(exemplar));
  const parts=new Map(),inputs=new Map(exemplar.additive.inputs.map(p=>[p.path,p]));let bank;
  for(const g of oldGroups){const original=nativeRequests.get(g.id),banks=sourceRequests.get(g.id).source_rule.target_banks;assert.equal(banks.length,1);assert.ok(!bank||bank===banks[0]);bank=banks[0];
   for(const p of original.additive.owner_parts){if(parts.has(p.path))assert.ok(exact(parts.get(p.path),p),'Native containing identity conflict '+p.path);parts.set(p.path,p);const pin=original.additive.inputs.find(x=>x.path===p.path);assert.ok(pin);if(inputs.has(pin.path))assert.ok(exact(inputs.get(pin.path),pin));inputs.set(pin.path,pin);}}
  exemplar.additive.owner_parts=[...parts.values()];exemplar.additive.inputs=[...inputs.values()];const filename='native-'+hi+'-'+ti+'.json';put(filename,exemplar);targetRows.push({target_id:targetId,bank_path:bank,filename});
 }
 for(const r of h.body.physical_restoration.restorations){const matches=h.body.consumed_inputs.filter(p=>p.bytes===r.whole_original_bytes&&p.sha256===r.whole_original_sha256);assert.equal(matches.length,1);physicalChecks.push({handoff_id:h.entry.id,original_product:r.path,source:matches[0]});}
 selectionDrafts.push({handoff_id:h.entry.id,source_filename:'source-'+hi+'.json',source_resources:resources(source),native_resources:resources(v2Native),physical_locator:{input:locator(locatorPins[hi].commit,locatorPins[hi].path),format:locatorPins[hi].path.endsWith('/physical-locators.json')?'keyed-path':'components-comparison-product'},targets:targetRows,
 predecessor_allowance:{source_request_path:{bytes:131072},operating_path:{bytes:1048576},publication_path:{bytes:131072},facts_path:{bytes:4194304},inventory_path:{bytes:4194304,uncompressed_bytes:8388608}},native_request_bytes_bound:131072});
}
const derivedCommit=commit();
const recipe={version:1,id:'actual-current13',mode:'greedy-model',registry:locator(registryPin.commit,registryPin.path),destination_prefix:'.cache/native-grid-candidates/current13-greedy-metadata',handoffs:selectionDrafts.map(s=>{const {source_filename,targets,...rest}=s;return {...rest,source_template:locator(derivedCommit,source_filename),targets:targets.map(t=>{const {filename,...target}=t;return {...target,native_template:locator(derivedCommit,filename)};})};})};
put('recipe.json',recipe);const recipeCommit=commit();
const implementationPin=reader.pin(templateCommit,'scripts/delivery-handoff-advance.mjs');assert.equal(sha(fs.readFileSync(implementationFile)),implementationWorktreeSha);
const implementationMatchesHead=implementationWorktreeSha===implementationPin.sha256;
const output=materializeRecipe(recipe,reader);
const expected=handoffs.flatMap(h=>h.entry.cohort_ids);assert.deepEqual(output.groups.flatMap(g=>g.component_ids),expected);assert.equal(new Set(expected).size,13);assert.ok(output.groups.every(g=>g.models.source.fits&&g.models.native.fits));
const mutants=[];
for(const [i,h] of handoffs.entries()){const changed=structuredClone(h.body);assert.ok(changed.original_gap_membership?.members.length);for(const [j,row]of changed.original_gap_membership.members.entries()){assert.equal(typeof row.original_batch_id,'string');row.original_batch_id='r'.repeat(row.original_batch_id.length);}put('relabeled-handoff-'+i+'.json',changed);mutants.push({h,filename:'relabeled-handoff-'+i+'.json'});}
const mutantCommit=commit();const mutatedRegistry=structuredClone(registry);
for(const {h,filename} of mutants){const pin=reader.pin(mutantCommit,filename),entry=mutatedRegistry.entries.find(e=>e.id===h.entry.id);entry.accepted_source_commit=mutantCommit;entry.source={path:pin.path,mode:pin.mode,blob:pin.git_blob_oid,bytes:pin.bytes,sha256:pin.sha256};}
put('relabeled-registry.json',mutatedRegistry);const registryCommit=commit();
const control=materializeRecipe({...recipe,registry:locator(registryCommit,'relabeled-registry.json')},reader);
assert.deepEqual(control.groups.map(g=>g.component_ids),output.groups.map(g=>g.component_ids));
const unchangedBodies=plan=>plan.products.filter(p=>p.uses.includes('physical-product')||p.source.path.includes('/payloads/')||p.source.path.includes('/native-operands/')).map(p=>[p.source.bytes,p.source.sha256].join(':')).sort();
assert.deepEqual(unchangedBodies(control.acquisition_plan),unchangedBodies(output.acquisition_plan));
assert.ok(readLog.every(p=>!(/\.(bin|gz|geojson)$/.test(p.path))),'Unexpected product body read');
const products=output.acquisition_plan.products,bodyKey=p=>[p.mode,p.bytes,p.sha256].join(':');assert.equal(new Set(products.map(p=>p.identity)).size,products.length);
function category(role,predicate){const rows=products.filter(p=>predicate(p));const occurrences=[];for(const g of output.groups){for(const filename of [g.source_template,g.native_template]){const r=JSON.parse(output.products[filename]);for(const p of (r.source_rule??r.additive).inputs)if(rows.some(x=>x.source.sha256===p.sha256&&x.source.bytes===p.bytes))occurrences.push(p);}}
 assert.ok(rows.length>0);assert.equal(new Set(rows.map(p=>bodyKey(p.source))).size,rows.length);return {role,unique_bodies:rows.length,phase_occurrences:occurrences.length,unique_encoded_bytes:rows.reduce((n,p)=>n+p.source.bytes,0),phase_encoded_bytes:occurrences.reduce((n,p)=>n+p.bytes,0),identities:rows.map(p=>({bytes:p.source.bytes,sha256:p.source.sha256,destinations:p.destinations}))};}
const physical=category('physical',p=>p.uses.includes('physical-product'));
const admin=category('administrative',p=>p.source.path.includes('original-geography-source-corpus')&&p.source.path.includes('/payloads/'));
const native=category('native',p=>p.source.path.includes('/native-operands/'));
const result={version:1,kind:'actual-current13-greedy-metadata-probe',implementation_base_commit:templateCommit,implementation_worktree_sha256:implementationWorktreeSha,implementation_matches_head:implementationMatchesHead,implementation_pin:implementationMatchesHead?implementationPin:null,production_code_commit:production,derived_fixture_commit:derivedCommit,recipe_fixture_commit:recipeCommit,recipe_fixture_path:path.join(fixture,'recipe.json'),component_count:13,ordered_complete_disjoint:true,
 groups:output.groups.map(g=>({id:g.id,components:g.component_ids.length,component_ids:g.component_ids,source_phase_bytes:g.models.source.total_bytes,native_phase_bytes:g.models.native.total_bytes,source_descriptors:g.models.source.descriptors,native_descriptors:g.models.native.descriptors,phase_limit:g.models.source.phase_bytes,source_fits:g.models.source.fits,native_fits:g.models.native.fits})),
 old_batch_relabel_control:{changed_field:'original_gap_membership.members[].original_batch_id',all_labels_replaced:true,partitions_unchanged:true,physical_admin_native_transport_identities_unchanged:true,mutant_fixture_commit:mutantCommit},no_bulk_product_body_reads:true,physical_original_pin_checks:physicalChecks,transport:[physical,admin,native],all_unique_transport_bodies:products.length,all_unique_encoded_bytes:output.acquisition_plan.unique_encoded_bytes,metadata_reads:readLog,
 limits:['Metadata recipe test only; no SOURCE/NATIVE/GIS execution or new source admission.','Actual production handoff/locator bytes were read and verified; derived v2 test template commits are isolated scratch fixtures.','Relabeled handoff/registry fixtures are metamorphic controls, not accepted source authority.','Deduplication applies to acquisition planning only; every independent SOURCE/NATIVE phase still includes full inputs and costs.','Prospective request budget excludes live supply and subsequent runtime acquisition accounting, which existing operators retain.']};
assert.equal(sha(fs.readFileSync(implementationFile)),implementationWorktreeSha,'Implementation changed during probe');
if(writeResult)fs.writeFileSync(path.join(scratch,'recipe-current13-greedy-result.json'),json(result));
const summary={result:writeResult?path.join(scratch,'recipe-current13-greedy-result.json'):null,groups:result.groups.map(g=>({id:g.id,n:g.components,source:g.source_phase_bytes,native:g.native_phase_bytes,limit:g.phase_limit})),relabel_unchanged:true,transport:result.transport.map(({identities,...r})=>r),metadata_bytes:readLog.reduce((n,p)=>n+p.bytes,0)};
return {result,summary};
}
if (process.env.WORLDATLAS_DELIVERY_FIXTURE === '1') test('real13 greedy model ignores original batch labels and deduplicates physical/admin/native transport',
  async t => {
    const scratch = fs.mkdtempSync(path.join(os.tmpdir(), 'delivery-greedy-'));
    t.after(() => fs.rmSync(scratch, {recursive: true, force: true}));
    const {result} = await current13GreedyProbe({root: path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..'), scratch});
    assert.equal(result.component_count, 13);
    assert.deepEqual(result.groups.map(g => g.components), [10, 3]);
    assert.ok(result.groups.every(g => g.source_phase_bytes <= g.phase_limit && g.native_phase_bytes <= g.phase_limit));
    assert.deepEqual(result.transport.map(r => r.unique_bodies), [14, 3, 7]);
  });

test('stale lock recovery serializes competing acquisition and refuses ambiguous acquisition guards', async t => {
  const j = journal(t), lockPath = path.join(j.stateTarget, 'advance.lock');
  const raw = Buffer.from(JSON.stringify({host: os.hostname(), pid: 2147483647, nonce: 'dead',
    intent_sha256: digest(Buffer.from(JSON.stringify({kind: j.intent.kind, recipe: j.intent.recipe,
      started_at: j.intent.started_at, version: j.intent.version}) + '\n'))}) + '\n');
  // The journal recipe uses commit/path in that canonical order.
  fs.writeFileSync(lockPath, raw);
  const unlink = fs.unlinkSync; let blocked = false, ran = false;
  fs.unlinkSync = function(filename) {
    if (filename === lockPath && !blocked) {
      blocked = true;
      assert.throws(() => withAdvanceLock(j, () => { ran = true; }), /acquisition is occupied/);
    }
    return unlink(filename);
  };
  try { await withAdvanceLock(j, () => { assert.equal(ran, false); }); } finally { fs.unlinkSync = unlink; }
  assert.equal(blocked, true); assert.equal(ran, false);
  fs.writeFileSync(path.join(j.stateTarget, 'advance.acquire'), raw);
  assert.throws(() => withAdvanceLock(j, () => { ran = true; }), /inspect its owner/);
  assert.equal(ran, false); assert.deepEqual(fs.readFileSync(path.join(j.stateTarget, 'advance.acquire')), raw);
});

test('initial advance intent is charged before mutation and on read-only reopening', t => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'delivery-intent-'));
  t.after(() => fs.rmSync(root, {recursive: true, force: true}));
  const allowance = {phaseBytes: 100, rssBytes: 1024 ** 3};
  assert.throws(() => openAdvanceJournal(root, '.cache/delivery-handoff/small', {commit, path: 'recipe.json'},
    {budget: candidateBudget([], {reserveBytes: 0, reserveDescriptors: 0, allowance})}), /Aggregate/);
  assert.equal(fs.existsSync(path.join(root, '.cache/delivery-handoff/small')), false);
  const j = openAdvanceJournal(root, '.cache/delivery-handoff/full', {commit, path: 'recipe.json'});
  const before = fs.readFileSync(path.join(j.stateTarget, 'advance.json'));
  assert.throws(() => openAdvanceJournal(root, j.destination, j.intent.recipe, {resume: true,
    budget: candidateBudget([], {reserveBytes: 0, reserveDescriptors: 0, allowance})}), /Aggregate/);
  assert.deepEqual(fs.readFileSync(path.join(j.stateTarget, 'advance.json')), before);
});
test('real advance CLI refuses an oversized admitted config before reading recipe or creating destination', t => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'delivery-config-'));
  t.after(() => fs.rmSync(root, {recursive: true, force: true}));
  fs.writeFileSync(path.join(root, 'config.json'), JSON.stringify({version: 1, recipe: {commit, path: 'recipe.json'},
    preparation_allowance: {phaseBytes: 100, rssBytes: 1024 ** 3}, extra: 'x'.repeat(1000)}));
  const script = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../scripts/prepare-delivery-handoff.mjs');
  const env = {...process.env}; delete env.NODE_OPTIONS; delete env.NODE_PATH;
  for (const phase of ['advance', 'status']) assert.throws(() => execFileSync(process.execPath,
    [script, phase, 'config.json', '.cache/delivery-handoff/blocked'], {cwd: root, env, stdio: ['ignore', 'pipe', 'pipe']}),
  error => error.stderr.toString().includes('Aggregate evidence preparation budget exceeded'));
  assert.equal(fs.existsSync(path.join(root, '.cache')), false);
});

test('journal writes and queue intent reads share admission before dispatch', async t => {
  const j = journal(t), packet = {repo: 'ChengshuLi/WorldAtlas', pr_number: 1, head_sha: commit};
  const budget = () => candidateBudget([], {reserveBytes: 0, reserveDescriptors: 0,
    allowance: {phaseBytes: 100, rssBytes: 1024 ** 3}});
  j.budget = budget();
  assert.throws(() => observeAdvance(j, {status: 'waiting', kind: 'commit', detail: 'x'.repeat(200)}), /Aggregate/);
  assert.equal(fs.readdirSync(j.target).length, 1);
  j.budget = budget(); let submitted = false;
  await assert.rejects(advanceQueue(j, packet, {authorizeSubmission: true, checkReview: async () => packet,
    submit: async () => { submitted = true; }}), /Aggregate/);
  assert.equal(submitted, false); assert.equal(fs.existsSync(path.join(j.stateTarget, 'queue-submission.json')), false);
  fs.writeFileSync(path.join(j.stateTarget, 'queue-submission.json'), JSON.stringify({...packet, request_id: 'a'.repeat(36)}));
  j.budget = budget();
  await assert.rejects(advanceQueue(j, packet, {submit: async () => { submitted = true; }}), /Aggregate/);
  assert.equal(submitted, false);
});

import {admitPublication, pinReader} from '../scripts/prepare-delivery-handoff.mjs';
test('materialization report preflight refuses late collisions and changed postimages', t => {
  const j = journal(t), destination = '.cache/delivery-handoff/report';
  const products = {'materialized-inputs.json': Buffer.from('{}\n')};
  const commit = admitPublication(j.root, destination, products, {phase: 'materialize'}, false, j.budget);
  assert.equal(fs.existsSync(path.join(j.root, destination)), false);
  fs.mkdirSync(path.join(j.root, destination)); fs.writeFileSync(path.join(j.root, destination, 'sentinel'), 'preserve');
  assert.throws(commit, /Occupied destination/);
  assert.equal(fs.readFileSync(path.join(j.root, destination, 'sentinel'), 'utf8'), 'preserve');
  const second = admitPublication(j.root, destination + '-second', products, {phase: 'materialize'}, false, j.budget);
  products['materialized-inputs.json'][0] = 65;
  assert.throws(second, /changed before publication/);
  assert.equal(fs.existsSync(path.join(j.root, destination + '-second')), false);
});

import {gzipSync} from 'node:zlib';
import {acquireDeliveryInputs, deliveryAcquisitionExecute} from '../scripts/delivery-handoff-advance.mjs';
{
const sha=b=>createHash('sha256').update(b).digest('hex');
const canonical=v=>Array.isArray(v)?v.map(canonical):v&&typeof v==='object'?Object.fromEntries(Object.keys(v).sort().map(k=>[k,canonical(v[k])])):v;
const json=v=>Buffer.from(JSON.stringify(canonical(v))+'\n');
function fixture(){
 const directory=fs.mkdtempSync(path.join(os.tmpdir(),'delivery-input-materializer-')),origin=path.join(directory,'origin'),destination=path.join(directory,'destination');
 const env={...process.env,GIT_NO_LAZY_FETCH:'1',GIT_CONFIG_NOSYSTEM:'1',GIT_CONFIG_GLOBAL:'/dev/null',GIT_TERMINAL_PROMPT:'0',GIT_AUTHOR_NAME:'fixture',GIT_AUTHOR_EMAIL:'fixture@example.invalid',GIT_COMMITTER_NAME:'fixture',GIT_COMMITTER_EMAIL:'fixture@example.invalid'};
 const git=(cwd,args,input)=>execFileSync('git',['-c','core.hooksPath=/dev/null','-C',cwd,...args],{env,input,stdio:['pipe','pipe','pipe']});
 for(const repo of [origin,destination]){fs.mkdirSync(repo);git(repo,['init','--bare','--template=']);}
 const decoded=Buffer.from('one complete immutable fixture row\n'),rawA=gzipSync(decoded,{mtime:0}),rawB=Buffer.from('second immutable body\n');
 const oidA=git(origin,['hash-object','-w','--stdin'],rawA).toString().trim(),oidB=git(origin,['hash-object','-w','--stdin'],rawB).toString().trim();
 const tree=git(origin,['mktree'],`100644 blob ${oidA}\talias-a.gz\n100644 blob ${oidA}\tsource-a.gz\n100644 blob ${oidB}\tsource-b.txt\n`).toString().trim();
 const commit=git(origin,['commit-tree',tree],'fixture\n').toString().trim();git(origin,['update-ref','refs/heads/main',commit]);
 // The destination has actual immutable tree/commit metadata and no file bodies.
 for(const [type,id]of [['tree',tree],['commit',commit]])git(destination,['hash-object','-w','-t',type,'--stdin'],git(origin,['cat-file',type,id]));
 const pin=(name,body,oid,extra={})=>({commit,path:name,mode:'100644',blob:oid,bytes:body.length,sha256:sha(body),...extra});
 const a=pin('source-a.gz',rawA,oidA,{uncompressed_bytes:decoded.length,uncompressed_sha256:sha(decoded)}),alias={...a,path:'alias-a.gz'},b=pin('source-b.txt',rawB,oidB);
 const destA='.cache/additive-native-gap-repair/delivery/'+a.sha256+'/sources-000.jsonl.gz',destB='.cache/additive-native-gap-repair/delivery/'+b.sha256+'/components-001.jsonl.gz';
 const product=(p,destination)=>({identity:sha(json({mode:p.mode,bytes:p.bytes,sha256:p.sha256,uncompressed_bytes:p.uncompressed_bytes??null,uncompressed_sha256:p.uncompressed_sha256??null})),source:p,destinations:[p.path,destination],uses:['source-input','native-input','physical-product']});
 const plan={version:1,kind:'transport-only-deduplicated-input-plan',products:[product(a,destA),product(alias,destA),product(b,destB)],unique_encoded_bytes:a.bytes+alias.bytes+b.bytes};
 const fetchCalls=[],importedOids=[],writes=[],bodyReads=[],control={interruptFetch:false,interruptFile:false,corruptRead:false};
 const execute=(command,args,options)=>{
  assert.equal(command,'git');assert.equal(options.env.GIT_NO_LAZY_FETCH,'1');
  if(args.includes('fetch')){
   const requested=options.input.trim().split('\n');fetchCalls.push(requested);assert.equal(new Set(requested).size,requested.length);
   args=args.map(a=>a==='https://github.com/ChengshuLi/WorldAtlas.git'?origin:a);
   if(control.interruptFetch){control.interruptFetch=false;const first=requested[0];execFileSync(command,args,{...options,input:first+'\n'});importedOids.push(first);throw Error('fixture interruption after real first-object import');}
   const out=execFileSync(command,args,options);importedOids.push(...requested);return out;
  }
  if(args.includes('cat-file')&&args.includes('blob'))bodyReads.push(args.at(-1));
  const raw=execFileSync(command,args,options);
  if(control.corruptRead&&args.includes('cat-file')&&args.includes('blob'))return Buffer.from('wrong bytes');return raw;
 };
 const options={execute,token:'',limits:{total:plan.unique_encoded_bytes+2*decoded.length+rawA.length+rawB.length},onMaterialized(event){writes.push(event.path);if(control.interruptFile){control.interruptFile=false;throw Error('fixture interruption after completed alias');}}};
 return {directory,origin,destination,plan,options,execute,control,fetchCalls,importedOids,writes,bodyReads,git,rawA,rawB,a,b,destA,destB,oidA,oidB,close(){fs.rmSync(directory,{recursive:true,force:true});}};
}

test('actual missing Git objects and repeated identities acquire once; complete aliases are materialized once',async()=>{
 const f=fixture();try{
  const sourceSentinel=Buffer.from('Existing ordinary source-tree path is not a materialization target.\n');
  fs.writeFileSync(path.join(f.destination,f.a.path),sourceSentinel);
  const result=await acquireDeliveryInputs(f.plan,f.destination,f.options);assert.equal(result.status,'complete');assert.equal(result.unique_objects,2);assert.equal(result.declarations,3);assert.equal(result.verified_import_objects,2);assert.equal(result.materialized_files,2);assert.equal(result.materialization_body_reads,2);assert.equal(f.bodyReads.length,4);
  assert.equal(f.fetchCalls.length,1);assert.deepEqual(new Set(f.importedOids),new Set([f.oidA,f.oidB]));assert.equal(f.importedOids.length,2);assert.equal(f.writes.length,2);
  assert.deepEqual(fs.readFileSync(path.join(f.destination,f.destA)),f.rawA);assert.deepEqual(fs.readFileSync(path.join(f.destination,f.destB)),f.rawB);
  for(let i=0;i<2;i++){const warm=await acquireDeliveryInputs(f.plan,f.destination,f.options);assert.equal(warm.verified_import_objects,0);assert.equal(warm.materialized_files,0);assert.equal(warm.resumed_files,2);assert.equal(warm.materialization_body_reads,2);}
  assert.equal(f.bodyReads.length,12); // Complete per-invocation reauthentication is retained.
  assert.equal(f.fetchCalls.length,1);assert.equal(f.importedOids.length,2);assert.equal(f.writes.length,2);
  assert.deepEqual(fs.readFileSync(path.join(f.destination,f.a.path)),sourceSentinel);assert.equal(fs.existsSync(path.join(f.destination,f.b.path)),false);
 }finally{f.close();}
});

test('caller-derived complete byte and destination allowances fail before acquisition',async()=>{
 for(const limits of [{member:1},{total:1},{entries:2},{destinations:1},{total:Infinity},{total:-1},{unknown:1}]){const f=fixture();try{
  await assert.rejects(acquireDeliveryInputs(f.plan,f.destination,{...f.options,limits:{...f.options.limits,...limits}}));assert.equal(f.fetchCalls.length,0);assert.equal(f.writes.length,0);assert.equal(f.bodyReads.length,0);
 }finally{f.close();}}
 const f=fixture();try{
  await assert.rejects(acquireDeliveryInputs(f.plan,f.destination,{...f.options,limits:undefined}),/Explicit acquisition/);
  await assert.rejects(acquireDeliveryInputs(f.plan,f.destination,{...f.options,limits:{total:f.options.limits.total-1}}),/Encoded \+ decoded \+ physical placement/);assert.equal(f.fetchCalls.length,0);assert.equal(f.writes.length,0);
  const limits={member:Math.max(f.a.bytes,f.a.uncompressed_bytes,f.b.bytes),total:f.options.limits.total,entries:3,destinations:2};
  const result=await acquireDeliveryInputs(f.plan,f.destination,{...f.options,limits});assert.deepEqual(result.admission.limits,limits);assert.equal(result.admission.total_modeled_bytes,limits.total);assert.equal(result.materialized_files,2);
 }finally{f.close();}
});

test('interrupted real import resumes from actual object state without fetching the completed identity again',async()=>{
 const f=fixture();try{
  f.control.interruptFetch=true;await assert.rejects(acquireDeliveryInputs(f.plan,f.destination,f.options),/acquisition failed/);assert.equal(f.importedOids.length,1);assert.equal(f.writes.length,0);
  const before=f.git(f.destination,['cat-file','--batch-check'],f.oidA+'\n'+f.oidB+'\n').toString();assert.equal(before.split('\n').filter(line=>line.endsWith(' missing')).length,1);
  const resumed=await acquireDeliveryInputs(f.plan,f.destination,f.options);assert.equal(resumed.status,'complete');assert.equal(f.fetchCalls.length,2);assert.equal(f.fetchCalls[1].length,1);assert.notEqual(f.fetchCalls[1][0],f.importedOids[0]);assert.equal(new Set(f.importedOids).size,2);assert.equal(f.importedOids.length,2);assert.equal(f.writes.length,2);
 }finally{f.close();}
});

test('the actual shared candidateBudget admits complete transport costs alongside existing metadata and reserves',async()=>{
 const f=fixture();try{
  const makeBudget=delta=>candidateBudget([{bytes:17}],{reserveBytes:11,reserveDescriptors:1,allowance:{phaseBytes:f.options.limits.total+28+delta,rssBytes:640*1024*1024}});
  await assert.rejects(acquireDeliveryInputs(f.plan,f.destination,{...f.options,limits:undefined,budget:makeBudget(-1)}),/Encoded \+ decoded \+ physical placement/);assert.equal(f.fetchCalls.length,0);assert.equal(f.writes.length,0);assert.equal(f.bodyReads.length,0);
  const budget=makeBudget(0);const result=await acquireDeliveryInputs(f.plan,f.destination,{...f.options,limits:undefined,budget});
  assert.equal(result.admission.shared_budget.accounted_bytes,17+f.options.limits.total);assert.equal(result.admission.shared_budget.accounted_descriptors,8);assert.equal(result.admission.shared_budget.reserved_review_bytes,11);assert.equal(f.fetchCalls.length,1);assert.equal(f.writes.length,2);
 }finally{f.close();}
});

test('interruption after a complete file resumes without another fetch or overwriting the completed alias',async()=>{
 const f=fixture();try{
  f.control.interruptFile=true;await assert.rejects(acquireDeliveryInputs(f.plan,f.destination,f.options),/completed alias/);assert.equal(f.fetchCalls.length,1);assert.equal(f.writes.length,1);const first=path.join(f.destination,f.writes[0]),before=fs.statSync(first);
  const resumed=await acquireDeliveryInputs(f.plan,f.destination,f.options);assert.equal(resumed.materialized_files,1);assert.equal(resumed.resumed_files,1);assert.equal(f.fetchCalls.length,1);assert.equal(f.writes.length,2);const after=fs.statSync(first);assert.equal(after.ino,before.ino);assert.equal(after.mtimeMs,before.mtimeMs);
 }finally{f.close();}
});

test('partial, corrupted and symlinked aliases are preserved and refused before any fetch',async()=>{
 for(const mode of ['partial','corrupt','symlink']){const f=fixture();try{const destination=path.join(f.destination,f.destA);fs.mkdirSync(path.dirname(destination),{recursive:true});let sentinel;
  if(mode==='symlink'){sentinel=path.join(f.directory,'sentinel');fs.writeFileSync(sentinel,f.rawA);fs.symlinkSync(sentinel,destination);}else fs.writeFileSync(destination,mode==='partial'?f.rawA.subarray(0,3):Buffer.alloc(f.rawA.length,1));
  const before=mode==='symlink'?fs.readFileSync(sentinel):fs.readFileSync(destination);
  await assert.rejects(acquireDeliveryInputs(f.plan,f.destination,f.options),/Nonordinary|differs/);assert.equal(f.fetchCalls.length,0);assert.equal(f.writes.length,0);assert.deepEqual(mode==='symlink'?fs.readFileSync(sentinel):fs.readFileSync(destination),before);
 }finally{f.close();}}
});

test('wrong whole bytes or decoded gzip identities cannot produce a materialized receipt',async()=>{
 let f=fixture();try{f.control.corruptRead=true;await assert.rejects(acquireDeliveryInputs(f.plan,f.destination,f.options),/does not match tree/);assert.equal(f.writes.length,0);}finally{f.close();}
 f=fixture();try{const changed=structuredClone(f.plan);for(const p of changed.products.filter(p=>p.source.blob===f.oidA)){p.source.uncompressed_sha256='0'.repeat(64);p.identity=sha(json({mode:p.source.mode,bytes:p.source.bytes,sha256:p.source.sha256,uncompressed_bytes:p.source.uncompressed_bytes,uncompressed_sha256:p.source.uncompressed_sha256}));}
 await assert.rejects(acquireDeliveryInputs(changed,f.destination,f.options),/decoded identity/);assert.equal(f.writes.length,0);
 }finally{f.close();}
});

test('identity, destination and whole-file admission failures occur before object fetches',async()=>{
 for(const edit of [p=>p.products[0].identity='0'.repeat(64),p=>p.products[0].destinations.push('../escape'),p=>p.products[0].destinations.push('data/unowned.json'),p=>p.products[0].source.bytes=33554433,p=>p.unique_encoded_bytes++]){const f=fixture();try{const bad=structuredClone(f.plan);edit(bad);await assert.rejects(acquireDeliveryInputs(bad,f.destination,f.options));assert.equal(f.fetchCalls.length,0);assert.equal(f.writes.length,0);}finally{f.close();}}
});

test('plain materialize CLI authenticates a saved recipe index and resumes with identical receipt and zero writes', () => {
  const f = fixture();
  try {
    const index = json({version: 1, acquisition_plan: f.plan});
    const blob = f.git(f.origin, ['hash-object', '-w', '--stdin'], index).toString().trim();
    const tree = f.git(f.origin, ['mktree'], `100644 blob ${blob}\trecipe-index.json\n`).toString().trim();
    const commit = f.git(f.origin, ['commit-tree', tree], 'saved recipe index\n').toString().trim();
    fs.writeFileSync(path.join(f.origin, 'config.json'), JSON.stringify({version: 1,
      recipe_index: {commit, path: 'recipe-index.json'}, preparation_allowance: {phaseBytes: 1024 * 1024, rssBytes: 1024 ** 3}}));
    const script = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../scripts/prepare-delivery-handoff.mjs');
    const env = {...process.env}; delete env.NODE_OPTIONS; delete env.NODE_PATH;
    const run = (...flags) => JSON.parse(execFileSync(process.execPath, [script, 'materialize', 'config.json',
      '.cache/delivery-handoff/materialized', ...flags], {cwd: f.origin, env, stdio: ['ignore', 'pipe', 'pipe']}));
    const first = run(); assert.equal(first.acquisition.materialized_files, 2); assert.equal(first.acquisition.fetch_batches, 0);
    const receiptPath = path.join(f.origin, '.cache/delivery-handoff/materialized/preparation.json');
    const original = fs.readFileSync(receiptPath), before = fs.statSync(path.join(f.origin, f.destA));
    const second = run('--resume'); assert.equal(second.resumed, true); assert.equal(second.acquisition.materialized_files, 0);
    assert.equal(second.acquisition.resumed_files, 2); assert.equal(second.acquisition.fetch_batches, 0);
    assert.deepEqual(fs.readFileSync(receiptPath), original); assert.equal(fs.statSync(path.join(f.origin, f.destA)).ino, before.ino);
    assert.throws(() => run(), error => error.stderr.toString().includes('Occupied destination'));
  } finally { f.close(); }
});

test('cold acquisition reuses gh login ephemerally; warm and non-fetch reads never request credentials', async () => {
  const f = fixture(); let tokenReads = 0, authenticatedFetches = 0;
  try {
    const execute = deliveryAcquisitionExecute({readToken: () => { tokenReads++; return 'local-fixture-token'; },
      execute: (command, args, options) => {
        if (args.includes('fetch')) {
          authenticatedFetches++; assert.equal(options.env.GIT_CONFIG_COUNT, '3');
          assert.equal(options.env.GIT_CONFIG_KEY_2, 'http.https://github.com/.extraheader');
          assert.equal(options.env.GIT_CONFIG_VALUE_2, 'AUTHORIZATION: basic ' + Buffer.from('x-access-token:local-fixture-token').toString('base64'));
        } else assert.notEqual(options.env?.GIT_CONFIG_COUNT, '3');
        return f.execute(command, args, options);
      }});
    await acquireDeliveryInputs(f.plan, f.destination, {...f.options, execute});
    assert.equal(tokenReads, 1); assert.equal(authenticatedFetches, 1);
    await acquireDeliveryInputs(f.plan, f.destination, {...f.options, execute});
    assert.equal(tokenReads, 1); assert.equal(authenticatedFetches, 1);
    assert.throws(() => execute('git', ['fetch', 'https://example.invalid/repository'], {env: {}}), /Unexpected acquisition/);
    assert.equal(tokenReads, 1);
  } finally { f.close(); }
});

}

// Genuine PR1762 shape, with only state required by the transition retained.
import {refreshReviewBase, deliveryBaseRefreshAPI, nextReviewStage} from '../scripts/delivery-handoff-advance.mjs';
const refreshRecord = JSON.parse(fs.readFileSync(new URL('./fixtures/delivery-pr-base-refresh.json', import.meta.url)));
function baseRefreshFixture(t) {
  const j = journal(t), repo = 'ChengshuLi/WorldAtlas', number = refreshRecord.before.number;
  const control = {pr: structuredClone(refreshRecord.before), main: refreshRecord.after.base.sha,
    reads: 0, refs: 0, writes: [], onRead: () => {}, patch: null};
  const api = async (route, method = 'GET', body) => {
    if (method === 'PATCH') {
      assert.equal(route, `/repos/${repo}/pulls/${number}`);
      assert.deepEqual(body, {base: 'main'}); control.writes.push({route, method, body});
      if (control.patch) return control.patch(control);
      control.pr.base.sha = control.main; return structuredClone(control.pr);
    }
    assert.equal(method, 'GET'); assert.equal(body, undefined);
    if (route === `/repos/${repo}/git/ref/heads/main`) {
      control.refs++; return {ref: 'refs/heads/main', object: {type: 'commit', sha: control.main}};
    }
    assert.equal(route, `/repos/${repo}/pulls/${number}`);
    const pr = structuredClone(control.pr); control.onRead(pr, ++control.reads); return pr;
  };
  const review = {repo, pr_number: number, refresh_base_metadata: true};
  const adapters = {api, refresh: deliveryBaseRefreshAPI(api)};
  return {j, control, review, adapters,
    run: options => withAdvanceLock(j, () => refreshReviewBase(j, review, {...adapters, ...options}))};
}

test('real retained stale-base shape refreshes once with exact draft/ready and body preservation', async t => {
  assert.equal(createHash('sha256').update(refreshRecord.before.body).digest('hex'), refreshRecord.body_sha256);
  assert.equal(refreshRecord.before.head.sha, '9f2f4108589bf772f30a8e4edf1838e953191daa');
  assert.equal(refreshRecord.before.base.sha, '7446e4bcf19825698f544a5fa2809b3a78f88a25');
  for (const draft of [false, true]) {
    const f = baseRefreshFixture(t); f.control.pr.draft = draft;
    const original = structuredClone(f.control.pr), result = await f.run();
    assert.deepEqual(result, {...original, base: {...original.base, sha: refreshRecord.after.base.sha}});
    assert.equal(f.control.writes.length, 1); assert.equal(f.control.refs, 1);
    const intent = fs.readFileSync(path.join(f.j.stateTarget, 'pr-base-refresh.json'));
    assert.equal(readAdvanceStatus(f.j).pr_base_refresh.last_observation.result, 'verified');
    await f.run();
    assert.equal(f.control.writes.length, 1); assert.equal(f.control.refs, 2);
    assert.deepEqual(fs.readFileSync(path.join(f.j.stateTarget, 'pr-base-refresh.json')), intent);
    assert.equal(readAdvanceStatus(f.j).pr_base_refresh.last_observation.mutation, 'observation-only');
  }
});

test('current base and absent opt-in cannot issue a refresh mutation', async t => {
  const f = baseRefreshFixture(t); f.control.pr = structuredClone(refreshRecord.after);
  await f.run(); assert.equal(f.control.writes.length, 0); assert.equal(f.control.refs, 1);
  assert.equal(fs.existsSync(path.join(f.j.stateTarget, 'pr-base-refresh.json')), false);
  const g = baseRefreshFixture(t); delete g.review.refresh_base_metadata;
  await assert.rejects(g.run(), /Explicit/); assert.equal(g.control.writes.length, 0); assert.equal(g.control.reads, 0);
});

const refreshDrifts = [
  p => { p.head.sha = 'c'.repeat(40); }, p => { p.head.ref = 'engineering/other'; },
  p => { p.head.repo.full_name = 'foreign/repo'; }, p => { p.base.ref = 'foreign-target'; },
  p => { p.base.repo.full_name = 'foreign/repo'; }, p => { p.body += '\nChanged acceptance'; },
  p => { p.draft = !p.draft; }, p => { p.state = 'closed'; }, p => { delete p.draft; },
];
test('foreign or incomplete targets and every exact-state drift refuse before PATCH', async t => {
  for (const drift of refreshDrifts) {
    const f = baseRefreshFixture(t); f.control.onRead = (pr, read) => { if (read === 2) drift(pr); };
    await assert.rejects(f.run(), /state changed|complete open/);
    assert.equal(f.control.writes.length, 0); assert.equal(fs.existsSync(path.join(f.j.stateTarget, 'pr-base-refresh.json')), false);
  }
  const foreign = baseRefreshFixture(t); foreign.control.pr.base.ref = 'other';
  await assert.rejects(foreign.run(), /already targeting main/); assert.equal(foreign.control.refs, 0);
  const noMain = baseRefreshFixture(t); noMain.control.main = undefined;
  await assert.rejects(noMain.run(), /actual target-main/); assert.equal(noMain.control.writes.length, 0);
});

test('post-PATCH drift stays unresolved and never authorizes a second mutation', async t => {
  for (const drift of refreshDrifts) {
    const f = baseRefreshFixture(t);
    f.control.patch = control => { control.pr.base.sha = control.main; drift(control.pr); return structuredClone(control.pr); };
    await assert.rejects(f.run(), /readback could not prove/);
    assert.equal(readAdvanceStatus(f.j).pr_base_refresh.last_observation.result, 'unresolved');
    await assert.rejects(f.run(), /unresolved|complete open/); assert.equal(f.control.writes.length, 1);
  }
});

test('denied and uncertain writes reconcile actual state without blind retries', async t => {
  const denied = baseRefreshFixture(t); denied.control.pr.draft = true;
  denied.control.patch = () => { throw Error('403 denied'); };
  await assert.rejects(denied.run(), /readback could not prove/);
  await assert.rejects(denied.run(), /unresolved/);
  assert.equal(denied.control.writes.length, 1); assert.equal(denied.control.pr.draft, true);
  const uncertain = baseRefreshFixture(t);
  uncertain.control.patch = control => { control.pr.base.sha = control.main; throw Error('response lost'); };
  assert.equal((await uncertain.run()).base.sha, uncertain.control.main);
  assert.equal(readAdvanceStatus(uncertain.j).pr_base_refresh.last_observation.mutation, 'uncertain');
  await uncertain.run(); assert.equal(uncertain.control.writes.length, 1);
});

test('interruption before dispatch is observation-only; interruption after dispatch proves readback', async t => {
  for (const phase of ['intent', 'mutation']) {
    const f = baseRefreshFixture(t);
    await assert.rejects(f.run({interrupt: event => { if (event === phase) throw Error('interruption'); }}), /interruption/);
    assert.equal(f.control.writes.length, phase === 'intent' ? 0 : 1);
    if (phase === 'intent') await assert.rejects(f.run(), /unresolved/);
    else await f.run();
    assert.equal(f.control.writes.length, phase === 'intent' ? 0 : 1);
  }
});

test('failed readback, moving main and foreign resumption cannot chase a new target', async t => {
  const f = baseRefreshFixture(t); f.control.onRead = (_pr, read) => { if (read === 3) throw Error('read unavailable'); };
  await assert.rejects(f.run(), /readback could not prove/); await f.run(); assert.equal(f.control.writes.length, 1);
  f.control.main = 'd'.repeat(40); await assert.rejects(f.run(), /unresolved/); assert.equal(f.control.writes.length, 1);
  f.review.pr_number++; await assert.rejects(f.run(), /another PR/); assert.equal(f.control.writes.length, 1);
});

test('journal admission, foreign inventory and dangling intent preserve originals before dispatch', async t => {
  const budget = baseRefreshFixture(t), admitted = budget.j.budget; let additions = 0;
  budget.j.budget = {add: item => { if (++additions === 3) throw Error('Aggregate admission'); admitted.add(item); }};
  await assert.rejects(budget.run(), /Aggregate/); assert.equal(budget.control.writes.length, 0);
  assert.equal(fs.existsSync(path.join(budget.j.stateTarget, 'pr-base-refresh.json')), false);
  const foreign = baseRefreshFixture(t), sentinel = path.join(foreign.j.target, 'foreign.txt');
  fs.writeFileSync(sentinel, 'original', {flag: 'wx'});
  await assert.rejects(foreign.run(), /Foreign advance/); assert.equal(fs.readFileSync(sentinel, 'utf8'), 'original');
  assert.equal(foreign.control.reads, 0);
  const linked = baseRefreshFixture(t), intent = path.join(linked.j.stateTarget, 'pr-base-refresh.json');
  fs.symlinkSync('missing-intent', intent); await assert.rejects(linked.run(), /Nonordinary/);
  assert.equal(fs.readlinkSync(intent), 'missing-intent'); assert.equal(linked.control.reads, 0);
});

test('actual narrow write adapter cannot modify another route or include readiness/body fields', async () => {
  const calls = [], patch = deliveryBaseRefreshAPI((...args) => { calls.push(args); });
  await patch('ChengshuLi/WorldAtlas', 1762);
  assert.deepEqual(calls, [['/repos/ChengshuLi/WorldAtlas/pulls/1762', 'PATCH', {base: 'main'}]]);
  assert.throws(() => patch('foreign/repo', 1762), /Invalid/); assert.throws(() => patch('ChengshuLi/WorldAtlas', '1762'), /Invalid/);
  assert.equal(calls.length, 1);
});

test('actual review transition freezes verified state and never silently rebinds a completed packet', async t => {
  const f = baseRefreshFixture(t); let freezes = 0;
  const adapters = {api: f.adapters.api, refreshBase: f.adapters.refresh, freezeReview: async input => {
    freezes++; assert.deepEqual(input.expectedPR, f.control.pr);
    return {'review-packet.json': Buffer.from(JSON.stringify({head_sha: input.expectedHead, base_sha: input.expectedPR.base.sha}))};
  }};
  const next = await nextReviewStage(f.j, f.review, {}, adapters);
  assert.equal(next.id, 'review'); await prepareAdvanceStage(f.j, next.id, next.phase, next.input, next.produce);
  const original = fs.readFileSync(path.join(f.j.target, 'review', 'review-packet.json'));
  f.control.pr.base.sha = refreshRecord.before.base.sha; // GitHub later reports stale metadata again.
  const repeated = await nextReviewStage(f.j, f.review, {}, adapters);
  assert.equal(repeated.queue.base_sha, refreshRecord.after.base.sha);
  assert.equal(f.control.writes.length, 1); assert.equal(f.control.refs, 1); assert.equal(freezes, 1);
  assert.deepEqual(fs.readFileSync(path.join(f.j.target, 'review', 'review-packet.json')), original);
  f.control.pr.head.sha = 'd'.repeat(40);
  await assert.rejects(nextReviewStage(f.j, f.review, {}, adapters), /Completed stage inputs changed/);
});

test('plain status CLI observes a retained base refresh without credentials, API calls or journal writes', async t => {
  const f = baseRefreshFixture(t), root = f.j.root;
  const git = (...args) => execFileSync('git', args, {cwd: root, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe']}).trim();
  git('init'); git('config', 'user.name', 'Fixture'); git('config', 'user.email', 'fixture@example.invalid');
  fs.writeFileSync(path.join(root, 'recipe.json'), '{}\n', {flag: 'wx'});
  git('add', 'recipe.json'); git('commit', '-m', 'Fixture');
  const head = git('rev-parse', 'HEAD'), recipe = pinReader(root).pin(head, 'recipe.json');
  const j = openAdvanceJournal(root, '.cache/delivery-handoff/status-control', recipe);
  await withAdvanceLock(j, () => refreshReviewBase(j, f.review, f.adapters));
  const snapshot = () => fs.readdirSync(j.target).sort().map(name => [name, fs.readFileSync(path.join(j.target, name)).toString('base64')]);
  const before = snapshot(), bin = path.join(root, 'bin'); fs.mkdirSync(bin);
  fs.writeFileSync(path.join(bin, 'gh'), '#!/bin/sh\necho unexpected-gh >&2\nexit 88\n', {flag: 'wx', mode: 0o755});
  fs.writeFileSync(path.join(root, 'config.json'), JSON.stringify({version: 1, recipe: {commit: head, path: 'recipe.json'}}), {flag: 'wx'});
  const env = {...process.env, PATH: bin + path.delimiter + process.env.PATH};
  for (const key of ['NODE_OPTIONS', 'NODE_PATH', 'GH_TOKEN', 'GITHUB_TOKEN']) delete env[key];
  const script = fileURLToPath(new URL('../scripts/prepare-delivery-handoff.mjs', import.meta.url));
  const status = JSON.parse(execFileSync(process.execPath, [script, 'status', 'config.json', j.destination],
    {cwd: root, env, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe']}));
  assert.equal(status.pr_base_refresh.main_sha, refreshRecord.after.base.sha);
  assert.equal(status.pr_base_refresh.last_observation.result, 'verified');
  assert.deepEqual(snapshot(), before); assert.equal(f.control.writes.length, 1);
});

import {committedComposition} from '../scripts/delivery-handoff-advance.mjs';
import {composeAuthorities, jsonBytes} from '../scripts/prepare-delivery-handoff.mjs';
function compositionRepository(t, originalObjects) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'delivery-composition-'));
  t.after(() => fs.rmSync(root, {recursive: true, force: true}));
  const env = {...process.env, GIT_NO_LAZY_FETCH: '1', GIT_CONFIG_NOSYSTEM: '1', GIT_CONFIG_GLOBAL: '/dev/null', GIT_TERMINAL_PROMPT: '0',
    GIT_AUTHOR_NAME: 'Fixture', GIT_AUTHOR_EMAIL: 'fixture@example.invalid', GIT_COMMITTER_NAME: 'Fixture', GIT_COMMITTER_EMAIL: 'fixture@example.invalid'};
  const git = (args, input) => execFileSync('git', ['-c', 'core.hooksPath=/dev/null', '-C', root, ...args],
    {env, input, encoding: 'utf8', stdio: ['pipe', 'pipe', 'pipe']}).trim();
  git(['init', '-q']);
  if (originalObjects) fs.writeFileSync(path.join(root, '.git/objects/info/alternates'), originalObjects + '\n', {flag: 'wx'});
  return {root, reader: pinReader(root), commit(files) {
    const rows = Object.entries(files).map(([name, raw]) => {
      assert.ok(!name.includes('/'));
      return '100644 blob ' + git(['hash-object', '-w', '--stdin'], Buffer.isBuffer(raw) ? raw : jsonBytes(raw)) + '\t' + name + '\n';
    });
    const tree = git(['mktree'], rows.sort().join(''));
    const outer = git(['mktree'], '040000 tree ' + tree + '\tcomposition\n');
    return git(['commit-tree', outer], 'Bounded composition fixture\n');
  }};
}
function commitComposition(f, j, changes = {}) {
  const names = ['authority-registry.json', 'composed-original-ledger.json', 'preparation.json'];
  const files = Object.fromEntries(names.map(name => [name, fs.readFileSync(path.join(j.target, 'compose', name))]));
  const commit = f.commit({...files, ...changes});
  return {commit, path: 'composition/preparation.json'};
}
async function freshCompositionFixture(t) {
  const f = compositionRepository(t), r = f.reader, j = journal(t);
  const inputs = f.commit({'rule-new.json': {fixture: 'new'}, 'rule-old.json': {fixture: 'old'}, 'source.json': {fixture: 'binding'}});
  const entry = name => {
    const rule = r.pin(inputs, `composition/rule-${name}.json`), source = r.pin(inputs, 'composition/source.json');
    const body = {policy_id: 'retained-source-literal-additions', policy_version: 1, rule_sha256: rule.sha256,
      rule_preimage: rule, source_authority: source};
    return {authority_sha256: digest(jsonBytes(body)), ...body};
  };
  const entries = ['new', 'old'].map(entry), registry = item => ({version: 1, kind: 'retained-rule-authority-registry-v1', entries: [item]});
  const geometry = {type: 'Polygon', coordinates: [[[0, 0], [1, 0], [0, 1], [0, 0]]]};
  const ledger = (item, index) => ({version: 1, kind: 'native-additive-repair-ledger-v1', rule_sha256: item.rule_sha256,
    parent_inventory: {total: 2}, scope_ids: ['component:' + index], rows: [{component_id: 'component:' + index, target_id: 'target',
      pixelIndex: index + 1, base_geometry_sha256: 'b'.repeat(64), geometry_sha256: digest(jsonBytes(geometry)), source_receipt_sha256: 'c'.repeat(64),
      geometry, native_cells: index + 1, disposition: 'assigned'}]});
  const original = f.commit({'new-only.json': registry(entries[0]), 'retained.json': registry(entries[1]),
    'new-ledger.json': ledger(entries[0], 0), 'old-ledger.json': ledger(entries[1], 1)});
  const pin = name => r.pin(original, 'composition/' + name);
  const config = {version: 1, registries: [pin('new-only.json'), pin('retained.json')], ledgers: [pin('new-ledger.json'), pin('old-ledger.json')]};
  await prepareAdvanceStage(j, 'compose', 'compose', config, () => composeAuthorities(config, r));
  return {f, r, j, config, registry: pin('new-only.json')};
}

test('fresh new-only composition derives both committed output pins while preserving frozen input', async t => {
  const {f, r, j, config, registry} = await freshCompositionFixture(t);
  const original = fs.readFileSync(path.join(j.stateTarget, 'compose.intent.json'));
  assert.equal(r.json(registry).entries.length, 1);
  assert.equal(committedComposition(j, r, {}, registry), null);
  const composition = commitComposition(f, j);
  const result = committedComposition(j, r, {composition}, registry);
  assert.equal(r.json(result.registry).entries.length, 2);
  assert.deepEqual(r.json(result.ledger).scope_ids, ['component:0', 'component:1']);
  assert.equal(r.json(result.ledger).authority_registry_sha256, result.registry.sha256);
  assert.equal(committedComposition(j, r, {composed_ledger: {commit: result.ledger.commit, path: result.ledger.path}}, registry), null);
  assert.deepEqual(committedComposition(j, r, {composed_ledger: {commit: result.ledger.commit, path: result.ledger.path}}, result.registry), result);
  assert.deepEqual(fs.readFileSync(path.join(j.stateTarget, 'compose.intent.json')), original);
  await assert.rejects(prepareAdvanceStage(j, 'compose', 'compose', {...config, registries: [result.registry]}, () => {
    throw Error('A completed composition must not rerun');
  }), /Changed stage inputs/);
  assert.deepEqual(fs.readFileSync(path.join(j.stateTarget, 'compose.intent.json')), original);
  await prepareAdvanceStage(j, 'package', 'package', result, () => ({'projection.json': jsonBytes(result)}));
  const receipt = fs.readFileSync(path.join(j.target, 'compose', 'preparation.json'));
  const equivalent = commitComposition(f, j, {'preparation.json': Buffer.concat([receipt, Buffer.from('\n')])});
  const changedPin = committedComposition(j, r, {composition: equivalent}, registry);
  assert.notEqual(changedPin.registry.commit, result.registry.commit);
  await assert.rejects(prepareAdvanceStage(j, 'package', 'package', changedPin, () => ({'projection.json': jsonBytes(changedPin)})), /Changed stage inputs/);
});

test('composition rejects changed committed members, refreshed false receipts, foreign bindings and conflicting legacy pins', async t => {
  const {f, r, j, registry} = await freshCompositionFixture(t), composition = commitComposition(f, j);
  const original = fs.readFileSync(path.join(j.target, 'compose', 'authority-registry.json'));
  const receipt = JSON.parse(fs.readFileSync(path.join(j.target, 'compose', 'preparation.json')));
  const body = JSON.parse(fs.readFileSync(path.join(j.target, 'compose', 'authority-registry.json')));
  body.entries.pop(); const changed = jsonBytes(body);
  const wrongMember = commitComposition(f, j, {'authority-registry.json': changed});
  assert.throws(() => committedComposition(j, r, {composition: wrongMember}, registry), /output differs/);
  const coherent = structuredClone(receipt); coherent.outputs['authority-registry.json'] = {bytes: changed.length, sha256: digest(changed)};
  const falseReceipt = commitComposition(f, j, {'authority-registry.json': changed, 'preparation.json': jsonBytes(coherent)});
  assert.throws(() => committedComposition(j, r, {composition: falseReceipt}, registry), /frozen input\/output/);
  const wrongBinding = structuredClone(receipt); wrongBinding.binding.config_sha256 = 'd'.repeat(64);
  const foreign = commitComposition(f, j, {'preparation.json': jsonBytes(wrongBinding)});
  assert.throws(() => committedComposition(j, r, {composition: foreign}, registry), /frozen input\/output/);
  assert.throws(() => committedComposition(j, r, {composition, composed_ledger: {commit: registry.commit, path: registry.path}}, registry), /Conflicting/);
  assert.throws(() => committedComposition(j, r, {composed_ledger: {commit: registry.commit, path: registry.path}}, registry), /ledger differs/);
  assert.throws(() => committedComposition(j, r, {composition: {...composition, sha256: 'd'.repeat(64)}}, registry), /handwritten/);
  assert.deepEqual(fs.readFileSync(path.join(j.target, 'compose', 'authority-registry.json')), original);
  assert.equal(r.json(committedComposition(j, r, {composition}, registry).registry).entries.length, 2);
  fs.writeFileSync(path.join(j.target, 'compose', 'authority-registry.json'), 'changed saved stage');
  assert.throws(() => committedComposition(j, r, {composition}, registry), /Completed metadata changed/);
  assert.equal(fs.readFileSync(path.join(j.target, 'compose', 'authority-registry.json'), 'utf8'), 'changed saved stage');
});

if (process.env.WORLDATLAS_DELIVERY_FIXTURE === '1') test('real five new-only authorities compose with the thirty retained authorities through a fresh committed receipt', async t => {
  const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
  const env = {...process.env, GIT_NO_LAZY_FETCH: '1', GIT_CONFIG_NOSYSTEM: '1', GIT_CONFIG_GLOBAL: '/dev/null', GIT_TERMINAL_PROMPT: '0'};
  const objects = execFileSync('git', ['rev-parse', '--path-format=absolute', '--git-path', 'objects'], {cwd: repo, env, encoding: 'utf8'}).trim();
  const f = compositionRepository(t, objects), r = f.reader, j = journal(t);
  const acceptedCommit = '9e7b93f43f8a2dccffc23cb1c9e6cd60613f3b9c';
  const accepted = r.pin(acceptedCommit, 'coordination/engineering/nor-grc-congo-delivery-20261011/combined-selected/authority-registry.json');
  const complete = r.json(accepted), prefix = 'coordination/engineering/nor-grc-congo-delivery-20261011/combined-selected/authorities/';
  const fresh = complete.entries.filter(e => e.source_authority.path.startsWith(prefix));
  const retained = complete.entries.filter(e => !e.source_authority.path.startsWith(prefix));
  assert.equal(fresh.length, 5); assert.equal(retained.length, 30);
  const committed = f.commit({'new-only.json': {...complete, entries: fresh}, 'retained-only.json': {...complete, entries: retained}});
  const registry = r.pin(committed, 'composition/new-only.json');
  const config = {version: 1, registries: [registry, r.pin(committed, 'composition/retained-only.json')],
    ledgers: complete.entries.map(e => r.json(e.source_authority).original_pins.ledger)};
  await prepareAdvanceStage(j, 'compose', 'compose', config, () => composeAuthorities(config, r));
  const composition = commitComposition(f, j), result = committedComposition(j, r, {composition}, registry);
  assert.deepEqual(r.read(result.registry), r.read(accepted));
  const expectedIds = config.ledgers.flatMap(p => r.json(p).scope_ids).sort();
  assert.deepEqual(r.json(result.ledger).scope_ids, expectedIds);
  assert.equal(r.json(result.ledger).authority_registry_sha256, accepted.sha256);
  const before = fs.readFileSync(path.join(j.stateTarget, 'compose.intent.json'));
  assert.deepEqual(committedComposition(j, r, {composition}, registry), result);
  assert.deepEqual(fs.readFileSync(path.join(j.stateTarget, 'compose.intent.json')), before);
});

import {acceptedReview} from '../scripts/delivery-handoff-advance.mjs';
import {renderClaim} from '../scripts/issue-claim-contract.mjs';
import {checkPremergeEvidence, reviewContractBinding} from '../scripts/premerge-evidence.mjs';

// Exercise the actual remote byte and distinct-review gates. Only GitHub
// transport is mocked; the legacy claim intentionally has no owned_paths.
function acceptedReviewFixture({nested = true} = {}) {
  const repo = 'ChengshuLi/WorldAtlas', branch = 'engineering/advance-acceptance';
  const prefix = nested ? 'coordination/engineering/retained/new-delivery/' : 'coordination/engineering/advance-acceptance/';
  const manifestPath = prefix + 'evidence-quality.json', outputPath = prefix + 'results.json';
  const baseline = Buffer.from('acceptance baseline\n'), output = Buffer.from('{"value":0.5}\n');
  const descriptor = (name, raw) => ({path: name, bytes: raw.length, sha256: digest(raw), hash_kind: 'file-bytes'});
  const spec = {mode: 'engineering', max_prs: 1, depends_on: [99], scope: 'Bounded delivery acceptance fixture',
    ...(nested ? {owned_paths: [prefix]} : {}),
    evidence_quality: {version: 1, manifest_path: manifestPath, subject_ids: [], pins: {}, review_kind: 'code'}};
  const issue = {number: 100, state: 'open', labels: ['type:engineering', 'kind:work-item', 'status:ready'],
    created_at: '2026-10-07T00:00:00Z', body: `Delivery acceptance.\n<!-- worldatlas-work:v1\n${JSON.stringify(spec)}\n-->`};
  const files = [{filename: outputPath, status: 'added'}, {filename: manifestPath, status: 'added'}];
  const pr = {number: 101, state: 'open', draft: false, created_at: issue.created_at, body: 'Refs #100\nScoped delivery.',
    head: {sha: later, ref: branch, repo: {full_name: repo}}, base: {sha: commit, ref: 'main', repo: {full_name: repo}}, changed_files: files.length};
  const claim = {version: 1, active: true, worker_id: 'author', claim_id: 'original-claim-001', branch, mode: 'engineering',
    expires_at: new Date(Date.now() + 3600000).toISOString()};
  const manifest = {version: 1, issue: issue.number, lane: 'engineering', worker_id: claim.worker_id,
    subject_ids: [], subject_ids_sha256: digest('[]'), baseline: {commit, files: [descriptor('baseline.txt', baseline)], pins: {}},
    sources: [], outputs: [descriptor(outputPath, output)],
    methods: [{id: 'synthetic', kind: 'code', description: 'Synthetic numeric byte control', software: 'Node 24', units: 'fraction'}],
    metrics: [{id: 'share', value: 0.5, unit: 'fraction', vintage: 'current', input_sha256: digest(baseline), evaluation_commit: commit}],
    summaries: [{metric_id: 'share', value: 0.5, unit: 'fraction'}], conclusions: [],
    stages: {research: 'complete', implementation: 'implemented', geographic_approval: 'not-requested'},
    commands: ['node --test test/delivery-handoff-advance.test.mjs'],
    metric_bindings: [{metric_id: 'share', path: outputPath, json_pointer: '/value'}]};
  const manifestBytes = Buffer.from(JSON.stringify(manifest));
  const receipt = {version: 1, pr_number: pr.number, head_sha: later, manifest_sha256: digest(manifestBytes),
    author_worker_id: claim.worker_id, reviewer_worker_id: 'independent-reviewer', outcome: 'accepted', limits: [],
    inspected_files: files.map(file => file.filename), evidence_hashes: [digest(baseline), digest(output)],
    domains: {implementation: {outcome: 'accepted', scope: 'Actual fixture byte inventory and scoped ownership.', limits: []}},
    ...reviewContractBinding(issue, pr)};
  const packet = {repo, pr_number: pr.number, head_sha: later, base_sha: commit, issue: structuredClone(issue),
    author_worker_id: claim.worker_id, manifest: {sha256: digest(manifestBytes)}, files: structuredClone(files), ...reviewContractBinding(issue, pr)};
  const control = {issue, pr, claim, dependency: {number: 99, state: 'closed'}, blockers: [], receipt, reviewAssociation: 'OWNER',
    calls: [], traversed: false, onEvidence: () => {}};
  const oid = raw => createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex');
  const contents = new Map([['baseline.txt', baseline], [outputPath, output], [manifestPath, manifestBytes]]);
  const blobs = new Map([...contents.values()].map(raw => [oid(raw), raw]));
  const tree = [...contents].map(([name, raw]) => ({path: name, type: 'blob', mode: '100644', size: raw.length, sha: oid(raw)}));
  const api = async (route, method = 'GET') => {
    control.calls.push(route); assert.equal(method, 'GET');
    if (route === `/repos/${repo}/pulls/101`) return structuredClone(control.pr);
    if (route === `/repos/${repo}/issues/100`) return structuredClone(control.issue);
    if (route === `/repos/${repo}/issues/99`) return structuredClone(control.dependency);
    if (route.includes('/pulls/101/files?')) return structuredClone(files);
    if (route.includes('/issues/100/comments?')) return [{id: 1, user: {login: 'github-actions[bot]'}, body: renderClaim(control.claim)}, ...control.blockers];
    if (route.includes('/issues/101/comments?')) {
      const comments = control.receipt ? [{id: 2, author_association: control.reviewAssociation,
        body: `<!-- worldatlas-review:v1\n${JSON.stringify(control.receipt)}\n-->`}] : [];
      control.traversed = true; control.onEvidence(control); return comments;
    }
    if (route.includes('/git/commits/')) return {tree: {sha: 'fixture-tree'}};
    if (route.includes('/git/trees/')) return {truncated: false, tree};
    if (route.includes('/git/blobs/')) { const sha = route.split('/').pop(), raw = blobs.get(sha);
      return {sha, size: raw.length, encoding: 'base64', content: raw.toString('base64')}; }
    if (route.includes('/compare/')) return {status: 'identical'};
    throw Error('Unexpected acceptance route: ' + route);
  };
  return {control, packet, api, run: () => acceptedReview(packet, api), rawCheck: () => checkPremergeEvidence({api, repo, pr, issue, reservation: claim, files, review: true})};
}

test('accepted review authenticates nested engineering ownership through real evidence and distinct receipt gates', async () => {
  const f = acceptedReviewFixture();
  await assert.rejects(f.rawCheck(), /preserve other lanes/); // Independent reproduction of the old raw-claim failure.
  const accepted = await f.run();
  assert.equal(accepted.review_comment_id, 2); assert.equal(accepted.reviewer_worker_id, 'independent-reviewer');
  assert.equal(accepted.manifest_sha256, f.packet.manifest.sha256); assert.equal(f.control.traversed, true);
  assert.equal(f.control.calls.filter(route => route.endsWith('/issues/99')).length, 0);
  assert.equal((await acceptedReviewFixture({nested: false}).run()).review_comment_id, 2);
});

test('accepted review rejects actual issue scope and PR changes during evidence traversal', async()=>{
 const mutations=[c=>{c.issue.state='closed';},
  c=>{c.issue.body=c.issue.body.replace('retained/new-delivery/','retained/foreign/');},
  c=>{c.pr.head.ref='engineering/foreign';},c=>{c.pr.base.ref='foreign';},
  c=>{c.pr.head.repo.full_name='foreign/repo';},c=>{c.pr.changed_files++;}];
 for(const mutate of mutations){const f=acceptedReviewFixture();f.control.onEvidence=mutate;await assert.rejects(f.run());assert.equal(f.control.traversed,true);}
});

test('accepted review tolerates a same-owner lease renewal without weakening independent substantive review', async () => {
  const f = acceptedReviewFixture(); f.control.onEvidence = c => {
    c.claim.expires_at = new Date(Date.now() + 7200000).toISOString(); c.claim.request_id = 'benign-renewal-001';
    c.issue.updated_at = new Date().toISOString();
  };
  assert.equal((await f.run()).review_comment_id, 2);
  for (const mutate of [c => { c.receipt = null; }, c => { c.receipt.reviewer_worker_id = 'author'; },
    c => { c.receipt.domains = {}; }, c => { c.reviewAssociation = 'NONE'; },
    c => { c.receipt.manifest_sha256 = 'f'.repeat(64); }, c => { c.receipt.head_sha = commit; }]) {
    const adverse = acceptedReviewFixture(); mutate(adverse.control); await assert.rejects(adverse.run(), /review|Review/);
  }
});

import {refreshDeliveryAuthorTree} from '../scripts/delivery-handoff-advance.mjs';
function authorRefreshFixture(t, {authorChange, mainChange} = {}) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'delivery-author-refresh-'));
  t.after(() => fs.rmSync(root, {recursive: true, force: true}));
  const env = {...process.env, GIT_NO_LAZY_FETCH: '1', GIT_CONFIG_GLOBAL: '/dev/null', GIT_CONFIG_NOSYSTEM: '1',
    GIT_AUTHOR_NAME: 'Refresh fixture', GIT_AUTHOR_EMAIL: 'fixture@example.invalid',
    GIT_COMMITTER_NAME: 'Refresh fixture', GIT_COMMITTER_EMAIL: 'fixture@example.invalid'};
  const git = (...args) => execFileSync('git', args, {cwd: root, env, encoding: 'utf8', stdio: ['pipe', 'pipe', 'pipe']}).trim();
  const put = (name, value) => { fs.mkdirSync(path.dirname(path.join(root, name)), {recursive: true}); fs.writeFileSync(path.join(root, name), value); };
  git('init', '--quiet', '--initial-branch=main');
  put('data/ownership-selection.json', '{"selected":"old"}\n');
  put('coordination/engineering/fixture/receipt.json', '{"owned":"old"}\n');
  put('shared.txt', 'first\nsecond\nthird\nfourth\nfifth\n');
  put('rename.txt', 'rename me\n'); put('delete.txt', 'delete me\n'); put('mode.txt', 'mode\n');
  git('add', '--all'); git('commit', '--quiet', '-m', 'Initial metadata');
  const base = git('rev-parse', 'HEAD');
  git('checkout', '--quiet', '-b', 'engineering/refresh-fixture');
  put('coordination/engineering/fixture/receipt.json', '{"owned":"new"}\n');
  authorChange?.({put, git, root});
  git('add', '--all'); git('commit', '--quiet', '-m', 'Owned author change');
  const before = git('rev-parse', 'HEAD');
  git('checkout', '--quiet', 'main');
  put('data/ownership-selection.json', '{"selected":"current"}\n');
  mainChange?.({put, git, root});
  git('add', '--all'); git('commit', '--quiet', '-m', 'Accepted main metadata');
  const main = git('rev-parse', 'HEAD'); git('checkout', '--quiet', 'engineering/refresh-fixture');
  // Isolate Git bookkeeping from scientific memory admission. The production
  // journal/CLI still uses candidateBudget and its actual available-memory gate.
  let accounted = 0, descriptors = 0;
  const budget = {add({bytes = 0}) { accounted += bytes; descriptors++;
    assert.ok(accounted <= 2 * 1024 * 1024 && descriptors <= 512, 'Bounded Git fixture journal'); }};
  const j = openAdvanceJournal(root, '.cache/delivery-handoff/refresh', {commit: base, path: 'recipe.json'}, {budget});
  const calls = [], validation = [];
  const execute = (command, args, options) => {
    assert.equal(options.env.GIT_NO_LAZY_FETCH, '1');
    assert.equal(command, 'git'); calls.push(args);
    return execFileSync(command, args, {...options, env: {...options.env, ...env}, stdio: ['pipe', 'pipe', 'pipe']});
  };
  const validate = async value => { validation.push(value); assert.equal(value.branch, 'engineering/refresh-fixture'); assert.equal(value.main, main); };
  const run = options => refreshDeliveryAuthorTree(j, {main, validate, execute, ...options});
  return {root, j, git, put, base, before, main, run, calls, validation};
}

test('author refresh inherits actual main selectors and preserves owned bytes, ancestry and untracked files', async t => {
  const f = authorRefreshFixture(t);
  f.put('untracked-sentinel.txt', 'keep me\n');
  const owned = f.git('rev-parse', f.before + ':coordination/engineering/fixture/receipt.json');
  const result = await f.run();
  assert.equal(result.status, 'refreshed'); assert.equal(f.git('rev-parse', 'HEAD'), result.head);
  assert.deepEqual(f.git('rev-list', '--parents', '-n', '1', result.head).split(' '), [result.head, f.before, f.main]);
  assert.equal(f.git('rev-parse', result.head + ':coordination/engineering/fixture/receipt.json'), owned);
  assert.equal(f.git('show', 'HEAD:data/ownership-selection.json'), '{"selected":"current"}');
  assert.equal(fs.readFileSync(path.join(f.root, 'untracked-sentinel.txt'), 'utf8'), 'keep me\n');
  assert.equal(f.git('status', '--porcelain', '--untracked-files=no'), '');
  assert.equal((await f.run()).head, result.head);
  assert.equal(f.calls.filter(args => args.includes('update-ref')).length, 1);
  assert.equal(f.calls.some(args => args.includes('fetch') || args.includes('reset')), false);
  const observations = readAdvanceStatus(f.j).timing.external_observations.filter(row => row.kind === 'author-tree-refresh');
  assert.equal(observations.length, 1); assert.equal(observations[0].head, result.head);
  assert.equal(observations[0].elapsed_ms, result.elapsed_ms);
});

test('author refresh resumes identical intent after interruption before ref, after ref and after checkout', async t => {
  for (const point of ['intent', 'ref', 'checkout']) await t.test(point, async t => {
    const f = authorRefreshFixture(t);
    await assert.rejects(f.run({interrupt: where => { if (where === point) throw Error('interrupted ' + point); }}), /interrupted/);
    const original = fs.readFileSync(path.join(f.j.stateTarget, 'author-tree-refresh.json'));
    const intended = JSON.parse(original);
    assert.equal(fs.existsSync(path.join(f.j.stateTarget, 'author-tree-refreshed.json')), false);
    assert.equal(f.git('rev-parse', 'HEAD'), point === 'intent' ? f.before : intended.head);
    const result = await f.run(); assert.equal(result.head, intended.head);
    assert.deepEqual(fs.readFileSync(path.join(f.j.stateTarget, 'author-tree-refresh.json')), original);
    assert.equal(f.git('status', '--porcelain', '--untracked-files=no'), '');
    assert.equal(f.calls.filter(args => args.includes('update-ref')).length, 1);
  });
});

test('author refresh refuses a genuine conflict before publication and preserves the original head', async t => {
  const f = authorRefreshFixture(t, {authorChange: ({put}) => put('shared.txt', 'author\n'), mainChange: ({put}) => put('shared.txt', 'main\n')});
  await assert.rejects(f.run(), /conflict or unavailable/);
  assert.equal(f.git('rev-parse', 'HEAD'), f.before);
  assert.equal(fs.readFileSync(path.join(f.root, 'shared.txt'), 'utf8'), 'author\n');
  assert.equal(fs.existsSync(path.join(f.j.stateTarget, 'author-tree-refresh.json')), false);
});

test('author refresh refuses even a clean textual merge when it changes an owned postimage', async t => {
  const f = authorRefreshFixture(t, {authorChange: ({put}) => put('shared.txt', 'author\nsecond\nthird\nfourth\nfifth\n'),
    mainChange: ({put}) => put('shared.txt', 'first\nsecond\nthird\nfourth\nmain\n')});
  await assert.rejects(f.run(), /owned postimage: shared.txt/);
  assert.equal(f.git('rev-parse', 'HEAD'), f.before);
  assert.equal(fs.existsSync(path.join(f.j.stateTarget, 'author-tree-refresh.json')), false);
});

test('author refresh preserves owned renames, deletions and file modes', async t => {
  const f = authorRefreshFixture(t, {authorChange: ({git, root}) => {
    git('mv', 'rename.txt', 'renamed.txt'); git('rm', '--quiet', 'delete.txt'); fs.chmodSync(path.join(root, 'mode.txt'), 0o755);
  }});
  const result = await f.run();
  for (const name of ['rename.txt', 'renamed.txt', 'delete.txt', 'mode.txt'])
    assert.equal(f.git('ls-tree', result.head, '--', name), f.git('ls-tree', f.before, '--', name));
});

test('author refresh refuses foreign index, worktree and untracked collisions without overwriting them', async t => {
  for (const kind of ['index', 'worktree', 'untracked']) await t.test(kind, async t => {
    const f = authorRefreshFixture(t, {mainChange: ({put}) => put('from-main.txt', 'accepted\n')});
    const name = kind === 'untracked' ? 'from-main.txt' : 'shared.txt'; f.put(name, 'foreign\n');
    if (kind === 'index') f.git('add', name);
    await assert.rejects(f.run(), kind === 'index' ? /Tracked index/ : kind === 'worktree' ? /Tracked worktree/ : /overwritten|read-tree/);
    assert.equal(f.git('rev-parse', 'HEAD'), f.before);
    assert.equal(fs.readFileSync(path.join(f.root, name), 'utf8'), 'foreign\n');
    assert.equal(fs.existsSync(path.join(f.j.stateTarget, 'author-tree-refresh.json')), false);
  });
});

test('author refresh rejects revoked validation and foreign movement during validation', async t => {
  const revoked = authorRefreshFixture(t);
  await assert.rejects(revoked.run({validate: async () => { throw Error('claim revoked'); }}), /claim revoked/);
  assert.equal(revoked.git('rev-parse', 'HEAD'), revoked.before);
  const moved = authorRefreshFixture(t); let validations = 0;
  await assert.rejects(moved.run({validate: async () => { if (++validations === 2) moved.git('update-ref', 'refs/heads/engineering/refresh-fixture', moved.main); }}), /Author state changed/);
  assert.equal(moved.git('rev-parse', 'HEAD'), moved.main);
  assert.equal(moved.calls.some(args => args.includes('update-ref')), false);
});

test('author refresh never chases a changed main or adopts foreign edits after interrupted ref update', async t => {
  const f = authorRefreshFixture(t);
  await assert.rejects(f.run({interrupt: where => { if (where === 'ref') throw Error('interrupted'); }}), /interrupted/);
  const intended = JSON.parse(fs.readFileSync(path.join(f.j.stateTarget, 'author-tree-refresh.json')));
  await assert.rejects(f.run({main: f.base}), /Foreign or changed author refresh intent/);
  f.put('shared.txt', 'foreign after ref\n');
  await assert.rejects(f.run(), /Tracked worktree/);
  assert.equal(f.git('rev-parse', 'HEAD'), intended.head);
  assert.equal(fs.readFileSync(path.join(f.root, 'shared.txt'), 'utf8'), 'foreign after ref\n');
});

import {commitAdvanceStage, automaticDeliveryObservations, runAutomaticDelivery} from '../scripts/delivery-handoff-advance.mjs';
function automaticGitFixture(t) {
  const root = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'delivery-auto-git-')));
  t.after(() => fs.rmSync(root, {recursive: true, force: true}));
  const git = (...args) => execFileSync('git', args, {cwd: root, env: {...process.env, GIT_NO_LAZY_FETCH: '1'}, encoding: 'utf8'}).trim();
  git('init', '-q', '-b', 'engineering/automatic-control'); git('config', 'user.name', 'Fixture'); git('config', 'user.email', 'fixture@example.invalid');
  fs.writeFileSync(path.join(root, 'original'), 'unchanged\n'); git('add', 'original'); git('commit', '-qm', 'baseline');
  let charged = 0;
  // Isolate journal/Git bookkeeping from production memory admission. The real
  // CLI retains its ordinary resource gate and is verified only when admitted.
  const budget = {add({bytes}) { charged += bytes; assert.ok(Number.isSafeInteger(bytes) && bytes >= 0 && charged < 2 * 1024 * 1024); }};
  const j = openAdvanceJournal(root, 'coordination/engineering/automatic-control/advance', {commit: git('rev-parse', 'HEAD'), path: 'recipe.json'}, {budget});
  const validate = async ({branch, paths}) => {assert.equal(branch, 'engineering/automatic-control'); assert.ok(paths.every(p => p.startsWith(j.destination + '/')));};
  return {j, git, validate};
}
for (const stop of ['intent', 'object', 'ref']) test('automatic commit resumes the same Git object after ' + stop, async t => {
  const {j, git, validate} = automaticGitFixture(t);
  await prepareAdvanceStage(j, 'recipe', 'recipe', {}, () => ({'recipe-index.json': Buffer.from('{"groups":[]}\n')}));
  const parent = git('rev-parse', 'HEAD');
  await assert.rejects(commitAdvanceStage(j, 'recipe', {validate, interrupt: point => {if (point === stop) throw Error('interrupted ' + stop);}}), /interrupted/);
  const intended = JSON.parse(fs.readFileSync(path.join(j.stateTarget, 'commit-recipe.json')));
  const result = await commitAdvanceStage(j, 'recipe', {validate});
  assert.equal(result.head, intended.head); assert.equal(git('rev-parse', 'HEAD^'), parent);
  assert.equal(git('rev-list', '--count', 'HEAD'), '2');
  assert.equal(git('show', 'HEAD:' + j.destination + '/recipe/recipe-index.json'), '{"groups":[]}');
  assert.ok(!git('ls-tree', '-r', '--name-only', 'HEAD').includes('advance.lock'));
  const again = await commitAdvanceStage(j, 'recipe', {validate}); assert.equal(again.resumed, true);
  assert.equal(git('rev-list', '--count', 'HEAD'), '2'); assert.equal(git('diff', '--name-only'), '');
});
test('automatic commit preserves foreign staged files, claim refusal and changed completed outputs', async t => {
  const {j, git, validate} = automaticGitFixture(t);
  await prepareAdvanceStage(j, 'recipe', 'recipe', {}, () => ({'recipe-index.json': Buffer.from('{}\n')}));
  const parent = git('rev-parse', 'HEAD');
  fs.writeFileSync(path.join(j.root, 'foreign'), 'keep me'); git('add', 'foreign');
  await assert.rejects(commitAdvanceStage(j, 'recipe', {validate}), /existing tracked\/index/);
  assert.equal(git('show', ':foreign'), 'keep me'); assert.equal(git('rev-parse', 'HEAD'), parent);
  git('reset', '-q', 'HEAD', '--', 'foreign');
  await assert.rejects(commitAdvanceStage(j, 'recipe', {validate: async () => {throw Error('revoked claim');}}), /revoked claim/);
  assert.equal(fs.existsSync(path.join(j.stateTarget, 'commit-recipe.json')), false);
  fs.writeFileSync(path.join(j.target, 'recipe', 'recipe-index.json'), 'changed');
  await assert.rejects(commitAdvanceStage(j, 'recipe', {validate}), /Completed metadata changed/);
  assert.equal(git('rev-parse', 'HEAD'), parent); assert.equal(fs.readFileSync(path.join(j.root, 'foreign'), 'utf8'), 'keep me');
});
test('automatic commit refuses foreign branch movement and explicit observation substitution', async t => {
  const {j, git, validate} = automaticGitFixture(t);
  await prepareAdvanceStage(j, 'recipe', 'recipe', {}, () => ({'recipe-index.json': Buffer.from('{}\n')}));
  await assert.rejects(commitAdvanceStage(j, 'recipe', {validate, interrupt: point => {if (point === 'intent') throw Error('stop');}}), /stop/);
  git('commit', '--allow-empty', '-qm', 'foreign movement'); const foreign = git('rev-parse', 'HEAD');
  await assert.rejects(commitAdvanceStage(j, 'recipe', {validate}), /Foreign branch movement/);
  assert.equal(git('rev-parse', 'HEAD'), foreign);
  const f = automaticGitFixture(t);
  await prepareAdvanceStage(f.j, 'recipe', 'recipe', {}, () => ({'recipe-index.json': Buffer.from('{}\n')}));
  const result = await commitAdvanceStage(f.j, 'recipe', {validate: f.validate});
  assert.equal(automaticDeliveryObservations(f.j, {}).observations.template_commit, result.head);
  assert.throws(() => automaticDeliveryObservations(f.j, {observations: {template_commit: 'f'.repeat(40)}}), /conflicts/);
});
test('automatic continuation commits and consumes several stages in one invocation then waits for a genuine terminal', async t => {
  const {j, git, validate} = automaticGitFixture(t); let preparations = 0;
  const nextStage = async (journal, config) => {
    const done = readAdvanceStatus(journal).completed;
    if (!done.includes('recipe')) return {id: 'recipe', phase: 'recipe', input: {}, produce: () => {preparations++;return {'recipe-index.json': Buffer.from('{}\n')};}};
    assert.equal(git('show', config.observations.template_commit + ':' + j.destination + '/recipe/recipe-index.json'), '{}');
    if (!done.includes('requests')) return {id: 'requests', phase: 'requests', input: {template: config.observations.template_commit},
      produce: () => {preparations++;return {'request.json': Buffer.from('{"genuine_future_execution":false}\n')};}};
    return {waiting: {status: 'waiting', stage: 'source-one', kind: 'source-terminal', detail: 'Actual supervisor result required'}};
  };
  const result = await runAutomaticDelivery(j, {}, {}, {}, {validate, nextStage});
  assert.equal(result.kind, 'source-terminal'); assert.equal(preparations, 2); assert.equal(git('rev-list', '--count', 'HEAD'), '3');
  const status = readAdvanceStatus(j); assert.equal(status.waiting.kind, 'source-terminal');
  assert.equal(status.timing.external_observations.filter(e => e.kind === 'automatic-invocation').length, 1);
  await runAutomaticDelivery(j, {}, {}, {}, {validate, nextStage});
  assert.equal(preparations, 2); assert.equal(git('rev-list', '--count', 'HEAD'), '3');
});

test('author refresh preserves sparse checkout without materializing unrelated inherited bodies', async t => {
  const f = authorRefreshFixture(t, {mainChange: ({put}) => put('unrelated/retained-body.txt', 'excluded metadata body\n')});
  f.git('sparse-checkout', 'init', '--no-cone');
  f.git('sparse-checkout', 'set', '--no-cone', '/data/ownership-selection.json', '/coordination/engineering/fixture/');
  assert.equal(fs.existsSync(path.join(f.root, 'unrelated/retained-body.txt')), false);
  const result = await f.run();
  assert.equal(f.git('show', result.head + ':unrelated/retained-body.txt'), 'excluded metadata body');
  assert.equal(fs.existsSync(path.join(f.root, 'unrelated/retained-body.txt')), false);
  assert.equal(f.git('status', '--porcelain', '--untracked-files=no'), '');
});

test('author refresh already containing captured main performs no commit or ref mutation', async t => {
  const f = authorRefreshFixture(t);
  const result = await f.run({main: f.base});
  assert.equal(result.status, 'current'); assert.equal(result.head, f.before);
  assert.equal(f.calls.some(args => args.includes('hash-object') || args.includes('update-ref') || args.includes('read-tree')), false);
  assert.equal(fs.existsSync(path.join(f.j.stateTarget, 'author-tree-refresh.json')), false);
});

test('author refresh respects an existing reference transaction hook refusal', async t => {
  const f = authorRefreshFixture(t), hook = path.join(f.root, '.git/hooks/reference-transaction');
  fs.writeFileSync(hook, '#!/bin/sh\nif [ "$1" = prepared ]; then exit 1; fi\nexit 0\n'); fs.chmodSync(hook, 0o755);
  await assert.rejects(f.run(), /ref updates aborted by hook|update-ref/);
  assert.equal(f.git('rev-parse', 'HEAD'), f.before);
  assert.equal(fs.existsSync(path.join(f.j.stateTarget, 'author-tree-refreshed.json')), false);
  assert.equal(f.git('status', '--porcelain', '--untracked-files=no'), '');
});

test('author refresh refuses assume-unchanged and materialized skip-worktree edits hidden from normal diff', async t => {
  for (const kind of ['assume', 'skip']) await t.test(kind, async t => {
    const f = authorRefreshFixture(t), name = 'data/ownership-selection.json';
    f.git('update-index', kind === 'assume' ? '--assume-unchanged' : '--skip-worktree', name);
    f.put(name, 'hidden foreign edit\n');
    await assert.rejects(f.run(), kind === 'assume' ? /Assume-unchanged/ : /Materialized skip-worktree/);
    assert.equal(f.git('rev-parse', 'HEAD'), f.before);
    assert.equal(fs.readFileSync(path.join(f.root, name), 'utf8'), 'hidden foreign edit\n');
    assert.equal(fs.existsSync(path.join(f.j.stateTarget, 'author-tree-refresh.json')), false);
  });
});

test('automatic commit rejects hidden index edits and a forged tree outside declared products', async t => {
  const {j, git, validate} = automaticGitFixture(t);
  await prepareAdvanceStage(j, 'recipe', 'recipe', {}, () => ({'recipe-index.json': Buffer.from('{}\n')}));
  git('update-index', '--assume-unchanged', 'original'); fs.writeFileSync(path.join(j.root, 'original'), 'hidden edit');
  await assert.rejects(commitAdvanceStage(j, 'recipe', {validate}), /Index trust flags/);
  assert.equal(fs.readFileSync(path.join(j.root, 'original'), 'utf8'), 'hidden edit');
  git('update-index', '--no-assume-unchanged', 'original'); fs.writeFileSync(path.join(j.root, 'original'), 'unchanged\n');
  await assert.rejects(commitAdvanceStage(j, 'recipe', {validate, interrupt: point => {if(point === 'intent') throw Error('stop');}}), /stop/);
  const filename = path.join(j.stateTarget, 'commit-recipe.json'), intent = JSON.parse(fs.readFileSync(filename));
  const originalTree = intent.tree;
  git('read-tree', intent.tree); fs.writeFileSync(path.join(j.root, 'foreign'), 'forged'); git('add', 'foreign'); intent.tree = git('write-tree');
  git('read-tree', intent.parent);
  intent.raw = intent.raw.replace(originalTree, intent.tree);
  intent.head = createHash('sha1').update(`commit ${Buffer.byteLength(intent.raw)}\0`).update(intent.raw).digest('hex');
  fs.writeFileSync(filename, JSON.stringify(intent));
  await assert.rejects(commitAdvanceStage(j, 'recipe', {validate}), /undeclared paths/);
  assert.equal(git('rev-parse', 'HEAD'), intent.parent);
});

test('author refresh resume rejects a forged inherited selector despite valid parents and unchanged owned postimages', async t => {
  const f = authorRefreshFixture(t), name = 'data/ownership-selection.json';
  await assert.rejects(f.run({interrupt: where => { if (where === 'intent') throw Error('interrupted'); }}), /interrupted/);
  const filename = path.join(f.j.stateTarget, 'author-tree-refresh.json'), intent = JSON.parse(fs.readFileSync(filename));
  const originalIndex = f.git('write-tree'), originalSelector = fs.readFileSync(path.join(f.root, name));
  const owned = 'coordination/engineering/fixture/receipt.json', originalOwned = fs.readFileSync(path.join(f.root, owned));
  const originalTree = intent.tree;
  const forge = (args, input) => execFileSync('git', args, {cwd: f.root, input, encoding: 'utf8',
    env: {...process.env, GIT_NO_LAZY_FETCH: '1', GIT_INDEX_FILE: path.join(f.root, '.git', 'refresh-adverse-index')}}).trim();
  const blob = forge(['hash-object', '-w', '--stdin'], '{"selected":"forged"}\n');
  forge(['read-tree', originalTree]);
  forge(['update-index', '--index-info'], `100644 ${blob}\t${name}\n`);
  intent.tree = forge(['write-tree']);
  const raw = f.git('cat-file', '-p', intent.head).replace(`tree ${originalTree}\n`, `tree ${intent.tree}\n`) + '\n';
  intent.head = forge(['hash-object', '-t', 'commit', '-w', '--stdin'], raw);
  const forgedIntent = Buffer.from(JSON.stringify(intent) + '\n'); fs.writeFileSync(filename, forgedIntent);
  assert.notEqual(intent.tree, originalTree);
  assert.deepEqual(f.git('rev-list', '--parents', '-n', '1', intent.head).split(' '), [intent.head, f.before, f.main]);
  assert.equal(f.git('ls-tree', intent.head, '--', owned), f.git('ls-tree', f.before, '--', owned));
  assert.equal(f.git('show', intent.head + ':' + name), '{"selected":"forged"}');
  await assert.rejects(f.run(), /candidate differs from the exact original merge tree/);
  assert.equal(f.git('rev-parse', 'HEAD'), f.before); assert.equal(f.git('write-tree'), originalIndex);
  assert.deepEqual(fs.readFileSync(path.join(f.root, name)), originalSelector);
  assert.deepEqual(fs.readFileSync(path.join(f.root, owned)), originalOwned);
  assert.deepEqual(fs.readFileSync(filename), forgedIntent);
  assert.equal(f.calls.some(args => args.includes('update-ref')), false);
  assert.equal(fs.existsSync(path.join(f.j.stateTarget, 'author-tree-refreshed.json')), false);
});

test('automatic commit recovery rejects forged parent-tree allowance and preserves unrelated staged contents', async t => {
  const {j, git, validate} = automaticGitFixture(t);
  await prepareAdvanceStage(j, 'recipe', 'recipe', {}, () => ({'recipe-index.json': Buffer.from('{}\n')}));
  await assert.rejects(commitAdvanceStage(j, 'recipe', {validate, interrupt: point => {
    if (point === 'intent') throw Error('interrupted');
  }}), /interrupted/);
  const filename = path.join(j.stateTarget, 'commit-recipe.json'), intent = JSON.parse(fs.readFileSync(filename));
  const head = git('rev-parse', 'HEAD'), name = 'foreign-staged', foreign = Buffer.from('preserve staged contents\n');
  fs.writeFileSync(path.join(j.root, name), foreign); git('add', name);
  const stagedTree = git('write-tree'), stagedEntry = git('ls-files', '--stage', '--', name);
  assert.notEqual(stagedTree, git('rev-parse', intent.parent + '^{tree}'));
  intent.parent_tree = stagedTree;
  const forgedIntent = Buffer.from(JSON.stringify(intent) + '\n'); fs.writeFileSync(filename, forgedIntent);
  await assert.rejects(commitAdvanceStage(j, 'recipe', {validate}), /parent tree differs from the actual parent commit/);
  assert.equal(git('rev-parse', 'HEAD'), head); assert.equal(git('write-tree'), stagedTree);
  assert.equal(git('ls-files', '--stage', '--', name), stagedEntry);
  assert.equal(git('show', ':' + name), foreign.toString().trim());
  assert.deepEqual(fs.readFileSync(path.join(j.root, name)), foreign);
  assert.deepEqual(fs.readFileSync(filename), forgedIntent);
  assert.equal(fs.existsSync(path.join(j.stateTarget, 'committed-recipe.json')), false);
});

// Real author authority and default transition wiring; no operator execution.
{
const {default: test} = await import('node:test');
const {default: assert} = await import('node:assert/strict');
const {default: fs} = await import('node:fs');
const {default: path} = await import('node:path');
const {default: os} = await import('node:os');
const {execFileSync} = await import('node:child_process');
const {createHash} = await import('node:crypto');
const {workspaceManager} = await import('../scripts/local-workspace.mjs');
const {renderClaim} = await import('../scripts/issue-claim-contract.mjs');
const {automaticAuthorGuard, openAdvanceJournal, runAutomaticDelivery, readAdvanceStatus, automaticDeliveryObservations} = await import('../scripts/delivery-handoff-advance.mjs');
const {prepareRequests} = await import('../scripts/prepare-delivery-handoff.mjs');
const hash = raw => createHash('sha256').update(raw).digest('hex'), clone = value => structuredClone(value);
function managedAutomaticFixture(t) {
  const outer = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'automatic-real-'))), seed = path.join(outer, 'seed');
  fs.mkdirSync(seed); t.after(() => fs.rmSync(outer, {recursive: true, force: true}));
  const run = (root, ...args) => execFileSync('git', ['-C', root, ...args], {encoding: 'utf8', stdio: ['pipe', 'pipe', 'pipe'],
    env: {...process.env, GIT_NO_LAZY_FETCH: '1', GIT_CONFIG_NOSYSTEM: '1', GIT_CONFIG_GLOBAL: '/dev/null',
      GIT_AUTHOR_NAME: 'Fixture', GIT_AUTHOR_EMAIL: 'fixture@example.invalid', GIT_COMMITTER_NAME: 'Fixture', GIT_COMMITTER_EMAIL: 'fixture@example.invalid'}}).trim();
  run(seed, 'init', '-q', '-b', 'main');
  run(seed, 'config', 'user.name', 'Fixture'); run(seed, 'config', 'user.email', 'fixture@example.invalid');
  fs.writeFileSync(path.join(seed, 'original'), 'untouched\n');
  run(seed, 'add', 'original'); run(seed, 'commit', '-qm', 'baseline');
  run(seed, 'remote', 'add', 'origin', seed);
  const worker = process.env.CODEX_THREAD_ID ?? 'non-codex-automatic-fixture';
  const manager = workspaceManager(seed), entry = manager.allocate({worker, branch: 'engineering/automatic-real', reserveGiB: 0.001, include: ['coordination/engineering/automatic-real', 'coordination/engineering/melanesia363-additive-delivery-20261010']});
  const root = entry.path, git = (...args) => run(root, ...args), prefix = 'coordination/engineering/automatic-real/';
  const spec = {mode: 'engineering', max_prs: 1, depends_on: [99], owned_paths: [prefix], scope: 'Actual automatic handoff guard fixture',
    evidence_quality: {version: 1, manifest_path: prefix + 'evidence-quality.json', subject_ids: [], pins: {}, review_kind: 'code'}};
  const issue = {number: 100, state: 'open', created_at: '2026-10-10T00:00:00Z', labels: ['type:engineering', 'kind:work-item', 'status:ready']};
  const claim = {version: 1, active: true, worker_id: worker, claim_id: 'automatic-real-claim', branch: entry.branch,
    mode: 'engineering', expires_at: new Date(Date.now() + 3600000).toISOString()};
  const control = {spec, issue, claim, dependency: {number: 99, state: 'closed'}, prs: [], blockers: []};
  const api = async route => {
    if (route.endsWith('/issues/100')) return {...clone(control.issue), body: `<!-- worldatlas-work:v1\n${JSON.stringify(control.spec)}\n-->`};
    if (route.endsWith('/issues/99')) return clone(control.dependency);
    if (route.includes('/issues/100/comments?')) return [{id: 1, user: {login: 'github-actions[bot]'}, body: renderClaim(control.claim)}, ...clone(control.blockers)];
    if (route.includes('/issues/100/timeline?')) return control.prs.map(pr => ({source: {issue: {number: pr.number, body: 'Refs #100', pull_request: {url: 'fixture'}}}}));
    const pr = control.prs.find(pr => route.endsWith('/pulls/' + pr.number)); if (pr) return clone(pr);
    throw Error('Unexpected guard route: ' + route);
  };
  const config = {automation: {issue_number: 100}};
  return {root, git, entry, manager, control, api, config, prefix};
}

test('real automatic author guard uses managed identity and declared output scope without leases', async t => {
  const f = managedAutomaticFixture(t), api=async route=>{
    assert(!route.includes('/comments')&&!route.includes('/timeline')&&!route.endsWith('/issues/99'));
    return f.api(route);
  }, guard = await automaticAuthorGuard(f.root, f.config, api);
  const scope = {branch: f.entry.branch, paths: [f.prefix + 'advance/recipe.json']};
  assert.equal((await guard(scope)).worker, process.env.CODEX_THREAD_ID ?? f.entry.worker);
  const original = clone(f.control);
  f.control.claim.active=false;f.control.claim.expires_at='2000-01-01';
  f.control.dependency.state='open';
  assert.deepEqual(await guard(scope),{worker:f.entry.worker,paths:f.control.spec.owned_paths});
  for(const mutate of [c=>{c.spec.owned_paths=['coordination/engineering/foreign/'];},c=>{c.issue.state='closed';}]){
    Object.assign(f.control,clone(original));mutate(f.control);await assert.rejects(guard(scope));
  }
  Object.assign(f.control,clone(original));
  await assert.rejects(guard({...scope,branch:'engineering/foreign'}),/managed ownership/);
  await assert.rejects(guard({...scope,paths:['coordination/engineering/foreign/output.json']}),/output exceeds/);
});

// This expected-refusal test exposes captured workspace authority surviving a
// registry revocation. Restore the exact fixture registry before cleanup.
test('real automatic author guard rereads current managed ownership before each mutation', async t => {
  const f = managedAutomaticFixture(t); let changeDuringRead;
  const guard = await automaticAuthorGuard(f.root, f.config, async route => {
    const result = await f.api(route); if (route.endsWith('/issues/100')) changeDuringRead?.(); return result;
  });
  const scope = {branch: f.entry.branch, paths: [f.prefix + 'advance/recipe.json']}; await guard(scope);
  const stateFile = path.join(f.manager.report().registry, 'state.json'), original = fs.readFileSync(stateFile);
  try {
    for (const mutate of [s => {s.entries[0].status = 'preparing';}, s => {s.entries[0].token = 'replacement-token';},
      s => {s.entries[0].branch = 'engineering/foreign';}, s => {s.entries = [];}]) {
      const state = JSON.parse(original); mutate(state); fs.writeFileSync(stateFile, JSON.stringify(state));
      await assert.rejects(guard(scope), /managed|workspace|ownership/i);
    }
    for (const mutate of [s => {s.entries[0].status = 'preparing';}, s => {s.entries[0].token = 'replacement-token';}]) {
      fs.writeFileSync(stateFile, original);
      changeDuringRead = () => {const state = JSON.parse(original); mutate(state); fs.writeFileSync(stateFile, JSON.stringify(state));};
      await assert.rejects(guard(scope), /managed|workspace|ownership/i);
    }
  } finally { fs.writeFileSync(stateFile, original); }
});

function realAutomaticRecipe(f,{explicit=false}={}){
 const physicalBytes=2000,decodedBytes=5000,phase=4*1024*1024,legacy=false;
 const supervisor='coordination/engineering/melanesia363-additive-delivery-20261010/supervise-source-native-linux.mjs';
 const codePaths=['code.mjs','scripts/local-workspace.mjs','scripts/worker-identity.mjs',supervisor];
 for(const name of codePaths){fs.mkdirSync(path.dirname(path.join(f.root,name)),{recursive:true});fs.writeFileSync(path.join(f.root,name),'// synthetic byte custody '+name+'\n');}
 f.git('add','--',...codePaths);f.git('commit','-qm','fixture code custody');
 const commit=f.git('rev-parse','HEAD');
 let charged=0;
 const budget={add({bytes}){assert.ok(Number.isSafeInteger(bytes)&&bytes>=0);charged+=bytes;assert.ok(charged<8*1024*1024,'bounded fixture accounting');}};
 const reader={budget,git:(...args)=>Buffer.from(f.git(...args)),pin(c,name){
   const line=f.git('ls-tree',c,'--',name),match=/^100644 blob ([a-f0-9]{40})\t/.exec(line);assert.ok(match,'ordinary committed input '+name);
   const raw=execFileSync('git',['-C',f.root,'cat-file','blob',match[1]],{env:{...process.env,GIT_NO_LAZY_FETCH:'1'}});
   assert.ok(raw.length<128*1024);budget.add({bytes:raw.length});
   return {commit:c,path:name,mode:'100644',git_blob_oid:match[1],bytes:raw.length,sha256:hash(raw)};
 },read(p){
   const actual=this.pin(p.commit,p.path);assert.equal(actual.git_blob_oid,p.git_blob_oid??p.blob);assert.equal(actual.bytes,p.bytes);assert.equal(actual.sha256,p.sha256);
   return execFileSync('git',['-C',f.root,'cat-file','blob',actual.git_blob_oid],{env:{...process.env,GIT_NO_LAZY_FETCH:'1'}});
 },json(p){return JSON.parse(this.read(p));}};
 const codePin=name=>{const p=reader.pin(commit,name);return {path:name,bytes:p.bytes,sha256:p.sha256};};
 const files=new Map();
 const pin=(path,bytes=123,extra={})=>({commit,path,mode:'100644',blob:hash(path).slice(0,40),bytes,sha256:hash(path),...extra});
 const put=(name,body)=>{const raw=Buffer.from(JSON.stringify(body)+'\n');fs.writeFileSync(path.join(f.root,name),raw);f.git('add','--',name);f.git('commit','-qm','fixture '+name);const c=f.git('rev-parse','HEAD'),actual=reader.pin(c,name),{git_blob_oid,...rest}=actual,p={...rest,blob:git_blob_oid};files.set(name,{raw,body,pin:p});return {commit:c,path:name};};
 const oldCode=codePin('code.mjs');
 const support=['scripts/local-workspace.mjs','scripts/worker-identity.mjs'].map(codePin);
 const runtime={version:1,platform:'linux',runtime:['git','node','process-inspector','time'].map(role=>({role,path:'/bin/'+role,mode:493,bytes:1000,sha256:hash(role)})),supervisor:codePin(supervisor),...(!legacy?{support_code:support}:{})};
 const resources={processing_allowance:{phaseBytes:phase,rssBytes:8*1024*1024},output_reserve:131072,operating_limits:{rss_bytes:8*1024*1024,wall_seconds:30,output_bytes:262144,retained_bytes:600000,log_bytes:1000,monitor_bytes:1000,receipt_bytes:1000}};
 const common={version:1,executed_code:[oldCode],installed_modules:[{...oldCode,path:'node_modules/module.js'}],report:pin('report.json'),parent:{components:3},baseline:{pins:[pin('selection.json')]},output_reserve:131072,operating_runtime:runtime,...(!legacy?{operating_profile:'source-native-v2',...resources}:{})};
 const componentIds=['c-a','c-b','c-c'],targetIds=['t-one'];
 const physicalPins=componentIds.map((id,i)=>pin('retained/components-00'+i+'.jsonl.gz',physicalBytes));
 const sourceMeta=pin('retained/sources-000.jsonl.gz',100);
 const admin=pin('admin.gz',100,{uncompressed_bytes:1000,uncompressed_sha256:hash('decoded-admin')});
 const locator=put('locators.json',Object.fromEntries(componentIds.map((id,i)=>[id,{path:'components-00'+i+'.jsonl.gz'}])));
 const handoff={scopeIds:componentIds,candidate_source_native_bindings:componentIds.map(component_id=>({component_id,retained_payload:{target_stable_location_id:'t-one'}})),
  original_physical_comparison_bindings:componentIds.map(component_id=>({component_id,physical_comparison:{row:{component_id}},original_queried_source_metadata:[]})),
  original_gap_membership:{members:componentIds.map((component_id,i)=>({component_id,original_batch_id:'unrelated-'+i}))},
  consumed_inputs:[files.get(locator.path).pin,...physicalPins,sourceMeta],
  consumed_source_bindings:[{source_id:'admin',catalogue_record:{parts:[{path:admin.path,bytes:admin.bytes,sha256:admin.sha256,uncompressed_bytes:admin.uncompressed_bytes,uncompressed_sha256:admin.uncompressed_sha256}]}}],
  physical_restoration:{restorations:[...physicalPins.map((p,i)=>({path:'components-00'+i+'.jsonl.gz',whole_original_bytes:p.bytes,whole_original_sha256:p.sha256,decoded_bytes:decodedBytes,decoded_sha256:hash('decoded-'+i),rows:1})),{path:'sources-000.jsonl.gz',whole_original_bytes:100,whole_original_sha256:sourceMeta.sha256,decoded_bytes:500,decoded_sha256:hash('source-decoded'),rows:3}]}};
 const handoffLocator=put('handoff.json',handoff),hp=files.get(handoffLocator.path).pin;
 const {commit:_,...entrySource}=hp;
 const registry=put('registry.json',{version:1,kind:'accepted-administrative-handoffs-v1',entries:[{id:'accepted-whole',accepted_source_commit:hp.commit,source:entrySource,cohort_ids:componentIds,target_ids:targetIds}]});
 const rp=files.get(registry.path).pin,bank=pin('bank.json'),manifest=pin('manifest.json'),bounds=pin('bounds.gz',100,{uncompressed_bytes:1000,uncompressed_sha256:hash('bounds')}),catalogue=pin('catalogue.json');
 const source={...clone(common),operation:'retained-land-source-premises-v1',destination:'.cache/native-grid-candidates/old-source',source_rule:{version:1,profile:'retained-consumed-administrative-source',geometry_scope:'full-component',cohort_ids:componentIds,expected_ids:componentIds,registry_path:rp.path,
  ...Object.fromEntries(['cases_path','outcomes_path','payloads_path','simplified_comparison_path','generalized_comparison_path','remainders_path'].map(k=>[k,hp.path])),
  administrative_products:[admin],original_products:[],target_banks:[bank.path],manifest_path:manifest.path,bounds_path:bounds.path,source_catalogue_path:catalogue.path,inputs:[hp,rp,admin,bank,manifest,bounds,catalogue]}};
 if(explicit)source.source_rule.expected_ids=componentIds.slice(1);
 const sourceTemplate=put('source-template.json',source),slots={source_request_path:files.get(sourceTemplate.path).pin,operating_path:pin('operating.json'),publication_path:pin('publication.json'),facts_path:pin('facts.json'),inventory_path:pin('inventory.gz',100,{uncompressed_bytes:1000,uncompressed_sha256:hash('inventory')})};
 const owner=pin('native-owner.gz',200,{uncompressed_bytes:1000,uncompressed_sha256:hash('owner')}),lat=pin('latitudes.gz',50,{uncompressed_bytes:100,uncompressed_sha256:hash('lat')});
 const native={...clone(common),operation:'unactivated-additive-native-batch-v1',destination:'.cache/native-grid-candidates/old-native',additive:{source_profile:source.source_rule.profile,scope_ids:componentIds,source_execution_commit:commit,source_runtime:{bytes:1000,sha256:hash('node')},manifest_path:manifest.path,bounds_path:bounds.path,latitudes_path:lat.path,original_bounds:{sha256:bounds.sha256},owner_parts:[{path:owner.path,manifest_path:'owner.bin',manifest_descriptor:{bytes:owner.bytes}}],...Object.fromEntries(Object.entries(slots).map(([k,p])=>[k,p.path])),inputs:[...source.source_rule.inputs,owner,lat,...Object.values(slots)]}};
 if(explicit)native.additive.scope_ids=componentIds.slice(1);
 const nativeTemplate=put('native-template.json',native);
 const selection={handoff_id:'accepted-whole',source_template:sourceTemplate,source_resources:clone(resources),native_resources:clone(resources),physical_locator:{input:locator,format:'keyed-path'},targets:[{target_id:'t-one',bank_path:bank.path,native_template:nativeTemplate}],
  predecessor_allowance:Object.fromEntries(Object.keys(slots).map(k=>[k,{bytes:k==='source_request_path'?131072:1000,...(k==='inventory_path'?{uncompressed_bytes:10000}:{})}])),native_request_bytes_bound:131072};
 const recipe={version:1,id:'delivery',mode:'greedy-model',registry,destination_prefix:'.cache/native-grid-candidates/delivery',handoffs:[selection]};
 if(explicit){recipe.mode='explicit-groups';delete recipe.handoffs;recipe.groups=[{id:'subset',handoff_id:'accepted-whole',component_ids:componentIds.slice(1),target_ids:['t-one'],source_template:sourceTemplate,native_template:nativeTemplate}];}
 const recipeLocator=put('recipe.json',recipe);return {reader,recipe,recipeLocator,budget,componentIds};
}

test('default automatic delivery commits actual recipe and issued SOURCE requests then preserves the terminal barrier', async t => {
  const f = managedAutomaticFixture(t), input = realAutomaticRecipe(f);
  const config = {...f.config, recipe: input.recipeLocator};
  const journal = openAdvanceJournal(f.root, f.prefix + 'advance', config.recipe, {budget: input.budget});
  const validate = await automaticAuthorGuard(f.root, config, f.api);
  const parent = f.git('rev-parse', 'HEAD'), initialCount = Number(f.git('rev-list', '--count', 'HEAD'));
  const result = await runAutomaticDelivery(journal, config, input.reader, {prepareRequests}, {validate});
  assert.equal(result.kind, 'source-terminal'); assert.equal(result.stage, 'source-delivery-001');
  assert.deepEqual(readAdvanceStatus(journal).completed, ['recipe', 'requests']);
  assert.equal(Number(f.git('rev-list', '--count', 'HEAD')), initialCount + 2);
  assert.equal(f.git('rev-parse', 'HEAD~2'), parent);
  const observation = automaticDeliveryObservations(journal, config).observations;
  const indexPath = journal.destination + '/recipe/recipe-index.json';
  const index = input.reader.json(input.reader.pin(observation.template_commit, indexPath));
  assert.equal(index.mode, 'greedy-model'); assert.deepEqual(index.groups[0].component_ids, input.componentIds);
  const requestPath = journal.destination + '/requests/delivery-001-source-request.json';
  const requestPin = input.reader.pin(f.git('rev-parse', 'HEAD'), requestPath), request = input.reader.json(requestPin);
  assert.deepEqual(request.source_rule.expected_ids, input.componentIds);
  assert.equal(request.operation, 'retained-land-source-premises-v1');
  assert.equal(request.destination, '.cache/native-grid-candidates/delivery-delivery-001-source');
  assert.equal(fs.existsSync(path.join(f.root, request.destination)), false);
  const requestBytes = input.reader.read(requestPin), head = f.git('rev-parse', 'HEAD');
  const repeated = await runAutomaticDelivery(journal, config, input.reader, {prepareRequests}, {validate});
  assert.equal(repeated.kind, 'source-terminal'); assert.equal(f.git('rev-parse', 'HEAD'), head);
  assert.deepEqual(input.reader.read(requestPin), requestBytes);
  assert.equal(readAdvanceStatus(journal).waiting.kind, 'source-terminal');
});
test('default automatic entry issues a genuine v2 subset and stops only at its SOURCE terminal', async t => {
  const f=managedAutomaticFixture(t),input=realAutomaticRecipe(f,{explicit:true});
  const config={...f.config,recipe:input.recipeLocator};
  const j=openAdvanceJournal(f.root,f.prefix+'advance-subset',config.recipe,{budget:input.budget});
  const validate=await automaticAuthorGuard(f.root,config,f.api);
  const result=await runAutomaticDelivery(j,config,input.reader,{prepareRequests},{validate});
  assert.equal(result.kind,'source-terminal');assert.equal(result.stage,'source-subset');
  const request=input.reader.json(input.reader.pin(f.git('rev-parse','HEAD'),j.destination+'/requests/subset-source-request.json'));
  assert.equal(request.operating_profile,'source-native-v2');
  assert.deepEqual(request.source_rule.expected_ids,input.componentIds.slice(1));
  assert.deepEqual(request.source_rule.cohort_ids,input.componentIds);
  assert.equal(fs.existsSync(path.join(f.root,request.destination)),false);
  const head=f.git('rev-parse','HEAD');
  await runAutomaticDelivery(j,config,input.reader,{prepareRequests},{validate});
  assert.equal(f.git('rev-parse','HEAD'),head,'unchanged resumed requests do not get another commit');
});

test('default automatic delivery revalidates actual issue scope before committing newly prepared requests', async t => {
  const f = managedAutomaticFixture(t), input = realAutomaticRecipe(f), config = {...f.config, recipe: input.recipeLocator};
  const journal = openAdvanceJournal(f.root, f.prefix + 'advance', config.recipe, {budget: input.budget});
  const validate = await automaticAuthorGuard(f.root, config, f.api);
  const initialCount = Number(f.git('rev-list', '--count', 'HEAD'));
  const adapters = {prepareRequests: (...args) => {const products = prepareRequests(...args); f.control.issue.state = 'closed'; return products;}};
  await assert.rejects(runAutomaticDelivery(journal, config, input.reader, adapters, {validate}), /open GitHub issue/);
  assert.equal(Number(f.git('rev-list', '--count', 'HEAD')), initialCount + 1);
  assert.deepEqual(readAdvanceStatus(journal).completed, ['recipe', 'requests']);
  assert.equal(fs.existsSync(path.join(journal.stateTarget, 'committed-requests.json')), false);
  const prepared = fs.readFileSync(path.join(journal.target, 'requests/delivery-001-source-request.json'));
  f.control.issue.state = 'open';
  const resumed = await runAutomaticDelivery(journal, config, input.reader, {prepareRequests}, {validate});
  assert.equal(resumed.kind, 'source-terminal'); assert.equal(Number(f.git('rev-list', '--count', 'HEAD')), initialCount + 2);
  assert.deepEqual(fs.readFileSync(path.join(journal.target, 'requests/delivery-001-source-request.json')), prepared);
});
}

import {qualifiedPreparedReuse} from '../scripts/delivery-handoff-advance.mjs';
test('qualified stage reuse preserves immutable products and records only references, with once-only resume', async t => {
 const f=fixture(),j=journal(t);j.reader=f.reader;
 const configPin=f.add(commit,'config.json',{original:'configuration'});
 const receipt=f.stage(commit,'qualified','requests',{'request.json':{actual:'request'}});
 const receiptPath=commit+':qualified/preparation.json';
 const body=JSON.parse(f.files.get(receiptPath));body.binding.config_sha256=configPin.sha256;
 f.add(commit,'qualified/preparation.json',body);
 const adoption={config:{commit,path:'config.json'},receipt};
 const products={'request.json':f.reader.read(f.reader.pin(commit,'qualified/request.json'))};
 let calls=0;
 await prepareAdvanceStage(j,'requests','requests',{derived:'same request'},()=>{calls++;return products;},{adoption});
 assert.equal(calls,1);assert.deepEqual(readAdvanceStatus(j).completed,['requests']);
 assert.equal(fs.existsSync(path.join(j.target,'requests')),false,'no copied evidence directory');
 const event=fs.readFileSync(path.join(j.stateTarget,'requests.completed.json'));
 await prepareAdvanceStage(j,'requests','requests',{derived:'same request'},()=>{throw Error('rerun');},{adoption});
 assert.deepEqual(fs.readFileSync(path.join(j.stateTarget,'requests.completed.json')),event);
 assert.throws(()=>qualifiedPreparedReuse(f.reader,adoption,'retain'),/phase/);
 assert.throws(()=>qualifiedPreparedReuse(f.reader,adoption,'requests',{'request.json':Buffer.from('{}')}),/no longer matches/);
 f.files.set(commit+':qualified/request.json',Buffer.from('corrupt'));
 assert.throws(()=>readAdvanceStatus(j),/differs/);
});

test('stage reuse rejects wrong raw config, missing outputs and changed inputs before completion', async t => {
 const f=fixture(),j=journal(t);j.reader=f.reader;
 f.add(commit,'config.json',{original:true});
 const receipt=f.stage(commit,'qualified','requests',{'request.json':{actual:true}});
 const adoption={config:{commit,path:'config.json'},receipt};
 const products={'request.json':f.reader.read(f.reader.pin(commit,'qualified/request.json'))};
 await assert.rejects(prepareAdvanceStage(j,'requests','requests',{},()=>products,{adoption}),/raw config/);
 assert.deepEqual(readAdvanceStatus(j).completed,[]);
 assert.equal(fs.existsSync(path.join(j.target,'requests')),false);
 await assert.rejects(prepareAdvanceStage(j,'requests','requests',{changed:true},()=>products,{adoption}),/Changed stage inputs/);
});

// Explicit read-only real-fixture suite. Requires the retained immutable Git
// objects; never fetches science, launches operators, edits the frozen branch or
// claims actual subsequent-batch adoption. Default CI uses the bounded controls.
if (process.env.WORLDATLAS_DELIVERY_V2_FIXTURE === '1') {
  test('frozen Norway B v2 subset resumes qualified final and earlier operator receipts without evidence copies', async t => {
    const prep=await import('../scripts/prepare-delivery-handoff.mjs');
    const flow=await import('../scripts/delivery-handoff-advance.mjs');
    const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
    const r=prep.pinReader(root,{allowance:{phaseBytes:536870912,rssBytes:1073741824}});
    const head='abf421fbca84da6673a6b0477acfefc9fd594ff4',prefix='coordination/engineering/nor18-selected-20261012/';
    const loc=name=>({commit:head,path:prefix+name}),read=name=>r.json(r.pin(head,prefix+name));
    const locator=p=>({commit:p.commit,path:p.path});
    const final=read('north13-finalize-config-001.json'),requests=read('north13-requests-config-001.json'),composition=read('north13-compose-config-001.json');
    const registry=r.json(final.registry),entry=registry.entries.find(e=>e.source_authority.path.includes('/north13-'));
    const binding=r.json(entry.source_authority),source=r.json(binding.original_pins.source_request),ids=source.source_rule.expected_ids;
    const accepted=r.json(requests.registry).entries.find(e=>e.id===requests.groups[0].handoff_id);
    const handoff=r.json({...accepted.source,commit:accepted.accepted_source_commit});
    const recipe={version:1,id:'nor13',mode:'explicit-groups',registry:locator(requests.registry),new_prefix:prefix,
      destination_prefix:'.cache/native-grid-candidates/nor13-continuation',selector:locator(final.selector),package_inputs:locator(final.package_inputs),
      retained_registries:[locator(composition.registries[0])],groups:[{id:'nor13',handoff_id:requests.groups[0].handoff_id,component_ids:ids,
        target_ids:[...new Set(handoff.candidate_source_native_bindings.filter(row=>ids.includes(row.component_id)).map(row=>row.retained_payload.target_stable_location_id))],
        source_template:locator(binding.original_pins.source_request),native_template:locator(binding.original_pins.native_request)}]};
    assert.equal(accepted.cohort_ids.length,18);assert.equal(ids.length,13);
    const adoption={config:loc('north13-finalize-config-001.json'),receipt:loc('north13-final-001/preparation.json')};
    const adapters={composeAuthorities:prep.composeAuthorities,rebindCustody:prep.rebindCustody,finalizeDelivery:prep.finalizeDelivery,
      authorityReader:()=>flow.deliveryAuthorityReader(root,r)};
    const snapshot=r.read(r.pin(head,adoption.receipt.path));
    const result=flow.qualifyFinalizedCheckpoint(recipe,adoption,r,adapters);
    assert.deepEqual(result.component_ids,ids);assert.deepEqual(r.read(result.receipt),snapshot);
    const bad=structuredClone(recipe);bad.groups[0].target_ids=['foreign-target'];
    assert.throws(()=>flow.qualifyFinalizedCheckpoint(bad,adoption,r,adapters),/target identities/);
    const omitted=structuredClone(recipe);omitted.retained_registries=[];
    assert.throws(()=>flow.qualifyFinalizedCheckpoint(omitted,adoption,r,adapters),/foreign\/duplicate/);
    assert.throws(()=>flow.qualifyFinalizedCheckpoint(recipe,adoption,r,{...adapters,finalizeDelivery:(...args)=>{
      const out=prep.finalizeDelivery(...args);delete out['ownership-selection.json'];return out;
    }}),/inventory differs/);
    // Dry-run through the actual automatic fixed transition, using an in-memory
    // recipe locator only. The original products all use the genuine Git reader.
    const raw=prep.jsonBytes(recipe),pin={commit:head,path:'fixture-recipe.json',mode:'100644',git_blob_oid:'a'.repeat(40),bytes:raw.length,sha256:digest(raw)};
    const reader={...r,pin:(c,p)=>p===pin.path&&c===head?pin:r.pin(c,p),read:p=>p.path===pin.path?raw:r.read(p),json:p=>p.path===pin.path?recipe:r.json(p)};
    const j=journal(t);j.reader=reader;
    const config={version:1,recipe:{commit:head,path:pin.path},resume_finalized:adoption};
    let publicationChecks=0;
    const outcome=await flow.runAutomaticDelivery(j,config,reader,adapters,{validate:async()=>{},beforePublication:async()=>{publicationChecks++;},
      commitStage:()=>{throw Error('Frozen checkpoint tried to commit duplicate evidence');}});
    assert.equal(outcome.kind,'publication-review');assert.equal(publicationChecks,1);
    assert.deepEqual(readAdvanceStatus(j).completed,[]);
    assert.equal(fs.readdirSync(j.target).some(name=>fs.lstatSync(path.join(j.target,name)).isDirectory()),false);
    for(const kind of ['source','native']){
      const observation={publication:loc('north13-'+kind+'-qualified-001/publication.json'),terminal:loc('north13-'+kind+'-qualified-001/terminal.json')};
      const retained=flow.committedRetentionConfig(r,observation),products=prep.retainProducts(retained.config,root,r,retained.readLocal);
      const cfg=kind==='source'?'north13-retain-config-001.json':'north13-native-retain-config-001.json';
      const reuse={config:loc(cfg),receipt:loc('north13-'+kind+'-qualified-001/preparation.json')};
      flow.qualifiedPreparedReuse(r,reuse,'retain',products);
      j.reader=r;
      await prepareAdvanceStage(j,kind+'-nor13','retain',observation,()=>products,{adoption:reuse});
      assert.equal(fs.existsSync(path.join(j.target,kind+'-nor13')),false);
    }
    assert.deepEqual(readAdvanceStatus(j).completed,['native-nor13','source-nor13']);
    assert.deepEqual(r.read(result.receipt),snapshot);
  });
}

test('automatic receipt adoption never commits copied products, including repeated invocation', async t => {
 const f=fixture(),j=journal(t);j.reader=f.reader;
 const original=f.add(commit,'original-config.json',{scope:'unchanged'});
 const receipt=f.stage(commit,'issued','requests',{'request.json':{scope:'unchanged'}});
 const document=JSON.parse(f.files.get(commit+':issued/preparation.json'));document.binding.config_sha256=original.sha256;
 f.add(commit,'issued/preparation.json',document);
 const adoption={config:{commit,path:'original-config.json'},receipt};
 const config={prepared_stages:{requests:adoption}},products={'request.json':f.reader.read(f.reader.pin(commit,'issued/request.json'))};
 let preparations=0,commits=0;
 const nextStage=async()=>readAdvanceStatus(j).completed.includes('requests')
  ?{waiting:{status:'waiting',stage:'source-g',kind:'source-terminal',detail:'Genuine terminal absent'}}
  :{id:'requests',phase:'requests',input:{scope:'unchanged'},produce:()=>{preparations++;return products;}};
 const options={validate:async()=>{},nextStage,commitStage:()=>{commits++;throw Error('duplicate commit');}};
 assert.equal((await runAutomaticDelivery(j,config,f.reader,{},options)).kind,'source-terminal');
 assert.equal((await runAutomaticDelivery(j,config,f.reader,{},options)).kind,'source-terminal');
 assert.equal(preparations,1);assert.equal(commits,0);assert.equal(fs.existsSync(path.join(j.target,'requests')),false);
 await assert.rejects(prepareAdvanceStage(j,'requests','requests',{scope:'unchanged'},()=>products),/reuse binding changed/);
 assert.throws(()=>qualifiedPreparedReuse(f.reader,adoption,'review'),/cannot be adopted/);
});

test('reused automatic observations preserve authenticated original aliases and reject foreign outputs', async t => {
 const f=fixture(),j=journal(t);j.reader=f.reader;
 const config=f.add(commit,'registry-config.json',{authorities:[]});
 const receipt=f.stage(later,'published','registry',{'authority-registry.json':{version:1,entries:[]}});
 const doc=JSON.parse(f.files.get(later+':published/preparation.json'));doc.binding.config_sha256=config.sha256;
 f.add(later,'published/preparation.json',doc);
 f.add(commit,'published/authority-registry.json',{version:1,entries:[]});
 const adoption={config:{commit,path:'registry-config.json'},receipt};
 const products={'authority-registry.json':f.reader.read(f.reader.pin(later,'published/authority-registry.json'))};
 await prepareAdvanceStage(j,'registry','registry',{},()=>products,{adoption});
 const original={commit,path:'published/authority-registry.json'};
 assert.deepEqual(automaticDeliveryObservations(j,{observations:{registry:original}}).observations.registry,original);
 f.add(commit,'published/authority-registry.json',{version:1,entries:['foreign']});
 assert.throws(()=>automaticDeliveryObservations(j,{observations:{registry:original}}),/conflicts/);
});


test('reuse refuses an interrupted product directory without completing or changing its sentinel', async t => {
 const f=fixture(),j=journal(t);j.reader=f.reader;
 const products={'a.json':Buffer.from('{}\n')};
 await assert.rejects(prepareAdvanceStage(j,'requests','requests',{},()=>products,{interrupt:()=>{throw Error('interruption');}}),/interruption/);
 const sentinel=fs.readFileSync(path.join(j.target,'requests/a.json'));
 let called=false;
 await assert.rejects(prepareAdvanceStage(j,'requests','requests',{},()=>{called=true;return products;},
  {adoption:{config:{commit,path:'unused.json'},receipt:{commit,path:'unused/preparation.json'}}}),/Cannot adopt/);
 assert.equal(called,false);assert.deepEqual(fs.readFileSync(path.join(j.target,'requests/a.json')),sentinel);
 assert.equal(fs.existsSync(path.join(j.stateTarget,'requests.completed.json')),false);
});

import {qualifyCompletedCustody} from '../scripts/delivery-handoff-advance.mjs';
function completedCustodyRecipe() {
 const original=JSON.parse(fs.readFileSync(new URL('./fixtures/native102-original-custody.json',import.meta.url)));
 const loc=name=>({commit:original.publication_commit,path:original.prefix+original[name]});
 return {version:1,id:'retained-original',mode:'completed-original-custody',new_prefix:'coordination/engineering/original-custody-fixture/',
  selector:{commit:original.context_commit,path:'data/ownership-selection.json'},
  package_inputs:{commit:original.context_commit,path:'.github/package-inputs.json'},retained_registries:[],
  groups:[{id:'original',component_ids:[original.component_id],target_ids:[original.target_id],
   source_publication:loc('source_publication'),native_publication:loc('native_publication'),native_operating:loc('native_operating')}]};
}
for(const [label,change] of Object.entries({
 'foreign route':r=>{r.mode='retained-groups';},
 'nonliteral recipe identity':r=>{r.id=['retained-original'];},
 'unbounded groups':r=>{r.groups=Array(33).fill(r.groups[0]);},
 'invented issuing resources':r=>{r.operating_profile='source-native-v2';},
 'foreign selection context':r=>{r.selector.path='other.json';},
 'unsafe destination':r=>{r.new_prefix='../foreign/';},
}))test('completed custody refuses '+label+' before reading historical evidence',()=>{
 const recipe=completedCustodyRecipe();change(recipe);
 assert.throws(()=>qualifyCompletedCustody(recipe,{pin(){throw Error('unexpected historical read');}},{}),
  /Explicit bounded|selection\/package\/retained context/);
});

// Explicit offline suite, never a skipped default gate or an implicit download.
// Exact original bodies are supplied by the retained fixture, not recreated
// singleton SOURCE data, v2 templates or an invented operating terminal.
if(process.env.WORLDATLAS_DELIVERY_ORIGINAL_FIXTURE==='1') {
 test('real Native102 completed custody preserves whole original scope and reaches only genuine later barriers',async t=>{
  const prep=await import('../scripts/prepare-delivery-handoff.mjs'),flow=await import('../scripts/delivery-handoff-advance.mjs');
  const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
  const original=JSON.parse(fs.readFileSync(new URL('./fixtures/native102-original-custody.json',import.meta.url)));
  const allowance={phaseBytes:268435456,rssBytes:536870912};
  const make=()=>{const r=prep.pinReader(root,{allowance});return {r,adapters:{authorityReader:()=>flow.deliveryAuthorityReader(root,r)}};};
  const recipe=completedCustodyRecipe(),{r,adapters}=make(),qualified=qualifyCompletedCustody(recipe,r,adapters);
  assert.deepEqual(qualified.component_ids,[original.component_id]);
  const group=qualified.groups[0],preimage=JSON.parse(group.qualified_products['original-rule-preimage.json']);
  assert.equal(preimage.source_rule.cohort_ids.length,original.source_cohort_count);
  assert.deepEqual(preimage.source_rule.expected_ids,[original.component_id]);
  assert.equal(preimage.source_rule.geometry_scope,'supported-fragment');assert.equal(preimage.source_rule.registry_path,undefined);
  assert.notEqual(preimage.source_rule.cases_path,preimage.source_rule.outcomes_path);
  assert.equal(digest(group.qualified_products['original-rule-preimage.json']),original.rule_sha256);
  const binding=JSON.parse(group.qualified_products['authority-binding.json']),ledger=r.json(binding.original_pins.ledger);
  assert.equal(binding.original_pins.ledger.sha256,original.ledger_sha256);
  assert.equal(ledger.assigned_cells,original.assigned_cells);assert.equal(ledger.rows[0].whole_gap_completion,false);
  assert.equal(ledger.rows[0].original_remainder?.is_empty??ledger.rows[0].remainder?.is_empty,false);
  for(const [label,change,pattern] of [
   ['foreign component',q=>q.groups[0].component_ids=['foreign-component'],/component\/target scope/],
   ['foreign target',q=>q.groups[0].target_ids=['foreign-target'],/component\/target scope/],
   ['extra authority',q=>q.groups.push({...q.groups[0],id:'duplicate'}),/Overlapping/],
   ['missing terminal',q=>q.groups[0].native_operating={...q.groups[0].native_operating,path:original.prefix+'missing-terminal.json'},/whole ordinary Git input/],
   ['changed terminal',q=>q.groups[0].native_operating=q.groups[0].native_publication,/Unqualified original native operating|operating/],
  ]) await t.test(label,()=>{const f=make(),q=structuredClone(recipe);change(q);assert.throws(()=>qualifyCompletedCustody(q,f.r,f.adapters),pattern);});
  await t.test('coherently changed committed original terminal refuses',()=>{
   const temporary=fs.mkdtempSync(path.join(os.tmpdir(),'changed-original-terminal-'));
   t.after(()=>fs.rmSync(temporary,{recursive:true,force:true}));
   const git=(args,input)=>execFileSync('git',['-c','core.hooksPath=/dev/null','-C',temporary,...args],{input,encoding:'utf8'}).trim();
   git(['init','-q']);fs.mkdirSync(path.join(temporary,'.git/objects/info'),{recursive:true});
   const objects=execFileSync('git',['-C',root,'rev-parse','--path-format=absolute','--git-path','objects'],{encoding:'utf8'}).trim();
   fs.writeFileSync(path.join(temporary,'.git/objects/info/alternates'),objects+'\n');
   git(['update-ref','refs/heads/main',original.context_commit]);git(['symbolic-ref','HEAD','refs/heads/main']);
   const operating=r.json(r.pin(recipe.groups[0].native_operating.commit,recipe.groups[0].native_operating.path));
   operating.qualified=false;
   const oid=git(['hash-object','-w','--stdin'],prep.jsonBytes(operating));
   const tree=git(['mktree'],'100644 blob '+oid+'\tchanged-operating.json\n');
   const changed=git(['-c','user.name=Fixture','-c','user.email=fixture@example.test','commit-tree',tree], 'Synthetic changed terminal control\n');
   const local=prep.pinReader(temporary,{allowance}),q=structuredClone(recipe);
   q.groups[0].native_operating={commit:changed,path:'changed-operating.json'};
   assert.throws(()=>qualifyCompletedCustody(q,local,{authorityReader:()=>flow.deliveryAuthorityReader(temporary,local)}),/Unqualified original native operating/);
  });
  const raw=prep.jsonBytes(recipe),pin={commit:original.publication_commit,path:'fixture-recipe.json',mode:'100644',git_blob_oid:'a'.repeat(40),bytes:raw.length,sha256:digest(raw)};
  const reader={...r,pin:(c,p)=>p===pin.path&&c===pin.commit?pin:r.pin(c,p),read:p=>p.path===pin.path?raw:r.read(p),json:p=>p.path===pin.path?recipe:r.json(p)};
  const j=journal(t);j.reader=reader;
  const config={version:1,recipe:{commit:pin.commit,path:pin.path}};
  const noIssuance={...adapters,prepareRequests:()=>{throw Error('SOURCE issuance must not run');},nativeRequests:()=>{throw Error('NATIVE issuance must not run');}};
  let next=await flow.nextDeliveryStage(j,config,reader,noIssuance);
  assert.equal(next.id,'authority-original');assert.equal(next.phase,'authority');
  await assert.rejects(prepareAdvanceStage(j,next.id,next.phase,next.input,next.produce,{interrupt:()=>{throw Error('interrupted original authority');}}),/interrupted original authority/);
  assert.deepEqual(readAdvanceStatus(j).completed,[]);
  const changed=structuredClone(config);changed.observations={sources:[]};
  await assert.rejects(flow.nextDeliveryStage(j,changed,reader,noIssuance),/substitute execution observations/);
  next=await flow.nextDeliveryStage(j,config,reader,noIssuance);
  await prepareAdvanceStage(j,next.id,next.phase,next.input,next.produce);
  const receipt=fs.readFileSync(path.join(j.stateTarget,'authority-original.completed.json'));
  next=await flow.nextDeliveryStage(j,config,reader,noIssuance);
  assert.equal(next.waiting.kind,'commit');assert.equal(next.waiting.stage,'registry');
  assert.deepEqual(readAdvanceStatus(j).completed,['authority-original']);
  assert.deepEqual(fs.readFileSync(path.join(j.stateTarget,'authority-original.completed.json')),receipt);
  assert.equal(fs.existsSync(path.join(j.target,'recipe')),false);assert.equal(fs.existsSync(path.join(j.target,'requests')),false);
  assert.equal(fs.existsSync(path.join(j.target,'native-requests')),false);
  await t.test('actual automatic Git continuation commits original custody once and stops at current rebind',async()=>{
   const f=automaticGitFixture(t),localRoot=f.j.root;
   fs.mkdirSync(path.join(localRoot,'.git/objects/info'),{recursive:true});
   fs.writeFileSync(path.join(localRoot,'.git/objects/info/alternates'),execFileSync('git',
    ['-C',root,'rev-parse','--path-format=absolute','--git-path','objects'],{encoding:'utf8'}));
   fs.writeFileSync(path.join(localRoot,'original-recipe.json'),prep.jsonBytes(recipe));
   f.git('add','original-recipe.json');f.git('commit','-qm','original custody recipe');
   const head=f.git('rev-parse','HEAD'),local=prep.pinReader(localRoot,{allowance});
   const config={version:1,recipe:{commit:head,path:'original-recipe.json'}};
   const j=openAdvanceJournal(localRoot,'coordination/engineering/automatic-native102/advance',config.recipe,{budget:local.budget});
   const adapters={authorityReader:()=>flow.deliveryAuthorityReader(localRoot,local),composeAuthorities:prep.composeAuthorities,
    prepareRequests:()=>{throw Error('SOURCE issuance must not run');},nativeRequests:()=>{throw Error('NATIVE issuance must not run');}};
   const validate=async({branch,paths})=>{assert.equal(branch,'engineering/automatic-control');assert.ok(paths.every(p=>p.startsWith(j.destination+'/')));};
   await assert.rejects(flow.runAutomaticDelivery(j,config,local,adapters,{validate,
    commitStage:(journal,id,options)=>flow.commitAdvanceStage(journal,id,{...options,interrupt:point=>{if(point==='ref')throw Error('interrupted authority ref');}})}),/interrupted authority ref/);
   const intended=JSON.parse(fs.readFileSync(path.join(j.stateTarget,'commit-authority-original.json')));
   assert.equal(f.git('rev-parse','HEAD'),intended.head);
   const result=await flow.runAutomaticDelivery(j,config,local,adapters,{validate});
   assert.equal(result.kind,'rebind-terminal');
   assert.deepEqual(readAdvanceStatus(j).completed,['authority-original','compose','registry']);
   assert.equal(f.git('rev-list','--count',head+'..HEAD'),'3');
   const final=f.git('rev-parse','HEAD'),observed=flow.automaticDeliveryObservations(j,config).observations;
   assert.equal(observed.authorities.length,1);assert.ok(observed.registry&&observed.composition);assert.equal(observed.rebind,undefined);
   const repeated=await flow.runAutomaticDelivery(j,config,local,adapters,{validate});
   assert.equal(repeated.kind,'rebind-terminal');assert.equal(f.git('rev-parse','HEAD'),final);
   assert.equal(fs.existsSync(path.join(j.target,'recipe')),false);assert.equal(fs.existsSync(path.join(j.target,'requests')),false);
   assert.equal(fs.existsSync(path.join(j.target,'native-requests')),false);
  });
  await t.test('actual advance CLI prepares original authority once and resumes at immutable commit barrier',()=>{
   const temporary=fs.mkdtempSync(path.join(os.tmpdir(),'original-custody-cli-'));
   t.after(()=>fs.rmSync(temporary,{recursive:true,force:true}));
   const git=(args,input)=>execFileSync('git',['-c','core.hooksPath=/dev/null','-C',temporary,...args],{input,encoding:'utf8'}).trim();
   git(['init','-q']);fs.mkdirSync(path.join(temporary,'.git/objects/info'),{recursive:true});
   fs.writeFileSync(path.join(temporary,'.git/objects/info/alternates'),execFileSync('git',['-C',root,'rev-parse','--path-format=absolute','--git-path','objects'],{encoding:'utf8'}));
   git(['read-tree',original.context_commit]);
   const blob=git(['hash-object','-w','--stdin'],prep.jsonBytes(recipe));
   git(['update-index','--add','--cacheinfo','100644,'+blob+',original-recipe.json']);
   const tree=git(['write-tree']),head=git(['-c','user.name=Fixture','-c','user.email=fixture@example.test','commit-tree',tree,'-p',original.context_commit],'Immutable original custody recipe fixture\n');
   git(['update-ref','refs/heads/main',head]);git(['symbolic-ref','HEAD','refs/heads/main']);
   fs.writeFileSync(path.join(temporary,'config.json'),prep.jsonBytes({version:1,recipe:{commit:head,path:'original-recipe.json'},preparation_allowance:allowance}));
   const env={...process.env,GIT_NO_LAZY_FETCH:'1'};delete env.NODE_PATH;
   const args=[path.join(root,'scripts/prepare-delivery-handoff.mjs'),'advance','config.json','.cache/delivery-handoff/original'];
   const first=JSON.parse(execFileSync(process.execPath,args,{cwd:temporary,env,encoding:'utf8'}));
   assert.equal(first.result.stage,'authority-original');
   const dir=path.join(temporary,'.cache/delivery-handoff/original'),before=fs.readFileSync(path.join(dir,'authority-original.completed.json'));
   const second=JSON.parse(execFileSync(process.execPath,[...args,'--resume'],{cwd:temporary,env,encoding:'utf8'}));
   assert.equal(second.waiting.kind,'commit');assert.equal(second.waiting.stage,'registry');
   assert.deepEqual(fs.readFileSync(path.join(dir,'authority-original.completed.json')),before);
   assert.deepEqual(fs.readdirSync(dir).filter(n=>n.endsWith('.completed.json')),['authority-original.completed.json']);
  });
 });
}


function sparseAutomaticGitFixture(t) {
  const base = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'delivery-promisor-')));
  t.after(() => fs.rmSync(base, {recursive: true, force: true}));
  const source = path.join(base, 'source'), root = path.join(base, 'work'); fs.mkdirSync(source);
  const run = (cwd, args, extra = {}) => execFileSync('git', args, {cwd, env: {...process.env, GIT_NO_LAZY_FETCH: '1'}, ...extra});
  const seed = (...args) => run(source, args).toString().trim();
  seed('init', '-q', '-b', 'engineering/automatic-control');
  seed('config', 'user.name', 'Fixture'); seed('config', 'user.email', 'fixture@example.invalid');
  seed('config', 'uploadpack.allowFilter', 'true');
  const inherited = ['unrelated/deep/body', 'coordination/engineering/automatic-control/retained/body'];
  for (const name of ['original', ...inherited]) {
    fs.mkdirSync(path.dirname(path.join(source, name)), {recursive: true}); fs.writeFileSync(path.join(source, name), 'retained ' + name + '\n');
  }
  seed('add', '.'); seed('commit', '-qm', 'original sparse parent');
  run(base, ['-c', 'protocol.file.allow=always', 'clone', '-q', '--filter=blob:none', '--no-checkout', 'file://' + source, root]);
  const git = (...args) => run(root, args).toString().trim();
  git('config', 'user.name', 'Fixture'); git('config', 'user.email', 'fixture@example.invalid'); git('config', 'gc.auto', '0');
  git('sparse-checkout', 'init', '--no-cone');
  git('sparse-checkout', 'set', '--no-cone', '/original', '/coordination/engineering/automatic-control/advance/');
  run(root, ['-c', 'protocol.file.allow=always', 'checkout', '-q'], {env: {...process.env, GIT_NO_LAZY_FETCH: '0'}});
  git('remote', 'set-url', 'origin', path.join(base, 'unavailable-origin'));
  const absent = inherited.map(name => ({name, oid: git('rev-parse', 'HEAD:' + name)}));
  const missing = oid => assert.throws(() => run(root, ['cat-file', '-e', oid], {stdio: 'pipe'}));
  absent.forEach(({oid}) => missing(oid));
  let charged = 0;
  const budget = {add({bytes}) {charged += bytes; assert.ok(charged < 2 * 1024 * 1024);}};
  const j = openAdvanceJournal(root, 'coordination/engineering/automatic-control/advance', {commit: git('rev-parse', 'HEAD'), path: 'recipe.json'}, {budget});
  const validate = async ({branch, paths}) => {assert.equal(branch, 'engineering/automatic-control'); assert.ok(paths.every(p => p.startsWith(j.destination + '/')));};
  return {j, git, run, root, absent, missing, validate};
}
for (const stop of [null, 'intent', 'object', 'ref']) test('automatic commit preserves absent inherited promisor bodies through ' + (stop ?? 'completion'), async t => {
  const f = sparseAutomaticGitFixture(t), parent = f.git('rev-parse', 'HEAD');
  const oldTree = f.git('ls-tree', '-r', parent);
  await prepareAdvanceStage(f.j, 'recipe', 'recipe', {}, () => ({'recipe-index.json': Buffer.from('{"groups":[]}\n')}));
  if (stop) {
    await assert.rejects(commitAdvanceStage(f.j, 'recipe', {validate: f.validate, interrupt: point => {if (point === stop) throw Error('interrupted');}}), /interrupted/);
    const intent = JSON.parse(fs.readFileSync(path.join(f.j.stateTarget, 'commit-recipe.json')));
    // The newly hash-object-written fixture product is loose; remove just that
    // known fixture object to exercise authenticated recovery, never parent data.
    const oid = intent.files[0].oid, objects = f.git('rev-parse', '--git-path', 'objects');
    const loose = path.resolve(f.root, objects, oid.slice(0, 2), oid.slice(2));
    assert.ok(fs.lstatSync(loose).isFile()); fs.unlinkSync(loose); f.missing(oid);
  }
  const result = await commitAdvanceStage(f.j, 'recipe', {validate: f.validate});
  const intent = JSON.parse(fs.readFileSync(path.join(f.j.stateTarget, 'commit-recipe.json')));
  assert.equal(result.head, intent.head); assert.equal(f.git('rev-parse', 'HEAD^'), parent);
  assert.equal(f.git('rev-list', '--count', 'HEAD'), '2');
  const added = new Set(intent.files.map(file => file.path));
  const inherited = f.git('ls-tree', '-r', 'HEAD').split('\n').filter(row => !added.has(row.split('\t')[1])).join('\n');
  assert.equal(inherited, oldTree);
  for (const file of intent.files) {
    assert.equal(f.git('cat-file', '-t', file.oid), 'blob');
    assert.deepEqual(f.run(f.root, ['cat-file', 'blob', file.oid]), fs.readFileSync(path.join(f.root, file.path)));
  }
  f.absent.forEach(({name, oid}) => {f.missing(oid); assert.equal(fs.existsSync(path.join(f.root, name)), false);});
  assert.equal((await commitAdvanceStage(f.j, 'recipe', {validate: f.validate})).resumed, true);
  assert.equal(f.git('rev-list', '--count', 'HEAD'), '2');
});
test('automatic sparse commit rejects unstored new products despite missing-ok inherited entries', async t => {
  const f = sparseAutomaticGitFixture(t), before = f.git('rev-parse', 'HEAD');
  await prepareAdvanceStage(f.j, 'recipe', 'recipe', {}, () => ({'recipe-index.json': Buffer.from('{}\n')}));
  const execute = (command, args, options) => {
    if (command === 'git' && args[0] === 'hash-object' && args.includes('-w'))
      return execFileSync(command, args.filter(arg => arg !== '-w'), options);
    return execFileSync(command, args, options);
  };
  await assert.rejects(commitAdvanceStage(f.j, 'recipe', {validate: f.validate, execute}), /cat-file|could not|Not a valid/);
  assert.equal(f.git('rev-parse', 'HEAD'), before);
  assert.equal(fs.existsSync(path.join(f.j.stateTarget, 'commit-recipe.json')), false);
});


test('original strict scratch writer reproduces the missing inherited object failure', async t => {
  const f = sparseAutomaticGitFixture(t), before = f.git('rev-parse', 'HEAD');
  await prepareAdvanceStage(f.j, 'recipe', 'recipe', {}, () => ({'recipe-index.json': Buffer.from('{}\n')}));
  const execute = (command, args, options) => execFileSync(command,
    args[0] === 'write-tree' && options.env.GIT_INDEX_FILE ? args.filter(arg => arg !== '--missing-ok') : args, options);
  await assert.rejects(commitAdvanceStage(f.j, 'recipe', {validate: f.validate, execute}), /write-tree|missing|invalid|could not/);
  assert.equal(f.git('rev-parse', 'HEAD'), before);
  f.absent.forEach(({oid}) => f.missing(oid));
});
test('sparse automatic recovery rejects changed or deleted inherited entries in any subtree', async t => {
  for (const change of ['modify', 'delete']) for (const target of ['unrelated/deep/body', 'coordination/engineering/automatic-control/retained/body']) await t.test(change + ':' + target, async t => {
    const f = sparseAutomaticGitFixture(t), before = f.git('rev-parse', 'HEAD');
    await prepareAdvanceStage(f.j, 'recipe', 'recipe', {}, () => ({'recipe-index.json': Buffer.from('{}\n')}));
    await assert.rejects(commitAdvanceStage(f.j, 'recipe', {validate: f.validate, interrupt: point => {if (point === 'intent') throw Error('stop');}}), /stop/);
    const file = path.join(f.j.stateTarget, 'commit-recipe.json'), intent = JSON.parse(fs.readFileSync(file));
    const env = {...process.env, GIT_NO_LAZY_FETCH: '1', GIT_INDEX_FILE: path.join(f.root, 'adversarial-index')};
    f.run(f.root, ['read-tree', intent.tree], {env});
    f.run(f.root, ['update-index', '--index-info'], {env, input: change === 'modify' ? `100644 ${intent.files[0].oid}\t${target}\n` : `0 ${'0'.repeat(40)}\t${target}\n`});
    intent.tree = f.run(f.root, ['write-tree', '--missing-ok'], {env}).toString().trim();
    intent.raw = intent.raw.replace(/^tree [a-f0-9]+/, 'tree ' + intent.tree);
    intent.head = createHash('sha1').update(`commit ${Buffer.byteLength(intent.raw)}\0`).update(intent.raw).digest('hex');
    fs.writeFileSync(file, JSON.stringify(intent));
    await assert.rejects(commitAdvanceStage(f.j, 'recipe', {validate: f.validate}), /undeclared paths/);
    assert.equal(f.git('rev-parse', 'HEAD'), before); f.absent.forEach(({oid}) => f.missing(oid));
  });
});

async function legacyRuntimeFixture(t, {published = false} = {}) {
  const f = automaticGitFixture(t), root = f.j.root;
  fs.writeFileSync(path.join(root, '.gitignore'), '/.cache/\n'); f.git('add', '.gitignore'); f.git('commit', '-qm', 'ignore runtime cache');
  await prepareAdvanceStage(f.j, 'recipe', 'recipe', {}, () => ({'recipe-index.json': Buffer.from('{"groups":[]}\n')}));
  await withAdvanceLock(f.j, () => commitAdvanceStage(f.j, 'recipe', {validate: f.validate}));
  const packet = {repo: 'ChengshuLi/WorldAtlas', pr_number: 1, head_sha: f.git('rev-parse', 'HEAD')};
  await assert.rejects(advanceQueue(f.j, packet, {authorizeSubmission: true, checkReview: async () => packet,
    submit: async () => {throw Error('uncertain original submission');}}), /uncertain original/);
  observeAdvance(f.j, {status: 'waiting', stage: 'current-rebind', kind: 'rebind-terminal', detail: 'Genuine external terminal required'});
  // Reproduce the accepted legacy physical layout using unchanged v1 bytes.
  const saved = new Map(fs.readdirSync(f.j.stateTarget).map(name => [name, fs.readFileSync(path.join(f.j.stateTarget, name))]));
  for (const [name] of saved) fs.renameSync(path.join(f.j.stateTarget, name), path.join(f.j.target, name));
  fs.rmdirSync(f.j.stateTarget);
  if (published) {f.git('add', f.j.destination); f.git('commit', '-qm', 'published legacy journal');}
  const reopen = () => openAdvanceJournal(root, f.j.destination, f.j.intent.recipe, {resume: true, budget: {add() {}}});
  return {...f, root, saved, packet, reopen, j: reopen(), head: f.git('rev-parse', 'HEAD'), published};
}
for (const published of [false, true]) test('runtime separation preserves original ' + (published ? 'published' : 'untracked') + ' journal bytes and operation identities', async t => {
  const f = await legacyRuntimeFixture(t, {published});
  if (!published) assert.match(f.git('status', '--porcelain'), /\?\?/);
  await withAdvanceLock(f.j, () => readAdvanceStatus(f.j));
  assert.notEqual(f.j.stateTarget, f.j.target);
  for (const [name, raw] of f.saved) {
    assert.deepEqual(fs.readFileSync(path.join(f.j.stateTarget, name)), raw);
    if (published) assert.deepEqual(fs.readFileSync(path.join(f.j.target, name)), raw);
    else assert.equal(fs.existsSync(path.join(f.j.target, name)), false);
  }
  assert.equal(f.git('status', '--porcelain'), ''); assert.equal(f.git('rev-parse', 'HEAD'), f.head);
  const j = f.reopen(), result = await withAdvanceLock(j, () => commitAdvanceStage(j, 'recipe', {validate: f.validate}));
  assert.equal(result.resumed, true); assert.equal(f.git('rev-parse', 'HEAD'), f.head);
  let observed = 0;
  await withAdvanceLock(j, () => advanceQueue(j, f.packet, {authorizeSubmission: true,
    submit: async () => {throw Error('No redispatch');}, api: async route => {
      assert.equal(route, '/repos/ChengshuLi/WorldAtlas/pulls/1'); observed++;
      return {merged: false, head: {sha: f.packet.head_sha}};
    }}));
  assert.equal(observed, 1); assert.equal(f.git('status', '--porcelain'), '');
});
for (const point of ['migration-intent', 'copied:advance.json', 'retired:advance.json', 'migration-complete'])
  test('legacy runtime relocation resumes unchanged after ' + point, async t => {
    const f = await legacyRuntimeFixture(t);
    await assert.rejects(withAdvanceLock(f.j, () => {throw Error('action must wait');}, {interrupt: where => {if (where === point) throw Error('interrupted relocation');}}), /interrupted relocation/);
    const j = f.reopen(); let actions = 0;
    await withAdvanceLock(j, () => {actions++; readAdvanceStatus(j);});
    assert.equal(actions, 1); assert.equal(f.git('rev-parse', 'HEAD'), f.head); assert.equal(f.git('status', '--porcelain'), '');
    for (const [name, raw] of f.saved) assert.deepEqual(fs.readFileSync(path.join(j.stateTarget, name)), raw);
  });
test('runtime relocation refuses changed, unknown, tracked-drift and symlink inputs without losing originals', async t => {
  for (const kind of ['changed-copy', 'unknown', 'tracked-drift', 'symlink']) await t.test(kind, async t => {
    const f = await legacyRuntimeFixture(t, {published: kind === 'tracked-drift'});
    const original = path.join(f.j.target, 'advance.json'), before = fs.readFileSync(original);
    if (kind === 'changed-copy') {
      await assert.rejects(withAdvanceLock(f.j, () => {}, {interrupt: point => {if (point === 'copied:advance.json') throw Error('stop');}}), /stop/);
      fs.writeFileSync(path.join(f.j.runtimeTarget, 'advance.json'), '{}');
    } else if (kind === 'unknown') fs.writeFileSync(path.join(f.j.target, 'foreign-record.json'), 'sentinel');
    else if (kind === 'tracked-drift') fs.writeFileSync(original, JSON.stringify({...f.j.intent, started_at: '2000-01-01T00:00:00Z'}));
    else {fs.mkdirSync(f.j.runtimeTarget, {recursive: true}); fs.symlinkSync(original, path.join(f.j.runtimeTarget, 'foreign-link'));}
    await assert.rejects(withAdvanceLock(f.j, () => {throw Error('must not advance');}), /changed|Foreign|Occupied|published|Nonordinary/i);
    if (kind !== 'tracked-drift') assert.deepEqual(fs.readFileSync(original), before);
    assert.equal(f.git('rev-parse', 'HEAD'), f.head);
  });
});
test('runtime cache ownership is destination-wide and blocks conflicting recipes and live owners', async t => {
  const f = await legacyRuntimeFixture(t);
  await withAdvanceLock(f.j, async () => {
    const same = f.reopen();
    await assert.rejects(async () => withAdvanceLock(same, () => {}), /Another advance process/);
    assert.throws(() => openAdvanceJournal(f.root, f.j.destination, {...f.j.intent.recipe, commit: 'f'.repeat(40)}, {resume: true}), /Foreign or changed/);
  });
  assert.equal(f.git('status', '--porcelain'), '');
});
test('fresh automatic products pass the unchanged stock current-rebind cleanliness boundary with runtime state retained', async t => {
  const f = automaticGitFixture(t), root = f.j.root;
  fs.writeFileSync(path.join(root, '.gitignore'), '/.cache/\n'); f.git('add', '.gitignore'); f.git('commit', '-qm', 'ignore runtime cache');
  await withAdvanceLock(f.j, async () => {
    await prepareAdvanceStage(f.j, 'compose', 'compose', {}, () => ({'authority-registry.json': Buffer.from('{}\n')}));
    await commitAdvanceStage(f.j, 'compose', {validate: f.validate});
    observeAdvance(f.j, {status: 'waiting', stage: 'current-rebind', kind: 'rebind-terminal', detail: 'Actual terminal required'});
  });
  assert.equal(f.git('status', '--porcelain'), ''); assert.ok(fs.readdirSync(f.j.stateTarget).length > 3);
  assert.match(stockCleanlinessBoundary(root), /stock cleanliness passed/);
  fs.writeFileSync(path.join(f.j.target, 'foreign.json'), 'not runtime state');
  assert.throws(() => stockCleanlinessBoundary(root), /Require frozen clean executing checkout/);
});

function stockCleanlinessBoundary(root) {
  const contract = fileURLToPath(new URL('../coordination/engineering/additive-native-composition-20261009/execution-contract.py', import.meta.url));
  const script = `import importlib.util,json,pathlib,subprocess,sys\np=pathlib.Path(sys.argv[1]);spec=importlib.util.spec_from_file_location('stock',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)\nroot=pathlib.Path(sys.argv[2]);git=sys.argv[3];head=subprocess.check_output([git,'-C',str(root),'rev-parse','HEAD'],text=True).strip()\npre={'code':[{'path':p} for p in json.loads((p.parent/'execution-code-paths.json').read_bytes())],'runtime':[{'role':'git','path':git}]}\ntry:m.capture(root,head,pre)\nexcept KeyError as e:\n assert e.args==('entry',),repr(e)\n print('stock cleanliness passed; absent scientific entry still refuses')\nelse:raise AssertionError('must not grant scientific execution')\n`;
  const git = execFileSync('which', ['git'], {encoding: 'utf8'}).trim();
  return execFileSync(process.env.WORLDATLAS_TEST_PYTHON || process.env.PYTHON || 'python3', ['-c', script, contract, root, git], {encoding: 'utf8'});
}

for (const published of [false, true]) test('first migrated action crosses stock cleanliness with ' + (published ? 'published' : 'untracked') + ' originals retained correctly', async t => {
  const f = await legacyRuntimeFixture(t, {published});
  await withAdvanceLock(f.j, () => {
    assert.equal(fs.existsSync(path.join(f.j.target, 'advance.lock')), false);
    assert.equal(fs.existsSync(path.join(f.j.stateTarget, 'advance.lock')), true);
    assert.match(stockCleanlinessBoundary(f.root), /stock cleanliness passed/);
  });
});
