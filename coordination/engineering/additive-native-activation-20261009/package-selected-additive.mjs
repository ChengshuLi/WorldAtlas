// Original-output custody and current assembly execution remain separate from
// scientific preparation. Assembly consumes the same current products as builds.
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {isDeepStrictEqual} from 'node:util';
import {loadPackageInputs,containsPackagePath,admitPackageInputTransition} from '../../../scripts/package-inputs.mjs';

const demand=(v,m)=>{if(!v)throw Error(m);};
const ordinary=name=>{
  demand(path.isAbsolute(name)&&path.resolve(name)===name,'Canonical ordinary path required');
  let at=path.parse(name).root;
  for(const component of name.slice(at.length).split(path.sep)){
    at=path.join(at,component);demand(!fs.lstatSync(at).isSymbolicLink(),'Ordinary ancestors required');
  }
  const stat=fs.lstatSync(name);demand(stat.isFile(),'Ordinary whole file required');return stat;
};

// Acquire only a genuinely requested missing immutable tree. This does not
// substitute current bytes for historical provenance or move the checkout.
export function bindPackageImmutableCommits(reader,declared){
 const descriptor=reader.descriptor.bind(reader),available=new Set(),fetched=[];
 reader.descriptor=(name,version=reader.version)=>{
  demand(declared(name),'Undeclared additive package source/code payload: '+name);
  demand(typeof version==='string'&&/^[a-f0-9]{40}$/.test(version),'Exact immutable package source version required');
  if(!available.has(version)){
   try{reader.git('cat-file','-e',version+'^{commit}');}
   catch{reader.git('fetch','--quiet','--depth=1','--filter=blob:none','--no-tags','--no-write-fetch-head','origin',version);fetched.push(version);}
   reader.git('cat-file','-e',version+'^{commit}');available.add(version);
  }
  return descriptor(name,version);
 };
 return fetched;
}

// A distinct package assembly capability. Serialized build/context receipts
// never enter the existing consumedContext or current-execution WeakMaps.
const packageAssemblies = new WeakMap();
const assemblyHash = bytes => createHash('sha256').update(bytes).digest('hex');
const assemblySame = isDeepStrictEqual;
const assemblyFingerprint = value => assemblyHash(JSON.stringify(value));
const assemblySafe = value => typeof value === 'string' && /^[A-Za-z0-9_.\/-]+$/.test(value) &&
  !value.startsWith('/') && value.split('/').every(part => part && part !== '.' && part !== '..');
const assemblyCommit = value => /^[a-f0-9]{40}$/.test(value ?? '');
const assemblyDigest = value => /^[a-f0-9]{64}$/.test(value ?? '');
const assemblyPositive = value => Number.isSafeInteger(value) && value > 0;

function assemblyFile(root, relative) {
  demand(assemblySafe(relative),'Safe assembly member required');
  const file = path.resolve(root,relative), stat = ordinary(file);
  demand(Number.isSafeInteger(stat.size)&&stat.size>=0,'Invalid whole assembly member size');
  const fd=fs.openSync(file,fs.constants.O_RDONLY|fs.constants.O_NOFOLLOW), hash=createHash('sha256');
  const buffer=Buffer.alloc(1048576);let bytes=0;
  try {
    for(;;){const count=fs.readSync(fd,buffer,0,buffer.length,null);if(!count)break;
      bytes+=count;demand(bytes<=stat.size,'Assembly member grew');hash.update(buffer.subarray(0,count));}
    const held=fs.fstatSync(fd),end=ordinary(file);
    demand(bytes===stat.size&&['dev','ino','size','mode','mtimeMs','ctimeMs'].every(key=>stat[key]===held[key]&&held[key]===end[key]),'Assembly member changed');
  }finally{fs.closeSync(fd);}
  return {path:relative,bytes,sha256:hash.digest('hex')};
}

async function assemblyJobLog(api,repo,job) {
  demand(typeof api.jobLogRedirect==='function','Authenticated original job-log transport required');
  const redirect=await api.jobLogRedirect(`/repos/${repo}/actions/jobs/${job}/logs`);
  demand(redirect.status===302,'Original package job log unavailable');
  const url=new URL(redirect.headers.get('location'));
  demand(url.protocol==='https:'&&!url.username&&!url.password&&url.hostname.endsWith('.blob.core.windows.net'),'Unsupported original job-log transport');
  const response=await fetch(url,{redirect:'error',signal:AbortSignal.timeout(30000)});
  demand(response.ok&&response.body,'Original job log download failed');
  const chunks=[];let bytes=0;
  for await(const chunk of response.body){bytes+=chunk.length;chunks.push(Buffer.from(chunk));}
  return Buffer.concat(chunks,bytes).toString('utf8').split(/\r?\n/).map(line=>line.replace(/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d+Z /,''));
}

// Discovery and private admission share the same job/log/artifact authority.
// Reading this record grants no assembly capability; only whole output admission
// below can mint the private token.
export async function readOriginalPackageInventory({api,repo,origin}) {
  const workflowHead=origin?.workflow_head??origin?.head;
  demand(/^[-\w.]+\/[-\w.]+$/.test(repo??'')&&origin&&
    ['run_id','run_attempt','job_id','artifact_id','artifact_bytes'].every(key=>assemblyPositive(origin[key]))&&
    assemblyCommit(workflowHead)&&assemblyDigest(origin.artifact_digest),'Exact original package origin required');
  const artifactName=`cloudflare-package-output-${origin.run_id}-${origin.run_attempt}`;
  demand(origin.artifact_name===artifactName,'Exact original package artifact name required');
  const run=await api(`/repos/${repo}/actions/runs/${origin.run_id}/attempts/${origin.run_attempt}`);
  const pullRequest=run.event==='pull_request'&&run.path==='.github/workflows/merge-integration-checks.yml';
  const worker=run.event==='workflow_dispatch'&&run.path==='.github/workflows/worker-merge.yml'&&run.head_branch==='main'&&assemblyCommit(origin.workflow_head);
  demand(run.id===origin.run_id&&run.run_attempt===origin.run_attempt&&run.head_sha===workflowHead&&
    (pullRequest||worker)&&run.status==='completed'&&
    run.repository?.full_name===repo&&run.head_repository?.full_name===repo,'Original package run differs');
  const job=await api(`/repos/${repo}/actions/jobs/${origin.job_id}`);
  demand(job.id===origin.job_id&&job.run_id===origin.run_id&&job.run_attempt===origin.run_attempt&&job.head_sha===workflowHead&&
    job.status==='completed'&&job.conclusion==='success'&&Array.isArray(job.steps),'Original package producer did not succeed');
  const step=name=>job.steps.filter(row=>row.name===name&&row.status==='completed'&&row.conclusion==='success').length===1;
  const full=pullRequest&&job.name==='regression (0)',selected=pullRequest&&job.name==='package',
    finalWorker=worker&&job.name==='integration (0)';
  demand(full||selected||finalWorker,'Original package producer differs');
  // Authenticate actual capture/build/inventory/upload. Removed historical
  // scientific readback is not a current producer or consumer role.
  const sequence=full?['Snapshot original full-regression package inputs','Build hosted assets',
    'Inventory original full-regression package output','Complete regression shard','Retain original full-regression package output']:
    selected?['Snapshot original selected package inputs','Build Cloudflare package without publishing',
      'Inventory original selected package output','Run selected-data consumer checks','Retain original selected package output']:
      ['Snapshot original final-worker package inputs','Build the combined application once before asset-dependent tests',
        'Inventory original final-worker package output','Test applicable combined-tree invariants without publishing or live imports','Retain original final-worker package output'];
  demand(sequence.every(step),'Original package producer lacks required actual steps');
  const numbers=sequence.map(name=>job.steps.find(row=>row.name===name).number);
  demand(numbers.every((number,index)=>assemblyPositive(number)&&(index===0||number>numbers[index-1]))&&numbers[2]===numbers[1]+1,
    'Original inventory must immediately follow the build and upload must follow successful current tests');
  const artifact=await api(`/repos/${repo}/actions/artifacts/${origin.artifact_id}`);
  demand(artifact.id===origin.artifact_id&&artifact.name===artifactName&&!artifact.expired&&artifact.size_in_bytes===origin.artifact_bytes&&
    artifact.digest==='sha256:'+origin.artifact_digest&&artifact.workflow_run?.id===origin.run_id&&
    artifact.workflow_run?.head_sha===workflowHead,'Original package artifact differs');
  const lines=await assemblyJobLog(api,repo,origin.job_id),receipts=[];
  for(const line of lines){if(!line.startsWith('{'))continue;let value;try{value=JSON.parse(line);}catch{continue;}
    if(Object.hasOwn(value,'package_output_manifest_sha256'))receipts.push(value);}
  const uploads=lines.filter(line=>line.startsWith('Artifact '+artifactName+' has been successfully uploaded!'));
  demand(receipts.length===1&&assemblyCommit(receipts[0].original_head)&&
    (pullRequest?receipts[0].original_head===workflowHead:true)&&
    (origin.head===undefined||receipts[0].original_head===origin.head)&&
    assemblyDigest(receipts[0].package_output_manifest_sha256)&&assemblyPositive(receipts[0].package_output_manifest_bytes)&&
    uploads.length===1&&uploads[0]===`Artifact ${artifactName} has been successfully uploaded! Final size is ${origin.artifact_bytes} bytes. Artifact ID is ${origin.artifact_id}`,
    'Missing or ambiguous actual original package upload receipt');
  const executed=receipts[0].executed_workflow;
  demand(assemblyCommit(executed?.sha)&&executed.path===run.path&&
    (pullRequest?/^refs\/pull\/[1-9]\d*\/merge$/.test(executed.ref):executed.ref==='refs/heads/main'&&executed.sha===workflowHead),
    'Actual executed package workflow context is missing or differs');
  // Other receipts may have their own archive digests. The exact output digest
  // must occur once, and the artifact API independently binds it to this name.
  demand(lines.filter(line=>line===`SHA256 digest of uploaded artifact zip is ${origin.artifact_digest}`).length===1,'Original package upload digest differs');
  return {...receipts[0],workflow_head:workflowHead,workflow_path:run.path};
}

// Called only by the trusted assembly driver, using its authenticated GitHub
// client. It authenticates the actual originating producer and log, rather than
// accepting a caller-supplied success flag or a copied context certificate.
export async function authenticateOriginalPackageOutput({api,repo,origin,root,manifestRaw}) {
  demand(assemblyCommit(origin?.head)&&Buffer.isBuffer(manifestRaw)&&manifestRaw.length>0,
    'Whole original package manifest and exact source head required');
  const receipt=await readOriginalPackageInventory({api,repo,origin});
  demand(receipt.package_output_manifest_sha256===assemblyHash(manifestRaw)&&receipt.package_output_manifest_bytes===manifestRaw.length,
    'Original package inventory differs from retained manifest');
  const manifest=JSON.parse(manifestRaw);
  demand(manifest.version===1&&manifest.kind==='original-cloudflare-package-output'&&manifest.source?.head===origin.head&&
    Array.isArray(manifest.output?.files)&&manifest.output.files.length>0&&manifest.output.files.length<=20000&&
    assemblyPositive(manifest.output.bytes)&&Number.isSafeInteger(manifest.output.bytes),'Original package manifest differs');
  // Walk only the fixed executed workflow path. Adding an imported discovery
  // helper here would change the separately qualified native build closure.
  const commit=await api(`/repos/${repo}/git/commits/${receipt.executed_workflow.sha}`);
  let tree=commit.tree?.sha,workflow;
  const components=receipt.workflow_path.split('/');
  for(let index=0;index<components.length;index++){
    demand(assemblyCommit(tree),'Executed producer workflow tree unavailable');
    const listing=await api(`/repos/${repo}/git/trees/${tree}`);
    demand(!listing.truncated&&Array.isArray(listing.tree),'Complete executed workflow tree required');
    const matches=listing.tree.filter(row=>row.path===components[index]);
    demand(matches.length===1,'Unique executed workflow path required');workflow=matches[0];
    if(index<components.length-1){
      demand(workflow.type==='tree'&&workflow.mode==='040000','Ordinary executed workflow ancestors required');tree=workflow.sha;
    }
  }
  const captured=manifest.source.producer?.workflows?.filter(row=>row.path===receipt.workflow_path);
  demand(manifest.source.producer?.kind==='immediate-cloudflare-build-v1'&&captured?.length===1&&
    workflow?.type==='blob'&&workflow.mode==='100644'&&
    assemblySame(captured[0],{path:receipt.workflow_path,mode:workflow.mode,oid:workflow.sha}),
    'Actual executed producer workflow differs from original source descriptor');
  root=fs.realpathSync(root);const expected=new Set();let bytes=0;
  for(const pin of manifest.output.files){demand(assemblySafe(pin.path)&&/^dist\/(client|cloudflare)\//.test(pin.path)&&
      !expected.has(pin.path)&&Number.isSafeInteger(pin.bytes)&&pin.bytes>=0&&Number.isSafeInteger(pin.bytes)&&assemblyDigest(pin.sha256),'Invalid original output roster');
    expected.add(pin.path);bytes+=pin.bytes;demand(assemblySame(assemblyFile(root,pin.path),pin),'Original output member changed');}
  demand(bytes===manifest.output.bytes,'Original output total differs');
  const found=[];const visit=relative=>{const absolute=path.join(root,relative),stat=fs.lstatSync(absolute);
    demand(!stat.isSymbolicLink(),'Original output cannot contain links');
    if(stat.isDirectory())for(const name of fs.readdirSync(absolute))visit(relative+'/'+name);
    else{demand(stat.isFile(),'Original output must be ordinary');found.push(relative);}};
  visit('dist');demand(assemblySame(found.sort(),[...expected].sort()),'Original output complete inventory differs');
  const token=Object.freeze({kind:'authenticated-original-cloudflare-output',source_head:origin.head});
  packageAssemblies.set(token,{root,manifest,origin:structuredClone(origin),manifest_sha256:assemblyHash(manifestRaw),fingerprint:assemblyFingerprint(manifest)});
  return token;
}

export function requireOriginalPackageOutput(token) {
  const value=packageAssemblies.get(token);
  demand(value&&value.fingerprint===assemblyFingerprint(value.manifest),'Privately authenticated original package output required');
  return value;
}

const currentAssemblies=new WeakMap();
function assemblyGit(root,args,input) {
  return execFileSync('git',['-C',root,...args],{input,encoding:'utf8',maxBuffer:Infinity,
    env:{...process.env,GIT_NO_LAZY_FETCH:'1',GIT_TERMINAL_PROMPT:'0'}});
}

function assemblyCode(source,executingRoot) {
  const names=new Set(),files=[];
  const visit=name=>{
    demand(assemblySafe(name),'Safe assembly code path required');if(names.has(name))return;names.add(name);
    const stat=ordinary(path.join(executingRoot,name));
    const raw=fs.readFileSync(path.join(executingRoot,name)),mode=stat.mode&0o111?'100755':'100644';
    demand(raw.length===stat.size,'Whole assembly code length changed');
    const oid=createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex');
    demand(assemblyGit(source,['ls-tree','HEAD','--',name]).trim()===`${mode} blob ${oid}\t${name}`,'Executing assembly code differs from current source');
    files.push({path:name,mode,bytes:raw.length,sha256:assemblyHash(raw),git_blob:oid});
    for(const match of raw.toString('utf8').matchAll(/(?:from\s*|import\s*(?:\(\s*)?)['"]([^'"]+)['"]/g))
      if(match[1].startsWith('.'))visit(path.posix.normalize(path.posix.join(path.posix.dirname(name),match[1])));
  };
  visit('scripts/assemble-selected-package.mjs');return files.sort((a,b)=>a.path.localeCompare(b.path,'en'));
}

function assemblySourceAdmission(original,source,acceptedInputs) {
  const before=requireOriginalPackageOutput(original).manifest.source,definition=loadPackageInputs(source);
  const read=name=>{
    const file=path.join(source,name),stat=ordinary(file);
    const raw=fs.readFileSync(file);demand(raw.length===stat.size,'Whole assembly metadata length changed');
    const oid=createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex');
    demand(assemblyGit(source,['ls-tree','HEAD','--',name]).trim()===`100644 blob ${oid}\t${name}`,'Assembly metadata differs from actual Git source');return JSON.parse(raw);
  };
  demand(assemblySame(read('.github/package-inputs.json'),definition),'Current package definition drift');
  const selection=read('data/ownership-selection.json');
  const all=assemblyGit(source,['ls-tree','-rz','--full-tree','HEAD']).split('\0').filter(Boolean).map(line=>{
    const tab=line.indexOf('\t'),[mode,type,oid]=line.slice(0,tab).split(' ');return {path:line.slice(tab+1),mode,type,oid};
  });
  const rows=all.filter(row=>containsPackagePath(definition.inputs,row.path));
  demand(rows.every(row=>row.type==='blob'&&['100644','100755'].includes(row.mode)),'Ordinary original input roles required');
  const plain=rows.map(({type,...row})=>row);
  const workflowPaths=['.github/workflows/merge-integration-checks.yml','.github/workflows/worker-merge.yml'];
  const workflows=all.filter(row=>workflowPaths.includes(row.path));
  demand(workflows.length===workflowPaths.length&&workflows.every(row=>row.type==='blob'&&row.mode==='100644'),
    'Ordinary original producer workflows required');
  const workflowPins=workflows.map(({type,...row})=>row);
  demand(before.producer?.kind==='immediate-cloudflare-build-v1'&&assemblySame(before.producer,{kind:'immediate-cloudflare-build-v1',workflows:workflowPins}),
    'Immediate original build capture and unchanged producer workflow required');
  const current={head:assemblyGit(source,['rev-parse','HEAD']).trim(),definition,selection,files:plain,
    producer:{kind:'immediate-cloudflare-build-v1',workflows:workflowPins}};
  admitPackageInputTransition(before,current,{acceptedInputs,preliminary:true});
}

// Separate from package-issued full-build execution: this authenticates only the
// actual small assembly programme and its immutable current source identities.
export function issuePackageAssemblyExecution({original,source,stage,executingRoot,acceptedInputs}) {
  requireOriginalPackageOutput(original);
  demand(process.execArgv.length===0&&!process.env.NODE_OPTIONS?.trim()&&!process.env.NODE_PATH?.trim(),'Plain assembly Node execution required');
  source=fs.realpathSync(source);stage=fs.realpathSync(stage);executingRoot=fs.realpathSync(executingRoot);
  assemblySourceAdmission(original,source,acceptedInputs);
  demand(path.resolve(process.argv[1])===path.join(executingRoot,'scripts/assemble-selected-package.mjs'),'Actual assembly driver required');
  const files=assemblyCode(source,executingRoot), executable=fs.realpathSync(process.execPath);
  const runtime={...assemblyFile(path.dirname(executable),path.basename(executable)),
    executable,version:process.version,versions:process.versions,platform:process.platform,arch:process.arch};
  delete runtime.path;
  const record=Object.freeze({kind:'current-selected-package-assembly',source_root:source,
    source_commit:assemblyGit(source,['rev-parse','HEAD']).trim(),source_tree:assemblyGit(source,['rev-parse','HEAD^{tree}']).trim(),
    stage_root:stage,entry_point:'scripts/assemble-selected-package.mjs',files,runtime,original});
  currentAssemblies.set(record,{executingRoot,fingerprint:assemblyFingerprint(record)});return record;
}
export function requirePackageAssemblyExecution(record) {
  const held=currentAssemblies.get(record);demand(held&&held.fingerprint===assemblyFingerprint(record),'Private current assembly execution required');
  requireOriginalPackageOutput(record.original);
  demand(assemblyGit(record.source_root,['rev-parse','HEAD']).trim()===record.source_commit&&
    assemblyGit(record.source_root,['rev-parse','HEAD^{tree}']).trim()===record.source_tree,'Assembly source changed');
  demand(assemblySame(assemblyCode(record.source_root,held.executingRoot),record.files),'Assembly code changed');
  const runtime=assemblyFile(path.dirname(record.runtime.executable),path.basename(record.runtime.executable));
  demand(runtime.bytes===record.runtime.bytes&&runtime.sha256===record.runtime.sha256&&record.runtime.version===process.version,'Assembly runtime changed');
  return record;
}
