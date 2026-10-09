// Same-runtime bounded supervisor. Scientific code is invoked as plain Node.
import fs from 'node:fs';
import path from 'node:path';
import {spawn,execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
const repo=fs.realpathSync(process.cwd()),sha=body=>createHash('sha256').update(body).digest('hex');
const requestPath=process.argv[2],raw=fs.readFileSync(requestPath),request=JSON.parse(raw),requestSha=sha(raw);
const head=execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim();
if(!execFileSync('git',['show',head+':'+requestPath],{maxBuffer:32*1024*1024}).equals(raw))throw Error('Request must be frozen');
if(process.execArgv.length||process.env.NODE_OPTIONS?.trim()||process.env.NODE_PATH?.trim())throw Error('Plain launch only');
const self=fileURLToPath(import.meta.url),selfName=path.relative(repo,self),selfRaw=fs.readFileSync(self);
if(!execFileSync('git',['show',head+':'+selfName],{maxBuffer:32*1024*1024}).equals(selfRaw))throw Error('Supervisor must be frozen');
const admitFresh=name=>{let current=repo;for(const part of name.split('/')){if(!part||part==='.'||part==='..')throw Error('Unsafe output');current=path.join(current,part);
 const stat=fs.lstatSync(current,{throwIfNoEntry:false});if(stat&&(current===path.join(repo,name)||!stat.isDirectory()||stat.isSymbolicLink()||fs.realpathSync(current)!==current))throw Error('Collision/nonordinary output ancestor');}};
admitFresh(request.destination);
const operation='.cache/'+path.basename(requestPath,'.json')+'-node-operating';admitFresh(operation);fs.mkdirSync(operation,{recursive:true});
const command=[process.execPath,'scripts/additive-gap-repair.mjs',repo,head,requestPath,requestSha,request.destination];
const stdout=fs.openSync(operation+'/stdout.txt','wx'),stderr=fs.openSync(operation+'/stderr.txt','wx');
const start=Date.now(),cap=512*1024*1024,wall=600000,samples=[],events=[];let refusal=null,peakParent=0;
function snapshot(){const map=new Map();for(const line of execFileSync('ps',['-axo','pid=,ppid=,pgid=,rss=,lstart='],{encoding:'utf8'}).trim().split('\n')){
 const fields=line.trim().split(/\s+/);if(fields.length>=9)map.set(Number(fields[0]),{pid:Number(fields[0]),ppid:Number(fields[1]),pgid:Number(fields[2]),rss_bytes:Number(fields[3])*1024,started:fields.slice(4).join(' ')});}return map;}
const child=spawn('/usr/bin/time',['-l',...command],{detached:true,stdio:['ignore',stdout,stderr]});fs.closeSync(stdout);fs.closeSync(stderr);
const terminal=new Promise(resolve=>child.once('exit',(code,signal)=>resolve({code,signal}))),initial=snapshot(),identity=initial.get(child.pid);
if(!identity||identity.pgid!==child.pid)throw Error('Fresh owned root identity absent');
const captured=new Map(),same=(a,b)=>a&&b&&a.pid===b.pid&&a.pgid===b.pgid&&a.started===b.started;
function members(){const rows=snapshot(),root=rows.get(child.pid);if(root&&!same(root,identity))throw Error('Owned root identity changed');
 // The isolated group is retained while time/its descendants exist. PID birth
 // and group identify survivors even after parent reaping changes the PPID.
 const values=[...rows.values()].filter(row=>row.pgid===identity.pgid);
 for(const row of values)if(row.pid!==child.pid&&!captured.has(row.pid))captured.set(row.pid,row);
 return values.filter(row=>row.pid===child.pid?same(row,identity):same(row,captured.get(row.pid)));}
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function terminate(){const send=signal=>{for(const row of members().filter(row=>row.pid!==child.pid)){
 try{process.kill(row.pid,signal);events.push({pid:row.pid,signal,identity:row});}catch(error){if(error.code!=='ESRCH')throw error;}}};
 send('SIGTERM');const deadline=Date.now()+10000;while(members().some(row=>row.pid!==child.pid)&&Date.now()<deadline)await sleep(50);
 if(members().some(row=>row.pid!==child.pid))send('SIGKILL');
 const settled=await Promise.race([terminal,sleep(10000).then(()=>null)]);if(!settled)throw Error('Time root failed to settle after owned-child termination');
 const last=Date.now()+10000;while(members().length&&Date.now()<last){send('SIGKILL');await sleep(50);}if(members().length)throw Error('Owned survivors remain');}
while(child.exitCode===null&&child.signalCode===null){const rows=members(),rss=rows.reduce((sum,row)=>sum+row.rss_bytes,0),parent=process.memoryUsage().rss;peakParent=Math.max(peakParent,parent);
 samples.push({elapsed_seconds:(Date.now()-start)/1000,rss_bytes:rss,supervisor_rss_bytes:parent,members:rows});
 if(rss+parent>cap||Date.now()-start>wall){refusal=rss+parent>cap?'sampled-group-plus-supervisor-rss-cap':'wall-deadline';await terminate();break;}await sleep(100);}
const exit=await terminal,remaining=members();if(remaining.length)throw Error('Owned process group survived natural exit');
const timeText=fs.readFileSync(operation+'/stderr.txt','utf8'),match=/(\d+)\s+maximum resident set size/.exec(timeText),lifetime=match?Number(match[1]):null;
const peak=Math.max(0,...samples.map(sample=>sample.rss_bytes));if(lifetime===null)refusal??='missing-time-lifetime-rss';
if(lifetime!==null&&lifetime+peakParent>cap)refusal??='time-lifetime-plus-supervisor-rss-cap';
const result={version:1,execution_commit:head,request_sha256:requestSha,destination:request.destination,qualified:exit.code===0&&!refusal&&!remaining.length,
 exit,refusal,owned_processes_remaining:remaining,command:['/usr/bin/time','-l',...command],owned_root_identity:identity,
 elapsed_seconds:(Date.now()-start)/1000,rss_cap_bytes:cap,wall_deadline_seconds:wall/1000,peak_sampled_group_rss_bytes:peak,
 time_lifetime_max_rss_bytes:lifetime,peak_supervisor_rss_bytes:peakParent,conservative_lifetime_and_supervisor_bound_bytes:lifetime===null?null:lifetime+peakParent,
 termination_events:events,monitoring_limits:'Complete isolated group samples plus time child lifetime and conservative separate supervisor peak; not kernel enforcement.',
 supervisor:{path:selfName,bytes:selfRaw.length,sha256:sha(selfRaw),runtime_shared_with_child:true}};
fs.writeFileSync(operation+'/samples.json',JSON.stringify(samples)+'\n',{flag:'wx'});fs.writeFileSync(operation+'/receipt.json',JSON.stringify(result,null,2)+'\n',{flag:'wx'});
process.stdout.write(JSON.stringify(result)+'\n');process.exitCode=result.qualified?0:1;
