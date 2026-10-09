import fs from 'node:fs';
import {execFileSync} from 'node:child_process';
import {runPREvidence,checkPREvidence} from '../../../scripts/check-pr-evidence.mjs';
import {githubAPI} from '../../../scripts/issue-claim-contract.mjs';
const repo='ChengshuLi/WorldAtlas';
const token=execFileSync('gh',['auth','token'],{encoding:'utf8'}).trim();
const numbers=process.argv.slice(2).map(Number);
if(!numbers.length||numbers.some(number=>!Number.isSafeInteger(number)||number<1))throw Error('Supply explicit current PR numbers; this probe performs read-only authenticated downloads');
fs.mkdirSync('.cache',{recursive:true});
for(const number of numbers){
 const pr=JSON.parse(execFileSync('gh',['api',`repos/${repo}/pulls/${number}`],{encoding:'utf8'}));
 const event={repository:{full_name:repo},pull_request:{number,head:{sha:pr.head.sha}}};
 const captured=new Map();
 const result=await runPREvidence({event,env:{GITHUB_REPOSITORY:repo,GH_TOKEN:token},directory:process.cwd(),
  apiFactory:(token,options)=>{const raw=githubAPI(token,options);return async(route,...rest)=>{const data=await raw(route,...rest);captured.set(route,data);return data;};}});
 let calls=0,blobs=0;
 const baseline=await checkPREvidence({event,api:async(route,method='GET')=>{
  calls++;if(method!=='GET')throw Error('Unexpected write');
  const match=/\/git\/blobs\/([a-f0-9]{40})$/.exec(route);
  if(match){blobs++;const bytes=execFileSync('git',['cat-file','blob',match[1]],{maxBuffer:33*1024*1024});return {sha:match[1],size:bytes.length,encoding:'base64',content:bytes.toString('base64')};}
  if(!captured.has(route))throw Error('Uncaptured mutable metadata '+route);
  return captured.get(route);
 }});
 const mechanical=(({request_accounting,immutable_transport,...rest})=>rest)(result);
 if(JSON.stringify(baseline)!==JSON.stringify(mechanical))throw Error('Different validation conclusions');
 const row={pr:number,head:pr.head.sha,baseline:pr.base.sha,status:result.status,changed_files:result.change_files_checked,
  manifest_sha256:result.manifest_sha256,old_path_simulated_api_attempts:calls,old_path_simulated_blob_attempts:blobs,
  new_path_actual_api:result.request_accounting,new_path_actual_transport:result.immutable_transport,
  identical_validation_result:true,limits:result.limits,
  measurement:'New path real remote reads using local credential; old path offline replay of same metadata and exact Git blobs. Not hosted installation quota measurement.'};
 fs.writeFileSync(`.cache/p0-pr-${number}-comparison.json`,JSON.stringify(row,null,2)+'\n');console.log(JSON.stringify(row));
}
