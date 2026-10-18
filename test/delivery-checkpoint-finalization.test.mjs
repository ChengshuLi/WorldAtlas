import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {execFileSync, spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {crc32, gzipSync, deflateRawSync} from 'node:zlib';
import {CHECKPOINT_MEMBERS, reportHash} from '../scripts/geographic-report-artifact.mjs';
import {renderWorkerResult} from '../scripts/worker-result.mjs';
import {releaseAcceptedCheckpoint} from '../scripts/accepted-selected-checkpoint.mjs';
import {pinReader, publish, publishFinalizedDelivery, finalizeDelivery, digest, jsonBytes} from '../scripts/prepare-delivery-handoff.mjs';
import {acquireFinalizationCheckpoint, finalizationCheckpointBytes, admitCanonicalCheckpoint} from '../scripts/delivery-checkpoint-finalization.mjs';

// Same real ZIP/accepted-receipt fixture protocol as accepted-selected-checkpoint.
// Both the production archive parser and private acquisition are exercised.
function zipMembers(members, {descriptor = false, method = 8} = {}) {
  const locals = [], centrals = []; let offset = 0;
  for (const [name, body] of members) {
    const filename = Buffer.from(name), packed = method === 8 ? deflateRawSync(body) : body;
    const crc = crc32(body), local = Buffer.alloc(30), central = Buffer.alloc(46);
    local.writeUInt32LE(0x04034b50); local.writeUInt16LE(20, 4); local.writeUInt16LE(descriptor ? 8 : 0, 6);
    local.writeUInt16LE(method, 8); local.writeUInt16LE(filename.length, 26);
    if (!descriptor) { local.writeUInt32LE(crc, 14); local.writeUInt32LE(packed.length, 18); local.writeUInt32LE(body.length, 22); }
    const data = descriptor ? Buffer.alloc(16) : Buffer.alloc(0);
    if (descriptor) { data.writeUInt32LE(0x08074b50); data.writeUInt32LE(crc, 4); data.writeUInt32LE(packed.length, 8); data.writeUInt32LE(body.length, 12); }
    central.writeUInt32LE(0x02014b50); central.writeUInt16LE(0x0314, 4); central.writeUInt16LE(20, 6);
    central.writeUInt16LE(descriptor ? 8 : 0, 8); central.writeUInt16LE(method, 10);
    central.writeUInt32LE(crc, 16); central.writeUInt32LE(packed.length, 20); central.writeUInt32LE(body.length, 24);
    central.writeUInt16LE(filename.length, 28); central.writeUInt32LE(offset, 42);
    locals.push(local, filename, packed, data); centrals.push(central, filename);
    offset += local.length + filename.length + packed.length + data.length;
  }
  const central = Buffer.concat(centrals), end = Buffer.alloc(22);
  end.writeUInt32LE(0x06054b50); end.writeUInt16LE(members.length, 8); end.writeUInt16LE(members.length, 10);
  end.writeUInt32LE(central.length, 12); end.writeUInt32LE(offset, 16);
  return Buffer.concat([...locals, central, end]);
}
const head = 'a'.repeat(40), baseline = 'b'.repeat(40), candidate = 'c'.repeat(40), merged = 'd'.repeat(40), tree = 'e'.repeat(40), workflowHead = 'f'.repeat(40);
const request = '01234567-abcd-4321-aaaa-123456789012';
const json = value => Buffer.from(JSON.stringify(value) + '\n');
const archivedPolygonMembers = ['facts.json', 'operands.json.gz', 'publication.json'];
function checkpoint({historical = false} = {}) {
  const bodies = [...CHECKPOINT_MEMBERS, ...(historical ? archivedPolygonMembers : [])].map(name => [name, name.endsWith('.gz') ? gzipSync(json({member: name})) : json({member: name})]);
  const report = {version: 1, method_id: 'worldatlas-trusted-geography-check-v1', baseline_commit: baseline,
    candidate_commit: candidate, trusted_code_commit: baseline, candidate_code_executed: false,
    published: false, source_approval: false, gate_status: 'passed', status: historical ? 'no-new-regression' : 'no-new-native-loss',
    ...(!historical ? {validation_scope: 'selected-native-map-cells', selected_native_report: {method: 'selected-native-owner-conservation-v1',
      status: 'no-new-native-loss', candidate_code_executed: false, lost_or_reassigned_cells: 0, intervals: []}} : {}),
    checkpoint: {version: 1, kind: 'selected-checkpoint-products-v1', members: bodies.map(([name, raw]) => ({name, bytes: raw.length,
      sha256: reportHash(raw), ...(name.endsWith('.gz') ? {decoded_bytes: json({member:name}).length, decoded_sha256: reportHash(json({member:name}))} : {})}))}};
  return {report, bodies};
}
const encode = f => ({raw: json(f.report), zip: zipMembers([['geography-check.json', json(f.report)], ...f.bodies])});

function acceptedFixture(options, alterReport = () => {}, selection = {version: 1, release: 'prior'}) {
  const f = checkpoint(options); alterReport(f.report);
  const facts = json({candidate_commit: candidate, candidate_selection: selection});
  f.bodies = f.bodies.map(([name, bytes]) => [name, name === 'derived-facts.json' ? facts : bytes]);
  const pin = f.report.checkpoint.members.find(pin => pin.name === 'derived-facts.json');
  pin.bytes = facts.length; pin.sha256 = reportHash(facts);
  const encoded = encode(f); Object.assign(f,encoded);
  f.source = {run_id:12,run_attempt:2,job_id:34,tree,head,baseline,candidate_commit:candidate,
    workflow_path:'.github/workflows/worker-merge.yml',event:'workflow_dispatch',workflow_head:workflowHead,
    artifact_id:56,artifact_name:`geography-${request}-2`,artifact_digest:reportHash(f.zip),artifact_bytes:f.zip.length,
    report_sha256:reportHash(f.raw),report_bytes:f.raw.length};
  f.receipt = {accepted:true,status:'merged',request_id:request,pr_number:7,merge_commit:merged,reviewed_head:head,
    tested_base:baseline,tested_candidate:candidate,geography:{status:'passed',trusted_code_commit:baseline,candidate_commit:candidate,
      report_sha256:f.source.report_sha256,source:f.source}};
  f.pr = {number:7,merged:true,head:{sha:head,repo:{full_name:'owner/repo'}},base:{ref:'main',repo:{full_name:'owner/repo'}},merge_commit_sha:merged};
  f.run = {id:12,run_attempt:2,head_sha:workflowHead,event:'workflow_dispatch',path:f.source.workflow_path,
    repository:{full_name:'owner/repo'},head_repository:{full_name:'owner/repo'},status:'completed'};
  f.job = {id:34,name:'geography',run_id:12,run_attempt:2,head_sha:workflowHead,status:'completed',conclusion:'success',steps:[
    'Checkout trusted geographic checker','Install trusted geographic dependencies','Check exact combined geography with trusted baseline code',
    'Run actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02'].map(name=>({name,status:'completed',conclusion:'success'}))};
  f.artifact = {id:56,name:f.source.artifact_name,expired:false,size_in_bytes:f.zip.length,digest:`sha256:${reportHash(f.zip)}`,
    workflow_run:{id:12,head_sha:workflowHead}};
  f.calls=[]; f.admitted=[]; f.bot='github-actions[bot]';
  const api=async route => {
    f.calls.push(route);
    if(route.endsWith('/comments?per_page=100&page=1')) return [{id:11,user:{login:f.bot},body:renderWorkerResult('merge',f.receipt)}];
    if(route.endsWith('/pulls/7')) return f.pr;
    if(route.endsWith('/attempts/2')) return f.run;
    if(route.endsWith('/attempts/2/jobs?per_page=100&page=1')) return {jobs:[f.job]};
    if(route.includes('/git/commits/')) return {sha:route.split('/').at(-1),tree:{sha:f.tree??tree}};
    throw Error('Unexpected fixture route '+route);
  };
  api.artifactRedirect=async route => {f.calls.push(route);assert.equal(route,`/repos/owner/repo/actions/artifacts/${f.artifact.id}/zip`);return new Response(null,{status:302,headers:{location:'https://fixtures.blob.core.windows.net/zip'}});};
  f.options={api,repo:'owner/repo',locator:{pr_number:7,request_id:request,head},token:'fixture',admit:bytes=>f.admitted.push(bytes),
    fetchImpl:async()=>new Response(f.zip)};
  return f;
}

function repository(t, {selection = {version: 1, release: 'prior'}, old = true} = {}) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'checkpoint-finalize-'));
  t.after(() => fs.rmSync(root, {recursive: true, force: true}));
  const git = (...args) => execFileSync('git', args, {cwd: root, encoding: 'utf8',
    env: {...process.env, GIT_CONFIG_GLOBAL: '/dev/null', GIT_CONFIG_NOSYSTEM: '1'}}).trim();
  git('init', '-q'); git('config', 'user.name', 'Fixture'); git('config', 'user.email', 'fixture@example.invalid');
  const write = (name, bytes) => { fs.mkdirSync(path.dirname(path.join(root, name)), {recursive: true}); fs.writeFileSync(path.join(root, name), bytes); };
  const commit = () => {git('add', '.');git('commit', '-qm', 'Fixture');return git('rev-parse', 'HEAD');};
  write('data/ownership-selection.json', json(selection));
  if (old) write('data/selected-checkpoint.json', json({old: true}));
  const base = commit();
  const f = acceptedFixture(), directory = 'coordination/engineering/checkpoint-test/accepted';
  const locator = {version: 1, kind: 'accepted-selected-checkpoint-locator-v1', acceptance: f.options.locator,
    retained_artifact: {path: directory + '/geography-artifact.zip'}};
  write(directory + '/selected-checkpoint.json', json(locator)); write(locator.retained_artifact.path, f.zip);
  const acquired = commit(), reader = pinReader(root);
  return {root, reader, f, locator, write, commit, config: {selector: {commit: base, path: 'data/ownership-selection.json'},
    accepted_checkpoint: {commit: acquired, path: directory + '/selected-checkpoint.json'}}};
}

test('optional checkpoint leaves the legacy finalizer and canonical file untouched', async t => {
  const f = repository(t), config = {selector: f.config.selector};
  assert.equal(await acquireFinalizationCheckpoint(config, f.reader), undefined);
  assert.equal(finalizationCheckpointBytes(config, f.reader), undefined);
  const original = fs.readFileSync(path.join(f.root, 'data/selected-checkpoint.json'));
  admitCanonicalCheckpoint(f.root, f.reader, config.selector, undefined)();
  assert.deepEqual(fs.readFileSync(path.join(f.root, 'data/selected-checkpoint.json')), original);
});

test('authenticated chosen locator publishes and automatically adopts exact bytes; identical resume works', async t => {
  const f = repository(t), handle = await acquireFinalizationCheckpoint(f.config, f.reader, f.f.options);
  t.after(() => releaseAcceptedCheckpoint(handle));
  const bytes = finalizationCheckpointBytes(f.config, f.reader, handle), destination = 'coordination/engineering/checkpoint-test/final';
  const products = {'selected-checkpoint.json': bytes}, binding = {phase: 'finalize', config_sha256: 'a'.repeat(64)};
  publishFinalizedDelivery(f.root, destination, products, binding, f.reader, f.config.selector);
  assert.deepEqual(fs.readFileSync(path.join(f.root, 'data/selected-checkpoint.json')), bytes);
  publishFinalizedDelivery(f.root, destination, products, binding, f.reader, f.config.selector, true);
  const receipt = JSON.parse(fs.readFileSync(path.join(f.root, destination, 'preparation.json')));
  assert.equal(receipt.outputs['selected-checkpoint.json'].sha256, reportHash(bytes));
});

test('interruption after completed batch publication resumes canonical adoption', async t => {
  const f = repository(t, {old: false}), handle = await acquireFinalizationCheckpoint(f.config, f.reader, f.f.options);
  t.after(() => releaseAcceptedCheckpoint(handle));
  const bytes = finalizationCheckpointBytes(f.config, f.reader, handle), destination = 'coordination/engineering/checkpoint-test/final';
  publish(f.root, destination, {'selected-checkpoint.json': bytes}, {phase: 'finalize'});
  assert.equal(fs.existsSync(path.join(f.root, 'data/selected-checkpoint.json')), false);
  publishFinalizedDelivery(f.root, destination, {'selected-checkpoint.json': bytes}, {phase: 'finalize'}, f.reader, f.config.selector, true);
  assert.deepEqual(fs.readFileSync(path.join(f.root, 'data/selected-checkpoint.json')), bytes);
});

test('incompatible prior selector, unaccepted self candidate and fabricated custody refuse', async t => {
  const f = repository(t, {selection: {version: 1, release: 'next'}});
  await assert.rejects(acquireFinalizationCheckpoint(f.config, f.reader, f.f.options), /prior selected baseline/);
  f.f.receipt.accepted = false;
  await assert.rejects(acquireFinalizationCheckpoint(f.config, f.reader, f.f.options), /accepted merge receipt/);
  assert.throws(() => finalizationCheckpointBytes(f.config, f.reader, {}), /private/);
  assert.throws(() => finalizeDelivery(f.config, f.reader), /private/);
});

test('missing pinned locator or archive refuses without remote substitution', async t => {
  const f = repository(t);
  await assert.rejects(acquireFinalizationCheckpoint({...f.config, accepted_checkpoint: {...f.config.accepted_checkpoint, path: 'absent.json'}}, f.reader, f.f.options));
  f.write('coordination/engineering/checkpoint-test/accepted/selected-checkpoint.json', json({...f.locator,
    retained_artifact: {path: 'coordination/engineering/checkpoint-test/missing/geography-artifact.zip'}}));
  const changed = {...f.config, accepted_checkpoint: {...f.config.accepted_checkpoint, commit: f.commit()}};
  await assert.rejects(acquireFinalizationCheckpoint(changed, pinReader(f.root), f.f.options));
  assert.equal(f.f.calls.length, 0);
});

test('conflicting canonical edits and links refuse before publication and again before adoption', async t => {
  const f = repository(t), handle = await acquireFinalizationCheckpoint(f.config, f.reader, f.f.options);
  t.after(() => releaseAcceptedCheckpoint(handle));
  const bytes = finalizationCheckpointBytes(f.config, f.reader, handle);
  const adopt = admitCanonicalCheckpoint(f.root, f.reader, f.config.selector, bytes);
  f.write('data/selected-checkpoint.json', json({unrelated: true}));
  assert.throws(adopt, /changed outside/);
  assert.throws(() => admitCanonicalCheckpoint(f.root, f.reader, f.config.selector, bytes, true), /changed outside/);
  fs.unlinkSync(path.join(f.root, 'data/selected-checkpoint.json'));
  fs.symlinkSync('ownership-selection.json', path.join(f.root, 'data/selected-checkpoint.json'));
  assert.throws(() => admitCanonicalCheckpoint(f.root, f.reader, f.config.selector, bytes), /Nonordinary/);
});

const PREFIX = 'coordination/engineering/finalize-config/';
const locator = ({commit, path}) => ({commit, path});
const entry = fileURLToPath(new URL('../scripts/prepare-delivery-handoff.mjs', import.meta.url));
function fullDeliveryFixture(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'delivery-finalize-config-'));
  t.after(() => fs.rmSync(root, {recursive: true, force: true}));
  const env = {...process.env, GIT_CONFIG_NOSYSTEM: '1', GIT_CONFIG_GLOBAL: '/dev/null', GIT_NO_LAZY_FETCH: '1', NODE_OPTIONS: '', NODE_PATH: ''};
  const git = (...args) => execFileSync('git', args, {cwd: root, env, encoding: 'utf8'}).trim();
  git('init', '-q'); git('config', 'user.name', 'Fixture'); git('config', 'user.email', 'fixture@example.invalid');
  const write = (name, value) => {
    fs.mkdirSync(path.dirname(path.join(root, name)), {recursive: true});
    fs.writeFileSync(path.join(root, name), jsonBytes(value));
  };
  const commit = () => { git('add', '.'); git('commit', '-qm', 'Immutable fixture'); return git('rev-parse', 'HEAD'); };
  const reader = () => pinReader(root);
  const pin = (commit, name) => reader().pin(commit, name);
  const common = PREFIX + 'original/';
  write(common + 'body.json', {retained: true});
  const body = pin(commit(), common + 'body.json');
  const authority = {policy_id: 'retained-source-literal-additions', policy_version: 1,
    rule_preimage: body, rule_sha256: body.sha256, source_authority: body};
  const authorityEntry = {authority_sha256: digest(jsonBytes(authority)), ...authority};
  const registry = {version: 1, kind: 'retained-rule-authority-registry-v1', entries: [authorityEntry]};
  const reference = {id: 'geography:base', footprints_sha256: 'a'.repeat(64), hierarchy_sha256: 'b'.repeat(64)};
  write(common + 'registry.json', registry);
  write(common + 'manifest.json', {geographic_release: reference.id, footprints_sha256: reference.footprints_sha256,
    hierarchy_sha256: reference.hierarchy_sha256, original_assets: {bounds: {sha256: body.sha256}}});
  write(common + 'operating.json', {execution_custody: {terminal: body}});
  const originals = commit(), priorRegistry = pin(originals, common + 'registry.json'), manifest = pin(originals, common + 'manifest.json');
  write(common + 'rebind.json', {request: body, facts: body, publication: body, result: body,
    operating: pin(originals, common + 'operating.json')});
  const base = {version: 1, release_id: reference.id, sha256: manifest.sha256, selected_geography: {z: 1, a: 2}};
  const sidecar = {version: 2, kind: 'retained-native-additive-selection-v2', base_selection: base,
    authority_registry: priorRegistry, runtime_envelope: body,
    logical_asset_map: {base_manifest: manifest, owner_roster: body, ledger: body, patch: body}};
  write(common + 'sidecar.json', sidecar);
  const inherited = commit(), rebind = pin(inherited, common + 'rebind.json'), priorSidecar = pin(inherited, common + 'sidecar.json');
  write('data/ownership-selection.json', {...base, additive_release: {path: priorSidecar.path, bytes: priorSidecar.bytes, sha256: priorSidecar.sha256}});
  write('.github/package-inputs.json', {version: 1, inputs: ['public/', '.github/package-inputs.json'],
    optional_inputs: ['public/'], verification_paths: [], generated_outputs: []});
  const baseline = commit(), selector = pin(baseline, 'data/ownership-selection.json'), package_inputs = pin(baseline, '.github/package-inputs.json');
  const geometry = {type: 'Polygon', coordinates: [[[0, 0], [1, 0], [0, 1], [0, 0]]]};
  const row = {representation: 'native-cells', component_id: 'source-target:original', target_id: 'target:original', pixelIndex: 1,
    disposition: 'assigned', base_geometry: geometry, base_geometry_sha256: digest(jsonBytes(geometry)),
    native_rows: [{y: 0, runs: [[0, 1, 1]]}], native_bounds: [0, 0, 1, 1], native_cells: 1,
    source_receipt_sha256: body.sha256, authority_sha256: authorityEntry.authority_sha256, rule_sha256: authority.rule_sha256};
  const ledger = {version: 2, kind: 'native-additive-repair-ledger-v2', authority_registry_sha256: digest(jsonBytes(registry)),
    scope_ids: [row.component_id], rows: [row], current_rebind: rebind, current_targets: [{target_id: row.target_id}]};
  const effective = {...reference, id: 'geography:next'};
  const patch = {authority_registry_sha256: digest(jsonBytes(registry)), ledger_sha256: digest(jsonBytes(ledger)),
    base_reference: reference, effective_reference: effective, rows: row.native_rows};
  const descriptor = value => ({bytes: jsonBytes(value).length, sha256: digest(jsonBytes(value))});
  const envelope = {base_reference: reference, effective_reference: effective, base_manifest: {bytes: manifest.bytes, sha256: manifest.sha256},
    owner_roster: {bytes: body.bytes, sha256: body.sha256}, ledger: descriptor(ledger), patch: descriptor(patch)};
  const products = {'authority-registry.json': registry, 'selected-ledger.json': ledger, 'patch.json': patch, 'runtime-envelope.json': envelope};
  for (const [name, value] of Object.entries(products)) write(PREFIX + 'compose/' + name, value);
  const composed = commit();
  const full = {version: 1, selector, package_inputs, rebind, new_prefix: PREFIX, sidecar_output: PREFIX + 'sidecar.json',
    registry: pin(composed, PREFIX + 'compose/authority-registry.json'), ledger: pin(composed, PREFIX + 'compose/selected-ledger.json'),
    selected_ledger: pin(composed, PREFIX + 'compose/selected-ledger.json'), patch: pin(composed, PREFIX + 'compose/patch.json'),
    runtime_envelope: pin(composed, PREFIX + 'compose/runtime-envelope.json')};
  const compact = {version: full.version, selector: locator(selector), package_inputs: locator(package_inputs), rebind: locator(rebind),
    new_prefix: full.new_prefix, sidecar_output: full.sidecar_output,
    composition: locator(full.selected_ledger)};
  const run = (config, destination, ...flags) => {
    write('config.json', config);
    return spawnSync(process.execPath, [entry, 'finalize', 'config.json', destination, ...flags], {cwd: root, env, encoding: 'utf8'});
  };
  return {root, reader, full, compact, write, commit, baseline, products, run};
}

test('both full and compact production finalizers retain every prior output and add only chosen authenticated transport', async t => {
  const f = fullDeliveryFixture(t), selection = f.reader().json(f.full.selector);
  const accepted = acceptedFixture(undefined, undefined, selection);
  const directory = PREFIX + 'accepted', name = directory + '/selected-checkpoint.json';
  const chosen = {version: 1, kind: 'accepted-selected-checkpoint-locator-v1', acceptance: accepted.options.locator,
    retained_artifact: {path: directory + '/geography-artifact.zip'}};
  f.write(name, chosen); fs.writeFileSync(path.join(f.root, chosen.retained_artifact.path), accepted.zip);
  const checkpoint = {commit: f.commit(), path: name}, reader = f.reader();
  const config = {...f.compact, accepted_checkpoint: checkpoint};
  const handle = await acquireFinalizationCheckpoint(config, reader, accepted.options);
  t.after(() => releaseAcceptedCheckpoint(handle));
  const expected = finalizeDelivery(f.compact, reader), actual = finalizeDelivery(config, reader, {acceptedCheckpoint: handle});
  assert.deepEqual(actual, {...expected, 'selected-checkpoint.json': jsonBytes(chosen)});
  assert.deepEqual(finalizeDelivery({...f.full, accepted_checkpoint: checkpoint}, reader, {acceptedCheckpoint: handle}), actual);
  assert.throws(() => finalizeDelivery(config, reader), /private/);
});

test('an unchanged compatible selector permits older accepted transport; a next delivery must select a matching acceptance', async t => {
  const f = repository(t), handle = await acquireFinalizationCheckpoint(f.config, f.reader, f.f.options);
  t.after(() => releaseAcceptedCheckpoint(handle));
  f.write('unrelated.json', json({later_commit: true}));
  let config = {...f.config, selector: {...f.config.selector, commit: f.commit()}}, reader = pinReader(f.root);
  assert.deepEqual(finalizationCheckpointBytes(config, reader, handle), json(f.locator));
  f.write('data/ownership-selection.json', json({version: 1, release: 'next'}));
  config = {...config, selector: {...config.selector, commit: f.commit()}}; reader = pinReader(f.root);
  await assert.rejects(acquireFinalizationCheckpoint(config, reader, f.f.options), /prior selected baseline/);
});

test('changed archive and retargeted operand cannot borrow an accepted capability', async t => {
  const f = repository(t), handle = await acquireFinalizationCheckpoint(f.config, f.reader, f.f.options);
  t.after(() => releaseAcceptedCheckpoint(handle));
  f.write('coordination/engineering/checkpoint-test/other/selected-checkpoint.json', json(f.locator));
  let config = {...f.config, accepted_checkpoint: {commit: f.commit(), path: 'coordination/engineering/checkpoint-test/other/selected-checkpoint.json'}};
  assert.throws(() => finalizationCheckpointBytes(config, pinReader(f.root), handle), /operand differs/);
  f.write(f.locator.retained_artifact.path, Buffer.from('altered archive'));
  config = {...f.config, accepted_checkpoint: {...f.config.accepted_checkpoint, commit: f.commit()}};
  await assert.rejects(acquireFinalizationCheckpoint(config, pinReader(f.root), f.f.options), /artifact digest/);
});

test('publication preflight rejects conflicting canonical bytes before any batch output', async t => {
  const f = repository(t), handle = await acquireFinalizationCheckpoint(f.config, f.reader, f.f.options);
  t.after(() => releaseAcceptedCheckpoint(handle));
  const bytes = finalizationCheckpointBytes(f.config, f.reader, handle), destination = 'coordination/engineering/checkpoint-test/final';
  f.write('data/selected-checkpoint.json', json({unrelated: true}));
  assert.throws(() => publishFinalizedDelivery(f.root, destination, {'selected-checkpoint.json': bytes},
    {phase: 'finalize'}, f.reader, f.config.selector), /changed outside/);
  assert.equal(fs.existsSync(path.join(f.root, destination)), false);
});
