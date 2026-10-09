import fs from 'node:fs';
import {requestAccounting,quotaDelay,completeReads} from './github-quota.mjs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {githubAPI, githubPages, readClaim, verifyClaimForPR} from './issue-claim-contract.mjs';
import {validateIssuePRBody} from './check-handoff-scope.mjs';
import {integrationProfile} from './integration-profile.mjs';

export async function selectIntegrationProfile({event, repo, api, now = Date.now()}) {
  const scheduled = event.pull_request;
  if (!scheduled || !Number.isSafeInteger(scheduled.number) || scheduled.number < 1 ||
      !/^[-\w.]+\/[-\w.]+$/.test(repo ?? '') || event.repository?.full_name !== repo) {
    throw Error('Supply the current repository pull_request event');
  }
  const prefix = `/repos/${repo}`;
  const pr = await api(`${prefix}/pulls/${scheduled.number}`);
  if (pr.number !== scheduled.number || pr.state !== 'open' ||
      pr.head?.sha !== scheduled.head?.sha || pr.head?.ref !== scheduled.head?.ref ||
      pr.base?.repo?.full_name !== repo) throw Error('PR changed since this check was scheduled');
  const files = await githubPages(api, `${prefix}/pulls/${pr.number}/files`);
  if (!Number.isSafeInteger(pr.changed_files) || files.length !== pr.changed_files ||
      new Set(files.map(file => file.filename)).size !== files.length) {
    throw Error('Incomplete changed-path inventory');
  }
  let reservation = {};
  if (pr.head.ref.startsWith('geography/')) {
    const {github_issue} = validateIssuePRBody(pr.body ?? '');
    const [issue, comments] = await completeReads([
      api(`${prefix}/issues/${github_issue}`),
      githubPages(api, `${prefix}/issues/${github_issue}/comments`)
    ]);
    if (issue.number !== github_issue || readClaim(comments)?.issue_number !== github_issue) {
      throw Error('Reservation must belong to the linked issue');
    }
    // Reuse the claim contract: current holder, exact branch, ready geography
    // issue, safe owned prefixes and equality with the reviewed issue scope.
    // Profile selection is not a replacement for the merge/evidence gates.
    reservation = verifyClaimForPR({branch: pr.head.ref, issue, comments, now});
  }
  const profile = integrationProfile(pr.head.ref, files, reservation);
  return {profile, shards: profile === 'full' ? [0, 1, 2] : [0]};
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const event = JSON.parse(fs.readFileSync(process.env.GITHUB_EVENT_PATH, 'utf8'));
  const accounting=requestAccounting('integration-profile');
  try{
    const result = await selectIntegrationProfile({event, repo: process.env.GITHUB_REPOSITORY,
      api: githubAPI(process.env.GH_TOKEN,{onRequest:accounting.observe})});
    fs.appendFileSync(process.env.GITHUB_OUTPUT,
      `profile=${result.profile}\nshards=${JSON.stringify(result.shards)}\n`);
    console.log(JSON.stringify({integration_profile: result.profile, shards: result.shards}));
  }catch(error){
    const delay=quotaDelay(error);
    console.log(JSON.stringify({status:'refused',reason:error.message,...(error.github?{api_error:error.github}:{}),
      retryable:delay!==null,...(delay!==null?{retry_at:new Date(Date.now()+delay).toISOString()}:{})}));
    process.exitCode=1;
  }finally{console.log(JSON.stringify({request_accounting:accounting.receipt()}));}
}
