import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import fs from 'node:fs';

export function laneForBranch(branch){
 const match=/^(engineering|research|geography)\/([a-z0-9][a-z0-9-]{0,63})$/.exec(branch??'');
 if(!match)throw Error('Use engineering/<job-id>, research/<campaign-id> or geography/<job-id> with a unique lower-case ID');
 return {lane:match[1],id:match[2]};
}
export function validateGeographyOwnedPaths(ownedPaths){
 if(!Array.isArray(ownedPaths)||ownedPaths.length<1||ownedPaths.length>8||new Set(ownedPaths).size!==ownedPaths.length||ownedPaths.some(prefix=>typeof prefix!=='string'||prefix.length>512||!/^(data\/regional-review|research\/geography)\/[a-z0-9][a-z0-9-]{0,63}\/(?:[a-z0-9][a-z0-9-]{0,63}\/){0,8}$/.test(prefix)))throw Error('Geography needs 1–8 distinct declared owned_paths under data/regional-review/<packet-id>/ or research/geography/<campaign-id>/, optionally narrowed to safe subdirectories');
 return [...ownedPaths];
}
// A trailing slash grants a directory; otherwise the declaration grants one file.
export function validateEngineeringOwnedPaths(ownedPaths){
 if(ownedPaths===undefined)return [];
 if(!Array.isArray(ownedPaths)||new Set(ownedPaths).size!==ownedPaths.length)throw Error('Engineering owned_paths must be distinct literal safe repository paths');
 for(const owned of ownedPaths){
  if(typeof owned!=='string'||!owned||owned.length>512)throw Error('Engineering owned_paths must be literal safe repository paths');
  const prefix=owned.endsWith('/'),parts=(prefix?owned.slice(0,-1):owned).split('/');
  if(parts.some(part=>! /^[a-zA-Z0-9_.-]+$/.test(part)||part==='.'||part==='..')||
   prefix&&parts.length<2||['coordination/engineering','coordination/engineering/'].includes(owned)||
   ['research/campaigns','research/geography','data/regional-review'].some(root=>owned===root||owned.startsWith(root+'/')))
   throw Error('Engineering owned_paths cannot grant unsafe paths, namespace roots or research/geography evidence');
 }
 return [...ownedPaths];
}
export function validateLanePaths(branch,paths,{ownedPaths}={}){
 const {lane,id}=laneForBranch(branch);
 const owned=lane==='geography'?validateGeographyOwnedPaths(ownedPaths):lane==='engineering'?validateEngineeringOwnedPaths(ownedPaths):null;
 for(const file of paths){
  if(typeof file!=='string'||!file||file.startsWith('/')||file.includes('\\')||file.includes('\0')||file.split('/').some(part=>part==='..'||part===''||part==='.'))throw Error('Invalid repository path');
  if(lane==='research'&&!file.startsWith(`research/campaigns/${id}/`))throw Error(`Research changes must stay in its own campaign: ${file}`);
  if(lane==='geography'&&!owned.some(prefix=>file.startsWith(prefix)))throw Error(`Geography changes must stay in its declared owned_paths: ${file}`);
  if(lane==='engineering'&&(file.startsWith('research/campaigns/')||file.startsWith('research/geography/')||file.startsWith('data/regional-review/')||file.startsWith('coordination/engineering/')&&file!==`coordination/engineering/${id}.json`&&!file.startsWith(`coordination/engineering/${id}/`)&&!owned.some(grant=>grant.endsWith('/')?file.startsWith(grant):file===grant)))throw Error(`Engineering must preserve other lanes' owned progress and research: ${file}`);
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
 const {lane}=laneForBranch(branch),expected={engineering:'type:engineering',research:'type:history-research',geography:'type:geography'}[lane];
 if(!issue||issue.pull_request||issue.state!=='open')throw Error('Link an open GitHub issue, not a PR or closed issue');
 const types=(issue.labels??[]).map(label=>typeof label==='string'?label:label.name).filter(label=>label?.startsWith('type:'));
 if(types.length!==1||types[0]!==expected)throw Error(`Linked issue must have exactly one type label: ${expected}`);
 return {issue_type:expected};
}
export function checkGitScope({branch,base,head='HEAD',run=execFileSync,prBody,ownedPaths}){
 const git=args=>run('git',args,{encoding:'utf8',maxBuffer:16*1024*1024});
 // Resolve refs first: untrusted values never become git options or shell code.
 const resolve=ref=>{const sha=git(['rev-parse','--verify','--end-of-options',ref+'^{commit}']).trim();if(!/^[a-f0-9]{40,64}$/.test(sha))throw Error('Invalid commit');return sha;};
 const baseSHA=resolve(base),headSHA=resolve(head),mergeBaseSHA=git(['merge-base',baseSHA,headSHA]).trim();
 if(!/^[a-f0-9]{40,64}$/.test(mergeBaseSHA))throw Error('Branches need a common integration base');
 const files=git(['diff','--name-only','--no-renames','-z',mergeBaseSHA,headSHA,'--']).split('\0').filter(Boolean);
 const lane=validateLanePaths(branch,files,{ownedPaths});
 if(lane.lane==='geography'&&files.length){
  const entries=git(['ls-tree','-r','-z',headSHA,'--',...files]).split('\0').filter(Boolean);
  if(entries.some(entry=>entry.startsWith('120000 ')||entry.startsWith('160000 ')))throw Error('Geography evidence must use ordinary files, not symlinks or submodules');
 }
 const issue=prBody===undefined?{}:validateIssuePRBody(prBody);
 if(issue.todo_id&&!(lane.lane==='engineering'?/^ENG-\d+(?:-\d+)*$/.test(issue.todo_id):new RegExp('^CAM:'+lane.id+':\\d+$').test(issue.todo_id)))throw Error('PR TODO ID must identify the single issue in its engineering/research lane');
 return {...lane,...issue,base:baseSHA,merge_base:mergeBaseSHA,head:headSHA,changed_files:files.length};
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 const args=process.argv.slice(2),options={};
 for(let i=0;i<args.length;i+=2){if(!['--branch','--base','--head','--pr-body-file','--pr-event-file','--issue-file'].includes(args[i])||!args[i+1]||options[args[i].slice(2)])throw Error('Usage: node scripts/check-handoff-scope.mjs --branch lane/id --base origin/main [--head HEAD] [--pr-body-file path] [--issue-file actual-issue.json]');options[args[i].slice(2)]=args[i+1];}
 if(!options.branch||!options.base)throw Error('Supply branch and base');
 if(options['pr-body-file']&&options['pr-event-file'])throw Error('Use one PR body source');
 if(options['pr-body-file'])options.prBody=fs.readFileSync(options['pr-body-file'],'utf8');
 if(options['pr-event-file'])options.prBody=JSON.parse(fs.readFileSync(options['pr-event-file'],'utf8')).pull_request?.body??'';
 if(options['issue-file']){
  const issue=JSON.parse(fs.readFileSync(options['issue-file'],'utf8'));
  validateIssueMetadata(options.branch,issue);
  const {lane}=laneForBranch(options.branch);
  if(lane==='geography'||lane==='engineering'){
   const blocks=[...String(issue.body??'').matchAll(/<!-- worldatlas-work:v1\s*\n([\s\S]*?)\n-->/g)];
   if(blocks.length!==1)throw Error(`A reviewed ${lane} work scope is required`);
   const spec=JSON.parse(blocks[0][1]);
   if(spec.mode!==lane)throw Error(`Issue ownership requires ${lane} mode`);
   if(lane==='engineering'&&(!Number.isInteger(spec.max_prs)||spec.max_prs<1||spec.max_prs>3||!Array.isArray(spec.depends_on)||spec.depends_on.some(n=>!Number.isSafeInteger(n)||n<1)||typeof spec.scope!=='string'||!spec.scope))throw Error('Engineering work items need bounded scope, 1–3 PRs and explicit dependency issue numbers');
   options.ownedPaths=lane==='geography'?validateGeographyOwnedPaths(spec.owned_paths):validateEngineeringOwnedPaths(spec.owned_paths);
  }
  if(options.prBody&&validateIssuePRBody(options.prBody).github_issue!==issue.number)throw Error('Issue ownership file must match the PR issue');
 }
 console.log(JSON.stringify({scope_check:'passed',...checkGitScope(options)}));
}
