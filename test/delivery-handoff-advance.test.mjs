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
test('interrupted metadata resumes identical postimages and only completes once', async t => {
  const j = journal(t), products = {'a.json': Buffer.from('{}\n'), 'b.json': Buffer.from('[]\n')};
  let stopped = false;
  await assert.rejects(withAdvanceLock(j, () => prepareAdvanceStage(j, 'requests', 'requests', {one: 1}, () => products,
    {interrupt: name => { if (name === 'a.json' && !stopped) { stopped = true; throw Error('interrupted'); } }})), /interrupted/);
  assert.deepEqual(readAdvanceStatus(j).completed, []);
  assert.equal(fs.existsSync(path.join(j.target, 'requests', 'preparation.json')), false);
  await withAdvanceLock(j, () => prepareAdvanceStage(j, 'requests', 'requests', {one: 1}, () => products));
  const before = fs.readFileSync(path.join(j.target, 'requests.completed.json'));
  const repeated = await withAdvanceLock(j, () => prepareAdvanceStage(j, 'requests', 'requests', {one: 1}, () => { throw Error('completed stage reran'); }));
  assert.equal(repeated.resumed, true);
  assert.deepEqual(fs.readFileSync(path.join(j.target, 'requests.completed.json')), before);
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
test('queue identity is durable before uncertain submit and resume can never dispatch twice', async t => {
  const j = journal(t), packet = {repo: 'ChengshuLi/WorldAtlas', pr_number: 1, head_sha: commit};
  let calls = 0, identity;
  const checkReview = async () => ({...packet, review_comment_id: 123});
  const client = async options => {
    const saved = JSON.parse(fs.readFileSync(path.join(j.target, 'queue-submission.json')));
    assert.equal(saved.request_id, options.requestId); identity ??= options.requestId; assert.equal(identity, options.requestId);
    if (!options.observeOnly) { calls++; throw Error('uncertain POST'); }
    assert.equal(options.resuming, true); return {status: 'pending', request_id: identity};
  };
  assert.equal((await advanceQueue(j, packet, {checkReview})).status, 'ready-for-queue');
  assert.equal(fs.existsSync(path.join(j.target, 'queue-submission.json')), false);
  await assert.rejects(advanceQueue(j, packet, {authorizeSubmission: true, checkReview, client}), /uncertain/);
  assert.equal((await advanceQueue(j, packet, {authorizeSubmission: true, checkReview, client})).status, 'pending');
  assert.equal(calls, 1);
  await assert.rejects(advanceQueue(j, {...packet, head_sha: later}, {checkReview, client}), /another target/);
});
test('missing independent acceptance never writes a queue identity', async t => {
  const j = journal(t);
  await assert.rejects(advanceQueue(j, {repo: 'ChengshuLi/WorldAtlas', pr_number: 1, head_sha: commit},
    {authorizeSubmission: true, checkReview: async () => { throw Error('stale review'); }}), /stale review/);
  assert.equal(fs.existsSync(path.join(j.target, 'queue-submission.json')), false);
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
const fixtureTest = (name, fn) => test(name, {skip: !realFixture}, fn);
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
  assert.equal(fs.existsSync(path.join(j.target, 'requests.intent.json')), false);
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
test('real13 greedy model ignores original batch labels and deduplicates physical/admin/native transport',
  {skip: process.env.WORLDATLAS_DELIVERY_FIXTURE !== '1'}, async t => {
    const scratch = fs.mkdtempSync(path.join(os.tmpdir(), 'delivery-greedy-'));
    t.after(() => fs.rmSync(scratch, {recursive: true, force: true}));
    const {result} = await current13GreedyProbe({root: path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..'), scratch});
    assert.equal(result.component_count, 13);
    assert.deepEqual(result.groups.map(g => g.components), [10, 3]);
    assert.ok(result.groups.every(g => g.source_phase_bytes <= g.phase_limit && g.native_phase_bytes <= g.phase_limit));
    assert.deepEqual(result.transport.map(r => r.unique_bodies), [14, 3, 7]);
  });

test('stale lock recovery serializes competing acquisition and refuses ambiguous acquisition guards', async t => {
  const j = journal(t), lockPath = path.join(j.target, 'advance.lock');
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
  fs.writeFileSync(path.join(j.target, 'advance.acquire'), raw);
  assert.throws(() => withAdvanceLock(j, () => { ran = true; }), /inspect its owner/);
  assert.equal(ran, false); assert.deepEqual(fs.readFileSync(path.join(j.target, 'advance.acquire')), raw);
});
