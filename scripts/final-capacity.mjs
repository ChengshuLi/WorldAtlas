import {performance} from 'node:perf_hooks';
import {safeEvidencePath, sha256} from './evidence-quality.mjs';
import {evidenceRequirement} from './evidence-policy.mjs';
import {githubPages, workSpec} from './issue-claim-contract.mjs';
import {validateReviewReceipt, reviewBindingRequired} from './premerge-evidence.mjs';
import {IMMUTABLE_CACHE_BYTES, IMMUTABLE_CACHE_ENTRIES} from './immutable-git-blobs.mjs';

export const CAPACITY_WAIT_MS = 61 * 60 * 1000;
const VALIDATION_MARGIN_MS = 13 * 60 * 1000;
const need = (value, message) => {if (!value) throw Error(message);};
const commitID = value => /^[a-f0-9]{40}$/.test(value ?? '');
const pages = rows => Math.floor(rows.length / 100) + 1;

// This is an estimate/rejection gate, never an evidence acceptance. The real
// byte, review and authority validators run again after capacity is observed.
export async function inventoryFinalEvidence({api, repo, pr, issue, reservation, files, policy}) {
  const requirement = evidenceRequirement(issue, workSpec(issue.body), policy, pr.head.ref);
  if (!requirement.required) return {blob_calls: 0, water: false, proof_calls: 0, descriptor_count: 0, original_count: 0};
  const root = `/repos/${repo}`;
  const readTree = async commit => {
    need(commitID(commit), 'Capacity inventory needs an exact commit');
    const object = await api(`${root}/git/commits/${commit}`);
    need(commitID(object?.tree?.sha), 'Capacity inventory needs an exact tree');
    const tree = await api(`${root}/git/trees/${object.tree.sha}?recursive=1`);
    need(tree?.truncated === false && Array.isArray(tree.tree), 'Capacity inventory needs complete trees');
    const entries = new Map(tree.tree.map(row => [row.path, row]));
    need(entries.size === tree.tree.length, 'Capacity inventory has duplicate tree paths');
    return entries;
  };
  const entries = await readTree(pr.head.sha);
  const entry = (tree, name, maximum = 32 * 1024 * 1024) => {
    safeEvidencePath(name); const row = tree.get(name);
    need(row?.type === 'blob' && ['100644', '100755'].includes(row.mode) && commitID(row.sha) &&
      Number.isSafeInteger(row.size) && row.size >= 0 && row.size <= maximum, 'Capacity inventory has invalid file binding');
    return row;
  };
  const manifestEntry = entry(entries, requirement.manifestPath, 1024 * 1024);
  const blob = await api(`${root}/git/blobs/${manifestEntry.sha}`);
  need(blob?.encoding === 'base64' && blob.size === manifestEntry.size && blob.sha === manifestEntry.sha,
    'Capacity manifest is incomplete');
  const raw = Buffer.from(blob.content, 'base64');
  need(raw.length === manifestEntry.size, 'Capacity manifest is incomplete');
  const manifest = JSON.parse(raw);
  need(Array.isArray(manifest.baseline?.files) && Array.isArray(manifest.outputs) && Array.isArray(manifest.sources),
    'Capacity inventory lacks bounded descriptors');
  const descriptors = [...manifest.baseline.files, ...manifest.outputs, ...manifest.sources.flatMap(source => {
    need(Array.isArray(source.files ?? []), 'Capacity source inventory is invalid'); return source.files ?? [];
  })];
  need(descriptors.length <= 512 && files.length === pr.changed_files && files.length <= 10000,
    'Capacity inventory exceeds existing descriptor/change limits');
  const baseline = await readTree(manifest.baseline.commit), base = await readTree(pr.base.sha);
  const loads = [[requirement.manifestPath, pr.head.sha, manifestEntry]];
  for (const descriptor of manifest.baseline.files) loads.push([descriptor.path, manifest.baseline.commit, entry(baseline, descriptor.path)]);
  for (const descriptor of [...manifest.outputs, ...manifest.sources.flatMap(source => source.files ?? [])])
    loads.push([descriptor.path, pr.head.sha, entry(entries, descriptor.path)]);
  const originals = files.filter(file => file.status !== 'added');
  for (const file of originals) loads.push([file.previous_filename ?? file.filename, pr.base.sha,
    entry(base, file.previous_filename ?? file.filename)]);
  const vintagePaths = new Map(), oids = new Map();
  for (const [name, vintage, row] of loads) {
    vintagePaths.set(`${vintage}:${name}`, row);
    need(!oids.has(row.sha) || oids.get(row.sha) === row.size, 'Immutable OID has conflicting tree sizes');
    oids.set(row.sha, row.size);
  }
  need([...vintagePaths.values()].reduce((sum, row) => sum + row.size, 0) <= 256 * 1024 * 1024 + 1024 * 1024,
    'Capacity inventory exceeds existing remote byte budget');
  const dossiers = manifest.geographic_adjudications ?? [];
  need(Array.isArray(dossiers) && dossiers.length <= 64, 'Capacity source dossier count is unbounded');
  const comments = await githubPages(api, `${root}/issues/${pr.number}/comments`), latest = new Map();
  for (const comment of comments) {
    if (!['OWNER', 'MEMBER', 'COLLABORATOR'].includes(comment.author_association)) continue;
    for (const match of (comment.body ?? '').matchAll(/<!-- worldatlas-review:v1\s*([\s\S]*?)\s*-->/g)) {
      const receipt = JSON.parse(match[1]); if (receipt.head_sha !== pr.head.sha) continue;
      if (!latest.has(receipt.reviewer_worker_id) || latest.get(receipt.reviewer_worker_id).id < comment.id)
        latest.set(receipt.reviewer_worker_id, {id: comment.id, receipt});
    }
  }
  need(![...latest.values()].some(row => row.receipt.outcome === 'changes-requested'), 'Current review rejects final validation');
  let accepted = false;
  for (const {receipt} of latest.values()) {
    try {
      // Empty limits intentionally cannot approve limited evidence. This early
      // rejection checks known bindings; the full validator computes limits later.
      validateReviewReceipt(receipt, {pr, issue, manifest, manifestHash: sha256(raw), files, limits: [],
        author: reservation.worker_id, reviewKind: requirement.quality.review_kind,
        requireContractBinding: reviewBindingRequired(pr, policy)}); accepted = true;
    } catch { /* Another current receipt may bind this exact inventory. */ }
  }
  need(accepted, 'Missing current exact-head review before costly evidence');
  const fitsCache = oids.size <= IMMUTABLE_CACHE_ENTRIES && [...oids.values()].reduce((a, b) => a + b, 0) <= IMMUTABLE_CACHE_BYTES;
  // A water pass repeats full validation and dossier loads. Count every request
  // if the verified tree-bound inventory cannot all fit the existing cache.
  const blobCalls = fitsCache ? oids.size : loads.length * (dossiers.length ? 2 : 1) + dossiers.length + 1;
  return {blob_calls: blobCalls, water: dossiers.length > 0, descriptor_count: descriptors.length,
    original_count: originals.length, immutable_oids: oids.size, cache_fit: fitsCache, review_pages: pages(comments)};
}

export function finalRequestBound({inventory, metadataCalls, admissionCalls = 0, proofCalls = 0, artifactPages = 1}) {
  need([metadataCalls, admissionCalls, proofCalls, artifactPages, inventory.blob_calls].every(n => Number.isSafeInteger(n) && n >= 0),
    'Cannot establish a finite final request bound');
  // Two metadata passes: fresh rejection gates after waiting and full final
  // inspection. Additional source authority includes its fresh rechecks. The
  // 48 additional calls allocate 16 to bounded cleanup/receipt, 20 to final
  // mutable guards/guarded merge, 8 to candidate/proof trees and 4 to artifact
  // download/notification. The paid-call guard preserves the 16-call recovery
  // portion outside validation and rejects unexpected pagination growth.
  const required = inventory.blob_calls + metadataCalls * (inventory.water ? 5 : 2) + admissionCalls + proofCalls + artifactPages + 48;
  need(Number.isSafeInteger(required) && required > 0, 'Cannot establish a finite final request bound');
  return required;
}

export function capacityObservation(payload) {
  const core = payload?.resources?.core;
  need(core && ['limit', 'remaining', 'reset'].every(key => Number.isSafeInteger(core[key])) &&
    core.limit > 0 && core.remaining >= 0 && core.remaining <= core.limit && core.reset > 0, 'Invalid or unavailable authenticated core capacity');
  const headers = payload.capacity_headers;
  if (headers !== undefined) {
    need(headers && ['limit', 'remaining', 'reset'].every(key => Number.isSafeInteger(headers[key])) &&
      headers.limit > 0 && headers.remaining >= 0 && headers.remaining <= headers.limit && headers.reset > 0,
      'Invalid authenticated capacity headers');
    // Different windows cannot safely be combined. Current request headers own
    // enforcement; a lower body observation remains a conservative constraint.
    need(headers.reset === core.reset && headers.limit === core.limit, 'Authenticated capacity observations disagree');
    return {limit: headers.limit, remaining: Math.min(headers.remaining, core.remaining), reset: headers.reset};
  }
  return {limit: core.limit, remaining: core.remaining, reset: core.reset};
}

export async function waitForFinalCapacity({api, required, now = () => performance.now(), wallNow = Date.now,
  sleep = ms => new Promise(resolve => setTimeout(resolve, ms)), deadlineMs = CAPACITY_WAIT_MS, pollMs = 30000, onObservation = () => {}}) {
  need(Number.isSafeInteger(required) && required > 0 && Number.isFinite(deadlineMs) && deadlineMs > 0 &&
    Number.isFinite(pollMs) && pollMs > 0 && pollMs <= 60000, 'Invalid bounded final capacity wait');
  const started = now(); let observations = 0;
  for (;;) {
    need(now() - started < deadlineMs, 'Final capacity wait timed out; bounded intervention required');
    const observed = capacityObservation(await api('/rate_limit'));
    need(now() - started < deadlineMs, 'Final capacity wait timed out; bounded intervention required');
    const elapsedMs = Math.max(0, now() - started); observations++;
    onObservation({phase: 'final-capacity', required, ...observed, observations, elapsed_ms: Math.floor(elapsedMs), reserved: false});
    need(required <= observed.limit, 'Final request bound exceeds observed core limit; bounded intervention required');
    if (observed.remaining >= required) return {...observed, required, observations, waited_ms: Math.floor(elapsedMs), reserved: false};
    const untilReset = observed.reset * 1000 - wallNow();
    // A past reset does not manufacture capacity. Continue bounded polling for
    // an actual new observation, including early capacity or delayed resets.
    await sleep(Math.min(pollMs, untilReset > 0 ? Math.max(1000, untilReset + 1000) : pollMs, deadlineMs - elapsedMs));
  }
}

export function finalRequestBudget(api) {
  let maximum = null, planning = false, used = 0, deadline;
  const checkDeadline = () => need(!deadline || deadline() > 0, 'Final capacity/validation deadline exhausted; bounded intervention required');
  return {setDeadline(value) {deadline = value;}, setLimit(value, isPlanning = false) {
    need(Number.isSafeInteger(value) && value > 0, 'Invalid final API call bound');
    maximum = value; planning = isPlanning; used = 0;
  }, api: async (...args) => {
    checkDeadline();
    if (args[0] === '/rate_limit' && (args[1] ?? 'GET') === 'GET') {
      const value = await api(...args); checkDeadline(); return value;
    }
    need(maximum !== null, 'Final API capacity has not been observed');
    if (used >= maximum) {
      const error = Error('Final inventory grew beyond safe request bound; bounded intervention required');
      if (planning) error.planningNeeded = maximum + 17;
      throw error;
    }
    used++;
    const value = await api(...args); checkDeadline(); return value;
  }};
}

export function boundedFinalAPI(api, maximum, {planning = false} = {}) {
  const budget = finalRequestBudget(api); budget.setLimit(maximum, planning); return budget.api;
}

export async function beginFinalPlanning(options) {
  const timing = options.capacityTiming ?? {}, now = timing.now ?? (() => performance.now());
  const started = now(), total = timing.deadlineMs ?? CAPACITY_WAIT_MS;
  const remaining = () => total - (now() - started);
  let receipt = {phase: 'final-planning-capacity', reserved: false};
  try {
    // No repository GET precedes this observation. A zero-capacity job can wait
    // for the reset before even its cheap head/FIFO/manifest planning reads.
    // Reserve 16 calls for bounded rejection cleanup and its durable receipt.
    const capacity = await waitForFinalCapacity({...timing, now, api: options.api, required: 17,
      onObservation: row => {receipt = {...row, phase: 'final-planning-capacity'}; options.capacityObserver?.(receipt);}});
    options.capacityBudget?.setLimit(capacity.remaining - 16, true);
    options.capacityBudget?.setDeadline(remaining);
    return {...options, capacityAPI: options.api,
      api: options.capacityBudget ? options.api : boundedFinalAPI(options.api, capacity.remaining - 16, {planning: true}),
      planningCapacity: capacity, capacityDeadlineRemaining: remaining};
  } catch (error) {error.capacity = receipt; throw error;}
}

export async function paceFinalValidation(options, {inspect, admission = async () => {}}) {
  let metadataCalls = 0, admissionCalls = 0, proofCalls = 0, artifactPages = 0;
  const counted = async (...args) => {metadataCalls++; return options.api(...args);};
  const admissionAPI = async (...args) => {admissionCalls++; return options.api(...args);};
  let receipt = {phase: 'final-capacity', reserved: false, ...(options.planningCapacity ? {planning: options.planningCapacity} : {})};
  try {
    const proofInventory = async api => {
      if (!options.proofRunId) return;
      const run = await api(`/repos/${options.repo}/actions/runs/${options.proofRunId}`);
      need(run?.run_attempt === options.proofRunAttempt && run.status === 'completed' && run.conclusion === 'success',
        'Trusted proof changed before final evidence; resubmit unchanged head');
      await githubPages(async route => (await api(route)).jobs,
        `/repos/${options.repo}/actions/runs/${options.proofRunId}/attempts/${options.proofRunAttempt}/jobs`);
    };
    let before;
    for (let planningAttempt = 1; planningAttempt <= 3; planningAttempt++) {
      metadataCalls = 0; admissionCalls = 0; proofCalls = 0; artifactPages = 0;
      try {
        const currentPR = await counted(`/repos/${options.repo}/pulls/${options.number}`);
        need(currentPR.head?.sha === options.expectedHead, 'PR head changed; obtain fresh exact-head review');
        if (!currentPR.merged) {
          const current = await counted(`/repos/${options.repo}/git/ref/heads/main`);
          need(current.object?.sha === options.testedBase, 'Main advanced before capacity wait; resubmit unchanged head');
        }
        await admission(admissionAPI);
        before = await inspect({...options, api: counted, evidenceCheck: inventoryFinalEvidence});
        if (before.replayed) return {api: options.capacityAPI ?? options.api, receipt: {...receipt, status: 'already-merged'}};
        need(before.base === options.testedBase, 'Main advanced before capacity wait; resubmit unchanged head');
        await proofInventory(async (...args) => {proofCalls++; return options.api(...args);});
        need(Number.isSafeInteger(options.artifactRunId) && options.artifactRunId > 0,
          'Cannot bound final geographic artifact inventory');
        for (let page = 1, seen = 0; page <= 100; page++) {
          const response = await options.api(`/repos/${options.repo}/actions/runs/${options.artifactRunId}/artifacts?per_page=100&page=${page}`);
          artifactPages++;
          need(Array.isArray(response?.artifacts) && Number.isSafeInteger(response.total_count) &&
            response.total_count >= 0 && response.total_count <= 10000, 'Cannot bound final geographic artifact inventory');
          seen += response.artifacts.length;
          if (seen === response.total_count) break;
          need(response.artifacts.length === 100 && seen < response.total_count && page < 100,
            'Incomplete final geographic artifact inventory');
        }
        receipt.planning_attempts = planningAttempt; break;
      } catch (error) {
        if (!error.planningNeeded || planningAttempt === 3 || !options.capacityAPI) throw error;
        // Only our own proven planning-call deficit permits this retry. API403,
        // authority failure and incomplete inventories remain original failures.
        // Discard every partial mutable inventory and start all metadata again.
        const capacity = await waitForFinalCapacity({...options.capacityTiming, api: options.capacityAPI,
          deadlineMs: options.capacityDeadlineRemaining(), required: error.planningNeeded,
          onObservation: row => {
            const observation = {...row, phase: 'final-planning-capacity', planning_attempt: planningAttempt};
            receipt = {...receipt, planning_retry: observation}; options.capacityObserver?.(observation);
          }});
        options.capacityBudget?.setLimit(capacity.remaining - 16, true);
        options = {...options, api: options.capacityBudget ? options.capacityAPI :
          boundedFinalAPI(options.capacityAPI, capacity.remaining - 16, {planning: true})};
      }
    }
    const required = finalRequestBound({inventory: before.evidence, metadataCalls, admissionCalls,
      proofCalls: proofCalls * 2, artifactPages});
    receipt = {...receipt, required, metadata_calls: metadataCalls, admission_calls: admissionCalls,
      proof_calls: proofCalls, artifact_pages: artifactPages, inventory: before.evidence};
    const capacity = await waitForFinalCapacity({...options.capacityTiming,
      ...(options.capacityDeadlineRemaining ? {deadlineMs: options.capacityDeadlineRemaining()} : {}),
      api: options.capacityAPI ?? options.api, required,
      onObservation: observation => {
        receipt = {...receipt, ...observation}; options.capacityObserver?.(observation);
      }});
    receipt = {...receipt, ...capacity, status: 'observed-sufficient'};
    options.capacityBudget?.setLimit(required - 16);
    options.capacityBudget?.setDeadline(() => options.capacityDeadlineRemaining() + VALIDATION_MARGIN_MS);
    const api = options.capacityBudget ? options.capacityAPI : boundedFinalAPI(options.capacityAPI ?? options.api, required - 16);
    receipt.validation_call_bound = required - 16;
    // Re-read every mutable rejection gate after waiting. These are not reused
    // by the normal completeIntegration inspection and full evidence validator.
    await admission(api);
    const after = await inspect({...options, api, evidenceCheck: inventoryFinalEvidence});
    need(!after.replayed && after.base === before.base && after.base === options.testedBase &&
      after.pr.head.sha === before.pr.head.sha && after.pr.body === before.pr.body && after.pr.title === before.pr.title &&
      after.pr.base.sha === before.pr.base.sha && after.issue.body === before.issue.body &&
      after.reservation.claim_id === before.reservation.claim_id && after.reservation.worker_id === before.reservation.worker_id,
      'Authority or tested base changed during capacity wait; resubmit unchanged head');
    await proofInventory(api);
    return {api, receipt};
  } catch (error) {error.capacity = receipt; throw error;}
}
