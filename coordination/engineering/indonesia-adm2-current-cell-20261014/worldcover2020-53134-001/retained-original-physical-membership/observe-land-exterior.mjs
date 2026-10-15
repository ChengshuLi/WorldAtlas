// Task invocation of accepted complete-operand APIs; no authority is produced.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {witnessCellEffects,validateWitnessGeometry,nativePolygonIntervals} from '../../idn-101610-local-delivery-preparation-001/accepted-b0b40-code/src/native-grid.js';
import {ImmutableReader,processingAllowance} from '../../idn-101610-local-delivery-preparation-001/accepted-b0b40-code/scripts/check-effective-geographic-regression.mjs';

const here=path.dirname(fileURLToPath(import.meta.url)),size=262166;
const need=(v,m)=>{if(!v)throw Error(m);},sha=b=>createHash('sha256').update(b).digest('hex');
need(process.argv.length===5&&process.argv[2]==='--observe-land-exterior','Require the reviewed observation interface');
need(!process.execArgv.length&&!process.env.NODE_OPTIONS&&!process.env.NODE_PATH,'Unexpected Node options');
const configPath=path.resolve(process.argv[3]),output=path.resolve(process.argv[4]);
need(configPath===path.join(here,'observation-config.json'),'Use the reviewed observation config');
need(output.startsWith(here+path.sep)&&!fs.existsSync(output),'Require fresh owned observation output');
const configRaw=fs.readFileSync(configPath),config=JSON.parse(configRaw);
need(configRaw.length===config.config_bytes&&fs.statSync(fileURLToPath(import.meta.url)).size===config.caller_bytes,'Observation proposal changed');
need(fs.statSync(process.execPath).size===config.runtime_bytes,'Runtime changed; recalculate complete bound');
const availableBytes=process.availableMemory(),currentRssBytes=process.memoryUsage().rss;
const admissionInputs={availableBytes,currentRssBytes,phaseBytes:config.observation_phase_bytes,rssBytes:config.observation_phase_bytes,
 headroomBytes:572882944,concurrentReservedBytes:0};
console.log(JSON.stringify({kind:'observation-normal-admission-inputs',complete_observation_bound_bytes:config.complete_observation_bound_bytes,
 requested_phase_bytes:admissionInputs.phaseBytes,requested_rss_bytes:admissionInputs.rssBytes,admission_inputs:admissionInputs}));
const allowance=processingAllowance(admissionInputs);
const reader=new ImmutableReader(config.repository,config.inputs.physical.commit,{allowance,
 executionBytes:config.execution_reserve_bytes,metadataBytes:config.metadata_bytes,outputBytes:config.owner_output_and_serialization_bytes});
const stockCharges=config.inputs.physical.bytes+config.inputs.latitudes.bytes+config.inputs.latitudes.decoded_bytes;
const extraReserve=config.complete_observation_bound_bytes-reader.used-stockCharges;
need(Number.isSafeInteger(extraReserve)&&extraReserve>=0&&config.complete_observation_bound_bytes<=allowance.phaseBytes,'Invalid complete observation reserve');
reader.used+=extraReserve;
const check=()=>reader.checkMemory();check();
process.env.GIT_NO_LAZY_FETCH='1';process.env.GIT_NO_REPLACE_OBJECTS='1';process.env.GIT_TERMINAL_PROMPT='0';
process.env.GIT_CONFIG_COUNT='1';process.env.GIT_CONFIG_KEY_0='protocol.allow';process.env.GIT_CONFIG_VALUE_0='never';
function local(pin,parse=true){
 check();const body=fs.readFileSync(path.resolve(here,pin.path));
 need(body.length===pin.bytes&&sha(body)===pin.sha256,'Local whole input drift: '+pin.path);
 return parse?JSON.parse(body):body;
}
const inventory=local(config.local.code_inventory),codeRoot=path.resolve(here,config.code_root);
for(const pin of inventory.files){const b=fs.readFileSync(path.join(codeRoot,pin.path));need(b.length===pin.bytes&&sha(b)===pin.sha256,'Accepted code closure drift');}
const scopePlan=local(config.local.scope_plan),requests=local(config.local.request);
const custody=local(config.local.original_custody,false),joins=local(config.local.joins,false);
const planning=local(config.planning_statistics),planningReceipt=local(config.planning_receipt,false);
need(planning.kind==='whole-operand-resource-planning'&&planning.existing_validator_executed===true&&planning.geometry_membership_executed===false,'Missing completed actual planning');
need(planning.owners===161&&planning.original_cells===53134&&planning.original_intervals===27306&&planning.owner_blocks===177,'Planning denominator changed');
need(planning.actual_max_membership_scratch_bytes===config.actual_max_membership_scratch_bytes&&planning.planned_stock_polygon_scan_blocks===354,'Actual whole-block scratch binding changed');
for(const key of ['physical','original_stage','original_context','latitudes'])need(JSON.stringify(planning.input_pins[key])===JSON.stringify(config.inputs[key]),'Planning whole-input pin mismatch: '+key);
for(const key of Object.keys(planning.local_pins))need(JSON.stringify(planning.local_pins[key])===JSON.stringify(config.local[key]),'Planning local-input pin mismatch: '+key);
const raw={};
for(const name of ['physical','latitudes']){
 const pin=config.inputs[name],actual=reader.descriptor(pin.path,pin.commit);
 need(actual.bytes===pin.bytes&&actual.git_blob_oid===pin.git_blob_oid&&actual.mode===pin.mode,'Immutable whole-input descriptor drift');
 const decoded=name==='latitudes'?pin.decoded_bytes:0;
 reader.admit(actual,decoded);raw[name]=reader.read(pin.path,{version:pin.commit,expected:pin.sha256,decoded});
}
const physical=JSON.parse(raw.physical);
const latitudeRaw=gunzipSync(raw.latitudes,{maxOutputLength:config.inputs.latitudes.decoded_bytes});
need(latitudeRaw.length===size*8&&sha(latitudeRaw)===config.inputs.latitudes.decoded_sha256,'Normative table drift');
const latitudes=Float64Array.from({length:size},(_,y)=>latitudeRaw.readDoubleLE(y*8));
// Original stage/context remain immutable provenance pins, without extra reads.
const operations=['mapped_land_support','mapped_inland_water_support','outside_mapped_L1_context',
 'missing_reconstruction','extra_reconstruction','contradictory_land_water_support','L2-outside-L1','L3-outside-L2','L4-outside-L3'];
const positiveNames=new Set(['mapped_land_support','outside_mapped_L1_context']);
const roster=scopePlan.scope.owner_target_roster,selected=new Map(roster.map(r=>[r.owner,r]));
need(roster.length===161&&selected.size===161,'Whole-owner roster changed');
need(requests.original_class==='source-relative'&&requests.selected_classification===null&&requests.hypothesis===null,'Original request meaning changed');
const owners=requests.owners.filter(r=>selected.has(r.owner));need(owners.length===161,'Missing original whole-owner requests');
const byTarget=new Map(physical.results.map(r=>[r.target,r])),statsByKey=new Map();
for(const row of planning.validator_rows){
 const key=row.owner+':'+row.operation;need(!statsByKey.has(key),'Duplicate actual planning operand');statsByKey.set(key,row);
}
need(statsByKey.size===1449,'Incomplete actual nine-operand planning inventory');
let totalCells=0,totalIntervals=0,ownerBlocks=0;
const count=rows=>rows.reduce((n,r)=>n+r.runs.reduce((s,run)=>s+run[1]-run[0],0),0);
for(const owner of owners){
 const expected=selected.get(owner.owner),whole=byTarget.get(owner.target_id),n=count(owner.requestedRows);
 const intervals=owner.requestedRows.reduce((n,r)=>n+r.runs.length,0);
 need(owner.target_id===expected.target&&whole&&n===expected.relative_cells&&intervals===expected.original_interval_records,'Whole-owner request differs from reviewed scope');
 need(owner.requestedRows.every(r=>r.runs.every(run=>run[2]===owner.owner)),'Foreign original owner');
 const blocks=[...new Set(owner.requestedRows.map(r=>Math.floor(r.y/4096)))];ownerBlocks+=blocks.length;
 totalCells+=n;totalIntervals+=intervals;
 for(const name of operations){
  const row=statsByKey.get(owner.owner+':'+name);
  need(row&&row.target_id===owner.target_id&&row.requested_cells===n&&row.membership_executed===false,'Planning target/key mismatch');
  const g=whole.support[name]??whole.support.hierarchy_disagreements[name];need(g,'Missing complete original operand');
  if(positiveNames.has(name)){
   need(row.blocks.length===blocks.length&&row.blocks.every((b,i)=>b.block===blocks[i]&&!b.empty&&b.scratch_bytes<=config.actual_max_membership_scratch_bytes),'Whole-block planning statistics changed');
  }else need(row.contact_effect==='validated-whole-empty'&&row.validation.empty===true,'Missing complete empty validation');
 }
}
need(totalCells===53134&&totalIntervals===27306&&ownerBlocks===177,'Original complete denominator changed');
check();fs.mkdirSync(output);
let diskBytes=0;
function emit(name,value){
 check();const body=Buffer.from(JSON.stringify(value,null,2)+'\n');
 need(body.length<=config.owner_output_and_serialization_bytes,'Complete metadata serialization exceeds reserve');
 need(diskBytes+body.length<=config.streamed_disk_cap_bytes,'Complete observation disk cap exceeded');
 fs.writeFileSync(path.join(output,name),body,{flag:'wx'});diskBytes+=body.length;
}
emit('admission.json',{kind:'normal-original-relative-observation-admission',admission_inputs:admissionInputs,
 complete_observation_bound_bytes:config.complete_observation_bound_bytes,requested_phase_bytes:config.observation_phase_bytes,
 requested_rss_bytes:config.observation_phase_bytes,config,whole_input_inventory:[...reader.inventory.values()]});
const totals=Object.fromEntries(operations.map(k=>[k,{cells:0,interior:0,boundary:0,line:0,point:0}]));
const fd=fs.openSync(path.join(output,'owner-observations.jsonl'),'wx');
let membershipCalls=0,emptyValidations=0,scanBlocks=0,observedOwners=0,observationBytes=0;
const started=performance.now();
try{
 for(const owner of owners){
  const whole=byTarget.get(owner.target_id),effects={};
  for(const name of operations){
   check();const g=whole.support[name]??whole.support.hierarchy_disagreements[name];
   if(positiveNames.has(name)){
    const actual=witnessCellEffects(g,{size,latitudes,requestedRows:owner.requestedRows,nativePolygonIntervals});
    effects[name]={origin:'existing-witnessCellEffects',membership_executed:true,...actual};
    membershipCalls++;scanBlocks+=actual.work.stock_scan_blocks;
   }else{
    const actual=validateWitnessGeometry(g);need(actual.empty,'Unexpected complete nonempty operand stops reduced observation');
    effects[name]={origin:'validated-whole-empty',membership_executed:false,validation:actual,hits:[],
     counts:{cells:0,interior:0,boundary:0,line:0,point:0}};
    emptyValidations++;
   }
   for(const key of Object.keys(totals[name]))totals[name][key]+=effects[name].counts[key];
  }
  check();const body=Buffer.from(JSON.stringify({owner:owner.owner,target_id:owner.target_id,name:owner.name,
   requested_cells:count(owner.requestedRows),original_class:'source-relative',selected_classification:null,operations:effects})+'\n');
  need(body.length<=config.owner_output_and_serialization_bytes,'One complete owner output exceeds serialization reserve');
  need(diskBytes+body.length<=config.streamed_disk_cap_bytes,'Complete streamed output exceeds disk cap');
  let at=0;while(at<body.length){const n=fs.writeSync(fd,body,at,body.length-at);need(n>0,'Incomplete output write');at+=n;}
  diskBytes+=body.length;observationBytes+=body.length;observedOwners++;
  console.log(JSON.stringify({owner:owner.owner,requested_cells:count(owner.requestedRows),completed_labels:9,membership_calls:2,validated_empty_operands:7}));
 }
}finally{fs.closeSync(fd);}
need(observedOwners===161&&membershipCalls===322&&emptyValidations===1127&&scanBlocks===354,'Incomplete original whole-owner observation');
check();emit('summary.json',{kind:'original-source-relative-retained-land-exterior-observation',original_class:'source-relative',
 selected_classification:null,owners:observedOwners,original_cells:totalCells,original_intervals:totalIntervals,
 membership_calls:membershipCalls,validated_empty_operands:emptyValidations,stock_polygon_scan_blocks:scanBlocks,
 operation_totals:totals,elapsed_seconds:(performance.now()-started)/1000,
 emitted_inventory:[{path:'owner-observations.jsonl',bytes:observationBytes}],
 planning_statistics:config.planning_statistics,complete_observation_bound_bytes:config.complete_observation_bound_bytes,
 requested_phase_bytes:config.observation_phase_bytes,requested_rss_bytes:config.observation_phase_bytes,
 authority_qualified_cells:0,accepted_repair_credit:0,adopted_review_dispositions:null,
 limits:['Independent labelled pointset contacts; overlaps and all exact contact kinds retained, no exclusive or complement class inferred.',
 'Seven zero effects derive only from actual complete accepted-validator emptiness; their membership was not run and no stock work was fabricated.',
 'Frozen original source-relative meaning, whole geometries, original owner/SID/ordinal custody and producer/frame/vintage/licence limits remain.',
 'No source/physical producer replay, authority/native qualification, owner-zero proof, joint consumer, Git mutation, publication or adoption.']});
console.log(JSON.stringify({status:'observation-completed',owners:observedOwners,original_cells:totalCells,original_intervals:totalIntervals,
 membership_calls:membershipCalls,validated_empty_operands:emptyValidations,stock_polygon_scan_blocks:scanBlocks,
 emitted_disk_bytes:diskBytes,complete_observation_bound_bytes:config.complete_observation_bound_bytes}));
