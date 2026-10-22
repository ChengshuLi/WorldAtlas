// Executed only after trusted selected-data classification proves this complete
// programme is unchanged from the PR base. API credentials stay in trusted code;
// subprocesses and current-product consumption receive no token environment.
import fs from 'node:fs';
import fsp from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {isDeepStrictEqual} from 'node:util';
import {execFileSync} from 'node:child_process';
import {gunzipSync} from 'node:zlib';
import {footprintHash} from './check-prepared.mjs';
import {originalNativeReference,validateReferenceMetadataHeader} from '../src/reference-metadata.js';
import {githubAPI, githubPages} from './issue-claim-contract.mjs';
import {loadPackageInputs, readPackageInputs, containsPackagePath, safePackagePath, PREPARED_STARTUP_INDEX} from './package-inputs.mjs';
import {compatiblePackageProducers,requireProducerInstallation} from './package-producer-contract.mjs';
import {assertCloudflareStaticAssets, inspectPackageNodeRuntime, verifyPackageDependencies} from './package-build.mjs';
import {committedPackageInputs, committedPackageProducer, PACKAGE_PRODUCER_WORKFLOWS, PACKAGE_PRODUCER_KIND, packageBuildConfiguration,
  validatePackageOutputManifest, admitPackageInputTransition, admitPackageOutputTransition, inertSelectedPackageInput, streamedPackageFile, resolvePackagePythonExecutable} from './package-output-artifact.mjs';
import {authenticateOriginalPackageOutput, readOriginalPackageInventory, requireOriginalPackageOutput, issuePackageAssemblyExecution, requirePackageAssemblyExecution}
  from '../coordination/engineering/additive-native-activation-20261009/package-selected-additive.mjs';

const need=(ok,message)=>{if(!ok)throw Error(message);};
const hash=raw=>createHash('sha256').update(raw).digest('hex');
const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const git=args=>execFileSync('git',['-C',root,...args],{encoding:'utf8',maxBuffer:Infinity,
  env:{...process.env,GIT_NO_LAZY_FETCH:'1',GIT_TERMINAL_PROMPT:'0'}}).trim();
const ordered=rows=>rows.sort((a,b)=>a.path.localeCompare(b.path,'en'));
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

// Source authenticity needs the complete declared input closure, not unrelated
// repository history. Only declared directories use recursive tree requests;
// exact leaves and workflow paths use ordinary authenticated ancestor trees.
function packageMetadata(api,repo){
  const commits=new Map(),trees=new Map();
  const oid=value=>/^[a-f0-9]{40}$/.test(value??'');
  const commit=async head=>{
    need(oid(head),'Exact package metadata commit required');
    if(!commits.has(head)){
      const object=await api(`/repos/${repo}/git/commits/${head}`);
      need(object.sha===head&&oid(object.tree?.sha),'Package metadata commit differs');commits.set(head,object);
    }
    return commits.get(head);
  };
  const listing=async(sha,recursive=false)=>{
    need(oid(sha),'Exact package metadata tree required');
    const key=sha+(recursive?'?recursive=1':'');
    if(!trees.has(key)){
      const value=await api(`/repos/${repo}/git/trees/${key}`);
      need(value.sha===sha&&value.truncated===false&&Array.isArray(value.tree),'Incomplete or different package metadata tree');
      const entries=new Map();
      for(const row of value.tree){
        need(typeof row.path==='string'&&!row.path.includes('\0')
          &&row.path.split('/').every(part=>part&&part!=='.'&&part!=='..')&&(recursive||!row.path.includes('/'))
          &&oid(row.sha)&&!entries.has(row.path),'Invalid or duplicate package metadata path');
        entries.set(row.path,row);
      }
      trees.set(key,entries);
    }
    return trees.get(key);
  };
  const scope=async(head,paths)=>{
    const object=await commit(head),entries=new Map();
    for(const name of new Set(paths)){
      need(safePackagePath(name),'Safe package metadata scope required');
      const directory=name.endsWith('/'),parts=name.replace(/\/$/,'').split('/');
      let sha=object.tree.sha,row;
      for(let index=0;index<parts.length;index++){
        row=(await listing(sha)).get(parts[index]);if(!row)break;
        if(index<parts.length-1){need(row.type==='tree'&&row.mode==='040000','Ordinary package metadata ancestor required');sha=row.sha;}
      }
      if(!row)continue; // Exact absence is part of optional-input admission.
      const prefix=parts.join('/');
      if(directory){
        need(row.type==='tree'&&row.mode==='040000','Declared package input directory differs');
        for(const [relative,child]of await listing(row.sha,true))entries.set(prefix+'/'+relative,{...child,path:prefix+'/'+relative});
      }else entries.set(prefix,{...row,path:prefix});
    }
    return {object,entries};
  };
  return {commit,scope};
}
const acceptedMetadataPaths=current=>current.definition.inputs.filter(name=>!name.endsWith('/')&&!inertSelectedPackageInput(name));

async function blobRaw(api,repo,tree,name){
  const row=tree.entries.get(name);need(row?.type==='blob'&&row.mode==='100644','Bounded ordinary original metadata required');
  const blob=await api(`/repos/${repo}/git/blobs/${row.sha}`);need(blob.encoding==='base64','Original metadata body unavailable');
  const raw=Buffer.from(blob.content,'base64');need(raw.length===row.size&&createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex')===row.sha,'Original metadata Git identity differs');
  return raw;
}
async function blobJSON(api,repo,tree,name){ return JSON.parse(await blobRaw(api,repo,tree,name)); }
function sourceCompatible(before,current,priorSidecarRaw,producerWorkflows,preparedStartup){
  try{admitPackageInputTransition(before,current,{acceptedInputs:current.accepted_selected_inputs,priorSidecarRaw,producerWorkflows,preparedStartup,preliminary:true});return true;}
  catch{return false;}
}

// This is the bootstrap's actual trusted PR/combined-candidate base, not the
// originating package head. Read only tree metadata for explicit retained leaves;
// the current-product consumer records their actual whole-body consumption.
function acceptedInputsFromTree(base,tree,current){
  const files=[];
  for(const name of current.definition.inputs){
    if(name.endsWith('/')||inertSelectedPackageInput(name))continue;
    const row=tree.entries.get(name);
    if(row?.type==='blob'&&row.mode==='100644'&&/^[a-f0-9]{40}$/.test(row.sha??'')&&
      Number.isSafeInteger(row.size)&&row.size>=0)
      files.push({path:name,mode:row.mode,oid:row.sha,bytes:row.size});
  }
  return {commit:base,files};
}
export async function acceptedSelectedPackageInputs({api,repo,base,current}){
  need(/^[a-f0-9]{40}$/.test(base??''),'Exact trusted selected base required');
  const tree=await packageMetadata(api,repo).scope(base,acceptedMetadataPaths(current));
  need(tree.object.sha===base,'Trusted selected base commit differs');
  return acceptedInputsFromTree(base,tree,current);
}

export async function findOriginalPackage({api,repo,current,originalRunId,trustedBase}){
  // A small recent-result search is an optimization. Exhaustion means a full
  // build, never a claim that no older result exists.
  need(originalRunId===undefined||Number.isSafeInteger(originalRunId)&&originalRunId>0,'Exact optional original run required');
  const metadata=packageMetadata(api,repo);
  let trustedCommit,acceptedInputs=trustedBase===undefined?current.accepted_selected_inputs:undefined;
  if(trustedBase!==undefined){
    need(/^[a-f0-9]{40}$/.test(trustedBase),'Exact trusted selected base required');
    trustedCommit=await metadata.commit(trustedBase);
    need(trustedCommit.sha===trustedBase&&/^[a-f0-9]{40}$/.test(trustedCommit.tree?.sha??''),'Trusted selected base commit differs');
  }
  const workflows=current.producer?.workflows?.map(row=>row.path);
  need(same(workflows,PACKAGE_PRODUCER_WORKFLOWS)||same(workflows,[PACKAGE_PRODUCER_WORKFLOWS[1]]),
    'Complete current package producer workflows required');
  const responses=originalRunId===undefined?await Promise.all(workflows.map(workflow=>
    api(`/repos/${repo}/actions/workflows/${path.posix.basename(workflow)}/runs?event=${workflow===PACKAGE_PRODUCER_WORKFLOWS[0]?'pull_request':'workflow_dispatch'}&per_page=20&page=1`)
  )):[{workflow_runs:[await api(`/repos/${repo}/actions/runs/${originalRunId}`)]}];
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
          // Check the small producer contract before requesting a whole declared
          // source closure for an incompatible original.
          const producerTree=await metadata.scope(origin.head,PACKAGE_PRODUCER_WORKFLOWS);
          const producer={kind:PACKAGE_PRODUCER_KIND,workflows:treeRows(producerTree)};
          const workflowTree=origin.head===receipt.executed_workflow.sha?producerTree:await metadata.scope(receipt.executed_workflow.sha,[receipt.workflow_path]);
          const actual=workflowTree.entries.get(receipt.workflow_path),captured=producer.workflows.find(row=>row.path===receipt.workflow_path);
          if(actual?.type!=='blob'||actual.mode!=='100644'||!same(captured,{path:receipt.workflow_path,mode:actual.mode,oid:actual.sha}))continue;
          let producerWorkflows;
          if(!same(producer,current.producer)){
            producerWorkflows={original:(await blobRaw(api,repo,producerTree,receipt.workflow_path)).toString('utf8'),
              current:(await blobRaw(api,repo,await metadata.scope(current.head,[receipt.workflow_path]),receipt.workflow_path)).toString('utf8')};
            compatiblePackageProducers(producer,current.producer,producerWorkflows);
            requireProducerInstallation(receipt.producer_job);
          }
          const definition=await readPackageInputs({route:`/repos/${repo}`,base:origin.head,api});
          const tree=await metadata.scope(origin.head,[...definition.inputs,...PACKAGE_PRODUCER_WORKFLOWS,'data/ownership-selection.json']),all=treeRows(tree);
          const source={head:origin.head,tree:tree.object.tree.sha,definition,producer,
            files:all.filter(row=>containsPackagePath(definition.inputs,row.path)),
            selection:await blobJSON(api,repo,tree,'data/ownership-selection.json')};
          if(trustedCommit&&!acceptedInputs){
            need(tree.object.sha===origin.head&&/^[a-f0-9]{40}$/.test(tree.object.tree?.sha??''),'Original source commit differs');
            // Reuse exact ancestor listings by tree OID, including across
            // distinct commits. New current leaves are resolved independently.
            acceptedInputs=acceptedInputsFromTree(trustedBase,
              await metadata.scope(trustedBase,acceptedMetadataPaths(current)),current);
          }
          const priorSidecarRaw=source.definition.inputs.some(name=>!current.definition.inputs.includes(name))
            ?await blobRaw(api,repo,await metadata.scope(origin.head,[source.selection.additive_release?.path]),source.selection.additive_release.path):undefined;
          let preparedStartup;
          if(source.files.some(row=>row.path===PREPARED_STARTUP_INDEX)&&current.files.some(row=>row.path===PREPARED_STARTUP_INDEX)){
            const nextTree=await metadata.scope(current.head,[PREPARED_STARTUP_INDEX,'data/ownership-selection.json']);
            preparedStartup={beforeIndex:await blobRaw(api,repo,tree,PREPARED_STARTUP_INDEX),
              afterIndex:await blobRaw(api,repo,nextTree,PREPARED_STARTUP_INDEX),
              beforeSelection:await blobRaw(api,repo,tree,'data/ownership-selection.json'),
              afterSelection:await blobRaw(api,repo,nextTree,'data/ownership-selection.json')};
          }
          if(!sourceCompatible(source,{...current,accepted_selected_inputs:acceptedInputs},priorSidecarRaw,producerWorkflows,preparedStartup))continue;
          return {source,origin,receipt,priorSidecarRaw,...(preparedStartup?{preparedStartup}:{}),...(producerWorkflows?{producerWorkflows}:{}),
            ...(trustedCommit?{accepted_selected_inputs:acceptedInputs}:{})};
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

// Reuse the independently authenticated emitted base, including actual geometry.
// The current ledger cannot supply its own supposedly independent target shape.
export function readOriginalPackageGeography(original,{sourceRoot}={}) {
  const {root:originalRoot,manifest}=requireOriginalPackageOutput(original);
  const output=new Map(manifest.output.files.map(pin=>[pin.path,pin]));
  const read=name=>{
    const pin=output.get(name);need(pin,'Original geography is absent from authenticated output');
    const raw=fs.readFileSync(path.join(originalRoot,name));
    need(raw.length===pin.bytes&&hash(raw)===pin.sha256,'Original geography output differs');return raw;
  };
  const atlas=JSON.parse(read('dist/client/atlas-geography.json'));
  need(atlas.additiveRelease?.base_reference,'Original additive base descriptor missing');
  const asset=pin=>{
    need(/^additive-repairs\/[A-Za-z0-9_.-]+$/.test(pin?.path??''),'Original additive asset path differs');
    const name='dist/client/'+pin.path;
    need(same(output.get(name),{path:name,bytes:pin.bytes,sha256:pin.sha256}),'Original additive asset pin differs');
    return read(name);
  };
  let selectedGrid;
  if(atlas.preparedOwnership!==undefined){
    need(atlas.preparedOwnership.version===2&&sourceRoot,'Original corrected bank requires its unchanged source native manifest');
    const name=manifest.source.selection.manifest_path,originalPin=manifest.source.files.find(pin=>pin.path===name);
    need(safePackagePath(name)&&originalPin?.mode==='100644','Original native source pin missing');
    const file=path.join(sourceRoot,name),raw=fs.readFileSync(file);
    need(fs.lstatSync(file).isFile()&&fs.realpathSync(file)===file&&createHash('sha1').update('blob '+raw.length+'\0').update(raw).digest('hex')===originalPin.oid
      &&hash(raw)===manifest.source.selection.sha256&&hash(raw)===atlas.preparedOwnership.native_manifest_sha256,'Original native source body differs');
    selectedGrid={sha256:hash(raw),manifest:JSON.parse(raw)};
  }else selectedGrid={sha256:atlas.additiveRelease.base_manifest.sha256,
    manifest:JSON.parse(asset(atlas.additiveRelease.base_manifest)),bounds:asset(atlas.additiveRelease.owner_roster)};
  const parts=(names,kind)=>{
    need(Array.isArray(names)&&names.length>0&&new Set(names).size===names.length,'Complete distinct original '+kind+' parts required');
    return names.flatMap(name=>{
      need(typeof name==='string'&&name.startsWith('geography/'+kind+'-')&&/^geography\/(?:catalog|part)-[0-9]+\.json\.gz$/.test(name),'Original geography part path differs');
      const rows=JSON.parse(gunzipSync(read('dist/client/'+name)));
      need(Array.isArray(rows)&&rows.length>0,'Nonempty original geography part required');return rows;
    });
  };
  const catalog=parts(atlas.parts,'catalog'),geometries=new Map();
  for(const row of parts(atlas.geometryParts,'part')){
    need(typeof row.id==='string'&&!geometries.has(row.id)&&row.geometry,'Duplicate or missing original geometry');
    geometries.set(row.id,row.geometry);
  }
  const ids=new Set(),features=catalog.map(feature=>{
    need(typeof feature.id==='string'&&!ids.has(feature.id)&&feature.geometry===null&&geometries.has(feature.id),'Original geography identity join differs');
    ids.add(feature.id);return {...feature,geometry:geometries.get(feature.id)};
  });
  const geographicRelease=atlas.additiveRelease.base_reference;
  need(ids.size===geometries.size&&footprintHash(features)===geographicRelease.footprints_sha256,'Original complete base geometry differs');
  let referenceRevision;
  if(manifest.source.selection?.reference_projection!==undefined||atlas.referenceMetadata!==undefined){
    const metadata=atlas.referenceMetadata;
    need(metadata,'Original reference metadata descriptor missing');
    const name='dist/client/reference-metadata/current.json',raw=read(name),pin=manifest.source.selection?.reference_projection;
    need(pin&&raw.length===pin.bytes&&hash(raw)===pin.sha256&&
      isDeepStrictEqual(metadata.asset,{path:'reference-metadata/current.json',bytes:raw.length,sha256:hash(raw)}),
    'Original reference metadata source/output identity differs');
    const projection=validateReferenceMetadataHeader(JSON.parse(raw),{selection:manifest.source.selection,manifest:selectedGrid.manifest});
    need(isDeepStrictEqual(projection.native,originalNativeReference(atlas.preparedOwnership?.native_pixel_map??atlas.pixelMap))&&isDeepStrictEqual(projection.native,metadata.native_reference)&&
      isDeepStrictEqual(projection.reference,metadata.reference)&&isDeepStrictEqual(projection.reference,geographicRelease),
      'Original reference metadata application differs');
    referenceRevision=metadata.application_reference_revision;
    need(/^[a-f0-9]{64}$/.test(referenceRevision??''),'Original application reference revision required');
  }
  return {atlas,selectedGrid,geographicRelease,features,...(referenceRevision===undefined?{}:{referenceRevision})};
}

export async function assembleSelectedPackage({api,repo,expectedHead,originalRunId,trustedBase}){
  const started=performance.now(),current=currentSource();need(current.head===expectedHead,'Actual selected head changed');
  const found=await findOriginalPackage({api,repo,current,originalRunId,trustedBase});if(!found)return {assembled:false,reason:'No applicable retained original output in bounded recent-result search'};
  if(trustedBase!==undefined)current.accepted_selected_inputs=found.accepted_selected_inputs;
  await verifyPackageDependencies(path.join(root,'node_modules'));
  admitDisk(found.origin.artifact_bytes,'the actual authenticated original archive');
  const scratch=await createPackageAssemblyScratch(root);
  let committed=false,preserveScratch=false;
  try{
    const archive=path.join(scratch,'original.zip'),originalRoot=path.join(scratch,'original');
    await downloadOriginal(api,repo,found.origin,archive);
    const extractorName='scripts/extract-package-output.py',extractorRaw=fs.readFileSync(path.join(root,extractorName));
    const extractor=streamedPackageFile(root,extractorName),extractorOid=createHash('sha1').update(`blob ${extractorRaw.length}\0`).update(extractorRaw).digest('hex');
    need(git(['ls-tree','HEAD','--',extractorName])===`100644 blob ${extractorOid}\t${extractorName}`&&hash(extractorRaw)===extractor.sha256,'Executing package extractor differs from current source');
    const python=resolvePackagePythonExecutable(),pythonArgs=['-I','-S','-B',path.join(root,extractorName)];
    // Authenticate and consume the archive once through the extractor's held descriptor.
    execFileSync(python.executable,[...pythonArgs,archive,originalRoot,found.origin.artifact_digest,found.receipt.package_output_manifest_sha256,String(found.receipt.package_output_manifest_bytes)],{stdio:'pipe',maxBuffer:1048576});
    need(same(streamedPackageFile(root,extractorName),extractor)&&same(resolvePackagePythonExecutable(python.sha256),python),'Package extraction execution changed');
    const manifestRaw=fs.readFileSync(path.join(originalRoot,'.cache/package-output-manifest.json')),manifest=validatePackageOutputManifest(JSON.parse(manifestRaw));
    for(const key of ['head','tree','definition','files','producer','selection'])need(same(manifest.source[key],found.source[key]),'Retained manifest differs from original immutable source: '+key);
    const original=await authenticateOriginalPackageOutput({api,repo,origin:found.origin,root:originalRoot,manifestRaw});
    // Admit the current locked installation for the computation we actually run.
    // Original runtime metadata stays in the retained artifact as history.
    const runtime=inspectPackageNodeRuntime(root);
    need(runtime.errors.length===0,'Current package runtime admission failed: '+JSON.stringify(runtime.errors));
    need(same(manifest.configuration,packageBuildConfiguration()),'Original build configuration differs');
    const stage=path.join(scratch,'assembly');fs.mkdirSync(stage);
    const execution=issuePackageAssemblyExecution({original,source:root,stage,executingRoot:root,
      acceptedInputs:current.accepted_selected_inputs,priorSidecarRaw:found.priorSidecarRaw,producerWorkflows:found.producerWorkflows,preparedStartup:found.preparedStartup});
    const {atlas,selectedGrid,geographicRelease,features,referenceRevision}=readOriginalPackageGeography(original,{sourceRoot:root});
    // The authenticated execution closure includes this literal deferred import.
    // Current locked dependencies are admitted above; no dependency sees API credentials.
    need(!process.env.GH_TOKEN&&!process.env.GITHUB_TOKEN,'Current additive consumption must be credential-free');
    const {readCurrentSelectedAdditive}=await import('./package-current-additive.mjs');
    const {packagePreparedStartupOwnership}=await import('./package-startup-ownership.mjs');
    const publication=await readCurrentSelectedAdditive({root,selectedGrid,geographicRelease,referenceRevision});
    need(publication&&same(publication.selection,current.selection),'Genuine same-source current additive publication required');
    need(isDeepStrictEqual(publication.referenceMetadata,atlas.referenceMetadata),'Current reference metadata differs from retained output');
    need(atlas.preparedOwnership?.version===2,'Corrected-bank reuse requires a matching full-capture producer');
    const bankPrefix='data/canonical-grid/current-startup/',preparedDirectory=path.join(scratch,'prepared');
    const prepared=await packagePreparedStartupOwnership({manifest:selectedGrid.manifest,manifestSha:selectedGrid.sha256,
      source:path.join(root,bankPrefix),destination:preparedDirectory,selected:publication,features});
    const consumed=[...publication.inputInventory,...prepared.input_inventory.map(pin=>({...pin,path:bankPrefix+pin.path}))].map(pin=>{
      const row=current.files.find(row=>row.path===pin.path);
      need(row&&row.mode===pin.mode&&row.oid===pin.git_blob_oid&&pin.whole_body_consumed===true,'Current prepared input differs from actual source');
      return {...pin,commit:current.head};
    });
    const transition=admitPackageOutputTransition(manifest,current,{acceptedInputs:current.accepted_selected_inputs,typedInputs:consumed,priorSidecarRaw:found.priorSidecarRaw,producerWorkflows:found.producerWorkflows,preparedStartup:found.preparedStartup});
    const originalNative=new Set([...JSON.parse(found.preparedStartup.beforeIndex).compatibility_files.map(pin=>pin.path),
      ...atlas.preparedOwnership.native_pixel_map.parts.map(pin=>pin.path),atlas.preparedOwnership.native_pixel_map.native_latitudes.transport_path]);
    const mutable=new Set([...atlas.pixelMap.parts,...atlas.preparedOwnership.context_parts]
      .filter(pin=>!originalNative.has(pin.path)).map(pin=>'dist/client/'+pin.path));
    mutable.add('dist/client/atlas-geography.json');
    const originalFiles=new Map(manifest.output.files.map(pin=>[pin.path,pin]));
    const newFiles=new Set(prepared.files.map(pin=>'dist/client/'+pin.path));
    for(const pin of prepared.files){
      const name='dist/client/'+pin.path,prior=originalFiles.get(name);
      need(!prior||same(prior,{path:name,bytes:pin.bytes,sha256:pin.sha256}),'Prepared immutable output URL would be rebound');
    }
    atlas.reference_release=publication.reference_release;atlas.additiveRelease=publication.additiveRelease;
    atlas.pixelMap=prepared.pixelMap;atlas.preparedOwnership=prepared.preparedOwnership;
    const atlasRaw=Buffer.from(JSON.stringify(atlas));
    admitDisk(atlasRaw.length+prepared.files.reduce((sum,pin)=>sum+pin.bytes,0)+6*4096,'the actual corrected bank and atlas');
    fs.renameSync(path.join(originalRoot,'dist/client'),path.join(stage,'dist'));
    for(const name of mutable)if(name!=='dist/client/atlas-geography.json'&&!newFiles.has(name))fs.unlinkSync(path.join(stage,'dist',name.slice('dist/client/'.length)));
    for(const pin of prepared.files)if(!originalFiles.has('dist/client/'+pin.path)){
      const file=path.join(stage,'dist',pin.path);fs.mkdirSync(path.dirname(file),{recursive:true});
      fs.copyFileSync(path.join(preparedDirectory,pin.path),file,fs.constants.COPYFILE_EXCL);
    }
    fs.writeFileSync(path.join(stage,'dist/atlas-geography.json'),atlasRaw);
    fs.renameSync(path.join(stage,'dist'),path.join(stage,'client'));
    fs.mkdirSync(path.join(stage,'dist'));fs.renameSync(path.join(stage,'client'),path.join(stage,'dist/client'));
    fs.renameSync(path.join(originalRoot,'dist/cloudflare'),path.join(stage,'dist/cloudflare'));
    for(const pin of manifest.output.files)if(!mutable.has(pin.path))need(same(streamedPackageFile(stage,pin.path),pin),'Invariant output changed during assembly');
    assertCloudflareStaticAssets(stage);
    requirePackageAssemblyExecution(execution);
    const assembly={kind:'retained-original-output-plus-current-additive',origin:found.origin,
      original_manifest_sha256:hash(manifestRaw),transition,current_execution:execution,
      original_base_context_retained:true,base_restoration_invoked:false,invariant_build_invoked:false,
      current_selected_inputs:consumed,elapsed_seconds:(performance.now()-started)/1000};
    const receipt={version:1,kind:'cloudflare',input_definition_sha256:current.input_definition_sha256,assembly,
      preflight:{passed:true,errors:[],inputs:{head:current.head},runtime:{...runtime,extractor:{python,source:extractor,startup:['-I','-S','-B']}},
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
    return {assembled:true,receipt_sha256:hash(receiptRaw),origin:found.origin,elapsed_seconds:assembly.elapsed_seconds,
      reused_output_files:manifest.output.files.length-mutable.size,current_prepared_assets:prepared.files.length};
  }finally{
    if(!preserveScratch)try{await fsp.rm(scratch,{recursive:true,force:true});}
    catch(error){if(!committed)throw error;console.warn('Committed selected output is valid; temporary output cleanup remains pending');}
  }
}

// Production assembly runs only inside the authenticated selected-data queue.
export function packageAssemblyInvocation(event, environment = process.env) {
  need(environment.GITHUB_EVENT_NAME==='workflow_dispatch'&&environment.GITHUB_WORKFLOW==='Serialize worker PR merges'&&
    environment.GITHUB_REF==='refs/heads/main','Trusted selected-data worker invocation required');
  need(environment.INTEGRATION_PROFILE==='full'&&environment.INTEGRATION_SHARD==='0'&&
    environment.INTEGRATION_TEST_SELECTION==='selected-data','Trusted selected-data worker integration (0) required');
  const expectedHead=environment.SELECTED_PACKAGE_CANDIDATE;
  need(/^[a-f0-9]{40}$/.test(expectedHead??''),'Exact selected package candidate required');
  const trustedBase=environment.SELECTED_PACKAGE_TRUSTED_BASE;
  need(trustedBase===undefined||/^[a-f0-9]{40}$/.test(trustedBase),'Exact trusted selected base required');
  return {expectedHead,...(trustedBase===undefined?{}:{trustedBase})};
}

export function packageAssemblyAPI(token,options={}){
  // Match the queue's existing non-merge read allowance. Shared transport owns
  // its unchanged transient status, attempt, timeout and denial policy.
  return githubAPI(token,{...options,conditionalReads:false,readWaitMs:8*60*1000});
}

if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  let result;
  try{
    need(process.argv.length===2&&process.env.GH_TOKEN&&process.env.GITHUB_REPOSITORY&&process.env.GITHUB_EVENT_PATH,'Trusted selected-data CI invocation required');
    const event=JSON.parse(fs.readFileSync(process.env.GITHUB_EVENT_PATH,'utf8'));
    const api=packageAssemblyAPI(process.env.GH_TOKEN);delete process.env.GH_TOKEN;delete process.env.GITHUB_TOKEN;
    const {expectedHead,trustedBase}=packageAssemblyInvocation(event);
    result=await assembleSelectedPackage({api,repo:process.env.GITHUB_REPOSITORY,expectedHead,trustedBase});
  }catch(error){result={assembled:false,reason:String(error.message).replace(/https?:\/\/\S+/g,'[delivery address]').slice(0,600)};}
  console.log(JSON.stringify(result));
  if(process.env.GITHUB_OUTPUT)fs.appendFileSync(process.env.GITHUB_OUTPUT,`assembled=${result.assembled}\nassembly_sha256=${result.receipt_sha256??''}\n`);
}
