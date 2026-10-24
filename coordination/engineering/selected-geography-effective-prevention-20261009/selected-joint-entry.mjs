// One trusted Node invocation compares accepted and proposed final banks.
// Proposed commits are data, never imported code.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';

const ROOT = fileURLToPath(new URL('../../../', import.meta.url));
const P = 'coordination/engineering/selected-geography-effective-prevention-20261009/';
export const JOINT_CODE = Object.freeze([
  'scripts/run-geographic-check.py', 'scripts/geography-prefetch.mjs', 'scripts/geography-routing-metadata.mjs',
  'scripts/package-startup-ownership.mjs','src/ownership-assets.js','src/ownership-method.js',
  'scripts/native-word-store.mjs','scripts/native-patch-store.mjs', 'scripts/check-effective-geographic-regression.mjs',
  'src/native-grid.js', 'src/ownership-codec.js',
  P + 'selected-neighbor-prevention.mjs', P + 'selected-checkpoint.mjs', P + 'selected-joint-entry.mjs',
  'scripts/research-import-gate.mjs',
  'src/regional-import-gate.js',
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

async function withSelectedComparison({repo,baseline,candidate,startup,phaseComplete,publicAccepted=false,trusted},consume) {
  const checkpoint = await import('./selected-checkpoint.mjs');
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
  phaseComplete('trusted-startup');
  demand(beforeReader.json('data/ownership-selection.json').version===2,'Current checker requires the accepted final-map format');
  {
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
}
// The existing cold/software entry uses the same exhaustive comparison but has
// no checkpoint destination or publication callback. It cannot mint a retained
// acceptance product, and an unavailable current final state never replays v1.
export async function inspectSelectedFinalBank(repo,baseline,candidate,startup) {
  const answer=await withSelectedComparison({repo,baseline,candidate,startup,phaseComplete:()=>{},publicAccepted:true},
    async ({nativeReport})=>{
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
  return withSelectedComparison({repo,baseline,candidate,startup,phaseComplete,trusted},async({nativeReport})=>{
    executionGuard(repo,trusted);
    return {version:1,kind:'trusted-selected-joint-comparison-v1',mode:'accepted-final-map-comparison-v1',
      native:{...nativeReport,runtime:startup.runtime,caller_runtime:startup.callerRuntime,
        execution_runtimes:startup.identities,execution_code_inventory:code},derived_checkpoint:null,candidate_code_executed:false};
  });
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const result = await selectedJointStage(...process.argv.slice(2));
  const body = JSON.stringify(result) + '\n';
  process.stdout.write(body);
}
