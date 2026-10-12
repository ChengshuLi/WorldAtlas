import {gunzipSync} from 'node:zlib';
import {ImmutableReader} from './check-effective-geographic-regression.mjs';
import {valueBytes, valueSha, readOriginalRuleAuthority, qualifyOriginalSourceAuthority, qualifyOriginalNativeAuthority, readRetainedRegistryAuthority} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
// Bounded metadata continuation of the existing delivery command.
// Resolve actual committed outputs; never accept caller-written derived hashes.
import path from 'node:path';
import fs from 'node:fs';
import os from 'node:os';
import {randomUUID} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {createAcquisition} from './geography-prefetch.mjs';
import {performance} from 'node:perf_hooks';
import {candidateBudget} from './native-ownership/native-preparation-guards.mjs';
import {runMergeQueueClient} from './merge-queue-client.mjs';
import {checkPremergeEvidence, reviewContractBinding} from './premerge-evidence.mjs';
import {githubPages, readClaim} from './issue-claim-contract.mjs';
import {createHash} from 'node:crypto';

const need = (value, message) => { if (!value) throw Error(message); };
const hash = raw => createHash('sha256').update(raw).digest('hex');
const safe = value => typeof value === 'string' && /^[a-zA-Z0-9_./-]+$/.test(value)
  && !path.isAbsolute(value) && value.split('/').every(x => x && x !== '.' && x !== '..');
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);

export function locate(reader, locator) {
  need(locator && same(Object.keys(locator).sort(), ['commit', 'path'])
    && /^[a-f0-9]{40}$/.test(locator.commit) && safe(locator.path),
  'Supply an exact commit/path locator, without handwritten derived descriptors');
  const pin = reader.pin(locator.commit, locator.path);
  reader.read(pin);
  return pin;
}

export function readPreparedStage(reader, locator, expectedPhase) {
  const pin = locate(reader, locator), receipt = reader.json(pin);
  need(path.posix.basename(pin.path) === 'preparation.json' && receipt.version === 1
    && receipt.binding?.phase === expectedPhase
    && /^[a-f0-9]{64}$/.test(receipt.binding.config_sha256)
    && receipt.outputs && Object.keys(receipt.outputs).length,
  'Missing completed preparation phase');
  const prefix = path.posix.dirname(pin.path), outputs = {};
  for (const [name, declared] of Object.entries(receipt.outputs)) {
    need(safe(name) && !name.includes('/') && name !== 'preparation.json', 'Unsafe prepared output');
    const actual = reader.pin(pin.commit, prefix + '/' + name), raw = reader.read(actual);
    need(actual.bytes === declared.bytes && hash(raw) === declared.sha256, 'Committed prepared output differs: ' + name);
    outputs[name] = actual;
  }
  return {pin, receipt, outputs};
}

// `templates` and `retained` are produced by the admitted recipe/stage index.
// They identify files, not component IDs, hashes, source acceptance or approvals.
export function nativeConfigFromStages(reader, {requests, retained, templates, requested_resources, compatibility}) {
  const issued = readPreparedStage(reader, requests, 'requests');
  need(issued.outputs['requests.json'], 'Missing issued request index');
  const index = reader.json(issued.outputs['requests.json']);
  need(index.version === 1 && Array.isArray(index.groups) && index.groups.length, 'Missing ordered issued groups');
  const ids = index.groups.map(row => row.id);
  need(new Set(ids).size === ids.length && same(Object.keys(retained).sort(), [...ids].sort())
    && same(Object.keys(templates).sort(), [...ids].sort()), 'Missing/extra/duplicate committed group binding');
  const groups = index.groups.map(row => {
    const request = issued.outputs[row.request];
    need(request && reader.json(request).source_rule
      && same(reader.json(request).source_rule.expected_ids, row.component_ids), 'Issued index/request scope differs');
    const stage = readPreparedStage(reader, retained[row.id], 'retain');
    for (const name of ['request.json', 'terminal.json', 'facts.json', 'inventory.jsonl.gz', 'publication.json'])
      need(stage.outputs[name], 'Incomplete retained SOURCE stage: ' + name);
    need(stage.outputs['request.json'].sha256 === request.sha256
      && stage.outputs['request.json'].bytes === request.bytes, 'Retained SOURCE belongs to another issued request');
    const facts = reader.json(stage.outputs['facts.json']);
    need(facts.request?.path === request.path && facts.request?.sha256 === request.sha256 && facts.request?.bytes === request.bytes,
    'Retained SOURCE does not name the actual original issued request');
    const original = locate(reader, {commit: facts.request.commit, path: facts.request.path});
    need(original.mode === facts.request.mode && original.git_blob_oid === (facts.request.git_blob_oid ?? facts.request.blob)
      && original.sha256 === request.sha256 && original.bytes === request.bytes,
    'Original issued request descriptor was substituted');
    const template = templates[row.id];
    need(safe(template.destination) && template.destination.startsWith('.cache/native-grid-candidates/'), 'Unsafe native destination');
    return {id: row.id, destination: template.destination, template: locate(reader, template.locator),
      source: {request: original, operating: stage.outputs['terminal.json'], publication: stage.outputs['publication.json'],
        facts: stage.outputs['facts.json'], inventory: stage.outputs['inventory.jsonl.gz']}};
  });
  // The existing nativeRequests constructor must still validate genuine terminal,
  // publication, whole handoff, complete inventory, runtime and native template.
  return {version: 1, ...(compatibility === undefined ? {} : {compatibility}),
    ...(requested_resources === undefined ? {} : {requested_resources}), groups};
}

export function rebindConfigFromStage(reader, {retained, operating}) {
  const stage = readPreparedStage(reader, retained, 'retain');
  const names = {request: 'request.json', terminal: 'terminal.json', publication: 'publication.json',
    facts: 'facts.json', result: 'result.json'};
  const config = {version: 1};
  for (const [role, name] of Object.entries(names)) {
    need(stage.outputs[name], 'Incomplete retained rebind stage: ' + name);
    config[role] = stage.outputs[name];
  }
  config.execution_custody = {};
  for (const [role, name] of Object.entries({code_source: 'code-source.json', issued_plan: 'issued-plan.json',
    stderr: 'stderr.log', stdout: 'stdout.json', terminal: 'terminal.json'})) {
    need(stage.outputs[name], 'Incomplete retained execution custody: ' + name);
    config.execution_custody[role] = stage.outputs[name];
  }
  if (operating) {
    const proof = readPreparedStage(reader, operating, 'rebind-operating');
    need(proof.outputs['operating.json'], 'Missing committed operating body');
    config.operating = proof.outputs['operating.json'];
  }
  return config;
}

const canonical = value => Array.isArray(value) ? value.map(canonical) : value && typeof value === 'object'
  ? Object.fromEntries(Object.keys(value).sort().map(key => [key, canonical(value[key])])) : value;
const bytes = value => Buffer.from(JSON.stringify(canonical(value)) + '\n');
const equal = (a, b) => bytes(a).equals(bytes(b));

function ordinaryFile(filename) {
  const stat = fs.lstatSync(filename);
  need(stat.isFile() && fs.realpathSync(filename) === filename && stat.size <= 33554432,
    'Require bounded ordinary journal file');
  return fs.readFileSync(filename);
}

function directory(root, relative) {
  need(safe(relative) && /^(?:\.cache\/delivery-handoff|coordination\/engineering\/[^/]+)\//.test(relative),
    'Use a bounded owned delivery destination');
  let current = fs.realpathSync(root);
  for (const part of relative.split('/')) {
    current = path.join(current, part);
    const stat = fs.lstatSync(current, {throwIfNoEntry: false});
    if (stat) need(stat.isDirectory() && fs.realpathSync(current) === current, 'Nonordinary journal ancestor');
  }
  return current;
}

function exclusive(filename, raw) {
  const fd = fs.openSync(filename, 'wx');
  try { fs.writeFileSync(fd, raw); fs.fsyncSync(fd); } finally { fs.closeSync(fd); }
}

// Immutable intent is created before outputs. It is a local resume aid, never a
// scientific receipt or an authorization. Only an identical intent may fill an
// interrupted metadata write; unknown files and changed bytes always refuse.
export function openAdvanceJournal(root, destination, recipe, {resume = false, now = Date.now, budget = null} = {}) {
  const target = directory(root, destination), intentPath = path.join(target, 'advance.json');
  budget ??= candidateBudget([], {reserveBytes: 0, reserveDescriptors: 0});
  let intentRaw;
  if (!fs.existsSync(target)) {
    intentRaw = bytes({version: 1, kind: 'delivery-advance-v1', recipe, started_at: new Date(now()).toISOString()});
    budget.add({bytes: intentRaw.length});
    fs.mkdirSync(path.dirname(target), {recursive: true}); fs.mkdirSync(target);
    exclusive(intentPath, intentRaw);
  } else {
    need(resume, 'Occupied advance destination; explicit resume required');
    const stat = fs.lstatSync(intentPath);
    need(stat.isFile() && fs.realpathSync(intentPath) === intentPath, 'Nonordinary advance intent');
    budget.add({bytes: stat.size}); intentRaw = ordinaryFile(intentPath);
  }
  const intent = JSON.parse(intentRaw);
  need(intent.version === 1 && intent.kind === 'delivery-advance-v1' && equal(intent.recipe, recipe)
    && Number.isFinite(Date.parse(intent.started_at)), 'Foreign or changed advance intent');
  return {root, target, destination, intent, now, budget, chargedJournalFiles: new Set([intentPath])};
}

function journalFile(journal, filename) {
  if (!journal.chargedJournalFiles.has(filename)) {
    const stat = fs.lstatSync(filename);
    need(stat.isFile() && fs.realpathSync(filename) === filename, 'Nonordinary journal body');
    journal.budget.add({bytes: stat.size}); journal.chargedJournalFiles.add(filename);
  }
  return ordinaryFile(filename);
}

function writeJournal(journal, filename, raw) {
  journal.budget.add({bytes: raw.length});
  exclusive(filename, raw); journal.chargedJournalFiles.add(filename);
}

export function withAdvanceLock(journal, action) {
  const filename = path.join(journal.target, 'advance.lock');
  const guard = path.join(journal.target, 'advance.acquire');
  const raw = bytes({host: os.hostname(), pid: process.pid, nonce: randomUUID(), intent_sha256: hash(bytes(journal.intent))});
  // All cooperating resumers serialize stale inspection AND creation. A dead
  // acquisition guard is deliberately not auto-reaped: its ambiguous owner must
  // be reconciled explicitly, rather than introducing another compare/unlink race.
  need(!fs.lstatSync(guard, {throwIfNoEntry: false}), 'Advance acquisition is occupied; inspect its owner before recovery');
  journal.budget.add({bytes: raw.length});
  journal.budget.add({bytes: raw.length});
  exclusive(guard, raw);
  try {
    if (fs.existsSync(filename) || fs.lstatSync(filename, {throwIfNoEntry: false})) {
      const original = journalFile(journal, filename), lock = JSON.parse(original);
      need(lock.host === os.hostname() && Number.isSafeInteger(lock.pid) && lock.pid > 0
        && lock.intent_sha256 === hash(bytes(journal.intent)), 'Foreign advance lock');
      let gone = false;
      try { process.kill(lock.pid, 0); } catch (error) { if (error.code === 'ESRCH') gone = true; else throw error; }
      need(gone && ordinaryFile(filename).equals(original), 'Another advance process owns this destination');
      fs.unlinkSync(filename);
    }
    exclusive(filename, raw);
  } finally {
    need(ordinaryFile(guard).equals(raw), 'Advance acquisition ownership changed'); fs.unlinkSync(guard);
  }
  return Promise.resolve().then(action).finally(() => {
    need(ordinaryFile(filename).equals(raw), 'Advance lock ownership changed'); fs.unlinkSync(filename);
  });
}

function stageNames(id) {
  need(/^[a-z0-9-]+$/.test(id), 'Unsafe delivery stage');
  return {intent: id + '.intent.json', event: id + '.completed.json', directory: id};
}

export function readAdvanceStatus(journal) {
  const completed = [], waiting = [], refused = [];
  for (const name of fs.readdirSync(journal.target)) {
    if (['advance.json', 'advance.lock', 'advance.acquire', 'queue-submission.json'].includes(name) || /^observation-\d{6}\.json$/.test(name)
      || /^[a-z0-9-]+\.(intent|completed)\.json$/.test(name)) continue;
    need(/^[a-z0-9-]+$/.test(name) && fs.lstatSync(path.join(journal.target, name)).isDirectory()
      && fs.realpathSync(path.join(journal.target, name)) === path.join(journal.target, name)
      && fs.existsSync(path.join(journal.target, stageNames(name).intent)), 'Foreign advance inventory');
  }
  for (const name of fs.readdirSync(journal.target).sort()) {
    if (!name.endsWith('.completed.json')) continue;
    const event = JSON.parse(journalFile(journal, path.join(journal.target, name)));
    need(event.version === 1 && name === stageNames(event.stage).event, 'Malformed completed stage');
    const intent = JSON.parse(journalFile(journal, path.join(journal.target, stageNames(event.stage).intent)));
    need(intent.stage === event.stage && equal(intent.binding, event.binding)
      && hash(bytes(intent.config)) === event.binding.config_sha256
      && Number.isFinite(event.preparation_ms) && event.preparation_ms >= 0
      && Number.isFinite(Date.parse(event.completed_at)), 'Completed stage intent/timing differs');
    const receipt = JSON.parse(journalFile(journal, path.join(journal.target, event.stage, 'preparation.json')));
    need(equal(receipt.binding, event.binding) && equal(receipt.outputs, event.outputs), 'Completion/whole inventory differs');
    const actualNames = fs.readdirSync(path.join(journal.target, event.stage)).sort();
    need(equal(actualNames, [...Object.keys(receipt.outputs), 'preparation.json'].sort()), 'Foreign completed output');
    for (const [file, pin] of Object.entries(receipt.outputs)) {
      need(safe(file) && !file.includes('/'), 'Unsafe completed filename');
      const raw = journalFile(journal, path.join(journal.target, event.stage, file));
      need(raw.length === pin.bytes && hash(raw) === pin.sha256, 'Completed metadata changed: ' + file);
    }
    completed.push(event);
  }
  const events = fs.readdirSync(journal.target).filter(n => /^observation-\d{6}\.json$/.test(n)).sort()
    .map(name => JSON.parse(journalFile(journal, path.join(journal.target, name))));
  for (const event of events) {
    if (event.status === 'waiting') waiting.push(event);
    if (event.status === 'refused') refused.push(event);
  }
  const last = events.at(-1);
  const resolved = last && completed.some(e => (e.observations_seen === undefined
    ? Date.parse(e.completed_at) > Date.parse(last.observed_at) : e.observations_seen >= events.length)
    && (last.status === 'refused' || e.stage === last.stage));
  const waits = waiting.map(event => {
    const start = Date.parse(event.observed_at), next = completed.find(row => row.stage === event.stage && Date.parse(row.completed_at) >= start);
    return {stage: event.stage, kind: event.kind, started_at: event.observed_at,
      elapsed_ms: Math.max(0, (next ? Date.parse(next.completed_at) : journal.now()) - start), ongoing: !next};
  });
  const operatorDurations = completed.filter(e => e.binding.phase === 'retain').map(e => {
    const terminal = journalJSON(journal, e.stage, 'terminal.json');
    return {stage: e.stage, elapsed_seconds: Number.isFinite(terminal.elapsed_seconds) ? terminal.elapsed_seconds : null, execution_commit: terminal.execution_commit,
      terminal_sha256: e.outputs['terminal.json'].sha256};
  });
  const queuePath = path.join(journal.target, 'queue-submission.json');
  const queue_submission = fs.existsSync(queuePath) ? JSON.parse(journalFile(journal, queuePath)) : null;
  return {version: 1, queue_submission, completed: completed.map(e => e.stage), waiting: !resolved && last?.status === 'waiting' ? last : null,
    last_refusal: !resolved && last?.status === 'refused' ? last : null,
    timing: {overall_wall_ms: Math.max(0, journal.now() - Date.parse(journal.intent.started_at)),
      preparation_ms: completed.reduce((n, e) => n + e.preparation_ms, 0),
      api_wait_ms: completed.reduce((n, e) => n + (e.api_wait_ms ?? 0), 0),
      stages: completed.map(({stage, preparation_ms, api_wait_ms, completed_at}) => ({stage, preparation_ms, api_wait_ms, completed_at})),
      external_observations: events, waits, operator_durations: operatorDurations,
      limits: ['Preparation milliseconds are measured separately from external waits.',
        'Per-operator elapsed receipts are individual durations, never summed as parallel wall time.',
        'No gap-closures/hour claim follows from metadata preparation timing.']}};
}

export function observeAdvance(journal, observation) {
  need(['waiting', 'refused', 'external'].includes(observation.status), 'Unknown delivery observation');
  const names = fs.readdirSync(journal.target).filter(n => /^observation-\d{6}\.json$/.test(n)).sort();
  const prior = names.length ? JSON.parse(journalFile(journal, path.join(journal.target, names.at(-1)))) : null;
  if (prior) { const {observed_at, ...value} = prior; if (equal(value, observation)) return prior; }
  const event = {...observation, observed_at: new Date(journal.now()).toISOString()};
  writeJournal(journal, path.join(journal.target, 'observation-' + String(names.length).padStart(6, '0') + '.json'), bytes(event));
  return event;
}

export async function prepareAdvanceStage(journal, id, phase, config, produce, {interrupt = () => {}, preparationStarted = performance.now(), apiWaitMilliseconds = () => 0} = {}) {
  const names = stageNames(id), binding = {phase, config_sha256: hash(bytes(config))};
  const intended = bytes({version: 1, stage: id, binding, config});
  const intentPath = path.join(journal.target, names.intent), eventPath = path.join(journal.target, names.event);
  if (fs.existsSync(intentPath)) need(journalFile(journal, intentPath).equals(intended), 'Changed stage inputs; preserve prior vintage');
  else {
    need(!fs.lstatSync(path.join(journal.target, names.directory), {throwIfNoEntry: false})
      && !fs.lstatSync(eventPath, {throwIfNoEntry: false}), 'Unowned stage collision');
    writeJournal(journal, intentPath, intended);
  }
  if (fs.existsSync(eventPath)) {
    const status = readAdvanceStatus(journal); need(status.completed.includes(id), 'Missing completed stage');
    return {stage: id, resumed: true};
  }
  const products = await produce();
  const budget = journal.budget, outputs = {};
  need(Object.keys(products).length, 'Empty advancement cannot complete');
  for (const [name, raw] of Object.entries(products)) {
    need(safe(name) && !name.includes('/') && name !== 'preparation.json' && Buffer.isBuffer(raw), 'Plain metadata products required');
    budget.add({bytes: raw.length}); outputs[name] = {bytes: raw.length, sha256: hash(raw)};
  }
  const receipt = bytes({version: 1, binding, outputs});
  budget.add({bytes: receipt.length});
  const target = path.join(journal.target, names.directory);
  if (fs.existsSync(target) || fs.lstatSync(target, {throwIfNoEntry: false})) {
    need(fs.lstatSync(target).isDirectory() && fs.realpathSync(target) === target, 'Foreign stage destination');
    const expected = {...products, 'preparation.json': receipt};
    for (const name of fs.readdirSync(target)) need(Object.hasOwn(expected, name)
      && journalFile(journal, path.join(target, name)).equals(expected[name]), 'Interrupted stage contains foreign/changed bytes');
    if (fs.existsSync(path.join(target, 'preparation.json')))
      need(fs.readdirSync(target).length === Object.keys(expected).length, 'Incomplete completed inventory');
  } else fs.mkdirSync(target);
  for (const [name, raw] of Object.entries({...products, 'preparation.json': receipt})) {
    const file = path.join(target, name); if (!fs.existsSync(file)) exclusive(file, raw);
    interrupt(name);
  }
  const api_wait_ms = apiWaitMilliseconds();
  need(Number.isFinite(api_wait_ms) && api_wait_ms >= 0, 'Invalid observed API wait');
  const event = {version: 1, stage: id, binding, outputs, preparation_ms: Math.max(0, performance.now() - preparationStarted - api_wait_ms), api_wait_ms,
    observations_seen: fs.readdirSync(journal.target).filter(n => /^observation-\d{6}\.json$/.test(n)).length,
    completed_at: new Date(journal.now()).toISOString()};
  writeJournal(journal, eventPath, bytes(event));
  return {stage: id, resumed: false};
}

// The same live evidence gate used by the queue resolves the independently
// authored receipt. A local accepted:true field is never an approval input.
export async function acceptedReview(packet, api) {
  const route = `/repos/${packet.repo}`, pr = await api(`${route}/pulls/${packet.pr_number}`);
  need(pr.state === 'open' && !pr.draft && pr.head.sha === packet.head_sha && pr.base.sha === packet.base_sha,
    'Review head/base/readiness changed');
  const issue = await api(`${route}/issues/${packet.issue.number}`);
  need(equal(reviewContractBinding(issue, pr), {issue_contract_sha256: packet.issue_contract_sha256,
    pr_body_sha256: packet.pr_body_sha256}), 'Frozen review acceptance/body changed');
  const reservation = readClaim(await githubPages(api, `${route}/issues/${issue.number}/comments`));
  need(reservation?.active && reservation.worker_id === packet.author_worker_id && reservation.branch === pr.head.ref
    && Date.parse(reservation.expires_at) > Date.now(), 'Current author claim changed');
  const files = await githubPages(api, `${route}/pulls/${pr.number}/files`);
  need(equal(files, packet.files) && files.length === pr.changed_files, 'Frozen review file inventory changed');
  const checked = await checkPremergeEvidence({api, repo: packet.repo, pr, issue, reservation, files, review: true});
  need(['bytes-verified', 'limited'].includes(checked.status) && checked.review?.comment_id
    && checked.manifest_sha256 === packet.manifest.sha256, 'Genuine independent acceptance required');
  // Recheck the state after the potentially long evidence traversal.
  const after = await api(`${route}/pulls/${pr.number}`), currentIssue = await api(`${route}/issues/${issue.number}`);
  need(equal([after.state, after.draft, after.head.sha, after.base.sha, reviewContractBinding(currentIssue, after)],
    [pr.state, pr.draft, pr.head.sha, pr.base.sha, reviewContractBinding(issue, pr)]), 'Review changed during queue preparation');
  return {review_comment_id: checked.review.comment_id, reviewer_worker_id: checked.review.reviewer,
    repo: packet.repo, pr_number: pr.number, head_sha: pr.head.sha, base_sha: pr.base.sha,
    issue_contract_sha256: packet.issue_contract_sha256, pr_body_sha256: packet.pr_body_sha256,
    manifest_sha256: checked.manifest_sha256};
}

// Same bounded read adapter as queue-pr-merge.mjs. The queue client's second
// argument is a read deadline, not githubAPI's HTTP-method argument.
export function deliveryQueueAPI({execute = execFileSync} = {}) {
  return (route, {timeoutMs = 20_000} = {}) => {
    need(typeof route === 'string' && route.startsWith('/repos/ChengshuLi/WorldAtlas/')
      && Number.isFinite(timeoutMs) && timeoutMs > 0, 'Invalid bounded queue read');
    let output, failure;
    try { output = execute('gh', ['api', '--include', route], {encoding: 'utf8',
      maxBuffer: 16 * 1024 * 1024, timeout: timeoutMs, killSignal: 'SIGKILL'}); }
    catch (error) { output = String(error.stdout ?? ''); failure = error; }
    const separator = output.search(/\r?\n\r?\n/);
    const headers = output.startsWith('HTTP/') && separator >= 0 ? output.slice(0, separator) : '';
    if (failure) {
      const error = Error(`GitHub read failed for ${route}; no merge claimed`);
      const field = name => new RegExp(`^${name}:\\s*(\\d+)\\s*$`, 'im').exec(headers)?.[1];
      let secondaryLimit = false;
      try { secondaryLimit = /secondary rate limit/i.test(JSON.parse(headers ? output.slice(separator).trim() : output).message ?? ''); }
      catch { /* Preserve HTTP rejection even when its body is incomplete. */ }
      error.github = {http_status: Number(/^HTTP\/\S+\s+(\d+)/.exec(headers)?.[1]),
        rate_remaining: field('x-ratelimit-remaining'), rate_reset: field('x-ratelimit-reset'),
        retry_after: field('retry-after'), secondary_limit: secondaryLimit};
      throw error;
    }
    return JSON.parse(headers ? output.slice(separator).trim() : output);
  };
}

// Submission identity reaches durable disk before the existing queue client can
// write. Any existing intent is observation-only, even if the original process
// died before POST. That ambiguity is reported, never turned into a retry.
export async function advanceQueue(journal, packet, {api, submit, authorizeSubmission = false,
  checkReview = acceptedReview, client = runMergeQueueClient, clientOptions = {}, queueAPI = api}) {
  need(packet.repo === 'ChengshuLi/WorldAtlas', 'Use the existing named-repository queue');
  const filename = path.join(journal.target, 'queue-submission.json');
  let intent, resuming = false;
  if (fs.existsSync(filename)) {
    intent = JSON.parse(journalFile(journal, filename)); resuming = true;
    need(intent.repo === packet.repo && intent.pr_number === packet.pr_number && intent.head_sha === packet.head_sha
      && /^[-a-zA-Z0-9]{16,100}$/.test(intent.request_id), 'Existing submission identity belongs to another target');
  } else {
    const acceptance = await checkReview(packet, api);
    if (!authorizeSubmission) return {status: 'ready-for-queue', acceptance,
      next: 'Use advance with --submit-queue for this exact independently accepted head.'};
    intent = {version: 1, ...acceptance, request_id: randomUUID(), created_at: new Date(journal.now()).toISOString()};
    writeJournal(journal, filename, bytes(intent));
  }
  const started = journal.now();
  const result = await client({...clientOptions, api: queueAPI, submit, repo: intent.repo, number: intent.pr_number,
    head: intent.head_sha, requestId: intent.request_id, observeOnly: resuming, resuming,
    progress: value => clientOptions.progress?.(value)});
  observeAdvance(journal, {status: 'external', kind: 'queue', request_id: intent.request_id,
    observation_elapsed_ms: journal.now() - started, result});
  return result;
}

// A publication locator suffices to discover actual facts/request and all
// publication members. Terminal and optional rebind custody are genuine external
// outputs, so their locations remain explicit observations, not predicted pins.
export function committedRetentionConfig(reader, observation) {
  const publication = locate(reader, observation.publication), document = reader.json(publication);
  need(path.posix.basename(publication.path) === 'publication.json', 'Actual publication filename required');
  const prefix = path.posix.dirname(publication.path), factsPath = document.outputs?.facts?.path ?? 'facts.json';
  need(safe(factsPath) && !factsPath.includes('/'), 'Unsafe published facts path');
  const facts = reader.json(reader.pin(publication.commit, prefix + '/' + factsPath));
  let request;
  if (facts.request) {
    request = locate(reader, {commit: facts.request.commit, path: facts.request.path});
    need(request.sha256 === facts.request.sha256 && request.bytes === facts.request.bytes
      && request.mode === facts.request.mode && request.git_blob_oid === (facts.request.blob ?? facts.request.git_blob_oid),
    'Published original request descriptor differs');
  } else {
    request = locate(reader, observation.request);
    need(facts.request_sha256 === request.sha256, 'Rebind facts/observed request differs');
  }
  const terminal = locate(reader, observation.terminal), readPins = new Map([[terminal.path, terminal]]);
  for (const row of document.outputs ? Object.values(document.outputs)
    : [{path: 'facts.json', ...document.facts}, {path: 'inventory.jsonl.gz', ...document.inventory}, ...(document.assets ?? [])]) {
    need(safe(row.path) && !row.path.includes('/'), 'Unsafe publication member');
    const pin = reader.pin(publication.commit, prefix + '/' + row.path);
    need(pin.bytes === row.bytes && pin.sha256 === row.sha256, 'Published whole member differs');
    need(!readPins.has(pin.path), 'Publication/terminal path collision'); readPins.set(pin.path, pin);
  }
  readPins.set(publication.path, publication);
  const custody = {};
  for (const [role, locator] of Object.entries(observation.custody ?? {})) {
    const pin = locate(reader, locator); need(!readPins.has(pin.path), 'Custody role path collision');
    readPins.set(pin.path, pin); custody[role] = pin.path;
  }
  return {config: {version: 1, request, terminal: terminal.path, output: prefix,
    ...(observation.custody ? {custody} : {})}, publication, terminal,
    readLocal: (_root, name) => { need(readPins.has(name), 'Undeclared committed publication read'); return reader.read(readPins.get(name)); }};
}

const locatorOf = pin => ({commit: pin.commit, path: pin.path});
function journalBody(journal, stage, name) { return journalFile(journal, path.join(journal.target, stage, name)); }
function journalJSON(journal, stage, name) { return JSON.parse(journalBody(journal, stage, name)); }

// Actual committed publication observations have no group IDs. Their original
// issued request supplies scope/order, and joins to the saved recipe index.
function groupObservations(reader, observations, groups, kind) {
  need(Array.isArray(observations), 'Expected actual publication observations');
  const result = new Map();
  for (const observation of observations) {
    const retained = committedRetentionConfig(reader, observation), request = reader.json(retained.config.request);
    const ids = kind === 'source' ? request.source_rule?.expected_ids : request.additive?.scope_ids;
    const matches = groups.filter(g => equal(g.component_ids, ids));
    need(matches.length === 1 && !result.has(matches[0].id), 'Unknown, extra, duplicate or reordered terminal group');
    result.set(matches[0].id, {observation, retained, request});
  }
  return result;
}

function sourcePins(reader, record) {
  const publication = reader.json(record.retained.publication), prefix = path.posix.dirname(record.retained.publication.path);
  const member = name => reader.pin(record.retained.publication.commit, prefix + '/' + name);
  return {request: record.retained.config.request, operating: record.retained.terminal, publication: record.retained.publication,
    facts: member('facts.json'), inventory: {...member('inventory.jsonl.gz'),
      uncompressed_bytes: publication.inventory.uncompressed_bytes, uncompressed_sha256: publication.inventory.uncompressed_sha256}};
}

function templatePin(reader, journal, index, group, kind, templateCommit) {
  const original = group[kind + '_locator'];
  const pin = original ? locate(reader, original) : reader.pin(templateCommit, journal.destination + '/recipe/' + group[kind + '_template']);
  need(equal(reader.json(pin), journalJSON(journal, 'recipe', group[kind + '_template'])), 'Committed recipe template changed');
  return pin;
}

function registryComposition(reader, registryPins) {
  const ledgerPins = new Map();
  for (const pin of registryPins) for (const entry of reader.json(pin).entries) {
    const binding = reader.json(entry.source_authority), ledger = binding.original_pins.ledger;
    reader.read(ledger); const key = ledger.commit + ':' + ledger.path;
    need(!ledgerPins.has(key) || equal(ledgerPins.get(key), ledger), 'Conflicting retained ledger descriptor');
    ledgerPins.set(key, ledger);
  }
  return {version: 1, registries: registryPins, ledgers: [...ledgerPins.values()]};
}

// Discovery from an existing selected release is only a metadata replay input.
// Each later phase still invokes its ordinary genuine terminal/custody checks.
export function observeCompletedDelivery(reader, {sidecar: sidecarLocator, composed_ledger, new_prefix}) {
  const sidecarPin = locate(reader, sidecarLocator), sidecar = reader.json(sidecarPin);
  const registry = reader.json(sidecar.authority_registry), selected = reader.json(sidecar.logical_asset_map.ledger);
  const certificate = reader.json(selected.current_rebind), operating = reader.json(certificate.operating);
  const sources = [], natives = [], authorities = [];
  for (const entry of registry.entries.filter(e => e.source_authority.path.startsWith(new_prefix))) {
    const binding = reader.json(entry.source_authority), native = reader.json(binding.original_pins.native_request).additive;
    const aliases = new Map((binding.source_output_aliases ?? []).map(a => [a.original.path, a.published]));
    const role = key => {
      const pins = native.inputs.filter(p => p.path === native[key]); need(pins.length === 1, 'Missing retained SOURCE role');
      return aliases.get(pins[0].path) ?? pins[0];
    };
    sources.push({publication: locatorOf(role('publication_path')), terminal: locatorOf(role('operating_path'))});
    natives.push({publication: locatorOf(binding.native_proof.publication), terminal: locatorOf(binding.native_proof.operating)});
    authorities.push({rule_preimage: locatorOf(entry.rule_preimage), source_authority: locatorOf(entry.source_authority)});
  }
  need(sources.length, 'Completed selection contains no owned authorities');
  return {sources, natives, authorities, registry: locatorOf(sidecar.authority_registry), composed_ledger,
    rebind: {request: locatorOf(certificate.request), publication: locatorOf(certificate.publication),
      terminal: locatorOf(operating.execution_custody.terminal), custody: Object.fromEntries(Object.entries(operating.execution_custody)
        .filter(([role]) => role !== 'terminal').map(([role, pin]) => [role, locatorOf(pin)]))},
    operating: locatorOf(certificate.operating), certificate: locatorOf(selected.current_rebind), sidecar: sidecarLocator};
}

// Fixed transitions, not a job graph. One invocation prepares the next available
// metadata stage or states the actual missing external input. Repeating the same
// command consumes saved indexes instead of handwritten result hashes or IDs.
export async function nextDeliveryStage(journal, config, reader, adapters) {
  const recipePin = locate(reader, config.recipe), recipe = reader.json(recipePin);
  const status = readAdvanceStatus(journal), done = new Set(status.completed);
  const completed = (id, input) => {
    if (!done.has(id)) return false;
    need(equal(journalJSON(journal, '.', stageNames(id).intent).config, input), 'Completed stage inputs changed: ' + id);
    return true;
  };
  const prepare = (id, phase, input, produce) => ({id, phase, input, produce});
  const wait = (stage, kind, detail) => ({waiting: {status: 'waiting', stage, kind, detail}});
  if (!done.has('recipe')) return prepare('recipe', 'recipe', {recipe: recipePin}, () => materializeRecipe(recipe, reader).products);
  const index = journalJSON(journal, 'recipe', 'recipe-index.json'), groups = index.groups;
  let observed = config.observations ?? {};
  if (config.completed_delivery) observed = {...observeCompletedDelivery(reader, config.completed_delivery), ...observed};
  const compatibility = index.compatibility ? {compatibility: index.compatibility} : {};
  if (index.mode !== 'retained-groups' && !observed.template_commit)
    return wait('requests', 'commit', 'Commit the completed recipe templates and supply their actual commit.');
  const requestConfig = kind => ({version: 1, ...compatibility, ...(kind === 'source' ? {
    registry: index.registry, component_ids: groups.flatMap(g => g.component_ids)} : {}), groups: groups.map(group => {
    const template = templatePin(reader, journal, index, group, kind, observed.template_commit), request = reader.json(template);
    return {id: group.id, ...(kind === 'source' ? {handoff_id: group.handoff_id, component_ids: group.component_ids} : {}),
      template, destination: group[kind + '_destination'], ...(index.compatibility ? {} : {requested_resources: {
        processing_allowance: request.processing_allowance, operating_limits: request.operating_limits}})};
  })});
  const sourcesConfig = requestConfig('source');
  if (!completed('requests', sourcesConfig)) return prepare('requests', 'requests', sourcesConfig, () => adapters.prepareRequests(sourcesConfig, reader));
  const sources = groupObservations(reader, observed.sources ?? [], groups, 'source');
  for (const group of groups) {
    const id = 'source-' + group.id;
    const row = sources.get(group.id);
    need(row || !done.has(id), 'Completed SOURCE observation was removed');
    if (!row) return wait(id, 'source-terminal', 'Existing SOURCE supervisor must finish and its genuine publication/terminal must be committed.');
    if (completed(id, row.observation)) continue;
    need(equal(row.request, journalJSON(journal, 'requests', group.id + '-source-request.json')), 'Actual SOURCE execution differs from prepared request');
    return prepare(id, 'retain', row.observation, () => adapters.retainProducts(row.retained.config, journal.root, reader, row.retained.readLocal));
  }
  need(sources.size === groups.length, 'Previously completed SOURCE observation was removed');
  const input = requestConfig('native');
  input.groups.forEach(group => { group.source = sourcePins(reader, sources.get(group.id)); });
  if (!completed('native-requests', input)) {
    return prepare('native-requests', 'native-requests', input, () => {
      const outputs = adapters.nativeRequests(input, reader);
      for (const raw of Object.values(outputs)) recheckNativeRequest(JSON.parse(raw));
      return outputs;
    });
  }
  const natives = groupObservations(reader, observed.natives ?? [], groups, 'native');
  for (const group of groups) {
    const id = 'native-' + group.id;
    const row = natives.get(group.id);
    need(row || !done.has(id), 'Completed NATIVE observation was removed');
    if (!row) return wait(id, 'native-terminal', 'Existing NATIVE supervisor must finish and its genuine publication/terminal must be committed.');
    if (completed(id, row.observation)) continue;
    const expected = index.mode === 'retained-groups' ? reader.json(templatePin(reader, journal, index, group, 'native'))
      : journalJSON(journal, 'native-requests', group.id + '-native-request.json');
    need(equal(row.request, expected), 'Actual NATIVE execution differs from original replay or prepared request');
    return prepare(id, 'retain', row.observation, () => adapters.retainProducts(row.retained.config, journal.root, reader, row.retained.readLocal));
  }
  need(natives.size === groups.length, 'Previously completed NATIVE observation was removed');
  for (const group of groups) {
    const id = 'authority-' + group.id;
    const input = {source_publication: sources.get(group.id).observation.publication,
      native_publication: natives.get(group.id).observation.publication, native_operating: natives.get(group.id).observation.terminal};
    if (completed(id, input)) continue;
    return prepare(id, 'authority', input, () => constructOriginalAuthority(adapters.authorityReader(), input).products);
  }
  if (!observed.authorities) return wait('registry', 'commit', 'Commit each completed authority pair and provide its actual pair locators.');
  need(Array.isArray(observed.authorities) && observed.authorities.length === groups.length, 'Missing/extra committed authority pair');
  const pairs = [], seen = new Set();
  for (const pair of observed.authorities) {
    const binding = reader.json(locate(reader, pair.source_authority)), ledger = reader.json(binding.original_pins.ledger);
    const group = groups.find(g => equal(g.component_ids, ledger.scope_ids));
    need(group && !seen.has(group.id), 'Unknown/duplicate committed authority scope'); seen.add(group.id);
    for (const [role, name] of [['rule_preimage', 'original-rule-preimage.json'], ['source_authority', 'authority-binding.json']])
      need(reader.read(locate(reader, pair[role])).equals(journalBody(journal, 'authority-' + group.id, name)), 'Committed authority differs from derived body');
    pairs.push(pair);
  }
  if (!completed('registry', {authorities: pairs})) return prepare('registry', 'registry', {authorities: pairs}, () => constructAuthorityRegistry(adapters.authorityReader(), pairs));
  if (!observed.registry) return wait('compose', 'commit', 'Commit the completed authority registry and supply its actual locator.');
  const registryPin = locate(reader, observed.registry), registry = reader.json(registryPin), expected = journalJSON(journal, 'registry', 'authority-registry.json');
  const retained = (recipe.retained_registries ?? []).map(p => locate(reader, p));
  const allowed = [...expected.entries, ...retained.flatMap(p => reader.json(p).entries)];
  need(expected.entries.every(e => registry.entries.some(a => equal(a, e)))
    && registry.entries.every(e => allowed.some(a => equal(a, e))), 'Committed registry missing derived authority or adds undeclared authority');
  const composition = registryComposition(reader, [registryPin, ...retained]);
  if (!completed('compose', composition)) {
    const input = composition;
    return prepare('compose', 'compose', input, () => adapters.composeAuthorities(input, reader));
  }
  if (!observed.rebind) return wait('rebind-retain', 'rebind-terminal', 'Run the existing rebind wrapper externally; supply its genuine committed publication, request and complete custody.');
  const reb = committedRetentionConfig(reader, observed.rebind);
  if (!completed('rebind-retain', observed.rebind)) return prepare('rebind-retain', 'retain', observed.rebind,
    () => adapters.retainProducts(reb.config, journal.root, reader, reb.readLocal));
  const rebind = {version: 1, request: reb.config.request, terminal: reb.terminal, publication: reb.publication,
    facts: reader.pin(reb.publication.commit, reb.config.output + '/facts.json'), result: reader.pin(reb.publication.commit, reb.config.output + '/result.json'),
    execution_custody: {...Object.fromEntries(Object.entries(observed.rebind.custody).map(([role, p]) => [role, locate(reader, p)])), terminal: reb.terminal}};
  if (!completed('rebind-operating', rebind)) return prepare('rebind-operating', 'rebind-operating', rebind, () => adapters.rebindCustody(rebind, reader));
  if (!observed.operating) return wait('rebind-certificate', 'commit', 'Commit the derived operating body and supply its actual locator.');
  rebind.operating = locate(reader, observed.operating);
  need(reader.read(rebind.operating).equals(journalBody(journal, 'rebind-operating', 'operating.json')), 'Committed operating body differs');
  if (!completed('rebind-certificate', rebind)) return prepare('rebind-certificate', 'rebind-certificate', rebind, () => adapters.rebindCustody(rebind, reader, true));
  if (!observed.certificate || !observed.composed_ledger) return wait('package', 'commit', 'Supply actual committed certificate and composed-ledger locators.');
  const certificate = locate(reader, observed.certificate), ledger = locate(reader, observed.composed_ledger);
  need(reader.read(certificate).equals(journalBody(journal, 'rebind-certificate', 'certificate.json'))
    && reader.read(ledger).equals(journalBody(journal, 'compose', 'composed-original-ledger.json'))
    && reader.read(registryPin).equals(journalBody(journal, 'compose', 'authority-registry.json')), 'Committed final authority/ledger/certificate differs');
  const projection = {version: 1, registry: registryPin, ledger, rebind: certificate, new_prefix: recipe.new_prefix};
  if (!completed('package', projection)) return prepare('package', 'package', projection, () => adapters.packageProjection(projection, reader));
  if (!observed.sidecar) return wait('finalize', 'assembly', 'Existing assembly/release preparation must supply the actual committed sidecar.');
  const sidecar = locate(reader, observed.sidecar), selected = reader.json(sidecar).logical_asset_map.ledger;
  const final = {...projection, sidecar, selected_ledger: selected, selector: locate(reader, recipe.selector), package_inputs: locate(reader, recipe.package_inputs)};
  if (!completed('finalize', final)) return prepare('finalize', 'finalize', final, () => adapters.finalizeDelivery(final, reader));
  if (!config.review) return wait('review', 'publication-review', 'Publish the actual author head/PR; provide repository and PR number.');
  const pr = await adapters.api(`/repos/${config.review.repo}/pulls/${config.review.pr_number}`);
  const reviewConfig = {repo: config.review.repo, number: config.review.pr_number, expectedHead: pr.head.sha};
  if (!completed('review', reviewConfig)) return prepare('review', 'review', reviewConfig, () => adapters.freezeReview({...reviewConfig, api: adapters.api, reader}));
  return {queue: journalJSON(journal, 'review', 'review-packet.json')};
}

// Existing-contract constructor, scoped to avoid mixing scientific identities.
export const {materializeRecipe, modelRequestBudget, recheckNativeRequest} = (() => {
// Metadata-only recipe postimage. No body acquisition, execution or publication.
const need=(v,m)=>{if(!v)throw Error(m);};
const FILE=33554432, SUPERVISOR=131072;
const canon=v=>Array.isArray(v)?v.map(canon):v&&typeof v==='object'?Object.fromEntries(Object.keys(v).sort().map(k=>[k,canon(v[k])])):v;
const bytes=v=>Buffer.from(JSON.stringify(canon(v))+'\n');
const sha=v=>createHash('sha256').update(v).digest('hex');
const equal=(a,b)=>bytes(a).equals(bytes(b));
const hash=(s,n=64)=>typeof s==='string'&&new RegExp(`^[a-f0-9]{${n}}$`).test(s);
const safe=s=>typeof s==='string'&&/^[A-Za-z0-9_.\/-]+$/.test(s)&&!s.startsWith('/')&&s.split('/').every(x=>x&&x!=='.'&&x!=='..');
const unique=a=>Array.isArray(a)&&a.length&&a.every(x=>typeof x==='string'&&x)&&new Set(a).size===a.length;
const integer=(n,name,max=Number.MAX_SAFE_INTEGER)=>{need(Number.isSafeInteger(n)&&n>=0&&n<=max,'Invalid '+name);return n;};
const add=values=>values.reduce((n,v)=>integer(n+v,'aggregate bytes'),0);
const operatorPin=p=>{const q={...p,blob:p.blob??p.git_blob_oid};delete q.git_blob_oid;return q;};
const identity=p=>({commit:p.commit,path:p.path,mode:p.mode,blob:p.blob??p.git_blob_oid,bytes:p.bytes,sha256:p.sha256});
function locate(reader,p){need(p&&equal(Object.keys(p).sort(),['commit','path'])&&hash(p.commit,40)&&safe(p.path),'Exact metadata commit/path locator required');const pin=reader.pin(p.commit,p.path);reader.read(pin);return pin;}
function read(reader,p){const pin=locate(reader,p);return {pin,body:reader.json(pin)};}
function uniquePins(pins){const map=new Map();for(const original of pins){const p=operatorPin(original);need(!map.has(p.path)||equal(map.get(p.path),p),'Conflicting input path: '+p.path);map.set(p.path,p);}return [...map.values()];}
function pinCosts(p){
 need(safe(p?.path)&&['100644','100755'].includes(p.mode)&&hash(p.sha256),'Invalid operator input descriptor');
 if(p.kind==='original-report-product')need(p.mode==='100644'&&p.path.startsWith('.cache/additive-native-gap-repair/')&&hash(p.report_sha256)&&/^(components|sources)-\d{3}\.jsonl\.gz$/.test(p.original_product_path),'Invalid original report product');
 else if(p.kind==='completed-inventory-body')need(p.mode==='100644'&&/^\.cache\/native-grid-candidates\/[A-Za-z0-9_-]+\/(facts\.json|publication\.json|inventory\.jsonl\.gz)$/.test(p.path),'Invalid predecessor body');
 else need(hash(p.commit,40)&&hash(p.blob??p.git_blob_oid,40),'Missing immutable input identity');
 const costs=[integer(p.bytes,'whole input',FILE)];
 if(p.uncompressed_bytes!==undefined){need(hash(p.uncompressed_sha256),'Missing decoded identity');costs.push(integer(p.uncompressed_bytes,'decoded input',FILE));}return costs;
}

// Mirrors inventoryCommand's prospective candidateBudget accounting, including
// BOTH child and supervisor request bytes. It is not live RSS/supply admission.
function modelRequestBudget(request,{predecessor_allowance=null,request_bytes_bound=null}={}){
 const stage=request.source_rule??request.additive;need(stage&&Array.isArray(stage.inputs),'Missing operator stage');
 const literal=request.operating_profile===undefined;
 need(literal||request.operating_profile==='source-native-v2','Unsupported resource profile');
 const allowance=literal?{phaseBytes:256*1024*1024,rssBytes:1024**3}:request.processing_allowance;
 need(allowance&&Object.keys(allowance).sort().join(',')==='phaseBytes,rssBytes'&&Object.values(allowance).every(n=>Number.isSafeInteger(n)&&n>0),'Explicit finite reader allowance required');
 const output=integer(request.output_reserve,'output reserve');need(output>=SUPERVISOR&&output<=allowance.phaseBytes,'Invalid output reserve');
 const operating=request.operating_runtime;need(operating?.version===1&&operating.platform==='linux'&&operating.runtime?.map(p=>p.role).join(',')==='git,node,process-inspector,time','Complete admitted runtime required');
 for(const p of operating.runtime)need(typeof p.path==='string'&&p.path.startsWith('/')&&p.mode===493&&hash(p.sha256)&&Number.isSafeInteger(p.bytes)&&p.bytes>0,'Invalid runtime binding');
 need(new Set(operating.runtime.map(p=>p.path)).size===4,'Duplicate runtime path');
 need(operating.supervisor?.path==='coordination/engineering/melanesia363-additive-delivery-20261010/supervise-source-native-linux.mjs'&&hash(operating.supervisor.sha256),'Invalid supervisor');
 const supervisor=integer(operating.supervisor.bytes,'supervisor',SUPERVISOR),actual=bytes(request).length;
 const requestedBound=request_bytes_bound===null?null:integer(request_bytes_bound,'request bytes bound',SUPERVISOR);
 const requestBytes=requestedBound===null?actual:Math.max(actual,requestedBound);
 let monitored=13*1024*1024;
 if(literal)need(request.operating_limits===undefined&&request.processing_allowance===undefined&&operating.support_code===undefined,'Historical resources must remain literal');
 else{
  const l=request.operating_limits;need(l&&Object.keys(l).sort().join(',')==='log_bytes,monitor_bytes,output_bytes,receipt_bytes,retained_bytes,rss_bytes,wall_seconds'&&Object.values(l).every(n=>Number.isSafeInteger(n)&&n>0)&&Number.isSafeInteger(l.wall_seconds*1000),'Complete operating limits required');
  need(l.output_bytes>=output+SUPERVISOR&&Number.isSafeInteger(l.output_bytes+l.receipt_bytes)&&l.output_bytes+l.receipt_bytes<=l.retained_bytes&&l.log_bytes<=l.retained_bytes&&l.monitor_bytes<=l.retained_bytes&&l.log_bytes<=l.rss_bytes&&l.monitor_bytes<=l.rss_bytes&&l.receipt_bytes<=l.rss_bytes&&allowance.phaseBytes<=l.rss_bytes&&allowance.rssBytes<=l.rss_bytes,'Inconsistent output/runtime limits');
  need(operating.support_code?.map(p=>p.path).join(',')==='scripts/local-workspace.mjs,scripts/worker-identity.mjs'&&operating.support_code.every(p=>hash(p.sha256)&&Number.isSafeInteger(p.bytes)&&p.bytes>0&&p.bytes<=FILE),'Complete operating support bindings required');
  monitored=add([l.log_bytes,l.monitor_bytes,l.receipt_bytes,2*add(operating.support_code.map(p=>p.bytes))]);
 }
 const sourceSlots=['source_request_path','operating_path','publication_path','facts_path','inventory_path'];
 const slotPaths=new Set(predecessor_allowance?sourceSlots.map(k=>stage[k]):[]);
 let inputPins=stage.inputs;
 const predecessorCosts=[];
 if(predecessor_allowance){
  need(request.additive&&equal(Object.keys(predecessor_allowance).sort(),[...sourceSlots].sort())&&slotPaths.size===5,'Complete five-role predecessor allowance required');
  for(const key of sourceSlots){need(stage.inputs.filter(p=>p.path===stage[key]).length===1,'Missing native predecessor slot');const p=predecessor_allowance[key];need(p&&Object.keys(p).every(k=>['bytes','uncompressed_bytes'].includes(k)),'Invalid predecessor allowance');need(p.bytes>0,'Positive predecessor allowance required');predecessorCosts.push(integer(p.bytes,'predecessor encoded allowance',FILE));if(p.uncompressed_bytes!==undefined)predecessorCosts.push(integer(p.uncompressed_bytes,'predecessor decoded allowance',FILE));}
  need(predecessor_allowance.inventory_path.uncompressed_bytes!==undefined,'Decoded SOURCE inventory allowance required');
  inputPins=stage.inputs.filter(p=>!slotPaths.has(p.path));
 }
 const code=[...request.executed_code,...request.installed_modules].map(p=>{need(typeof p.path==='string'&&safe(p.path.replaceAll('@',''))&&hash(p.sha256),'Invalid code/module descriptor');return integer(p.bytes,'code/module bytes',FILE);});
 const costs=[...code,requestBytes,...pinCosts(request.report),...inputPins.flatMap(pinCosts),...predecessorCosts,...request.baseline.pins.flatMap(pinCosts)];
 const operatingReserve=add([add(operating.runtime.filter(p=>p.role!=='node').map(p=>p.bytes)),supervisor,requestBytes,monitored]);
 const reserved=add([operating.runtime.find(p=>p.role==='node').bytes,output,SUPERVISOR,operatingReserve]);
 const total=add([...costs,reserved]),descriptors=costs.length+16,reasons=[];
 if(actual>SUPERVISOR||requestBytes>SUPERVISOR)reasons.push('request byte cap');
 if(requestedBound!==null&&actual>requestedBound)reasons.push('request byte reservation');
 if(stage.inputs.length>213)reasons.push('stage descriptor cap');
 if(descriptors>512)reasons.push('phase descriptor cap');
 if(total>allowance.phaseBytes)reasons.push('phase byte cap');
 return {fits:!reasons.length,reasons,request_bytes:actual,modeled_request_bytes:requestBytes,input_bytes:add(costs),reserved_bytes:reserved,total_bytes:total,descriptors,phase_bytes:allowance.phaseBytes,rss_bytes:allowance.rssBytes,predecessor_allowance};
}

function recheckNativeRequest(request){
 need(request.operation==='unactivated-additive-native-batch-v1','Native request required');
 const model=modelRequestBudget(request);need(model.fits,'Actual native request exceeds admission: '+model.reasons.join(', '));return model;
}

function accepted(reader,registry,selection){
 const entries=registry.body.entries.filter(e=>e.id===selection.handoff_id);need(entries.length===1,'Unknown/ambiguous accepted handoff');
 const entry=entries[0],pin={...entry.source,commit:entry.accepted_source_commit};
 const scope=reader.json(pin),rows=scope.candidate_source_native_bindings;
 need(unique(entry.cohort_ids)&&equal(scope.scopeIds,entry.cohort_ids)&&equal(rows?.map(r=>r.component_id),entry.cohort_ids),'Accepted handoff scope/order changed');
 need(equal([...new Set(rows.map(r=>r.retained_payload?.target_stable_location_id))].sort(),[...entry.target_ids].sort()),'Accepted target mapping changed');
 return {entry,pin:operatorPin(pin),scope,rows};
}
function resourceRequest(template,resources){
 need(template.operating_profile==='source-native-v2'&&resources&&equal(Object.keys(resources).sort(),['operating_limits','output_reserve','processing_allowance']),'New recipe requires admitted v2 template and explicit resources');
 return {...structuredClone(template),...structuredClone(resources)};
}
function directProduct(binding){return binding.physical_comparison?.original_report_product?.path;}
function locatorMap(reader,selection,handoff){
 if(!selection.physical_locator)return null;
 const {input,format}=selection.physical_locator,loaded=read(reader,input);
 const match=handoff.scope.consumed_inputs.filter(p=>p.path===loaded.pin.path&&equal(identity(p),identity(loaded.pin)));
 need(match.length===1,'Physical locator is not an exact consumed handoff input');
 if(format==='keyed-path')return new Map(Object.entries(loaded.body).map(([id,row])=>[id,row.path]));
 need(format==='components-comparison-product'&&Array.isArray(loaded.body.components),'Unsupported physical locator format');
 const rows=loaded.body.components;need(new Set(rows.map(r=>r.component_id)).size===rows.length,'Duplicate physical locator identity');
 return new Map(rows.map(r=>[r.component_id,r.comparison_product]));
}
function physicalProduct(handoff,name,report,acquisitions){
 const matches=handoff.scope.physical_restoration?.restorations?.filter(p=>p.path===name);
 need(matches?.length===1&&/^(components|sources)-\d{3}\.jsonl\.gz$/.test(name),'Missing/ambiguous restored physical product: '+name);
 const r=matches[0];
 const reused=handoff.scope.reused_whole_product_inputs===undefined?[]:handoff.scope.reused_whole_product_inputs;
 need(Array.isArray(reused)&&reused.every(p=>p?.whole_body_consumed===false),'Malformed reused whole physical product custody');
 // The unchanged handoff retains its honest prior-consumption annotations.
 // These ordinary pins request future acquisition of the actual whole bodies.
 const declared=[...handoff.scope.consumed_inputs,...reused];
 const paths=new Set(declared.filter(p=>p.bytes===r.whole_original_bytes&&p.sha256===r.whole_original_sha256).map(p=>p.path));
 const candidates=declared.filter(p=>paths.has(p.path));
 need(candidates.every(p=>p.blob===undefined||p.git_blob_oid===undefined||p.blob===p.git_blob_oid),
 'Conflicting physical product blob aliases: '+name);
 const sources=uniquePins(candidates.map(p=>({...identity(p),
  ...(p.uncompressed_bytes===undefined?{}:{uncompressed_bytes:p.uncompressed_bytes}),
  ...(p.uncompressed_sha256===undefined?{}:{uncompressed_sha256:p.uncompressed_sha256})})));
 need(sources.length>0,'No exact whole physical product pin: '+name);
 sources.forEach(pinCosts);
 need(sources.every(p=>(p.uncompressed_bytes===undefined||p.uncompressed_bytes===r.decoded_bytes)
  &&(p.uncompressed_sha256===undefined||p.uncompressed_sha256===r.decoded_sha256)),
 'Conflicting decoded physical product identity: '+name);
 const source=operatorPin(sources[0]);pinCosts(source);
 const destination='.cache/additive-native-gap-repair/delivery/'+source.sha256+'/'+name;
 acquisitions.push({source,destination,role:'physical-product'});
 return {kind:'original-report-product',path:destination,mode:'100644',bytes:r.whole_original_bytes,sha256:r.whole_original_sha256,
  uncompressed_bytes:r.decoded_bytes,uncompressed_sha256:r.decoded_sha256,report_sha256:report.sha256,original_product_path:name};
}
function adminProducts(handoff,pool){
 const records=handoff.scope.consumed_source_bindings;need(Array.isArray(records)&&records.length,'Missing consumed administrative source bindings');
 const result=[];
 for(const record of records){
  need(typeof record?.source_id==='string'&&record.source_id.length,'Missing administrative source identity');
  const custody=record.original_source_custody;
  need(custody===undefined||(custody&&typeof custody==='object'&&!Array.isArray(custody)
   &&custody.source_id===record.source_id&&custody.catalogue_record!==undefined),'Conflicting administrative source custody identity');
  const catalogues=[record.catalogue_record,custody?.catalogue_record].filter(value=>value!==undefined);
  need(catalogues.length&&catalogues.every(value=>value&&typeof value==='object'&&!Array.isArray(value)
   &&Array.isArray(value.parts)&&value.parts.length),'Incomplete administrative product parts');
  need(catalogues.every(value=>equal(value,catalogues[0])),'Conflicting administrative catalogue aliases');
  const catalogue=catalogues[0];
  need((catalogue.key===undefined||catalogue.key===record.source_id)
   &&(record.whole_bytes===undefined||record.whole_bytes===catalogue.original_bytes)
   &&(record.whole_sha256===undefined||record.whole_sha256===catalogue.original_sha256),
  'Conflicting administrative catalogue source identity');
  for(const part of catalogue.parts){const found=pool.filter(p=>p.path===part?.path&&['bytes','sha256','uncompressed_bytes','uncompressed_sha256'].every(k=>p[k]===part[k]));
   need(found.length&&found.every(p=>equal(p,found[0])),'Missing/ambiguous exact administrative input pin: '+part?.path);result.push(found[0]);}}
 return uniquePins(result);
}
const sourceKeys=['cases_path','outcomes_path','payloads_path','simplified_comparison_path','generalized_comparison_path','remainders_path'];
const nativeKeys=['source_request_path','operating_path','publication_path','facts_path','inventory_path'];
function nativeInvariant(request){const r=structuredClone(request);delete r.destination;for(const k of [...nativeKeys,'scope_ids','source_execution_commit','source_runtime','inputs','owner_parts'])delete r.additive[k];return r;}
function sourceCommon(request){const r=request.source_rule,removed=new Set([...sourceKeys.map(k=>r[k]),r.registry_path,...r.original_products.map(p=>p.path),...r.administrative_products.map(p=>p.path),...r.target_banks]);return r.inputs.filter(p=>!removed.has(p.path));}

function materializeRecipe(recipe,reader){
 need(recipe?.version===1&&['greedy-model','retained-groups'].includes(recipe.mode)&&/^[a-z0-9-]+$/.test(recipe.id),'Explicit admitted delivery recipe required');
 need(safe(recipe.destination_prefix)&&recipe.destination_prefix.startsWith('.cache/native-grid-candidates/'),'Fresh candidate destination prefix required');
 const registry=read(reader,recipe.registry);need(registry.body.version===1&&registry.body.kind==='accepted-administrative-handoffs-v1'&&Array.isArray(registry.body.entries),'Accepted registry required');
 const products={},groups=[],acquisitions=[],allIds=new Set();
 function emit(id,handoff,source,native,models,locators={}){
  const component_ids=source.source_rule.expected_ids;
  need(unique(component_ids)&&component_ids.every(x=>!allIds.has(x)),'Duplicate/empty recipe scope');component_ids.forEach(x=>allIds.add(x));
  need(equal(native.additive.scope_ids,component_ids),'SOURCE/NATIVE scope differs');
  const sourceName=id+'-source-template.json',nativeName=id+'-native-template.json';
  need(!products[sourceName],'Duplicate group label');products[sourceName]=bytes(source);products[nativeName]=bytes(native);
  const group={id,handoff_id:handoff.entry.id,component_ids,source_template:sourceName,native_template:nativeName,
   source_destination:recipe.mode==='retained-groups'?source.destination:recipe.destination_prefix+'-'+id+'-source',native_destination:recipe.mode==='retained-groups'?native.destination:recipe.destination_prefix+'-'+id+'-native',...locators,models};
  groups.push(group);
  for(const [stage,request] of [['source',source],['native',native]])for(const p of [request.report,...request.baseline.pins,...(request.source_rule??request.additive).inputs]){
   if(p.kind||(recipe.mode==='greedy-model'&&stage==='native'&&nativeKeys.some(k=>request.additive[k]===p.path)))continue;acquisitions.push({source:operatorPin(p),destination:p.path,role:stage+'-input'});}
 }
 if(recipe.mode==='retained-groups'){
  need(recipe.compatibility==='literal-historical-v1'&&Array.isArray(recipe.groups)&&recipe.groups.length,'Explicit literal retained replay required');
  const cover=new Map();
  for(const g of recipe.groups){need(/^[a-z0-9-]+$/.test(g.id)&&g.component_ids===undefined,'Replay IDs derive only from issued SOURCE');
   const h=accepted(reader,registry,g),source=read(reader,g.source_template).body,native=read(reader,g.native_template).body,r=source.source_rule;
   need(source.operation==='retained-land-source-premises-v1'&&native.operation==='unactivated-additive-native-batch-v1'&&r?.profile==='retained-consumed-administrative-source'&&equal(r.cohort_ids,h.entry.cohort_ids)&&r.registry_path===registry.pin.path&&r.cases_path===h.pin.path&&equal(r.inputs.find(p=>p.path===r.cases_path),h.pin),'Replay template differs from accepted whole handoff');
   need(unique(r.expected_ids)&&equal(r.expected_ids,h.entry.cohort_ids.filter(id=>r.expected_ids.includes(id)))&&equal(native.baseline,source.baseline),'Replay original ordered scope differs');
   const prior=cover.get(h.entry.id)??[];cover.set(h.entry.id,[...prior,...r.expected_ids]);
   emit(g.id,h,source,native,{source:modelRequestBudget(source),native:modelRequestBudget(native)},{source_locator:g.source_template,native_locator:g.native_template});
  }
  for(const [id,ids]of cover){const entry=registry.body.entries.find(e=>e.id===id);need(equal([...ids].sort(),[...entry.cohort_ids].sort()),'Replay omitted accepted handoff components');}
 }else{
  need(recipe.compatibility===undefined&&Array.isArray(recipe.handoffs)&&recipe.handoffs.length,'New admitted handoffs required');
  for(const selection of recipe.handoffs){
   need(selection.component_ids===undefined&&selection.groups===undefined,'Component/group lists are not new recipe inputs');
   const h=accepted(reader,registry,selection),sourceBase=resourceRequest(read(reader,selection.source_template).body,selection.source_resources);
   need(sourceBase.operation==='retained-land-source-premises-v1'&&sourceBase.source_rule?.profile==='retained-consumed-administrative-source'&&sourceBase.source_rule.geometry_scope==='full-component','Registered administrative full-component recipe required');
   need(Array.isArray(selection.targets)&&selection.targets.length&&new Set(selection.targets.map(t=>t.target_id)).size===selection.targets.length,'Explicit unique target mapping required');
   const targetMap=new Map(selection.targets.map(t=>{const n=resourceRequest(read(reader,t.native_template).body,selection.native_resources);need(n.operation==='unactivated-additive-native-batch-v1'&&n.additive?.source_profile===sourceBase.source_rule.profile&&equal(n.baseline,sourceBase.baseline)&&equal(n.report,sourceBase.report)&&equal(n.parent,sourceBase.parent),'Native recipe baseline/report/parent differs');return [t.target_id,{...t,native:n}];}));
   need(equal([...targetMap.keys()].sort(),[...h.entry.target_ids].sort()),'Target mapping must cover exactly the accepted handoff');
   const pool=uniquePins([...sourceBase.source_rule.inputs,...[...targetMap.values()].flatMap(t=>t.native.additive.inputs)]);
   const admin=adminProducts(h,pool),locators=locatorMap(reader,selection,h),physical=h.scope.original_physical_comparison_bindings;
   need(Array.isArray(physical)&&new Set(physical.map(p=>p.component_id)).size===physical.length,'Unique physical comparison bindings required');
   const sourceProducts=h.scope.physical_restoration.restorations.filter(p=>/^sources-\d{3}\.jsonl\.gz$/.test(p.path)).map(p=>p.path);need(sourceProducts.length,'Missing complete queried source metadata product');
   const rows=h.rows.map(row=>{const bindings=physical.filter(p=>p.component_id===row.component_id);need(bindings.length===1&&bindings[0].physical_comparison?.row?.component_id===row.component_id,'Missing exact component physical comparison');const direct=directProduct(bindings[0]),mapped=locators?.get(row.component_id);need(!direct||!mapped||direct===mapped,'Physical locator conflicts with handoff');const original=direct??mapped;need(original,'Missing per-case physical-product locator');const target=targetMap.get(row.retained_payload.target_stable_location_id);return {id:row.component_id,original,target};});
   let ordinal=0;
   function construct(members){
    const id=recipe.id+'-'+String(groups.length+1).padStart(3,'0'),nativeBase=members[0].target.native;
    need(members.every(r=>equal(nativeInvariant(r.target.native),nativeInvariant(nativeBase))),'Mixed native method/runtime recipe');
    const originals=[...new Set([...members.map(r=>r.original),...sourceProducts])].map(name=>physicalProduct(h,name,sourceBase.report,acquisitions));
    const banks=uniquePins(members.map(r=>{const found=r.target.native.additive.inputs.filter(p=>p.path===r.target.bank_path);need(found.length===1,'Target mapping bank lacks exact exemplar pin');return found[0];}));
    const rule={...structuredClone(sourceBase.source_rule),cohort_ids:h.entry.cohort_ids,expected_ids:members.map(r=>r.id),registry_path:registry.pin.path,
     ...Object.fromEntries(sourceKeys.map(k=>[k,h.pin.path])),administrative_products:admin,original_products:originals.map(p=>({original_product_path:p.original_product_path,path:p.path})),target_banks:banks.map(p=>p.path)};
    rule.inputs=uniquePins([...sourceCommon(sourceBase),h.pin,operatorPin(registry.pin),...originals,...admin,...banks]);
    const source={...sourceBase,destination:recipe.destination_prefix+'-'+id+'-source',source_rule:rule};
    const ownerParts=new Map(),nativeExtra=[];
    for(const member of members){const n=member.target.native,s=n.additive;for(const part of s.owner_parts??[]){const old=ownerParts.get(part.path);need(!old||equal(old,part),'Conflicting native owner operand');ownerParts.set(part.path,part);}
     const sourceNames=new Set([...sourceBase.source_rule.inputs.map(p=>p.path),...sourceKeys.map(k=>sourceBase.source_rule[k]),...nativeKeys.map(k=>s[k])]);
     // Keep only expressly admitted native owner/bounds/latitude/manifest operands.
     const needed=new Set([s.manifest_path,s.bounds_path,s.latitudes_path,...(s.owner_parts??[]).map(p=>p.path)]);
     nativeExtra.push(...s.inputs.filter(p=>needed.has(p.path)&&!sourceNames.has(p.path)));}
    const s=nativeBase.additive,slots=nativeKeys.map(k=>{const p=s.inputs.filter(p=>p.path===s[k]);need(p.length===1,'Native exemplar lacks five real predecessor slots');return p[0];});
    const native={...nativeBase,destination:recipe.destination_prefix+'-'+id+'-native',additive:{...s,scope_ids:rule.expected_ids,owner_parts:[...ownerParts.values()],inputs:uniquePins([...rule.inputs,...nativeExtra,...slots])}};
    const models={source:modelRequestBudget(source),native:modelRequestBudget(native,{predecessor_allowance:selection.predecessor_allowance,request_bytes_bound:selection.native_request_bytes_bound})};
    need(selection.predecessor_allowance&&Number.isSafeInteger(selection.native_request_bytes_bound),'Explicit future SOURCE output/request bounds required');
    return {id,source,native,models};
   }
   let pending=[];
   for(const row of rows){
    if(pending.length&&!equal(nativeInvariant(pending[0].target.native),nativeInvariant(row.target.native))){const built=construct(pending);emit(built.id,h,built.source,built.native,built.models);pending=[];}
    let built=construct([...pending,row]);
    if(!built.models.source.fits||!built.models.native.fits){need(pending.length,'Singleton exceeds admitted SOURCE/NATIVE resource budget: '+row.id);const previous=construct(pending);emit(previous.id,h,previous.source,previous.native,previous.models);pending=[];built=construct([row]);need(built.models.source.fits&&built.models.native.fits,'Singleton exceeds admitted SOURCE/NATIVE resource budget: '+row.id);}
    pending.push(row);ordinal++;
   }
   if(pending.length){const built=construct(pending);emit(built.id,h,built.source,built.native,built.models);}
   need(ordinal===h.entry.cohort_ids.length,'Incomplete recipe materialization');
  }
 }
 const transport=new Map();
 for(const item of acquisitions){const p=item.source;pinCosts(p);const key=sha(bytes({mode:p.mode,bytes:p.bytes,sha256:p.sha256,uncompressed_bytes:p.uncompressed_bytes??null,uncompressed_sha256:p.uncompressed_sha256??null}));const prior=transport.get(key)??{identity:key,source:p,destinations:[],uses:[]};if(!prior.destinations.includes(item.destination))prior.destinations.push(item.destination);if(!prior.uses.includes(item.role))prior.uses.push(item.role);transport.set(key,prior);}
 const acquisition_plan={version:1,kind:'transport-only-deduplicated-input-plan',products:[...transport.values()],unique_encoded_bytes:add([...transport.values()].map(p=>p.source.bytes)),limits:['Acquisition reuse only. Every operator phase authenticates and accounts for its complete issued input closure.']};
 const index={version:1,mode:recipe.mode,registry:registry.pin,...(recipe.compatibility?{compatibility:recipe.compatibility}:{}),groups,acquisition_plan,limits:['Metadata planning is not live resource admission, source approval, execution, or current-bank qualification.','Native templates retain real exemplar slots only until genuine SOURCE results replace them; templates must never execute directly.']};
 products['recipe-index.json']=bytes(index);return {products,groups,index,acquisition_plan};
}
return {materializeRecipe, modelRequestBudget, recheckNativeRequest};
})();

// Existing-contract constructor, scoped to avoid mixing scientific identities.
export const {constructOriginalAuthority, constructAuthorityRegistry} = (() => {
// Scratch integration fragment. Replace only the two absolute import specifiers
// with their normal relative repository imports in delivery-handoff-advance.mjs.
// These constructors read committed evidence and never execute a science operator.

const need = (ok, message) => { if (!ok) throw Error(message); };
const sha = raw => createHash('sha256').update(raw).digest('hex');
const same = (a, b) => valueBytes(a).equals(valueBytes(b));
const FILE = 32 * 1024 * 1024;
const safe = name => typeof name === 'string' && !name.startsWith('/') && !name.includes('\\') && !name.includes('\0')
  && name.split('/').every(part => part && part !== '.' && part !== '..');
// Preserve already charged state even when another reader owns the shared
// budget. This adapter cannot declare another reader's live graph released.
const outerFrame = reader => Math.max(reader.metadataBytes, reader.used - reader.runtimeBytes - reader.executionBytes - reader.outputBytes);
const identity = p => ({commit: p.commit, path: p.path, mode: p.mode, git_blob_oid: p.git_blob_oid ?? p.blob, bytes: p.bytes, sha256: p.sha256});

function exactLocator(locator) {
  need(locator && Object.keys(locator).sort().join(',') === 'commit,path'
    && /^[a-f0-9]{40}$/.test(locator.commit) && safe(locator.path),
  'Supply exact commit/path locators only; derived hashes and IDs are not inputs');
  return locator;
}

// The declared decoded bound is read from a committed publication, never from
// caller-authored derived fields. The actual bytes must agree before it escapes.
function committedBody(reader, locator, declared = null, parse = false) {
  exactLocator(locator);
  const {commit, path: name} = locator, d = reader.descriptor(name, commit);
  const decoded = declared?.uncompressed_bytes ?? 0;
  need(Number.isSafeInteger(decoded) && decoded >= 0 && decoded <= FILE, 'Invalid committed decoded bound');
  const scratch = (parse ? 4 * (decoded || d.bytes) : 2 * decoded);
  need(Number.isSafeInteger(scratch) && reader.used + scratch <= reader.phaseLimit, 'Authority constructor metadata exceeds admitted phase');
  reader.used += scratch;
  const encoded = reader.read(name, {version: commit, decoded});
  const pin = {...identity({...d, sha256: sha(encoded)})};
  let raw = encoded;
  if (declared?.uncompressed_bytes !== undefined) {
    raw = gunzipSync(encoded, {maxOutputLength: Math.max(1, decoded)});
    pin.uncompressed_bytes = raw.length; pin.uncompressed_sha256 = sha(raw);
  }
  if (declared) for (const key of ['bytes', 'sha256', 'uncompressed_bytes', 'uncompressed_sha256'])
    need(pin[key] === declared[key], 'Committed publication/member differs: ' + name + ' ' + key);
  return {pin, ...(parse ? {body: JSON.parse(raw)} : {})};
}

function publicationMembers(reader, locator) {
  need(path.posix.basename(exactLocator(locator).path) === 'publication.json', 'Locate the committed publication.json');
  const {pin, body} = committedBody(reader, locator, null, true);
  need(body.version === 1 && body.complete === true && body.facts && body.inventory, 'Missing complete committed publication');
  const member = name => ({commit: pin.commit, path: path.posix.join(path.posix.dirname(pin.path), name)});
  const facts = committedBody(reader, member('facts.json'), body.facts, true);
  const inventory = committedBody(reader, member('inventory.jsonl.gz'), body.inventory);
  return {pin, body, facts, inventory, member};
}

function deriveOriginalBinding(reader, inputs) {
  need(inputs && Object.keys(inputs).sort().join(',') === 'native_operating,native_publication,source_publication', 'Require SOURCE publication, NATIVE publication and NATIVE operating locators');
  for (const locator of Object.values(inputs)) exactLocator(locator);
  const source = publicationMembers(reader, inputs.source_publication);
  const native = publicationMembers(reader, inputs.native_publication);
  const issued = (facts, kind) => {
    const old = facts.body.request;
    need(old && old.commit && old.path, 'Missing original ' + kind + ' issued request locator');
    const result = committedBody(reader, {commit: old.commit, path: old.path}, null, true);
    need(same(result.pin, identity(old)), 'Original ' + kind + ' issued request descriptor differs');
    return result;
  };
  const sourceRequest = issued(source.facts, 'SOURCE'), nativeRequest = issued(native.facts, 'NATIVE');
  const spec = nativeRequest.body.additive;
  need(spec && Array.isArray(spec.inputs), 'Missing native SOURCE predecessor');
  const aliases = [];
  for (const [key, published] of [['facts_path', source.facts.pin], ['publication_path', source.pin], ['inventory_path', source.inventory.pin]]) {
    const matches = spec.inputs.filter(p => p.path === spec[key]);
    need(matches.length === 1, 'Missing/duplicate original SOURCE predecessor: ' + key);
    const original = matches[0];
    if (original.kind === 'completed-inventory-body') aliases.push({original, published});
    else need(same(identity(original), identity(published)), 'Native SOURCE predecessor points to another committed body: ' + key);
  }
  need(Array.isArray(native.body.assets) && native.body.assets.length > 0 && native.body.assets.length <= 512,
    'Missing bounded native publication asset roster');
  const names = native.body.assets.map(p => p.path);
  need(new Set(names).size === names.length && names.every(n => safe(n) && !n.includes('/')), 'Duplicate/unsafe native publication asset');
  const assets = native.body.assets.map(p => committedBody(reader, native.member(p.path), p).pin);
  const manifest = assets.filter(p => path.posix.basename(p.path) === 'base-native-manifest.json');
  const envelopes = native.body.assets.filter(p => p.path === 'release-envelope.json');
  need(envelopes.length === 1, 'Native publication omits its release envelope');
  const envelope = committedBody(reader, native.member(envelopes[0].path), envelopes[0], true).body;
  const ledgerRole = envelope.additiveRelease?.ledger;
  need(ledgerRole && safe(ledgerRole.path) && ledgerRole.path.startsWith('additive-repairs/'), 'Missing published original ledger role');
  const ledger = assets.filter(p => path.posix.basename(p.path) === path.posix.basename(ledgerRole.path)
    && p.bytes === ledgerRole.bytes && p.sha256 === ledgerRole.sha256);
  need(manifest.length === 1 && ledger.length === 1, 'Native publication omits its unique base manifest or original ledger');
  const operating = committedBody(reader, inputs.native_operating).pin;
  return {version: 1, kind: 'original-issued-rule-source-custody-v1',
    original_pins: {source_request: sourceRequest.pin, source_facts: source.facts.pin, native_request: nativeRequest.pin,
      native_facts: native.facts.pin, native_manifest: manifest[0], ledger: ledger[0]},
    ...(aliases.length ? {source_output_aliases: aliases} : {}),
    native_proof: {publication: native.pin, inventory: native.inventory.pin, operating, assets}};
}

function constructOriginalAuthority(reader, inputs) {
  need(reader instanceof ImmutableReader, 'Require the existing ImmutableReader');
  const outerMetadata = outerFrame(reader);
  const binding = deriveOriginalBinding(reader, inputs);
  // The discovery bodies are out of scope. Carry only the produced binding into
  // the existing validators, which own their unchanged whole-body accounting.
  reader.metadataBytes = outerMetadata + 4 * valueBytes({inputs, binding, inventory: [...reader.inventory.values()]}).length;
  const custody = readOriginalRuleAuthority(reader, binding.original_pins, binding.source_output_aliases ?? []);
  qualifyOriginalSourceAuthority(custody);
  const native = qualifyOriginalNativeAuthority(custody, binding.native_proof);
  return {products: {'original-rule-preimage.json': valueBytes(custody.rule_preimage), 'authority-binding.json': valueBytes(binding)},
    component_ids: [...custody.source_scope_ids], ledger: binding.original_pins.ledger, rule_sha256: custody.rule_sha256,
    limitations: native.limitations};
}

// Invoke only after the preceding bodies are committed. Policy is the existing
// selected-consumer policy; the complete original program is re-authenticated by
// readRetainedRegistryAuthority. A registry alone never approves selection.
function constructAuthorityRegistry(reader, authorities) {
  need(reader instanceof ImmutableReader && Array.isArray(authorities) && authorities.length > 0 && authorities.length <= 512,
    'Require bounded committed authority pairs and existing ImmutableReader');
  const entries = [], seen = new Set(), components = new Set();
  const outerMetadata = outerFrame(reader);
  function committedEntry(locators) {
    need(locators && Object.keys(locators).sort().join(',') === 'rule_preimage,source_authority', 'Require committed preimage/binding locators only');
    for (const locator of Object.values(locators)) exactLocator(locator);
    const rule = committedBody(reader, locators.rule_preimage, null, true), binding = committedBody(reader, locators.source_authority);
    need(rule.pin.sha256 === valueSha(rule.body), 'Original rule preimage is not the canonical complete body');
    const body = {policy_id: 'retained-source-literal-additions', policy_version: 1, rule_sha256: rule.pin.sha256,
      rule_preimage: rule.pin, source_authority: binding.pin};
    const entry = {authority_sha256: valueSha(body), ...body};
    need(!seen.has(entry.authority_sha256), 'Duplicate committed original authority'); seen.add(entry.authority_sha256);
    reader.metadataBytes += 4 * valueBytes({rule: rule.body, entry}).length;
    const proof = readRetainedRegistryAuthority(reader, entry);
    return {entry, scope: [...proof.source_scope_ids]};
  }
  for (const locators of authorities) {
    // Previous qualified graphs are no longer retained. Keep the registry and
    // unique component roster live across the next existing-reader phase.
    reader.metadataBytes = outerMetadata + 4 * valueBytes({authorities, entries, scope: [...components], seen: [...seen], inventory: [...reader.inventory.values()]}).length;
    reader.phase();
    const {entry, scope} = committedEntry(locators);
    for (const id of scope) { need(!components.has(id), 'Overlapping original authority component'); components.add(id); }
    entries.push(entry);
  }
  entries.sort((a, b) => a.authority_sha256.localeCompare(b.authority_sha256));
  return {'authority-registry.json': valueBytes({version: 1, kind: 'retained-rule-authority-registry-v1', entries})};
}
return {constructOriginalAuthority, constructAuthorityRegistry};
})();

export function deliveryAuthorityReader(root, pinReader) {
  const outer = pinReader.budget.snapshot(), git = pinReader.git;
  class DeliveryReader extends ImmutableReader {
    git(...args) { return git(...args); }
    admit(pin, decoded = 0) {
      const extra = this.charged.has(pin.commit + ':' + pin.path) ? 0 : 1;
      need(outer.accounted_descriptors + this.charged.size + extra <= 512, 'Shared delivery/authority descriptor budget exceeded');
      super.admit(pin, decoded);
    }
  }
  return new DeliveryReader(root, git('rev-parse', 'HEAD').toString().trim(), {
    allowance: pinReader.budget.allowance, metadataBytes: 8 * 1024 * 1024 + outer.accounted_bytes});
}

// Reuse the already authenticated gh account only at an actual cold fetch.
// The token stays in this one subprocess environment; no credential is created
// or persisted, and warm verification never consults account credentials.
export function deliveryAcquisitionExecute({execute = execFileSync,
  readToken = () => execFileSync('gh', ['auth', 'token'], {encoding: 'utf8', maxBuffer: 16384, timeout: 20_000}).trim()} = {}) {
  let token;
  return (command, args, options) => {
    if (command === 'git' && args.includes('fetch')) {
      need(args.includes('https://github.com/ChengshuLi/WorldAtlas.git'), 'Unexpected acquisition repository');
      token ??= readToken(); need(typeof token === 'string' && token.trim(), 'Existing gh login required for cold acquisition');
      const env = {...options.env, GIT_CONFIG_COUNT: '3',
        GIT_CONFIG_KEY_2: 'http.https://github.com/.extraheader',
        GIT_CONFIG_VALUE_2: 'AUTHORIZATION: basic ' + Buffer.from('x-access-token:' + token).toString('base64')};
      return execute(command, args, {...options, env});
    }
    return execute(command, args, options);
  };
}

// Exact-body acquisition reuses the existing prefetch importer and ordinary writer.
export const acquireDeliveryInputs = (() => {
// Thin adapter for the existing exact Git object acquisition. It does not
// decode scientific records, restore logical products or execute operators.
const CAP=33554432;
const need=(v,m)=>{if(!v)throw Error(m);};
const sha=raw=>createHash('sha256').update(raw).digest('hex');
const oid=raw=>createHash('sha1').update('blob '+raw.length+'\0').update(raw).digest('hex');
const hex=(s,n)=>typeof s==='string'&&new RegExp(`^[a-f0-9]{${n}}$`).test(s);
const canonical=v=>Array.isArray(v)?v.map(canonical):v&&typeof v==='object'?Object.fromEntries(Object.keys(v).sort().map(k=>[k,canonical(v[k])])):v;
const bytes=v=>Buffer.from(JSON.stringify(canonical(v))+'\n');
const safe=s=>typeof s==='string'&&!path.isAbsolute(s)&&/^[A-Za-z0-9_.\/-]+$/.test(s)&&s.split('/').every(x=>x&&x!=='.'&&x!=='..');
const bodyIdentity=p=>({mode:p.mode,bytes:p.bytes,sha256:p.sha256,uncompressed_bytes:p.uncompressed_bytes??null,uncompressed_sha256:p.uncompressed_sha256??null});

// Narrow extraction of canonical-restoration.mjs ordinary/read/writeExactObject:
// an existing destination is reauthenticated, never overwritten. Interrupted
// incomplete members remain a refusal; completed members are safe to resume.
function ordinaryPath(root,relative){
 need(safe(relative)&&path.isAbsolute(root)&&fs.realpathSync(root)===root,'Ordinary acquisition root/path required');
 let current=root;for(const part of relative.split('/')){current=path.join(current,part);const stat=fs.lstatSync(current,{throwIfNoEntry:false});if(stat)need(!stat.isSymbolicLink()&&(current===path.join(root,relative)?stat.isFile():stat.isDirectory()),'Nonordinary acquisition destination');}return current;
}
function readExactFile(root,relative,pin){
 const name=ordinaryPath(root,relative),stat=fs.lstatSync(name,{throwIfNoEntry:false});if(!stat)return null;
 need(stat.isFile()&&stat.size===pin.bytes&&(stat.mode&0o777)===0o644,'Existing acquisition body size/mode differs');
 const fd=fs.openSync(name,fs.constants.O_RDONLY|fs.constants.O_NOFOLLOW);
 try{const opened=fs.fstatSync(fd);need(opened.isFile()&&opened.dev===stat.dev&&opened.ino===stat.ino&&opened.size===stat.size,'Acquisition file identity drift');const raw=Buffer.alloc(pin.bytes+1);let n=0;
  while(n<raw.length){const count=fs.readSync(fd,raw,n,raw.length-n,null);if(!count)break;n+=count;}
  const after=fs.fstatSync(fd),current=fs.lstatSync(name);need(n===pin.bytes&&after.size===stat.size&&after.mtimeMs===opened.mtimeMs&&after.ctimeMs===opened.ctimeMs&&current.dev===opened.dev&&current.ino===opened.ino&&!current.isSymbolicLink(),'Acquisition file changed during read');
  const body=raw.subarray(0,n);need(sha(body)===pin.sha256&&oid(body)===(pin.git_blob_oid??pin.blob),'Existing acquisition body hash differs');return body;
 }finally{fs.closeSync(fd);}
}
function writeExactFile(root,relative,pin,raw){
 need(raw.length===pin.bytes&&sha(raw)===pin.sha256&&oid(raw)===(pin.git_blob_oid??pin.blob),'Materialized source bytes differ');
 if(readExactFile(root,relative,pin))return false;
 const file=ordinaryPath(root,relative);fs.mkdirSync(path.dirname(file),{recursive:true});ordinaryPath(root,relative);
 fs.writeFileSync(file,raw,{flag:'wx',mode:0o644});readExactFile(root,relative,pin);return true;
}

async function acquireDeliveryInputs(plan,root,{execute=execFileSync,token,onMaterialized=()=>{},limits,budget}={}){
 let sharedBefore=null;
 if(budget){need(typeof budget.add==='function'&&typeof budget.snapshot==='function','Existing candidate budget required');sharedBefore=budget.snapshot();
  need(['limit_bytes','accounted_bytes','reserved_review_bytes'].every(k=>Number.isSafeInteger(sharedBefore[k])&&sharedBefore[k]>=0),'Finite shared acquisition allowance required');
  limits={...limits,total:Math.min(limits?.total??Number.MAX_SAFE_INTEGER,sharedBefore.limit_bytes-sharedBefore.accounted_bytes-sharedBefore.reserved_review_bytes)};
 }
 need(limits&&typeof limits==='object'&&!Array.isArray(limits)&&Object.keys(limits).every(k=>['member','total','entries','destinations'].includes(k)),'Explicit acquisition allowance required');
 const allowance={member:CAP,entries:512,destinations:512,...limits};
 for(const value of Object.values(allowance))need(Number.isSafeInteger(value)&&value>=0,'Acquisition allowance must be finite');
 need(Number.isSafeInteger(allowance.total)&&allowance.member<=CAP&&allowance.entries<=512,'Existing whole-member and descriptor limits required');
 need(plan?.version===1&&plan.kind==='transport-only-deduplicated-input-plan'&&Array.isArray(plan.products)&&plan.products.length>0&&plan.products.length<=allowance.entries,'Bounded delivery acquisition plan required');
 need(path.isAbsolute(root)&&fs.realpathSync(root)===root,'Actual ordinary acquisition root required');
 const rows=[],objects=new Map(),destinations=new Map(),descriptors=new Map();let declared=0,decodedTotal=0,materializedTotal=0;
 for(const item of plan.products){
  const p=item.source;need(p&&safe(p.path)&&hex(p.commit,40)&&p.mode==='100644'&&hex(p.git_blob_oid??p.blob,40)&&hex(p.sha256,64)&&Number.isSafeInteger(p.bytes)&&p.bytes>=0&&p.bytes<=allowance.member,'Complete immutable acquisition pin required');
  need(p.git_blob_oid===undefined||p.blob===undefined||p.git_blob_oid===p.blob,'Conflicting acquisition object aliases');
  need((p.uncompressed_bytes===undefined)===(p.uncompressed_sha256===undefined),'Incomplete decoded acquisition identity');
  if(p.uncompressed_bytes!==undefined){need(Number.isSafeInteger(p.uncompressed_bytes)&&p.uncompressed_bytes>=0&&p.uncompressed_bytes<=allowance.member&&hex(p.uncompressed_sha256,64),'Bounded decoded acquisition identity required');decodedTotal+=p.uncompressed_bytes;need(Number.isSafeInteger(decodedTotal),'Complete decoded acquisition bound');}
  need(item.identity===sha(bytes(bodyIdentity(p)))&&Array.isArray(item.destinations)&&item.destinations.length>0&&item.destinations.length<=512,'Acquisition identity/destination inventory differs');
  declared+=p.bytes;need(Number.isSafeInteger(declared)&&declared<=allowance.total,'Complete declared acquisition bound');
  const key=p.git_blob_oid??p.blob,old=objects.get(key);
  need(!old||(old.pin.bytes===p.bytes&&old.pin.sha256===p.sha256&&old.pin.mode===p.mode),'Conflicting immutable acquisition body');
  const group=old??{pin:p,pins:[],destinations:new Set()};group.pins.push(p);objects.set(key,group);
  const descriptorKey=p.commit+':'+p.path,prior=descriptors.get(descriptorKey);
  need(!prior||(prior.git_blob_oid??prior.blob)===key,'Conflicting immutable acquisition path');descriptors.set(descriptorKey,p);
  for(const destination of item.destinations){
   need(safe(destination),'Unsafe acquisition destination');
   if(destination===p.path)continue; // Immutable consumers read this from Git.
   need(destination.startsWith('.cache/additive-native-gap-repair/delivery/'+p.sha256+'/'),'Only content-addressed physical aliases may be materialized');
   const before=destinations.get(destination);need(!before||before===key,'Conflicting materialization destination');
   if(!before){materializedTotal+=p.bytes;need(Number.isSafeInteger(materializedTotal)&&destinations.size<allowance.destinations,'Complete physical alias acquisition bound');}
   destinations.set(destination,key);group.destinations.add(destination);
  }
  rows.push(p);
 }
 need(plan.unique_encoded_bytes===declared,'Declared acquisition aggregate differs');
 const totalModeled=declared+decodedTotal+materializedTotal;
 need(Number.isSafeInteger(totalModeled)&&totalModeled<=allowance.total,'Encoded + decoded + physical placement exceeds explicit acquisition allowance');
 // The CLI's existing budget already includes config, plan and reserved receipts.
 // Admit this entire body inventory before any body read, fetch or file write.
 if(budget){for(const p of rows){budget.add({bytes:p.bytes});if(p.uncompressed_bytes!==undefined)budget.add({bytes:p.uncompressed_bytes});}
  for(const [destination,key]of destinations)budget.add({bytes:objects.get(key).pin.bytes});budget.snapshot();
 }
 for(const [destination,key]of destinations)readExactFile(root,destination,objects.get(key).pin);
 const acquisition=createAcquisition({repo:root,token,execute,limits:{member:allowance.member,total:allowance.total,entries:allowance.entries},loadDescriptor:async(version,name)=>{const p=descriptors.get(version+':'+name);need(p,'Undeclared acquisition metadata');return {type:'blob',mode:p.mode,sha:p.git_blob_oid??p.blob,size:p.bytes};}});
 const admitted=[];
 for(const p of rows)admitted.push(await acquisition.descriptor(p.commit,p.path,{mode:p.mode,git_blob_oid:p.git_blob_oid??p.blob,bytes:p.bytes,sha256:p.sha256}));
 acquisition.acquire(admitted); // Existing import checks and missing-OID resume.
 const gitEnv=Object.fromEntries(Object.entries(process.env).filter(([key])=>!key.startsWith('GIT_')));
 Object.assign(gitEnv,{GIT_NO_LAZY_FETCH:'1',GIT_NO_REPLACE_OBJECTS:'1',GIT_CONFIG_NOSYSTEM:'1',GIT_CONFIG_GLOBAL:'/dev/null',GIT_TERMINAL_PROMPT:'0'});
 const outcomes=[];let bodyReads=0;
 for(const [key,group] of objects){
  const raw=execute('git',['-c','core.hooksPath=/dev/null','-C',root,'cat-file','blob',key],{env:gitEnv,maxBuffer:CAP+1,timeout:60000,stdio:['ignore','pipe','pipe']});bodyReads++;
  need(Buffer.isBuffer(raw)&&raw.length===group.pin.bytes&&sha(raw)===group.pin.sha256&&oid(raw)===key,'Acquired body changed before materialization');
  const decodedPins=group.pins.filter(p=>p.uncompressed_bytes!==undefined);
  if(decodedPins.length){const decoded=gunzipSync(raw,{maxOutputLength:Math.max(1,allowance.member)});for(const p of decodedPins)need(decoded.length===p.uncompressed_bytes&&sha(decoded)===p.uncompressed_sha256,'Acquired decoded identity differs');}
  for(const destination of group.destinations){const created=writeExactFile(root,destination,group.pin,raw);outcomes.push({path:destination,bytes:raw.length,sha256:group.pin.sha256,created});if(created)onMaterialized({path:destination,bytes:raw.length,sha256:group.pin.sha256});}
 }
 return {version:1,kind:'materialized-delivery-inputs-v1',plan_sha256:sha(bytes(plan)),status:'complete',...acquisition.stats,
  materialization_body_reads:bodyReads,materialized_files:outcomes.filter(p=>p.created).length,resumed_files:outcomes.filter(p=>!p.created).length,files:outcomes,
  admission:{limits:allowance,declared_encoded_bytes:declared,declared_decoded_bytes:decodedTotal,physical_alias_bytes:materializedTotal,physical_aliases:destinations.size,total_modeled_bytes:totalModeled,...(budget?{shared_budget:budget.snapshot()}:{})},
  limits:['Transport and exact-byte physical aliases only. Every scientific operator still authenticates and accounts for its own complete inputs.','Completed objects/files resume by their actual identities; partial or corrupted destination files are refused and preserved.']};
}
return acquireDeliveryInputs;
})();
