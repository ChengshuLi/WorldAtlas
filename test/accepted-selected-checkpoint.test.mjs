import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {crc32, gzipSync, deflateRawSync} from 'node:zlib';
import {CHECKPOINT_MEMBERS, readReportArchive, reportHash, geographicReportProducts,
  loadGeographicReport} from '../scripts/geographic-report-artifact.mjs';
import {acquireAcceptedCheckpoint, readAcceptedCheckpoint, releaseAcceptedCheckpoint,
  retainAcceptedCheckpoint, validateAcceptedCheckpointLocator, acceptedCheckpointAPI} from '../scripts/accepted-selected-checkpoint.mjs';
import {renderWorkerResult} from '../scripts/worker-result.mjs';

// Real multi-member ZIPs, including uploader data descriptors. No extractor or
// synthetic archive-parser stub is involved in the acquisition entry point.
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
function checkpoint() {
  const bodies = CHECKPOINT_MEMBERS.map(name => [name, name.endsWith('.gz') ? gzipSync(json({member: name})) : json({member: name})]);
  const report = {version: 1, method_id: 'worldatlas-trusted-geography-check-v1', baseline_commit: baseline,
    candidate_commit: candidate, trusted_code_commit: baseline, candidate_code_executed: false,
    published: false, source_approval: false, gate_status: 'passed', status: 'no-new-regression',
    checkpoint: {version: 1, kind: 'selected-checkpoint-products-v1', members: bodies.map(([name, raw]) => ({name, bytes: raw.length,
      sha256: reportHash(raw), ...(name.endsWith('.gz') ? {decoded_bytes: json({member:name}).length, decoded_sha256: reportHash(json({member:name}))} : {})}))}};
  return {report, bodies};
}
const encode = f => ({raw: json(f.report), zip: zipMembers([['geography-check.json', json(f.report)], ...f.bodies])});

for (const descriptor of [false, true]) for (const method of [0, 8]) test(`fixed checkpoint archive preserves every byte: method ${method}, descriptor ${descriptor}`, () => {
  const f = checkpoint(), raw = json(f.report), zip = zipMembers([['geography-check.json',raw],...f.bodies],{descriptor,method});
  const observed = [];
  const report = readReportArchive(zip, reportHash(raw), raw.length, {admit: bytes => observed.push(bytes)});
  assert.deepEqual(report, f.report); const products = geographicReportProducts(report);
  for (const [name, body] of f.bodies) assert(products.members.get(name).equals(body));
  assert.equal(products.admitted_bytes, observed.at(-1)); assert(observed.at(-1) > zip.length);
});
test('legacy report-only archives retain the full original 32 MiB report bound', () => {
  const raw=Buffer.alloc(32*1024*1024,32); raw.write('{}');
  const archive=zipMembers([['geography-check.json',raw]]),charges=[];
  const report=readReportArchive(archive,reportHash(raw),raw.length,{admit:bytes=>charges.push(bytes)});
  assert.deepEqual(report,{});assert.equal(geographicReportProducts(report).members.size,0);
  assert(charges[0]>256*1024*1024); // Current caller admission still sees every representation.
});
test('root authentication precedes untrusted descriptor and checkpoint member interpretation', () => {
  const f = checkpoint(), good = encode(f); f.report.checkpoint = {malicious: true};
  const altered = encode(f);
  assert.throws(() => readReportArchive(altered.zip,reportHash(good.raw)), /trusted geography job digest/);
});
test('omitted, extra, duplicate and traversing members cannot use an authenticated descriptor', () => {
  for (const mutate of [f => f.bodies.pop(), f => f.bodies.push(['operating.json',json({})]),
    f => f.bodies.push(f.bodies[0]), f => f.bodies[0][0] = '../derived-certificate.json.gz',
    f => f.report.checkpoint.members.pop(), f => f.report.checkpoint.members[1] = f.report.checkpoint.members[0]]) {
    const f = checkpoint(); mutate(f); const {raw,zip} = encode(f);
    assert.throws(() => readReportArchive(zip,reportHash(raw)));
  }
});
test('encoded drift, refreshed candidate digests and gzip decoded lies all refuse', () => {
  for (const mutate of [f => f.bodies[1][1] = json({forged:true}),
    f => f.report.checkpoint.members[0].decoded_bytes = 1,
    f => f.report.checkpoint.members[0].decoded_sha256 = '0'.repeat(64)]) {
    const f = checkpoint(); mutate(f); const {raw,zip} = encode(f);
    assert.throws(() => readReportArchive(zip,reportHash(raw)));
  }
});
test('physical overlap, local metadata drift, links and descriptor corruption refuse', () => {
  const f = checkpoint(), raw = json(f.report);
  for (const mutate of [zip => zip.writeUInt32LE(0xa0000000,zip.readUInt32LE(zip.length - 6) + 38),
    zip => zip.writeUInt32LE(3,10), zip => zip.writeUInt32LE(1,zip.readUInt32LE(zip.length - 6) + 42),
    zip => zip.writeUInt32LE(0,zip.readUInt32LE(zip.length - 6) - 4)]) {
    const zip = zipMembers([['geography-check.json',raw],...f.bodies],{descriptor:true}); mutate(zip);
    assert.throws(() => readReportArchive(zip,reportHash(raw)));
  }
});
test('current admission refuses before product allocation and full declared union has a fixed bound', () => {
  const f = checkpoint(), {raw,zip} = encode(f); let calls = 0;
  assert.throws(() => readReportArchive(zip,reportHash(raw),raw.length,{admit: () => {calls++; throw Error('current allowance');}}), /current allowance/);
  assert.equal(calls,1);
  // Inflate claims can be small individually while the complete live decoded
  // representation is impossible. All central/local sizes agree with the root.
  for (const row of f.report.checkpoint.members) { row.bytes=32*1024*1024; if(row.decoded_bytes) row.decoded_bytes=row.bytes; }
  const hugeRoot = json(f.report), huge = zipMembers([['geography-check.json',hugeRoot],...f.bodies],{descriptor:true});
  let cursor=huge.readUInt32LE(huge.length-6);
  for(let i=0;i<8;i++) {const nameLength=huge.readUInt16LE(cursor+28); if(i) {
    huge.writeUInt32LE(32*1024*1024,cursor+24);
    const local=huge.readUInt32LE(cursor+42), start=local+30+huge.readUInt16LE(local+26), packed=huge.readUInt32LE(cursor+20);
    huge.writeUInt32LE(32*1024*1024,start+packed+12);
  } cursor+=46+nameLength;}
  assert.throws(() => readReportArchive(huge,reportHash(hugeRoot)),/combined budget/);
});

function acceptedFixture() {
  const f = checkpoint(), encoded = encode(f); Object.assign(f,encoded);
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
    if(route.endsWith('/artifacts?per_page=100&page=1')) return {total_count:1,artifacts:[f.artifact]};
    throw Error('Unexpected fixture route '+route);
  };
  api.artifactRedirect=async route => {f.calls.push(route);return new Response(null,{status:302,headers:{location:'https://fixtures.blob.core.windows.net/zip'}});};
  f.options={api,repo:'owner/repo',locator:{pr_number:7,request_id:request,head},token:'fixture',admit:bytes=>f.admitted.push(bytes),
    fetchImpl:async()=>new Response(f.zip)};
  return f;
}
test('real acquisition accepts bot/merged/tree/origin/artifact custody and mints only a private lifetime', async () => {
  const f=acceptedFixture(), result=await acquireAcceptedCheckpoint(f.options);
  assert.equal(result.available,true); const proof=readAcceptedCheckpoint(result.handle);
  assert.equal(proof.source.workflow_head,workflowHead); assert.equal(proof.source.head,head);
  assert.equal(proof.archive_origin,'actions'); assert.equal(proof.products['facts.json'].member,'facts.json');
  assert(Object.isFrozen(proof.products['facts.json'])); assert.equal(proof.admitted_bytes,f.admitted.at(-1));
  assert.throws(()=>readAcceptedCheckpoint(JSON.parse(JSON.stringify(result.handle))),/private/);
  releaseAcceptedCheckpoint(result.handle); assert.throws(()=>readAcceptedCheckpoint(result.handle),/private/);
});
test('fake bot or nonaccepted receipt produces no checkpoint authority', async () => {
  for(const mutate of [f=>f.bot='attacker',f=>f.receipt.accepted=false,f=>f.receipt.request_id='another-request-12345']) {
    const f=acceptedFixture();mutate(f);assert.equal((await acquireAcceptedCheckpoint(f.options)).available,false);
  }
});
test('actual merge, origin workflow/head/attempt, job steps, artifact identity and tree cannot be substituted', async () => {
  for(const mutate of [f=>f.pr.merged=false,f=>f.pr.head.sha=baseline,f=>f.pr.merge_commit_sha=baseline,
    f=>f.pr.number=8,f=>f.receipt.reviewed_head=baseline,f=>f.tree=baseline,
    f=>f.run.head_sha=head,f=>f.run.path='.github/workflows/merge-integration-checks.yml',
    f=>f.run.event='pull_request',f=>f.run.run_attempt=1,f=>f.job.head_sha=head,f=>f.job.id=99,
    f=>f.job.steps.push(f.job.steps[0]),f=>f.job.steps[2].conclusion='skipped',
    f=>f.artifact.id=1,f=>f.artifact.digest='sha256:'+'0'.repeat(64)]) {
    const f=acceptedFixture();mutate(f);await assert.rejects(acquireAcceptedCheckpoint(f.options));
  }
});
test('expired original is unavailable unless the exact accepted artifact is retained', async () => {
  const missing=acceptedFixture();missing.artifact.expired=true;
  assert.equal((await acquireAcceptedCheckpoint(missing.options)).available,false);
  const f=acceptedFixture();f.artifact.expired=true;let read=0;
  const result=await acquireAcceptedCheckpoint({...f.options,retainedArchive:async maximum=>{read++;assert.equal(maximum,f.zip.length);return f.zip;}});
  assert.equal(read,1);assert.equal(readAcceptedCheckpoint(result.handle).archive_origin,'retained-exact');
  assert(!f.calls.some(route=>route.endsWith('/zip')));
  const forged=acceptedFixture();forged.artifact.expired=true;
  const other=checkpoint();other.bodies[1][1]=json({forged:true});
  other.report.checkpoint.members[1]={name:other.bodies[1][0],bytes:other.bodies[1][1].length,sha256:reportHash(other.bodies[1][1])};
  await assert.rejects(acquireAcceptedCheckpoint({...forged.options,retainedArchive:async()=>encode(other).zip}),/accepted artifact digest/);
});
test('a missing retained copy never bypasses a permission or inventory failure', async () => {
  const f=acceptedFixture();let reads=0;const original=f.options.api;
  const api=Object.assign(async route=>{if(route.includes('/artifacts?'))throw Error('access denied');return original(route);},{artifactRedirect:original.artifactRedirect});
  await assert.rejects(acquireAcceptedCheckpoint({...f.options,api,retainedArchive:async()=>{reads++;return f.zip;}}),/access denied/);
  assert.equal(reads,0);
});
test('fresh queue loader retains real workflow identity and original successful upload receipt', async () => {
  const f=acceptedFixture();f.run.status='in_progress';
  const log=Buffer.from([JSON.stringify({report_sha256:f.source.report_sha256,report_bytes:f.raw.length}),
    `SHA256 digest of uploaded artifact zip is ${f.source.artifact_digest}`,
    `Artifact ${f.source.artifact_name} has been successfully uploaded! Final size is ${f.zip.length} bytes. Artifact ID is 56`].join('\n'));
  f.options.api.jobLogRedirect=async()=>new Response(null,{status:302,headers:{location:'https://fixtures.blob.core.windows.net/log'}});
  const report=await loadGeographicReport({...f.options,runId:12,artifactName:f.source.artifact_name,expectedHash:f.source.report_sha256,
    fresh:{run_attempt:2,head,baseline,candidate_commit:candidate,workflow_head:workflowHead,request_id:request},
    fetchImpl:async url=>new Response(url.endsWith('/log')?log:f.zip)});
  assert.deepEqual(geographicReportProducts(report).source,f.source);
});

test('durable entry retains exact accepted archive and validates its final untrusted locator', async t => {
  const f=acceptedFixture(), result=await acquireAcceptedCheckpoint(f.options);
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'accepted-copy-'));t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
  fs.mkdirSync(path.join(root,'coordination/engineering/batch-b'),{recursive:true});
  const directory='coordination/engineering/batch-b/accepted-a';
  const locator=retainAcceptedCheckpoint(result.handle,{repo:root,directory});
  const saved=fs.readFileSync(path.join(root,directory,'geography-artifact.zip'));
  assert(saved.equals(f.zip));assert.equal(reportHash(saved),f.receipt.geography.source.artifact_digest);
  assert.deepEqual(validateAcceptedCheckpointLocator(JSON.parse(fs.readFileSync(path.join(root,directory,'selected-checkpoint.json')))),locator);
  assert.equal(locator.retained_artifact.path,directory+'/geography-artifact.zip');
  assert.throws(()=>retainAcceptedCheckpoint(result.handle,{repo:root,directory}),/already exists/);
  assert(fs.readFileSync(path.join(root,directory,'geography-artifact.zip')).equals(f.zip));
  fs.symlinkSync(path.join(root,'missing'),path.join(root,'coordination/engineering/batch-b/dangling'));
  assert.throws(()=>retainAcceptedCheckpoint(result.handle,{repo:root,directory:'coordination/engineering/batch-b/dangling'}),/already exists/);
  for(const altered of [{...locator,retained_artifact:null}, {...locator,retained_artifact:{path:'../archive.zip'}},
    {...locator,retained_artifact:{path:'coordination/engineering/batch-b/../geography-artifact.zip'}},
    {...locator,acceptance:{...locator.acceptance,pr_number:0}}]) assert.throws(()=>validateAcceptedCheckpointLocator(altered));
});
test('retained partial-write failure leaves original ZIP but never publishes a final locator',async t=>{
  const f=acceptedFixture(), result=await acquireAcceptedCheckpoint(f.options);
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'accepted-failed-copy-'));t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
  fs.mkdirSync(path.join(root,'coordination/engineering/batch-b'),{recursive:true});
  const original=fs.writeFileSync,directory='coordination/engineering/batch-b/failed';
  fs.writeFileSync=(file,...args)=>{if(String(file).endsWith('/selected-checkpoint.json'))throw Error('injected final-write failure');return original(file,...args);};
  try{assert.throws(()=>retainAcceptedCheckpoint(result.handle,{repo:root,directory}),/injected final-write failure/);}
  finally{fs.writeFileSync=original;}
  assert(fs.readFileSync(path.join(root,directory,'geography-artifact.zip')).equals(f.zip));
  assert(!fs.existsSync(path.join(root,directory,'selected-checkpoint.json')));
});
test('metadata uses the shared authenticated API with a bounded response and inventory allowance',async()=>{
  const api=acceptedCheckpointAPI('fixture',{fetchImpl:async()=>new Response(Buffer.alloc(2*1024*1024+1))});
  await assert.rejects(api('/repos/owner/repo/pulls/7'),/bounded page/);
  const f=acceptedFixture();f.options.api=async()=>Array.from({length:100},()=>({body:'x'.repeat(30000)}));
  await assert.rejects(acquireAcceptedCheckpoint(f.options),/metadata inventory/);
  assert.equal(f.admitted[0],16*1024*1024);
});
test('queue rerun carries its actual successful original attempt without relabeling it current', async () => {
  const f=acceptedFixture();
  const log=Buffer.from([JSON.stringify({report_sha256:f.source.report_sha256,report_bytes:f.raw.length}),
    `SHA256 digest of uploaded artifact zip is ${f.source.artifact_digest}`,
    `Artifact ${f.source.artifact_name} has been successfully uploaded! Final size is ${f.zip.length} bytes. Artifact ID is 56`].join('\n'));
  f.options.api.jobLogRedirect=async()=>new Response(null,{status:302,headers:{location:'https://fixtures.blob.core.windows.net/log'}});
  const report=await loadGeographicReport({...f.options,runId:12,artifactName:f.source.artifact_name,expectedHash:f.source.report_sha256,
    fresh:{run_attempt:3,head,baseline,candidate_commit:candidate,workflow_head:workflowHead,request_id:request},
    fetchImpl:async url=>new Response(url.endsWith('/log')?log:f.zip)});
  const source=geographicReportProducts(report).source;
  assert.equal(source.run_attempt,2);assert.equal(source.job_id,34);assert.equal(source.artifact_name,f.source.artifact_name);
  assert(!f.calls.some(route=>route.includes('/attempts/3/')));
});
