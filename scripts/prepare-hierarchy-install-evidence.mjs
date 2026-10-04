// Partition the complete installation inventory without relaxing trusted limits.
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {gunzipSync} from 'node:zlib';
import {sha256,subjectsHash,safeEvidencePath} from './evidence-quality.mjs';
import {encodeEvidenceJSON} from './evidence/encode-json.mjs';

const root=process.cwd(),job='hierarchy-install-20261003-a9c2';
const owned=`data/engineering/${job}`,directory=`coordination/engineering/${job}`;
const [base]=process.argv.slice(2);
if(!/^[a-f0-9]{40}$/.test(base??''))throw Error('Supply the exact current PR base commit after staging intended changes');
const git=args=>execFileSync('git',args,{encoding:'utf8',maxBuffer:8*1024*1024});
const read=name=>{safeEvidencePath(name);const file=path.join(root,name);if(fs.realpathSync(file)!==file||!fs.lstatSync(file).isFile())throw Error('Ordinary evidence file required');return fs.readFileSync(file);};
const descriptor=(name,raw)=>{
 if(raw.length>32*1024*1024)throw Error('Individual evidence limit exceeded');
 const result={path:name,bytes:raw.length,sha256:sha256(raw),hash_kind:'file-bytes'};
 if(name.endsWith('.gz')&&!name.endsWith('.tar.gz')){
  try{const expanded=gunzipSync(raw,{maxOutputLength:32*1024*1024});result.uncompressed_bytes=expanded.length;result.uncompressed_sha256=sha256(expanded);}
  catch(error){if(error.code!=='ERR_BUFFER_TOO_LARGE')throw error;result.inspection_limit='Whole compressed bytes verified; aggregate expansion exceeds individual decoded-evidence budget';}
 }
 return result;
};
const write=(name,value)=>{fs.mkdirSync(path.dirname(name),{recursive:true});fs.writeFileSync(name,encodeEvidenceJSON(value));};
const inventoryPath=`${owned}/baseline-inventory.json.gz`,inventory=JSON.parse(gunzipSync(read(inventoryPath)));
const reportPath=`${owned}/installation-report.json`,report=JSON.parse(read(reportPath));
const sourceManifest=JSON.parse(read('coordination/engineering/hierarchy-crosswalk-20261003-a9c2/evidence-quality.json'));
const rootPath=`${directory}/evidence-quality.json`,indexPath=`${directory}/partitions.json`;
const changes=[],raw=git(['diff','--cached','--name-status','-z','--find-renames',base]).split('\0');
for(let i=0;i<raw.length&&raw[i];){
 const status=raw[i++],first=raw[i++];
 const row=status.startsWith('R')?{path:raw[i++],previous_path:first,status:'renamed'}:{path:first,status:{A:'added',M:'modified',D:'removed'}[status]};
 if(!row.status||row.status==='removed')throw Error('This metadata installation must not delete original payloads');
 if(row.status!=='added')row.original_sha256=sha256(execFileSync('git',['show',base+':'+(row.previous_path??row.path)],{maxBuffer:32*1024*1024}));
 if(!row.path.startsWith(directory+'/'))changes.push(row);
}
const protectedFiles=new Map(Object.entries(report.preserved).map(([name,pin])=>['data/'+name,pin]));
for(const file of report.immutable_grid_parts)protectedFiles.set('data/'+file.path,file.sha256);
const outputNames=new Set([...changes.map(row=>row.path),...protectedFiles.keys()]);
const codeInventoryPath=`${owned}/generation-code-inventory.json`,codeInventory=JSON.parse(read(codeInventoryPath));
for(const file of codeInventory.files){if(sha256(read(file.path))!==file.sha256)throw Error('Generation code differs from the two-run source snapshot');outputNames.add(file.path);}
for(const [name,pin]of protectedFiles)if(sha256(read(name))!==pin)throw Error('Protected installed bytes changed: '+name);
const commonName='data/hierarchy.json',common=inventory.files.find(row=>row.path===commonName);
if(!common)throw Error('Missing common hierarchy baseline');
const shape={version:1,issue:6,lane:'engineering',worker_id:'engineering-hierarchy-crosswalk-a9c25e14-20261003',subject_ids:sourceManifest.subject_ids,subject_ids_sha256:subjectsHash(sourceManifest.subject_ids),baseline:{commit:inventory.baseline_commit,files:[common],pins:{hierarchy:common.sha256},pin_files:{hierarchy:commonName}},sources:sourceManifest.sources,methods:[{id:'whole-file-partition-accounting',kind:'code',description:'Immutable original data and exact candidate/preservation file bytes; no fresh source inspection or geometry measurement',software:'Node24, Git2.52; trusted existing premerge whole-file validator',units:'whole-file bytes and exact changed-file inventories'}],metrics:[],metric_bindings:[],summaries:[],conclusions:[],stages:{research:'partial',implementation:'implemented',geographic_approval:'not-requested'},commands:[`node scripts/validate-evidence-partitions.mjs ${indexPath} ${base} HEAD`]};
const groups=[];let group={baseline:[],outputs:[],bytes:common.bytes};
function add(vintage,file){
 if(group.baseline.length+group.outputs.length===380||group.bytes+file.bytes>128*1024*1024){groups.push(group);group={baseline:[],outputs:[],bytes:common.bytes};}
 group[vintage].push(file);group.bytes+=file.bytes;
}
for(const file of inventory.files)if(file.path!==commonName)add('baseline',file);
for(const name of [...outputNames].sort())add('outputs',descriptor(name,read(name)));
if(group.baseline.length+group.outputs.length)groups.push(group);
const children=[];
for(const [i,part]of groups.entries()){
 const name=`${directory}/partition-${String(i).padStart(2,'0')}.json`,assigned=changes.filter(row=>part.outputs.some(file=>file.path===row.path));
 const manifest={...structuredClone(shape),baseline:{...structuredClone(shape.baseline),files:[common,...part.baseline]},outputs:part.outputs,change_receipts:[...assigned,{path:name,status:'added'}]};
 write(name,manifest);children.push({...descriptor(name,read(name)),change_paths:manifest.change_receipts.map(row=>row.path)});
}
const index={version:1,issue:6,worker_id:shape.worker_id,baseline_commit:inventory.baseline_commit,queue_enforces_aggregate:false,index_path:indexPath,root_manifest_path:rootPath,root_change_paths:[rootPath,indexPath],baseline_inventory:{...descriptor(inventoryPath,read(inventoryPath)),files:inventory.files.length},preservation_report:{...descriptor(reportPath,read(reportPath)),files:protectedFiles.size},partitions:children};
write(indexPath,index);
const controls=['positive-control','negative-control','reproducibility'].map(kind=>`${owned}/${kind}.json`);
const evidence={...structuredClone(shape),outputs:[indexPath,...children.map(row=>row.path),...controls].map(name=>descriptor(name,read(name))),change_receipts:index.root_change_paths.map(name=>({path:name,status:'added'}))};
evidence.methods.push({id:'hierarchy-install-generator',kind:'generator',helper_version:'worldatlas-evidence-preparation-v1',description:'Full offline generation with existing release/metadata/source validators, preserved payloads and ownership buffers, unchanged macro envelope compatibility, two complete raw-byte-equal runs',software:'Python3.12.14/zlib1.3.2, Node24.19.0 and committed requirements',units:'identity counts and exact raw file bytes'});
evidence.validation=controls.map((name,i)=>({method_id:'hierarchy-install-generator',kind:['positive-control','negative-control','reproducibility'][i],outcome:'passed',evidence_path:name}));
const reproduction=JSON.parse(read(controls[2]));
for(const [key,value]of Object.entries(reproduction.counts)){
 const id=`current-${key}-count`;evidence.metrics.push({id,value,unit:`${key} identities`,vintage:'baseline',input_sha256:sha256(read(controls[2])),evaluation_commit:inventory.baseline_commit});evidence.metric_bindings.push({metric_id:id,path:controls[2],json_pointer:'/counts/'+key});
}
write(rootPath,evidence);
console.log(JSON.stringify({root_manifest:rootPath,root_sha256:sha256(read(rootPath)),partitions:children.length+1,baseline_files:inventory.files.length,preserved_files:protectedFiles.size,accounted_changes:changes.length+children.length+2,queue_enforces_aggregate:false}));
