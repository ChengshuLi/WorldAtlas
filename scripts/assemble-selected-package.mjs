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
import {githubAPI, githubPages} from './issue-claim-contract.mjs';
import {integrationTree} from './integration-profile.mjs';
import {loadPackageInputs, readPackageInputs, containsPackagePath} from './package-inputs.mjs';
import {inspectPackageRuntime, verifyPackageDependencies} from './package-build.mjs';
import {committedPackageInputs, committedPackageProducer, PACKAGE_PRODUCER_WORKFLOWS, PACKAGE_PRODUCER_KIND, packageBuildConfiguration,
  validatePackageOutputManifest, admitPackageInputTransition, admitPackageOutputTransition, inertSelectedPackageInput, streamedPackageFile, installedPackageIdentity, installedPackageDifferences, declaredPackagePythonRoots} from './package-output-artifact.mjs';
import {authenticateOriginalPackageOutput, readOriginalPackageInventory, issuePackageAssemblyExecution, preparePackageSelectedAdditive,
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
  try{admitPackageInputTransition(before,current,{acceptedInputs:current.accepted_selected_inputs,preliminary:true});return true;}
  catch{return false;}
}

// This is the bootstrap's actual trusted PR/combined-candidate base, not the
// originating package head. Read only tree metadata for explicit retained leaves;
// the existing private selected reader authenticates their typed consumption.
function acceptedInputsFromTree(base,tree,current){
  const files=[];
  for(const name of current.definition.inputs){
    if(name.endsWith('/')||inertSelectedPackageInput(name))continue;
    const row=tree.entries.get(name);
    if(row?.type==='blob'&&row.mode==='100644'&&/^[a-f0-9]{40}$/.test(row.sha??'')&&
      Number.isSafeInteger(row.size)&&row.size>=0&&row.size<=32*1048576)
      files.push({path:name,mode:row.mode,oid:row.sha,bytes:row.size});
  }
  return {commit:base,files};
}
export async function acceptedSelectedPackageInputs({api,repo,base,current}){
  need(/^[a-f0-9]{40}$/.test(base??''),'Exact trusted selected base required');
  const tree=await integrationTree(api,repo,base);
  need(tree.object.sha===base,'Trusted selected base commit differs');
  return acceptedInputsFromTree(base,tree,current);
}

export async function findOriginalPackage({api,repo,current,originalRunId,trustedBase}){
  // A small recent-result search is an optimization. Exhaustion means a full
  // build, never a claim that no older result exists.
  need(originalRunId===undefined||Number.isSafeInteger(originalRunId)&&originalRunId>0,'Exact optional original run required');
  let trustedCommit,acceptedInputs=trustedBase===undefined?current.accepted_selected_inputs:undefined;
  if(trustedBase!==undefined){
    need(/^[a-f0-9]{40}$/.test(trustedBase),'Exact trusted selected base required');
    trustedCommit=await api(`/repos/${repo}/git/commits/${trustedBase}`);
    need(trustedCommit.sha===trustedBase&&/^[a-f0-9]{40}$/.test(trustedCommit.tree?.sha??''),'Trusted selected base commit differs');
  }
  const responses=originalRunId===undefined?await Promise.all([
    api(`/repos/${repo}/actions/workflows/merge-integration-checks.yml/runs?event=pull_request&per_page=20&page=1`),
    api(`/repos/${repo}/actions/workflows/worker-merge.yml/runs?event=workflow_dispatch&per_page=20&page=1`)
  ]):[{workflow_runs:[await api(`/repos/${repo}/actions/runs/${originalRunId}`)]}];
  need(responses.every(response=>Array.isArray(response.workflow_runs)&&response.workflow_runs.length<=20),'Bounded original run discovery unavailable');
  const runs=responses.flatMap(response=>response.workflow_runs).sort((a,b)=>b.id-a.id||b.run_attempt-a.run_attempt);
  if(originalRunId!==undefined)need(runs.length===1&&runs[0]?.id===originalRunId,'Pinned original run identity differs');
  const seen=new Set();
  for(const run of runs){
    const identity=`${run.id}/${run.run_attempt}`;
    if(run.status!=='completed'||seen.has(identity)||run.repository?.full_name!==repo||run.head_repository?.full_name!==repo)continue;
    seen.add(identity);
    if(!(run.event==='pull_request'&&run.path==='.github/workflows/merge-integration-checks.yml'||
      run.event==='workflow_dispatch'&&run.path==='.github/workflows/worker-merge.yml'&&run.head_branch==='main'))continue;
    // A missing/obsolete original is a cache miss. A later run may contain a
    // compatible candidate even when both runs executed the same main workflow.
    try{
      const inventory=await api(`/repos/${repo}/actions/runs/${run.id}/artifacts?per_page=100&page=1`);
      if(!Array.isArray(inventory.artifacts)||inventory.total_count!==inventory.artifacts.length||inventory.artifacts.length>100)continue;
      // Failed-job reruns retain successful earlier producers. Artifact names
      // identify their actual attempts; each still needs its original job proof.
      const prefix=`cloudflare-package-output-${run.id}-`;
      const artifacts=inventory.artifacts.filter(row=>!row.expired&&row.name?.startsWith(prefix)&&
        /^[1-9]\d*$/.test(row.name.slice(prefix.length))&&Number(row.name.slice(prefix.length))<=run.run_attempt)
        .sort((a,b)=>Number(b.name.slice(prefix.length))-Number(a.name.slice(prefix.length)));
      for(const artifact of artifacts){
        const attempt=Number(artifact.name.slice(prefix.length));
        if(inventory.artifacts.filter(row=>row.name===artifact.name).length!==1)continue;
        try{
          const jobs=await githubPages(async route=>(await api(route)).jobs,
            `/repos/${repo}/actions/runs/${run.id}/attempts/${attempt}/jobs`);
          const candidates=jobs.filter(job=>job.status==='completed'&&job.conclusion==='success'&&
            job.steps?.some(step=>['Retain original full-regression package output','Retain original selected package output',
              'Retain original final-worker package output'].includes(step.name)&&step.conclusion==='success'));
          if(candidates.length!==1)continue;
          if(!/^sha256:[a-f0-9]{64}$/.test(artifact.digest??'')||!Number.isSafeInteger(artifact.size_in_bytes)||artifact.size_in_bytes<=0)continue;
          const origin={run_id:run.id,run_attempt:attempt,job_id:candidates[0].id,workflow_head:run.head_sha,
            artifact_id:artifact.id,artifact_name:artifact.name,artifact_digest:artifact.digest.slice(7),artifact_bytes:artifact.size_in_bytes};
          const receipt=await readOriginalPackageInventory({api,repo,origin});
          origin.head=receipt.original_head;
          const tree=await integrationTree(api,repo,origin.head),all=treeRows(tree);
          const producer={kind:PACKAGE_PRODUCER_KIND,workflows:all.filter(row=>PACKAGE_PRODUCER_WORKFLOWS.includes(row.path))};
          if(!same(producer,current.producer))continue;
          const workflowTree=origin.head===receipt.executed_workflow.sha?tree:await integrationTree(api,repo,receipt.executed_workflow.sha);
          const actual=workflowTree.entries.get(receipt.workflow_path),captured=producer.workflows.find(row=>row.path===receipt.workflow_path);
          if(actual?.type!=='blob'||actual.mode!=='100644'||!same(captured,{path:receipt.workflow_path,mode:actual.mode,oid:actual.sha}))continue;
          const definition=await readPackageInputs({route:`/repos/${repo}`,base:origin.head,api});
          const source={head:origin.head,tree:tree.object.tree.sha,definition,producer,
            files:all.filter(row=>containsPackagePath(definition.inputs,row.path)),
            selection:await blobJSON(api,repo,tree,'data/ownership-selection.json')};
          if(trustedCommit&&!acceptedInputs){
            need(tree.object.sha===origin.head&&/^[a-f0-9]{40}$/.test(tree.object.tree?.sha??''),'Original source commit differs');
            // Both commit identities came from this invocation's authenticated API.
            // Reuse only the already-read complete tree, never a caller-supplied map.
            acceptedInputs=tree.object.tree.sha===trustedCommit.tree.sha
              ?acceptedInputsFromTree(trustedBase,tree,current)
              :await acceptedSelectedPackageInputs({api,repo,base:trustedBase,current});
          }
          if(!sourceCompatible(source,{...current,accepted_selected_inputs:acceptedInputs}))continue;
          return {source,origin,receipt,...(trustedCommit?{accepted_selected_inputs:acceptedInputs}:{})};
        }catch(error){
          console.warn(`Skipped original package producer ${run.id}/${attempt}: ${String(error.message).replace(/https?:\/\/\S+/g,'[delivery address]').slice(0,300)}`);
        }
      }
    }catch(error){
      console.warn(`Skipped original package run ${identity}: ${String(error.message).replace(/https?:\/\/\S+/g,'[delivery address]').slice(0,300)}`);
    }
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
  const fd=fs.openSync(destination,'wx',0o600);let bytes=0;
  try{for await(const chunk of delivery.body){bytes+=chunk.length;need(bytes<=origin.artifact_bytes,'Original archive exceeds authenticated bytes');fs.writeSync(fd,chunk);}}
  finally{fs.closeSync(fd);}
  need(bytes===origin.artifact_bytes,'Original output archive length differs');
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
    files:committedPackageInputs(root,definition),producer:committedPackageProducer(root)};
}

function packageAssemblyPhaseMarker(started){
  let previous=started;
  return phase=>{
    const now=performance.now();
    console.error('[selected-package-phase] '+JSON.stringify({phase,
      phase_seconds:(now-previous)/1000,elapsed_seconds:(now-started)/1000}));
    previous=now;
  };
}

export async function assembleSelectedPackage({api,repo,expectedHead,originalRunId,trustedBase}){
  const started=performance.now(),completePhase=packageAssemblyPhaseMarker(started);
  const current=currentSource();need(current.head===expectedHead,'Actual selected head changed');
  completePhase('current-source');
  const found=await findOriginalPackage({api,repo,current,originalRunId,trustedBase});
  completePhase('original-discovery');
  if(!found)return {assembled:false,reason:'No applicable retained original output in bounded recent-result search'};
  if(trustedBase!==undefined)current.accepted_selected_inputs=found.accepted_selected_inputs;
  await verifyPackageDependencies(path.join(root,'node_modules'));
  admitDisk(found.origin.artifact_bytes,'the actual authenticated original archive');
  const scratch=await createPackageAssemblyScratch(root);
  completePhase('dependencies-and-scratch');
  let committed=false,preserveScratch=false;
  try{
    const archive=path.join(scratch,'original.zip'),originalRoot=path.join(scratch,'original');
    await downloadOriginal(api,repo,found.origin,archive);
    completePhase('archive-download');
    const pythonArgs=['-I','-S','-B',path.join(root,'scripts/extract-package-output.py')];
    // Authenticate and consume the archive once through the extractor's held descriptor.
    execFileSync('python3',[...pythonArgs,archive,originalRoot,found.origin.artifact_digest,found.receipt.package_output_manifest_sha256,String(found.receipt.package_output_manifest_bytes)],{stdio:'pipe',maxBuffer:1048576});
    completePhase('archive-extraction');
    const manifestRaw=fs.readFileSync(path.join(originalRoot,'.cache/package-output-manifest.json')),manifest=validatePackageOutputManifest(JSON.parse(manifestRaw));
    for(const key of ['head','tree','definition','files','producer','selection'])need(same(manifest.source[key],found.source[key]),'Retained manifest differs from original immutable source: '+key);
    need(manifest.runtime.installed?.version===2&&manifest.runtime.installed.python?.parser,
      'Version 2 original installed parser evidence required; legacy aggregate evidence requires a full build');
    const original=await authenticateOriginalPackageOutput({api,repo,origin:found.origin,root:originalRoot,manifestRaw});
    completePhase('original-output-authentication');
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
      inheritedMetadata:[current,found.source,manifest,atlas,{runtime}],acceptedInputs:current.accepted_selected_inputs});
    completePhase('runtime-and-source-loading');
    const publication=await preparePackageSelectedAdditive({root:stage,originalPackage:original,assemblyExecution:execution,
      selectedGrid:{sha256:current.selection.sha256},geographicRelease:atlas.additiveRelease.base_reference});
    need(publication,'Genuine current additive publication required');
    const consumed=packageSelectedPublicationInventory(publication,{root:stage});
    const transition=admitPackageOutputTransition(manifest,current,{acceptedInputs:current.accepted_selected_inputs,typedInputs:consumed});
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
    completePhase('additive-assembly');
    for(const pin of manifest.output.files)if(!mutable.has(pin.path))need(same(streamedPackageFile(stage,pin.path),pin),'Invariant output changed during assembly');
    requirePackageAssemblyExecution(execution);
    completePhase('final-checks');
    const assembly={kind:'retained-original-output-plus-current-additive',origin:found.origin,
      original_manifest_sha256:hash(manifestRaw),runtime_identity_version:2,transition,current_execution:execution,
      original_base_context_retained:true,base_restoration_invoked:false,invariant_build_invoked:false,
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
    completePhase('output-publication');
    return {assembled:true,receipt_sha256:hash(receiptRaw),origin:found.origin,elapsed_seconds:assembly.elapsed_seconds,
      reused_output_files:manifest.output.files.length-mutable.size,current_additive_assets:4};
  }finally{
    if(!preserveScratch)try{await fsp.rm(scratch,{recursive:true,force:true});}
    catch(error){if(!committed)throw error;console.warn('Committed selected output is valid; temporary output cleanup remains pending');}
  }
}

// Production assembly binds source and original output custody. Reference-run
// authentication and output equivalence belong to the independent observer.
export function packageAssemblyInvocation(event, environment = process.env) {
  const proofMode=environment.GITHUB_EVENT_NAME==='workflow_dispatch'&&environment.GITHUB_WORKFLOW==='Selected package equivalence proof';
  const workerMode=environment.GITHUB_EVENT_NAME==='workflow_dispatch'&&environment.GITHUB_WORKFLOW==='Serialize worker PR merges'&&
    environment.GITHUB_REF==='refs/heads/main';
  need(proofMode||workerMode||environment.GITHUB_EVENT_NAME==='pull_request','Trusted selected-data CI invocation required');
  if(workerMode)need(environment.INTEGRATION_PROFILE==='full'&&environment.INTEGRATION_SHARD==='0'&&
    environment.INTEGRATION_TEST_SELECTION==='selected-data','Trusted selected-data worker integration (0) required');
  const expectedHead=proofMode?event.inputs?.source_head:workerMode?environment.SELECTED_PACKAGE_CANDIDATE:event.pull_request?.head?.sha;
  need(/^[a-f0-9]{40}$/.test(expectedHead??''),proofMode?'Exact proof source head required':'Exact selected package candidate required');
  let originalRunId;
  if(proofMode){
    need(/^[1-9]\d*$/.test(event.inputs?.original_run_id??'')&&Number.isSafeInteger(Number(event.inputs.original_run_id)),
      'Exact original package run identity required');
    originalRunId=Number(event.inputs.original_run_id);
  }
  const trustedBase=environment.SELECTED_PACKAGE_TRUSTED_BASE;
  need(trustedBase===undefined||/^[a-f0-9]{40}$/.test(trustedBase),'Exact trusted selected base required');
  return {proofMode,expectedHead,originalRunId,...(trustedBase===undefined?{}:{trustedBase})};
}

if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  let result;
  try{
    need(process.argv.length===2&&process.env.GH_TOKEN&&process.env.GITHUB_REPOSITORY&&process.env.GITHUB_EVENT_PATH,'Trusted selected-data CI invocation required');
    const event=JSON.parse(fs.readFileSync(process.env.GITHUB_EVENT_PATH,'utf8'));
    const api=githubAPI(process.env.GH_TOKEN,{conditionalReads:false});delete process.env.GH_TOKEN;delete process.env.GITHUB_TOKEN;
    const {proofMode,expectedHead,originalRunId,trustedBase}=packageAssemblyInvocation(event);
    result=await assembleSelectedPackage({api,repo:process.env.GITHUB_REPOSITORY,expectedHead,originalRunId,trustedBase});
    if(proofMode)need(result.assembled,'Actual assembly required; fallback cannot establish equivalence');
  }catch(error){if(process.env.GITHUB_EVENT_NAME==='workflow_dispatch'&&process.env.GITHUB_WORKFLOW==='Selected package equivalence proof')process.exitCode=1;result={assembled:false,reason:String(error.message).replace(/https?:\/\/\S+/g,'[delivery address]').slice(0,600)};}
  console.log(JSON.stringify(result));
  if(process.env.GITHUB_OUTPUT)fs.appendFileSync(process.env.GITHUB_OUTPUT,`assembled=${result.assembled}\nassembly_sha256=${result.receipt_sha256??''}\n`);
}
