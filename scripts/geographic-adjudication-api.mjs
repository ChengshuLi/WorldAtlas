// Read-only exact-head authority; proposed dossiers never approve themselves.
import {githubPages, linkedPulls, verifyClaimForPR, workSpec} from './issue-claim-contract.mjs';
import {validateIssuePRBody, validateLanePaths} from './check-handoff-scope.mjs';
import {evidenceRequirement, loadEvidencePolicy} from './evidence-policy.mjs';
import {checkPremergeEvidence, validateReviewReceipt, reviewBindingRequired} from './premerge-evidence.mjs';
import {safeEvidencePath, sha256} from './evidence-quality.mjs';

export const METHOD = 'worldatlas-geographic-water-adjudication-v1';
export const TARGET = 'current-reference-geography';
const MAX_FILE = 32 * 1024 * 1024;
const need = (ok, message) => { if (!ok) throw Error(message); };
const hash = value => /^[a-f0-9]{64}$/.test(value ?? '');
const sorted = value => Array.isArray(value) && value.every(hash) &&
  new Set(value).size === value.length && JSON.stringify([...value].sort()) === JSON.stringify(value);
function stable(value) {
  if (Array.isArray(value)) return value.map(stable);
  if (value && typeof value === 'object') return Object.fromEntries(Object.keys(value).sort().map(key => [key, stable(value[key])]));
  return value;
}
// Match the shared Python canonical_json protocol, including its final newline.
export const bindingHash = value => sha256(JSON.stringify(stable(value)) + '\n');

async function candidateReader(api, repo, commit) {
  const object = await api(`/repos/${repo}/git/commits/${commit}`);
  const tree = await api(`/repos/${repo}/git/trees/${object.tree.sha}?recursive=1`);
  need(!tree.truncated && Array.isArray(tree.tree), 'Incomplete adjudication tree');
  const entries = new Map(tree.tree.map(row => [row.path, row]));
  let total = 0;
  return async (name, maximum = MAX_FILE) => {
    safeEvidencePath(name);
    const row = entries.get(name);
    need(row?.type === 'blob' && ['100644', '100755'].includes(row.mode) &&
      Number.isSafeInteger(row.size) && row.size > 0 && row.size <= maximum,
      'Missing, nonordinary or oversized adjudication file');
    total += row.size; need(total <= MAX_FILE, 'Adjudication transport exceeds decoded packet budget');
    const blob = await api(`/repos/${repo}/git/blobs/${row.sha}`);
    need(blob.encoding === 'base64', 'Unsupported adjudication blob encoding');
    const raw = Buffer.from(blob.content, 'base64');
    need(raw.length === row.size, 'Incomplete adjudication bytes');
    return raw;
  };
}

function latestReviews(comments, head) {
  const latest = new Map();
  for (const comment of comments) {
    if (!['OWNER', 'MEMBER', 'COLLABORATOR'].includes(comment.author_association)) continue;
    for (const match of (comment.body ?? '').matchAll(/<!-- worldatlas-review:v1\s*([\s\S]*?)\s*-->/g)) {
      const receipt = JSON.parse(match[1]);
      if (receipt.head_sha !== head) continue;
      const key = receipt.reviewer_worker_id;
      if (!latest.has(key) || latest.get(key).comment.id < comment.id) latest.set(key, {receipt, comment});
    }
  }
  need(![...latest.values()].some(row => row.receipt.outcome === 'changes-requested'),
    'Source decision has an unresolved independent rejection');
  const rows = [...latest.values()].sort((a, b) => b.comment.id - a.comment.id);
  need(rows.length, 'Missing current exact-head source decision');
  return rows[0];
}

function inspectDecision(decision, descriptor, dossier, manifest) {
  need(decision?.dossier_path === descriptor.path && decision.dossier_sha256 === descriptor.sha256 &&
    decision.target_context === TARGET && dossier.target_context === TARGET &&
    dossier.version === 1 && dossier.method_id === METHOD, 'Decision does not bind exact dossier/target');
  for (const [key, value] of Object.entries({target_water: 'supported', physical_provenance: 'accepted',
    temporal_suitability: 'accepted', resolution_suitability: 'accepted', target_uncertainty: 'resolved-for-this-target'})) {
    need(decision[key] === value, 'Unresolved or rejected target-specific physical-water evidence');
  }
  need(Array.isArray(decision.source_limits) && decision.source_limits.every(value => typeof value === 'string' && value.trim()),
    'Source scope limitations must be retained explicitly');
  need(Array.isArray(dossier.findings) && dossier.findings.length > 0 && dossier.findings.length <= 4096 &&
    sorted(decision.finding_sha256s) && decision.finding_sha256s.length === dossier.findings.length &&
    JSON.stringify(dossier.findings.map(row => row.sha256).sort()) === JSON.stringify(decision.finding_sha256s),
    'Missing, duplicate or incomplete exact-finding decisions');
  need(Array.isArray(dossier.source_refs) && dossier.source_refs.length > 0 && dossier.source_refs.length <= 32 &&
    decision.source_refs_sha256 === bindingHash(dossier.source_refs), 'Source/native-feature bindings differ from review');
  for (const ref of dossier.source_refs) {
    const source = manifest.sources.find(row => row.id === ref.source_id);
    const file = source?.files?.find(row => row.path === ref.path && row.sha256 === ref.sha256);
    need(source?.role === 'physical-surface-water' && source.retention === 'retained' &&
      source.verification === 'verified' && source.temporal_status === 'reference' &&
      source.license?.status === 'redistributable' && file &&
      (ref.path.endsWith('.gz') ? file.uncompressed_sha256 : file.sha256) === ref.decoded_sha256,
      'Require retained original, verified, licensed physical-water source bytes');
    for (const native of [ref.native_identity, ref.native_role]) {
      need(native && typeof native.property === 'string' && native.property.length > 0 &&
        (typeof native.value === 'string' || Number.isSafeInteger(native.value)), 'Unsupported native identity/role binding');
    }
    need(hash(ref.native_geometry_sha256), 'Missing original native water geometry digest');
  }
}

export async function collectGeographicApproval({api, repo, number, expectedHead, policy = loadEvidencePolicy()}) {
  need(/^[-\w.]+\/[-\w.]+$/.test(repo ?? '') && Number.isSafeInteger(number) && number > 0 &&
    /^[a-f0-9]{40}$/.test(expectedHead ?? ''), 'Require exact repository PR and reviewed head');
  const pr = await api(`/repos/${repo}/pulls/${number}`);
  need(pr.number === number && pr.head.sha === expectedHead && pr.state === 'open' && !pr.draft &&
    !pr.merged && pr.base.ref === 'main' && pr.head.repo?.full_name === repo, 'PR changed or lacks source-decision authority');
  const {github_issue} = validateIssuePRBody(pr.body ?? '');
  const issue = await api(`/repos/${repo}/issues/${github_issue}`);
  const reservation = verifyClaimForPR({branch: pr.head.ref, issue,
    comments: await githubPages(api, `/repos/${repo}/issues/${github_issue}/comments`),
    prs: await linkedPulls(api, repo, github_issue)});
  const files = await githubPages(api, `/repos/${repo}/pulls/${number}/files`);
  need(files.length === pr.changed_files && new Set(files.map(row => row.filename)).size === files.length,
    'Incomplete source-decision change inventory');
  validateLanePaths(pr.head.ref, files.flatMap(row => [row.filename, row.previous_filename].filter(Boolean)),
    {ownedPaths: reservation.owned_paths});
  const requirement = evidenceRequirement(issue, workSpec(issue.body), policy, pr.head.ref);
  need(requirement.required && policy.mode === 'enforce-new', 'Legacy/report-only evidence cannot authorize water exceptions');
  const read = await candidateReader(api, repo, expectedHead);
  const manifestRaw = await read(requirement.manifestPath, 1024 * 1024);
  const manifest = JSON.parse(manifestRaw), descriptors = manifest.geographic_adjudications;
  if (descriptors === undefined || (Array.isArray(descriptors) && descriptors.length === 0)) {
    return {version: 1, method_id: METHOD, status: 'not-requested', reviewed_head: expectedHead};
  }
  need(Array.isArray(descriptors) && descriptors.length <= 64 && new Set(descriptors.map(row => row.path)).size === descriptors.length,
    'Invalid or duplicate source-decision dossier inventory');
  const checked = await checkPremergeEvidence({api, repo, pr, issue, reservation, files, policy, review: true});
  // The current shared validator returns bytes-verified, not its overwritten
  // intermediate checked label. No legacy/report-failure result qualifies.
  need(checked.status === 'bytes-verified' && checked.review?.comment_id && checked.head_sha === expectedHead &&
    checked.manifest_sha256 === sha256(manifestRaw), 'Missing actual whole-file/exact-head review validation');
  const dossiers = [];
  const prefix = requirement.manifestPath.slice(0, requirement.manifestPath.lastIndexOf('/') + 1);
  for (const descriptor of descriptors) {
    safeEvidencePath(descriptor.path);
    need(descriptor.path.startsWith(prefix) && hash(descriptor.sha256) && manifest.outputs.some(row =>
      row.path === descriptor.path && row.sha256 === descriptor.sha256), 'Unowned or unbound source-decision dossier');
    const raw = await read(descriptor.path);
    need(sha256(raw) === descriptor.sha256, 'Reviewed dossier bytes changed');
    dossiers.push({path: descriptor.path, sha256: descriptor.sha256, bytes_base64: raw.toString('base64'), parsed: JSON.parse(raw)});
  }
  // Read latest authority after potentially long byte validation. Do not call
  // inspectMerge: requiring a green geography job here would create a cycle.
  const freshPR = await api(`/repos/${repo}/pulls/${number}`);
  const freshIssue = await api(`/repos/${repo}/issues/${github_issue}`);
  need(freshPR.head.sha === expectedHead && freshPR.body === pr.body && freshPR.title === pr.title &&
    freshIssue.body === issue.body && freshPR.state === 'open' && !freshPR.draft && !freshPR.merged &&
    freshPR.base.ref === 'main' && freshPR.head.repo?.full_name === repo, 'PR or source contract changed during byte validation');
  const freshReservation = verifyClaimForPR({branch: freshPR.head.ref, issue: freshIssue,
    comments: await githubPages(api, `/repos/${repo}/issues/${github_issue}/comments`),
    prs: await linkedPulls(api, repo, github_issue)});
  need(freshReservation.claim_id === reservation.claim_id && freshReservation.worker_id === reservation.worker_id,
    'Source reservation changed during validation');
  const {receipt, comment} = latestReviews(await githubPages(api, `/repos/${repo}/issues/${number}/comments`), expectedHead);
  need(comment.id === checked.review.comment_id, 'Source decision changed during byte validation; rerun same head');
  validateReviewReceipt(receipt, {pr: freshPR, issue: freshIssue, manifest, manifestHash: checked.manifest_sha256, files,
    limits: checked.limits, author: reservation.worker_id, reviewKind: requirement.quality.review_kind,
    requireContractBinding: reviewBindingRequired(freshPR, policy)});
  for (const name of ['source', 'geometry']) need(receipt.domains?.[name] &&
    ['accepted', 'accepted-with-limits'].includes(receipt.domains[name].outcome) &&
    typeof receipt.domains[name].scope === 'string' && receipt.domains[name].scope.trim(), 'Missing substantive source/geometry review');
  const review = receipt.geographic_adjudications;
  need(review?.version === 1 && Array.isArray(review.decisions) && review.decisions.length === dossiers.length &&
    new Set(review.decisions.map(row => row.dossier_path)).size === dossiers.length, 'Missing explicit per-dossier independent source decisions');
  for (const dossier of dossiers) {
    const decision = review.decisions.find(row => row.dossier_path === dossier.path);
    inspectDecision(decision, dossier, dossier.parsed, manifest);
    dossier.decision = decision; delete dossier.parsed;
  }
  dossiers.sort((a, b) => a.path.localeCompare(b.path));
  const authority = {version: 1, method_id: METHOD, pr_number: number, reviewed_head: expectedHead,
    claim_id: reservation.claim_id, issue_contract_sha256: sha256(issue.body),
    manifest_sha256: checked.manifest_sha256, review: {reviewer_worker_id: receipt.reviewer_worker_id,
      comment_id: comment.id, comment_body_sha256: sha256(comment.body)}, decisions: dossiers.map(row => row.decision)};
  need((await api(`/repos/${repo}/pulls/${number}`)).head.sha === expectedHead, 'PR head changed during source validation');
  return {version: 1, method_id: METHOD, status: 'reviewed', authority_sha256: bindingHash(authority),
    review: authority.review, authority, dossiers};
}
