import {createHash} from 'node:crypto';

const need=(ok,message)=>{if(!ok)throw Error(message);};
const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const workflowPath='.github/workflows/worker-merge.yml';
const hash=raw=>createHash('sha256').update(raw).digest('hex');
const oid=raw=>createHash('sha1').update(`blob ${Buffer.byteLength(raw)}\0`).update(raw).digest('hex');
const install='python -m pip install -r requirements.txt';
const ordinary="needs.prepare.outputs.profile == 'full' || needs.prepare.outputs.profile == 'evidence'";
const fallback="needs.prepare.outputs.profile == 'full' && matrix.shard == 0 && steps.assembly.outputs.assembled != 'true'";
const names={
  checkout:'Checkout exact candidate for application regression',
  materialize:'Materialize exact prepared checkout inputs',
  verify:'Checkout complete candidate for application regression',
  installer:'Authenticate selected package installer inputs',
  assembly:'Assemble unchanged base with current selected output',
  snapshot:'Snapshot original final-worker package inputs',
  build:'Build the combined application once before asset-dependent tests',
  inventory:'Inventory original final-worker package output',
  upload:'Retain original final-worker package output',
};

// This is a recognizer for the queue's supported block-style producer, not a
// YAML interpreter. Literal script/path bodies are opaque and remain byte-bound.
// No anchors, tags, merge keys, duplicate structural keys or continuation syntax
// may smuggle effects into a field that this projection does not understand.
function lines(raw){
  need(typeof raw==='string'&&raw.endsWith('\n')&&!/[\0\r\t]/.test(raw),'Supported producer workflow text required');
  let literal=-1;
  const result=[],mappings=[];
  for(const line of raw.split('\n')){
    const indent=line.length-line.trimStart().length;
    if(literal>=0&&(!line.trim()||indent>literal)){result.push(line);continue;}
    literal=-1;
    if(!line.trim()||/^ *#/.test(line))continue;
    const match=/^( *)(?:- )?([A-Za-z_][A-Za-z0-9_-]*):(?: (.*))?$/.exec(line);
    need(match&&indent%2===0,'Unsupported producer workflow syntax');
    const sequence=line.slice(indent).startsWith('- '),depth=indent+(sequence?2:0);
    while(mappings.length&&(mappings.at(-1).depth>depth||sequence&&mappings.at(-1).depth>=indent))mappings.pop();
    if(mappings.at(-1)?.depth!==depth)mappings.push({depth,keys:new Set()});
    need(!mappings.at(-1).keys.has(match[2]),'Duplicate producer mapping key');
    mappings.at(-1).keys.add(match[2]);
    const value=match[3]??'';
    need(!/^(?:[&*!>]|---|\.\.\.)/.test(value)&&!/(?:^|[ ,\[{])[&*][A-Za-z_]/.test(value),
      'Producer workflow aliases, tags and folded values are unsupported');
    if(value.startsWith("'"))need(value.endsWith("'"),'Multiline producer scalar is unsupported');
    if(value.startsWith('"')){try{JSON.parse(value);}catch{throw Error('Unsupported quoted producer scalar');}}
    if(value.startsWith('|')){need(value==='|','Unsupported producer literal modifier');literal=indent+(line.slice(indent).startsWith('- ')?2:0);}
    result.push(line);
  }
  return result;
}

function uniqueKeys(rows,indent,allowed){
  const seen=new Set();
  for(const line of rows){
    const match=new RegExp('^ {'+indent+'}([A-Za-z_][A-Za-z0-9_-]*):').exec(line);
    if(!match)continue;
    need(!seen.has(match[1])&&allowed.includes(match[1]),'Unknown or duplicate producer field: '+match[1]);
    seen.add(match[1]);
  }
  return seen;
}

export function packageProducerContract(raw){
  const all=lines(raw),top=uniqueKeys(all,0,['name','run-name','on','permissions','concurrency','env','defaults','jobs']);
  need(top.has('jobs')&&all.filter(line=>line==='jobs:').length===1,'One ordinary producer jobs mapping required');
  const start=all.indexOf('jobs:'),header=all.slice(0,start);
  need(all.slice(start+1).every(line=>line.startsWith(' ')),'Producer root fields must precede jobs');
  const jobs=[];
  for(let i=start+1;i<all.length;i++)if(/^  [A-Za-z_][A-Za-z0-9_-]*:$/.test(all[i]))jobs.push([all[i].slice(2,-1),i]);
  need(new Set(jobs.map(([name])=>name)).size===jobs.length,'Duplicate producer job');
  const at=jobs.findIndex(([name])=>name==='integration');
  need(at>=0,'Supported integration producer job required');
  const job=all.slice(jobs[at][1]+1,jobs[at+1]?.[1]??all.length);
  const fields=uniqueKeys(job,4,['needs','if','runs-on','timeout-minutes','strategy','permissions','env','defaults','steps']);
  need(fields.has('steps')&&job.filter(line=>line==='    steps:').length===1&&job.includes('    runs-on: ubuntu-latest'),
    'Isolated supported producer runner and steps required');
  const stepsAt=job.indexOf('    steps:');
  need(job.slice(stepsAt+1).every(line=>!/^    [^ ]/.test(line)),'Producer job fields must precede steps');
  const starts=[];
  for(let i=stepsAt+1;i<job.length;i++)if(/^      - /.test(job[i]))starts.push(i);
  need(starts.length&&starts[0]===stepsAt+1,'Ordinary producer step sequence required');
  const steps=starts.map((index,n)=>{
    const rows=job.slice(index,starts[n+1]??job.length),first=rows[0].replace('      - ','        ');
    const direct=[first,...rows.slice(1)];
    uniqueKeys(direct,8,['name','id','if','run','uses','with','env','shell','working-directory','continue-on-error','timeout-minutes']);
    const properties=Object.fromEntries(direct.filter(line=>/^        [^ ]/.test(line)).map(line=>{
      const split=line.indexOf(':');return [line.slice(8,split),line.slice(split+1).trimStart()];
    }));
    need(Boolean(properties.run)!==Boolean(properties.uses),'Exactly one producer command or action required');
    return {rows,properties};
  });
  const role=step=>{
    const p=step.properties;
    if(p.name){const found=Object.keys(names).find(key=>names[key]===p.name);if(found)return found;}
    if(/^actions\/setup-node@[a-f0-9]{40}$/.test(p.uses??''))return 'node';
    if(/^actions\/setup-python@[a-f0-9]{40}$/.test(p.uses??''))return 'python';
    if(p.run==='npm ci --no-audit --no-fund')return 'npm';
    if(p.run===install)return 'pip';
    return null;
  };
  const upload=steps.findIndex(step=>role(step)==='upload');
  need(upload>=0,'Immediate original producer upload required');
  const producer=steps.slice(0,upload+1),roles=producer.map(role);
  need(same(roles.filter(value=>value!=='pip'),
    ['checkout','materialize','verify','node','python','installer','npm','assembly','snapshot','build','inventory','upload']),
    'Unsupported effectful producer sequence');
  need(roles.filter(value=>value==='pip').length===1,'One scientific installation prerequisite required');
  const pipAt=roles.indexOf('pip'),assemblyAt=roles.indexOf('assembly');
  need(pipAt===assemblyAt-1||pipAt===assemblyAt+1,'Scientific installation must surround assembly and precede snapshot');
  const pip=producer[pipAt].properties;
  need(same(Object.keys(pip).sort(),['if','run'])&&
    (pip.if===ordinary||pip.if===`(${ordinary}) && steps.assembly.outputs.assembled != 'true'`),
    'Unsupported scientific installation prerequisite');
  const byRole=name=>producer[roles.indexOf(name)].properties;
  for(const [name,command]of [['snapshot','node scripts/package-output-artifact.mjs --snapshot'],
    ['build','npm run build:cloudflare'],['inventory','node scripts/package-output-artifact.mjs']]){
    const p=byRole(name);
    need(p.run===command&&p.if===fallback&&!p.uses&&!p['continue-on-error'],'Supported immediate build/capture command required');
  }
  need(/^actions\/checkout@[a-f0-9]{40}$/.test(byRole('checkout').uses??'')&&
    /^actions\/upload-artifact@[a-f0-9]{40}$/.test(byRole('upload').uses??'')&&
    byRole('upload').if==='success() && '+fallback,'Supported checkout and immediate artifact custody required');
  // Only installation's condition/position is normalized. Every other command,
  // action pin, inherited environment/default and effectful prefix remains exact.
  // The recognized full-build condition implies either installation condition.
  const plan={version:1,kind:'queue-full-build-producer-v1',header,job:job.slice(0,stepsAt),
    steps:producer.filter((_,i)=>roles[i]!=='pip').map(step=>step.rows),installation:install};
  return {kind:plan.kind,sha256:hash(JSON.stringify(plan))};
}

export function compatiblePackageProducers(before,current,workflowBodies){
  need(before?.kind==='immediate-cloudflare-build-v1'&&current?.kind===before.kind,
    'Immediate original build capture and unchanged producer workflow required');
  if(same(before,current))return null;
  const pin=value=>value?.workflows?.length===1&&value.workflows[0].path===workflowPath&&
    value.workflows[0].mode==='100644'&&/^[a-f0-9]{40}$/.test(value.workflows[0].oid??'');
  need(pin(before)&&pin(current)&&workflowBodies&&typeof workflowBodies.original==='string'&&typeof workflowBodies.current==='string',
    'Authenticated supported producer workflow bodies required; unchanged producer workflow required otherwise');
  need(oid(workflowBodies.original)===before.workflows[0].oid&&oid(workflowBodies.current)===current.workflows[0].oid,
    'Producer workflow body differs from immutable identity');
  const original=packageProducerContract(workflowBodies.original),next=packageProducerContract(workflowBodies.current);
  need(same(original,next),'Effective original build producer changed');
  return original;
}

// A semantic projection never grants producer authority. For changed YAML the
// actual successful job must also show installation before the capture window.
export function requireProducerInstallation(job){
  const steps=job?.steps;
  need(job?.status==='completed'&&job.conclusion==='success'&&Array.isArray(steps),'Successful complete original producer required');
  const unique=name=>{
    const rows=steps.filter(step=>step.name===name);
    need(rows.length===1&&rows[0].status==='completed'&&rows[0].conclusion==='success'&&Number.isSafeInteger(rows[0].number),
      'Successful original producer prerequisite required: '+name);
    return rows[0].number;
  };
  need(unique('Run '+install)<unique(names.snapshot),'Scientific installation must precede original snapshot');
}
