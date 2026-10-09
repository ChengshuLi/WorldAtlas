// Independently reviewed external continuation; not a candidate authority issuer.
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {gzipSync} from 'node:zlib';
import {pathToFileURL} from 'node:url';
const [planPath,planSha]=process.argv.slice(2);
const FILE=33554432,PHASE=268435456,sha=b=>createHash('sha256').update(b).digest('hex'),need=(v,m)=>{if(!v)throw Error(m);};
need(process.argv.length===4&&!process.env.NODE_OPTIONS&&!process.env.NODE_PATH&&process.execArgv.length===0,'Exact reviewed external continuation argv/environment required');
function whole(pin){const s=fs.lstatSync(pin.path);need(s.isFile()&&!s.isSymbolicLink()&&s.size===pin.bytes&&s.size<=FILE,'Whole ordinary continuation operand cap/type/size');const b=fs.readFileSync(pin.path);need(sha(b)===pin.sha256,'Whole original continuation custody differs');return b;}
const plan=JSON.parse(whole({path:planPath,bytes:fs.statSync(planPath).size,sha256:planSha}));
need(plan.version===1&&plan.kind==='reviewed-original-cold-product-continuation-v1'&&plan.producer_commit==='417187c6a9f68561f3c73a9bf2808c29bf598328','Unknown original completion scope');
need(plan.runtime_and_code_bytes+2*fs.statSync(planPath).size+2*plan.maximum_initial_whole_bytes+8*1048576+33554432<=PHASE,'Complete prospective original custody admission');
const review=JSON.parse(whole(plan.reuse_review));need(review.kind==='independent-retained-cold-child-reuse-review'&&review.producer_commit===plan.producer_commit&&review.parent_status==='failed, unqualified; retained unchanged','No independently reviewed original child completion proof');
for(const pin of review.products)whole(pin);
const oldReceipt=JSON.parse(whole(review.products.find(p=>p.path.endsWith('/operating-receipt.json')))),issued=JSON.parse(whole(review.products.find(p=>p.path.endsWith('/program/issued-command.json'))));
need(oldReceipt.exit_code===1&&!oldReceipt.operating_admission_qualified&&oldReceipt.natural_terminal_owned_processes_absent&&oldReceipt.code_head===plan.producer_commit&&oldReceipt.baseline===plan.baseline&&oldReceipt.candidate===plan.candidate,'Original failed parent or scope relabel');
need(JSON.stringify(oldReceipt.source_pre_use)===JSON.stringify(oldReceipt.source_post_use)&&JSON.stringify(oldReceipt.source_pre_use)===JSON.stringify(issued.source_files),'Original actual executed source pre/post custody differs');
for(const row of issued.source_files){const archived={path:path.join(path.dirname(review.products.find(p=>p.path.endsWith('/program/issued-command.json')).path),row.path),bytes:row.bytes,sha256:row.sha256},b=whole(archived);need(createHash('sha1').update(Buffer.from('blob '+b.length+'\0')).update(b).digest('hex')===row.git_blob_oid,'Original full Git body inverse differs');}
for(const pin of plan.current_code)whole(pin);
const importRoot=relative=>import(pathToFileURL(path.join(plan.repo,relative)).href),native=await importRoot('scripts/check-effective-geographic-regression.mjs'),helper=await importRoot('coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs'),entry=await importRoot('coordination/engineering/selected-geography-effective-prevention-20261009/selected-continuous-entry.mjs');
const startup=native.selectedBootstrap(plan.repo,plan.baseline,plan.candidate,{parentRuntimePath:plan.parent_python});
const context={repo:plan.repo,runtimeBytes:startup.beforeReader.runtimeBytes,executionBytes:startup.beforeReader.executionBytes+plan.external_driver_bytes,gitExecutable:startup.beforeReader.gitExecutable,identities:startup.identities,original_execution_custody:{review,receipt:oldReceipt,issued},current_external_driver:plan.driver_pin,continuation_plan:plan};
need(context.runtimeBytes+context.executionBytes<=plan.runtime_and_code_bytes,'Actual continuation installed union exceeds prospective bound');
const code=plan.current_code,stagePaths=plan.stage_paths,ack=stagePaths.map(directory=>{
 const publication=JSON.parse(whole(review.products.find(p=>p.path===path.join(directory,'publication.json')))),facts=JSON.parse(whole(review.products.find(p=>p.path===path.join(directory,'facts.json'))));
 need(facts.executing_commit===plan.producer_commit&&facts.complete_owners===49625&&facts.complete_sources===36&&publication.complete===true,'Original child scope/incomplete publication');
 return {publication,complete_owners:facts.complete_owners,complete_sources:facts.complete_sources,candidate_code_executed:false};
});
const receipts=[],lifecycle=[],carry=v=>2*helper.valueBytes(v).length;
for(const [i,selected]of [plan.baseline,plan.candidate].entries()){const receipt=entry.validatePersistedColdSide(native,helper,{repo:plan.repo,selected,directory:stagePaths[i],ack:ack[i],context,carriedState:{context,code,ack,receipts,lifecycle}});receipts.push(receipt);lifecycle.push({kind:'current-consumer-original-cold-validation',vintage:i?'candidate':'baseline',complete_phase_bytes:receipt.complete_phase_bytes});}
const closure=entry.reopenCompleteColdPlan(native,helper,{repo:plan.repo,baseline:plan.baseline,candidate:plan.candidate,stagePaths,ack,receipts,context,carriedBytes:carry({context,code,ack,receipts,lifecycle})}),{plan:neighborPlan,rows,inputs}=closure;
lifecycle.push({kind:'complete-both-vintage-neighbor-plan',complete_phase_bytes:closure.complete_phase_bytes});
const outputs={baseline:{},candidate:{}},inverse=[];
for(const [vintage,selected,i]of [['baseline',plan.baseline,0],['candidate',plan.candidate,1]]){for(const name of neighborPlan.source_paths[vintage]){const result=entry.acquireContinuousSource(native,helper,{repo:plan.repo,selected,name,receipt:receipts[i],rows:rows[vintage],inputs:inputs[vintage],context,carriedBytes:carry({context,code,ack,receipts,plan:neighborPlan,rows,inputs,outputs,inverse,lifecycle})});Object.assign(outputs[vintage],result.features);inverse.push(...result.inverse.map(r=>({vintage,...r})));lifecycle.push({kind:'complete-required-containing-source',vintage,source:name,complete_phase_bytes:result.complete_phase_bytes,inputs:result.inputs});}need(Object.keys(outputs[vintage]).sort().join('\0')===neighborPlan.required_ids.join('\0'),'Required affected owner omitted');}
const destination=plan.destination;need(!fs.existsSync(destination),'Fresh continuation output required');
const operands=helper.valueBytes({version:1,kind:'complete-selected-continuous-operands-v1',plan:neighborPlan,effective_additions:{baseline:receipts[0].effective_additions,candidate:receipts[1].effective_additions},...outputs}),encoded=gzipSync(operands,{level:9,mtime:0}),facts=helper.valueBytes({version:1,kind:'trusted-selected-continuous-comparison-v1',executing_commit:plan.consumer_commit,producer_commit:plan.producer_commit,source_stage_vintage:'original417-completed-child-return-values-reconstructed; raw-stdout-not-retained',original_parent_status:'failed-unqualified-preserved',baseline_commit:plan.baseline,candidate_commit:plan.candidate,execution_code:code,runtime:context.identities,source_stages:ack.map(a=>a.publication),complete_cold_custody:receipts,lifecycle,plan:neighborPlan,inverse,candidate_code_executed:false});
need(operands.length+encoded.length+2*facts.length<FILE,'Complete affected output reserve');
new native.ImmutableReader(plan.repo,plan.baseline,{runtimeBytes:context.runtimeBytes,executionBytes:context.executionBytes,gitExecutable:context.gitExecutable,metadataBytes:8388608+carry({context,code,ack,receipts,plan:neighborPlan,rows,inputs,outputs,inverse,lifecycle})});
fs.mkdirSync(destination);for(const [name,b]of [['operands.json.gz',encoded],['facts.json',facts]])fs.writeFileSync(path.join(destination,name),b,{flag:'wx',mode:0o644});
const publication={version:1,complete:true,kind:'trusted-selected-continuous-comparison-v1',operands:{path:'operands.json.gz',bytes:encoded.length,sha256:sha(encoded),decoded_bytes:operands.length,decoded_sha256:sha(operands)},facts:{path:'facts.json',bytes:facts.length,sha256:sha(facts)}};fs.writeFileSync(path.join(destination,'publication.json'),helper.valueBytes(publication),{flag:'wx',mode:0o644});
console.log(JSON.stringify({publication,producer_commit:plan.producer_commit,consumer_commit:plan.consumer_commit,changed_ids:neighborPlan.changed_ids,affected_ids:neighborPlan.required_ids,candidate_code_executed:false,scientific_requalification:false}));
