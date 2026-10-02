import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import fs from 'node:fs';

export function laneForBranch(branch){
 const match=/^(engineering|research)\/([a-z0-9][a-z0-9-]{0,63})$/.exec(branch??'');
 if(!match)throw Error('Use engineering/<job-id> or research/<campaign-id> with a unique lower-case ID');
 return {lane:match[1],id:match[2]};
}
export function validateLanePaths(branch,paths){
 const {lane,id}=laneForBranch(branch);
 for(const file of paths){
  if(typeof file!=='string'||!file||file.startsWith('/')||file.includes('\\')||file.includes('\0')||file.split('/').some(part=>part==='..'||part===''||part==='.'))throw Error('Invalid repository path');
  if(lane==='research'&&!file.startsWith(`research/campaigns/${id}/`))throw Error(`Research changes must stay in its own campaign: ${file}`);
  if(lane==='engineering'&&(file.startsWith('research/campaigns/')||file.startsWith('coordination/engineering/')&&file!==`coordination/engineering/${id}.json`&&!file.startsWith(`coordination/engineering/${id}/`)))throw Error(`Engineering must preserve other lanes' owned progress and research: ${file}`);
 }
 return {lane,id};
}
export function validateIssuePRBody(body){
 if(typeof body!=='string')throw Error('Supply the PR body');
 const links=body.split('\n').filter(line=>/^\s*(?:refs?|close[sd]?|fix(?:e[sd])?|resolve[sd]?)\b/i.test(line));
 if(links.length!==1||!/^(Refs|Closes) #[1-9]\d*$/.test(links[0]))throw Error('One issue per PR: use exactly one Refs #<issue-number> for partial work or Closes #<issue-number> for final completion');
 const automaticClosures=[...body.matchAll(/\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s+#[1-9]\d*/gi)];
 if(automaticClosures.length!==(links[0].startsWith('Closes')?1:0))throw Error('Additional automatic issue closures are not allowed anywhere in the PR body');
 // Optional historical IDs support the transition from the archived document trackers.
 const todos=[...body.matchAll(/^TODO:\s*(\S+)\s*$/gm)];
 if(todos.length>1)throw Error('Only one legacy TODO ID may be supplied');
 return {...(todos.length?{todo_id:todos[0][1]}:{}),github_issue:Number(links[0].split('#')[1]),issue_action:links[0].startsWith('Closes')?'close':'reference'};
}
export function validateIssueMetadata(branch,issue){
 const {lane}=laneForBranch(branch),expected=lane==='engineering'?'type:engineering':'type:history-research';
 if(!issue||issue.pull_request||issue.state!=='open')throw Error('Link an open GitHub issue, not a PR or closed issue');
 const types=(issue.labels??[]).map(label=>typeof label==='string'?label:label.name).filter(label=>label?.startsWith('type:'));
 if(types.length!==1||types[0]!==expected)throw Error(`Linked issue must have exactly one type label: ${expected}`);
 return {issue_type:expected};
}
export function checkGitScope({branch,base,head='HEAD',run=execFileSync,prBody}){
 const git=args=>run('git',args,{encoding:'utf8',maxBuffer:16*1024*1024});
 // Resolve refs first: untrusted values never become git options or shell code.
 const resolve=ref=>{const sha=git(['rev-parse','--verify','--end-of-options',ref+'^{commit}']).trim();if(!/^[a-f0-9]{40,64}$/.test(sha))throw Error('Invalid commit');return sha;};
 const baseSHA=resolve(base),headSHA=resolve(head),mergeBaseSHA=git(['merge-base',baseSHA,headSHA]).trim();
 if(!/^[a-f0-9]{40,64}$/.test(mergeBaseSHA))throw Error('Branches need a common integration base');
 const files=git(['diff','--name-only','--no-renames','-z',mergeBaseSHA,headSHA,'--']).split('\0').filter(Boolean);
 const lane=validateLanePaths(branch,files);
 const issue=prBody===undefined?{}:validateIssuePRBody(prBody);
 if(issue.todo_id&&!(lane.lane==='engineering'?/^ENG-\d+(?:-\d+)*$/.test(issue.todo_id):new RegExp('^CAM:'+lane.id+':\\d+$').test(issue.todo_id)))throw Error('PR TODO ID must identify the single issue in its engineering/research lane');
 return {...lane,...issue,base:baseSHA,merge_base:mergeBaseSHA,head:headSHA,changed_files:files.length};
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 const args=process.argv.slice(2),options={};
 for(let i=0;i<args.length;i+=2){if(!['--branch','--base','--head','--pr-body-file','--pr-event-file'].includes(args[i])||!args[i+1]||options[args[i].slice(2)])throw Error('Usage: node scripts/check-handoff-scope.mjs --branch lane/id --base origin/main [--head HEAD] [--pr-body-file path]');options[args[i].slice(2)]=args[i+1];}
 if(!options.branch||!options.base)throw Error('Supply branch and base');
 if(options['pr-body-file']&&options['pr-event-file'])throw Error('Use one PR body source');
 if(options['pr-body-file'])options.prBody=fs.readFileSync(options['pr-body-file'],'utf8');
 if(options['pr-event-file'])options.prBody=JSON.parse(fs.readFileSync(options['pr-event-file'],'utf8')).pull_request?.body??'';
 console.log(JSON.stringify({scope_check:'passed',...checkGitScope(options)}));
}
