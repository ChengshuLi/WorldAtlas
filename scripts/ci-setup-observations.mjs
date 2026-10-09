import assert from 'node:assert/strict';
import {performance} from 'node:perf_hooks';
import {spawnSync} from 'node:child_process';
const names=new Set(['immutable-regression-inputs','canonical-checkout','canonical-package','package-materialization','package-execution-authentication']);
// These setup entry points make no REST requests themselves. Git/Actions may
// perform HTTP internally; absent transport counters are unknown, never zero.
export async function observeSetupPhase(name,work,{emit=value=>console.log(JSON.stringify(value)),clock=()=>performance.now(),counters}={}){
 assert(names.has(name)&&typeof work==='function');
 const before=clock();let status='failed';
 emit({setup_phase:name,status:'started'});
 try{const result=await work();status='success';return result;}
 finally{
  const elapsed=clock()-before;assert(Number.isFinite(elapsed)&&elapsed>=0);
  emit({setup_phase:name,status,elapsed_ms:elapsed,
   counters:{controlled_rest_attempts:0,controlled_quota_sleep_ms:0,...(counters?.()??{}),http_observation_ms:null,transport_quota_sleep_ms:null},
   process_peak_rss_bytes:process.resourceUsage().maxRSS*1024,
   limits:['RSS is the process high-water mark, not an isolated phase maximum.','Git/Actions internal HTTP attempts and waits are not established by this record.']});
 }
}
export function measuredGitSetup({run=spawnSync,clock=()=>performance.now()}={}){
 const observations={git_command_attempts:0,git_fetch_attempts:0,git_command_elapsed_ms:0,git_fetch_elapsed_ms:0};
 return {run(command,args,options){
  assert.equal(command,'git');assert(Array.isArray(args));
  const fetch=args[0]==='fetch',before=clock();observations.git_command_attempts++;if(fetch)observations.git_fetch_attempts++;
  try{return run(command,args,options);}finally{
   const elapsed=clock()-before;assert(Number.isFinite(elapsed)&&elapsed>=0);observations.git_command_elapsed_ms+=elapsed;if(fetch)observations.git_fetch_elapsed_ms+=elapsed;
  }
 },snapshot:()=>({...observations})};
}
