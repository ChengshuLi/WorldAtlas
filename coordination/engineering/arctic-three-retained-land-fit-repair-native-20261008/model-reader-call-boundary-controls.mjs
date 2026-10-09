// Exact production-call extraction with real complete selector/stage metadata.
// Delegated whole restoration/consumption is not executed by this tiny control.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
const root=process.cwd(),N2='coordination/engineering/arctic-three-retained-land-fit-repair-native-20261008';
// This observational branch runs only AFTER the ordinary build has completed.
// It does not issue a consumption identity or re-execute scientific qualification.
function reportDestination(value){
 assert(value&& !value.split(path.sep).includes('..'),'Unsafe readback report path');
 const target=path.resolve(value),cache=path.join(root,'.cache');
 assert(target.startsWith(cache+path.sep),'Report must be in owned cache');
 for(let current=target;;current=path.dirname(current)){
  try{const stat=fs.lstatSync(current);assert(!stat.isSymbolicLink(),'Readback destination symlink');if(current===target)assert.fail('Readback report already exists');assert(stat.isDirectory(),'Report ancestor is not a directory');}
  catch(error){if(error.code!=='ENOENT')throw error;}
  if(current===root)break;
 }
 return target;
}
const readbackHash=bytes=>createHash('sha256').update(bytes).digest('hex');
function emittedFile(base,relative){
 assert(typeof relative==='string'&&relative&&!path.isAbsolute(relative)&&relative.split('/').every(x=>x&&x!=='.'&&x!=='..'),'Unsafe emitted path');
 const full=path.join(base,relative);let current=base;
 assert(fs.lstatSync(base).isDirectory()&&!fs.lstatSync(base).isSymbolicLink(),'Invalid build directory');
 for(const component of relative.split('/')){current=path.join(current,component);assert(!fs.lstatSync(current).isSymbolicLink(),'Emitted symlink');}
 assert(fs.lstatSync(full).isFile(),'Missing ordinary emitted file');
 return fs.readFileSync(full);
}
function requireEmittedPin(base,pin){const bytes=emittedFile(base,pin.path);if(pin.bytes!==undefined||pin.compressed_bytes!==undefined)assert.equal(bytes.length,pin.bytes??pin.compressed_bytes);assert.equal(readbackHash(bytes),pin.sha256);return bytes;}
function emittedInventory(base){
 const result=[];
 function walk(relative){for(const name of fs.readdirSync(path.join(base,relative)).sort()){
  const file=relative?relative+'/'+name:name,stat=fs.lstatSync(path.join(base,file));assert(!stat.isSymbolicLink(),'Emitted symlink');
  if(stat.isDirectory())walk(file);else{assert(stat.isFile(),'Nonordinary emitted file');const bytes=emittedFile(base,file);result.push({path:file,bytes:bytes.length,sha256:readbackHash(bytes)});}
 }}walk('');return result;
}

const originalStartupPins=[{"path":"native-v1/ownership/startup-runs-0.bin.gz","bytes":3854101,"sha256":"3d551738a3454d2028e1d9adc352b7446d7c0f25c8d42044704cf1efb6f64b6b"},{"path":"native-v1/ownership/startup-runs-12582912.bin.gz","bytes":3478667,"sha256":"01012dd358291a9e4ee51888a1d2b618ab2003e06a6eebd3a236392ecdbbc015"},{"path":"native-v1/ownership/startup-runs-16777216.bin.gz","bytes":3289324,"sha256":"d5ed4d7e1700fb60298a53cc37ad9943257f57f853e19cc786ef975ebc7f0cae"},{"path":"native-v1/ownership/startup-runs-20971520.bin.gz","bytes":3146696,"sha256":"198daba78eaeed9f316f088a86f8a7c4cf8f7e868253fc09487870eceddaf58a"},{"path":"native-v1/ownership/startup-runs-25165824.bin.gz","bytes":3272873,"sha256":"764a967753d010daa794b30ca597bee0503646e7cae6965b14df63f280b9c544"},{"path":"native-v1/ownership/startup-runs-29360128.bin.gz","bytes":3296575,"sha256":"ff29a1956ae0dd99e4db155c9cdabf96c72155a1a772210910d5119845759cf8"},{"path":"native-v1/ownership/startup-runs-33554432.bin.gz","bytes":3521891,"sha256":"826cffaf4b05286a68ae479bc6e6caba3b3b3993f7fa57eae08efe7f6089694b"},{"path":"native-v1/ownership/startup-runs-37748736.bin.gz","bytes":3497645,"sha256":"18472136ceb94b95a17918acdfba32c56d13a2979043c66fb74cf615d81551ee"},{"path":"native-v1/ownership/startup-runs-4194304.bin.gz","bytes":3428397,"sha256":"da6498fc3c898adca6231896e9b1f2c734153064d78431bc5a311fec768c18f9"},{"path":"native-v1/ownership/startup-runs-41943040.bin.gz","bytes":3534601,"sha256":"f4e7f8de92e3d709db9675386961fac934a8a21652bf6f34f8d122ed71c73c44"},{"path":"native-v1/ownership/startup-runs-46137344.bin.gz","bytes":3556931,"sha256":"bb9b1ba3ace6229a338eee6c903e1d5db637a765c46ed60f957ceb6e34346101"},{"path":"native-v1/ownership/startup-runs-50331648.bin.gz","bytes":3397952,"sha256":"09aaf4d9a115dea6a85ed2a853532045c627ea2408f259513ce9de8e616ef55d"},{"path":"native-v1/ownership/startup-runs-54525952.bin.gz","bytes":2460609,"sha256":"91bfddd9aa632dc18ecc2f487a71673b504f971d2795e7c4af9c9298f4fe4fbc"},{"path":"native-v1/ownership/startup-runs-8388608.bin.gz","bytes":3423683,"sha256":"244e3da13a412b4a4ccbc652191a080495a5611df5d0ee2207c8d08ac27b929a"}];

async function builtOutputReadback(report){
 const target=reportDestination(report),base=path.join(root,'dist/client');
 const {gunzipSync}=await import('node:zlib');
 const {unshuffleOwnershipBytes}=await import('../../../src/ownership-codec.js');
 const {validateCoverageManifest}=await import('../../../src/coverage-classification.js');
 const files=emittedInventory(base),largest=files.reduce((a,b)=>a.bytes>b.bytes?a:b,{bytes:0});
 assert(files.length<=20000,'Cloudflare free static asset count exceeded');assert(largest.bytes<=25*1024*1024,'Cloudflare static file limit exceeded');
 const atlas=JSON.parse(emittedFile(base,'atlas-geography.json'));
 const nativeRaw=fs.readFileSync(N2+'/native-v9/manifest.json'),native=JSON.parse(nativeRaw),nativeSha=readbackHash(nativeRaw);
 const stage=JSON.parse(fs.readFileSync(N2+'/context-stage-v9.json'));
 const selected=JSON.parse(fs.readFileSync('data/ownership-selection.json'));
 assert.equal(nativeSha,selected.sha256);
 const pixel=atlas.pixelMap;assert.equal(pixel.version,2);assert.equal(pixel.size,native.size);assert.equal(pixel.runWords,native.runWords);
 assert.equal(atlas.reference_release.id,'geography:review:dbb133d7b123bacd1d38253c467891bff656d011000a9f11d369ac9262302bfb');
 assert.equal(atlas.preparedEvidence.footprints_sha256,native.footprints_sha256);assert.equal(atlas.preparedEvidence.hierarchy_sha256,native.hierarchy_sha256);
 validateCoverageManifest(atlas.coverageClassification,{...native,canonical_grid_sha256:nativeSha,release_id:atlas.reference_release.id});
 const rowsPart=pixel.parts.filter(x=>x.kind==='rows');assert.equal(rowsPart.length,1);
 const rowRaw=requireEmittedPin(base,rowsPart[0]),rows=unshuffleOwnershipBytes(gunzipSync(rowRaw),rowsPart[0].words);
 assert.equal(readbackHash(Buffer.from(rows.buffer)),rowsPart[0].decoded_sha256);assert.equal(rows.length,native.size*2);
 function counts(parts,decodedPins){
  const out=new Float64Array(49626),streamHash=createHash('sha256');let wordOffset=0,row=0,rowEnd=rows[1],previous=0;
  for(const part of parts){
   assert.equal(part.offset,wordOffset);const words=unshuffleOwnershipBytes(gunzipSync(requireEmittedPin(base,part)),part.words);
   streamHash.update(Buffer.from(words.buffer));if(decodedPins)assert.equal(readbackHash(Buffer.from(words.buffer)),part.decoded_sha256);
   assert.equal(words.length%2,0);
   for(let i=0;i<words.length;i+=2){const run=(wordOffset+i)/2;
    while(run===rowEnd&&row<native.size-1){row++;assert.equal(rows[row*2],run);rowEnd=run+rows[row*2+1];previous=0;}
    assert(run<rowEnd,'Unreferenced ownership run');const a=words[i],b=words[i+1],start=a&524287,end=(b&524287)+1,id=(a>>>19)+(b>>>19)*8192;
    assert(id>0&&id<out.length&&start>=previous&&end>start&&end<=native.size,'Invalid ownership interval');out[id]+=end-start;previous=end;
   }wordOffset+=words.length;
  }
  assert.equal(wordOffset,native.runWords);assert.equal(rowEnd,native.runWords/2);return {counts:out,word_stream_sha256:streamHash.digest('hex')};
 }
 const oldParts=originalStartupPins.map(pin=>({...pin,kind:'runs',offset:Number(pin.path.match(/startup-runs-(\d+)/)[1]),words:Math.min(4194304,native.runWords-Number(pin.path.match(/startup-runs-(\d+)/)[1]))})).sort((a,b)=>a.offset-b.offset);
 const oldDecoded=counts(oldParts,false),oldCounts=oldDecoded.counts;
 const runs=pixel.parts.filter(x=>x.kind==='runs').sort((a,b)=>a.offset-b.offset);
 assert(runs.every(x=>x.path.startsWith('ownership-vintages/'+nativeSha+'/')),'Successor URL vintage missing');
 const newDecoded=counts(runs,true),newCounts=newDecoded.counts,deltas=[];let total=0;
 for(let id=1;id<newCounts.length;id++){total+=newCounts[id];if(newCounts[id]!==oldCounts[id])deltas.push({owner:id,old:oldCounts[id],current:newCounts[id],gain:newCounts[id]-oldCounts[id]});}
 assert.deepEqual(deltas,[{owner:6666,old:25131612,current:25131752,gain:140},{owner:6757,old:15853829,current:15853830,gain:1}]);
 assert.equal(total,native.accounting.owned_cells);
 const ownerRows=[],ids=new Set();
 for(const relative of atlas.parts){for(const feature of JSON.parse(gunzipSync(emittedFile(base,relative)))){assert(!ids.has(feature.id));ids.add(feature.id);ownerRows.push([feature.pixelIndex,feature.id]);}}
 assert.equal(ids.size,49625);assert.equal(readbackHash(JSON.stringify(ownerRows)),pixel.reference_owner_sha256);
 const changedRaw=fs.readFileSync(N2+'/changed-complete-context-rows.json');assert.equal(readbackHash(changedRaw),'415fe26f080cbf831be326dc7ac29b59c7758ba04a6143fe454fb86a54be62a3');
 const expectedTargets=new Map(JSON.parse(changedRaw).map(row=>[row.id,row.geometry])),seenGeometry=new Set(),actualTargets=[];
 for(const relative of atlas.geometryParts)for(const row of JSON.parse(gunzipSync(emittedFile(base,relative)))){
  assert(!seenGeometry.has(row.id),'Duplicate emitted geometry identity');seenGeometry.add(row.id);
  if(expectedTargets.has(row.id)){assert.deepEqual(row.geometry,expectedTargets.get(row.id));actualTargets.push(row.id);}
 }
 assert.equal(seenGeometry.size,49625);assert.deepEqual(actualTargets.sort(),[...expectedTargets.keys()].sort());assert.deepEqual([...seenGeometry].sort(),[...ids].sort());
 for(const field of ['entityParts','temporalHistoryParts'])for(const relative of atlas[field])JSON.parse(gunzipSync(emittedFile(base,relative)));
 const prepared=JSON.parse(emittedFile(base,'prepared-evidence/index.json'));assert.equal(readbackHash(emittedFile(base,'prepared-evidence/index.json')),atlas.preparedEvidence.index_sha256);
 assert.equal(prepared.footprints_sha256,native.footprints_sha256);assert.equal(prepared.hierarchy_sha256,native.hierarchy_sha256);
 const historyRaw=requireEmittedPin(base,{path:'atlas-history.json.gz',bytes:455,sha256:'7b541f0f2caaaa531cd7ca0c124d1a2ae7cab55d667aa0b73b2ae6aa9916ab2d'});const history=JSON.parse(gunzipSync(historyRaw));
 const worker=emittedInventory(path.join(root,'dist/cloudflare'));
 const result={version:1,kind:'ordinary-cloudflare-built-output-readback',head:execFileSync(process.platform==='darwin'?'/Library/Developer/CommandLineTools/usr/bin/git':'/usr/bin/git',['rev-parse','HEAD'],{encoding:'utf8'}).trim(),
  selected_manifest_sha256:nativeSha,certificate:stage.artifact_consumption.certificate,review:stage.artifact_consumption.review,
  static_assets:{count:files.length,bytes:files.reduce((n,x)=>n+x.bytes,0),largest,limits:{file_bytes:25*1024*1024,free_count:20000},files},worker_bundle_files:worker,
  old_url_provenance:{original_budget_sha256:'1f8c8ceb7f7ec7bd5c36a5d7ce083f246841187a23b663b6b228ccea1fdc2e85',pins:originalStartupPins},
  ownership:{complete_source_owners:ids.size,unchanged_owner_counts:49623,rows:native.size,runWords:native.runWords,total_owned_cells:total,deltas,old_word_stream_sha256:oldDecoded.word_stream_sha256,current_word_stream_sha256:newDecoded.word_stream_sha256},
  emitted_geometry:{records:seenGeometry.size,qualified_targets:actualTargets},reference_release:atlas.reference_release,preparedEvidence:atlas.preparedEvidence,coverageClassification:atlas.coverageClassification,
  nativeContextInputStage:atlas.nativeContextInputStage,contentCapabilities:atlas.contentCapabilities,referenceAttributes:atlas.referenceAttributes,
  history_sha256:readbackHash(emittedFile(base,'atlas-history.json.gz')),history_keys:Object.keys(history),
  limitation:'Offline whole emitted bytes and ownership/association readback; no browser, deployment, scientific replay or inferred repair acceptance.'};
 fs.mkdirSync(path.dirname(target),{recursive:true});fs.writeFileSync(target,JSON.stringify(result,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify({built_output_readback:target,bytes:fs.statSync(target).size,sha256:readbackHash(fs.readFileSync(target))}));
}
if(process.argv[2]==='--built-output-controls'){
 const scratch=fs.mkdtempSync(path.join(root,'.cache/built-readback-controls-'));
 try{
  const base=path.join(scratch,'client');fs.mkdirSync(base);const bytes=Buffer.from('actual emitted fixture');fs.writeFileSync(path.join(base,'asset.bin'),bytes);
  const pin={path:'asset.bin',bytes:bytes.length,sha256:readbackHash(bytes)};
  assert.deepEqual(requireEmittedPin(base,pin),bytes);assert.equal(emittedInventory(base).length,1);
  let refusals=0;
  for(const operation of [()=>requireEmittedPin(base,{...pin,path:'missing.bin'}),()=>requireEmittedPin(base,{...pin,sha256:'0'.repeat(64)}),()=>requireEmittedPin(base,{...pin,bytes:1}),()=>emittedFile(base,'../asset.bin')]){assert.throws(operation);refusals++;}
  fs.writeFileSync(path.join(base,'asset.bin'),'changed');assert.throws(()=>requireEmittedPin(base,pin));refusals++;
  const existing=path.join(scratch,'existing.json');fs.writeFileSync(existing,'old');assert.throws(()=>reportDestination(existing));refusals++;
  const dangling=path.join(scratch,'dangling.json');fs.symlinkSync(path.join(scratch,'absent'),dangling);assert.throws(()=>reportDestination(dangling));refusals++;
  assert.throws(()=>reportDestination(path.join(root,'.cache/../outside.json')));refusals++;
  fs.symlinkSync(path.join(scratch,'absent'),path.join(base,'symlink'));assert.throws(()=>emittedInventory(base));refusals++;
  console.log(JSON.stringify({built_output_controls:{positives:2,refusals},limitation:'Tiny actual output reader and destination boundaries only; no full build qualification.'}));
 }finally{fs.rmSync(scratch,{recursive:true,force:true});}
 process.exit(0);
}
if(process.argv[2]==='--built-output-readback'){await builtOutputReadback(process.argv[3]);process.exit(0);}

const raw=fs.readFileSync(new URL('./prepare-model-reader-checkout.mjs',import.meta.url));
const source=raw.toString(),start=source.indexOf('export async function prepareModelReaderCheckout');
assert(start>=0);
const git=process.platform==='darwin'?'/Library/Developer/CommandLineTools/usr/bin/git':'/usr/bin/git';
function original(relative){return JSON.parse(fs.existsSync(relative)?fs.readFileSync(relative):execFileSync(git,['show','HEAD:'+relative]));}
const selection=original('data/ownership-selection.json'),stage=original(N2+'/context-stage-v9.json');
const AsyncFunction=Object.getPrototypeOf(async function(){}).constructor;
async function invoke({profile='full',shard=2,changeSelection,changeStage,failPreflight=false}={}){
 const selected=structuredClone(selection),sidecar=structuredClone(stage),events=[];let reads=0;
 changeSelection?.(selected);changeStage?.(sidecar);
 const mockFs={realpathSync:value=>value,readFileSync:file=>{reads++;return Buffer.from(JSON.stringify(file.endsWith('ownership-selection.json')?selected:sidecar));},mkdirSync:()=>events.push('mkdir')};
 const preflight=options=>{events.push('preflight');assert.deepEqual(options,{source:root,stage:root,sidecar});if(failPreflight)throw Error('admission refused');return {actual_admission_fixture:true};};
 const issue=options=>{events.push('issue');assert.equal(options.root,root);assert.equal(options.admission.actual_admission_fixture,true);return {private_execution_fixture:true};};
 const restore=options=>{events.push('restore');assert.equal(options.root,root);assert.equal(options.mode,'checkout');assert.equal(options.temporaryRoot,path.join(root,'.cache'));return {original_custody_fixture:true};};
 const consume=async options=>{events.push('consume');assert.equal(options.restoredReceipt.original_custody_fixture,true);assert.equal(options.currentExecution.private_execution_fixture,true);return {receipt:{current_execution:{fixture:true}}};};
 const install=async options=>{events.push('install');assert.equal(options.context.receipt.current_execution.fixture,true);return {fixture:true};};
 const factory=new AsyncFunction('assert','fs','path','N2','preflightArtifactPackage','issueCheckoutExecution','restoreCanonicalProducts','consumeQualifiedArcticArtifacts','installV9Stage',source.slice(start).replace('export async function','async function')+'\nreturn prepareModelReaderCheckout;');
 const fn=await factory(assert,mockFs,path,N2,preflight,issue,restore,consume,install);
 try{return {result:await fn({root,profile,shard}),events,reads};}catch(error){error.events=events;error.reads=reads;throw error;}
}
const positive=await invoke();
assert.deepEqual(positive.events,['preflight','issue','mkdir','restore','consume','install']);assert.equal(positive.result.applicable,true);
const preparedPositive=await invoke({shard:1});assert.deepEqual(preparedPositive.events,positive.events);
const packagedPositive=await invoke({shard:0});assert.deepEqual(packagedPositive.events,positive.events);
let rejected=0;
for(const options of [{profile:'evidence'},{shard:3},{changeStage:s=>s.version=3},{changeSelection:s=>s.artifact_consumption.certificate.sha256='0'.repeat(64)},{failPreflight:true}]){
 await assert.rejects(()=>invoke(options),error=>{assert(!error.events.includes('restore'));return true;});rejected++;
}
console.log(JSON.stringify({positive:3,rejected,actual_production_source_sha256:createHash('sha256').update(raw).digest('hex'),metadata:{selection,stage},order:positive.events,
 limitation:'Exact production function, real complete metadata and stubbed delegated boundaries; no restoration, consumption, installer or full normal checkout qualification.'},null,2));

// Complete selected root-space inputs and actual executing source closure must
// be included in the real sparse package definition before a hosted dispatch.
const {validatePackageInputs,containsPackagePath}=await import('../../../scripts/package-inputs.mjs');
const {completeReleaseProductInputs}=await import('./release-product-inputs.mjs');
const {gunzipSync}=await import('node:zlib');
const certificate=original(N2+'/qualified-artifacts/consumption-certificate.json');
const codeInventory=original(N2+'/qualified-artifacts/application-consumer-code.json');
const cataloguePin=certificate.release_product_catalogue;
const catalogueRaw=fs.readFileSync(cataloguePin.path);
assert.equal(catalogueRaw.length,cataloguePin.bytes);
assert.equal(createHash('sha256').update(catalogueRaw).digest('hex'),cataloguePin.sha256);
const catalogueDecoded=gunzipSync(catalogueRaw);
assert.equal(catalogueDecoded.length,cataloguePin.decoded_bytes);
assert.equal(createHash('sha256').update(catalogueDecoded).digest('hex'),cataloguePin.decoded_sha256);
const expanded=completeReleaseProductInputs(certificate,JSON.parse(catalogueDecoded));
assert.equal(expanded.length,533);
const required=new Set([stage.artifact_consumption.certificate.path,stage.artifact_consumption.review.path]);
for(const pin of expanded)if((pin.space??'root')==='root')required.add(pin.path);
for(const pin of codeInventory.critical_files)required.add(pin.path);
for(const entry of ['scripts/build-static-inner.mjs','scripts/build-hosted-inner.mjs','scripts/build-cloudflare-inner.mjs']){
 for(const pin of codeInventory.entry_critical_files[entry])required.add(pin.path);
 for(const relative of codeInventory.entry_roles[entry].actual_current_execution_wrappers)required.add(relative);
}
function requirePackageCoverage(value){
 const definition=validatePackageInputs(value);
 for(const relative of required)assert(containsPackagePath(definition.inputs,relative),'Missing selected package input: '+relative);
 return definition;
}
const definition=original('.github/package-inputs.json');
requirePackageCoverage(definition);
let missingPathRefusals=0;
for(const relative of [
 N2+'/selected-geography/part-29-application.json.gz',
 N2+'/application-geometry-serialization.mjs',N2+'/application-geometry-producer.mjs',
 N2+'/phase-admission.mjs',N2+'/artifact-checkout-execution.mjs',N2+'/prepare-model-reader-checkout.mjs'
]){
 const omitted=structuredClone(definition);
 omitted.inputs=omitted.inputs.filter(input=>input!==relative);
 assert.throws(()=>requirePackageCoverage(omitted),/Missing selected package input:/);
 missingPathRefusals++;
}
console.log(JSON.stringify({package_coverage_positive:1,missing_path_refusals:missingPathRefusals,
 expanded_roles:expanded.length,required_root_and_executing_paths:required.size,
 input_definition_sha256:createHash('sha256').update(fs.readFileSync('.github/package-inputs.json')).digest('hex'),
 limitation:'Real selected certificate/catalogue and code metadata joined to real sparse config; no package materialization, artifact consumption or scientific replay.'},null,2));

// Execute the exact selected-runner call against the real setup observer.
const {observeSetupPhase}=await import('../../../scripts/ci-setup-observations.mjs');
const runner=fs.readFileSync('scripts/run-integration-tests.mjs','utf8');
const begin=runner.indexOf('const selectedCheckout=await observeSetupPhase(');
const finish=runner.indexOf('console.log(JSON.stringify({selected_model_reader_checkout:selectedCheckout}));',begin);
assert(begin>=0&&finish>begin);
const invocation=runner.slice(begin,finish);
const delegatedImport="const {prepareModelReaderCheckout}=await import('../coordination/engineering/arctic-three-retained-land-fit-repair-native-20261008/prepare-model-reader-checkout.mjs');";
assert(invocation.includes(delegatedImport));
const actualCall=new AsyncFunction('observeSetupPhase','prepareModelReaderCheckout','profile','shard',invocation.replace(delegatedImport,'')+'\nreturn selectedCheckout;');
assert(runner.includes('if ([0,1,2].includes(shard)) {'));
const observations=[];let delegated=0;
const observed=(name,work)=>observeSetupPhase(name,work,{emit:value=>observations.push(value)});
for(const shard of [0,1,2]){
 const selected=await actualCall(observed,async options=>{delegated++;assert.deepEqual(options,{root:process.cwd(),profile:'full',shard});return {distinct_selected_checkout_fixture:true};},'full',shard);
 assert.equal(selected.distinct_selected_checkout_fixture,true);
}
assert.equal(delegated,3);
assert.deepEqual(observations.map(value=>[value.setup_phase,value.status]),[['canonical-checkout','started'],['canonical-checkout','success'],['canonical-checkout','started'],['canonical-checkout','success'],['canonical-checkout','started'],['canonical-checkout','success']]);
let forbiddenDelegated=0;
await assert.rejects(()=>observeSetupPhase('selected-model-reader-checkout',async()=>{forbiddenDelegated++;}),/assert|expression/i);
assert.equal(forbiddenDelegated,0);
console.log(JSON.stringify({actual_runner_observer_positive:3,unsupported_label_refused_before_work:1,
 runner_sha256:createHash('sha256').update(runner).digest('hex'),
 limitation:'Exact runner invocation and actual observer with delegated checkout stub; no restore, consumption or full regression run.'},null,2));

// Real original package issuer/validator, with the Cloudflare outer entry.
// The complete fixture contains frozen source bodies but performs no compiler,
// application installation, provider operation or historical science.
const {issueCurrentExecution,authenticateCurrentExecution,requireCurrentExecution,currentExecutionClosure}=await import('../eastern-two-gap-repair-native-20261007/current-execution.mjs');
const cloudflareEntry='scripts/build-cloudflare-inner.mjs';
const cloudflareFiles=currentExecutionClosure(root,cloudflareEntry);
const cloudflareRecord=issueCurrentExecution({source:root,stage:root,entry:cloudflareEntry});
authenticateCurrentExecution(cloudflareRecord,{root,executingRoot:root,sourceRoot:root});
assert.equal(requireCurrentExecution(cloudflareRecord),cloudflareRecord);
assert.equal(cloudflareRecord.entry_point,cloudflareEntry);
assert(cloudflareFiles.includes('scripts/build-static-inner.mjs'),'Cloudflare imports the static compiler in the same process');
const declaredCritical=[...codeInventory.critical_files,...codeInventory.entry_critical_files[cloudflareEntry]];
const declaredWrappers=Object.values(codeInventory.entry_roles[cloudflareEntry]).flat();
assert.deepEqual([...declaredCritical.map(pin=>pin.path),...declaredWrappers].sort(),cloudflareFiles);
for(const pin of declaredCritical){const actual=cloudflareRecord.files.find(file=>file.path===pin.path);assert.deepEqual(actual,pin);}
for(const foreign of [{},structuredClone(cloudflareRecord)])assert.throws(()=>requireCurrentExecution(foreign));
console.log(JSON.stringify({actual_cloudflare_issuer_positive:1,private_authority_refusals:2,
 entry:cloudflareRecord.entry_point,complete_execution_files:cloudflareRecord.files.length,
 admission:cloudflareRecord.runtime.bytes,
 limitation:'Actual immutable original issuer/authenticator and full Cloudflare execution closure on a complete source-only Git fixture; no full normal build, deployment or scientific qualification.'},null,2));
