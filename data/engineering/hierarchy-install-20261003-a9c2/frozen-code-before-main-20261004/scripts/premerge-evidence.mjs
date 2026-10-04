import {gunzipSync} from 'node:zlib';
import {sha256, validateEvidence, safeEvidencePath} from './evidence-quality.mjs';
import {githubPages, workSpec} from './issue-claim-contract.mjs';
import {validateLanePaths} from './check-handoff-scope.mjs';
import {evidenceRequirement, loadEvidencePolicy} from './evidence-policy.mjs';

const need = (ok, message) => { if (!ok) throw Error(message); };
const MAX_FILE = 32 * 1024 * 1024;
export const GEOMETRY_VERSION = 'worldatlas-evidence-geometry-v1';
export const PREPARATION_VERSION = 'worldatlas-evidence-preparation-v1';
const geometryPolicy = {
  axis_order: 'longitude-latitude', crs: 'EPSG:4326',
  area_method: 'WGS84 straight-source-edge ellipsoidal integral', distance_method: 'WGS84 inverse geodesic'
};

/** Strengthen byte receipts with actual output bindings and change accounting. No submitted code runs. */
export function validatePremergeManifest(manifest, {readFile, files, manifestPath, issue, spec, reservation, branch}) {
  const quality = spec.evidence_quality;
  validateLanePaths(branch, [manifestPath], {ownedPaths: reservation.owned_paths});
  need(manifest.worker_id === reservation.worker_id, 'Manifest worker differs from canonical reservation');
  const result = validateEvidence(manifest, {readFile, expectedIssue: issue.number,
    expectedLane: spec.mode, expectedSubjects: quality.subject_ids, expectedPins: quality.pins});
  const receipts = manifest.change_receipts;
  need(Array.isArray(receipts) && receipts.length === files.length && new Set(receipts.map(row => row.path)).size === receipts.length,
    'Incomplete changed-file receipts');
  const descriptors = [...manifest.baseline.files, ...manifest.sources.flatMap(source => source.files ?? []), ...manifest.outputs];
  const outputs = new Set(manifest.outputs.map(file => file.path));
  const retained = new Set(manifest.sources.flatMap(source => source.files?.map(file => file.path) ?? []));
  for (const file of files) {
    const row = receipts.find(row => row.path === file.filename);
    need(row?.status === file.status && row.previous_path === file.previous_filename, `Change receipt mismatch: ${file.filename}`);
    for (const name of [file.filename, file.previous_filename].filter(Boolean)) safeEvidencePath(name);
    if (file.status !== 'added') {
      const original = file.previous_filename ?? file.filename;
      need(/^[a-f0-9]{64}$/.test(row.original_sha256) && sha256(readFile(original, 'base')) === row.original_sha256,
        `Original change bytes mismatch: ${original}`);
    }
    if (file.status === 'removed') need(typeof row.reason === 'string' && row.reason.trim(), 'Deletion needs a preservation explanation');
    else if (file.filename !== manifestPath) need(outputs.has(file.filename) || retained.has(file.filename),
      `Changed file lacks whole-file output/source descriptor: ${file.filename}`);
    need(!(file.status !== 'added' && (retained.has(file.filename) || retained.has(file.previous_filename))),
      'Refresh must retain original source bytes in a new vintage');
    // Baseline source descriptors explicitly identify immutable originals, including deleted/renamed paths.
    need(!manifest.baseline.files.some(input => input.role === 'original-source' &&
      [file.filename, file.previous_filename].includes(input.path)), 'Cannot overwrite original-source baseline evidence');
  }
  need(descriptors.length <= 512, 'Evidence file inventory exceeds bounded review budget');
  const bindings = manifest.metric_bindings ?? [];
  need(bindings.length === manifest.metrics.length && new Set(bindings.map(row => row.metric_id)).size === bindings.length,
    'Every metric needs an actual generated-output binding');
  for (const metric of manifest.metrics) {
    const binding = bindings.find(row => row.metric_id === metric.id);
    need(binding && outputs.has(binding.path) && typeof binding.json_pointer === 'string' && binding.json_pointer.startsWith('/'), 'Invalid metric output binding');
    let raw = readFile(binding.path, 'candidate');
    if (binding.path.endsWith('.gz')) raw = gunzipSync(raw, {maxOutputLength: MAX_FILE});
    let value = JSON.parse(raw);
    for (const key of binding.json_pointer.slice(1).split('/').map(key => key.replaceAll('~1', '/').replaceAll('~0', '~'))) {
      need(value && Object.hasOwn(value, key), 'Metric pointer does not resolve'); value = value[key];
    }
    need(value === metric.value, `Generated result differs from ledger: ${metric.id}`);
  }
  for (const method of manifest.methods) {
    if (method.kind === 'geography') {
      need(method.helper_version === GEOMETRY_VERSION && Object.entries(geometryPolicy).every(([key, value]) => method[key] === value),
        'Unsupported geographic helper/coordinate/method policy');
    }
    if (method.kind === 'generator') need(method.helper_version === PREPARATION_VERSION, 'Unsupported immutable preparation helper');
    if (['geography', 'generator', 'measurement'].includes(method.kind)) {
      const controls = manifest.validation ?? [];
      const kinds = ['positive-control', 'negative-control', ...(method.kind === 'generator' ? ['reproducibility'] : [])];
      for (const kind of kinds) {
        const control = controls.find(row => row.method_id === method.id && row.kind === kind);
        need(control?.outcome === 'passed' && outputs.has(control.evidence_path), `Missing ${kind} result for ${method.id}`);
        const evidence = JSON.parse(readFile(control.evidence_path, 'candidate'));
        need(evidence.method_id === method.id && evidence.kind === kind && evidence.outcome === 'passed', 'Control bytes do not match receipt');
        if (kind === 'reproducibility') need(evidence.run_one_sha256 === evidence.run_two_sha256 && /^[a-f0-9]{64}$/.test(evidence.run_one_sha256), 'Two-run reproducibility hashes differ');
      }
    }
  }
  if (result.limits.length) need(manifest.stages.geographic_approval !== 'approved', 'Limited source evidence cannot approve geography');
  need(manifest.stages.geographic_approval !== 'approved' && manifest.stages.implementation !== 'published',
    'A premerge receipt cannot certify geographic approval or a deployment; use the existing publication gates');
  return {...result, change_files_checked: files.length, metric_bindings_checked: bindings.length};
}

/** Cooperative worker identities, not a security boundary between shared-account operators. */
export function validateReviewReceipt(receipt, {pr, manifest, manifestHash, files, limits, author, reviewKind = 'code'}) {
  need(receipt?.version === 1 && receipt.pr_number === pr.number && receipt.head_sha === pr.head.sha &&
    receipt.manifest_sha256 === manifestHash && receipt.author_worker_id === author &&
    typeof receipt.reviewer_worker_id === 'string' && receipt.reviewer_worker_id.trim() && receipt.reviewer_worker_id !== author,
    'Review must bind exact head, manifest and a distinct worker identity');
  const expectedFiles = [...new Set(files.flatMap(file => [file.filename, file.previous_filename].filter(Boolean)))].sort();
  need(JSON.stringify([...(receipt.inspected_files ?? [])].sort()) === JSON.stringify(expectedFiles), 'Review omitted changed/renamed files');
  const hashes = [...new Set([...manifest.baseline.files, ...manifest.outputs, ...manifest.sources.flatMap(source => source.files ?? [])].map(file => file.sha256))].sort();
  need(JSON.stringify([...(receipt.evidence_hashes ?? [])].sort()) === JSON.stringify(hashes), 'Review evidence hashes differ');
  need(receipt.outcome === 'accepted' && Array.isArray(receipt.limits) && limits.every(limit => receipt.limits.includes(limit)), 'Review rejected work or omitted verification limits');
  const required = ['implementation'];
  if (reviewKind !== 'code') required.push(reviewKind === 'source' ? 'source' : reviewKind);
  if (manifest.sources.length || ['geography', 'source-only', 'content'].includes(manifest.lane)) required.push('source');
  if (manifest.methods.some(method => method.kind === 'geography') || files.some(file => /(?:hierarchy|world-index|crosswalk|ellipsoidal|geometry)/.test(file.filename))) required.push('geometry');
  if (files.some(file => /(?:release|migration|identity|regional-approval)/.test(file.filename))) required.push('release');
  for (const domain of new Set(required)) {
    const review = receipt.domains?.[domain];
    need(review && ['accepted', 'accepted-with-limits'].includes(review.outcome) && typeof review.scope === 'string' && review.scope.trim() &&
      Array.isArray(review.limits), `Missing substantive ${domain} review`);
  }
  if (limits.length && required.includes('source')) need(receipt.domains.source.outcome === 'accepted-with-limits', 'Limited source review must retain limited status');
  return {reviewer: receipt.reviewer_worker_id, domains: [...new Set(required)], limits: receipt.limits};
}

async function remoteReader(api, repo, commits) {
  const trees = new Map(), cache = new Map();
  for (const [vintage, commit] of Object.entries(commits)) {
    const object = await api(`/repos/${repo}/git/commits/${commit}`);
    const tree = await api(`/repos/${repo}/git/trees/${object.tree.sha}?recursive=1`);
    need(!tree.truncated && Array.isArray(tree.tree), 'Incomplete repository tree; cannot verify evidence');
    trees.set(vintage, new Map(tree.tree.map(file => [file.path, file])));
  }
  let total = 0;
  async function load(name, vintage, max = MAX_FILE) {
    safeEvidencePath(name); const key = `${vintage}:${name}`;
    if (cache.has(key)) return cache.get(key);
    const entry = trees.get(vintage)?.get(name);
    need(entry?.type === 'blob' && ['100644', '100755'].includes(entry.mode) && entry.size <= max, 'Missing/oversized/nonordinary evidence file');
    total += entry.size; need(total <= 256 * 1024 * 1024, 'Remote evidence budget exceeded');
    const blob = await api(`/repos/${repo}/git/blobs/${entry.sha}`);
    need(blob.encoding === 'base64', 'Unsupported Git blob encoding');
    const bytes = Buffer.from(blob.content, 'base64'); need(bytes.length === entry.size, 'Incomplete Git blob bytes');
    cache.set(key, bytes); return bytes;
  }
  return {load, read: (name, vintage) => { const bytes = cache.get(`${vintage}:${name}`); need(bytes, 'Unloaded evidence bytes'); return bytes; }};
}

export async function checkPremergeEvidence({api, repo, pr, issue, reservation, files, policy = loadEvidencePolicy(), review = false}) {
  let requirement;
  try {
    const spec = workSpec(issue.body);
    requirement = evidenceRequirement(issue, spec, policy, pr.head.ref);
    if (!requirement.required) return {status: 'legacy-or-report-only', ...requirement, head_sha: pr.head.sha, limits: ['No versioned manifest was required or checked; no factual approval']};
    need(files.length === pr.changed_files, 'Incomplete PR change inventory');
    const initial = await remoteReader(api, repo, {candidate: pr.head.sha, base: pr.base.sha});
    const manifestBytes = await initial.load(requirement.manifestPath, 'candidate', 1024 * 1024);
    const manifest = JSON.parse(manifestBytes);
    need(Array.isArray(manifest.baseline?.files) && Array.isArray(manifest.sources) && Array.isArray(manifest.outputs) &&
      manifest.baseline.files.length + manifest.outputs.length + manifest.sources.flatMap(source => source.files ?? []).length <= 512,
      'Invalid or oversized evidence inventory');
    need(/^[a-f0-9]{40}$/.test(manifest.baseline?.commit ?? ''), 'Invalid evidence baseline');
    const comparison = await api(`/repos/${repo}/compare/${manifest.baseline.commit}...${pr.base.sha}`);
    need(['ahead', 'identical'].includes(comparison.status), 'Baseline is not an ancestor of PR base');
    const reader = await remoteReader(api, repo, {candidate: pr.head.sha, base: pr.base.sha, [manifest.baseline.commit]: manifest.baseline.commit});
    const loads = [...manifest.baseline.files.map(file => [file.path, manifest.baseline.commit]),
      ...manifest.sources.flatMap(source => source.files ?? []).map(file => [file.path, 'candidate']), ...manifest.outputs.map(file => [file.path, 'candidate']),
      ...files.filter(file => file.status !== 'added').map(file => [file.previous_filename ?? file.filename, 'base'])];
    for (const [name, vintage] of loads) await reader.load(name, vintage);
    const checked = validatePremergeManifest(manifest, {readFile: reader.read, files, manifestPath: requirement.manifestPath,
      issue, spec, reservation, branch: pr.head.ref});
    const result = {status: 'checked', head_sha: pr.head.sha, manifest_sha256: sha256(manifestBytes), ...checked};
    if (review) {
      const comments = await githubPages(api, `/repos/${repo}/issues/${pr.number}/comments`);
      const receipts = [];
      for (const comment of comments) {
        if (!['OWNER', 'MEMBER', 'COLLABORATOR'].includes(comment.author_association)) continue;
        const matches = [...(comment.body ?? '').matchAll(/<!-- worldatlas-review:v1\s*([\s\S]*?)\s*-->/g)];
        for (const match of matches) {
          const receipt = JSON.parse(match[1]);
          if (receipt.head_sha === pr.head.sha) receipts.push({receipt, comment});
        }
      }
      const latest = new Map();
      for (const row of receipts) {
        const key = row.receipt.reviewer_worker_id;
        if (!latest.has(key) || latest.get(key).comment.id < row.comment.id) latest.set(key, row);
      }
      need(![...latest.values()].some(row => row.receipt.outcome === 'changes-requested'), 'Current head has an unresolved independent review');
      const candidates = [...latest.values()].sort((a, b) => b.comment.id - a.comment.id);
      need(candidates.length, 'Missing independent exact-head review receipt');
      result.review = validateReviewReceipt(candidates[0].receipt, {pr, manifest, manifestHash: result.manifest_sha256, files,
        limits: checked.limits, author: reservation.worker_id, reviewKind: requirement.quality.review_kind});
      result.review.comment_id = candidates[0].comment.id;
    }
    return result;
  } catch (error) {
    if (policy.mode === 'enforce-new') throw error;
    return {status: 'report-failure', head_sha: pr.head.sha, reason: error.message, limits: ['Report-only rollout; not an approval']};
  }
}
