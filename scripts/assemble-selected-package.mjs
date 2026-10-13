// Executed only after trusted selected-data classification proves this complete
// programme is unchanged from the PR base. API credentials stay in trusted code;
// subprocesses and the current scientific reader receive no token environment.
import fs from 'node:fs';
import fsp from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {processingAllowance} from './check-effective-geographic-regression.mjs';
import {loadSelectedPackageReadback} from './selected-package-readback-proof.mjs';
import {githubAPI, githubPages} from './issue-claim-contract.mjs';
import {integrationTree} from './integration-profile.mjs';
import {loadPackageInputs, readPackageInputs, containsPackagePath} from './package-inputs.mjs';
import {inspectPackageRuntime, verifyPackageDependencies} from './package-build.mjs';
import {committedPackageInputs, committedPackageProgramme, packageProducerPath, packageBuildConfiguration,
  validatePackageOutputManifest, admitPackageOutputTransition, streamedPackageFile, installedPackageIdentity, installedPackageDifferences, declaredPackagePythonRoots} from './package-output-artifact.mjs';
import {authenticateOriginalPackageOutput, issuePackageAssemblyExecution, preparePackageSelectedAdditive,
  publishPackageSelectedAdditive, packageSelectedPublicationInventory, requirePackageAssemblyExecution}
  from '../coordination/engineering/additive-native-activation-20261009/package-selected-additive.mjs';

const need=(ok,message)=>{if(!ok)throw Error(message);};
const hash=raw=>createHash('sha256').update(raw).digest('hex');
const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const git=args=>execFileSync('git',['-C',root,...args],{encoding:'utf8',maxBuffer:32*1048576,
  env:{...process.env,GIT_NO_LAZY_FETCH:'1',GIT_TERMINAL_PROMPT:'0'}}).trim();
const ordered=rows=>rows.sort((a,b)=>a.path.localeCompare(b.path,'en'));
export function admitAssemblyAtlasMetadata(bytes,allowance=processingAllowance()){
  need(Number.isSafeInteger(bytes)&&bytes>0&&2*bytes<=allowance.phaseBytes,'Actual atlas exceeds current metadata allocation');
  return bytes;
}
export async function createPackageAssemblyScratch(sourceRoot){
  const cache=path.join(sourceRoot,'.cache');
  let stat;try{stat=await fsp.lstat(cache);}catch(error){if(error.code!=='ENOENT')throw error;}
  need(!stat||stat.isDirectory()&&!stat.isSymbolicLink(),'Ordinary package assembly scratch directory required');
  if(!stat)await fsp.mkdir(cache,{mode:0o700});
  return fsp.mkdtemp(path.join(cache,'selected-package-'));
}
function admitDisk(bytes,label){
  const disk=fs.statfsSync(root);
  need(Number.isSafeInteger(bytes)&&bytes>=0&&disk.bavail*disk.bsize>=bytes,'Insufficient disk for '+label);
}
const treeRows=tree=>ordered([...tree.entries.values()].filter(row=>row.type==='blob').map(row=>({path:row.path,mode:row.mode,oid:row.sha})));

async function blobJSON(api,repo,tree,name){
  const row=tree.entries.get(name);need(row?.type==='blob'&&row.mode==='100644'&&row.size<=8*1048576,'Bounded ordinary original metadata required');
  const blob=await api(`/repos/${repo}/git/blobs/${row.sha}`);need(blob.encoding==='base64','Original metadata body unavailable');
  const raw=Buffer.from(blob.content,'base64');need(raw.length===row.size&&createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex')===row.sha,'Original metadata Git identity differs');
  return JSON.parse(raw);
}
function sourceCompatible(before,current){
  const {inputs:oldInputs,...oldPolicy}=before.definition,{inputs:newInputs,...newPolicy}=current.definition;
  if(!same(oldPolicy,newPolicy)||!same(oldInputs,newInputs.slice(0,oldInputs.length)))return false;
  const {additive_release:oldHook,...oldBase}=before.selection,{additive_release:newHook,...newBase}=current.selection;
  if(!oldHook||!newHook||!same(oldBase,newBase)||!same(before.programme,current.programme))return false;
  const now=new Map(current.files.map(row=>[row.path,row]));
  return before.files.every(row=>now.has(row.path)&&(['.github/package-inputs.json','data/ownership-selection.json'].includes(row.path)||same(row,now.get(row.path))));
}

export async function findOriginalPackage({api,repo,current,originalRunId}){
  // A small recent-result search is an optimization. Exhaustion means a full
  // build, never a claim that no older result exists.
  need(originalRunId===undefined||Number.isSafeInteger(originalRunId)&&originalRunId>0,'Exact optional original run required');
  const response=originalRunId===undefined?await api(`/repos/${repo}/actions/workflows/merge-integration-checks.yml/runs?event=pull_request&per_page=20&page=1`):
    {workflow_runs:[await api(`/repos/${repo}/actions/runs/${originalRunId}`)]};
  need(Array.isArray(response.workflow_runs),'Original run discovery unavailable');
  if(originalRunId!==undefined)need(response.workflow_runs.length===1&&response.workflow_runs[0]?.id===originalRunId,'Pinned original run identity differs');
  const seen=new Set();
  for(const run of response.workflow_runs){
    if(run.status!=='completed'||seen.has(run.head_sha)||run.repository?.full_name!==repo||run.head_repository?.full_name!==repo)continue;
    seen.add(run.head_sha);
    const tree=await integrationTree(api,repo,run.head_sha),all=treeRows(tree);
    const programme=all.filter(row=>packageProducerPath(row.path));
    if(!same(programme,current.programme))continue;
    const definition=await readPackageInputs({route:`/repos/${repo}`,base:run.head_sha,api});
    const source={head:run.head_sha,tree:tree.object.tree.sha,definition,programme,
      files:all.filter(row=>containsPackagePath(definition.inputs,row.path)),
      selection:await blobJSON(api,repo,tree,'data/ownership-selection.json')};
    if(!sourceCompatible(source,current))continue;
    const jobs=await githubPages(async route=>(await api(route)).jobs,
      `/repos/${repo}/actions/runs/${run.id}/attempts/${run.run_attempt}/jobs`);
    const candidates=jobs.filter(job=>job.status==='completed'&&job.conclusion==='success'&&
      job.steps?.some(step=>['Retain original full-regression package output','Retain original selected package output'].includes(step.name)&&step.conclusion==='success'));
    if(candidates.length!==1)continue;
    const artifactName=`cloudflare-package-output-${run.id}-${run.run_attempt}`;
    const inventory=await api(`/repos/${repo}/actions/runs/${run.id}/artifacts?per_page=100&page=1`);
    if(!Array.isArray(inventory.artifacts)||inventory.total_count!==inventory.artifacts.length)continue;
    const matches=inventory.artifacts.filter(row=>row.name===artifactName&&!row.expired);
    if(matches.length!==1)continue;
    const artifact=matches[0];
    if(!/^sha256:[a-f0-9]{64}$/.test(artifact.digest??'')||!Number.isSafeInteger(artifact.size_in_bytes)||artifact.size_in_bytes<=0)continue;
    return {source,origin:{run_id:run.id,run_attempt:run.run_attempt,job_id:candidates[0].id,head:run.head_sha,
      artifact_id:artifact.id,artifact_name:artifactName,artifact_digest:artifact.digest.slice(7),artifact_bytes:artifact.size_in_bytes}};
  }
  return null;
}

async function downloadOriginal(api,repo,origin,destination){
  const response=await api.artifactRedirect(`/repos/${repo}/actions/artifacts/${origin.artifact_id}/zip`);
  need(response.status===302,'Original output artifact unavailable');
  const url=new URL(response.headers.get('location'));
  need(url.protocol==='https:'&&!url.username&&!url.password&&url.hostname.endsWith('.blob.core.windows.net'),'Unsupported original output delivery');
  const delivery=await fetch(url,{redirect:'error',signal:AbortSignal.timeout(120000)});
  need(delivery.ok&&delivery.body,'Original output delivery failed');
  const fd=fs.openSync(destination,'wx',0o600),digest=createHash('sha256');let bytes=0;
  try{for await(const chunk of delivery.body){bytes+=chunk.length;need(bytes<=origin.artifact_bytes,'Original archive exceeds authenticated bytes');digest.update(chunk);fs.writeSync(fd,chunk);}}
  finally{fs.closeSync(fd);}
  need(bytes===origin.artifact_bytes&&digest.digest('hex')===origin.artifact_digest,'Original output archive differs');
}

function currentSource(){
  const definition=loadPackageInputs(root);
  const actual=relative=>{
    const raw=fs.readFileSync(path.join(root,relative)),row=git(['ls-tree','HEAD','--',relative]);
    need(row===`100644 blob ${createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex')}\t${relative}`,'Current selected metadata differs from Git');return JSON.parse(raw);
  };
  need(same(actual('.github/package-inputs.json'),definition),'Current package declaration differs');
  return {head:git(['rev-parse','HEAD']),tree:git(['rev-parse','HEAD^{tree}']),definition,
    selection:actual('data/ownership-selection.json'),input_definition_sha256:hash(fs.readFileSync(path.join(root,'.github/package-inputs.json'))),
    files:committedPackageInputs(root,definition),programme:committedPackageProgramme(root)};
}

export async function assembleSelectedPackage({api,repo,expectedHead,originalRunId,proofReadback}){
  const started=performance.now(),current=currentSource();need(current.head===expectedHead,'Actual selected head changed');
  const found=await findOriginalPackage({api,repo,current,originalRunId});if(!found)return {assembled:false,reason:'No applicable retained original output in bounded recent-result search'};
  await verifyPackageDependencies(path.join(root,'node_modules'));
  admitDisk(found.origin.artifact_bytes,'the actual authenticated original archive');
  const scratch=await createPackageAssemblyScratch(root);
  let committed=false,preserveScratch=false;
  try{
    const archive=path.join(scratch,'original.zip'),manifestFile=path.join(scratch,'manifest.json');
    await downloadOriginal(api,repo,found.origin,archive);
    const pythonArgs=['-I','-S','-B',path.join(root,'scripts/extract-package-output.py')];
    execFileSync('python3',[...pythonArgs,'--manifest',archive,manifestFile,found.origin.artifact_digest],{stdio:'pipe',maxBuffer:1048576});
    const manifestRaw=fs.readFileSync(manifestFile),manifest=validatePackageOutputManifest(JSON.parse(manifestRaw));
    for(const key of ['head','tree','definition','files','programme','selection'])need(same(manifest.source[key],found.source[key]),'Retained manifest differs from original immutable source: '+key);
    need(manifest.runtime.installed?.version===2&&manifest.runtime.installed.python?.parser,
      'Version 2 original installed parser evidence required; legacy aggregate evidence requires a full build');
    const originalRoot=path.join(scratch,'original');
    execFileSync('python3',[...pythonArgs,archive,manifestFile,originalRoot,found.origin.artifact_digest],{stdio:'pipe',maxBuffer:1048576});
    const original=await authenticateOriginalPackageOutput({api,repo,origin:found.origin,root:originalRoot,manifestRaw});
    const installed=installedPackageIdentity(root,declaredPackagePythonRoots(root),{expectedParser:manifest.runtime.installed.python.parser,expectedExecutable:manifest.runtime.installed.python.executable_sha256});
    const differences=installedPackageDifferences(manifest.runtime.installed,installed);
    const recordAndRequireRuntime=()=>{
      fs.writeFileSync(path.join(root,'.cache/package-runtime-comparison.json'),JSON.stringify({version:2,
        original_manifest_sha256:hash(manifestRaw),current:installed,differences})+'\n',{flag:'wx'});
      need(differences.length===0,'Original runtime incompatibility: '+JSON.stringify(differences.map(row=>
        ({component:row.component,...(row.changed_components?{changed_components:row.changed_components}:{}),...(row.changed_files?{changed_files:row.changed_files.slice(0,10),changed_file_count:row.changed_files.length}: {})}))));
    };
    if(differences.length)recordAndRequireRuntime();
    // Actual scientific imports run only after original custody and complete
    // installed-byte admission, with the same no-site startup as measurement.
    const runtime=inspectPackageRuntime(root);
    if(runtime.errors.length){differences.push({component:'runtime.preflight',errors:runtime.errors});recordAndRequireRuntime();}
    const actualRuntime={node:process.version,platform:process.platform,arch:process.arch,
      versions:process.versions,dependencies:runtime.package_lock_sha256,
      python:{version:runtime.python.version,imports:runtime.python.imports}};
    for(const [component,value] of Object.entries(actualRuntime))if(!same(manifest.runtime[component],value))
      differences.push({component:'runtime.'+component,original:manifest.runtime[component],current:value});
    if(!same(manifest.configuration,packageBuildConfiguration()))differences.push({component:'configuration',
      original:manifest.configuration,current:packageBuildConfiguration()});
    recordAndRequireRuntime();
    const stage=path.join(scratch,'assembly');fs.mkdirSync(stage);
    for(const name of ['.github/package-inputs.json','data/ownership-selection.json']){
      fs.mkdirSync(path.dirname(path.join(stage,name)),{recursive:true});fs.copyFileSync(path.join(root,name),path.join(stage,name),fs.constants.COPYFILE_EXCL);
    }
    const atlasPath=path.join(originalRoot,'dist/client/atlas-geography.json');
    const atlasPin=manifest.output.files.find(pin=>pin.path==='dist/client/atlas-geography.json');
    // Atlas is an actual emitted asset, not an 8 MiB control receipt. Charge its
    // authenticated whole bytes to the same current scientific allowance; the
    // private execution frame then accounts for the parsed graph and checks RSS.
    need(atlasPin&&fs.statSync(atlasPath).size===atlasPin.bytes,'Authenticated whole atlas size differs');
    admitAssemblyAtlasMetadata(atlasPin.bytes);
    const atlas=JSON.parse(fs.readFileSync(atlasPath));need(atlas.additiveRelease?.base_reference,'Original additive base descriptor missing');
    const execution=issuePackageAssemblyExecution({original,source:root,stage,executingRoot:root,
      inheritedMetadata:[current,found.source,manifest,atlas,{runtime,...(proofReadback?{proofReadback}:{})}]});
    const publication=await preparePackageSelectedAdditive({root:stage,originalPackage:original,assemblyExecution:execution,
      selectedGrid:{sha256:current.selection.sha256},geographicRelease:atlas.additiveRelease.base_reference});
    need(publication,'Genuine current additive publication required');
    const consumed=packageSelectedPublicationInventory(publication,{root:stage});
    const transition=admitPackageOutputTransition(manifest,current,consumed.map(row=>row.path));
    const oldAssets=['base_manifest','ledger','owner_roster','patch'].map(role=>atlas.additiveRelease[role]);
    need(oldAssets.every(pin=>/^additive-repairs\/[A-Za-z0-9_.-]+$/.test(pin?.path??''))&&new Set(oldAssets.map(pin=>pin.path)).size===4,'Original four public additive assets required');
    for(const pin of oldAssets)need(same(streamedPackageFile(originalRoot,'dist/client/'+pin.path),{path:'dist/client/'+pin.path,bytes:pin.bytes,sha256:pin.sha256}),'Original additive output differs');
    const mutable=new Set(oldAssets.map(pin=>'dist/client/'+pin.path));mutable.add('dist/client/atlas-geography.json');
    for(const role of ['base_manifest','ledger','owner_roster','patch']){
      const name='dist/client/'+publication.additiveRelease[role].path;
      need(!manifest.output.files.some(pin=>pin.path===name&&!mutable.has(name)),'New additive asset collides with invariant output');
    }
    atlas.reference_release=publication.reference_release;atlas.additiveRelease=publication.additiveRelease;
    const atlasRaw=Buffer.from(JSON.stringify(atlas));
    admitDisk(atlasRaw.length+['base_manifest','ledger','owner_roster','patch'].reduce((sum,role)=>sum+publication.additiveRelease[role].bytes,0)+6*4096,
      'the actual current additive assets and atlas');
    fs.renameSync(path.join(originalRoot,'dist/client'),path.join(stage,'dist'));
    for(const pin of oldAssets)fs.unlinkSync(path.join(stage,'dist',pin.path));
    publishPackageSelectedAdditive(publication,{root:stage});
    fs.writeFileSync(path.join(stage,'dist/atlas-geography.json'),atlasRaw);
    fs.renameSync(path.join(stage,'dist'),path.join(stage,'client'));
    fs.mkdirSync(path.join(stage,'dist'));fs.renameSync(path.join(stage,'client'),path.join(stage,'dist/client'));
    fs.renameSync(path.join(originalRoot,'dist/cloudflare'),path.join(stage,'dist/cloudflare'));
    for(const pin of manifest.output.files)if(!mutable.has(pin.path))need(same(streamedPackageFile(stage,pin.path),pin),'Invariant output changed during assembly');
    requirePackageAssemblyExecution(execution);
    const assembly={kind:'retained-original-output-plus-current-additive',origin:found.origin,
      original_manifest_sha256:hash(manifestRaw),runtime_identity_version:2,transition,current_execution:execution,
      original_base_context_retained:true,base_restoration_invoked:false,invariant_build_invoked:false,
      base_tests_reused:['test/canonical-compact-repack.test.mjs','test/prepared-parity.test.mjs'],
      current_selected_inputs:consumed,elapsed_seconds:(performance.now()-started)/1000};
    const receipt={version:1,kind:'cloudflare',input_definition_sha256:current.input_definition_sha256,assembly,
      preflight:{passed:true,errors:[],inputs:{head:current.head},runtime,
        limitation:'Current assembly code, dependency and selected-source admission; original invariant build is reused, not reexecuted.'}};
    const receiptRaw=Buffer.from(JSON.stringify(receipt,null,2)+'\n');
    const receiptTarget=path.join(root,'.cache/package-input-build.json'),stagedReceipt=path.join(scratch,'receipt.json');
    admitDisk(receiptRaw.length+4096,'the actual assembly receipt');
    fs.writeFileSync(stagedReceipt,receiptRaw,{flag:'wx'});
    const target=path.join(root,'dist'),backup=path.join(scratch,'previous-dist'),oldReceipt=path.join(scratch,'previous-receipt');
    const existed=fs.existsSync(target),receiptExisted=fs.existsSync(receiptTarget);
    let outputPublished=false,receiptPublished=false,outputSaved=false,receiptSaved=false;
    try{
      if(existed){fs.renameSync(target,backup);outputSaved=true;}
      if(receiptExisted){fs.renameSync(receiptTarget,oldReceipt);receiptSaved=true;}
      fs.renameSync(path.join(stage,'dist'),target);outputPublished=true;
      fs.renameSync(stagedReceipt,receiptTarget);receiptPublished=true;
    }catch(error){
      try{
        if(receiptPublished)fs.renameSync(receiptTarget,stagedReceipt);
        if(outputPublished)fs.renameSync(target,path.join(stage,'dist'));
        if(receiptSaved)fs.renameSync(oldReceipt,receiptTarget);
        if(outputSaved)fs.renameSync(backup,target);
      }catch(rollback){preserveScratch=true;throw new AggregateError([error,rollback],'Output rollback requires preserved scratch recovery');}
      throw error;
    }
    committed=true;
    let proof;
    if(proofReadback){
      need(!same(manifest.source.selection.additive_release,current.selection.additive_release)&&
        oldAssets.some((pin,index)=>pin.sha256!==publication.additiveRelease[['base_manifest','ledger','owner_roster','patch'][index]].sha256),
        'Changed-selection proof requires genuinely different selected output');
      // Import only the two original source metadata blobs needed by the
      // comparison, using ordinary filtered Git acquisition, not a base checkout.
      try{git(['cat-file','-e',manifest.source.head+'^{commit}']);}
      catch{git(['fetch','--quiet','--depth=1','--filter=blob:none','--no-tags','--no-write-fetch-head','origin',manifest.source.head]);}
      for(const name of ['.github/package-inputs.json','data/ownership-selection.json'])
        execFileSync('git',['-C',root,'show',manifest.source.head+':'+name],{stdio:'pipe',maxBuffer:8*1048576,
          env:{...process.env,GIT_NO_LAZY_FETCH:'0',GIT_TERMINAL_PROMPT:'0',GIT_NO_REPLACE_OBJECTS:'1'}});
      const {compareSelectedPackageReadback}=await import('./compare-selected-package-output.mjs');
      proof={reference:proofReadback.origin,comparison:compareSelectedPackageReadback({assembled:root,readback:proofReadback.report,
        originalHead:manifest.source.head,currentHead:current.head,sourceRoot:root,originalManifest:manifestFile})};
      fs.writeFileSync(path.join(root,'.cache/selected-package-proof.json'),JSON.stringify(proof,null,2)+'\n',{flag:'wx'});
    }
    return {assembled:true,receipt_sha256:hash(receiptRaw),origin:found.origin,...(proof?{proof}:{}),elapsed_seconds:assembly.elapsed_seconds,
      reused_output_files:manifest.output.files.length-mutable.size,current_additive_assets:4};
  }finally{
    if(!preserveScratch)try{await fsp.rm(scratch,{recursive:true,force:true});}
    catch(error){if(!committed)throw error;console.warn('Committed selected output is valid; temporary output cleanup remains pending');}
  }
}

if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  let result;
  try{
    need(process.argv.length===2&&process.env.GH_TOKEN&&process.env.GITHUB_REPOSITORY&&process.env.GITHUB_EVENT_PATH,'Trusted selected-data CI invocation required');
    const event=JSON.parse(fs.readFileSync(process.env.GITHUB_EVENT_PATH,'utf8'));
    const api=githubAPI(process.env.GH_TOKEN,{conditionalReads:false});delete process.env.GH_TOKEN;delete process.env.GITHUB_TOKEN;
    const proofMode=process.env.GITHUB_EVENT_NAME==='workflow_dispatch'&&process.env.GITHUB_WORKFLOW==='Selected package equivalence proof';
    let proofReadback,originalRunId;
    const expectedHead=proofMode?event.inputs?.source_head:event.pull_request?.head?.sha;
    if(proofMode){
      need(/^[a-f0-9]{40}$/.test(expectedHead??''),'Exact proof source head required');
      for(const key of ['original_run_id','readback_run_id','readback_attempt'])need(/^[1-9]\d*$/.test(event.inputs?.[key]??''),'Exact proof run identity required');
      originalRunId=Number(event.inputs.original_run_id);
      proofReadback=await loadSelectedPackageReadback({api,repo:process.env.GITHUB_REPOSITORY,
        runId:Number(event.inputs.readback_run_id),attempt:Number(event.inputs.readback_attempt),expectedHead});
    }
    result=await assembleSelectedPackage({api,repo:process.env.GITHUB_REPOSITORY,expectedHead,originalRunId,proofReadback});
    if(proofMode)need(result.assembled&&result.proof,'Actual proof assembly required; fallback cannot establish equivalence');
  }catch(error){if(process.env.GITHUB_EVENT_NAME==='workflow_dispatch')process.exitCode=1;result={assembled:false,reason:String(error.message).replace(/https?:\/\/\S+/g,'[delivery address]').slice(0,600)};}
  console.log(JSON.stringify(result));
  if(process.env.GITHUB_OUTPUT)fs.appendFileSync(process.env.GITHUB_OUTPUT,`assembled=${result.assembled}\nassembly_sha256=${result.receipt_sha256??''}\n`);
}
