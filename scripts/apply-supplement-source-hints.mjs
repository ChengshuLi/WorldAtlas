// Apply a reviewed, hashed offline plan. Default operation is read-only preflight.
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {isDeepStrictEqual} from 'node:util';
import {readClaim, githubPages, linkedPulls} from './issue-claim-contract.mjs';

const repo = 'ChengshuLi/WorldAtlas';
const hash = value => createHash('sha256').update(value).digest('hex');
const need = (condition, message) => { if (!condition) throw Error(message); };
const oldPath = 'data/macro-foundation/new-location-source-profiles-v4.json.gz';
const retainedPath = 'data/reference-migrations/macro-improvements-v4/queue-checkpoint/new-location-source-profiles-v4.json.gz';

function scope(body) {
  const matches = [...body.matchAll(/```json[^\S\n]*\n(.*?)\n```/gs)]
    .map(match => ({match, value: JSON.parse(match[1])})).filter(row => row.value.source_profile_hints);
  need(matches.length === 1, 'Expected one supplemental source-hint scope');
  return matches[0];
}

export function verifyRepair(row, issue, claim, pulls) {
  need(issue.number === row.number && issue.state === row.state, 'Issue identity/state changed');
  need(!claim?.active && !pulls.some(pr => pr.state === 'open'), 'Target still has an active worker or PR');
  need(hash(row.body) === row.after_body_sha256, 'Candidate body hash changed');
  need(hash(issue.body) === row.before_body_sha256 || hash(issue.body) === row.after_body_sha256,
    'Issue body changed after planning; replan rather than overwrite another edit');
  if (hash(issue.body) === row.after_body_sha256) return 'already-corrected';
  const before = scope(issue.body), after = scope(row.body);
  const outside = ({match}, body) => body.slice(0, match.index) + body.slice(match.index + match[0].length);
  need(outside(before, issue.body) === outside(after, row.body), 'Non-scope instruction/history changed');
  const normalize = value => {
    const result = structuredClone(value);
    delete result.source_profile_artifact;
    for (const hint of result.source_profile_hints) {
      need([oldPath, retainedPath].includes(hint.durable_full_source_profile_path), 'Unexpected profile pointer');
      hint.durable_full_source_profile_path = oldPath;
      delete hint.full_source_profile_hash_scope;
    }
    return result;
  };
  need(isDeepStrictEqual(normalize(before.value), normalize(after.value)),
    'Release, subjects, ownership or unrelated source fields changed');
  need(after.value.source_profile_artifact?.path === retainedPath &&
    after.value.source_profile_hints.every(hint => hint.durable_full_source_profile_path === retainedPath &&
      hint.full_source_profile_hash_scope === 'canonical-entry-utf8-json-without-trailing-newline'),
    'Candidate does not restore the retained pointer');
  return 'eligible';
}

export async function applyPlan(plan, api, {apply = false, checkpoint = () => {}} = {}) {
  need(plan.version === 1 && plan.issue === 554 && Array.isArray(plan.repairs), 'Wrong bounded repair plan');
  need(JSON.stringify(plan.repairs.map(row => row.number)) === JSON.stringify([520,521,522,523,524,525,526,527]),
    'Plan must cover exactly the original eight supplemental issues');
  const receipt = {issue: 554, applied: apply, completed: false, results: [],
    limits: ['GitHub instruction corrections only; no source evidence, work contracts, completion state or live atlas changes.']};
  checkpoint(receipt);
  async function inspect(row) {
    const issue = await api(`/repos/${repo}/issues/${row.number}`);
    const comments = await githubPages(api, `/repos/${repo}/issues/${row.number}/comments`);
    const pulls = await linkedPulls(api, repo, row.number);
    return {issue, result: verifyRepair(row, issue, readClaim(comments), pulls)};
  }
  // Establish eligibility for the entire batch before the first write.
  for (const row of plan.repairs) await inspect(row);
  for (const row of plan.repairs) {
    const {issue, result} = await inspect(row); // fresh check immediately before each write
    if (apply && result === 'eligible') {
      await api(`/repos/${repo}/issues/${row.number}`, 'PATCH', {body: row.body});
    }
    const after = apply ? await api(`/repos/${repo}/issues/${row.number}`) : issue;
    need(!apply || hash(after.body) === row.after_body_sha256, 'GitHub body readback mismatch');
    need(after.state === issue.state && JSON.stringify(after.labels) === JSON.stringify(issue.labels) &&
      JSON.stringify(after.assignees) === JSON.stringify(issue.assignees), 'Issue state/labels/assignees changed');
    receipt.results.push({number: row.number, result: apply ? result === 'eligible' ? 'corrected-and-read-back' : result : 'preflight-passed',
      before_body_sha256: hash(issue.body), observed_body_sha256: hash(after.body), expected_body_sha256: row.after_body_sha256,
      completion_state_preserved: true, worker_contract_and_scope_preserved: true});
    checkpoint(receipt); // retain partial proof after each settled write
  }
  receipt.completed = true;
  checkpoint(receipt);
  return receipt;
}

async function main() {
  const [planFile, expectedHash, receiptFile, mode] = process.argv.slice(2);
  need(planFile && /^[a-f0-9]{64}$/.test(expectedHash ?? '') && receiptFile && (!mode || mode === '--apply'),
    'Usage: node scripts/apply-supplement-source-hints.mjs PLAN SHA256 NEW-RECEIPT [--apply]');
  const bytes = fs.readFileSync(planFile);
  need(hash(bytes) === expectedHash, 'Reviewed plan bytes changed');
  need(!fs.existsSync(receiptFile), 'Use a new receipt path; preserve previous attempts');
  const api = async (route, method = 'GET', body) => JSON.parse(execFileSync('gh',
    ['api', route, ...(method === 'GET' ? [] : ['--method', method, '--input', '-'])],
    {encoding: 'utf8', maxBuffer: 8 * 1024 * 1024, ...(body ? {input: JSON.stringify(body)} : {})}));
  const checkpoint = receipt => fs.writeFileSync(receiptFile, JSON.stringify({...receipt, plan_sha256: expectedHash}, null, 2) + '\n');
  const result = await applyPlan(JSON.parse(bytes), api, {apply: mode === '--apply', checkpoint});
  console.log(JSON.stringify({completed: result.completed, applied: result.applied, receipt: receiptFile}));
}
if (process.argv[1] === fileURLToPath(import.meta.url)) await main();
