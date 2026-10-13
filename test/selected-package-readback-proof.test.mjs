import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {loadSelectedPackageReadback} from '../scripts/selected-package-readback-proof.mjs';

const hash = raw => createHash('sha256').update(raw).digest('hex');
const repo = 'ChengshuLi/WorldAtlas', expectedHead = 'a'.repeat(40), workflowHead = 'b'.repeat(40);
const producerSteps = [
  'Build the combined application once before asset-dependent tests',
  'Read back qualified native build outputs when selected',
  'Test applicable combined-tree invariants without publishing or live imports',
  'Retain native built-output readback'
];
const authorSteps = [
  'Verify full-regression package controls', 'Build hosted assets',
  'Read back qualified native build outputs when selected', 'Complete regression shard',
  'Verify full-regression package receipt', 'Retain native built-output readback',
  'Retain full-regression package receipt'
];
const authorReceipt = 'Actual reviewed-head Cloudflare package and applicable native readback receipts verified.';
const makeZip = (entries, streaming = false, forceZip64 = false) => execFileSync('python3', ['-I', '-S', '-B', '-c', `
import base64, io, json, stat, sys, zipfile
options = json.load(sys.stdin)
entries = options['entries']
class Stream(io.BytesIO):
    def seek(self, *args): raise OSError('Nonseekable Actions-style transport')
output = Stream() if options['streaming'] else io.BytesIO()
with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as package:
    for entry in entries:
        info = zipfile.ZipInfo(entry['name'])
        info.create_system = 3
        info.external_attr = entry.get('mode', stat.S_IFREG | 0o644) << 16
        info.compress_type = entry.get('compression', zipfile.ZIP_DEFLATED)
        with package.open(info, 'w', force_zip64=options['forceZip64']) as member:
            member.write(base64.b64decode(entry['body']))
sys.stdout.buffer.write(output.getvalue())
`], {input: JSON.stringify({entries, streaming, forceZip64}), env: {PATH: '/usr/bin:/bin'}, maxBuffer: 32 * 1048576});
const entry = (name, body, options = {}) => ({name, body: Buffer.from(body).toString('base64'), ...options});
function fixture({author = false, smoke = !author, reportChange, zipChange, archiveChange, streaming = false, forceZip64 = false} = {}) {
  const pin = (path, body) => ({path, bytes: Buffer.byteLength(body), sha256: hash(body)});
  const assets = [pin('atlas-geography.json', '{}'), pin('native/rows.bin', 'rows')];
  const report = {version: 1, kind: 'ordinary-cloudflare-built-output-readback', head: expectedHead,
    static_assets: {count: assets.length, bytes: assets.reduce((sum, row) => sum + row.bytes, 0), files: assets},
    worker_bundle_files: [pin('index.js', 'worker'), pin('wrangler.json', '{}')],
    nativeContextInputStage: {version: 1, original_stage: {all: ['retained', 'fields']}, current_execution: {
      source_head: expectedHead, full_code_closure: [{path: 'scripts/build.mjs', mode: '100644', bytes: 7, sha256: hash('builder')}],
      counters: {whole_member_reads: 30}, arbitrary_original_field: {retained: true}}}};
  reportChange?.(report);
  const raw = Buffer.from(JSON.stringify(report, null, 2) + '\n');
  let entries = [entry('native-normal-built-output.json', raw)];
  if (smoke) entries.push(entry('selected-delivery-smoke.json', '{"passed":true}\n'));
  entries = zipChange?.(entries) ?? entries;
  let archive = makeZip(entries, streaming, forceZip64);
  archive = archiveChange?.(archive) ?? archive;
  const run = {id: 17, run_attempt: 2, head_sha: workflowHead, head_branch: author ? 'engineering/native102' : 'main',
    event: author ? 'pull_request' : 'workflow_dispatch',
    path: author ? '.github/workflows/merge-integration-checks.yml' : '.github/workflows/worker-merge.yml', status: 'completed', conclusion: 'success',
    repository: {full_name: repo}, head_repository: {full_name: repo},
    ...(author ? {pull_requests: [{number: 1808, url: `https://api.github.com/repos/${repo}/pulls/1808`,
      head: {sha: expectedHead, ref: 'engineering/native102', repo: {url: `https://api.github.com/repos/${repo}`}},
      base: {sha: 'c'.repeat(40), ref: 'main', repo: {url: `https://api.github.com/repos/${repo}`}}}]} : {})};
  const job = {id: 29, run_id: 17, run_attempt: 2, head_sha: workflowHead, name: author ? 'regression (0)' : 'integration (0)',
    status: 'completed', conclusion: 'success', steps: (author ? authorSteps : producerSteps).map((name, index) =>
      ({name, number: index + 12, status: 'completed', conclusion: 'success'}))};
  const artifact = {id: 41, name: author ? `native-built-output-regression-1808-${expectedHead}` : 'native-built-output-12345678-1234-1234-1234-123456789abc', size_in_bytes: archive.length,
    digest: 'sha256:' + hash(archive), expired: false, workflow_run: {id: 17, head_sha: workflowHead}};
  const receipt = {built_output_readback: '/home/runner/work/WorldAtlas/WorldAtlas/.cache/native-normal-built-output.json',
    bytes: raw.length, sha256: hash(raw)};
  const inventory = {total_count: 2, jobs: [job, {id: 30, name: 'merge'}]};
  const f = {run, job, artifact, report, receipt, inventory, archive, calls: [], deliveries: [],
    logLocation: 'https://fixture.blob.core.windows.net/job-log', artifactLocation: 'https://fixture.blob.core.windows.net/archive'};
  f.log = () => [JSON.stringify(f.receipt), ...(author ? [authorReceipt] : []),
    'SHA256 digest of uploaded artifact zip is ' + f.artifact.digest.slice(7),
    `Artifact ${f.artifact.name} has been successfully uploaded! Final size is ${f.artifact.size_in_bytes} bytes. Artifact ID is ${f.artifact.id}`,
    // An unrelated upload digest in the same job is not a conflicting receipt.
    'SHA256 digest of uploaded artifact zip is ' + 'e'.repeat(64)
  ].map(line => '2026-10-12T20:26:51.9866172Z ' + line).join('\n');
  const api = async route => {
    f.calls.push(route);
    if (route === `/repos/${repo}/actions/runs/17/attempts/2`) return f.run;
    if (route === `/repos/${repo}/actions/runs/17/attempts/2/jobs?per_page=100&page=1`) return f.inventory;
    if (route === `/repos/${repo}/actions/jobs/29`) return f.job;
    if (route === `/repos/${repo}/actions/artifacts/41`) return f.artifact;
    throw Error('Unexpected fixture authority route: ' + route);
  };
  api.jobLogRedirect = async route => {
    assert.equal(route, `/repos/${repo}/actions/jobs/29/logs`);
    return new Response(null, {status: 302, headers: {location: f.logLocation}});
  };
  api.artifactRedirect = async route => {
    assert.equal(route, `/repos/${repo}/actions/artifacts/41/zip`);
    return new Response(null, {status: 302, headers: {location: f.artifactLocation}});
  };
  const fetchImpl = async (url, options) => {
    f.deliveries.push(String(url));
    assert.equal(options.headers, undefined, 'Delivery must not receive authentication');
    assert.equal(options.redirect, 'error');
    if (String(url) === f.logLocation) return new Response(f.log());
    assert.equal(String(url), f.artifactLocation);
    return new Response(f.archive);
  };
  f.load = () => loadSelectedPackageReadback({api, repo, runId: 17, attempt: 2, expectedHead, fetchImpl});
  return f;
}

test('exact queue attempt authenticates the full native report with optional smoke, without conflating workflow and candidate heads', async () => {
  for (const smoke of [false, true]) {
    const f = fixture({smoke}), result = await f.load();
    assert.deepEqual(result.report, f.report);
    assert.deepEqual(result.report.nativeContextInputStage, f.report.nativeContextInputStage);
    assert.equal(result.origin.head, expectedHead);
    assert.equal(result.origin.workflow_head, workflowHead);
    assert.equal(result.origin.report_sha256, f.receipt.sha256);
    assert.equal(result.origin.artifact_digest, hash(f.archive));
    assert.equal(result.origin.use, 'full-output-comparison-only');
    assert.equal(f.calls.length, 4);
    assert.equal(f.deliveries.length, 2);
  }
});

test('ordinary author full regression authenticates exact PR linkage, full receipt, and source independently of synthetic workflow head', async () => {
  const f = fixture({author: true, streaming: true});
  f.run.conclusion = 'failure'; // An unrelated shard cannot invalidate this completed full producer.
  const result = await f.load();
  assert.deepEqual(result.report, f.report);
  assert.equal(result.origin.workflow_path, '.github/workflows/merge-integration-checks.yml');
  assert.equal(result.origin.event, 'pull_request');
  assert.equal(result.origin.pull_request, 1808);
  assert.equal(result.origin.head, expectedHead);
  assert.equal(result.origin.workflow_head, workflowHead);
  assert.notEqual(result.origin.head, result.origin.workflow_head);
  assert.equal(result.origin.artifact_name, `native-built-output-regression-1808-${expectedHead}`);
  assert.equal(result.origin.use, 'full-output-comparison-only');
});

test('author producer rejects mismatched PR/head/repository, metadata jobs, skipped full steps and replayed receipts', async () => {
  const changes = [
    f => f.run.event = 'pull_request_target',
    f => f.run.path = '.github/workflows/worker-merge.yml',
    f => f.run.pull_requests = [],
    f => f.run.pull_requests.push({...f.run.pull_requests[0]}),
    f => f.run.pull_requests[0].number = 1809,
    f => f.run.pull_requests[0].head.sha = workflowHead,
    f => f.run.pull_requests[0].head.ref = 'other-branch',
    f => f.run.pull_requests[0].head.repo.url = 'https://api.github.com/repos/fork/WorldAtlas',
    f => f.run.pull_requests[0].base.repo.url = 'https://api.github.com/repos/other/WorldAtlas',
    f => f.run.pull_requests[0].base.ref = 'other-base',
    f => f.run.pull_requests[0].base.sha = 'unbound-base',
    f => f.job.name = 'package',
    f => f.job.name = 'regression (1)',
    f => f.job.name = 'selected-package-assembly',
    f => f.job.conclusion = 'skipped',
    f => f.job.steps = [{name: 'Use full-regression package verification', number: 1, status: 'completed', conclusion: 'success'}],
    ...authorSteps.map(name => f => f.job.steps.find(row => row.name === name).conclusion = 'skipped'),
    ...authorSteps.map(name => f => f.job.steps = f.job.steps.filter(row => row.name !== name)),
    f => f.job.steps[4].number = 1,
    f => f.job.steps.push({...f.job.steps[1]}),
    f => f.artifact.name = `native-built-output-regression-1809-${expectedHead}`,
    f => f.artifact.name = `native-built-output-regression-1808-${workflowHead}`,
    f => f.artifact.name = 'native-built-output-12345678-1234-1234-1234-123456789abc',
    f => { const original = f.log; f.log = () => original().replace(authorReceipt, 'Reused earlier package metadata.'); },
    f => { const original = f.log; f.log = () => original() + '\n' + authorReceipt; }
  ];
  for (let index = 0; index < changes.length; index++) {
    const f = fixture({author: true}); changes[index](f);
    await assert.rejects(f.load, undefined, 'Adverse author producer case ' + index);
  }
});

test('author full-output proof preserves complete archive, report-head and digest controls', async () => {
  await assert.rejects(fixture({author: true, smoke: true}).load, /Native archive inventory differs/);
  await assert.rejects(fixture({author: true, reportChange: report => report.head = workflowHead}).load);
  await assert.rejects(fixture({author: true, archiveChange: archive => Buffer.concat([archive, Buffer.from('extra')])}).load);
  const f = fixture({author: true}); f.receipt.sha256 = 'f'.repeat(64);
  await assert.rejects(f.load);
});

test('Actions-style streaming ZIP data descriptors and ZIP64 member descriptors are accepted', async () => {
  for (const forceZip64 of [false, true]) {
    const f = fixture({streaming: true, forceZip64});
    assert.deepEqual((await f.load()).report, f.report);
  }
});

test('completed integration remains valid when a later aggregate queue job fails', async () => {
  const f = fixture(); f.run.conclusion = 'failure';
  assert.equal((await f.load()).origin.job_id, 29);
});

test('run, attempt, exact successful producer steps and artifact identity fail independently', async () => {
  const changes = [
    f => f.run.id = 18, f => f.run.run_attempt = 3,
    f => f.run.head_branch = 'feature', f => f.run.event = 'pull_request',
    f => f.run.path = '.github/workflows/merge-integration-checks.yml',
    f => f.run.repository.full_name = 'other/repo', f => f.run.head_repository.full_name = 'fork/repo',
    f => f.run.status = 'in_progress', f => f.inventory.total_count = 3,
    f => { f.inventory.jobs[1] = {...f.job, id: 31}; },
    f => f.job.run_attempt = 1, f => f.job.run_id = 18,
    f => f.job.head_sha = expectedHead, f => f.job.conclusion = 'failure',
    ...producerSteps.map(name => f => f.job.steps.find(row => row.name === name).conclusion = 'skipped'),
    f => f.job.steps.push({...f.job.steps[0]}), f => f.job.steps[2].number = 1,
    f => f.artifact.expired = true, f => f.artifact.workflow_run.id = 18,
    f => f.artifact.workflow_run.head_sha = expectedHead,
    f => f.artifact.digest = 'sha256:' + 'f'.repeat(64)
  ];
  for (let index = 0; index < changes.length; index++) {
    const f = fixture(); changes[index](f);
    await assert.rejects(f.load, undefined, 'Adverse identity case ' + index);
  }
});

test('actual report/upload receipts, digest and whole archive transport fail independently', async () => {
  const changes = [
    f => f.receipt.bytes++, f => f.receipt.sha256 = 'f'.repeat(64),
    f => f.receipt.built_output_readback = '/home/runner/.cache/other.json',
    f => f.receipt.built_output_readback = '/home/../.cache/native-normal-built-output.json',
    f => { const log = f.log; f.log = () => log() + '\n' + log(); },
    f => { const log = f.log; f.log = () => log().replace('Artifact ID is 41', 'Artifact ID is 42'); },
    f => { const log = f.log; f.log = () => log().replace('SHA256 digest of uploaded artifact zip is ' + f.artifact.digest.slice(7), 'missing digest'); },
    f => { const log = f.log; f.log = () => log() + '\nSHA256 digest of uploaded artifact zip is ' + f.artifact.digest.slice(7); },
    f => f.archive = Buffer.concat([f.archive, Buffer.from('extra')]),
    f => f.archive = f.archive.subarray(0, f.archive.length - 1),
    f => { f.archive = Buffer.from(f.archive); f.archive[40] ^= 1; },
    f => f.logLocation = 'https://attacker.invalid/job-log',
    f => f.artifactLocation = 'https://fixture.blob.core.windows.net.attacker.invalid/archive',
    f => f.artifactLocation = 'https://name:secret@fixture.blob.core.windows.net/archive',
    f => f.artifactLocation = 'http://fixture.blob.core.windows.net/archive'
  ];
  for (let index = 0; index < changes.length; index++) {
    const f = fixture(); changes[index](f);
    await assert.rejects(f.load, undefined, 'Adverse receipt/delivery case ' + index);
  }
});

test('authenticated archives still reject extra, duplicate, linked, unsupported and missing members', async () => {
  const changes = [
    entries => [...entries, entry('extra.json', '{}')],
    entries => [entries[0], entries[0]],
    entries => [entry('../native-normal-built-output.json', '{}')],
    entries => [entry('native-normal-built-output.json', 'elsewhere', {mode: 0o120777})],
    entries => [entry('native-normal-built-output.json/', '{}', {mode: 0o040755})],
    entries => [entries[1]],
    entries => [{...entries[0], compression: 12}],
    entries => [entry('native-normal-built-output.json', '{}')]
  ];
  for (let index = 0; index < changes.length; index++) {
    const f = fixture({zipChange: changes[index]});
    await assert.rejects(f.load, undefined, 'Adverse archive case ' + index);
  }
});

test('fully authenticated ZIPs reject hidden local members, prefixes, trailing bytes and corrupt optional smoke', async () => {
  const hiddenLocalMember = archive => {
    const eocd = archive.length - 22;
    const centralOffset = archive.readUInt32LE(eocd + 16);
    let offset = centralOffset;
    const records = [];
    while (offset < eocd) {
      const size = 46 + archive.readUInt16LE(offset + 28) + archive.readUInt16LE(offset + 30) + archive.readUInt16LE(offset + 32);
      records.push(archive.subarray(offset, offset + size)); offset += size;
    }
    const kept = records.slice(0, -1), central = Buffer.concat(kept), tail = Buffer.from(archive.subarray(eocd));
    tail.writeUInt16LE(kept.length, 8); tail.writeUInt16LE(kept.length, 10); tail.writeUInt32LE(central.length, 12);
    return Buffer.concat([archive.subarray(0, centralOffset), central, tail]);
  };
  const cases = [
    {archiveChange: archive => Buffer.concat([archive, Buffer.from('trailing')])},
    {archiveChange: archive => Buffer.concat([Buffer.from('prefix'), archive])},
    {zipChange: entries => [...entries, entry('unlisted-secret', 'hidden payload')], archiveChange: hiddenLocalMember},
    {archiveChange: archive => {
      const changed = Buffer.from(archive), marker = Buffer.from('selected-delivery-smoke.json');
      const name = changed.indexOf(marker); const body = name + marker.length;
      changed[body] ^= 128; return changed;
    }}
  ];
  for (const options of cases) await assert.rejects(fixture(options).load);
});

test('fully rehashed reports reject missing context, candidate mismatch and malformed exhaustive inventories', async () => {
  const changes = [
    r => r.kind = 'original-cloudflare-package-output', r => r.head = workflowHead,
    r => delete r.nativeContextInputStage, r => r.nativeContextInputStage.current_execution.source_head = workflowHead,
    r => r.nativeContextInputStage.current_execution.full_code_closure = [],
    r => r.static_assets.files.pop(), r => r.static_assets.bytes++, r => r.static_assets.count++,
    r => r.static_assets.files[0].path = '../escape', r => r.static_assets.files[0].bytes = -1,
    r => r.static_assets.files[0].sha256 = 'not-a-digest',
    r => r.static_assets.files[1].path = r.static_assets.files[0].path,
    r => r.worker_bundle_files = [], r => r.worker_bundle_files[1].path = 'missing-config.json',
    r => r.worker_bundle_files.push({...r.worker_bundle_files[0], path: 'index.js/nested'})
  ];
  for (let index = 0; index < changes.length; index++) {
    const f = fixture({reportChange: changes[index]});
    await assert.rejects(f.load, undefined, 'Adverse report case ' + index);
  }
});

test('output byte counts are observation, not an invented small package cap', async () => {
  const f = fixture({reportChange: r => {
    r.static_assets.files[1].bytes = 40 * 1024 ** 3;
    r.static_assets.bytes = r.static_assets.files.reduce((sum, pin) => sum + pin.bytes, 0);
  }});
  assert.ok((await f.load()).report.static_assets.bytes > 32 * 1048576);
});

test('temporary extraction cleans up on success and failure and subprocess inherits no token variables', async () => {
  const entries = () => fs.readdirSync(os.tmpdir()).filter(name => name.startsWith('worldatlas-readback-')).sort();
  const before = entries();
  await fixture().load();
  await assert.rejects(fixture({zipChange: entries => [entries[1]]}).load);
  assert.deepEqual(entries(), before);
  const source = fs.readFileSync(new URL('../scripts/selected-package-readback-proof.mjs', import.meta.url), 'utf8');
  assert.match(source, /env: \{PATH: '\/usr\/bin:\/bin', LANG: 'C.UTF-8'\}/);
  assert.doesNotMatch(source, /env:\s*\{\s*\.\.\.process\.env/);
  assert.ok(source.includes("execFileSync('python3', ['-I', '-S', '-B'"));
});
