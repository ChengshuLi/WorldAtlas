// Linux sibling of the retained same-Node SOURCE/NATIVE supervisor. Numerical
// operators and historical launchers are unchanged. No arbitrary command CLI.
import fs from 'node:fs';
import path from 'node:path';
import {spawn,execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {fileURLToPath,pathToFileURL} from 'node:url';
const sha=raw=>createHash('sha256').update(raw).digest('hex');
const demand=(ok,message)=>{if(!ok)throw Error(message);};
const MiB=1024*1024,CAP=1024*MiB,WALL=600000;
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
const within=(promise,ms,message)=>new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error(message)),ms);promise.then(value=>{clearTimeout(timer);resolve(value);},error=>{clearTimeout(timer);reject(error);});});
// Exact executables already independently reviewed for the Linux runner. Paths
// come from the frozen request, so no laptop/cloud installation path is encoded.
export const RUNTIME_BODIES=Object.freeze([
 {role:'git',bytes:4082768,sha256:'356db14e102d68a1a37d8a1ac577dfd678d45d46e92f468bef8b7154e7bfdc60'},
 {role:'node',bytes:125989464,sha256:'bc17c508ffeed0ec622934f9b7fa72f8e78da65350e63c3eceb56fa688aa5e12'},
 {role:'process-inspector',bytes:154552,sha256:'43b8d2d049183e9ebc409c86b89150b5a4a68fa19fe1815b16bed5561921a9c3'},
 {role:'time',bytes:27384,sha256:'efc0d1112e36ec76c14bf7508e287935cf1631d9d0d91fb532802d07aef51cea'}
]);
export function requirePinnedGit(env,pin) {
 const resolved=env.PATH.split(path.delimiter).map(directory=>path.join(directory,'git')).find(file=>{
  try{return fs.statSync(file).isFile()&&(fs.statSync(file).mode&0o111)!==0;}catch{return false;}
 });
 demand(resolved&&fs.realpathSync(resolved)===pin.path,'Child PATH does not resolve the pinned Git');
}
export function scientificEnvironment(runtime) {
 const git=runtime.find(p=>p.role==='git'),ps=runtime.find(p=>p.role==='process-inspector');
 const env={PATH:[...new Set([path.dirname(git.path),path.dirname(ps.path)])].join(path.delimiter),LANG:'C',LC_ALL:'C',
  GIT_NO_LAZY_FETCH:'1',GIT_CONFIG_NOSYSTEM:'1',GIT_CONFIG_GLOBAL:'/dev/null',GIT_TERMINAL_PROMPT:'0',
  GIT_CONFIG_COUNT:'2',GIT_CONFIG_KEY_0:'core.hooksPath',GIT_CONFIG_VALUE_0:'/dev/null',GIT_CONFIG_KEY_1:'credential.helper',GIT_CONFIG_VALUE_1:''};
 requirePinnedGit(env,git);return env;
}
function birth(pid){
 try{const raw=boundedText('/proc/'+pid+'/stat',4096),f=raw.slice(raw.lastIndexOf(')')+2).trim().split(/\s+/);
  demand(f.length>19&&/^[0-9]+$/.test(f[2])&&/^[0-9]+$/.test(f[19]),'Malformed process birth');
  return {pid,pgid:Number(f[2]),started_ticks:f[19]};
 }catch(error){if(error.code==='ENOENT'||error.code==='ESRCH')return null;throw error;}
}
export function signalAuthenticatedGroup(original,current,signal,send=process.kill){
 if(!original||!current||original.pid!==current.pid||original.pgid!==current.pgid||original.started_ticks!==current.started_ticks)return false;
 demand(original.pid===original.pgid,'Owned root is not a detached group');send(-original.pgid,signal);return true;
}
export function ordinary(pin){
 const before=fs.lstatSync(pin.path);
 demand(before.isFile()&&!before.isSymbolicLink()&&fs.realpathSync(pin.path)===pin.path
   &&before.size===pin.bytes&&(before.mode&0o777)===pin.mode,'Runtime descriptor differs');
 const fd=fs.openSync(pin.path,fs.constants.O_RDONLY|fs.constants.O_NOFOLLOW),hash=createHash('sha256'),buffer=Buffer.alloc(MiB);
 const same=s=>s.isFile()&&s.size===before.size&&s.ino===before.ino&&s.dev===before.dev&&s.mode===before.mode;
 try{demand(same(fs.fstatSync(fd)),'Opened runtime differs');for(let n;(n=fs.readSync(fd,buffer,0,buffer.length,null));)hash.update(buffer.subarray(0,n));
  demand(hash.digest('hex')===pin.sha256&&same(fs.fstatSync(fd))&&same(fs.lstatSync(pin.path)),'Whole runtime drift');
 }finally{fs.closeSync(fd);}
}
export function parseTime(text){
 const one=pattern=>{const values=[...text.matchAll(pattern)];demand(values.length===1,'Missing/duplicate GNU time usage');return values[0][1];};
 const rss=Number(one(/^\s*Maximum resident set size \(kbytes\):\s*(\d+)\s*$/gm))*1024;
 const fields=one(/^\s*Elapsed \(wall clock\) time \(h:mm:ss or m:ss\):\s*(\d+(?::\d+){1,2}(?:\.\d+)?)\s*$/gm).split(':').map(Number);
 const seconds=fields.reduce((total,value)=>total*60+value,0),code=Number(one(/^\s*Exit status:\s*(\d+)\s*$/gm));
 demand(Number.isSafeInteger(rss)&&rss>=0&&Number.isFinite(seconds),'Invalid GNU time usage');return {rss_bytes:rss,elapsed_seconds:seconds,exit_code:code};
}
function boundedText(name,limit=65536){
 for(let part=name;;part=path.dirname(part)){demand(!fs.lstatSync(part).isSymbolicLink(),'Symlink resource observation');if(part===path.dirname(part))break;}
 const fd=fs.openSync(name,fs.constants.O_RDONLY|fs.constants.O_NOFOLLOW),buffer=Buffer.alloc(limit+1);let length=0;
 try{for(let n;(n=fs.readSync(fd,buffer,length,buffer.length-length,null));){length+=n;if(length===buffer.length)break;}
  demand(length<=limit,'Oversized resource observation');return buffer.subarray(0,length).toString('utf8');
 }finally{fs.closeSync(fd);}
}
export function evaluateSupply(evidence,cap=CAP){
 demand(Number.isSafeInteger(cap)&&cap>0,'Invalid requested process reservation');
 const value=name=>{const m=[...evidence.meminfo.matchAll(new RegExp('^'+name+':\\s*(\\d+) kB$','gm'))];demand(m.length===1,'Missing/duplicate memory report');return Number(m[0][1])*1024;};
 const total=value('MemTotal'),available=value('MemAvailable');
 demand(Number.isSafeInteger(total)&&available>=0&&available<=total,'Malformed memory totals');
 demand(Number.isSafeInteger(evidence.reserved)&&evidence.reserved>=0&&Number.isSafeInteger(evidence.aggregate_rss)&&evidence.aggregate_rss>=0,'Missing concurrent reservation');
 let supply=Math.min(available,Math.max(0,total-evidence.aggregate_rss));
 demand(Array.isArray(evidence.ancestors)&&evidence.ancestors.length<=64,'Oversized hierarchy report');
 for(const row of evidence.ancestors){demand(/^(0|[1-9][0-9]*)$/.test(row.current)&&/^(max|0|[1-9][0-9]*)$/.test(row.maximum),'Malformed exposed memory ceiling');
  if(row.maximum!=='max')supply=Math.min(supply,Math.max(0,Number(row.maximum)-Number(row.current)));}
 for(const [label,key] of [['Max address space','VmSize'],['Max data size','VmData']]){
  const ceilings=[...evidence.limits.matchAll(new RegExp('^'+label+'\\s+(unlimited|[0-9]+)\\s+(?:unlimited|[0-9]+)\\s+bytes\\s*$','gm'))];
  const usage=[...evidence.status.matchAll(new RegExp('^'+key+':\\s*(\\d+) kB$','gm'))];
  demand(ceilings.length===1&&usage.length===1,'Unknown process ceiling/usage');
  if(ceilings[0][1]!=='unlimited')supply=Math.min(supply,Math.max(0,Number(ceilings[0][1])-Number(usage[0][1])*1024));
 }
 const residual=supply-2*1024*MiB-evidence.reserved-cap;demand(residual>=768*MiB,'Fresh reported residual supply refused');
 return {supply_upper_bytes:supply,residual_reported_bytes:residual,headroom_reserve_bytes:2*1024*MiB,process_peak_reservation_bytes:cap,required_bytes:768*MiB,observations:evidence,
  uncertainty:'Reported availability only; unexposed limits remain unknown, not unlimited. No swap credit or guaranteed allocation.'};
}
export function freshSupply(ps,reserved,cap=CAP){
 demand(/^(0|[1-9][0-9]*)$/.test(reserved??''),'Fresh coordinator reservation required');
 const proc='/proc/'+process.pid,evidence={reserved:Number(reserved),ancestors:[],unknown_limits:[]};
 for(const [key,name] of Object.entries({meminfo:'/proc/meminfo',cgroup:proc+'/cgroup',mountinfo:proc+'/mountinfo',limits:proc+'/limits',status:proc+'/status'}))evidence[key]=boundedText(name);
 const mounts=evidence.mountinfo.trim().split('\n').map(line=>{
  const sides=line.split(' - '),left=sides[0].split(' '),right=sides[1]?.split(' ');
  demand(sides.length===2&&left.length>=6&&right.length>=3,'Malformed mount report');
  return {type:right[0],root:left[3],mount:left[4],memory:right[2].split(',').includes('memory')};
 }).filter(m=>m.type==='cgroup2'||m.type==='cgroup'&&m.memory);
 for(const line of evidence.cgroup.trim().split('\n')){
  const fields=line.split(':');demand(fields.length===3&&/^\d+$/.test(fields[0]),'Malformed cgroup membership');
  const kind=fields[0]==='0'&&fields[1]===''?'cgroup2':fields[1].split(',').includes('memory')?'cgroup':null;if(!kind)continue;
  const member=fields[2];demand(member.startsWith('/')&&!member.split('/').some(p=>p==='.'||p==='..'),'Unsafe membership');
  const possible=mounts.filter(m=>m.type===kind),matches=possible.filter(m=>member===m.root||member.startsWith(m.root.replace(/\/$/,'')+'/'));
  if(!matches.length){demand(!possible.length,'Exposed hierarchy does not map membership');evidence.unknown_limits.push('No exposed '+kind+' memory mount');continue;}
  demand(matches.length===1,'Ambiguous memory hierarchy');const mount=matches[0];
  demand(!/\\/.test(mount.root+mount.mount)&&mount.mount.startsWith('/'),'Unsupported escaped cgroup mount');
  let directory=path.join(mount.mount,path.relative(mount.root,member)),count=0;
  while(true){demand(++count<=64&&evidence.ancestors.length<64,'Oversized memory hierarchy');
   const max=path.join(directory,kind==='cgroup2'?'memory.max':'memory.limit_in_bytes'),cur=path.join(directory,kind==='cgroup2'?'memory.current':'memory.usage_in_bytes');
   if(!fs.existsSync(max)&&directory===mount.mount&&mount.root==='/'){
    demand(boundedText(path.join(directory,'cgroup.controllers'),4096).split(/\s+/).includes('memory'),'Unknown root memory exposure');
    evidence.unknown_limits.push('Exposed root has no memory.max; hidden ancestors remain unknown');
   }else{const maximum=boundedText(max,4096).trim(),current=boundedText(cur,4096).trim();demand(boundedText(max,4096).trim()===maximum,'Memory ceiling changed');evidence.ancestors.push({path:directory,maximum,current});}
   if(directory===mount.mount)break;directory=path.dirname(directory);
  }
  evidence.unknown_limits.push('Ancestors outside the exposed mount remain unknown');
 }
 demand(boundedText(proc+'/cgroup')===evidence.cgroup,'Membership changed');
 const rows=execFileSync(ps,['-axo','pid=,rss='],{encoding:'utf8',maxBuffer:65536});evidence.aggregate_rss=0;
 for(const line of rows.trim().split('\n')){const fields=line.trim().split(/\s+/);demand(fields.length===2&&fields.every(x=>/^\d+$/.test(x)),'Malformed aggregate RSS');evidence.aggregate_rss+=Number(fields[1])*1024;}
 return evaluateSupply(evidence,cap);
}
const LEGACY_ASSEMBLY_LIMITS=Object.freeze({rss_bytes:CAP,wall_seconds:1200,output_bytes:4*MiB,retained_bytes:12*MiB,log_bytes:4*MiB,monitor_bytes:8*MiB,receipt_bytes:MiB});
export function assemblyOperatingLimits(value){
 const fields='log_bytes,monitor_bytes,output_bytes,receipt_bytes,retained_bytes,rss_bytes,wall_seconds';
 demand(value&&typeof value==='object'&&!Array.isArray(value)&&Object.keys(value).sort().join(',')===fields,'Complete issued assembly operating limits required');
 demand(Object.values(value).every(n=>Number.isSafeInteger(n)&&n>0)&&Number.isSafeInteger(value.wall_seconds*1000),'Finite positive assembly operating limits required');
 demand(Number.isSafeInteger(value.output_bytes+value.receipt_bytes)&&value.log_bytes<=value.rss_bytes&&value.monitor_bytes<=value.rss_bytes&&value.receipt_bytes<=value.rss_bytes&&value.output_bytes+value.receipt_bytes<=value.retained_bytes&&value.log_bytes<=value.retained_bytes&&value.monitor_bytes<=value.retained_bytes,'Assembly output/log/monitor/receipt exceed retained admission');
 return Object.freeze({...value});
}
export function assemblyStorage(output,operation,reservedSamples=0,issuedLimits=LEGACY_ASSEMBLY_LIMITS) {
 const limits=assemblyOperatingLimits(issuedLimits);
 const names=['ledger.json','patch.json','envelope.json','qualification.json'];
 const sum=(directory,allowed)=>{
  if(!fs.existsSync(directory))return 0;
  const stat=fs.lstatSync(directory);demand(stat.isDirectory()&&!stat.isSymbolicLink(),'Nonordinary assembly output directory');
  return fs.readdirSync(directory).reduce((total,name)=>{demand(allowed.includes(name),'Unexpected assembly output member');
   const p=path.join(directory,name),s=fs.lstatSync(p);demand(s.isFile()&&!s.isSymbolicLink(),'Nonordinary assembly output member');return total+s.size;},0);
 };
 const productBytes=sum(output,names),operationBytes=sum(operation,['stdout.txt','stderr.txt','samples.json','receipt.json']);
 const stderr=path.join(operation,'stderr.txt');
 demand(productBytes<=limits.output_bytes,'Assembly product reserve');
 demand(!fs.existsSync(stderr)||fs.statSync(stderr).size<=(issuedLimits===LEGACY_ASSEMBLY_LIMITS?40960:limits.log_bytes),'Assembly stderr reserve');
 const retainedBytes=productBytes+operationBytes+(fs.existsSync(path.join(operation,'samples.json'))?0:reservedSamples);
 demand(retainedBytes<=limits.retained_bytes,'Assembly retained growth reserve');return {productBytes,retainedBytes};
}
export function sourceNativeStorage(output,operation,reservedSamples,issuedLimits){
 const limits=assemblyOperatingLimits(issuedLimits);
 const sum=(directory,allowed)=>{if(!fs.existsSync(directory))return 0;const stat=fs.lstatSync(directory);demand(stat.isDirectory()&&!stat.isSymbolicLink(),'Nonordinary source/native output directory');return fs.readdirSync(directory).reduce((n,name)=>{const p=path.join(directory,name),s=fs.lstatSync(p);demand(allowed(name)&&s.isFile()&&!s.isSymbolicLink()&&s.size<=32*MiB,'Foreign or oversized source/native output member');return n+s.size;},0);};
 const productBytes=sum(output,name=>/^[a-z0-9-]+\.json(?:l)?(?:\.gz)?$/.test(name)),operationBytes=sum(operation,name=>['stdout.txt','stderr.txt','samples.json','receipt.json'].includes(name));
 const retainedBytes=productBytes+operationBytes+(fs.existsSync(path.join(operation,'samples.json'))?0:reservedSamples);
 demand(productBytes<=limits.output_bytes&&retainedBytes<=limits.retained_bytes,'Source/native issued output/retained reserve exceeded');return {productBytes,retainedBytes};
}
export function sourceNativeStockAdmission(stock,root,growth){
 const integer=n=>Number.isSafeInteger(n)&&n>=0;
 demand(stock&&integer(stock.freeBytes)&&Number.isSafeInteger(stock.limits?.minimumFree)&&stock.limits.minimumFree>0&&Number.isSafeInteger(growth)&&growth>0,'Finite assembly storage admission required');
 const own=stock.entries.filter(e=>e.path===root&&e.slot==='work'&&e.status==='ready');
 demand(own.length===1&&integer(own[0].reservation),'Exact ready owned assembly slot required');
 const actual=stock.worktrees.filter(e=>e.path===root&&e.managed===true);
 demand(actual.length===1&&integer(actual[0].bytes),'Measured owned assembly footprint required');
 let peers=0;for(const entry of stock.entries){if(entry.path===root)continue;const rows=stock.worktrees.filter(e=>e.path===entry.path);demand(integer(entry.reservation)&&rows.length<=1&&(!rows.length||integer(rows[0].bytes)),'Measured peer reservation required');peers+=Math.max(0,entry.reservation-(rows[0]?.bytes??0));}
 const ownRemaining=Math.max(0,own[0].reservation-actual[0].bytes),admitted=Math.max(ownRemaining,growth),residual=stock.freeBytes-peers-admitted;
 demand(Number.isSafeInteger(peers)&&Number.isSafeInteger(residual)&&residual>=stock.limits.minimumFree,'Assembly free space/peer reservation/growth refused');
 return {free_bytes:stock.freeBytes,minimum_free_bytes:stock.limits.minimumFree,own_remaining_reservation_bytes:ownRemaining,peer_remaining_reservation_bytes:peers,issued_growth_bytes:growth,admitted_growth_bytes:admitted,residual_bytes:residual};
}
export function monitoringSampleBytes(bytes,count){
 demand(Number.isSafeInteger(bytes)&&bytes>=0&&Number.isSafeInteger(count)&&count>=0,'Invalid monitoring byte accounting');
 return count?bytes+count+2:3;
}
export function writeMonitoringSamples(file,samples,limit){
 const fd=fs.openSync(file,'wx');
 try{fs.writeSync(fd,'[');for(let i=0;i<samples.length;i++)fs.writeSync(fd,(i?',':'')+JSON.stringify(samples[i]));fs.writeSync(fd,']\n');}finally{fs.closeSync(fd);}
 if(limit!==undefined)demand(fs.statSync(file).size<=limit,'monitoring-output-reserve');
}
export async function supervise(command,{time,ps,operation,cap=CAP,wall=WALL,interval=100,env,profile='source-native-v1',outputDirectory,operatingLimits}){
 demand(env&&env.GIT_NO_LAZY_FETCH==='1'&&env.GIT_CONFIG_GLOBAL==='/dev/null','Isolated no-lazy child environment required');
 demand(['source-native-v1','source-native-v2','selected-assembly-v1','selected-assembly-v2'].includes(profile),'Unknown fixed operating profile');
 const configurable=profile.endsWith('-v2'),assembly=profile.startsWith('selected-assembly-'),sourceConfigured=profile==='source-native-v2';
 const limits=configurable?assemblyOperatingLimits(operatingLimits):LEGACY_ASSEMBLY_LIMITS;
 if(configurable){demand(cap===limits.rss_bytes&&wall===limits.wall_seconds*1000,'Issued assembly process limits differ');freshSupply(ps,env.WORLDATLAS_CONCURRENT_RESERVED_BYTES,cap);}
 else demand(Number.isSafeInteger(cap)&&cap>0&&cap<=CAP&&Number.isInteger(wall)&&wall>0&&wall<=(assembly?1200000:WALL),'Limits cannot be expanded');
 demand(!(assembly||sourceConfigured)||typeof outputDirectory==='string'&&path.isAbsolute(outputDirectory),'Assembly destination required');
 fs.mkdirSync(operation);const out=path.join(operation,'stdout.txt'),err=path.join(operation,'stderr.txt');
 const stdout=fs.openSync(out,'wx'),stderr=fs.openSync(err,'wx'),samples=[],events=[],captured=new Map();
 let child,identity,launchBirth,exit=null,refusal=null,peakParent=0,peak=0,sampleBytes=0;const start=Date.now();
 const snapshot=()=>{const rows=new Map();for(const line of execFileSync(ps,['-axo','pid=,ppid=,pgid=,rss=,lstart='],{encoding:'utf8',maxBuffer:65536}).trim().split('\n')){
  const f=line.trim().split(/\s+/);demand(f.length>=9&&f.slice(0,4).every(x=>/^\d+$/.test(x)),'Malformed process report');
  const b=birth(Number(f[0]));if(b&&b.pgid===Number(f[2]))rows.set(Number(f[0]),{...b,ppid:Number(f[1]),rss_bytes:Number(f[3])*1024,started:f.slice(4).join(' ')});}return rows;};
 const same=(a,b)=>a&&b&&a.pid===b.pid&&a.pgid===b.pgid&&a.started_ticks===b.started_ticks;
 const members=()=>{const rows=snapshot(),root=rows.get(child.pid);demand(!root||same(root,identity),'Owned root identity changed');
  const group=[...rows.values()].filter(r=>r.pgid===identity.pgid);
  for(const row of group)if(row.pid!==child.pid&&!captured.has(row.pid))captured.set(row.pid,row);
  demand(group.every(row=>row.pid===child.pid?same(row,identity):same(row,captured.get(row.pid))),'Owned child identity changed');return group;};
 let terminal;
 const emergency=async()=>{
  if(!child?.pid)return;
  for(const signal of ['SIGTERM','SIGKILL']){
   try{
    if(signalAuthenticatedGroup(launchBirth,birth(child.pid),signal))events.push({signal,identity:launchBirth,authority:'authenticated original detached root birth/group'});
    else for(const original of captured.values()){
     const current=birth(original.pid);
     if(same(original,current)){process.kill(original.pid,signal);events.push({signal,identity:original});}
    }
   }catch(error){if(error.code!=='ESRCH')throw error;}
   if(signal==='SIGTERM')await sleep(50);
  }
  await within(terminal,5000,'Owned launch failed to settle');
 };
 const terminate=async()=>{
  for(const signal of ['SIGTERM','SIGKILL']){for(const row of members().filter(r=>r.pid!==child.pid)){
   try{process.kill(row.pid,signal);events.push({signal,identity:row});}catch(error){if(error.code!=='ESRCH')throw error;}}
   const until=Date.now()+(signal==='SIGTERM'?1000:5000);while(members().some(r=>r.pid!==child.pid)&&Date.now()<until)await sleep(25);
  }
  await within(terminal,5000,'Time root failed to settle');
  demand(!members().length,'Owned survivors remain');
 };
 try{
  child=spawn(time,['-v',...command],{detached:true,stdio:['ignore',stdout,stderr],env});
  terminal=new Promise(resolve=>{child.once('error',error=>{exit={code:null,signal:null,error:error.code};resolve(exit);});child.once('exit',(code,signal)=>{exit={code,signal};resolve(exit);});});
  fs.closeSync(stdout);fs.closeSync(stderr);
  if(child.pid){launchBirth=birth(child.pid);identity=snapshot().get(child.pid);demand(identity?.pgid===child.pid&&same(identity,launchBirth),'Fresh owned root identity absent');}
  else {await terminal;throw Error('Time launch failed: '+exit.error);}
  while(!exit){const rows=members(),rss=rows.reduce((n,r)=>n+r.rss_bytes,0),parent=process.memoryUsage().rss;peak=Math.max(peak,rss);peakParent=Math.max(peakParent,parent);
   const sample={elapsed_seconds:(Date.now()-start)/1000,rss_bytes:rss,supervisor_rss_bytes:parent,members:rows};
   const nextBytes=sampleBytes+Buffer.byteLength(JSON.stringify(sample));
   if((configurable?monitoringSampleBytes(nextBytes,samples.length+1):nextBytes)>(configurable?limits.monitor_bytes:8*MiB))refusal='monitoring-output-reserve';else{sampleBytes=nextBytes;samples.push(sample);}
   if(rss+parent>cap)refusal='sampled-group-plus-supervisor-rss-cap';
   if(Date.now()-start>wall)refusal='wall-deadline';
   if(fs.statSync(out).size+fs.statSync(err).size>(configurable?limits.log_bytes:4*MiB))refusal='raw-output-reserve';
   if(assembly)try{assemblyStorage(outputDirectory,operation,configurable?monitoringSampleBytes(sampleBytes,samples.length):sampleBytes+samples.length+3,configurable?limits:LEGACY_ASSEMBLY_LIMITS);}catch(error){refusal??=error.message;}
   if(sourceConfigured)try{sourceNativeStorage(outputDirectory,operation,monitoringSampleBytes(sampleBytes,samples.length),limits);}catch(error){refusal??=error.message;}
   if(refusal){await terminate();break;}await sleep(interval);
  }
  await terminal;if(members().length){refusal??='owned-group-survived-natural-exit';await terminate();}
 }catch(error){refusal??=error.message;await emergency();}
 if(fs.statSync(out).size+fs.statSync(err).size>(configurable?limits.log_bytes:4*MiB))refusal??='raw-output-reserve';
 let usage=null;try{usage=parseTime(boundedText(err,configurable?limits.log_bytes:4*MiB));}catch(error){refusal??=error.message;}
 try{writeMonitoringSamples(path.join(operation,'samples.json'),samples,configurable?limits.monitor_bytes:undefined);}catch(error){refusal??=error.message;}
 if(assembly)try{assemblyStorage(outputDirectory,operation,0,configurable?limits:LEGACY_ASSEMBLY_LIMITS);}catch(error){refusal??=error.message;}
 if(sourceConfigured)try{sourceNativeStorage(outputDirectory,operation,0,limits);}catch(error){refusal??=error.message;}
 peakParent=Math.max(peakParent,process.memoryUsage().rss);
 if(usage&&(usage.rss_bytes+peakParent>cap||usage.elapsed_seconds>wall/1000||usage.exit_code!==exit?.code))refusal??='time-lifetime-supervisor-wall-or-exit-bound';
 let remaining=[];if(identity){try{remaining=members();}catch(error){refusal??=error.message;}}
 const result={version:1,qualified:exit?.code===0&&!refusal&&!remaining.length,exit,refusal,command:[time,'-v',...command],owned_root_identity:identity??null,owned_processes_remaining:remaining,
  elapsed_seconds:(Date.now()-start)/1000,rss_cap_bytes:cap,wall_deadline_seconds:wall/1000,peak_sampled_group_rss_bytes:peak,peak_supervisor_rss_bytes:peakParent,time_lifetime_max_rss_bytes:usage?.rss_bytes??null,
  conservative_lifetime_and_supervisor_bound_bytes:usage?usage.rss_bytes+peakParent:null,termination_events:events,monitoring_limits:'Complete isolated-group samples plus GNU time child lifetime and conservative separate parent peak; not kernel enforcement.'};
 if(configurable)result.operating_limits=limits;
 return result;
}
async function main(){
 demand(process.platform==='linux'&&!process.execArgv.length&&!process.env.NODE_OPTIONS?.trim()&&!process.env.NODE_PATH?.trim(),'Plain Linux Node launch required');
 const repo=fs.realpathSync(process.cwd()),name=process.argv[2];demand(name&&!path.isAbsolute(name)&&name.split('/').every(p=>p&&p!=='.'&&p!=='..'),'Safe frozen request path required');
 const stat=fs.lstatSync(name);demand(stat.isFile()&&!stat.isSymbolicLink()&&stat.size<=131072,'Bounded ordinary request required');
 const concurrent=process.env.WORLDATLAS_CONCURRENT_RESERVED_BYTES,available=process.availableMemory();
 demand(/^(0|[1-9][0-9]*)$/.test(concurrent??'')&&Number.isSafeInteger(Number(concurrent))&&Number.isSafeInteger(available)&&available-Number(concurrent)-2*1024**3-768*MiB>=2*stat.size,'Current request bootstrap memory admission refused');
 const raw=fs.readFileSync(name),request=JSON.parse(raw),operating=request.operating_runtime;
 demand(operating?.version===1&&operating.platform==='linux'&&operating.runtime.length===RUNTIME_BODIES.length,'Missing exact Linux runtime');
 for(let i=0;i<RUNTIME_BODIES.length;i++){const expected=RUNTIME_BODIES[i],pin=operating.runtime[i];demand(pin.role===expected.role&&pin.bytes===expected.bytes&&pin.sha256===expected.sha256&&pin.mode===0o755,'Foreign runtime body');ordinary(pin);}
 const role=name=>operating.runtime.find(p=>p.role===name).path;demand(role('node')===process.execPath,'Foreign running Node');
 const env=scientificEnvironment(operating.runtime);
 const git=(...args)=>execFileSync(role('git'),args,{maxBuffer:32*MiB,env}),head=git('rev-parse','HEAD').toString().trim();
 demand(git('show',head+':'+name).equals(raw),'Request must be frozen');
 const self=fileURLToPath(import.meta.url),selfName=path.relative(repo,self),selfRaw=fs.readFileSync(self);
 demand(git('show',head+':'+selfName).equals(selfRaw)&&operating.supervisor.path===selfName&&operating.supervisor.bytes===selfRaw.length&&operating.supervisor.sha256===sha(selfRaw),'Supervisor must match frozen binding');
 demand(['retained-land-source-premises-v1','unactivated-additive-native-batch-v1'].includes(request.operation),'Source/native operation only');
 const profile=request.operating_profile??'source-native-v1';demand(['source-native-v1','source-native-v2'].includes(profile),'Foreign source/native operating profile');
 const configured=profile==='source-native-v2',limits=configured?assemblyOperatingLimits(request.operating_limits):null;
 if(configured){const a=request.processing_allowance;demand(a&&Object.keys(a).sort().join(',')==='phaseBytes,rssBytes'&&Object.values(a).every(n=>Number.isSafeInteger(n)&&n>0&&n<=limits.rss_bytes),'Explicit source/native reader allowance required');demand(Number.isSafeInteger(request.output_reserve)&&request.output_reserve>=131072&&Number.isSafeInteger(request.output_reserve+131072)&&limits.output_bytes>=request.output_reserve+131072,'Source/native complete output reserve differs');}
 else demand(request.operating_profile===undefined&&request.operating_limits===undefined&&request.processing_allowance===undefined&&operating.support_code===undefined,'Foreign literal source/native v1 limits');
 const supportPaths=['scripts/local-workspace.mjs','scripts/worker-identity.mjs'];
 const verifySupport=()=>{if(!configured)return;demand(Array.isArray(operating.support_code)&&JSON.stringify(operating.support_code.map(p=>p.path))===JSON.stringify(supportPaths),'Complete source/native operating support required');for(const pin of operating.support_code){demand(Number.isSafeInteger(pin.bytes)&&pin.bytes>0&&pin.bytes<=32*MiB&&/^[a-f0-9]{64}$/.test(pin.sha256),'Invalid operating support pin');ordinary({...pin,path:path.join(repo,pin.path),mode:0o644});const body=git('show',head+':'+pin.path),row=git('ls-tree','-z',head,'--',pin.path).toString();demand(/^100644 blob [a-f0-9]{40}\t/.test(row)&&row.endsWith('\t'+pin.path+'\0')&&body.length===pin.bytes&&sha(body)===pin.sha256,'Operating support Git/body mismatch');}};
 verifySupport();
 const cap=limits?.rss_bytes??CAP,wall=(limits?.wall_seconds??WALL/1000)*1000;

 const fresh=name=>{demand(!path.isAbsolute(name)&&name.split('/').every(p=>p&&p!=='.'&&p!=='..'),'Unsafe destination');let current=repo;for(const part of name.split('/')){current=path.join(current,part);const s=fs.lstatSync(current,{throwIfNoEntry:false});demand(!s||(current!==path.join(repo,name)&&s.isDirectory()&&!s.isSymbolicLink()&&fs.realpathSync(current)===current),'Output collision/nonordinary ancestor');}};
 fresh(request.destination);const operation='.cache/'+path.basename(name,'.json')+'-linux-operating';fresh(operation);fs.mkdirSync(path.dirname(operation),{recursive:true});
 const supply=freshSupply(role('process-inspector'),concurrent,cap);
 let storage=null;if(configured){const {workspaceManager}=await import(pathToFileURL(path.join(repo,supportPaths[0])));storage=sourceNativeStockAdmission(workspaceManager(repo).check(),repo,limits.retained_bytes);}
 const command=[process.execPath,'scripts/additive-gap-repair.mjs',repo,head,name,sha(raw),request.destination];
 const result=await supervise(command,{time:role('time'),ps:role('process-inspector'),operation,env:configured?{...env,WORLDATLAS_CONCURRENT_RESERVED_BYTES:concurrent}:env,profile,cap,wall,...(configured?{operatingLimits:limits,outputDirectory:path.join(repo,request.destination)}:{})});
 Object.assign(result,{execution_commit:head,request_sha256:sha(raw),destination:request.destination,resource_admission:supply,operating_runtime:operating,supervisor:{path:selfName,bytes:selfRaw.length,sha256:sha(selfRaw),runtime_shared_with_child:true}});
 for(const pin of operating.runtime)ordinary(pin);
 if(configured){verifySupport();demand(git('rev-parse','HEAD').toString().trim()===head&&git('show',head+':'+name).equals(raw)&&fs.readFileSync(self).equals(selfRaw),'Source/native execution changed');Object.assign(result,{profile,processing_allowance:request.processing_allowance,operating_limits:limits,storage_admission:storage});}
 result.peak_supervisor_rss_bytes=Math.max(result.peak_supervisor_rss_bytes,process.memoryUsage().rss);
 result.conservative_lifetime_and_supervisor_bound_bytes=result.time_lifetime_max_rss_bytes===null?null:result.time_lifetime_max_rss_bytes+result.peak_supervisor_rss_bytes;
 if(result.conservative_lifetime_and_supervisor_bound_bytes>cap){result.refusal??='post-use-lifetime-plus-supervisor-rss-cap';result.qualified=false;}
 const receipt=JSON.stringify(result,null,2)+'\n';demand(Buffer.byteLength(receipt)<=(limits?.receipt_bytes??MiB),'Operating receipt exceeds metadata reserve');
 if(configured){const retained=sourceNativeStorage(path.join(repo,request.destination),operation,0,limits);demand(retained.retainedBytes+Buffer.byteLength(receipt)<=limits.retained_bytes,'Source/native final receipt exceeds retained reserve');}
 fs.writeFileSync(path.join(operation,'receipt.json'),receipt,{flag:'wx'});process.stdout.write(JSON.stringify(result)+'\n');process.exitCode=result.qualified?0:1;
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url))main().catch(error=>{process.stderr.write(error.stack+'\n');process.exitCode=1;});
