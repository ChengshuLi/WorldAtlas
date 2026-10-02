import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {validateIssuePRBody,validateIssueMetadata} from './check-handoff-scope.mjs';

export async function checkLinkedIssue({branch,event,token,fetchIssue=fetch}){
 const pr=event.pull_request,repo=event.repository?.full_name;
 if(!pr||!/^[-\w.]+\/[-\w.]+$/.test(repo??''))throw Error('Supply a repository pull_request event');
 const {github_issue,issue_action}=validateIssuePRBody(pr.body??'');
 if(!token)throw Error('A read-only GitHub token is required');
 const response=await fetchIssue(`https://api.github.com/repos/${repo}/issues/${github_issue}`,{headers:{Authorization:`Bearer ${token}`,Accept:'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'},signal:AbortSignal.timeout(15000)});
 if(!response.ok)throw Error(`Could not read linked GitHub issue (HTTP ${response.status})`);
 const metadata=validateIssueMetadata(branch,await response.json());
 return {github_issue,issue_action,...metadata};
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 const event=JSON.parse(fs.readFileSync(process.env.GITHUB_EVENT_PATH,'utf8'));
 console.log(JSON.stringify({linked_issue_check:'passed',...await checkLinkedIssue({branch:process.env.LANE_BRANCH,event,token:process.env.GH_TOKEN})}));
}
