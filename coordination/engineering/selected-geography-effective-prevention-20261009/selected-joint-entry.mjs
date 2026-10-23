// One trusted Node invocation owns checkpoint authority and native comparison.
// Proposed commits are data, never imported code.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {gzipSync} from 'node:zlib';

const ROOT = fileURLToPath(new URL('../../../', import.meta.url));
const P = 'coordination/engineering/selected-geography-effective-prevention-20261009/';
export const JOINT_CODE = Object.freeze([
  'scripts/run-geographic-check.py', 'scripts/geography-prefetch.mjs', 'scripts/geography-routing-metadata.mjs',
  'scripts/package-startup-ownership.mjs','src/ownership-assets.js','src/ownership-method.js',
  'scripts/native-word-store.mjs','scripts/native-patch-store.mjs', 'scripts/check-effective-geographic-regression.mjs', 'scripts/selected-checkpoint-native.mjs',
  'src/native-grid.js', 'src/ownership-codec.js',
  P + 'selected-neighbor-prevention.mjs', P + 'selected-checkpoint.mjs', P + 'selected-joint-entry.mjs',
  'scripts/accepted-selected-checkpoint.mjs', 'scripts/check-handoff-scope.mjs',
  'scripts/evidence-policy.mjs', 'scripts/evidence-quality.mjs', 'scripts/geographic-report-artifact.mjs',
  'scripts/github-quota.mjs', 'scripts/github-snapshots.mjs', 'scripts/integration-proof.mjs',
  'scripts/issue-claim-contract.mjs', 'scripts/research-import-gate.mjs',
  'scripts/worker-result.mjs', 'src/regional-import-gate.js', 'scripts/geographic_checkpoint_products.py',
  'scripts/selected-reference-metadata.mjs', 'src/reference-metadata.js'
]);
const sha = body => createHash('sha256').update(body).digest('hex');
const demand = (ok, message) => { if (!ok) throw Error(message); };
const commit = value => typeof value === 'string' && /^[a-f0-9]{40}$/.test(value);
function ordinaryParents(target) {
  for (let p = path.dirname(target);; p = path.dirname(p)) {
    const stat = fs.lstatSync(p);
    demand(stat.isDirectory() && !stat.isSymbolicLink(), 'Nonordinary joint output/code ancestor');
    if (p === path.dirname(p)) break;
  }
}
function fresh(destination) {
  ordinaryParents(destination);
  try { fs.lstatSync(destination); } catch (error) { if (error.code === 'ENOENT') return; throw error; }
  throw Error('Joint output already exists');
}
// Transport hints are immutable candidate data, separate from scientific routes.
// The acceptance reader authenticates their contents; these descriptors never
// mint authority and stay explicit applicability/admission dependencies.
export function checkpointTransportInput(reader, name, {consume = true} = {}) {
  demand(typeof name === 'string' && !path.posix.isAbsolute(name) && !name.includes('\\')
    && !name.includes('\0') && name.split('/').every(p => p && p !== '.' && p !== '..'),
  'Unsafe checkpoint transport path');
  const tree = reader.git('ls-tree', '-z', reader.version, '--', name).toString();
  if (!tree) return {pin:{commit:reader.version, path:name, present:false, whole_body_consumed:false}, body:null};
  demand(/^100644 blob [a-f0-9]{40}\t/.test(tree) && tree.endsWith('\t' + name + '\0'),
    'Checkpoint transport input is not an ordinary Git file');
  const key=reader.version+':'+name, previous=reader.inventory.get(key);
  try {
    const descriptor=reader.descriptor(name);
    const pin={...descriptor,present:true,whole_body_consumed:consume};
    if(!consume)return {pin,body:null};
    const body=reader.read(name);
    pin.sha256=sha(body);
    return {pin,body};
  } finally {
    // Keep transport hints in their separate explicit custody roster.
    if(!previous)reader.inventory.delete(key);
  }

}

function executionGuard(repo, trusted) {
  demand(commit(trusted) && fs.realpathSync(repo) === fs.realpathSync(ROOT), 'Joint entry requires its actual trusted checkout');
  demand(process.execArgv.length === 0
    && process.env.NODE_OPTIONS === undefined && process.env.NODE_PATH === undefined,
  'Joint entry requires its exact trusted runtime arguments');
  const git = (...args) => {
    const options={stdio:['ignore', 'pipe', 'pipe'],maxBuffer:Infinity};
    if(args[0]==='cat-file'&&args[1]==='blob') options.maxBuffer=Number(git('cat-file','-s',args[2]))+1;
    return execFileSync('git', ['-c', 'core.hooksPath=/dev/null', '-C', repo, ...args],options);
  };
  demand(git('rev-parse', 'HEAD').toString().trim() === trusted, 'Joint executing commit differs from checkout');
  const files = JOINT_CODE.map(name => {
    const file = path.join(ROOT, name); ordinaryParents(file); const stat = fs.lstatSync(file);
    demand(stat.isFile() && !stat.isSymbolicLink(), 'Nonordinary joint execution code');
    return {name, file, stat};
  });
  return files.map(({name, file, stat}) => {
    const row = git('ls-tree', '-z', trusted, '--', name).toString();
    demand(/^100(644|755) blob [a-f0-9]{40}\t/.test(row) && row.endsWith('\t' + name + '\0'), 'Unbound joint code');
    const [mode,, oid] = row.slice(0, row.indexOf('\t')).split(' ');
    demand(Number(git('cat-file', '-s', oid)) === stat.size, 'Joint code size differs');
    const local = fs.readFileSync(file), body = git('cat-file', 'blob', oid);
    demand(local.equals(body) && (stat.mode & 0o777) === (mode === '100755' ? 0o755 : 0o644), 'Joint code body/mode differs');
    return {commit:trusted, path:name, mode, git_blob_oid:oid, bytes:body.length, sha256:sha(body)};
  });
}

async function withSelectedComparison({repo,baseline,candidate,startup,phaseComplete,publicAccepted=false,trusted,checkpointFetchImpl},consume) {
  const {compareSelectedCheckpointNative} = await import('../../../scripts/selected-checkpoint-native.mjs');
  const checkpoint = await import('./selected-checkpoint.mjs');
  const {valueBytes, valueSha} = await import('./selected-neighbor-prevention.mjs');
  const {beforeReader, afterReader} = startup;
  const {createAcquisition} = await import('../../../scripts/geography-prefetch.mjs');
  let declaredPin;
  const acquisition = createAcquisition({repo,
    // Complete pins already supply lengths. The existing acquisition compares
    // mode/OID with the local origin tree, without a remote tree or blob read.
    loadDescriptor:(_version,name) => {
      demand(name === declaredPin.path, 'Selected input acquisition path differs');
      return {type:'blob',mode:declaredPin.mode,sha:declaredPin.git_blob_oid,size:declaredPin.bytes};
    },
    execute:(_command,args,options) => execFileSync(beforeReader.gitExecutable,args,
      {...options,env:{...options.env,GIT_EXEC_PATH:startup.gitExecPath}})});
  const acquireAuthorityInputs = async (reader,pins) => {
    const rows=[];
    for (const p of pins) { declaredPin=p; rows.push(await acquisition.pin(reader.version,p)); }
    acquisition.acquire(rows);
  };
  // Reuse the existing explicit metadata transport only for genuinely missing
  // headers. Warm inputs cause no remote metadata request or archive discovery.
  let metadata;
  const acquireMetadata=async(reader,pins)=>{
    for(const p of pins){
      const route=reader.treeRoute(p.path),match=/^100644 blob ([a-f0-9]{40})\t/.exec(route);
      demand(match,'Missing ordinary selected metadata: '+p.path);
      const status=reader.gitBatch(['--no-lazy-fetch','cat-file','--batch-check=%(objectname) %(objecttype) %(objectsize)'],match[1]+'\n',128).toString();
      if(status===match[1]+' missing\n'){
        const {createRoutingMetadataAcquisition}=await import('../../../scripts/geography-routing-metadata.mjs');
        metadata??=createRoutingMetadataAcquisition({repo,baseline,execute:(_command,args,options)=>execFileSync(beforeReader.gitExecutable,args,
          {...options,env:{...options.env,GIT_EXEC_PATH:startup.gitExecPath}})});
        await metadata.acquire({commit:reader.version,path:p.path},p);
      }
    }
  };
  await acquireMetadata(beforeReader,[{path:'data/ownership-selection.json'}]);
  await acquireMetadata(afterReader,[{path:'data/ownership-selection.json'}]);
  let state, acceptedHandle;
  const transportInputs = [];
  phaseComplete('trusted-startup');
  if(beforeReader.json('data/ownership-selection.json').version===2){
    demand(trusted===undefined||trusted===baseline,'Final-map acceptance must execute the accepted baseline checker');
    for(const reader of [beforeReader,afterReader]){
      const selection=reader.json('data/ownership-selection.json');
      const {scientificNativeSelection,finalBankSelection}=await import('../../../src/reference-metadata.js');
      const native=scientificNativeSelection(selection),bank=finalBankSelection(selection);
      demand(bank,'Accepted final bank cannot downgrade to historical replay');
      await acquireMetadata(reader,[{path:native.manifest_path,sha256:native.sha256},bank,
        ...(selection.reference_projection?[selection.reference_projection]:[])]);
    }
    const nativeReport=await checkpoint.compareAcceptedFinalBank({beforeReader,afterReader,acquireAuthorityInputs,acquireMetadataInputs:acquireMetadata});
    phaseComplete('native-comparison');
    return consume({direct:true,nativeReport});
  }
  // Historical selectors retain their historical migration reader only.
  const accepted = await import('../../../scripts/accepted-selected-checkpoint.mjs');
  try {
    const locatorInput = checkpointTransportInput(afterReader, accepted.ACCEPTED_CHECKPOINT_LOCATOR);
    transportInputs.push(locatorInput.pin);
    let qualified;
    if (locatorInput.body) {
      const locator = accepted.validateAcceptedCheckpointLocator(JSON.parse(locatorInput.body));
      const archiveName = locator.retained_artifact?.path;
      let archiveIndex;
      if (archiveName) {
        archiveIndex = transportInputs.length;
        transportInputs.push(checkpointTransportInput(afterReader, archiveName, {consume:false}).pin);
      }
      const token = process.env.GH_TOKEN;
      if (!token && (!publicAccepted || !archiveName)) {
        phaseComplete('checkpoint-acquisition');
        return coldDecision({cold:'baseline-and-candidate', reason:'Accepted checkpoint authenticated API access unavailable'});
      }
      const proof = await accepted.acquireAcceptedCheckpoint({repo:process.env.GITHUB_REPOSITORY ?? 'ChengshuLi/WorldAtlas',
        locator:locator.acceptance, token,
        ...(!token?{api:accepted.acceptedCheckpointAPI(undefined,{publicReadOnly:true,...(checkpointFetchImpl?{fetchImpl:checkpointFetchImpl}:{})})}:{}),
        retainedArchive:archiveName ? () => {
          const input = checkpointTransportInput(afterReader, archiveName);
          transportInputs[archiveIndex] = input.pin;
          return input.body;
        } : undefined});
      phaseComplete('checkpoint-acquisition');
      if (!proof.available) return coldDecision({cold:'baseline-and-candidate', reason:proof.reason});
      acceptedHandle = proof.handle;
      qualified = await checkpoint.qualifyAcceptedCheckpoint({reader:beforeReader, acceptedHandle, acquireAuthorityInputs});
    } else {
      phaseComplete('checkpoint-acquisition');
      qualified = await checkpoint.qualifyCheckpoint({reader:beforeReader, acquireAuthorityInputs});
    }
    phaseComplete('baseline-qualification');
    if (!qualified.available) return coldDecision(qualified);
    state = qualified.state;
    const transition = await checkpoint.qualifyTransition({state, reader:afterReader});
    phaseComplete('candidate-qualification');
    if (!transition.available) return coldDecision(transition);
    checkpoint.authenticateTransition({transition});
    const nativeReport = await compareSelectedCheckpointNative({transition});
    phaseComplete('native-comparison');
    demand(nativeReport && ['native-regressions-found', 'no-new-native-loss'].includes(nativeReport.status),
      'Joint native consumer did not complete an actual comparison');

    return await consume({transition,nativeReport,checkpoint,transportInputs,valueBytes,valueSha});
  } finally {
    if (state) checkpoint.releaseCheckpoint(state);
    if (acceptedHandle) accepted.releaseAcceptedCheckpoint(acceptedHandle);
  }
}
function coldDecision(decision) {
  return {version:1, kind:'trusted-selected-joint-comparison-v1', mode:'legacy-cold-required',
    reuse_unavailable:{cold:decision.cold, reason:decision.reason}, candidate_code_executed:false};
}
// The existing cold/software entry uses the same exhaustive comparison but has
// no checkpoint destination or publication callback. It cannot mint a retained
// acceptance product, and an unavailable current final state never replays v1.
export async function inspectSelectedFinalBank(repo,baseline,candidate,startup,{fetchImpl:checkpointFetchImpl}={}) {
  if(checkpointFetchImpl!==undefined&&typeof checkpointFetchImpl!=='function')throw Error('Invalid checkpoint fetch implementation');
  const answer=await withSelectedComparison({repo,baseline,candidate,startup,phaseComplete:()=>{},publicAccepted:true,checkpointFetchImpl},
    async ({direct,transition,nativeReport,checkpoint})=>{
      demand(direct||checkpoint.authenticateTransition({transition}).candidate.version===2,'Current final-bank report cannot downgrade to historical replay');
      return {...nativeReport,candidate_code_executed:startup.beforeReader.git('-C',ROOT,'rev-parse','HEAD').toString().trim()!==baseline,
        runtime:startup.runtime,caller_runtime:startup.callerRuntime,
        execution_runtimes:startup.identities,execution_code_inventory:startup.executionCode};
    });
  demand(answer?.method==='selected-native-owner-conservation-v1',
    'Current final ownership requires its accepted main comparison: '+(answer?.reuse_unavailable?.reason??'comparison unavailable'));
  return answer;
}

export async function selectedJointStage(repo, trusted, baseline, candidate, destination, parentRuntimePath) {
  demand(commit(baseline) && commit(candidate), 'Joint comparison requires immutable selected commits');
  destination = path.resolve(destination); fresh(destination);
  let phaseStarted = performance.now();
  const phaseComplete = phase => {
    const now = performance.now();
    process.stderr.write(JSON.stringify({selected_joint_phase:phase, elapsed_ms:Math.round(now - phaseStarted)}) + '\n');
    phaseStarted = now;
  };
  const code = executionGuard(repo, trusted);
  const native = await import('../../../scripts/check-effective-geographic-regression.mjs');
  const startup = native.selectedBootstrap(repo, baseline, candidate, {parentRuntimePath});
  const {beforeReader,afterReader}=startup;
  return withSelectedComparison({repo,baseline,candidate,startup,phaseComplete,trusted},async({direct,transition,nativeReport,checkpoint,transportInputs,valueBytes,valueSha})=>{
    if(direct){
      executionGuard(repo,trusted);
      return result(nativeReport,null,'accepted-final-map-comparison-v1');
    }
    if(nativeReport.status==='native-regressions-found')return result(nativeReport,null);
    // Native comparison is the selected-map acceptance boundary. Do not build
    // or compare continuous polygon operands, including on no-change runs.
    const genuine = checkpoint.authenticateTransition({transition});
    const authorityPaths = [P + 'supported-programs.json',
      'coordination/engineering/selected-checkpoint-reuse-20261012/accepted-checkpoints.json'];
    const authorityPins = authorityPaths.map(name => beforeReader.inventory.get(trusted + ':' + name));
    demand(authorityPins.every(pin => pin?.whole_body_consumed && /^[a-f0-9]{64}$/.test(pin.sha256)),
      'Derived custody requires actual consumed executing authority pins');
    const executingPolicy = checkpoint.checkpointExecutingPolicy({transition});
    const inventory = reader => [...reader.inventory.values()].sort((a,b) =>
      (a.commit + ':' + a.path).localeCompare(b.commit + ':' + b.path));
    const routes = valueBytes(checkpoint.checkpointRouteCensus({transition}));
    const routePin = {path:'checkpoint-routes.json', bytes:routes.length, sha256:sha(routes)};
    const final=genuine.candidate.version===2;
    const profile={version:final?2:1,kind:final?'derived-selected-final-checkpoint-candidate-v2':'derived-selected-checkpoint-candidate-v1'};
    const derivedFactsBase = {...profile,
      validation_stage:'native-passed', accepted_checkpoint:false,
      executing_commit:trusted, execution_code:code, runtime:startup.identities,
      baseline_accepted_execution:genuine.baseline.accepted_execution,
      executing_authority_pins:authorityPins, executing_policy:executingPolicy,
      checkpoint_transport_inputs:transportInputs, checkpoint_routes:routePin,
      actual_reader_inventories:{baseline:inventory(beforeReader), candidate:inventory(afterReader)},
      baseline_commit:baseline, candidate_commit:candidate,
      baseline_selection:genuine.baseline.selection, candidate_selection:genuine.candidate.selection,
      ...(final?{accepted_authorities:genuine.candidate.accepted_authorities}:{}),
      candidate_bindings:final?{index:genuine.candidate.selection.prepared_bank,
        manifest_sha256:genuine.candidate.baseSelection.sha256,effective_reference:genuine.candidate.selection.reference,
        accepted_authorities_sha256:valueSha(genuine.candidate.accepted_authorities)}:{ledger_sha256:valueSha(genuine.candidate.ledger), registry_sha256:valueSha(genuine.candidate.registry),
        patch_sha256:valueSha(genuine.candidate.patch), manifest_sha256:valueSha(genuine.candidate.manifest)},
      native_result_sha256:valueSha(nativeReport), candidate_code_executed:false};
    const certificate = valueBytes(genuine.candidate.certificate);
    const certificateEncoded = gzipSync(certificate, {level:9, mtime:0});
    const certificatePin = {path:'derived-certificate.json.gz', bytes:certificateEncoded.length,
      sha256:sha(certificateEncoded), decoded_bytes:certificate.length, decoded_sha256:sha(certificate)};
    const derivedFacts = valueBytes({...derivedFactsBase, certificate:certificatePin});
    const derivedPublication = {...profile, complete:true,
      accepted_checkpoint:false, validation_stage:'native-passed', certificate:certificatePin,
      facts:{path:'derived-facts.json', bytes:derivedFacts.length, sha256:sha(derivedFacts)}, routes:routePin};
    const derivedPublicationBody = valueBytes(derivedPublication);
    checkpoint.authenticateTransition({transition});
    executionGuard(repo, trusted); fresh(destination); fs.mkdirSync(destination);
    for (const [name, body] of [['derived-certificate.json.gz', certificateEncoded],
      ['derived-facts.json', derivedFacts], ['checkpoint-routes.json', routes], ['derived-publication.json', derivedPublicationBody]])
      fs.writeFileSync(path.join(destination, name), body, {flag:'wx', mode:0o644});
    phaseComplete('checkpoint-output');
    return result(nativeReport, derivedPublication);
  });
  function result(nativeReport, derivedCheckpoint, mode='authenticated-checkpoint-append-v1') {
    return {version:1, kind:'trusted-selected-joint-comparison-v1', mode,
      native:{...nativeReport, runtime:startup.runtime, caller_runtime:startup.callerRuntime,
        execution_runtimes:startup.identities, execution_code_inventory:code}, derived_checkpoint:derivedCheckpoint,
      candidate_code_executed:false};
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const result = await selectedJointStage(...process.argv.slice(2));
  const body = JSON.stringify(result) + '\n';
  process.stdout.write(body);
}
