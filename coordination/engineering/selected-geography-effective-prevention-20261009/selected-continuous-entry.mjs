// Trusted cold acquisition only. Proposed commits are data, never imported code.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {gzipSync,gunzipSync} from 'node:zlib';
const FILE=33554432,ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../..');
const P='coordination/engineering/selected-geography-effective-prevention-20261009/';
const CODE=[P+'selected-continuous-entry.mjs',P+'selected-neighbor-prevention.mjs','scripts/check-effective-geographic-regression.mjs','scripts/visible-gap-eligibility.mjs','src/native-grid.js','src/ownership-codec.js','scripts/run-geographic-check.py','scripts/check-geographic-regression.py','scripts/evidence/immutable.py','scripts/evidence/geometry.py','scripts/ellipsoidal_area.py','requirements.txt'];
const demand=(v,m)=>{if(!v)throw Error(m);},sha=b=>createHash('sha256').update(b).digest('hex');
const coldGc=globalThis.gc;
function timedStage(name, details, run) {
 const start=performance.now();
 process.stderr.write(JSON.stringify({selected_continuous_stage:name,event:'start',...details})+'\n');
 try { return run(); }
 finally { process.stderr.write(JSON.stringify({selected_continuous_stage:name,event:'end',...details,elapsed_ms:Math.round(performance.now()-start)})+'\n'); }
}
// An additive hook can only disable the old shortcut. It grants no acceptance;
// complete coordinate acquisition still validates both immutable selections.
export function mayUseNonAdditiveShortcut(beforeReader,afterReader) {
 const selectors=[beforeReader,afterReader].map(reader=>reader.json('data/ownership-selection.json'));
 return !selectors.some(value=>value!==null&&typeof value==='object'&&Object.hasOwn(value,'additive_release'));
}
export function checkColdReclaimer(){demand(process.execArgv.length===1&&process.execArgv[0]==='--expose-gc'&&process.env.NODE_OPTIONS===undefined&&process.env.NODE_PATH===undefined&&typeof coldGc==='function'&&globalThis.gc===coldGc&&Function.prototype.toString.call(coldGc).includes('[native code]'),'Cold whole-source acquisition requires authenticated native GC entry');}
function reclaimCompletedSource(){checkColdReclaimer();coldGc();}
const commit=v=>typeof v==='string'&&/^[a-f0-9]{40}$/.test(v);
function ordinaryParents(target){for(let p=path.dirname(target);;p=path.dirname(p)){const s=fs.lstatSync(p);demand(s.isDirectory()&&!s.isSymbolicLink(),'Nonordinary cold output ancestor');if(p===path.dirname(p))break;}}
function fresh(target){ordinaryParents(target);let exists=true;try{fs.lstatSync(target);}catch(e){if(e.code!=='ENOENT')throw e;exists=false;}demand(!exists,'Cold output already exists');}
function guard(repo,trusted){
 demand(commit(trusted),'Missing immutable trusted executing commit');
 const git=(...a)=>execFileSync('git',['-c','core.hooksPath=/dev/null','-C',repo,...a],{maxBuffer:FILE+1,stdio:['ignore','pipe','pipe']});
 demand(git('rev-parse','HEAD').toString().trim()===trusted&&fs.realpathSync(repo)===fs.realpathSync(ROOT),'Cold checker must run from actual trusted checkout');
 const stats=CODE.map(name=>{const f=path.join(ROOT,name);ordinaryParents(f);const s=fs.lstatSync(f);demand(s.isFile()&&!s.isSymbolicLink()&&s.size<=FILE,'Nonordinary cold execution code');return {name,f,s};});
 // Pre-import admission mirrors the shared current allowance; the authenticated
 // reader independently rechecks current availability after these code opens.
 const reserved=Number(process.env.WORLDATLAS_CONCURRENT_RESERVED_BYTES??0),available=process.availableMemory();
 demand([reserved,available].every(n=>Number.isSafeInteger(n)&&n>=0),'Invalid cold current resource observations');
 const phaseBytes=Math.floor((available-reserved-2*1024**3-768*1024**2)/2);
 demand(phaseBytes>0&&stats.reduce((n,r)=>n+r.s.size,0)+fs.statSync(process.execPath).size+8388608+FILE<phaseBytes,'Cold code/runtime admission before code body opens');
 return stats.map(({name,f,s})=>{const row=git('ls-tree','-z',trusted,'--',name).toString();demand(/^100(644|755) blob [a-f0-9]{40}\t/.test(row)&&row.endsWith('\t'+name+'\0'),'Unbound cold execution code');const [mode,,oid]=row.slice(0,row.indexOf('\t')).split(' ');demand(Number(git('cat-file','-s',oid))===s.size,'Cold code size differs');const local=fs.readFileSync(f),raw=git('cat-file','blob',oid);demand(local.equals(raw)&&(s.mode&0o777)===(mode==='100755'?0o755:0o644),'Cold code whole body/mode differs');return {commit:trusted,path:name,mode,git_blob_oid:oid,bytes:raw.length,sha256:sha(raw)};});
}
export async function coordinateStage(repo,trusted,selected,destination,parentRuntimePath){
 demand(commit(selected),'Missing immutable selected input commit');destination=path.resolve(destination);fresh(destination);checkColdReclaimer();
 const code=guard(repo,trusted);
 const native=await import('../../../scripts/check-effective-geographic-regression.mjs');
 const helper=await import('./selected-neighbor-prevention.mjs');
 const startup=native.selectedBootstrap(repo,selected,selected,{parentRuntimePath});
 const context=bootstrapContext(repo,startup);
 return acquireCompleteColdSide(native,helper,{repo,trusted,selected,destination,context,
  carriedState:{context,code,ack:[],receipts:[],lifecycle:[]}}).ack;
}
function bootstrapContext(repo,startup) {
 return {repo,runtimeBytes:startup.beforeReader.runtimeBytes,executionBytes:startup.beforeReader.executionBytes,
  gitExecutable:startup.beforeReader.gitExecutable,identities:startup.identities};
}
// This frame publishes only compact custody. Shards, decoded/encoded certificate
// buffers and the original whole source collections cannot escape to readback.
function publishCoordinateSnapshot(helper,{repo,trusted,selected,destination,context,code,reader,resolver}) {
 const shards=[];
 // The issued footprint value is once-qualified historical authority. This
 // separate certificate authenticates every actual selected whole source body,
 // full unique owner roster and per-record pointsets; it does not recompute the
 // legacy world digest using a source traversal that was never its method.
 for(const name of resolver.paths){shards.push(timedStage('coordinate-source',{selected,source:name},()=>helper.selectedCoordinateShard(resolver,[name],{priorShards:shards})));
  // Only compact immutable certificates survive here. The complete original
  // FeatureCollection has left the helper frame; reclaim it before next input.
  reclaimCompletedSource();
 }
 const certificate=helper.joinSelectedCoordinateCertificate(resolver,shards),decoded=helper.valueBytes(certificate);
 demand(decoded.length<=FILE,'Complete certificate ordinary decoded cap');
 const encoded=gzipSync(decoded,{level:9,mtime:0});
 const facts={version:1,kind:'trusted-selected-coordinate-stage-v1',executing_commit:trusted,selected_commit:selected,execution_code:code,
  runtime:context.identities,runtime_argv:process.execArgv,source_lifecycle:'whole-containing-body-authenticate-extract-discard-native-gc',source_certificate_domain:'complete-selected-source-pointsets:v1',historical_footprint_authority:{value:resolver.release.footprints_sha256,release:resolver.release,recomputed:false},binding:certificate.binding,complete_owners:certificate.entries.length,complete_sources:resolver.paths.length,
  inputs:[...reader.inventory.values()],acquisition_phases:shards.flatMap(s=>s.phases),join_phase_bytes:certificate.complete_phase_bytes,
  limits:certificate.limitations,candidate_code_executed:false};
 const factsBody=helper.valueBytes(facts),publication={version:1,complete:true,kind:facts.kind,
  certificate:{path:'certificate.json.gz',bytes:encoded.length,sha256:sha(encoded),decoded_bytes:decoded.length,decoded_sha256:sha(decoded)},
  facts:{path:'facts.json',bytes:factsBody.length,sha256:sha(factsBody)}};
 const pubBody=helper.valueBytes(publication);
 demand(encoded.length+decoded.length+2*factsBody.length+pubBody.length<=FILE,'Complete cold output reservation exceeded');
 // Whole publication last. No partial output is represented as completion.
 guard(repo,trusted);fresh(destination);fs.mkdirSync(destination);
 for(const [name,body]of [['certificate.json.gz',encoded],['facts.json',factsBody],['publication.json',pubBody]])fs.writeFileSync(path.join(destination,name),body,{flag:'wx',mode:0o644});
 return {publication,complete_owners:facts.complete_owners,complete_sources:facts.complete_sources,candidate_code_executed:false};
}
function readColdProduct(directory,ack,reader,helper){
 directory=path.resolve(directory);ordinaryParents(path.join(directory,'publication.json'));const directoryStat=fs.lstatSync(directory);demand(directoryStat.isDirectory()&&!directoryStat.isSymbolicLink(),'Nonordinary cold stage directory');
 const files=[{name:'publication.json',bytes:helper.valueBytes(ack.publication).length,sha256:sha(helper.valueBytes(ack.publication))},{name:'facts.json',...ack.publication.facts},{name:'certificate.json.gz',...ack.publication.certificate}];
 for(const p of files){demand(!p.name.includes('/')&&Number.isSafeInteger(p.bytes)&&p.bytes>0&&p.bytes<=FILE&&(p.decoded_bytes===undefined||Number.isSafeInteger(p.decoded_bytes)&&p.decoded_bytes>0&&p.decoded_bytes<=FILE),'Cold product ordinary cap');const f=path.join(directory,p.name),stat=fs.lstatSync(f);demand(stat.isFile()&&!stat.isSymbolicLink()&&stat.size===p.bytes&&(stat.mode&0o777)===0o644,'Cold product mode/whole length differs');}
 const charge=files.reduce((n,p)=>n+p.bytes+(p.decoded_bytes??0),0);demand(reader.used+charge<=reader.phaseLimit,'Whole cold product phase exceeds cap before reads');reader.used+=charge;
 const bodies=files.map(p=>{const raw=fs.readFileSync(path.join(directory,p.name));demand(raw.length===p.bytes&&sha(raw)===p.sha256,'Whole cold product differs from issued child acknowledgement');return raw;});
 const decoded=gunzipSync(bodies[2],{maxOutputLength:files[2].decoded_bytes});demand(decoded.length===files[2].decoded_bytes&&sha(decoded)===files[2].decoded_sha256,'Whole cold certificate decoded inverse differs');
 return {publication:JSON.parse(bodies[0]),facts:JSON.parse(bodies[1]),certificate:JSON.parse(decoded),encoded_sha256:sha(bodies[2]),decoded_sha256:sha(decoded)};
}
// Installed runtime/code were wholly authenticated by the real bootstrap once.
// Retain only those small identities between frames; new readers prospectively
// charge the same complete union plus every live carried byte before input opens.
function coldReader(native,context,selected,carriedBytes) {
 demand(Number.isSafeInteger(carriedBytes)&&carriedBytes>=0&&context&&Number.isSafeInteger(context.runtimeBytes)&&Number.isSafeInteger(context.executionBytes),'Incomplete installed-code/runtime/carry context');
 return new native.ImmutableReader(context.repo,selected,{runtimeBytes:context.runtimeBytes,executionBytes:context.executionBytes,gitExecutable:context.gitExecutable,metadataBytes:8388608+carriedBytes,outputBytes:FILE});
}
// Shared coordinate helpers reset their own metadata at each real acquisition
// boundary. A private subclass adds the enclosing invocation's complete custody
// and growing inventory to EVERY such phase, before any body can be opened.
// It preserves the ordinary reader's runtime, output, file, RSS and phase limits;
// no scientific helper body or historical programme identity is changed.
function coordinateFrameReader(native,helper,context,selected,carriedState) {
 demand(carriedState&&Object.keys(carriedState).sort().join(',')==='ack,code,context,lifecycle,receipts'
  &&carriedState.context===context&&Array.isArray(carriedState.code)&&Array.isArray(carriedState.ack)
  &&Array.isArray(carriedState.receipts)&&Array.isArray(carriedState.lifecycle),'Incomplete coordinate-frame carried metadata');
 demand(context&&Number.isSafeInteger(context.runtimeBytes)&&Number.isSafeInteger(context.executionBytes),'Incomplete coordinate-frame runtime context');
 class CoordinateFrameReader extends native.ImmutableReader {
  phase() {
   super.phase();
   const carry=2*helper.valueBytes({carriedState,inventory:[...this.inventory.values()]}).length+(this.coordinateResolverBytes??0);
   demand(Number.isSafeInteger(carry)&&carry>=0&&this.used+carry<this.phaseLimit,'Complete coordinate-frame carry exceeds phase before body opens');
   this.used+=carry;
  }
 }
 return new CoordinateFrameReader(context.repo,selected,{runtimeBytes:context.runtimeBytes,executionBytes:context.executionBytes,
  gitExecutable:context.gitExecutable,metadataBytes:8388608,outputBytes:FILE});
}
// The same genuine selected snapshot independently checks the persisted product
// against its issued acknowledgement. Publication readback, full owner/source
// joins and private receipt issuance remain mandatory; no serialized proof can
// manufacture a new selected authority.
function generatedColdSnapshot(native,helper,{repo,trusted,selected,destination,context,carriedState}) {
 fresh(destination);checkColdReclaimer();
 const reader=coordinateFrameReader(native,helper,context,selected,carriedState);
 const snapshot=timedStage('coordinate-selection',{selected},()=>native.loadSelection(reader));
 demand(snapshot&&snapshot.reader===reader&&reader.version===selected,'Selected cold side removed or rebound');
 const resolver=snapshot.geometrySources??new native.SelectedGeometrySources(snapshot);
 // Legacy source resolvers may own an image distinct from snapshot.image. The
 // shared join omits that view when resetting its own metadata. Carry the whole
 // resolver view numerically on every subsequent phase, without retaining it.
 Object.defineProperty(reader,'coordinateResolverBytes',{value:continuousResolverBytes(helper,resolver)});
 reclaimCompletedSource();
 const ack=publishCoordinateSnapshot(helper,{repo,trusted,selected,destination,context,code:carriedState.code,reader,resolver});
 reclaimCompletedSource();
 demand(snapshot.reader===reader&&resolver.reader===reader&&reader.version===selected,'Selected cold side removed or rebound');
 reader.metadataBytes=8388608+continuousSnapshotBytes(helper,snapshot,resolver)+2*helper.valueBytes(ack).length;
 reader.outputBytes=FILE;reader.phase();
 const product=readColdProduct(destination,ack,reader,helper);
 const certificate=helper.acceptColdCoordinateCertificate(resolver,product.certificate,{...product,expectedPublication:ack.publication});
 const receipt=helper.sealColdCoordinateCertificate(certificate,product);
 return {reader,snapshot,resolver,receipt,ack};
}
export function acquireCompleteColdSide(native,helper,options) {
 const {receipt,ack}=generatedColdSnapshot(native,helper,options);
 return {receipt,ack};
}
function continuousResolverBytes(helper,resolver) {
 // Also cover the legacy resolver's own image, which may not be snapshot.image.
 return 2*helper.valueBytes({bank:resolver.bank??null,paths:resolver.paths,sources:resolver.sources,release:resolver.release,
  image:resolver.image?{index:resolver.image.index,map:resolver.image.map}:null}).length;
}
function continuousSnapshotBytes(helper,snapshot,resolver) {
 return 2*snapshot.metadataBytes+continuousResolverBytes(helper,resolver);
}
// Private acquisition may live only inside a validating/projecting helper frame.
// Public completed helpers return custody and bounded projections, never readers.
function validatedColdSnapshot(native,helper,{repo,selected,parentRuntimePath,directory,ack,context,carriedState}) {
 demand(carriedState&&Object.keys(carriedState).sort().join(',')==='ack,code,context,lifecycle,receipts'&&carriedState.context===context&&Array.isArray(carriedState.code)&&Array.isArray(carriedState.lifecycle)&&Array.isArray(carriedState.ack)&&carriedState.ack.includes(ack)&&Array.isArray(carriedState.receipts),'Incomplete cold carried metadata');
 const carriedBytes=2*helper.valueBytes(carriedState).length;
 const reader=coldReader(native,context,selected,carriedBytes);
 reader.metadataBytes=8388608+carriedBytes;reader.outputBytes=FILE;reader.phase();
 const snapshot=timedStage('persisted-selection',{selected},()=>native.loadSelection(reader));
 demand(snapshot&&snapshot.reader===reader&&reader.version===selected,'Selected cold side removed or rebound');
 const resolver=snapshot.geometrySources??new native.SelectedGeometrySources(snapshot);
 reader.metadataBytes=8388608+carriedBytes+continuousSnapshotBytes(helper,snapshot,resolver);reader.phase();
 const product=readColdProduct(directory,ack,reader,helper);
 const certificate=helper.acceptColdCoordinateCertificate(resolver,product.certificate,{...product,expectedPublication:ack.publication});
 const receipt=helper.sealColdCoordinateCertificate(certificate,product);
 return {reader,snapshot,resolver,receipt};
}
export function validatePersistedColdSide(native,helper,options) {
 return validatedColdSnapshot(native,helper,options).receipt;
}
export function reopenCompleteColdPlan(native,helper,{repo,baseline,candidate,parentRuntimePath,stagePaths,ack,receipts,context,carriedBytes}) {
 demand(Number.isSafeInteger(carriedBytes)&&carriedBytes>=2*helper.valueBytes({context,ack,receipts}).length,'Incomplete reopened carry');
 const reader=coldReader(native,context,baseline,carriedBytes);
 reader.outputBytes=FILE;reader.metadataBytes=8388608+carriedBytes;reader.phase();
 const oldProduct=readColdProduct(stagePaths[0],ack[0],reader,helper);
 const oldCertificate=helper.reopenColdCoordinateCertificate(receipts[0],oldProduct);
 // Whole raw buffers ended in readColdProduct. Its parsed product is carried.
 const oldBytes=helper.valueBytes(oldProduct).length;
 reader.metadataBytes=8388608+carriedBytes+2*oldBytes;reader.phase();
 const newProduct=readColdProduct(stagePaths[1],ack[1],reader,helper);
 const newCertificate=helper.reopenColdCoordinateCertificate(receipts[1],newProduct);
 reader.metadataBytes=8388608+carriedBytes+2*(oldBytes+helper.valueBytes(newProduct).length);reader.phase();
 const plan=helper.selectedCertificateAffectedPlan(oldCertificate,newCertificate),required=new Set(plan.required_ids);
 const rows={baseline:oldCertificate.entries.filter(r=>required.has(r.id)),candidate:newCertificate.entries.filter(r=>required.has(r.id))};
 demand(rows.baseline.length===required.size&&rows.candidate.length===required.size,'Complete affected cold row closure differs');
 return {plan,rows,inputs:{baseline:oldCertificate.inputs,candidate:newCertificate.inputs},complete_phase_bytes:reader.used};
}
// The actual whole collection/raw buffers belong only to this completed frame.
// The enclosing same-vintage frame retains authenticated metadata and projected
// outputs, never a whole containing source or a cross-vintage reader cache.
function projectContinuousSource(helper,{reader,snapshot,resolver,name,receipt,rows,inputs}) {
 demand(helper.valueSha(snapshot.selection)===helper.valueSha(receipt.binding.selection)&&helper.valueSha(resolver.release)===helper.valueSha(receipt.binding.release)&&helper.valueSha(resolver.sources)===helper.valueSha(receipt.binding.sources)&&helper.valueSha(snapshot.owners)===receipt.binding.owners_sha256,'Reacquired selected source differs from complete cold binding');

 const actual=resolver.read(name),input=inputs.find(p=>p.path===name);
 demand(input&&actual.whole_sha256===input.whole_body_sha256,'Complete affected containing input differs from qualified certificate');
 const features={},inverse=[];
 for(const row of rows.filter(r=>r.source===name)){
  const feature=actual.collection.features[row.ordinal];
  demand(feature&&(feature.id??feature.properties?.id)===row.id&&helper.valueSha(feature)===row.whole_feature_sha256&&helper.valueSha(feature.geometry)===row.geometry_sha256,'Whole affected source record inverse differs');
  features[row.id]=feature;inverse.push({id:row.id,source:name,ordinal:row.ordinal,whole_source_sha256:actual.whole_sha256,whole_feature_sha256:row.whole_feature_sha256,geometry_sha256:row.geometry_sha256});
 }
 demand(helper.valueBytes({features,inverse}).length<=FILE,'Complete required source projection exceeds ordinary bound');
 return {features,inverse,complete_phase_bytes:reader.used,inputs:[...reader.inventory.values()]};
}
export function acquireContinuousSources(native,helper,{repo,selected,parentRuntimePath,names,receipt,rows,inputs,context,carriedBytes}) {
 demand(Array.isArray(names)&&names.every(name=>typeof name==='string')&&new Set(names).size===names.length,'Foreign/duplicate required containing source');
 demand(Number.isSafeInteger(carriedBytes)&&carriedBytes>=0,'Incomplete required-source carry');
 if(!names.length)return [];
 const reader=coldReader(native,context,selected,carriedBytes);
 reader.metadataBytes=8388608+carriedBytes;reader.outputBytes=FILE;reader.phase();
 const snapshot=timedStage('required-side-selection',{selected,sources:names.length},()=>native.loadSelection(reader));
 demand(snapshot&&snapshot.reader===reader&&reader.version===selected,'Required selected side removed or rebound');
 const resolver=snapshot.geometrySources??new native.SelectedGeometrySources(snapshot);
 return projectContinuousSources(helper,{reader,snapshot,resolver,selected,names,receipt,rows,inputs,carriedBytes});
}
// Both callers obtain this snapshot themselves through loadSelection. No public
// supplied-snapshot fast path or persistent cache can skip that authentication.
function projectContinuousSources(helper,{reader,snapshot,resolver,selected,names,receipt,rows,inputs,carriedBytes}) {
 const results=[];
 for(const name of names){
  demand(snapshot.reader===reader&&resolver.reader===reader&&reader.version===selected,'Required selected side removed or rebound');
  demand(resolver.paths.includes(name),'Foreign required containing source');
  // Count the complete retained snapshot plus every prior projection/receipt and
  // the growing reader inventory before admitting another actual whole source.
  const retainedBytes=2*helper.valueBytes({results,inventory:[...reader.inventory.values()]}).length;
  reader.metadataBytes=8388608+carriedBytes+continuousSnapshotBytes(helper,snapshot,resolver)+retainedBytes;reader.phase();
  const result=timedStage('required-source',{selected,source:name},()=>projectContinuousSource(helper,{reader,snapshot,resolver,name,receipt,rows,inputs}));
  results.push({source:name,...result});
 }
 demand(helper.valueBytes(results).length<=FILE,'Complete required-source side projection exceeds ordinary bound');
 return results;
}
export function acquireContinuousSource(native,helper,options) {
 const [result]=acquireContinuousSources(native,helper,{...options,names:[options.name]});
 const {source,...projection}=result;return projection;
}
// The one candidate snapshot survives validation, complete plan construction,
// and candidate projection in this explicit frame only. Every nested reader is
// charged for it and its complete inventory. Baseline acquisition starts only
// after this frame returns custody/required rows/projections, never a snapshot.
export function acquireCandidateContinuousSources(native,helper,{repo,baseline,candidate,parentRuntimePath,stagePaths,ack,context,code,baselineReceipt,lifecycle}) {
 demand(baselineReceipt?.facts?.selected_commit===baseline&&ack.length===2&&stagePaths.length===2,'Incomplete candidate-frame baseline custody');
 const receipts=[baselineReceipt],carriedState={context,code,ack,receipts,lifecycle};
 const {reader,snapshot,resolver,receipt}=validatedColdSnapshot(native,helper,{repo,selected:candidate,parentRuntimePath,directory:stagePaths[1],ack:ack[1],context,carriedState});
 return projectCandidateFrame(native,helper,{repo,baseline,candidate,parentRuntimePath,stagePaths,ack,context,code,receipts,lifecycle,reader,snapshot,resolver,receipt});
}
export function acquireCompleteCandidateSources(native,helper,{repo,trusted,baseline,candidate,parentRuntimePath,stagePaths,ack,context,code,baselineReceipt,lifecycle}) {
 demand(baselineReceipt?.facts?.selected_commit===baseline&&ack.length===1&&stagePaths.length===2,'Incomplete candidate-frame baseline custody');
 const receipts=[baselineReceipt],carriedState={context,code,ack,receipts,lifecycle};
 const completed=generatedColdSnapshot(native,helper,{repo,trusted,selected:candidate,destination:stagePaths[1],context,carriedState});
 const {ack:issued,...frame}=completed;ack.push(issued);
 return projectCandidateFrame(native,helper,{repo,baseline,candidate,parentRuntimePath,stagePaths,ack,context,code,receipts,lifecycle,...frame});
}
function projectCandidateFrame(native,helper,{repo,baseline,candidate,parentRuntimePath,stagePaths,ack,context,code,receipts,lifecycle,reader,snapshot,resolver,receipt}) {
 receipts.push(receipt);
 const stages=[...lifecycle,{kind:'complete-snapshot-bound-cold-validation',vintage:'candidate',complete_phase_bytes:receipt.complete_phase_bytes}];
 const custodyBytes=value=>2*helper.valueBytes(value).length;
 const snapshotCarry=continuousSnapshotBytes(helper,snapshot,resolver)+custodyBytes([...reader.inventory.values()]);
 const closure=timedStage('affected-plan',{},()=>reopenCompleteColdPlan(native,helper,{repo,baseline,candidate,parentRuntimePath,stagePaths,ack,receipts,context,
  carriedBytes:custodyBytes({context,code,ack,receipts,lifecycle:stages})+snapshotCarry}));
 stages.push({kind:'complete-both-vintage-neighbor-plan',complete_phase_bytes:closure.complete_phase_bytes});
 const results=projectContinuousSources(helper,{reader,snapshot,resolver,selected:candidate,names:closure.plan.source_paths.candidate,receipt,rows:closure.rows.candidate,inputs:closure.inputs.candidate,
  carriedBytes:custodyBytes({context,code,ack,receipts,closure,lifecycle:stages})});
 return {receipts,lifecycle:stages,closure,results};
}
export async function continuousOperandsStage(repo,trusted,baseline,candidate,destination,parentRuntimePath){
 demand(commit(baseline)&&commit(candidate),'Missing immutable selected comparison commits');destination=path.resolve(destination);fresh(destination);checkColdReclaimer();const code=guard(repo,trusted);
 const native=await import('../../../scripts/check-effective-geographic-regression.mjs'),helper=await import('./selected-neighbor-prevention.mjs');
 let startup=native.selectedBootstrap(repo,baseline,candidate,{parentRuntimePath});
 if(mayUseNonAdditiveShortcut(startup.beforeReader,startup.afterReader)){
  let before=timedStage('shortcut-baseline-selection',{selected:baseline},()=>native.loadSelection(startup.beforeReader));
  demand(before,'Selected baseline removed or unsupported');startup.afterReader.metadataBytes=8388608+2*before.metadataBytes;startup.afterReader.phase();
  let after=timedStage('shortcut-candidate-selection',{selected:candidate},()=>native.loadSelection(startup.afterReader));demand(after,'Selected candidate removed or unsupported');
  const oldResolver=before.geometrySources??new native.SelectedGeometrySources(before),newResolver=after.geometrySources??new native.SelectedGeometrySources(after);
  const normal=r=>r.sources.map(p=>({path:p.logical_path??p.path,mode:p.mode,bytes:p.decoded_bytes??p.bytes,sha256:p.decoded_sha256??p.sha256??p.git_blob_oid}));
  if(!before.additive&&!after.additive&&helper.valueSha(normal(oldResolver))===helper.valueSha(normal(newResolver))&&helper.valueSha(before.owners)===helper.valueSha(after.owners))return {version:1,kind:'trusted-selected-continuous-comparison-v1',status:'selected-sources-unchanged',changed_ids:[],complete_owners:before.owners.length,candidate_code_executed:false};
 }
 // Bootstrap selectors and any non-additive shortcut snapshots end here. Only
 // runtime context survives into independent complete coordinate acquisitions.
 const context=bootstrapContext(repo,startup);
 startup=null;reclaimCompletedSource();
 fs.mkdirSync(destination);const stagePaths=[path.join(destination,'baseline'),path.join(destination,'candidate')],ack=[];
 const custodyBytes=value=>2*helper.valueBytes(value).length;
 const baselineSide=acquireCompleteColdSide(native,helper,{repo,trusted,selected:baseline,destination:stagePaths[0],context,
  carriedState:{context,code,ack,receipts:[],lifecycle:[]}});
 ack.push(baselineSide.ack);const baselineReceipt=baselineSide.receipt;
 // The baseline frame has ended: no snapshot or source resolver survives here.
 reclaimCompletedSource();
 let completed=acquireCompleteCandidateSources(native,helper,{repo,trusted,baseline,candidate,parentRuntimePath,stagePaths,ack,context,code,baselineReceipt,
  lifecycle:[{kind:'complete-snapshot-bound-cold-validation',vintage:'baseline',complete_phase_bytes:baselineReceipt.complete_phase_bytes}]});
 const {receipts,lifecycle,closure}=completed;
 let candidateResults=completed.results;completed=null;reclaimCompletedSource();
 // Both whole certificates remain authenticated persisted outputs. Their full
// scan has finished; retain every required row, release only unused live rows.
 const {plan,rows,inputs}=closure,outputs={baseline:{},candidate:{}},inverse=[];
 process.stderr.write(JSON.stringify({selected_continuous_stage:'required-source-count',baseline:plan.source_paths.baseline.length,candidate:plan.source_paths.candidate.length,changed_owners:plan.changed_ids.length,required_owners:plan.required_ids.length})+'\n');
 for(const [vintage,selected,i]of [['baseline',baseline,0],['candidate',candidate,1]]){
  const results=vintage==='candidate'?candidateResults:acquireContinuousSources(native,helper,{repo,selected,parentRuntimePath,names:plan.source_paths[vintage],receipt:receipts[i],rows:rows[vintage],inputs:inputs[vintage],context,
   carriedBytes:custodyBytes({context,code,ack,receipts,plan,rows,inputs,outputs,inverse,lifecycle,candidateResults})});
  for(const result of results){
   Object.assign(outputs[vintage],result.features);inverse.push(...result.inverse.map(r=>({vintage,...r})));
   lifecycle.push({kind:'complete-required-containing-source',vintage,source:result.source,complete_phase_bytes:result.complete_phase_bytes,inputs:result.inputs});
  }
  demand(Object.keys(outputs[vintage]).sort().join('\0')===plan.required_ids.join('\0'),'Affected operand closure omitted owner');
 }
 candidateResults=null;
 const effective_additions={baseline:receipts[0].effective_additions,candidate:receipts[1].effective_additions};
 const operands=helper.valueBytes({version:1,kind:'complete-selected-continuous-operands-v1',plan,effective_additions,...outputs}),encoded=gzipSync(operands,{level:9,mtime:0});
 const facts=helper.valueBytes({version:1,kind:'trusted-selected-continuous-comparison-v1',executing_commit:trusted,baseline_commit:baseline,candidate_commit:candidate,execution_code:code,runtime:context.identities,source_stages:ack.map(a=>a.publication),complete_cold_custody:receipts,lifecycle,plan,inverse,candidate_code_executed:false});
 demand(operands.length+encoded.length+2*facts.length<FILE,'Complete affected output reserve exceeded; no scope clipping');guard(repo,trusted);
 const finalReader=coldReader(native,context,baseline,custodyBytes({context,code,ack,receipts,plan,rows,inputs,outputs,inverse,lifecycle}));
 for(const [name,body]of [['operands.json.gz',encoded],['facts.json',facts]])fs.writeFileSync(path.join(destination,name),body,{flag:'wx',mode:0o644});
 const publication={version:1,complete:true,kind:'trusted-selected-continuous-comparison-v1',operands:{path:'operands.json.gz',bytes:encoded.length,sha256:sha(encoded),decoded_bytes:operands.length,decoded_sha256:sha(operands)},facts:{path:'facts.json',bytes:facts.length,sha256:sha(facts)}};fs.writeFileSync(path.join(destination,'publication.json'),helper.valueBytes(publication),{flag:'wx',mode:0o644});
 return {version:1,kind:publication.kind,status:plan.changed_ids.length?'selected-operands-complete':'no-selected-footprint-change',publication,changed_ids:plan.changed_ids,complete_owners:receipts[0].facts.complete_owners,affected_ids:plan.required_ids,candidate_code_executed:false};
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 const [operation,repo,trusted,...args]=process.argv.slice(2);
 let result;if(operation==='coordinate')result=await coordinateStage(repo,trusted,...args);else if(operation==='continuous')result=await continuousOperandsStage(repo,trusted,...args);else throw Error('Unsupported cold selected operation');
 process.stdout.write(JSON.stringify(result)+'\n');
}
