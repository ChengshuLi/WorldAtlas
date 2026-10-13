import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync,spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {resolveFrozenPackageProgramme, requireSeparatedProofRoots,
  requireActualAssembly, retainProofManifest, prepareFreshAssemblyScratch, recordFrozenChildDiagnostic} from '../scripts/run-selected-package-proof.mjs';

const hash = raw => createHash('sha256').update(raw).digest('hex');
const FROZEN_REVIEWED_HEAD = '9'.repeat(40);
const sourceHead = 'a'.repeat(40), acceptedHead = 'b'.repeat(40), tree = 'c'.repeat(40);
const repository = 'ChengshuLi/WorldAtlas';
const extractor = fileURLToPath(new URL('../scripts/extract-package-output.py', import.meta.url));
function temporary(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'atlas-proof-driver-'));
  t.after(() => fs.rmSync(root, {recursive: true, force: true})); return root;
}
function resolver() {
  const pr = {number: 1802, merged: true, state: 'closed', base: {ref: 'main'},
    head: {sha: FROZEN_REVIEWED_HEAD, repo: {full_name: repository}}, merge_commit_sha: acceptedHead};
  const accepted = {sha: acceptedHead, tree: {sha: tree}}, candidate = {sha: sourceHead, tree: {sha: tree}}, calls = [];
  const api = async route => {
    calls.push(route);
    if (route === `/repos/${repository}/pulls/1802`) return pr;
    if (route === `/repos/${repository}/git/commits/${acceptedHead}`) return accepted;
    if (route === `/repos/${repository}/git/commits/${sourceHead}`) return candidate;
    throw Error('Unexpected frozen-source authority route: ' + route);
  };
  return {pr, accepted, candidate, calls, load: () => resolveFrozenPackageProgramme({api, sourceHead, pullRequest:1802}), api};
}

test('production programme resolves requested accepted delivery and complete same-tree candidate commit', async () => {
  const f = resolver();
  assert.deepEqual(await f.load(), {pull_request: 1802, reviewed_head: FROZEN_REVIEWED_HEAD,
    accepted_commit: acceptedHead, source_head: sourceHead, source_tree: tree});
  assert.deepEqual(f.calls, [`/repos/${repository}/pulls/1802`, `/repos/${repository}/git/commits/${acceptedHead}`,
    `/repos/${repository}/git/commits/${sourceHead}`]);
  assert.notEqual(sourceHead, acceptedHead, 'A different candidate commit with exactly the accepted tree is valid');
});

test('unaccepted or replaced PR identity and partial-tree equivalence never establish the frozen programme', async () => {
  const changes = [f => f.pr.number = 1803, f => f.pr.merged = false, f => f.pr.state = 'open',
    f => f.pr.base.ref = 'work', f => f.pr.head.repo.full_name = 'fork/WorldAtlas',
    f => f.pr.head.sha = 'main', f => f.pr.merge_commit_sha = 'main',
    f => f.accepted.sha = sourceHead, f => f.candidate.sha = acceptedHead,
    f => f.accepted.tree.sha = 'not-a-tree', f => f.candidate.tree.sha = 'd'.repeat(40),
    f => delete f.candidate.tree];
  for (const change of changes) { const f = resolver(); change(f); await assert.rejects(f.load); }
  for (const invalid of ['main', '', 'a'.repeat(39), 'A'.repeat(40), null]) {
    const f = resolver(); await assert.rejects(resolveFrozenPackageProgramme({api: f.api, sourceHead: invalid, pullRequest:1802}), /Exact accepted source/);
    assert.deepEqual(f.calls, []);
  }
});

function checkouts(t) {
  const base = temporary(t);
  const create = (name, body) => {
    const root = path.join(base, name); fs.mkdirSync(root);
    const git = (...args) => execFileSync('git', ['-C', root, ...args], {encoding: 'utf8',
      env: {PATH: process.env.PATH, HOME: base, GIT_CONFIG_NOSYSTEM: '1', GIT_CONFIG_GLOBAL: '/dev/null'}}).trim();
    git('init', '-q'); fs.writeFileSync(path.join(root, 'identity'), body); git('add', 'identity');
    git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', name);
    return {root, head: git('rev-parse', 'HEAD')};
  };
  const source = create('candidate', 'frozen production'), observer = create('observer', 'separate proof');
  return {base, source, observer, options: {sourceRoot: source.root, observerRoot: observer.root,
    sourceHead: source.head, proofHead: observer.head}};
}

test('separate ordinary checkouts bind independent actual Git heads', t => {
  const f = checkouts(t);
  assert.deepEqual(requireSeparatedProofRoots(f.options), {source: f.source.root, observer: f.observer.root});
  const alias = path.join(f.base, 'candidate-alias'); fs.symlinkSync(f.source.root, alias);
  const nested = path.join(f.source.root, 'observer'); fs.mkdirSync(nested);
  for (const changed of [
    {sourceHead}, {proofHead: acceptedHead}, {sourceHead: 'main'}, {proofHead: ''},
    {observerRoot: f.source.root, proofHead: f.source.head}, {observerRoot: nested},
    {sourceRoot: alias}, {sourceRoot: f.base}, {sourceRoot: path.join(f.base, 'missing')}
  ]) assert.throws(() => requireSeparatedProofRoots({...f.options, ...changed}));
});

test('ambient Git identity overrides cannot redirect separated-checkout inspection', t => {
  const f = checkouts(t), values = {GIT_DIR: path.join(f.observer.root, '.git'), GIT_WORK_TREE: f.observer.root,
    GIT_CONFIG_COUNT: '1', GIT_CONFIG_KEY_0: 'core.bare', GIT_CONFIG_VALUE_0: 'true'};
  const before = new Map(Object.keys(values).map(key => [key, process.env[key]]));
  t.after(() => { for (const [key, value] of before) value === undefined ? delete process.env[key] : process.env[key] = value; });
  Object.assign(process.env, values);
  assert.deepEqual(requireSeparatedProofRoots(f.options), {source: f.source.root, observer: f.observer.root});
});

function assembly() {
  const origin = {head: FROZEN_REVIEWED_HEAD, run_id: 17, run_attempt: 1, artifact_id: 29,
    artifact_bytes: 100, artifact_digest: 'd'.repeat(64)};
  const receipt = {version: 1, kind: 'cloudflare', preflight: {passed: true, errors: [], inputs: {head: sourceHead}},
    assembly: {kind: 'retained-original-output-plus-current-additive', runtime_identity_version:2, current_execution: {source_commit: sourceHead},
      original_base_context_retained: true, base_restoration_invoked: false, invariant_build_invoked: false,
      original_manifest_sha256: 'e'.repeat(64), origin}};
  const raw = Buffer.from(JSON.stringify(receipt) + '\n');
  const result = {assembled:true,receipt_sha256:hash(raw),origin};
  return {receipt, raw, child: {status: 0, signal: null, error: undefined,
    stdout: 'Actual production CLI progress\n' + JSON.stringify(result) + '\n'}};
}

test('successful actual production child binds its fresh receipt without owning reference comparison', () => {
  const f = assembly(), result = requireActualAssembly(f.child, f.raw, sourceHead, 17);
  assert.deepEqual(result.receipt, f.receipt); assert.equal(result.receipt_sha256, hash(f.raw));
  assert.deepEqual(result.origin, f.receipt.assembly.origin);
  assert.equal(result.frozen_cli.exit_status, 0); assert.equal(result.frozen_cli.cli_succeeded, true);
  assert.equal(result.frozen_cli.result.assembled, true);
  assert.equal(result.frozen_cli.committed_output_observed, true);
  // A receipt must match the successful child's actual byte hash.
  const spaced = Buffer.concat([f.raw, Buffer.from(' ')]);
  assert.throws(()=>requireActualAssembly(f.child, spaced, sourceHead, 17), /bind actual receipt/);
  assert.throws(() => requireActualAssembly(f.child, f.raw, acceptedHead, 17), /identity differs/);
  assert.throws(() => requireActualAssembly(f.child, f.raw, sourceHead, 18), /identity differs/);
});

test('child failures, transport interruption, unbound success and missing output cannot continue', () => {
  const f = assembly(), encoded = value => JSON.stringify(value) + '\n';
  for (const child of [undefined, {...f.child, status: 1}, {...f.child, status: 2},
    {...f.child, signal: 'SIGTERM'}, {...f.child, error: Error('timed out')},
    {...f.child, stdout: ''}, {...f.child, stdout: '{truncated'}, {...f.child, stdout: '{}'},
    {...f.child, stdout: encoded({assembled: true, reason: 'Scientific context differs beyond authenticated provenance'})},
    {...f.child, stdout: encoded({assembled: false, reason: 'No applicable original output'})},
    {...f.child, stdout: encoded({assembled: false, reason: 'Actual proof assembly required; fallback cannot establish equivalence'})},
    {...f.child, stdout: encoded({assembled: false, reason: 'Archive digest differs'})},
    {...f.child, stdout: f.child.stdout + encoded({assembled: false, reason: 'Later unrelated failure'})}
  ]) assert.throws(() => requireActualAssembly(child, f.raw, sourceHead, 17));
  for (const raw of [Buffer.alloc(0), Buffer.from('{truncated'), Buffer.from('{}')])
    assert.throws(() => requireActualAssembly(f.child, raw, sourceHead, 17));
});

test('reconstructed receipt substitutions still reject fallback, wrong identities and executed invariant work', () => {
  for (const change of [
    r => r.kind = 'native-readback', r => r.preflight.passed = false,
    r => r.preflight.errors = ['actual failure'], r => delete r.preflight.errors,
    r => r.preflight.inputs.head = acceptedHead, r => r.assembly.kind = 'full-build',
    r => r.assembly.current_execution.source_commit = acceptedHead,
    r => r.assembly.runtime_identity_version = 1,
    r => r.assembly.origin.head = 'main', r => r.assembly.origin.run_id = 18,
    r => r.assembly.original_manifest_sha256 = 'invalid',
    r => r.assembly.original_base_context_retained = false,
    r => r.assembly.base_restoration_invoked = true, r => r.assembly.invariant_build_invoked = true,
    r => delete r.assembly.invariant_build_invoked
  ]) {
    const f = assembly(); change(f.receipt); const raw = Buffer.from(JSON.stringify(f.receipt));
    const result=JSON.parse(f.child.stdout.trim().split('\n').at(-1)); result.receipt_sha256=hash(raw);
    const child={...f.child,stdout:JSON.stringify(result)};
    assert.throws(() => requireActualAssembly(child, raw, sourceHead, 17), /identity differs/);
  }
});

function validManifest() {
  const definition = {version: 1, inputs: ['.github/package-inputs.json'], optional_inputs: [],
    verification_paths: [], generated_outputs: ['dist/']};
  const files = ['dist/client/atlas-geography.json', 'dist/cloudflare/index.js', 'dist/cloudflare/wrangler.json']
    .map(name => ({path: name, bytes: 2, sha256: hash('{}')}));
  return {version: 1, kind: 'original-cloudflare-package-output', source: {head: FROZEN_REVIEWED_HEAD, tree,
    input_definition_sha256: hash(JSON.stringify(definition)), definition,
    files: [{path: '.github/package-inputs.json', mode: '100644', oid: tree}], selection: {version: 1}},
    runtime: {node: process.version, platform: process.platform, arch: process.arch, dependencies: 'd'.repeat(64),
      installed: {node: {sha256: 'e'.repeat(64)}, dependencies: {sha256: 'f'.repeat(64)}}},
    configuration: {}, output: {files, bytes: 6}};
}
function archiveFixture(t, {changeManifest, zipMode = 'valid'} = {}) {
  const directory = temporary(t), manifest = validManifest(); changeManifest?.(manifest);
  const raw = Buffer.from(JSON.stringify(manifest) + '\n');
  const archive = execFileSync('python3', ['-I', '-B', '-c', `
import io, stat, sys, zipfile
mode = sys.argv[1]
raw = sys.stdin.buffer.read()
output = io.BytesIO()
with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as package:
    name = '.cache/package-output-manifest.json'
    if mode == 'missing': name = 'wrong-manifest.json'
    info = zipfile.ZipInfo(name)
    info.create_system = 3
    info.external_attr = ((stat.S_IFLNK | 0o777) if mode == 'symlink' else (stat.S_IFREG | 0o644)) << 16
    package.writestr(info, raw)
    if mode == 'duplicate': package.writestr(name, raw)
sys.stdout.buffer.write(output.getvalue())
`, zipMode], {input: raw, env: {PATH: process.env.PATH}, stdio: ['pipe', 'pipe', 'pipe'], maxBuffer: 1048576});
  const f = {directory, manifest, raw, archive, extractor, expectedHash: hash(raw), fetches: 0, routes: [],
    location: 'https://fixture.blob.core.windows.net/original-output', redirectStatus: 302, deliveryStatus: 200,
    origin: {artifact_id: 29, artifact_bytes: archive.length, artifact_digest: hash(archive)}};
  f.api = {artifactRedirect: async route => { f.routes.push(route);
    return new Response(null, {status: f.redirectStatus, headers: {location: f.location}}); }};
  f.fetchImpl = async (url, options) => {
    f.fetches++; assert.equal(String(url), f.location); assert.equal(options.redirect, 'error');
    assert.equal(options.headers, undefined, 'Signed-blob delivery must receive no credentials');
    return new Response(f.archive, {status: f.deliveryStatus});
  };
  f.load = () => retainProofManifest(f); return f;
}

test('proof manifest uses exact authenticated archive and real bounded extractor without delivery credentials', async t => {
  const f = archiveFixture(t), result = await f.load();
  assert.deepEqual(result.raw, f.raw); assert.deepEqual(JSON.parse(result.raw), f.manifest);
  assert.equal(result.file, path.join(f.directory, 'original-manifest.json'));
  assert.deepEqual(f.routes, [`/repos/${repository}/actions/artifacts/29/zip`]);
  assert.equal(f.fetches, 1); assert.equal(fs.existsSync(path.join(f.directory, 'original-output.zip')), false);
});

test('archive transport rejects wrong origin, untrusted redirects, incomplete or substituted bytes, and stale manifest hash', async t => {
  const changes = [f => f.origin.artifact_id = 0, f => f.origin.artifact_bytes = 0,
    f => f.origin.artifact_digest = 'not-a-digest', f => f.expectedHash = 'invalid',
    f => f.redirectStatus = 200, f => f.deliveryStatus = 500,
    f => f.location = 'http://fixture.blob.core.windows.net/output',
    f => f.location = 'https://fixture.blob.core.windows.net.attacker.invalid/output',
    f => f.location = 'https://name:password@fixture.blob.core.windows.net/output',
    f => f.location = 'https://fixture.blob.core.windows.net:444/output',
    f => f.origin.artifact_bytes++, f => f.origin.artifact_bytes--,
    f => f.origin.artifact_digest = 'f'.repeat(64), f => f.expectedHash = 'e'.repeat(64),
    f => { f.archive = Buffer.from(f.archive); f.archive[40] ^= 1; }];
  for (const change of changes) { const f = archiveFixture(t); change(f); await assert.rejects(f.load); }
});

test('authenticated ZIP does not excuse malformed, absent, duplicate or linked manifest control data', async t => {
  for (const zipMode of ['missing', 'duplicate', 'symlink']) await assert.rejects(archiveFixture(t, {zipMode}).load);
  for (const changeManifest of [m => m.kind = 'native-readback', m => m.source.head = 'main',
    m => m.output.files.pop(), m => m.output.bytes++, m => m.output.files[0].path = 'dist/client/../../escape'])
    await assert.rejects(archiveFixture(t, {changeManifest}).load);
});

test('archive and manifest destination collisions preserve existing bytes', async t => {
  for (const name of ['original-output.zip', 'original-manifest.json']) {
    const f = archiveFixture(t), file = path.join(f.directory, name); fs.writeFileSync(file, 'sentinel');
    await assert.rejects(f.load); assert.equal(fs.readFileSync(file, 'utf8'), 'sentinel');
  }
});

test('manifest extraction receives no ambient credential or code-injection environment', async t => {
  const f = archiveFixture(t), names = ['GH_TOKEN', 'GITHUB_TOKEN', 'WORLDATLAS_CHECKOUT_TOKEN', 'ACTIONS_RUNTIME_TOKEN',
    'PACKAGE_SECRET', 'REPOSITORY_PASSWORD', 'PACKAGE_CREDENTIAL', 'REMOTE_AUTHORIZATION', 'SESSION_COOKIE', 'NODE_OPTIONS', 'NODE_PATH'];
  const before = new Map(names.map(name => [name, process.env[name]]));
  t.after(() => { for (const [name, value] of before) value === undefined ? delete process.env[name] : process.env[name] = value; });
  for (const name of names) process.env[name] = 'test-only-sentinel';
  const wrapper = path.join(f.directory, 'assert-clean-extractor.py');
  fs.writeFileSync(wrapper, `import os, runpy\nassert not any(name in os.environ for name in ${JSON.stringify(names)})\nrunpy.run_path(${JSON.stringify(extractor)}, run_name='__main__')\n`);
  f.extractor = wrapper; assert.deepEqual((await f.load()).raw, f.raw);
});

test('proof workflow keeps current observer separate from frozen production and authenticates before installers', () => {
  const workflow = fs.readFileSync(new URL('../.github/workflows/selected-package-proof.yml', import.meta.url), 'utf8');
  const steps = workflow.split(/^      - /m).slice(1);
  const step = name => {
    const rows = steps.filter(text => text.startsWith('name: ' + name + '\n'));
    assert.equal(rows.length, 1, 'Exactly one workflow step: ' + name); return rows[0];
  };
  const observer = step('Checkout current proof implementation separately');
  const frozen = step('Checkout frozen production source');
  assert.equal(steps.filter(text => /uses: actions\/checkout@/.test(text)).length, 2);
  assert.match(observer, /ref: \$\{\{ github\.sha \}\}/); assert.match(observer, /path: proof-tools/);
  assert.match(frozen, /ref: \$\{\{ inputs\.source_head \}\}/); assert.match(frozen, /path: candidate/);
  for (const checkout of [observer, frozen]) assert.match(checkout, /persist-credentials: false/);
  assert.match(workflow, /defaults:\n      run:\n        working-directory: candidate/);
  const resolve = step('Authenticate complete accepted frozen programme');
  const installer = step('Authenticate installer inputs before candidate dependency execution');
  const dependencies = step('Install actual pinned dependencies');
  const assembly = step('Assemble frozen production source and compare with current proof implementation');
  assert.ok(steps.indexOf(resolve) < steps.indexOf(installer));
  assert.ok(steps.indexOf(installer) < steps.indexOf(dependencies));
  assert.ok(steps.indexOf(dependencies) < steps.indexOf(assembly));
  assert.match(resolve, /working-directory: proof-tools/);
  assert.match(resolve, /node scripts\/run-selected-package-proof\.mjs --resolve-frozen/);
  assert.match(installer, /SELECTED_PACKAGE_TRUSTED_BASE: \$\{\{ steps\.frozen\.outputs\.programme_sha \}\}/);
  assert.match(assembly, /working-directory: proof-tools/);
  assert.match(assembly, /SELECTED_PACKAGE_TRUSTED_BASE: \$\{\{ github\.sha \}\}/);
  assert.match(assembly, /SELECTED_PACKAGE_ENTRY_POINT: scripts\/run-selected-package-proof\.mjs/);
  const native = step('Read back actual assembled native output');
  const consumers = step('Run genuine current selected output consumers');
  assert.match(native, /model-reader-call-boundary-controls\.mjs --built-output-readback \.cache\/native-normal-built-output\.json/);
  assert.match(consumers, /INTEGRATION_TEST_SELECTION: selected-output/);
  assert.match(consumers, /SELECTED_PACKAGE_ASSEMBLY_SHA256: \$\{\{ steps\.assembly\.outputs\.assembly_sha256 \}\}/);
  assert.match(consumers, /selectedDeliverySmoke\(process\.env\.SELECTED_EXPECTATIONS_PATH\)/);
  assert.match(consumers, /node scripts\/run-integration-tests\.mjs/);
  assert.ok(steps.indexOf(assembly) < steps.indexOf(native) && steps.indexOf(native) < steps.indexOf(consumers));
  for (const consumer of [native, consumers]) assert.doesNotMatch(consumer, /working-directory: proof-tools|continue-on-error: true/);
  const upload = step('Retain actual comparison and current consumer receipts');
  assert.match(upload, /if: success\(\)/); assert.match(upload, /if-no-files-found: error/);
  assert.ok(steps.indexOf(consumers) < steps.indexOf(upload));
  for (const name of ['selected-package-proof', 'selected-package-original-manifest', 'package-input-build', 'native-normal-built-output', 'selected-delivery-smoke'])
    assert.ok(upload.includes('candidate/.cache/' + name + '.json'));
  assert.doesNotMatch(workflow, /npm run build|node scripts\/build|continue-on-error: true|(?:contents|actions|pull-requests): write/);
});


test('driver rejects stale output before genuine frozen CLI and isolates its failure output from final proof', () => {
  const source = fs.readFileSync(new URL('../scripts/run-selected-package-proof.mjs', import.meta.url), 'utf8');
  const freshness = source.indexOf("Fresh frozen proof checkout required; prior output is not evidence");
  const child = source.indexOf("const child=spawnSync(");
  const receipt = source.indexOf('const receiptRaw=recordFrozenChildDiagnostic(');
  const comparison = source.indexOf('const comparison=compareSelectedPackageReadback(');
  const success = source.indexOf('`assembled=true');
  assert.ok(freshness > 0 && child > freshness && receipt > child && comparison > receipt && success > comparison);
  const guard = source.slice(source.lastIndexOf('for(const target', freshness), freshness);
  for (const name of ["path.join(sourceRoot,'dist')", 'receiptPath', "path.join(cache,'selected-package-proof.json')"])
    assert.ok(guard.includes(name), 'Freshness covers ' + name);
  assert.match(guard, /fs\.lstatSync\(target\)/);
  assert.ok(source.indexOf('const receiptPath=prepareFreshAssemblyScratch(sourceRoot)')<child);
  const invocation = source.slice(child, receipt);
  assert.match(invocation, /selected-package-bootstrap\.py/);
  assert.match(invocation, /cwd:sourceRoot/);
  assert.match(invocation, /SELECTED_PACKAGE_TRUSTED_BASE:frozen\.accepted_commit/);
  assert.match(invocation, /SELECTED_PACKAGE_ENTRY_POINT:'scripts\/assemble-selected-package\.mjs'/);
  assert.match(invocation, /SELECTED_PACKAGE_VERIFY_ONLY:'false'/);
  assert.match(invocation, /GITHUB_OUTPUT:path\.join\(sourceRoot,'\.cache\/frozen-cli-output'\)/);
  assert.doesNotMatch(invocation, /GITHUB_EVENT_PATH:|GITHUB_EVENT_NAME:|GITHUB_WORKFLOW:/);
  assert.doesNotMatch(source, /process\.argv\s*=|import\(.*assemble-selected-package/);
  assert.match(source, /frozen_cli:committed\.frozen_cli/);
});


test('fresh assembly scratch is created ordinarily and rejects stale files or dangling links', t => {
  const root=temporary(t),receipt=prepareFreshAssemblyScratch(root);
  assert.equal(receipt,path.join(root,'.cache/package-input-build.json'));
  assert.ok(fs.lstatSync(path.dirname(receipt)).isDirectory());
  for(const target of [path.join(root,'dist'),receipt,path.join(root,'.cache/selected-package-proof.json'),path.join(root,'.cache/frozen-cli-output')]){
    fs.symlinkSync(path.join(root,'missing'),target);
    assert.throws(()=>prepareFreshAssemblyScratch(root),/Fresh frozen/);fs.unlinkSync(target);
    fs.writeFileSync(target,'prior');assert.throws(()=>prepareFreshAssemblyScratch(root),/Fresh frozen/);fs.unlinkSync(target);
  }
  fs.rmdirSync(path.join(root,'.cache'));fs.symlinkSync(path.join(root,'missing'),path.join(root,'.cache'));
  assert.throws(()=>prepareFreshAssemblyScratch(root),/Ordinary assembly scratch/);
});


test('real pre-receipt child failure logs and retains sanitized cause before missing receipt rejection',t=>{
  const root=temporary(t);prepareFreshAssemblyScratch(root);
  const secret='private-sentinel-value';
  const child=spawnSync(process.execPath,['-e',`console.log(JSON.stringify({assembled:false,reason:'Original runtime differs '+process.env.TEST_DIAGNOSTIC_SECRET}));console.error('fetch https://example.invalid/signed?secret=hidden Bearer another-secret');process.exitCode=1;`],
    {encoding:'utf8',env:{PATH:process.env.PATH,TEST_DIAGNOSTIC_SECRET:secret}});
  child.options={env:{UNRELATED_PRIVATE_VALUE:'do-not-serialize-environment'}};
  const logs=[];
  assert.throws(()=>recordFrozenChildDiagnostic({child,sourceRoot:root,secret,log:text=>logs.push(text)}),/did not publish an ordinary receipt/);
  const raw=fs.readFileSync(path.join(root,'.cache/selected-package-child-diagnostic.json'),'utf8'),record=JSON.parse(raw);
  assert.equal(record.status,1);assert.match(record.stdout.text,/Original runtime differs/);
  assert.match(record.stdout.text,/redacted/);assert.match(record.stderr.text,/delivery address/);
  assert.equal(logs.length,1);assert.match(logs[0],/Original runtime differs/);
  for(const leaked of [secret,'another-secret','secret=hidden','do-not-serialize-environment'])assert.ok(!raw.includes(leaked)&&!logs[0].includes(leaked));
  assert.equal(fs.existsSync(path.join(root,'.cache/package-input-build.json')),false);
});
test('diagnostics preserve genuine receipt bytes but reject symlink receipts and remain non-success evidence',t=>{
  for(const linked of [false,true]){
    const root=temporary(t);prepareFreshAssemblyScratch(root);const receipt=path.join(root,'.cache/package-input-build.json');
    const raw=Buffer.from('{"kind":"test-receipt-only"}');
    if(linked){const outside=path.join(root,'outside');fs.writeFileSync(outside,raw);fs.symlinkSync(outside,receipt);}
    else fs.writeFileSync(receipt,raw);
    const child={status:1,signal:null,stdout:'{"assembled":false,"reason":"known failure"}',stderr:''};
    const run=()=>recordFrozenChildDiagnostic({child,sourceRoot:root,log:()=>{}});
    if(linked)assert.throws(run,/ordinary receipt/);else assert.deepEqual(run(),raw);
    assert.match(JSON.parse(fs.readFileSync(path.join(root,'.cache/selected-package-child-diagnostic.json'))).semantics,/does not establish assembly/);
  }
});
test('workflow retains only sanitized child diagnosis on failure without granting proof success',()=>{
  const workflow=fs.readFileSync(new URL('../.github/workflows/selected-package-proof.yml',import.meta.url),'utf8');
  const step=workflow.split('      - name: Retain frozen child execution diagnostic')[1].split('      - name:')[0];
  assert.match(step,/if: always\(\)/);assert.match(step,/candidate\/\.cache\/selected-package-child-diagnostic\.json/);
  assert.match(step,/if-no-files-found: ignore/);assert.doesNotMatch(step,/continue-on-error|package-input-build|selected-package-proof\.json/);
});


test('actual spawn, signal, timeout and output-limit failures retain first cause without an assembly receipt',t=>{
  const cases=[
    ['missing executable',()=>spawnSync('/definitely-absent-package-proof-command',[],{encoding:'utf8'}),'ENOENT'],
    ['signal',()=>spawnSync(process.execPath,['-e',"console.error('signal-first-cause');process.kill(process.pid,'SIGTERM')"],{encoding:'utf8'}),null],
    ['timeout',()=>spawnSync(process.execPath,['-e',"console.error('timeout-first-cause');setTimeout(()=>{},5000)"],{encoding:'utf8',timeout:150}),'ETIMEDOUT'],
    ['output limit',()=>spawnSync(process.execPath,['-e',"process.stdout.write('output-first-cause '+ 'x'.repeat(131072))"],{encoding:'utf8',maxBuffer:1024}),'ENOBUFS']
  ];
  for(const [label,invoke,code]of cases){
    const root=temporary(t);prepareFreshAssemblyScratch(root);const child=invoke(),logs=[];
    assert.throws(()=>recordFrozenChildDiagnostic({child,sourceRoot:root,log:text=>logs.push(text)}),/did not publish/);
    const diagnostic=JSON.parse(fs.readFileSync(path.join(root,'.cache/selected-package-child-diagnostic.json')));
    assert.equal(diagnostic.error_code,code,label);assert.equal(logs.length,1,label);
    if(label==='signal')assert.equal(diagnostic.signal,'SIGTERM');
    if(label==='output limit'){assert.match(diagnostic.stdout.text,/output-first-cause/);assert.ok(diagnostic.stdout.text.length<9000);}
    assert.throws(()=>requireActualAssembly(child,Buffer.from('{}'),sourceHead,1));
  }
});
test('malformed receipts and unrelated failures preserve diagnostics without manufacturing proof success',t=>{
  const root=temporary(t);prepareFreshAssemblyScratch(root);fs.writeFileSync(path.join(root,'.cache/package-input-build.json'),'{broken');
  const child=spawnSync(process.execPath,['-e',"console.log(JSON.stringify({assembled:false,reason:'Scientific context differs beyond authenticated provenance'}));process.exitCode=1"],{encoding:'utf8'});
  const raw=recordFrozenChildDiagnostic({child,sourceRoot:root,log:()=>{}});
  assert.throws(()=>requireActualAssembly(child,raw,sourceHead,1),/Successful actual production assembly/);
  assert.ok(fs.existsSync(path.join(root,'.cache/selected-package-child-diagnostic.json')));
});
test('large diagnostic retains both first and final cause and reaches logs even if durable write fails',t=>{
  const root=temporary(t);prepareFreshAssemblyScratch(root);const file=path.join(root,'.cache/selected-package-child-diagnostic.json');fs.writeFileSync(file,'preserved prior');
  const logs=[],child={status:2,signal:null,stderr:'FIRST CAUSE '+ 'x'.repeat(20000)+' FINAL CAUSE',stdout:''};
  assert.throws(()=>recordFrozenChildDiagnostic({child,sourceRoot:root,log:text=>logs.push(text)}),/EEXIST/);
  assert.equal(fs.readFileSync(file,'utf8'),'preserved prior');assert.equal(logs.length,2);assert.match(logs[1],/persistence failed/);
  assert.match(logs[0],/FIRST CAUSE/);assert.match(logs[0],/FINAL CAUSE/);assert.match(logs[0],/diagnostic middle omitted/);
});


test('requested delivery identity is general but must remain an exact positive pull request',async()=>{
  const f=resolver(); f.pr.number=2042;
  const api=route=>f.api(route.replace('/pulls/2042','/pulls/1802'));
  assert.equal((await resolveFrozenPackageProgramme({api,sourceHead,pullRequest:2042})).pull_request,2042);
  for(const pullRequest of [undefined,0,-1,1.5,'1802',Number.MAX_SAFE_INTEGER+1])
    await assert.rejects(resolveFrozenPackageProgramme({api,sourceHead,pullRequest}),/Exact accepted/);
});
test('current observer owns explicit accepted reference authority and final comparison',()=>{
  const source=fs.readFileSync(new URL('../scripts/run-selected-package-proof.mjs',import.meta.url),'utf8');
  assert.match(source,/expectedPullRequest:Number\(input.source_pull_request\)/);
  assert.doesNotMatch(source,/retainSuccessfulChildProof|result\.proof/);
  assert.ok(source.indexOf('const readback=await loadSelectedPackageReadback(')<source.indexOf('const child=spawnSync('));
  assert.ok(source.indexOf('const comparison=compareSelectedPackageReadback(')>source.indexOf('const committed=requireActualAssembly('));
});
