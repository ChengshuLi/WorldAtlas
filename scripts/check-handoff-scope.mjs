// Legacy explicit live-operation and scientific-exception contracts only.
// Ordinary authoring and merge admission do not use these conventions.
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
 const binding=links.length===1?/^(Refs|Closes) #([1-9]\d*)(?=$|[^\w#])([^.!;]*)/.exec(links[0]):null;
 // Other issue mentions may be context after a sentence/clause ends, not a binding list.
 if(!binding||/#\d+/.test(binding[3])||[...body.matchAll(/\brefs?\s+#[1-9]\d*/gi)].length!==(binding[1]==='Refs'?1:0))throw Error('One issue per PR: use exactly one Refs #<issue-number> for partial work or Closes #<issue-number> for final completion');
 const automaticClosures=[...body.matchAll(/\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s+#[1-9]\d*/gi)];
 if(automaticClosures.length!==(binding[1]==='Closes'?1:0))throw Error('Additional automatic issue closures are not allowed anywhere in the PR body');
 return {github_issue:Number(binding[2]),issue_action:binding[1]==='Closes'?'close':'reference'};
}
export function validateIssueMetadata(branch,issue){
 const {lane}=laneForBranch(branch),expected={engineering:'type:engineering',research:'type:history-research',geography:'type:geography'}[lane];
 if(!issue||issue.pull_request||issue.state!=='open')throw Error('Link an open GitHub issue, not a PR or closed issue');
 const types=(issue.labels??[]).map(label=>typeof label==='string'?label:label.name).filter(label=>label?.startsWith('type:'));
 if(types.length!==1||types[0]!==expected)throw Error(`Linked issue must have exactly one type label: ${expected}`);
 return {issue_type:expected};
}
