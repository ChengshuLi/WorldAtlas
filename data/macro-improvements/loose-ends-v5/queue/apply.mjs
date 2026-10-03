// Designated publisher only. Without --create or --apply this performs no writes.
import fs from 'node:fs';
import path from 'node:path';
import {gunzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {execFile} from 'node:child_process';
import {pathToFileURL} from 'node:url';
import {readClaim,githubPages} from '../../../../scripts/issue-claim-contract.mjs';
const hash=x=>createHash('sha256').update(x).digest('hex');
const labels=x=>(x.labels??[]).map(l=>typeof l==='string'?l:l.name).sort();
export function guard(update,actual,claim){
  if(actual.state!=='open')return 'preserve-closed';
  if(labels(actual).includes('status:claimed')||claim?.active)return 'preserve-active-claim';
  if(actual.body===update.body)return 'already-matching';
  if(hash(actual.body??'')!==update.before_body_sha256||actual.updated_at!==update.before_updated_at)throw Error('Concurrent body/date edit; preserve and replan #'+update.number);
  if(JSON.stringify(labels(actual))!==JSON.stringify([...update.before_labels].sort())||JSON.stringify(labels(actual))!==JSON.stringify([...update.labels].sort()))throw Error('Concurrent labels or unexpected label mutation #'+update.number);
  return 'apply-body-only';
}
function request(route,body,method='PATCH'){
  return new Promise((resolve,reject)=>{const child=execFile('gh',['api',route,...(body?['--method',method,'--input','-']:[])],{maxBuffer:16*1024*1024},(error,stdout)=>{if(error)return reject(error);try{resolve(JSON.parse(stdout));}catch(e){reject(e);}});if(body)child.stdin.end(JSON.stringify(body));});
}
export async function main(argv){
  const option=(key,fallback)=>argv.find(x=>x.startsWith('--'+key+'='))?.slice(key.length+3)??fallback;
  const file=option('plan');if(!file)throw Error('--plan=FILE required');
  const bytes=fs.readFileSync(file),plan=JSON.parse(file.endsWith('.gz')?gunzipSync(bytes):bytes);
  if(!plan.read_only||!plan.publication_verified||plan.release?.version!==5)throw Error('Root-verified published v5 plan required');
  const create=argv.includes('--create'),apply=argv.includes('--apply');if(create&&apply)throw Error('Create, then replan numeric dependencies before apply');
  if(!create&&!apply){console.log(JSON.stringify({writes:0,creations:plan.issue_creations.length,updates:plan.issue_updates.length}));return;}
  const directory=option('output','/tmp/worldatlas-v5-queue-application');fs.mkdirSync(directory,{recursive:true});
  const repo='repos/'+option('repo','ChengshuLi/WorldAtlas'),log=path.join(directory,'applied-issues.jsonl');
  if(create){
    const existing=(await githubPages(route=>request(route),'/'+repo+'/issues?state=all')).filter(i=>!i.pull_request),mapping={};
    for(const x of plan.issue_creations){
      const marker='<!-- worldatlas-queue-item:'+x.key+' -->',matches=existing.filter(i=>(i.body??'').includes(marker));if(matches.length>1)throw Error('Duplicate supplemental marker '+x.key);
      const actual=matches[0]??await request(repo+'/issues',{title:x.title,body:x.body,labels:x.labels},'POST');mapping[x.key]={number:actual.number};
      fs.writeFileSync(path.join(directory,'created-issues.json'),JSON.stringify(mapping,null,2)+'\n');
    }
    console.log(JSON.stringify({created_or_found:mapping,next:'Re-run plan.py --created-issues=created-issues.json with the fresh issue snapshot, final handoffs and live receipt; then --apply.'}));return;
  }
  if(!plan.publication_gate.issue_number_links_resolved||plan.issue_creations.some(x=>!Number.isSafeInteger(x.number)))throw Error('Numeric supplemental links must be resolved before apply');
  let next=0;const errors=[],results=[];
  async function worker(){while(next<plan.issue_updates.length&&!errors.length){const x=plan.issue_updates[next++];try{
    const actual=await request(repo+'/issues/'+x.number),comments=actual.state==='open'&&!labels(actual).includes('status:claimed')&&actual.comments?await githubPages(route=>request(route),'/'+repo+'/issues/'+x.number+'/comments'):[],decision=guard(x,actual,readClaim(comments));
    if(decision==='apply-body-only'){const patched=await request(repo+'/issues/'+x.number,{body:x.body});if(patched.body!==x.body||JSON.stringify(labels(patched))!==JSON.stringify(labels(actual))||patched.state!==actual.state)throw Error('Write readback differs #'+x.number);}
    const receipt={number:x.number,decision,body_sha256:hash(decision==='apply-body-only'?x.body:actual.body??''),checked_at:new Date().toISOString()};results.push(receipt);fs.appendFileSync(log,JSON.stringify(receipt)+'\n');
  }catch(e){errors.push({number:x.number,error:e.message});}}}
  await Promise.all(Array.from({length:4},worker));
  const receipt={plan_sha256:hash(bytes),expected:plan.issue_updates.length,checked:results.length,results,errors};fs.writeFileSync(path.join(directory,'apply-receipt.json'),JSON.stringify(receipt,null,2)+'\n');console.log(JSON.stringify({checked:results.length,expected:plan.issue_updates.length,errors}));if(errors.length)throw Error('Preserved conflicting issues; replan before continuing');
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href)await main(process.argv.slice(2));
