import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {workSpec} from '../../../scripts/issue-claim-contract.mjs';
import {validateIssueMetadata} from '../../../scripts/check-handoff-scope.mjs';
import {evidenceRequirement,loadEvidencePolicy} from '../../../scripts/evidence-policy.mjs';

const packet=path.dirname(fileURLToPath(import.meta.url));
const repo=path.resolve(packet,'../../..');
const pinned=JSON.parse(fs.readFileSync(path.join(packet,'issue-scope-pinned.json'),'utf8'));
const scope=JSON.parse(fs.readFileSync(path.join(packet,'scope.json'),'utf8'));
const saved=JSON.parse(fs.readFileSync(path.join(packet,'follow-up-issues.json'),'utf8'));
const pinsToFiles={world_index:'data/world-index.json',source_registry:'data/administrative-sources.json',
  geography_part_8:'data/geography/part-8.json',geography_part_22:'data/geography/part-22.json',
  geography_part_28:'data/geography/part-28.json',macro_publication_v5:'data/validation/macro-publication-v5.json'};
const kinds={910:['FJI',15],911:['NCL',3],912:['VUT',6],913:['SLB',1]};
function blob(commit,file){
  const r=spawnSync('git',['-C',repo,'show',`${commit}:${file}`],{encoding:null,maxBuffer:32*1024*1024});
  if(r.status!==0)throw Error(`Unable to read pinned baseline blob ${commit}:${file}`);
  return r.stdout;
}
function sha(bytes){return [...new Uint8Array(requireHash(bytes))].map(x=>x.toString(16).padStart(2,'0')).join('');}
import {createHash} from 'node:crypto';
function requireHash(bytes){return createHash('sha256').update(bytes).digest();}
const parentIds=new Set(scope.member_location_ids);
if(saved.parent_issue!==454||saved.main_commit!=='a7c44deed5de3dd08bfdb0ee099d6e57efb3ea8b')throw Error('Wrong follow-up parent or baseline main pin');
const checked=[];
for(const issue of saved.followups){
  const [code,count]=kinds[issue.number]??[];
  if(!code||issue.state!=='open')throw Error(`Unexpected follow-up ${issue.number}`);
  const spec=workSpec(issue.body), quality=spec.evidence_quality;
  const idBlock=issue.body.match(/```json\s*\n([\s\S]*?)\n```/);
  if(!idBlock)throw Error(`Missing machine-readable subject scope on #${issue.number}`);
  const child=JSON.parse(idBlock[1]);
  if(child.subject_ids.length!==count||JSON.stringify(child.subject_ids)!==JSON.stringify(quality.subject_ids)||child.subject_ids.some(id=>!parentIds.has(id)||!(id.startsWith(`gb:${code}:`)||code==='NCL'&&id.startsWith('NCL-'))))throw Error(`Subject scope mismatch on #${issue.number}`);
  const job=spec.owned_paths[0].split('/')[2],branch=`geography/${job}`;
  validateIssueMetadata(branch,issue);
  const requirement=evidenceRequirement(issue,spec,loadEvidencePolicy(),branch);
  const labels=issue.labels.map(x=>x.name);
  if(!labels.includes('kind:work-item')||!labels.includes('priority:follow-up')||!labels.includes('status:blocked')||labels.includes('status:ready')||!labels.includes('type:geography'))throw Error(`Readiness state mismatch on #${issue.number}`);
  if(JSON.stringify(spec.depends_on)!=='[454]'||requirement.manifestPath!==spec.owned_paths[0]+'evidence-quality.json')throw Error(`Dependency or manifest mismatch on #${issue.number}`);
  const verifiedPins=[];
  for(const [name,expected] of Object.entries(quality.pins)){
    const file=pinsToFiles[name];
    if(!file)throw Error(`Unknown pin ${name} on #${issue.number}`);
    const actual=sha(blob(saved.main_commit,file));
    if(actual!==expected)throw Error(`Baseline pin mismatch for ${name} on #${issue.number}`);
    verifiedPins.push({name,path:file,sha256:actual});
  }
  checked.push({issue:issue.number,title:issue.title,subject_count:count,scope:'exact subset of #454',status:'blocked on parent',manifest_path:requirement.manifestPath,verified_pins:verifiedPins});
}
const result={version:1,parent_issue:454,pinned_main_commit:saved.main_commit,followups:checked,all_contracts_valid:true};
fs.writeFileSync(path.join(packet,'follow-up-contract-check.json'),JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify(result));
