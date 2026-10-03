import fs from 'node:fs';
import {githubAPI, githubPages, readClaim, workSpec} from './issue-claim-contract.mjs';
import {validateIssuePRBody} from './check-handoff-scope.mjs';
import {sha256} from './evidence-quality.mjs';

// Read-only inventory. Output belongs to the caller's engineering job; never edit old packets.
const output = process.argv[2];
if (!/^coordination\/engineering\/[-a-z0-9]+\/[-a-z0-9]+\.json$/.test(output ?? '')) throw Error('Supply an owned engineering inventory path');
const repo = process.env.GITHUB_REPOSITORY ?? 'ChengshuLi/WorldAtlas', api = githubAPI(process.env.GH_TOKEN);
const [rows, pulls] = await Promise.all([githubPages(api, `/repos/${repo}/issues?state=open`), githubPages(api, `/repos/${repo}/pulls?state=open`)]);
const issues = rows.filter(row => !row.pull_request), candidates = new Set();
const prs = pulls.map(pr => {
  let linked;
  try {linked = validateIssuePRBody(pr.body ?? '').github_issue; candidates.add(linked);} catch { /* explicitly unlinked */ }
  return {number: pr.number, head_sha: pr.head.sha, branch: pr.head.ref, issue: linked ?? null};
});
for (const issue of issues) if (issue.labels.some(label => label.name === 'status:claimed')) candidates.add(issue.number);
const claims = [];
for (const number of candidates) {
  const claim = readClaim(await githubPages(api, `/repos/${repo}/issues/${number}/comments`));
  claims.push({issue: number, claim: claim ?? null, decision: 'Retain original scope and evidence; do not retroactively enforce new requirements'});
}
const inventory = {version: 1, repository: repo, observed_at: new Date().toISOString(),
  decision: 'Existing issues preserve their scope. This is not factual approval; explicit adoption remains possible.',
  bounded_follow_up: 624, issues: issues.map(issue => {
    let spec; try {spec = workSpec(issue.body);} catch { /* legacy/unstructured remains explicit */ }
    return {number: issue.number, created_at: issue.created_at, issue_body_sha256: sha256(issue.body ?? ''),
      mode: spec?.mode ?? null, has_quality_contract: Boolean(spec?.evidence_quality)};
  }), claims, open_prs: prs, limits: ['Point-in-time snapshot; new work before activation is also grandfathered by creation timestamp',
    'Claim labels are only discovery hints; listed claims were read from canonical bot comments',
    'No evidence packet is approved by this inventory; known deficiencies remain in their bounded correction issues']};
fs.mkdirSync(output.slice(0, output.lastIndexOf('/')), {recursive: true});
fs.writeFileSync(output, JSON.stringify(inventory, null, 2) + '\n', {flag: 'wx'});
console.log(JSON.stringify({issues: inventory.issues.length, claims: claims.length, open_prs: prs.length, output}));
