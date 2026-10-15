import test from 'node:test';
import assert from 'node:assert/strict';
import {deflateRawSync, crc32} from 'node:zlib';
import {githubAPI} from '../scripts/issue-claim-contract.mjs';
import {requestAccounting} from '../scripts/github-quota.mjs';
import {completeIntegration, prepareIntegration} from '../scripts/merge-integration.mjs';
import fs from 'node:fs';
import {readReportArchive, loadGeographicReport, reportHash, validateGeographyOrigin, validatePRGeographyCandidate,
  readGeographyJobReceipt, validateGeographyProof, geographicReportProducts, checkGeographicReport,
  preparedQueueSource} from '../scripts/geographic-report-artifact.mjs';

// Real single-file ZIP records, with both archive formats used by uploaders.
function archive(raw, {method = 8, descriptor = false, name = 'geography-check.json', attributes = 0} = {}) {
  const filename = Buffer.from(name), packed = method === 8 ? deflateRawSync(raw) : raw;
  const crc = crc32(raw), flags = descriptor ? 8 : 0;
  const local = Buffer.alloc(30); local.writeUInt32LE(0x04034b50); local.writeUInt16LE(20, 4);
  local.writeUInt16LE(flags, 6); local.writeUInt16LE(method, 8); local.writeUInt16LE(filename.length, 26);
  if (!descriptor) { local.writeUInt32LE(crc, 14); local.writeUInt32LE(packed.length, 18); local.writeUInt32LE(raw.length, 22); }
  const data = descriptor ? Buffer.alloc(16) : Buffer.alloc(0);
  if (descriptor) { data.writeUInt32LE(0x08074b50); data.writeUInt32LE(crc, 4); data.writeUInt32LE(packed.length, 8); data.writeUInt32LE(raw.length, 12); }
  const central = Buffer.alloc(46); central.writeUInt32LE(0x02014b50); central.writeUInt16LE(0x0314, 4);
  central.writeUInt16LE(20, 6); central.writeUInt16LE(flags, 8); central.writeUInt16LE(method, 10);
  central.writeUInt32LE(crc, 16); central.writeUInt32LE(packed.length, 20); central.writeUInt32LE(raw.length, 24);
  central.writeUInt16LE(filename.length, 28); central.writeUInt32LE(attributes, 38);
  const end = Buffer.alloc(22); end.writeUInt32LE(0x06054b50); end.writeUInt16LE(1, 8); end.writeUInt16LE(1, 10);
  end.writeUInt32LE(46 + filename.length, 12); end.writeUInt32LE(local.length + filename.length + packed.length + data.length, 16);
  return Buffer.concat([local, filename, packed, data, central, filename, end]);
}
const report = Buffer.from(JSON.stringify({version: 1, status: 'not-applicable'}) + '\n');
const digest = reportHash(report);
for (const method of [0, 8]) for (const descriptor of [false, true]) test(`actual ZIP records: method ${method}, descriptor ${descriptor}`, () => {
  assert.deepEqual(readReportArchive(archive(report, {method, descriptor}), digest), JSON.parse(report));
});
test('different valid report bytes cannot impersonate trusted job output', () => {
  assert.throws(() => readReportArchive(archive(Buffer.from('{}')), digest), /trusted geography job digest/);
});
test('path traversal, alternate names, symlinks and directories are rejected without extraction', () => {
  for (const options of [{name: '../scripts/merge-integration.mjs'}, {name: 'another.json'},
    {attributes: (0xa000 << 16) >>> 0}, {attributes: 0x10}]) {
    assert.throws(() => readReportArchive(archive(report, options), digest));
  }
});
test('corrupt CRC, inconsistent directory, missing data and multiple entries fail closed', () => {
  for (const mutate of [raw => raw.writeUInt16LE(2, raw.length - 12),
    raw => raw.writeUInt32LE(0, raw.length - 6), raw => raw.writeUInt32LE(0, 14),
    raw => raw.writeUInt32LE(0, raw.readUInt32LE(raw.length - 6) + 16)]) {
    const raw = archive(report); mutate(raw); assert.throws(() => readReportArchive(raw, digest));
  }
  assert.throws(() => readReportArchive(archive(report).subarray(1), digest));
});
test('inflation is bounded even when claimed uncompressed size is small', () => {
  const raw = archive(Buffer.alloc(33 * 1024 * 1024));
  const central = raw.readUInt32LE(raw.length - 6);
  raw.writeUInt32LE(10, 22); raw.writeUInt32LE(10, central + 24);
  assert.throws(() => readReportArchive(raw, digest));
});
function transport(overrides = {}) {
  const calls = [], artifact = {id: 12, name: 'geography-1234567890123456-1', expired: false, size_in_bytes: 300};
  const options = {repo: 'owner/repo', runId: '123', artifactName: artifact.name, expectedHash: digest, token: 'synthetic-token',
    api: async route => { calls.push(route); return {total_count: 1, artifacts: [artifact]}; },
    fetchImpl: async (url, init) => {
      calls.push({url, init});
      if (url.startsWith('https://api.github.com/')) return new Response(null, {status: 302, headers: {location: 'https://results.blob.core.windows.net/artifact?signature=fixture'}});
      return new Response(archive(report));
    }, ...overrides};
  return {options, calls, artifact};
}
test('bounded actual ZIP download authenticates only fixed API host, retains exact report digest', async () => {
  const f = transport(); assert.deepEqual(await loadGeographicReport(f.options), JSON.parse(report));
  assert.equal(f.calls[1].init.headers.Authorization, 'Bearer synthetic-token');
  assert.equal(f.calls[2].init.headers, undefined); assert.equal(f.calls[2].init.redirect, 'error');
});
test('missing trusted digest and poisoned same-name artifact are blocked', async () => {
  const a = transport({expectedHash: undefined}); await assert.rejects(loadGeographicReport(a.options), /trusted geographic artifact outputs/);
  const b = transport(); const original = b.options.fetchImpl;
  b.options.fetchImpl = async (url, init) => url.startsWith('https://api.github.com/') ? original(url, init) : new Response(archive(Buffer.from('{}')));
  await assert.rejects(loadGeographicReport(b.options), /trusted geography job digest/);
});
test('duplicate, expired and incomplete artifact inventories are blocked', async () => {
  for (const kind of ['duplicate', 'expired', 'incomplete']) {
    const f = transport();
    if (kind === 'expired') f.artifact.expired = true;
    else f.options.api = async () => ({total_count: 2, artifacts: kind === 'duplicate' ? [f.artifact, f.artifact] : [f.artifact]});
    await assert.rejects(loadGeographicReport(f.options)); assert.equal(f.calls.filter(call => typeof call === 'object').length, 0);
  }
});
test('foreign or credential-bearing delivery addresses never receive a fetch', async () => {
  for (const location of ['https://attacker.example/a?secret=x', 'http://results.blob.core.windows.net/a', 'https://u:p@results.blob.core.windows.net/a']) {
    const f = transport({fetchImpl: async () => new Response(null, {status: 302, headers: {location}})});
    await assert.rejects(loadGeographicReport(f.options), /delivery host/);
  }
});

test('real shared client accounts inventory and redirect, signed delivery remains token-free', async () => {
  const f = transport(), accounting = requestAccounting('geographic-download'), requests = [];
  const api = githubAPI(f.options.token, {onRequest: accounting.observe, fetchImpl: async (url, init) => {
    requests.push({url, init});
    if (url.includes('/actions/runs/')) return Response.json({total_count: 1, artifacts: [f.artifact]});
    return new Response(null, {status: 302, headers: {location: 'https://results.blob.core.windows.net/a?signature=private-secret'}});
  }});
  const delivery = [];
  const result = await loadGeographicReport({...f.options, api, fetchImpl: async (url, init) => {
    delivery.push({url, init}); return new Response(archive(report));
  }});
  assert.deepEqual(result, JSON.parse(report)); assert.equal(requests.length, 2);
  assert.equal(accounting.receipt().actual_http_attempts, 2);
  assert.equal(delivery.length, 1); assert.equal(delivery[0].init.headers, undefined);
  assert(!JSON.stringify(accounting.receipt()).includes('private-secret'));
});
test('shared admission refusal stops artifact download before credential-free delivery', async () => {
  const f = transport(); let delivery = false;
  const api = githubAPI(f.options.token, {fetchImpl: async () => Response.json({total_count: 1, artifacts: [f.artifact]})});
  let budget = 1;
  api.setHTTPAdmission(() => {if (!budget--) throw Error('shared admission refused');});
  await assert.rejects(loadGeographicReport({...f.options, api, fetchImpl: async () => {delivery = true; return new Response(archive(report));}}), /shared admission refused/);
  assert.equal(delivery, false);
});

function originalTransport() {
  const zip = archive(report), name = 'proposed-geography-2-1', requests = [], deliveries = [];
  const artifact = {id: 12, name, expired: false, size_in_bytes: zip.length,
    digest: `sha256:${reportHash(zip)}`, workflow_run: {id: 123, head_sha: 'b'.repeat(40)}};
  const log = Buffer.from([
    JSON.stringify({status: 'not-applicable', regressions: null, report_bytes: report.length, report_sha256: digest}),
    `SHA256 digest of uploaded artifact zip is ${reportHash(zip)}`,
    `Artifact ${name} has been successfully uploaded! Final size is ${zip.length} bytes. Artifact ID is 12`
  ].map(line => `2026-10-10T23:11:37.4984934Z ${line}`).join('\n'));
  const f = {zip, log, artifact, requests, deliveries};
  const accounting = requestAccounting('original-geography');
  const api = githubAPI('synthetic-token', {onRequest: accounting.observe, fetchImpl: async (url, init) => {
    requests.push({url, init});
    if (url.includes('/artifacts?')) return Response.json({total_count: 1, artifacts: [f.artifact]});
    return new Response(null, {status: 302, headers: {
      location: `https://results.blob.core.windows.net/${url.endsWith('/logs') ? 'log' : 'zip'}?signature=private-secret`
    }});
  }});
  f.options = {api, repo: 'owner/repo', number: 2, head: 'b'.repeat(40), baseline: 'c'.repeat(40), token: 'synthetic-token',
    proof: {run_id: 123, run_attempt: 1, tree: 'a'.repeat(40), geography_job_id: 55},
    fetchImpl: async (url, init) => {
      deliveries.push({url, init}); return new Response(url.includes('/log?') ? f.log : f.zip);
    }};
  f.source = validateGeographyProof({run_id: 123, run_attempt: 1, job_id: 55,
    tree: f.options.proof.tree, head: f.options.head, baseline: f.options.baseline,
    workflow_path: '.github/workflows/merge-integration-checks.yml', event: 'pull_request',
    workflow_head: f.options.head, candidate_commit: f.options.head,
    ...readGeographyJobReceipt(log, name)});
  f.loadOptions = {api, repo: f.options.repo, runId: 123, artifactName: name,
    expectedHash: digest, source: f.source, token: f.options.token, fetchImpl: f.options.fetchImpl};
  f.accounting = accounting;
  return f;
}

test('accepted original source binds the exact archive and raw report without relabeling', async () => {
  const f = originalTransport(), result = await loadGeographicReport(f.loadOptions);
  assert.deepEqual(result, JSON.parse(report));
  assert.deepEqual(geographicReportProducts(result).source, f.source);
  assert.equal(f.source.job_id, 55); assert.equal(f.source.run_id, 123);
  assert.equal(f.source.head, 'b'.repeat(40)); assert.equal(f.source.baseline, 'c'.repeat(40));
  assert.equal(f.source.artifact_id, 12); assert.equal(f.source.report_bytes, report.length);
  assert.equal(f.accounting.receipt().actual_http_attempts, 2);
  assert(f.requests.every(row => row.init.headers.Authorization === 'Bearer synthetic-token'));
  assert(f.deliveries.every(row => row.init.headers === undefined && row.init.redirect === 'error'));
  assert(!JSON.stringify(f.accounting.receipt()).includes('private-secret'));
});

test('original job receipt rejects ambiguity, malformed counts and missing upload identity', () => {
  const f = originalTransport(), name = f.artifact.name;
  assert.equal(readGeographyJobReceipt(f.log, name).artifact_id, 12);
  for (const raw of [Buffer.concat([f.log, Buffer.from('\n'), f.log]),
    Buffer.from(f.log.toString().replace('"report_bytes":' + report.length, '"report_bytes":0')),
    Buffer.from(f.log.toString().replace('Artifact ID is 12', 'Artifact ID is 0')),
    Buffer.from(f.log.toString().replace(name, 'proposed-geography-3-1')),
    Buffer.alloc(2 * 1024 * 1024 + 1)]) assert.throws(() => readGeographyJobReceipt(raw, name));
});

test('pinned source refuses overwritten, foreign, expired and tampered original artifacts', async () => {
  for (const mutate of [
    f => {f.artifact.id++;}, f => {f.artifact.expired = true;},
    f => {f.artifact.workflow_run.id++;}, f => {f.artifact.workflow_run.head_sha = 'd'.repeat(40);},
    f => {f.artifact.digest = 'sha256:' + 'f'.repeat(64);}, f => {f.artifact.size_in_bytes++;},
    f => {f.zip = archive(Buffer.from('{}'));},
  ]) {
    const f = originalTransport(); mutate(f); await assert.rejects(loadGeographicReport({...f.loadOptions, fetchImpl: f.options.fetchImpl}));
  }
  const f = originalTransport(), source = f.source;
  assert.throws(() => validateGeographyProof({...source, job_id: -1}));
  assert.throws(() => validateGeographyProof({...source, extra: 'untrusted'}));
  await assert.rejects(loadGeographicReport({...f.options, runId: 124, artifactName: source.artifact_name,
    expectedHash: source.report_sha256, source}), /outputs changed/);
});

test('job-log capability retains shared admission and refuses arbitrary redirect routes', async () => {
  const f = originalTransport(); let delivered = false;
  f.options.api.setHTTPAdmission(() => {throw Error('shared admission refused');});
  await assert.rejects(f.options.api.jobLogRedirect('/repos/owner/repo/actions/jobs/55/logs'), /shared admission refused/);
  assert.equal(delivered, false); assert.equal(f.requests.length, 0);
  assert.throws(() => f.options.api.jobLogRedirect('/repos/owner/repo/issues/2'), /job log redirect route/);
});

// Verbatim receipt lines from successful job 114478521619 (run 38142298387,
// attempt 1). Job 114483839359, exposed by attempt 2 after failed-job-only retry,
// returned the byte-identical complete log. No geographic experiment is rerun.
const retained1726Receipt = Buffer.from(`2026-10-11T13:28:18.8017747Z {"status": "not-applicable", "regressions": null, "report_bytes": 274717, "report_sha256": "00ba911099849b347811c5dabc4b79f3e797a4ec25ab7fce81b0439260555cb7"}
2026-10-11T13:28:19.2767025Z SHA256 digest of uploaded artifact zip is 799a31398a52ae11c73c8646337aa0c02e810d175fc8c69741d868a24db1381e
2026-10-11T13:28:19.4818073Z Artifact proposed-geography-1726-1 has been successfully uploaded! Final size is 39994 bytes. Artifact ID is 11703004023`);
test('retained failed-job-only retry log keeps its exact origin instead of relabeling attempt two', () => {
  assert.throws(() => readGeographyJobReceipt(retained1726Receipt, 'proposed-geography-1726-2'), /receipt/);
  assert.deepEqual(readGeographyJobReceipt(retained1726Receipt, 'proposed-geography-1726-1'), {
    artifact_name: 'proposed-geography-1726-1', artifact_id: 11703004023, artifact_bytes: 39994,
    artifact_digest: '799a31398a52ae11c73c8646337aa0c02e810d175fc8c69741d868a24db1381e',
    report_sha256: '00ba911099849b347811c5dabc4b79f3e797a4ec25ab7fce81b0439260555cb7', report_bytes: 274717
  });
  for (const raw of [Buffer.from(retained1726Receipt.toString().replace('proposed-geography-1726-1', 'proposed-geography-1726-3')),
    Buffer.from(retained1726Receipt.toString().replace('proposed-geography-1726-1', 'proposed-geography-1727-1')),
    Buffer.from(retained1726Receipt.toString().split('\n').slice(0, 2).join('\n')),
    Buffer.concat([retained1726Receipt, Buffer.from('\nArtifact proposed-geography-1726-2 has been successfully uploaded! Final size is 39994 bytes. Artifact ID is 99')]),
    Buffer.concat([retained1726Receipt, Buffer.from('\nArtifact proposed-geography-1727-1 has been successfully uploaded! Final size is 39994 bytes. Artifact ID is 99')])])
    assert.throws(() => readGeographyJobReceipt(raw, 'proposed-geography-1726-1'), /receipt/);
});

function carriedTransport() {
  const f = originalTransport(), original = f.options.api;
  f.source = {...f.source, current_run_attempt: 2, current_job_id: 66};
  f.run = {id: 123, run_attempt: 1, head_sha: f.options.head, event: 'pull_request',
    path: '.github/workflows/merge-integration-checks.yml', repository: {full_name: 'owner/repo'},
    head_repository: {full_name: 'owner/repo'}, status: 'completed', conclusion: 'failure',
    pull_requests: [{number: 2, head: {sha: f.options.head}}]};
  f.jobs = [{id: 55, run_id: 123, run_attempt: 1, head_sha: f.options.head, name: 'geography',
    status: 'completed', conclusion: 'success', steps: ['Checkout trusted geographic checker', 'Install trusted geographic dependencies',
      'Check proposed geography with trusted baseline code', 'Run actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02']
      .map(name => ({name, status: 'completed', conclusion: 'success'}))}];
  f.metadata = [];
  f.options.api = async (...args) => {
    const [route] = args; f.metadata.push(route);
    if (route.endsWith('/attempts/1')) return structuredClone(f.run);
    if (route.includes('/attempts/1/jobs')) return {jobs: structuredClone(f.jobs)};
    return original(...args);
  };
  f.options.api.artifactRedirect = original.artifactRedirect;
  f.options.api.jobLogRedirect = async route => {
    f.metadata.push(route);
    return new Response(null, {status: 302, headers: {location: `https://results.blob.core.windows.net/${route.includes('/55/') ? 'origin-log' : 'log'}?fixture`}});
  };
  const fetch = f.options.fetchImpl;
  f.options.fetchImpl = async (url, init) => url.includes('/origin-log?') ? new Response(f.originLog ?? f.log) : fetch(url, init);
  return f;
}
test('accepted carried geography authenticates its exact successful original producer', async () => {
  const f = carriedTransport();
  await validateGeographyOrigin({...f.options, source: f.source});
  const result = await loadGeographicReport({...f.loadOptions, api: f.options.api, source: f.source});
  assert.equal(f.source.run_attempt, 1); assert.equal(f.source.job_id, 55);
  assert.equal(f.source.current_run_attempt, 2); assert.equal(f.source.current_job_id, 66);
  assert.equal(f.source.artifact_name, 'proposed-geography-2-1');
  assert.deepEqual(result, JSON.parse(report));
  assert.equal(f.metadata.filter(x => x.endsWith('/attempts/1')).length, 1);
  assert.equal(f.metadata.filter(x => x.includes('/attempts/1/jobs')).length, 1);
  assert(!f.metadata.some(x => /attempts\/(?:0|2|3)\//.test(x)));
});
test('accepted original run and successful job metadata cannot be substituted', async () => {
  for (const mutate of [
    f => {f.run.id++;}, f => {f.run.run_attempt++;}, f => {f.run.head_sha = 'f'.repeat(40);},
    f => {f.run.repository.full_name = 'foreign/repo';}, f => {f.run.head_repository.full_name = 'foreign/repo';},
    f => {f.run.event = 'push';}, f => {f.run.path = '.github/workflows/other.yml';},
    f => {f.run.pull_requests[0].head.sha = 'f'.repeat(40);}, f => {f.run.pull_requests[0].number++;},
    f => {f.run.status = 'in_progress';}, f => {delete f.run.pull_requests;},
    f => {f.jobs[0].id++;}, f => {f.jobs[0].run_id++;}, f => {f.jobs[0].run_attempt++;}, f => {f.jobs[0].head_sha = 'f'.repeat(40);},
    f => {f.jobs[0].conclusion = 'failure';}, f => {f.jobs[0].status = 'in_progress';},
    f => {f.jobs[0].conclusion = 'skipped';}, f => {f.jobs[0].conclusion = 'cancelled';}, f => {f.jobs.push(structuredClone(f.jobs[0]));},
    f => {f.jobs = [];}
  ]) {
    const f = carriedTransport(); mutate(f);
    await assert.rejects(validateGeographyOrigin({...f.options, source: f.source}));
    assert(!f.metadata.some(x => x.includes('/artifacts?')), 'reject before artifact discovery');
  }
});
test('completed cancelled origin retains its actually successful geography without historical PR links', async () => {
  const f = carriedTransport(); f.run.conclusion = 'cancelled'; f.run.pull_requests = [];
  await validateGeographyOrigin({...f.options, source: f.source});
  assert.equal(f.source.run_attempt, 1); assert.equal(f.source.job_id, 55);
});

function combinedTransport(changeReport = value => value) {
  const f = originalTransport(), candidate = 'd'.repeat(40);
  const body = Buffer.from(JSON.stringify(changeReport({version: 1, method_id: 'worldatlas-trusted-geography-check-v1',
    baseline_commit: f.options.baseline, trusted_code_commit: f.options.baseline, candidate_commit: candidate,
    candidate_code_executed: false, published: false, source_approval: false, gate_status: 'passed', status: 'not-applicable'})));
  f.zip = archive(body); f.artifact.size_in_bytes = f.zip.length; f.artifact.digest = `sha256:${reportHash(f.zip)}`;
  f.log = Buffer.from([JSON.stringify({status: 'not-applicable', regressions: null,
    candidate_commit: candidate, report_bytes: body.length, report_sha256: reportHash(body)}),
    `SHA256 digest of uploaded artifact zip is ${reportHash(f.zip)}`,
    `Artifact ${f.artifact.name} has been successfully uploaded! Final size is ${f.zip.length} bytes. Artifact ID is 12`].join('\n'));
  f.commit = {sha: candidate, tree: {sha: f.options.proof.tree}, parents: [{sha: f.options.baseline}, {sha: f.options.head}]};
  const original = f.options.api;
  f.options.api = async route => route.endsWith(`/git/commits/${candidate}`) ? structuredClone(f.commit) : original(route);
  f.options.api.jobLogRedirect = original.jobLogRedirect;
  f.options.api.artifactRedirect = original.artifactRedirect;
  f.source = {...f.source, ...readGeographyJobReceipt(f.log, f.artifact.name)};
  f.loadOptions = {...f.loadOptions, api: f.options.api, source: f.source,
    expectedHash: f.source.report_sha256};
  return f;
}
test('retained combined candidate keeps exact reviewed head, parents and source tree', async () => {
  const f = combinedTransport();
  await validatePRGeographyCandidate({...f.options, source: f.source});
  const result = await loadGeographicReport(f.loadOptions);
  checkGeographicReport(result, f.options.baseline, f.commit.sha);
  assert.equal(f.source.candidate_commit, f.commit.sha);
  assert.equal(result.candidate_commit, f.commit.sha);
  assert.equal(f.source.head, f.options.head);
  assert.equal(f.source.workflow_head, f.options.head);
  assert.equal(f.source.tree, f.commit.tree.sha);
  assert.equal(f.source.baseline, f.options.baseline);
  assert.notEqual(f.source.head, f.source.candidate_commit);
});
test('retained combined geography rejects foreign tree, stale parents and relabeled report', async () => {
  for (const mutate of [f => {f.commit.sha = 'e'.repeat(40);}, f => {f.commit.tree.sha = 'e'.repeat(40);},
    f => {f.commit.parents.reverse();}, f => {f.commit.parents.pop();},
    f => {f.commit.parents[0].sha = 'e'.repeat(40);}, f => {f.commit.parents[1].sha = 'e'.repeat(40); }]) {
    const f = combinedTransport(); mutate(f);
    await assert.rejects(validatePRGeographyCandidate({...f.options, source: f.source}), /candidate parents or tree/);
    assert(!f.requests.some(row => row.url.includes('/artifacts?')));
  }
  for (const key of ['baseline_commit', 'trusted_code_commit', 'candidate_commit']) {
    const f = combinedTransport(report => ({...report, [key]: 'e'.repeat(40)}));
    const result = await loadGeographicReport(f.loadOptions);
    assert.throws(() => checkGeographicReport(result, f.options.baseline, f.commit.sha), /exact trusted combined check/);
  }
  const f = combinedTransport(); f.log = Buffer.from(f.log.toString().replace('"candidate_commit":"' + f.commit.sha + '"', '"candidate_commit":"invalid"'));
  assert.throws(() => readGeographyJobReceipt(f.log, f.artifact.name), /candidate receipt/);
});
test('accepted producer ignores stale step projections while preserving actual successful job identity', async () => {
  for (const steps of [undefined, [], [{name: 'old checker label', status: 'in_progress', conclusion: null}]]) {
    const f = carriedTransport(); f.jobs[0].steps = steps;
    await validateGeographyOrigin({...f.options, source: f.source});
    assert.equal(f.source.job_id, 55); assert.equal(f.source.current_job_id, 66);
    assert.equal(f.source.run_attempt, 1); assert.equal(f.source.report_sha256, digest);
  }
});

function freshQueueTransport(changeReport) {
  const f = combinedTransport(changeReport), original = f.options.api;
  const oldName = f.artifact.name, name = 'geography-fixture-request-12345678-1';
  f.artifact.name = name;
  f.artifact.workflow_run.head_sha = 'e'.repeat(40);
  f.log = Buffer.from(f.log.toString().replace(oldName, name));
  f.run = {id: 123, run_attempt: 1, head_sha: 'e'.repeat(40), head_branch: 'main', event: 'workflow_dispatch',
    path: '.github/workflows/worker-merge.yml', repository: {full_name: 'owner/repo'},
    head_repository: {full_name: 'owner/repo'}, status: 'in_progress'};
  f.jobs = [{id: 55, run_id: 123, run_attempt: 1, head_sha: f.run.head_sha,
    name: 'geography', status: 'completed', conclusion: 'success', steps: []}];
  f.metadata = [];
  const api = async route => {
    f.metadata.push(route);
    if (route.endsWith('/attempts/1')) return structuredClone(f.run);
    if (route.includes('/attempts/1/jobs')) return {jobs: structuredClone(f.jobs)};
    return original(route);
  };
  api.jobLogRedirect = async route => {
    f.metadata.push(route);
    assert.equal(route, '/repos/owner/repo/actions/jobs/55/logs');
    return original.jobLogRedirect(route);
  };
  api.artifactRedirect = original.artifactRedirect;
  f.loadOptions = {api, repo: 'owner/repo', runId: 123, artifactName: name,
    expectedHash: JSON.parse(f.log.toString().split('\n')[0]).report_sha256,
    token: f.options.token, fetchImpl: f.options.fetchImpl,
    fresh: {run_attempt: 1, workflow_head: f.run.head_sha, head: f.options.head,
      baseline: f.options.baseline, candidate_commit: f.commit.sha, request_id: 'fixture-request-12345678'}};
  return f;
}

for (const [label, steps] of [['missing', undefined], ['empty', []], ['stale', [
  {name: 'Check exact combined geography with trusted baseline code', status: 'in_progress', conclusion: null},
  {name: 'Run actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02', status: 'pending', conclusion: null}
]], ['renamed', [{name: 'renamed checker', status: 'completed', conclusion: 'success'}]]]) {
  test(`fresh queue loader authenticates successful producer with ${label} step projection`, async () => {
    const f = freshQueueTransport(); f.jobs[0].steps = steps;
    const result = await loadGeographicReport(f.loadOptions);
    checkGeographicReport(result, f.options.baseline, f.commit.sha);
    const source = geographicReportProducts(result).source;
    assert.ok(preparedQueueSource(result));
    assert.equal(Object.isFrozen(preparedQueueSource(result)), true);
    assert.equal(Object.hasOwn(geographicReportProducts(result), 'prepared_queue'), false);
    assert.equal(source.job_id, 55); assert.equal(source.run_id, 123); assert.equal(source.run_attempt, 1);
    assert.equal(source.workflow_head, f.run.head_sha); assert.equal(source.head, f.options.head);
    assert.equal(source.tree, f.commit.tree.sha); assert.equal(source.candidate_commit, f.commit.sha);
    assert.equal(source.artifact_digest, reportHash(f.zip));
    assert(f.metadata.some(route => route.endsWith('/jobs/55/logs')));
  });
}

test('failed-job queue retry authenticates carried geography from its successful original attempt',async()=>{
  const f=freshQueueTransport();
  f.loadOptions.fresh.run_attempt=2;
  f.run.status='completed';f.run.conclusion='failure';
  const result=await loadGeographicReport(f.loadOptions);
  checkGeographicReport(result,f.options.baseline,f.commit.sha);
  const source=geographicReportProducts(result).source;
  assert.equal(source.run_attempt,1);assert.equal(source.job_id,55);
  assert(!f.metadata.some(route=>route.includes('/attempts/2')),'Do not relabel the original successful producer');
  f.jobs[0].conclusion='failure';
  await assert.rejects(loadGeographicReport(f.loadOptions),/successful|succeed/);
});

test('fresh queue loader rejects foreign or unsuccessful producers and altered receipt custody with empty steps', async () => {
  for (const mutate of [
    f => {f.run.id++;}, f => {f.run.run_attempt++;}, f => {f.run.head_sha = 'f'.repeat(40);},
    f => {f.run.path = '.github/workflows/other.yml';}, f => {f.run.event = 'push';},
    f => {f.run.head_branch = 'engineering/foreign';}, f => {delete f.run.head_branch;},
    f => {f.run.repository.full_name = 'foreign/repo';}, f => {f.run.head_repository.full_name = 'foreign/repo';},
    f => {f.jobs[0].id = 0;}, f => {f.jobs[0].run_id++;}, f => {f.jobs[0].run_attempt++;},
    f => {f.jobs[0].head_sha = 'f'.repeat(40);}, f => {f.jobs[0].status = 'in_progress';},
    ...['failure', 'cancelled', 'skipped'].map(conclusion => f => {f.jobs[0].conclusion = conclusion;}),
    f => {f.jobs.push(structuredClone(f.jobs[0]));}, f => {f.jobs = [];},
    f => {f.log = Buffer.from('no upload receipt');},
    f => {f.log = Buffer.from(f.log.toString().replace('"report_bytes":', '"report_bytes":0,"unused":'));},
    f => {f.log = Buffer.concat([f.log, Buffer.from('\n'), f.log]);},
    f => {f.log = Buffer.alloc(2 * 1024 * 1024 + 1);},
    f => {f.log = Buffer.from(f.log.toString().replace('Artifact ID is 12', 'Artifact ID is 13'));},
    f => {f.loadOptions.expectedHash = 'f'.repeat(64);},
    f => {f.artifact.workflow_run.id++;}, f => {f.artifact.workflow_run.head_sha = 'f'.repeat(40);},
    f => {f.artifact.digest = `sha256:${'f'.repeat(64)}`;},
    f => {f.zip = archive(Buffer.from('{}'));}, f => {f.commit.sha = 'f'.repeat(40);},
    f => {f.commit.tree.sha = 'invalid';}
  ]) {
    const f = freshQueueTransport(); mutate(f);
    await assert.rejects(loadGeographicReport(f.loadOptions));
  }
});

test('fresh queue authenticated report still requires exact baseline, candidate and passed scientific gate', async () => {
  for (const changeReport of [r => ({...r, baseline_commit: 'f'.repeat(40)}),
    r => ({...r, trusted_code_commit: 'f'.repeat(40)}), r => ({...r, candidate_commit: 'f'.repeat(40)}),
    r => ({...r, gate_status: 'failed'}), r => ({...r, candidate_code_executed: true})]) {
    const f = freshQueueTransport(changeReport), result = await loadGeographicReport(f.loadOptions);
    assert.throws(() => checkGeographicReport(result, f.options.baseline, f.commit.sha));
  }
});

test('actual fresh software archive binds candidate code without impersonating a baseline report', async () => {
  const f = freshQueueTransport(report => ({...report, trusted_code_commit: report.candidate_commit,
    candidate_code_executed: true, trusted_code_inventory_sha256: 'f'.repeat(64)}));
  const result = await loadGeographicReport(f.loadOptions);
  assert.equal(checkGeographicReport(result, f.options.baseline, f.commit.sha, f.commit.sha), false);
  assert.throws(() => checkGeographicReport(result, f.options.baseline, f.commit.sha), /exact trusted combined/);
  const source = geographicReportProducts(result).source;
  assert.equal(source.candidate_commit, f.commit.sha);
  assert.equal(source.report_sha256, f.loadOptions.expectedHash);
  assert.equal(source.artifact_digest, reportHash(f.zip));
});

// Reuse the actual ZIP/run/job/log producer fixture through the final merge
// boundary. The only replaced components are GitHub responses and byte delivery.
function queueCompletionFixture(f = freshQueueTransport()) {
  const {repo, head, baseline: base} = f.options, candidate = f.commit.sha;
  const root = `/repos/${repo}`, original = f.loadOptions.api;
  const integrationRequestId = 'queue-report-fixture-0001';
  const reference = `worldatlas-integration/pr-2-${integrationRequestId}`;
  f.calls = []; f.writes = []; f.preparationWrites = [];
  f.issue = {number: 1, state: 'open', created_at: '2020-01-01T00:00:00Z',
    labels: ['type:engineering', 'kind:work-item', 'status:ready'],
    body: '<!-- worldatlas-work:v1\n' + JSON.stringify({mode: 'engineering', max_prs: 1,
      depends_on: [], scope: 'Synthetic prepared queue controls'}) + '\n-->'};
  f.pr = {number: 2, state: 'open', draft: false, merged: false, body: 'Refs #1', title: 'Prepared queue control',
    changed_files: 1, head: {sha: head, ref: 'engineering/fixture', repo: {full_name: repo}},
    base: {ref: 'main', sha: base}, mergeable: true, merge_commit_sha: candidate};
  f.files = [{filename: 'src/a.js', status: 'modified'}];
  f.authored = [{path: 'src/a.js', sha: '1'.repeat(40), mode: '100644', type: 'blob'}];
  f.integrated = structuredClone(f.authored); f.baseline = [];
  f.api = async (route, method = 'GET', body) => {
    f.calls.push(route); const name = route.split('?')[0];
    if (method === 'POST' && name === root + '/git/refs') {
      assert.deepEqual(body, {ref: `refs/heads/${reference}`, sha: base});
      f.preparationWrites.push(name);
      return {ref: body.ref, object: {sha: base}};
    }
    if (method === 'POST' && name === root + '/merges') {
      assert.deepEqual(body, {base: reference, head,
        commit_message: `WorldAtlas isolated integration PR2 request ${integrationRequestId}`});
      f.preparationWrites.push(name);
      return {sha: candidate};
    }
    if (method === 'PUT') {f.writes.push(body); return {merged: true, sha: 'f'.repeat(40)};}
    if (name === root + '/pulls/2') return structuredClone(f.pr);
    if (name === root + '/issues/1') return structuredClone(f.issue);
    if (name === root + '/issues/1/timeline') return [];
    if (name === root + '/pulls/2/files') return structuredClone(f.files);
    if (name === root + '/commits/' + head + '/check-runs') return {check_runs: [
      {id: 1, name: 'scope', app: {id: 1}, status: 'completed', conclusion: f.checkConclusion ?? 'success'}]};
    if (name === root + '/commits/' + head + '/status') return f.status ?? {statuses: []};
    if (name === root + '/git/ref/heads/main') return {object: {sha: f.currentBase ?? base}};
    if (name === root + '/git/commits/' + candidate) return structuredClone(f.commit);
    if (name === root + '/git/commits/' + head) return {sha: head, tree: {sha: '2'.repeat(40)}};
    if (name === root + '/git/commits/' + base) return {sha: base, tree: {sha: '3'.repeat(40)}};
    if (name === root + '/git/trees/' + '2'.repeat(40)) return {truncated: false, tree: f.authored};
    if (name === root + '/git/trees/' + '3'.repeat(40)) return {truncated: false, tree: f.baseline};
    if (name === root + '/git/trees/' + f.commit.tree.sha) return {truncated: false, tree: f.integrated};
    return original(route, method, body);
  };
  f.api.jobLogRedirect = original.jobLogRedirect; f.api.artifactRedirect = original.artifactRedirect;
  f.mergeOptions = () => ({api: f.api, repo, number: 2, expectedHead: head, integrationRequestId,
    policy: {version: 1, mode: 'enforce-new', activation_time: '2100-01-01T00:00:00Z'},
    evidenceCheck: async () => {assert.notEqual(f.review, 'withdrawn', 'Fresh exact-head review is required'); return {status: 'legacy'};}});
  f.load = ({api = f.api} = {}) => loadGeographicReport({...f.loadOptions, api});
  f.complete = (extra = {}) => completeIntegration({...f.mergeOptions(), integrationResult: 'success', geographyResult: 'success',
    testedBase: base, testedCandidate: candidate, geographyReportLoader: f.load, ...extra});
  f.treeReads = () => f.calls.filter(route => /\/git\/trees\/.*\?recursive=1$/.test(route));
  return f;
}

test('authenticated main queue reuses successful prepared tree comparison without recursive final reads', async () => {
  const f = queueCompletionFixture();
  await prepareIntegration(f.mergeOptions());
  assert.deepEqual(f.preparationWrites, [`/repos/${f.options.repo}/git/refs`, `/repos/${f.options.repo}/merges`]);
  assert.equal(f.treeReads().length, 2, 'Preparation still compares both complete trees');
  f.calls.length = 0;
  const result = await f.complete();
  assert.equal(result.accepted, true); assert.equal(f.writes.length, 1);
  assert.deepEqual(f.treeReads(), []);
  assert(f.calls.some(route => route.endsWith('/git/commits/' + f.commit.sha)), 'Final commit identity is reread');
  assert.equal(f.metadata.filter(route => route.endsWith('/attempts/1')).length, 1, 'Fresh authentication is not duplicated');
  const workflow = fs.readFileSync('.github/workflows/worker-merge.yml', 'utf8');
  assert.match(workflow, /prepare:\n    if: github.ref == 'refs\/heads\/main'/);
  assert.match(workflow, /geography:\n    needs: prepare\n    if: needs.prepare.outputs.candidate != ''/);
  assert.match(workflow, /GEOGRAPHY_CANDIDATE: \$\{\{ needs.prepare.outputs.candidate \}\}/);
});

test('prepared queue keeps focused coordination routing through final ordinary-tree verification', async () => {
  const f = queueCompletionFixture();
  f.files = [{filename:'scripts/merge-integration.mjs',status:'modified'},
    {filename:'test/merge-integration.test.mjs',status:'modified'}];
  f.pr.changed_files = f.files.length;
  f.authored = f.files.map(file => ({path:file.filename,sha:'1'.repeat(40),mode:'100644',type:'blob'}));
  f.integrated = structuredClone(f.authored);
  const prepared = await prepareIntegration(f.mergeOptions());
  assert.equal(prepared.profile,'evidence');
  assert.equal(prepared.geography_software,false);
  f.calls.length = 0;
  const result = await f.complete();
  assert.equal(result.accepted,true);
  assert.equal(result.geography.trusted_code_commit,f.options.baseline);
  assert.deepEqual(f.treeReads(),[`/repos/owner/repo/git/trees/${'2'.repeat(40)}?recursive=1`]);
});

test('authenticated custody never substitutes for candidate identity, ordered parents or exact source bindings', async () => {
  for (const field of ['candidate_commit', 'baseline', 'head', 'tree', 'workflow_path', 'event']) {
    const f = queueCompletionFixture(), geography = await f.load();
    geographicReportProducts(geography).source[field] = field === 'workflow_path'
      ? '.github/workflows/merge-integration-checks.yml' : field === 'event' ? 'pull_request' : 'f'.repeat(40);
    await assert.rejects(f.complete({geographyReportLoader: async () => geography}), /source differs/);
    assert.equal(f.writes.length, 0, field);
  }
  for (const mutate of [f => {f.commit.sha = 'f'.repeat(40);}, f => {delete f.commit.tree;},
    f => {f.commit.parents.reverse();}, f => {f.commit.parents.pop();},
    f => {f.commit.parents[0].sha = 'f'.repeat(40);}, f => {f.commit.parents[1].sha = 'f'.repeat(40); }]) {
    const f = queueCompletionFixture(); mutate(f);
    await assert.rejects(f.complete(), /candidate identity|exact current main/);
    assert.equal(f.writes.length, 0); assert.deepEqual(f.treeReads(), []);
  }
});

test('forged metadata on plain, archive-only, historical and supplied queue reports cannot skip comparison', async () => {
  for (const kind of ['plain', 'archive-only', 'historical', 'supplied-queue']) {
    const f = queueCompletionFixture(kind === 'historical' ? combinedTransport() : freshQueueTransport());
    const fresh = await f.load(); let geography = fresh;
    if (kind === 'plain') geography = structuredClone(fresh);
    if (kind === 'archive-only') geography = readReportArchive(f.zip, f.loadOptions.expectedHash);
    if (kind === 'supplied-queue') geography = await loadGeographicReport({...f.loadOptions, api: f.api,
      fresh: undefined, source: geographicReportProducts(fresh).source});
    const products = geographicReportProducts(geography);
    if (products) products.prepared_queue = true;
    geography.prepared_queue = true;
    assert.equal(preparedQueueSource(geography), null);
    f.calls.length = 0;
    f.integrated[0].sha = 'f'.repeat(40);
    await assert.rejects(f.complete({geographyReportLoader: async () => geography}), /changes reviewed bytes/);
    assert.equal(f.treeReads().length, 2, kind); assert.equal(f.writes.length, 0, kind);
  }
});

test('replacing fresh queue product data cannot relabel private admitted custody', async () => {
  const f = queueCompletionFixture(), geography = await f.load();
  const products = geographicReportProducts(geography);
  products.source = {...products.source, workflow_head: 'f'.repeat(40)};
  products.prepared_queue = true;
  await assert.rejects(f.complete({geographyReportLoader: async () => geography}), /source differs from authenticated queue producer/);
  assert.equal(f.writes.length, 0); assert.deepEqual(f.treeReads(), []);
});

test('retargeting both genuine report and public custody cannot reuse original preparation', async () => {
  const f = queueCompletionFixture(), geography = await f.load(), retarget = 'f'.repeat(40);
  const original = f.api;
  f.api = async (route, ...args) => route.endsWith('/git/commits/' + retarget)
    ? {...structuredClone(f.commit), sha: retarget} : original(route, ...args);
  geography.candidate_commit = retarget;
  geographicReportProducts(geography).source.candidate_commit = retarget;
  await assert.rejects(f.complete({testedCandidate: retarget, geographyReportLoader: async () => geography}),
    /source differs from authenticated queue producer/);
  assert.equal(f.writes.length, 0); assert.deepEqual(f.treeReads(), []);
});

test('prepared queue still loads authored and baseline trees for selected-data classification', async () => {
  const f = queueCompletionFixture();
  f.files = [{filename: 'data/ownership-selection.json', status: 'modified'},
    {filename: 'coordination/engineering/fixture/selected-delivery-expectations.json', status: 'added'}];
  f.pr.changed_files = f.files.length;
  const result = await f.complete();
  assert.equal(result.accepted, true);
  assert.deepEqual(f.treeReads(), ['2', '3'].map(n => `/repos/owner/repo/git/trees/${n.repeat(40)}?recursive=1`));
  // The absent selected smoke keeps conservative complete validation; this test
  // establishes tree loading, not a fabricated selected-data qualification.
  assert.equal(f.writes.length, 1);
});

test('prepared custody preserves fresh final main, head, issue, check, status and review guards', async () => {
  for (const changed of ['main', 'head', 'issue', 'check', 'status', 'review']) {
    const f = queueCompletionFixture();
    const loader = async options => {
      const geography = await f.load(options);
      if (changed === 'main') f.currentBase = 'f'.repeat(40);
      if (changed === 'head') f.pr.head.sha = 'f'.repeat(40);
      if (changed === 'issue') f.issue.body += '\nChanged acceptance';
      if (changed === 'check') f.checkConclusion = 'failure';
      if (changed === 'status') f.status = {statuses: [{}], state: 'failure'};
      return geography;
    };
    if (changed === 'review') f.review = 'withdrawn';
    await assert.rejects(f.complete({geographyReportLoader: loader}));
    assert.equal(f.writes.length, 0, changed);
  }
});


test('candidate software report requires explicit expected code identity and cannot impersonate baseline proof', () => {
 const baseline = 'a'.repeat(40), candidate = 'b'.repeat(40);
 const report = {version: 1, method_id: 'worldatlas-trusted-geography-check-v1',
  baseline_commit: baseline, candidate_commit: candidate, trusted_code_commit: candidate,
  trusted_code_inventory_sha256: 'c'.repeat(64), candidate_code_executed: true,
  published: false, source_approval: false, gate_status: 'passed', status: 'not-applicable'};
 assert.equal(checkGeographicReport(report, baseline, candidate, candidate), false);
 assert.throws(() => checkGeographicReport(report, baseline, candidate), /exact trusted combined/);
 for (const mutation of [{trusted_code_commit: baseline}, {candidate_code_executed: false},
  {trusted_code_inventory_sha256: ''}, {checkpoint: {}}, {unchanged_selected_inputs: {}}, {reused_baseline_proof: {}}]) {
  assert.throws(() => checkGeographicReport({...report, ...mutation}, baseline, candidate, candidate));
 }
 const old = {...report, trusted_code_commit: baseline, candidate_code_executed: false};
 assert.equal(checkGeographicReport(old, baseline, candidate), false);
 assert.throws(() => checkGeographicReport(old, baseline, candidate, candidate));
});


test('reviewed focused test-only prepare retains final ordinary-file proof through authenticated custody', async () => {
  for(const failure of [null,'integration','geography','cancelled-geography','review']) {
    const f=queueCompletionFixture(),name='test/native-diagnostic-entry.test.mjs';
    f.files=[{filename:name,status:'modified'}];f.authored[0].path=name;f.integrated=structuredClone(f.authored);
    const prepared=await prepareIntegration(f.mergeOptions());
    assert.deepEqual(f.preparationWrites,[`/repos/${f.options.repo}/git/refs`,`/repos/${f.options.repo}/merges`]);
    assert.equal(prepared.profile,'evidence');assert.equal(prepared.geography_software,false);
    assert.equal(f.treeReads().length,2);f.calls.length=0;
    if(failure==='review')f.review='withdrawn';
    const options=failure==='integration'?{integrationResult:'failure'}:failure==='geography'?{geographyResult:'failure'}:
      failure==='cancelled-geography'?{geographyResult:'cancelled'}:{};
    if(failure) {
      await assert.rejects(f.complete(options),failure==='integration'?/Integration tests failed/:['geography','cancelled-geography'].includes(failure)?/Trusted combined geography check/:/exact-head review/);
      assert.equal(f.writes.length,0);
    } else {
      const result=await f.complete(options);assert.equal(result.accepted,true);assert.equal(f.writes.length,1);
      assert.equal(result.geography.execution,'fresh-queue');
      assert.equal(result.geography.trusted_code_commit,f.options.baseline);
      assert.equal(Object.hasOwn(result,'proof'),false);assert.equal(Object.hasOwn(result,'profile'),false);
    }
    assert.deepEqual(f.treeReads(),['integration','review'].includes(failure) ? [] : [`/repos/owner/repo/git/trees/${'2'.repeat(40)}?recursive=1`],
      'Final focused eligibility reads ordinary authored entries before accepting or refusing geography');
  }
});


test('eligible skipped geography verifies current authored and candidate trees without loading a report', async () => {
  for (const drift of [false, true]) {
    const f=queueCompletionFixture(),name='test/native-diagnostic-entry.test.mjs';
    f.files=[{filename:name,status:'modified'}];f.authored[0].path=name;f.integrated=structuredClone(f.authored);
    const prepared=await prepareIntegration(f.mergeOptions());
    assert.equal(prepared.geography_required,false);
    f.calls.length=0;
    if(drift)f.integrated[0].sha='f'.repeat(40);
    const complete=()=>f.complete({geographyResult:'skipped',geographyReportLoader:async()=>{throw Error('Skipped geography must not load a report');}});
    if(drift) {
      await assert.rejects(complete,/changes reviewed bytes/);
      assert.equal(f.writes.length,0);
    } else {
      const result=await complete();
      assert.equal(result.accepted,true);assert.equal(f.writes.length,1);
      assert.deepEqual(result.geography,{status:'not-applicable',reason:'non-geographic-controls'});
    }
    assert.deepEqual(f.treeReads(),['2'.repeat(40),f.commit.tree.sha].map(sha=>`/repos/owner/repo/git/trees/${sha}?recursive=1`),
      'A skipped job cannot substitute historical prepared custody for current ordinary-file proof');
  }
});
