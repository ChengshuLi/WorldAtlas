import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import path from 'node:path';

const tracker='docs/HISTORY_HANDOFF.md';
const start='<!-- RESEARCH-CAMPAIGNS:START -->',end='<!-- RESEARCH-CAMPAIGNS:END -->';
export function laneForBranch(branch){
 const match=/^(engineering|research)\/([a-z0-9][a-z0-9-]{0,63})$/.exec(branch??'');
 if(!match)throw Error('Use engineering/<job-id> or research/<campaign-id> with a unique lower-case ID');
 return {lane:match[1],id:match[2]};
}
export function validateLanePaths(branch,paths){
 const {lane,id}=laneForBranch(branch);
 for(const file of paths){
  if(typeof file!=='string'||!file||file.startsWith('/')||file.includes('\\')||file.includes('\0')||file.split('/').some(part=>part==='..'||part===''||part==='.'))throw Error('Invalid repository path');
  if(lane==='research'&&file!==tracker&&!file.startsWith(`research/campaigns/${id}/`))throw Error(`Research changes must stay in its own campaign or owned tracker rows: ${file}`);
  if(lane==='engineering'&&(file.startsWith('research/campaigns/')||file.startsWith('coordination/engineering/')&&file!==`coordination/engineering/${id}.json`&&!file.startsWith(`coordination/engineering/${id}/`)))throw Error(`Engineering must preserve other lanes' owned progress and research: ${file}`);
 }
 return {lane,id};
}
function trackerParts(text){
 const parts=text.split(start);if(parts.length!==2)throw Error('Research tracker start marker must be preserved exactly once');
 const tail=parts[1].split(end);if(tail.length!==2)throw Error('Research tracker end marker must be preserved exactly once');
 return {before:parts[0],body:tail[0],after:tail[1]};
}
const validDate=value=>/^\d{4}-\d{2}-\d{2}$/.test(value)&&Number.isFinite(Date.parse(value+'T00:00:00Z'))&&new Date(value+'T00:00:00Z').toISOString().startsWith(value);
function trackerRows(body){
 const lines=body.trim().split('\n');if(lines.length<2)throw Error('Research tracker table is required');
 const rows=new Map();
 for(const line of lines.slice(2)){
  if(!line.startsWith('|')||!line.endsWith('|'))throw Error('Research tracker must contain only table rows');
  const columns=line.slice(1,-1).split('|').map(value=>value.trim());
  const [id,scope,status,raised,recorded,completed,evidence]=columns;
  if(columns.length!==7||!/^CAM:[a-z0-9][a-z0-9-]{0,63}:\d+$/.test(id)||!scope||!['open','active','blocked','done'].includes(status)||raised!=='unknown'&&!validDate(raised)||!validDate(recorded)||status==='done'&&(!validDate(completed)||!evidence||evidence==='—')||status!=='done'&&completed!=='—'||rows.has(id))throw Error('Invalid or duplicate research tracker row; completion requires date and evidence');
  rows.set(id,line);
 }
 return {header:lines.slice(0,2).join('\n'),rows};
}
export function validateTrackerChange(branch,before,after){
 const {lane,id}=laneForBranch(branch),old=trackerParts(before),next=trackerParts(after);
 if(lane==='engineering'){
  if(old.body!==next.body)throw Error('Engineering must preserve campaign-owned tracker rows; integrate the research PR instead');
  return;
 }
 if(old.before!==next.before||old.after!==next.after)throw Error('Research may change only its campaign rows, not shared handover instructions or global TODOs');
 const previous=trackerRows(old.body),current=trackerRows(next.body);
 if(previous.header!==current.header)throw Error('Research tracker header must remain unchanged');
 for(const [key,value] of previous.rows){
  if(!current.rows.has(key))throw Error('Keep completed/open tracker items as records; do not delete rows');
  if(!key.startsWith(`CAM:${id}:`)&&current.rows.get(key)!==value)throw Error('Research must preserve another campaign tracker row');
  if(key.startsWith(`CAM:${id}:`)){
   const oldColumns=value.slice(1,-1).split('|').map(cell=>cell.trim()),newColumns=current.rows.get(key).slice(1,-1).split('|').map(cell=>cell.trim());
   if(oldColumns[3]!==newColumns[3]||oldColumns[4]!==newColumns[4])throw Error('Preserve first-raised and first-recorded dates');
   if(oldColumns[2]==='done'&&value!==current.rows.get(key))throw Error('Keep completed milestone rows unchanged; append a linked follow-up');
  }
 }
 for(const key of current.rows.keys())if(!previous.rows.has(key)&&!key.startsWith(`CAM:${id}:`))throw Error('New research tracker items must use this campaign ID');
}
export function checkGitScope({branch,base,head='HEAD',run=execFileSync}){
 const git=args=>run('git',args,{encoding:'utf8',maxBuffer:16*1024*1024});
 // Resolve refs first: untrusted values never become git options or shell code.
 const resolve=ref=>{const sha=git(['rev-parse','--verify','--end-of-options',ref+'^{commit}']).trim();if(!/^[a-f0-9]{40,64}$/.test(sha))throw Error('Invalid commit');return sha;};
 const baseSHA=resolve(base),headSHA=resolve(head),mergeBaseSHA=git(['merge-base',baseSHA,headSHA]).trim();
 if(!/^[a-f0-9]{40,64}$/.test(mergeBaseSHA))throw Error('Branches need a common integration base');
 const files=git(['diff','--name-only','--no-renames','-z',mergeBaseSHA,headSHA,'--']).split('\0').filter(Boolean);
 const lane=validateLanePaths(branch,files);
 if(files.includes(tracker))validateTrackerChange(branch,git(['show',mergeBaseSHA+':'+tracker]),git(['show',headSHA+':'+tracker]));
 return {...lane,base:baseSHA,merge_base:mergeBaseSHA,head:headSHA,changed_files:files.length};
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 const args=process.argv.slice(2),options={};
 for(let i=0;i<args.length;i+=2){if(!['--branch','--base','--head'].includes(args[i])||!args[i+1]||options[args[i].slice(2)])throw Error('Usage: node scripts/check-handoff-scope.mjs --branch lane/id --base origin/work [--head HEAD]');options[args[i].slice(2)]=args[i+1];}
 if(!options.branch||!options.base)throw Error('Supply branch and base');
 console.log(JSON.stringify({scope_check:'passed',...checkGitScope(options)}));
}
