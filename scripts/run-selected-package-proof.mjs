// Separately identified observer for an accepted changed-selection delivery.
// The production tree and its original full producer retain their own identities.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync,spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {githubAPI} from './issue-claim-contract.mjs';
import {loadSelectedPackageReadback} from './selected-package-readback-proof.mjs';
import {compareSelectedPackageReadback} from './compare-selected-package-output.mjs';
import {validatePackageOutputManifest,inventoryPackageOutput} from './package-output-artifact.mjs';

const need=(ok,message)=>{if(!ok)throw Error(message);};
const sha=raw=>createHash('sha256').update(raw).digest('hex');
const oid=value=>typeof value==='string'&&/^[a-f0-9]{40}$/.test(value);
const positive=value=>Number.isSafeInteger(value)&&value>0;
const repository='ChengshuLi/WorldAtlas';
const sameOrigin=(left,right)=>JSON.stringify(left)===JSON.stringify(right);
const proofRoot=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
function cleanEnvironment(){
  const env={...process.env};
  for(const key of Object.keys(env))if(/TOKEN|SECRET|PASSWORD|CREDENTIAL|AUTHORIZATION|COOKIE/i.test(key)||key.startsWith('GIT_')||['GH_TOKEN','GITHUB_TOKEN','NODE_OPTIONS','NODE_PATH','LD_PRELOAD','LD_LIBRARY_PATH','DYLD_INSERT_LIBRARIES','DYLD_LIBRARY_PATH'].includes(key))delete env[key];
  return {...env,GIT_NO_LAZY_FETCH:'1',GIT_NO_REPLACE_OBJECTS:'1',GIT_CONFIG_NOSYSTEM:'1',GIT_CONFIG_GLOBAL:'/dev/null',GIT_TERMINAL_PROMPT:'0'};
}
const git=(root,...args)=>execFileSync('git',['-C',root,...args],{encoding:'utf8',env:cleanEnvironment(),maxBuffer:8*1048576}).trim();
export async function resolveFrozenPackageProgramme({api,sourceHead,pullRequest}){
  need(oid(sourceHead)&&positive(pullRequest),'Exact accepted source and pull request required');
  const pr=await api(`/repos/${repository}/pulls/${pullRequest}`);
  need(pr.number===pullRequest&&pr.merged===true&&pr.state==='closed'&&pr.base?.ref==='main'&&
    pr.head?.repo?.full_name===repository&&oid(pr.head.sha)&&oid(pr.merge_commit_sha),
    'Production programme must be an accepted same-repository main delivery');
  const accepted=await api(`/repos/${repository}/git/commits/${pr.merge_commit_sha}`);
  const candidate=await api(`/repos/${repository}/git/commits/${sourceHead}`);
  need(accepted.sha===pr.merge_commit_sha&&candidate.sha===sourceHead&&oid(accepted.tree?.sha)&&
    candidate.tree?.sha===accepted.tree.sha,'Frozen source differs from complete accepted production tree');
  return {pull_request:pullRequest,reviewed_head:pr.head.sha,accepted_commit:pr.merge_commit_sha,
    source_head:sourceHead,source_tree:accepted.tree.sha};
}
export function requireSeparatedProofRoots({sourceRoot,observerRoot,sourceHead,proofHead}){
  need(oid(sourceHead)&&oid(proofHead),'Exact source and observer identities required');
  const source=fs.realpathSync(sourceRoot),observer=fs.realpathSync(observerRoot);
  need(source===path.resolve(sourceRoot)&&observer===path.resolve(observerRoot)&&source!==observer&&
    !source.startsWith(observer+path.sep)&&!observer.startsWith(source+path.sep),'Separate ordinary production and proof checkouts required');
  need(git(source,'rev-parse','HEAD')===sourceHead&&git(observer,'rev-parse','HEAD')===proofHead,
    'Actual source or observer checkout identity differs');
  return {source,observer};
}
export function prepareFreshAssemblyScratch(sourceRoot){
  const cache=path.join(sourceRoot,'.cache');
  let existing;try{existing=fs.lstatSync(cache);}catch(error){if(error.code!=='ENOENT')throw error;}
  need(!existing||existing.isDirectory()&&!existing.isSymbolicLink(),'Ordinary assembly scratch directory required');
  if(!existing)fs.mkdirSync(cache,{mode:0o700});
  const receiptPath=path.join(cache,'package-input-build.json');
  for(const target of [path.join(sourceRoot,'dist'),receiptPath,path.join(cache,'selected-package-proof.json'),path.join(cache,'selected-package-child-proof.json'),path.join(cache,'package-runtime-comparison.json'),path.join(cache,'frozen-cli-output'),path.join(cache,'selected-package-child-diagnostic.json')]){
    let prior;try{prior=fs.lstatSync(target);}catch(error){if(error.code!=='ENOENT')throw error;}
    need(!prior,'Fresh frozen proof checkout required; prior output is not evidence');
  }
  return receiptPath;
}
export function recordFrozenChildDiagnostic({child,sourceRoot,secret='',log=message=>console.error(message)}){
  // Observe the real child before touching its optional post-commit receipt.
  // Never serialize its spawn options, full environment or API credential.
  const sanitize=value=>{
    let text=String(value??'');
    if(secret)text=text.split(secret).join('[redacted]');
    text=text.replace(/\b(?:gh[pousr]_[A-Za-z0-9_]+|github_pat_[A-Za-z0-9_]+)\b/g,'[redacted]')
      .replace(/Bearer\s+[^\s'"<>]+/gi,'Bearer [redacted]')
      .replace(/https?:\/\/[^\s'"<>]+/g,'[delivery address]');
    // Keep useful tail diagnostics without unbounded hosted logs/artifacts.
    return {text:text.length>8192?text.slice(0,4096)+'\n[...diagnostic middle omitted...]\n'+text.slice(-4096):text,
      original_characters:String(value??'').length,truncated:text.length>8192};
  };
  const diagnostic={version:1,kind:'frozen-package-child-execution-diagnostic',
    status:child.status??null,signal:child.signal??null,
    error_code:/^[A-Z0-9_]+$/.test(child.error?.code??'')?child.error.code:null,error:sanitize(child.error?.message),
    stdout:sanitize(child.stdout),stderr:sanitize(child.stderr),
    semantics:'Child observation only; does not establish assembly, equivalence or consumer success.'};
  const file=path.join(sourceRoot,'.cache/selected-package-child-diagnostic.json');
  log('Frozen package child diagnostic: '+JSON.stringify(diagnostic));
  try{fs.writeFileSync(file,JSON.stringify(diagnostic,null,2)+'\n',{flag:'wx',mode:0o600});}
  catch(error){
    const code=/^[A-Z0-9_]+$/.test(error.code??'')?error.code:'UNKNOWN';
    log('Frozen child diagnostic persistence failed: '+JSON.stringify({code,error:sanitize(error.message)}));
    throw Error('Unable to retain frozen child diagnostic ('+code+'); original child observation logged above');
  }
  const receiptPath=path.join(sourceRoot,'.cache/package-input-build.json');
  let stat;try{stat=fs.lstatSync(receiptPath);}catch(error){if(error.code!=='ENOENT')throw error;}
  need(stat?.isFile()&&!stat.isSymbolicLink(),
    'Frozen assembly did not publish an ordinary receipt; see the retained child diagnostic above');
  return fs.readFileSync(receiptPath);
}
export function requireActualAssembly(child,receiptRaw,sourceHead,originalRunId){
  need(child?.status===0&&!child.error&&child.signal===null,'Successful actual production assembly required');
  const lines=String(child.stdout).trim().split('\n');
  const result=JSON.parse(lines.at(-1));
  need(result.assembled===true&&result.receipt_sha256===sha(receiptRaw),
    'Successful child result must bind actual receipt');
  const receipt=JSON.parse(receiptRaw);
  need(receipt.kind==='cloudflare'&&receipt.preflight?.passed===true&&
    Array.isArray(receipt.preflight.errors)&&receipt.preflight.errors.length===0&&receipt.preflight.inputs?.head===sourceHead&&
    receipt.assembly?.kind==='retained-original-output-plus-current-additive'&&receipt.assembly.runtime_identity_version===2&&
    receipt.assembly.current_execution?.source_commit===sourceHead&&
    receipt.assembly.original_base_context_retained===true&&receipt.assembly.base_restoration_invoked===false&&
    receipt.assembly.invariant_build_invoked===false&&oid(receipt.assembly.origin?.head)&&
    receipt.assembly.origin.run_id===originalRunId&&/^[a-f0-9]{64}$/.test(receipt.assembly.original_manifest_sha256??'')&&
    sameOrigin(result.origin,receipt.assembly.origin),'Committed assembly receipt identity differs');
  return {receipt,receipt_sha256:sha(receiptRaw),origin:receipt.assembly.origin,
    frozen_cli:{exit_status:child.status,result,committed_output_observed:true,cli_succeeded:true}};
}
export async function retainProofManifest({api,origin,directory,extractor,expectedHash,fetchImpl=fetch}){
  need(positive(origin?.artifact_id)&&positive(origin.artifact_bytes)&&/^[a-f0-9]{64}$/.test(origin.artifact_digest??'')&&
    /^[a-f0-9]{64}$/.test(expectedHash),'Exact original archive and manifest identity required');
  const disk=fs.statfsSync(directory);need(disk.bavail*disk.bsize>=origin.artifact_bytes+8*1048576,'Insufficient disk for actual proof archive and control manifest');
  const archive=path.join(directory,'original-output.zip'),manifest=path.join(directory,'original-manifest.json');
  const redirect=await api.artifactRedirect(`/repos/${repository}/actions/artifacts/${origin.artifact_id}/zip`);
  need(redirect.status===302,'Original proof archive redirect unavailable');
  const url=new URL(redirect.headers.get('location'));
  need(url.protocol==='https:'&&!url.username&&!url.password&&!url.port&&url.hostname.endsWith('.blob.core.windows.net'),'Unsupported original proof archive delivery');
  const response=await fetchImpl(url,{redirect:'error',signal:AbortSignal.timeout(120000)});
  need(response.ok&&response.body,'Original proof archive unavailable');
  const fd=fs.openSync(archive,'wx',0o600),digest=createHash('sha256');let bytes=0;
  try{for await(const chunk of response.body){bytes+=chunk.length;need(bytes<=origin.artifact_bytes,'Original proof archive grew');digest.update(chunk);fs.writeSync(fd,chunk);}}
  finally{fs.closeSync(fd);}
  need(bytes===origin.artifact_bytes&&digest.digest('hex')===origin.artifact_digest,'Original proof archive digest differs');
  execFileSync('python3',['-I','-S','-B',extractor,'--manifest',archive,manifest,origin.artifact_digest],{env:cleanEnvironment(),stdio:'pipe',maxBuffer:1048576});
  const raw=fs.readFileSync(manifest);need(sha(raw)===expectedHash,'Original proof manifest differs from authenticated assembly');
  validatePackageOutputManifest(JSON.parse(raw));fs.unlinkSync(archive);return {file:manifest,raw};
}


async function main(){
  need(process.env.GITHUB_REPOSITORY===repository&&process.env.GITHUB_REF==='refs/heads/main'&&
    process.env.GITHUB_EVENT_NAME==='workflow_dispatch'&&process.env.GITHUB_WORKFLOW==='Selected package equivalence proof',
    'Proof runs from accepted main workflow only');
  const event=JSON.parse(fs.readFileSync(process.env.GITHUB_EVENT_PATH)),input=event.inputs??{};
  const token=process.env.GH_TOKEN;need(token,'Read-only proof API authority required');
  const api=githubAPI(token,{conditionalReads:false});delete process.env.GH_TOKEN;delete process.env.GITHUB_TOKEN;
  need(/^[1-9]\d*$/.test(input.source_pull_request??''),'Exact accepted source pull request required');
  const frozen=await resolveFrozenPackageProgramme({api,sourceHead:input.source_head,pullRequest:Number(input.source_pull_request)});
  if(process.argv[2]==='--resolve-frozen'){
    fs.appendFileSync(process.env.GITHUB_OUTPUT,`programme_sha=${frozen.accepted_commit}\nsource_tree=${frozen.source_tree}\n`);
    console.log(JSON.stringify({frozen_package_programme:frozen}));return;
  }
  need(process.argv.length===2,'Unknown proof invocation');
  for(const key of ['original_run_id','readback_run_id','readback_attempt'])need(/^[1-9]\d*$/.test(input[key]??'')&&positive(Number(input[key])),'Exact proof run required');
  const sourceRoot=path.resolve(proofRoot,'../candidate');
  requireSeparatedProofRoots({sourceRoot,observerRoot:proofRoot,sourceHead:input.source_head,proofHead:process.env.GITHUB_SHA});
  need(git(sourceRoot,'rev-parse','HEAD^{tree}')===frozen.source_tree,'Actual frozen production tree differs');
  // The current observer graph was authenticated by the same bootstrap before
  // startup. Authenticate the frozen graph independently before importing it.
  const startup=JSON.parse(execFileSync('python3',['-I','-S','-B',path.join(proofRoot,'scripts/selected-package-bootstrap.py')],{
    cwd:sourceRoot,env:{...cleanEnvironment(),GH_TOKEN:token,SELECTED_PACKAGE_TRUSTED_BASE:frozen.accepted_commit,
      SELECTED_PACKAGE_ENTRY_POINT:'scripts/assemble-selected-package.mjs',SELECTED_PACKAGE_VERIFY_ONLY:'true'},encoding:'utf8',maxBuffer:1048576}));
  need(startup.kind==='authenticated-package-startup-closure'&&startup.trusted_base===frozen.accepted_commit&&
    startup.entry_point==='scripts/assemble-selected-package.mjs'&&startup.files.includes(startup.entry_point),'Frozen startup authentication missing');
  const readback=await loadSelectedPackageReadback({api,repo:repository,runId:Number(input.readback_run_id),
    attempt:Number(input.readback_attempt),expectedHead:input.source_head,expectedPullRequest:Number(input.source_pull_request)});
  // Invoke the genuine production CLI. It must finish actual assembly successfully.
  // This observer independently authenticates the reference and compares output.
  const receiptPath=prepareFreshAssemblyScratch(sourceRoot);
  const child=spawnSync('python3',['-I','-S','-B',path.join(proofRoot,'scripts/selected-package-bootstrap.py')],{
    cwd:sourceRoot,env:{...cleanEnvironment(),GH_TOKEN:token,SELECTED_PACKAGE_TRUSTED_BASE:frozen.accepted_commit,
      SELECTED_PACKAGE_ENTRY_POINT:'scripts/assemble-selected-package.mjs',SELECTED_PACKAGE_VERIFY_ONLY:'false',
      GITHUB_OUTPUT:path.join(sourceRoot,'.cache/frozen-cli-output')},encoding:'utf8',maxBuffer:8*1048576});
  const receiptRaw=recordFrozenChildDiagnostic({child,sourceRoot,secret:token});
  const committed=requireActualAssembly(child,receiptRaw,input.source_head,Number(input.original_run_id));
  const {receipt}=committed;
  const directory=fs.mkdtempSync(path.join(proofRoot,'.cache-proof-'));
  try{
    const original=await retainProofManifest({api,origin:committed.origin,directory,
      extractor:path.join(proofRoot,'scripts/extract-package-output.py'),expectedHash:receipt.assembly.original_manifest_sha256});
    const manifest=JSON.parse(original.raw);
    need(manifest.runtime.installed?.version===2,'Version 2 original installed evidence required for current proof');
    const selection=JSON.parse(fs.readFileSync(path.join(sourceRoot,'data/ownership-selection.json')));
    need(JSON.stringify(manifest.source.selection.additive_release)!==JSON.stringify(selection.additive_release),'Changed selection required');
    const inventory=inventoryPackageOutput(sourceRoot),atlas=JSON.parse(fs.readFileSync(path.join(sourceRoot,'dist/client/atlas-geography.json')));
    need(['base_manifest','ledger','owner_roster','patch'].some(role=>{
      const pin=atlas.additiveRelease?.[role],old=manifest.output.files.find(row=>row.path==='dist/client/'+pin?.path);
      return old&&old.sha256!==pin.sha256&&inventory.files.some(row=>row.path===old.path&&row.sha256===pin.sha256);
    }),'Genuine changed additive output required');
    // Only original metadata blobs are acquired; never a historical checkout.
    const originalHead=manifest.source.head;
    try{git(sourceRoot,'cat-file','-e',originalHead+'^{commit}');}
    catch{git(sourceRoot,'fetch','--quiet','--depth=1','--filter=blob:none','--no-tags','--no-write-fetch-head','origin',originalHead);}
    for(const name of ['.github/package-inputs.json','data/ownership-selection.json'])execFileSync('git',['-C',sourceRoot,'show',originalHead+':'+name],
      {env:{...cleanEnvironment(),GIT_NO_LAZY_FETCH:'0'},stdio:'pipe',maxBuffer:8*1048576});
    const comparison=compareSelectedPackageReadback({assembled:sourceRoot,sourceRoot,readback:readback.report,trustedBase:frozen.accepted_commit,
      originalHead,currentHead:input.source_head,originalManifest:original.file});
    const implementationFiles=['scripts/run-selected-package-proof.mjs','scripts/compare-selected-package-output.mjs',
      'scripts/selected-package-bootstrap.py','scripts/selected-package-readback-proof.mjs','scripts/package-output-artifact.mjs','scripts/extract-package-output.py'];
    const proof={version:2,kind:'separate-observer-accepted-package-equivalence',frozen_programme:frozen,
      proof_implementation:{commit:process.env.GITHUB_SHA,tree:git(proofRoot,'rev-parse','HEAD^{tree}'),
        files:implementationFiles.map(name=>{const raw=fs.readFileSync(path.join(proofRoot,name));return {path:name,bytes:raw.length,sha256:sha(raw)};})},
      original:committed.origin,reference:readback.origin,assembly_receipt_sha256:committed.receipt_sha256,
      frozen_startup:startup,frozen_cli:committed.frozen_cli,comparison,current_consumers:'Required subsequent native, smoke and selected-output steps in this same proof job.'};
    fs.writeFileSync(path.join(sourceRoot,'.cache/selected-package-proof.json'),JSON.stringify(proof,null,2)+'\n',{flag:'wx'});
    fs.writeFileSync(path.join(sourceRoot,'.cache/selected-package-original-manifest.json'),original.raw,{flag:'wx'});
    fs.appendFileSync(process.env.GITHUB_OUTPUT,`assembled=true\nassembly_sha256=${committed.receipt_sha256}\n`);
    console.log(JSON.stringify({assembled:true,frozen_cli:committed.frozen_cli,proof:comparison,proof_implementation:process.env.GITHUB_SHA,origin:committed.origin}));
  }finally{fs.rmSync(directory,{recursive:true,force:true});}
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url))main().catch(error=>{console.error(error.message);process.exitCode=1;});
