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
export function checkColdReclaimer(){demand(process.execArgv.includes('--expose-gc')&&typeof coldGc==='function'&&globalThis.gc===coldGc&&Function.prototype.toString.call(coldGc).includes('[native code]'),'Cold whole-source acquisition requires authenticated native GC entry');}
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
 before=null;after=null;oldResolver=null;newResolver=null;startup=null;
 fs.mkdirSync(destination);const stagePaths=[path.join(destination,'baseline'),path.join(destination,'candidate')],ack=[];
 const env={...process.env};delete env.NODE_OPTIONS;delete env.NODE_PATH;
 for(const [i,selected]of [baseline,candidate].entries()){
  const raw=execFileSync(process.execPath,['--expose-gc',fileURLToPath(import.meta.url),'coordinate',repo,trusted,selected,stagePaths[i],...(parentRuntimePath?[parentRuntimePath]:[])],{env,maxBuffer:1048576,stdio:['ignore','pipe','pipe']});const value=JSON.parse(raw);demand(value.publication?.complete===true,'Cold coordinate child lacks complete acknowledgement');ack.push(value);
 }
 startup=native.selectedBootstrap(repo,baseline,candidate,{parentRuntimePath});before=native.loadSelection(startup.beforeReader);startup.afterReader.metadataBytes=8388608+2*before.metadataBytes;startup.afterReader.phase();after=native.loadSelection(startup.afterReader);
 oldResolver=before.geometrySources??new native.SelectedGeometrySources(before);newResolver=after.geometrySources??new native.SelectedGeometrySources(after);
 const reader=startup.beforeReader;reader.outputBytes=FILE;reader.metadataBytes=8388608+2*(before.metadataBytes+after.metadataBytes);reader.phase();
 const oldProduct=readColdProduct(stagePaths[0],ack[0],reader,helper),newProduct=readColdProduct(stagePaths[1],ack[1],reader,helper);
 const oldCertificate=helper.acceptColdCoordinateCertificate(oldResolver,oldProduct.certificate,{...oldProduct,expectedPublication:ack[0].publication}),newCertificate=helper.acceptColdCoordinateCertificate(newResolver,newProduct.certificate,{...newProduct,expectedPublication:ack[1].publication});
 const plan=helper.selectedCertificateAffectedPlan(oldCertificate,newCertificate),outputs={baseline:{},candidate:{}},inverse=[];
 // Certificates/metadata stay live; each whole-source acquisition is genuinely
 // detached from the previous source body, with all retained outputs charged.
 const retained=helper.valueBytes({oldCertificate,newCertificate,plan}).length+before.metadataBytes+after.metadataBytes;
 for(const [vintage,resolver,certificate]of [['baseline',oldResolver,oldCertificate],['candidate',newResolver,newCertificate]]){
  const required=new Map(certificate.entries.filter(r=>plan.required_ids.includes(r.id)).map(r=>[r.id,r]));
  for(const name of plan.source_paths[vintage]){
   const r=resolver.reader;r.outputBytes=FILE;r.metadataBytes=8388608+retained+helper.valueBytes({outputs,inverse}).length;r.phase();const actual=resolver.read(name);demand(actual.whole_sha256===certificate.inputs.find(p=>p.path===name)?.whole_body_sha256,'Complete affected containing input differs from qualified certificate');
   for(const [id,row]of required)if(row.source===name){const feature=actual.collection.features[row.ordinal];demand(feature&&(feature.id??feature.properties?.id)===id&&helper.valueSha(feature)===row.whole_feature_sha256&&helper.valueSha(feature.geometry)===row.geometry_sha256,'Whole affected source record inverse differs');outputs[vintage][id]=feature;inverse.push({vintage,id,source:name,ordinal:row.ordinal,whole_source_sha256:actual.whole_sha256,whole_feature_sha256:row.whole_feature_sha256,geometry_sha256:row.geometry_sha256});}
  }
  demand(Object.keys(outputs[vintage]).sort().join('\0')===plan.required_ids.join('\0'),'Affected operand closure omitted owner');
 }
 const effective_additions={baseline:before.additive?.normalized_rows??[],candidate:after.additive?.normalized_rows??[]};
 const operands=helper.valueBytes({version:1,kind:'complete-selected-continuous-operands-v1',plan,effective_additions,...outputs}),encoded=gzipSync(operands,{level:9,mtime:0});
 const facts=helper.valueBytes({version:1,kind:'trusted-selected-continuous-comparison-v1',executing_commit:trusted,baseline_commit:baseline,candidate_commit:candidate,execution_code:code,runtime:startup.identities,source_stages:ack.map(a=>a.publication),plan,inverse,candidate_code_executed:false});
 demand(operands.length+encoded.length+2*facts.length<FILE,'Complete affected output reserve exceeded; no scope clipping');guard(repo,trusted);
 for(const [name,body]of [['operands.json.gz',encoded],['facts.json',facts]])fs.writeFileSync(path.join(destination,name),body,{flag:'wx',mode:0o644});
 const publication={version:1,complete:true,kind:'trusted-selected-continuous-comparison-v1',operands:{path:'operands.json.gz',bytes:encoded.length,sha256:sha(encoded),decoded_bytes:operands.length,decoded_sha256:sha(operands)},facts:{path:'facts.json',bytes:facts.length,sha256:sha(facts)}};fs.writeFileSync(path.join(destination,'publication.json'),helper.valueBytes(publication),{flag:'wx',mode:0o644});
 return {version:1,kind:publication.kind,status:plan.changed_ids.length?'selected-operands-complete':'no-selected-footprint-change',publication,changed_ids:plan.changed_ids,complete_owners:oldCertificate.entries.length,affected_ids:plan.required_ids,candidate_code_executed:false};
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 const [operation,repo,trusted,...args]=process.argv.slice(2);
 let result;if(operation==='coordinate')result=await coordinateStage(repo,trusted,...args);else if(operation==='continuous')result=await continuousOperandsStage(repo,trusted,...args);else throw Error('Unsupported cold selected operation');
 process.stdout.write(JSON.stringify(result)+'\n');
}
