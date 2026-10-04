import test from 'node:test';
import assert from 'node:assert/strict';
import {sha256, subjectsHash} from '../scripts/evidence-quality.mjs';
import {evidenceRequirement} from '../scripts/evidence-policy.mjs';
import {validatePremergeManifest, validateReviewReceipt, checkPremergeEvidence, GEOMETRY_VERSION} from '../scripts/premerge-evidence.mjs';

const commit = 'a'.repeat(40), head = 'b'.repeat(40), branch = 'engineering/synthetic';
const manifestPath = 'coordination/engineering/synthetic/evidence-quality.json';
const outputPath = 'coordination/engineering/synthetic/results.json';
const baseline = Buffer.from('synthetic baseline\n'), output = Buffer.from('{"value":0.5}\n');
const desc = (path, bytes) => ({path, bytes: bytes.length, sha256: sha256(bytes), hash_kind: 'file-bytes'});
const policy = {version: 1, mode: 'enforce-new', activation_time: '2026-10-03T00:00:00Z', legacy_follow_up: 624};
function fixture() {
  const quality = {version: 1, manifest_path: manifestPath, subject_ids: [], pins: {}, review_kind: 'code'};
  const spec = {mode: 'engineering', evidence_quality: quality, max_prs: 1, depends_on: [], scope: 'Synthetic fixture'};
  const files = [{filename: outputPath, status: 'added'}, {filename: manifestPath, status: 'added'}];
  const issue = {number: 100, created_at: '2026-10-04T00:00:00Z', body: `<!-- worldatlas-work:v1\n${JSON.stringify(spec)}\n-->`};
  const manifest = {version: 1, issue: 100, lane: 'engineering', worker_id: 'author', subject_ids: [], subject_ids_sha256: subjectsHash([]),
    baseline: {commit, files: [desc('baseline.txt', baseline)], pins: {}}, sources: [], outputs: [desc(outputPath, output)],
    methods: [{id: 'synthetic', kind: 'code', description: 'Synthetic ledger', software: 'Node 24', units: 'fraction'}],
    metrics: [{id: 'share', value: 0.5, unit: 'fraction', vintage: 'current', input_sha256: sha256(baseline), evaluation_commit: commit}],
    summaries: [{metric_id: 'share', value: 0.5, unit: 'fraction'}], conclusions: [],
    stages: {research: 'complete', implementation: 'implemented', geographic_approval: 'not-requested'}, commands: ['node --test test/premerge-evidence.test.mjs'],
    change_receipts: files.map(file => ({path: file.filename, status: file.status})),
    metric_bindings: [{metric_id: 'share', path: outputPath, json_pointer: '/value'}]};
  const reservation = {worker_id: 'author'};
  const pr = {number: 101, head: {sha: head, ref: branch}, base: {sha: commit}, changed_files: files.length};
  const readFile = name => name === 'baseline.txt' ? baseline : output;
  return {manifest, spec, issue, files, reservation, pr, readFile, manifestPath, branch};
}
const validate = f => validatePremergeManifest(f.manifest, f);
function receipt(f) {
  return {version: 1, pr_number: f.pr.number, head_sha: head, manifest_sha256: sha256(JSON.stringify(f.manifest)), author_worker_id: 'author',
    reviewer_worker_id: 'reviewer', inspected_files: f.files.map(file => file.filename), evidence_hashes: [sha256(baseline), sha256(output)],
    outcome: 'accepted', limits: [], domains: {implementation: {outcome: 'accepted', scope: 'Actual synthetic ledger and changed-file controls', limits: []}}};
}
function review(f, r = receipt(f), options = {}) {
  return validateReviewReceipt(r, {pr: f.pr, manifest: f.manifest, manifestHash: sha256(JSON.stringify(f.manifest)), files: f.files,
    limits: [], author: 'author', ...options});
}
test('new requirements preserve old scopes, enforce new declarations and permit explicit legacy adoption', () => {
  const f = fixture(); assert.equal(evidenceRequirement(f.issue, f.spec, policy, branch).required, true);
  delete f.spec.evidence_quality; assert.throws(() => evidenceRequirement(f.issue, f.spec, policy, branch), /New work/);
  f.issue.created_at = '2026-10-02T00:00:00Z'; assert.equal(evidenceRequirement(f.issue, f.spec, policy, branch).legacy, true);
  delete f.issue.created_at; assert.throws(() => evidenceRequirement(f.issue, f.spec, policy, branch), /timestamp/);
  assert.equal(evidenceRequirement({}, {}, {...policy, mode: 'report-only'}).required, false);
});
test('positive real-format ledger validates actual files and binds an independent review', () => {
  const f = fixture(); assert.equal(validate(f).metric_bindings_checked, 1); assert.equal(review(f).reviewer, 'reviewer');
});
test('regressions: stale vintage, entry hash, wrong source/path and conflicting generated result fail', () => {
  const mutations = [f => f.manifest.baseline.files[0].sha256 = 'broken', f => f.manifest.baseline.files[0].hash_kind = 'entry',
    f => f.manifest.metrics[0].evaluation_commit = head, f => f.manifest.summaries[0].value = 0.9,
    f => f.manifest.metric_bindings[0].json_pointer = '/absent', f => f.manifest.metrics[0].value = f.manifest.summaries[0].value = 0.2,
    f => f.manifest.outputs[0].path = '../secret', f => f.manifest.worker_id = 'different', f => f.pr.base.sha = head, f => f.manifest.stages.geographic_approval = 'approved'];
  for (const mutate of mutations) {const f = fixture(); mutate(f); assert.throws(() => validate(f));}
});
test('full changes include rename/deletion originals; immutable original-source refresh cannot overwrite evidence', () => {
  const f = fixture(); f.files[0] = {...f.files[0], status: 'renamed', previous_filename: 'old.json'};
  f.manifest.change_receipts[0] = {path: outputPath, status: 'renamed', previous_path: 'old.json', original_sha256: sha256(output)};
  assert.equal(validate(f).change_files_checked, 2);
  delete f.manifest.change_receipts[0].previous_path; assert.throws(() => validate(f), /receipt/);
  f.manifest.change_receipts[0].previous_path = 'old.json'; f.manifest.baseline.files[0].path = 'old.json';
  f.manifest.baseline.files[0] = {...desc('old.json', output), role: 'original-source'};
  f.manifest.metrics[0].input_sha256 = sha256(output);
  assert.throws(() => validate(f), /original-source/);
  f.manifest.change_receipts.pop(); assert.throws(() => validate(f), /Incomplete/);
});
test('coordinate/helper policies require positive and negative controls; generators need reproducibility', () => {
  const f = fixture(); f.manifest.methods[0] = {id: 'area', kind: 'geography', description: 'Scientific control', software: 'pyproj 3.7.2', units: 'm2',
    helper_version: GEOMETRY_VERSION, axis_order: 'latitude-longitude', crs: 'EPSG:4326',
    area_method: 'WGS84 straight-source-edge ellipsoidal integral', distance_method: 'WGS84 inverse geodesic'};
  assert.throws(() => validate(f), /geographic|geography/i);
  f.manifest.methods[0].axis_order = 'longitude-latitude'; assert.throws(() => validate(f), /positive-control/);
  f.manifest.methods[0].helper_version = 'unreviewed'; assert.throws(() => validate(f), /Unsupported/);
  f.manifest.methods[0] = {id: 'gen', kind: 'generator', description: 'Two-run control', software: 'Python 3.12', units: 'bytes', helper_version: 'worldatlas-evidence-preparation-v1'};
  assert.throws(() => validate(f), /positive-control/);
});
test('generator controls bind actual positive, negative and equal two-run output bytes', () => {
  const f = fixture(), bytes = new Map([['baseline.txt', baseline], [outputPath, output]]);
  f.manifest.methods = [{id: 'gen', kind: 'generator', description: 'Synthetic deterministic JSON generator', software: 'Node 24',
    units: 'bytes', helper_version: 'worldatlas-evidence-preparation-v1'}];
  f.manifest.validation = [];
  for (const kind of ['positive-control', 'negative-control', 'reproducibility']) {
    const path = `coordination/engineering/synthetic/${kind}.json`;
    const record = {method_id: 'gen', kind, outcome: 'passed', ...(kind === 'reproducibility' ? {run_one_sha256: sha256(output), run_two_sha256: sha256(output)} : {})};
    const raw = Buffer.from(JSON.stringify(record)); bytes.set(path, raw);
    f.manifest.outputs.push(desc(path, raw)); f.files.push({filename: path, status: 'added'});
    f.manifest.change_receipts.push({path, status: 'added'}); f.manifest.validation.push({method_id: 'gen', kind, outcome: 'passed', evidence_path: path});
  }
  f.readFile = name => bytes.get(name); assert.equal(validate(f).change_files_checked, 5);
  const last = f.manifest.outputs.at(-1), record = JSON.parse(bytes.get(last.path)); record.run_two_sha256 = 'c'.repeat(64);
  bytes.set(last.path, Buffer.from(JSON.stringify(record))); Object.assign(last, desc(last.path, bytes.get(last.path)));
  assert.throws(() => validate(f), /reproducibility/);
});
test('Washington-style generated narrative/table mismatch fails against the same numeric ledger', () => {
  const f = fixture(), path = 'coordination/engineering/synthetic/table.md', raw = Buffer.from('Share | 50.00%\n');
  f.manifest.outputs.push({...desc(path, raw), role: 'generated-table'});
  f.files.push({filename: path, status: 'added'}); f.manifest.change_receipts.push({path, status: 'added'});
  f.manifest.rendered_tables = [{path, rows: [{metric_id: 'share', line: 1, template: 'Share | {value}%', decimals: 2, scale: 100}]}];
  f.readFile = name => name === path ? raw : name === 'baseline.txt' ? baseline : output;
  assert.equal(validate(f).change_files_checked, 3);
  f.manifest.rendered_tables[0].rows[0].template = 'Wrong | {value}%'; assert.throws(() => validate(f), /table differs/);
  f.manifest.rendered_tables = []; assert.throws(() => validate(f), /ledger-bound/);
});
test('reviews reject self approval, stale heads, omitted hashes/files and absent factual/geometry review', () => {
  for (const mutate of [r => r.reviewer_worker_id = 'author', r => r.head_sha = commit, r => r.evidence_hashes.pop(),
    r => r.inspected_files.pop(), r => r.outcome = 'changes-requested', r => delete r.domains.implementation]) {
    const f = fixture(), r = receipt(f); mutate(r); assert.throws(() => review(f, r));
  }
  const f = fixture(); assert.throws(() => review(f, receipt(f), {reviewKind: 'geometry'}), /geometry/);
  assert.throws(() => review(f, receipt(f), {limits: ['Primary source inaccessible']}), /limits/);
});

function remoteFixture(f, comments = []) {
  const bytes = Buffer.from(JSON.stringify(f.manifest));
  const contents = new Map([['baseline.txt', baseline], [outputPath, output], [manifestPath, bytes]]);
  const blobs = new Map([...contents].map(([name, bytes], index) => [`blob${index}`, bytes]));
  const tree = [...contents].map(([path, bytes], index) => ({path, type: 'blob', mode: '100644', size: bytes.length, sha: `blob${index}`}));
  const calls = [];
  const api = async (route, method = 'GET') => {
    calls.push({route, method}); assert.equal(method, 'GET', 'Setup must never mutate GitHub');
    if (route.includes('/git/commits/')) return {tree: {sha: 'tree'}};
    if (route.includes('/git/trees/')) return {truncated: false, tree};
    if (route.includes('/git/blobs/')) return {encoding: 'base64', content: blobs.get(route.split('/').pop()).toString('base64')};
    if (route.includes('/compare/')) return {status: 'identical'};
    if (route.includes('/comments?')) return comments;
    throw Error(`Unexpected remote route: ${route}`);
  };
  return {api, calls, bytes};
}
test('mock remote queue checks exact blobs/head/independent receipt with read-only requests', async () => {
  const f = fixture(), r = receipt(f), remote = remoteFixture(f); r.manifest_sha256 = sha256(remote.bytes);
  const {api, calls} = remoteFixture(f, [{id: 1, author_association: 'OWNER', body: `<!-- worldatlas-review:v1\n${JSON.stringify(r)}\n-->`}]);
  const result = await checkPremergeEvidence({...f, api, repo: 'test/repo', policy, review: true});
  assert.equal(result.review.reviewer, 'reviewer'); assert.ok(calls.every(row => row.method === 'GET'));
  await assert.rejects(() => checkPremergeEvidence({...f, api: remote.api, repo: 'test/repo', policy, review: true}), /Missing independent/);
  const failed = await checkPremergeEvidence({...f, api: remote.api, repo: 'test/repo', policy: {...policy, mode: 'report-only'}, review: true});
  assert.equal(failed.status, 'report-failure');
});
test('incomplete remote trees cannot become a passed byte check', async () => {
  const f = fixture(), remote = remoteFixture(f);
  await assert.rejects(() => checkPremergeEvidence({...f, repo: 'test/repo', policy,
    api: async route => route.includes('/git/trees/') ? {truncated: true, tree: []} : remote.api(route)}), /Incomplete/);
});
test('remote decisions reject stale exact-head reviews and a later change request', async () => {
  const f = fixture(), remote = remoteFixture(f), r = receipt(f); r.manifest_sha256 = sha256(remote.bytes);
  const comment = receipt => ({id: 1, author_association: 'OWNER', body: `<!-- worldatlas-review:v1\n${JSON.stringify(receipt)}\n-->`});
  await assert.rejects(() => checkPremergeEvidence({...f, repo: 'test/repo', policy, review: true,
    api: remoteFixture(f, [comment({...r, head_sha: commit})]).api}), /Missing independent/);
  await assert.rejects(() => checkPremergeEvidence({...f, repo: 'test/repo', policy, review: true,
    api: remoteFixture(f, [comment(r), {...comment({...r, outcome: 'changes-requested'}), id: 2}]).api}), /unresolved/);
  await assert.rejects(() => checkPremergeEvidence({...f, repo: 'test/repo', policy,
    api: route => route.includes('/compare/') ? Promise.resolve({status: 'diverged'}) : remote.api(route)}), /ancestor/);
});

test('unchanged authored evidence survives unrelated main advance, while current metrics require refresh', () => {
  const f = fixture(); f.pr.base.sha = 'c'.repeat(40);
  f.manifest.metrics[0].vintage = 'baseline';
  assert.equal(validate(f).change_files_checked, 2);
  f.manifest.metrics[0].vintage = 'current';
  assert.throws(() => validate(f), /actual PR-base vintage/);
});

test('trusted hosted gate checks a new limited prior-evidence registry and still rejects nonancestor baselines', async () => {
  const f=fixture(), prefix='research/geography/synthetic/', manifestFile=prefix+'evidence-quality.json', registryFile=prefix+'registry.geojson';
  const prior=Buffer.from(JSON.stringify({exact_subjects:['5901']}));
  const registry=Buffer.from(JSON.stringify({type:'FeatureCollection',features:[{type:'Feature',id:'StatCan:5901',geometry:null,
    properties:{id:'StatCan:5901',source_property:'CDUID',source_value:'5901'}}]}));
  f.pr.head.ref='geography/synthetic';f.spec.mode='geography';f.spec.owned_paths=[prefix];
  f.spec.evidence_quality={...f.spec.evidence_quality,manifest_path:manifestFile,subject_ids:['StatCan:5901']};
  f.issue.body=`<!-- worldatlas-work:v1\n${JSON.stringify(f.spec)}\n-->`;
  f.reservation={...f.reservation,owned_paths:[prefix]};
  f.manifest.stages={research:'complete',implementation:'not-proposed',geographic_approval:'unapproved'};
  f.manifest.lane='geography';f.manifest.subject_ids=['StatCan:5901'];f.manifest.subject_ids_sha256=subjectsHash(['StatCan:5901']);
  f.manifest.baseline={commit,files:[desc('prior-audit.json',prior)],pins:{},subject_inventory:{version:1,basis:'prior-evidence',
    path:'prior-audit.json',json_pointer:'/exact_subjects',id_prefix:'StatCan:',source_property:'CDUID',source_id:'source',registry_path:registryFile}};
  f.manifest.sources=[{id:'source',url:'https://example.org/source',role:'Original census roster',vintage:'2021',retrieved_at:'2026-10-03',
    license:{status:'unknown',terms:'Not independently inspected'},retention:'restoration-only',verification:'unverified',
    temporal_status:'reference',restoration:'Restore original archive',limit:'Original source not checked'}];
  f.manifest.outputs=[desc(registryFile,registry)];f.manifest.metrics=[];f.manifest.summaries=[];f.manifest.metric_bindings=[];
  f.files=[{filename:registryFile,status:'added'},{filename:manifestFile,status:'added'}];
  f.manifest.change_receipts=f.files.map(file=>({path:file.filename,status:'added'}));
  const raw=new Map([[manifestFile,Buffer.from(JSON.stringify(f.manifest))],['prior-audit.json',prior],[registryFile,registry]]);
  const tree=[...raw].map(([path,bytes])=>({path,type:'blob',mode:'100644',sha:sha256(bytes),size:bytes.length}));
  const api=async route=>{
    if(route.includes('/git/commits/'))return {tree:{sha:'tree'}};
    if(route.includes('/git/trees/'))return {truncated:false,tree};
    if(route.includes('/git/blobs/')){const row=tree.find(row=>row.sha===route.split('/').pop());return {encoding:'base64',content:raw.get(row.path).toString('base64')};}
    if(route.includes('/compare/'))return {status:'ahead'};
    throw Error('Unexpected route');
  };
  const r=await checkPremergeEvidence({...f,api,repo:'test/repo',policy});
  assert.equal(r.status,'limited');assert.equal(r.change_files_checked,2);assert.match(r.limits.join('\n'),/retained prior evidence/);
  await assert.rejects(()=>checkPremergeEvidence({...f,repo:'test/repo',policy,
    api:route=>route.includes('/compare/')?Promise.resolve({status:'diverged'}):api(route)}),/not an ancestor/);
});
