// Trusted cold acquisition only. Proposed commits are data, never imported code.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {gzipSync,gunzipSync} from 'node:zlib';
const FILE=33554432,PHASE=268435456,ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../..');
const P='coordination/engineering/selected-geography-effective-prevention-20261009/';
const CODE=[P+'selected-continuous-entry.mjs',P+'selected-neighbor-prevention.mjs','scripts/check-effective-geographic-regression.mjs','src/ownership-codec.js','scripts/run-geographic-check.py','scripts/check-geographic-regression.py','scripts/evidence/immutable.py','scripts/evidence/geometry.py','scripts/ellipsoidal_area.py','requirements.txt'];
const demand=(v,m)=>{if(!v)throw Error(m);},sha=b=>createHash('sha256').update(b).digest('hex');
const coldGc=globalThis.gc;
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
 demand(stats.reduce((n,r)=>n+r.s.size,0)+fs.statSync(process.execPath).size+8388608+FILE<PHASE,'Cold code/runtime admission before code body opens');
 return stats.map(({name,f,s})=>{const row=git('ls-tree','-z',trusted,'--',name).toString();demand(/^100(644|755) blob [a-f0-9]{40}\t/.test(row)&&row.endsWith('\t'+name+'\0'),'Unbound cold execution code');const [mode,,oid]=row.slice(0,row.indexOf('\t')).split(' ');demand(Number(git('cat-file','-s',oid))===s.size,'Cold code size differs');const local=fs.readFileSync(f),raw=git('cat-file','blob',oid);demand(local.equals(raw)&&(s.mode&0o777)===(mode==='100755'?0o755:0o644),'Cold code whole body/mode differs');return {commit:trusted,path:name,mode,git_blob_oid:oid,bytes:raw.length,sha256:sha(raw)};});
}
export async function coordinateStage(repo,trusted,selected,destination,parentRuntimePath){
 demand(commit(selected),'Missing immutable selected input commit');destination=path.resolve(destination);fresh(destination);checkColdReclaimer();
 const code=guard(repo,trusted);
 const native=await import('../../../scripts/check-effective-geographic-regression.mjs');
 const helper=await import('./selected-neighbor-prevention.mjs');
 const startup=native.selectedBootstrap(repo,selected,selected,{parentRuntimePath});
 startup.beforeReader.outputBytes=FILE;startup.beforeReader.phase();
 const snapshot=native.loadSelection(startup.beforeReader);demand(snapshot,'Selected continuous certificate requires a committed native selection');
 // Completed metadata helper frames no longer retain raw decoded containers.
 // The complete authenticated snapshot remains live and charged below.
 checkColdReclaimer();coldGc();
 const resolver=snapshot.geometrySources??new native.SelectedGeometrySources(snapshot),shards=[];
 // The issued footprint value is once-qualified historical authority. This
 // separate certificate authenticates every actual selected whole source body,
 // full unique owner roster and per-record pointsets; it does not recompute the
 // legacy world digest using a source traversal that was never its method.
 for(const name of resolver.paths){shards.push(helper.selectedCoordinateShard(resolver,[name],{priorShards:shards}));
  // Only compact immutable certificates survive here. The complete original
  // FeatureCollection has left the helper frame; reclaim it before next input.
  reclaimCompletedSource();
 }
 const certificate=helper.joinSelectedCoordinateCertificate(resolver,shards),decoded=helper.valueBytes(certificate);
 demand(decoded.length<=FILE,'Complete certificate ordinary decoded cap');
 const encoded=gzipSync(decoded,{level:9,mtime:0});
 const facts={version:1,kind:'trusted-selected-coordinate-stage-v1',executing_commit:trusted,selected_commit:selected,execution_code:code,
  runtime:startup.identities,runtime_argv:process.execArgv,source_lifecycle:'whole-containing-body-authenticate-extract-discard-native-gc',source_certificate_domain:'complete-selected-source-pointsets:v1',historical_footprint_authority:{value:resolver.release.footprints_sha256,release:resolver.release,recomputed:false},binding:certificate.binding,complete_owners:certificate.entries.length,complete_sources:resolver.paths.length,
  inputs:[...startup.beforeReader.inventory.values()],acquisition_phases:shards.flatMap(s=>s.phases),join_phase_bytes:certificate.complete_phase_bytes,
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
 const charge=files.reduce((n,p)=>n+p.bytes+(p.decoded_bytes??0),0);demand(reader.used+charge<=PHASE,'Whole cold product phase exceeds cap before reads');reader.used+=charge;
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
// A completed helper frame returns custody, never a selected snapshot/image.
export function validatePersistedColdSide(native,helper,{repo,selected,parentRuntimePath,directory,ack,context,carriedState}) {
 demand(carriedState&&Object.keys(carriedState).sort().join(',')==='ack,code,context,lifecycle,receipts'&&carriedState.context===context&&Array.isArray(carriedState.code)&&Array.isArray(carriedState.lifecycle)&&Array.isArray(carriedState.ack)&&carriedState.ack.includes(ack)&&Array.isArray(carriedState.receipts),'Incomplete cold carried metadata');
 const carriedBytes=2*helper.valueBytes(carriedState).length;
 const reader=coldReader(native,context,selected,carriedBytes);
 reader.metadataBytes=8388608+carriedBytes;reader.outputBytes=FILE;reader.phase();
 const snapshot=native.loadSelection(reader);demand(snapshot,'Selected cold side removed or unsupported');
 const resolver=snapshot.geometrySources??new native.SelectedGeometrySources(snapshot);
 reader.metadataBytes=8388608+carriedBytes+2*snapshot.metadataBytes;reader.phase();
 const product=readColdProduct(directory,ack,reader,helper);
 const certificate=helper.acceptColdCoordinateCertificate(resolver,product.certificate,{...product,expectedPublication:ack.publication});
 return helper.sealColdCoordinateCertificate(certificate,product);
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
function acquireContinuousSource(native,helper,{repo,selected,parentRuntimePath,name,receipt,rows,inputs,context,carriedBytes}) {
 const reader=coldReader(native,context,selected,carriedBytes);
 reader.metadataBytes=8388608+carriedBytes;reader.outputBytes=FILE;reader.phase();
 const snapshot=native.loadSelection(reader);demand(snapshot,'Required selected side removed');
 const resolver=snapshot.geometrySources??new native.SelectedGeometrySources(snapshot);
 demand(helper.valueSha(snapshot.selection)===helper.valueSha(receipt.binding.selection)&&helper.valueSha(resolver.release)===helper.valueSha(receipt.binding.release)&&helper.valueSha(resolver.sources)===helper.valueSha(receipt.binding.sources)&&helper.valueSha(snapshot.owners)===receipt.binding.owners_sha256,'Reacquired selected source differs from complete cold binding');
 reader.metadataBytes=8388608+carriedBytes+2*snapshot.metadataBytes;reader.phase();
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
export async function continuousOperandsStage(repo,trusted,baseline,candidate,destination,parentRuntimePath){
 demand(commit(baseline)&&commit(candidate),'Missing immutable selected comparison commits');destination=path.resolve(destination);fresh(destination);const code=guard(repo,trusted);
 const native=await import('../../../scripts/check-effective-geographic-regression.mjs'),helper=await import('./selected-neighbor-prevention.mjs');
 let startup=native.selectedBootstrap(repo,baseline,candidate,{parentRuntimePath}),before=native.loadSelection(startup.beforeReader);
 demand(before,'Selected baseline removed or unsupported');startup.afterReader.metadataBytes=8388608+2*before.metadataBytes;startup.afterReader.phase();let after=native.loadSelection(startup.afterReader);demand(after,'Selected candidate removed or unsupported');
 let oldResolver=before.geometrySources??new native.SelectedGeometrySources(before),newResolver=after.geometrySources??new native.SelectedGeometrySources(after);
 const normal=r=>r.sources.map(p=>({path:p.logical_path??p.path,mode:p.mode,bytes:p.decoded_bytes??p.bytes,sha256:p.decoded_sha256??p.sha256??p.git_blob_oid}));
 if(!before.additive&&!after.additive&&helper.valueSha(normal(oldResolver))===helper.valueSha(normal(newResolver))&&helper.valueSha(before.owners)===helper.valueSha(after.owners))return {version:1,kind:'trusted-selected-continuous-comparison-v1',status:'selected-sources-unchanged',changed_ids:[],complete_owners:before.owners.length,candidate_code_executed:false};
 // The bootstrap metadata is discarded before independent cold acquisitions.
 // Only the issued child acknowledgements survive, not a global geometry image.
 const context={repo,runtimeBytes:startup.beforeReader.runtimeBytes,executionBytes:startup.beforeReader.executionBytes,gitExecutable:startup.beforeReader.gitExecutable,identities:startup.identities};
 before=null;after=null;oldResolver=null;newResolver=null;startup=null;
 fs.mkdirSync(destination);const stagePaths=[path.join(destination,'baseline'),path.join(destination,'candidate')],ack=[];
 const env={...process.env};delete env.NODE_OPTIONS;delete env.NODE_PATH;
 for(const [i,selected]of [baseline,candidate].entries()){
  const raw=execFileSync(process.execPath,['--expose-gc',fileURLToPath(import.meta.url),'coordinate',repo,trusted,selected,stagePaths[i],...(parentRuntimePath?[parentRuntimePath]:[])],{env,maxBuffer:1048576,stdio:['ignore','pipe','pipe']});const value=JSON.parse(raw);demand(value.publication?.complete===true,'Cold coordinate child lacks complete acknowledgement');ack.push(value);
 }
 const custodyBytes=value=>2*helper.valueBytes(value).length;
 const receipts=[],lifecycle=[];
 for(const [i,selected]of [baseline,candidate].entries()){
  const receipt=validatePersistedColdSide(native,helper,{repo,selected,parentRuntimePath,directory:stagePaths[i],ack:ack[i],context,carriedState:{context,code,ack,receipts,lifecycle}});
  receipts.push(receipt);lifecycle.push({kind:'complete-snapshot-bound-cold-validation',vintage:i?'candidate':'baseline',complete_phase_bytes:receipt.complete_phase_bytes});
 }
 const closure=reopenCompleteColdPlan(native,helper,{repo,baseline,candidate,parentRuntimePath,stagePaths,ack,receipts,context,carriedBytes:custodyBytes({code,ack,receipts,lifecycle})});
 lifecycle.push({kind:'complete-both-vintage-neighbor-plan',complete_phase_bytes:closure.complete_phase_bytes});
 // Both whole certificates remain authenticated persisted outputs. Their full
// scan has finished; retain every required row, release only unused live rows.
 const {plan,rows,inputs}=closure,outputs={baseline:{},candidate:{}},inverse=[];
 for(const [vintage,selected,i]of [['baseline',baseline,0],['candidate',candidate,1]]){
  for(const name of plan.source_paths[vintage]){
   const result=acquireContinuousSource(native,helper,{repo,selected,parentRuntimePath,name,receipt:receipts[i],rows:rows[vintage],inputs:inputs[vintage],context,carriedBytes:custodyBytes({context,code,ack,receipts,plan,rows,inputs,outputs,inverse,lifecycle})});
   Object.assign(outputs[vintage],result.features);inverse.push(...result.inverse.map(r=>({vintage,...r})));
   lifecycle.push({kind:'complete-required-containing-source',vintage,source:name,complete_phase_bytes:result.complete_phase_bytes,inputs:result.inputs});
  }
  demand(Object.keys(outputs[vintage]).sort().join('\0')===plan.required_ids.join('\0'),'Affected operand closure omitted owner');
 }
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
