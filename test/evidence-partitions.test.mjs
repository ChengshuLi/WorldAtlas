import test from 'node:test';
import assert from 'node:assert/strict';
import {gzipSync} from 'node:zlib';
import {validateEvidencePartitions} from '../scripts/validate-evidence-partitions.mjs';
import {sha256,subjectsHash} from '../scripts/evidence-quality.mjs';
const encode=value=>Buffer.from(JSON.stringify(value)+'\n');
const descriptor=(path,raw)=>({path,bytes:raw.length,sha256:sha256(raw),hash_kind:'file-bytes'});
function fixture(){
 const baselineCommit='a'.repeat(40),workerId='partition-test-worker',rootPath='coordination/engineering/partition-test/evidence-quality.json',childPath='coordination/engineering/partition-test/child.json',indexPath='coordination/engineering/partition-test/index.json',inventoryPath='coordination/engineering/partition-test/inventory.json.gz';
 const source=Buffer.from('immutable baseline'),inputs=[descriptor('data/input.json',source)],bytes=new Map([['data/input.json',source],['docs/result.md',Buffer.from('candidate result')]]);
 const shape={version:1,issue:6,lane:'engineering',worker_id:workerId,subject_ids:[],subject_ids_sha256:subjectsHash([]),baseline:{commit:baselineCommit,files:inputs,pins:{},pin_files:{}},sources:[],methods:[{id:'byte-accounting',kind:'code',description:'Fixture for partition byte/accounting control',software:'Node24',units:'bytes'}],metrics:[],metric_bindings:[],summaries:[],conclusions:[],stages:{research:'partial',implementation:'proposed',geographic_approval:'not-requested'},commands:['synthetic partition control']};
 const child={...structuredClone(shape),outputs:[descriptor('docs/result.md',bytes.get('docs/result.md'))],change_receipts:[{path:'docs/result.md',status:'added'},{path:childPath,status:'added'}]};
 bytes.set(childPath,encode(child));
 const inventory={version:1,baseline_commit:baselineCommit,files:inputs};bytes.set(inventoryPath,gzipSync(encode(inventory)));
 const reportPath='coordination/engineering/partition-test/report.json';bytes.set(reportPath,encode({preserved:{'input.json':sha256(source)},immutable_grid_parts:[]}));
 const index={version:1,issue:6,worker_id:workerId,baseline_commit:baselineCommit,queue_enforces_aggregate:false,index_path:indexPath,root_manifest_path:rootPath,root_change_paths:[rootPath,indexPath,inventoryPath,reportPath],baseline_inventory:{path:inventoryPath,sha256:sha256(bytes.get(inventoryPath)),files:1},preservation_report:{path:reportPath,sha256:sha256(bytes.get(reportPath)),files:1},partitions:[{...descriptor(childPath,bytes.get(childPath)),change_paths:['docs/result.md',childPath]}]};
 bytes.set(indexPath,encode(index));
 const root={...structuredClone(shape),outputs:[indexPath,inventoryPath,childPath,reportPath,'data/input.json'].map(name=>descriptor(name,bytes.get(name))),change_receipts:index.root_change_paths.map(path=>({path,status:'added'}))};bytes.set(rootPath,encode(root));
 const files=[...index.root_change_paths,...index.partitions[0].change_paths].map(filename=>({filename,status:'added'}));
 const options={files,branch:'engineering/partition-test',workerId,issueNumber:6,readFile:name=>{if(!bytes.has(name))throw Error('Missing fixture');return bytes.get(name);}};
 return {index,bytes,options,childPath,rootPath,indexPath,inventoryPath};
}
function bindIndex(f){f.bytes.set(f.indexPath,encode(f.index));const root=JSON.parse(f.bytes.get(f.rootPath));root.outputs=root.outputs.map(row=>row.path===f.indexPath?descriptor(f.indexPath,f.bytes.get(f.indexPath)):row);f.bytes.set(f.rootPath,encode(root));}
test('bounded root and child evidence verify complete changed-file union and baseline inventory',()=>{
 const f=fixture(),result=validateEvidencePartitions(f.index,f.options);
 assert.equal(result.validated,true);assert.equal(result.changed_files_verified,6);assert.equal(result.baseline_files_verified,1);assert.equal(result.preserved_files_verified,1);assert.equal(result.partitions.length,2);assert.equal(result.queue_enforces_aggregate,false);
});
test('changed child manifest and absent/unassigned changed files reject',()=>{
 let f=fixture();f.bytes.set(f.childPath,Buffer.from('tampered'));assert.throws(()=>validateEvidencePartitions(f.index,f.options),/manifest bytes changed|Input bytes mismatch/);
 f=fixture();f.options.files.push({filename:'docs/unassigned.md',status:'added'});assert.throws(()=>validateEvidencePartitions(f.index,f.options),/Incomplete aggregate/);
 f=fixture();f.index.partitions[0].change_paths.push('docs/absent.md');bindIndex(f);assert.throws(()=>validateEvidencePartitions(f.index,f.options),/absent changed file/);
});
test('root hash cycles, duplicate assignments and changed context reject',()=>{
 let f=fixture();f.index.partitions[0].path=f.rootPath;bindIndex(f);assert.throws(()=>validateEvidencePartitions(f.index,f.options),/self-hash cycle/);
 f=fixture();f.index.partitions[0].change_paths.push(f.indexPath);bindIndex(f);assert.throws(()=>validateEvidencePartitions(f.index,f.options),/more than once/);
 f=fixture();f.index.queue_enforces_aggregate=true;assert.throws(()=>validateEvidencePartitions(f.index,f.options),/Wrong aggregate context/);
});
test('partial baseline inventory cannot replace actual byte verification',()=>{
 const f=fixture();const inventory=encode({version:1,baseline_commit:f.index.baseline_commit,files:[{path:'data/unverified.json',sha256:'f'.repeat(64),bytes:1,hash_kind:'file-bytes'}]});
 f.bytes.set(f.inventoryPath,gzipSync(inventory));f.index.baseline_inventory.sha256=sha256(f.bytes.get(f.inventoryPath));f.bytes.set(f.indexPath,encode(f.index));
 const root=JSON.parse(f.bytes.get(f.rootPath));root.outputs=root.outputs.map(row=>[f.inventoryPath,f.indexPath].includes(row.path)?descriptor(row.path,f.bytes.get(row.path)):row);f.bytes.set(f.rootPath,encode(root));
 assert.throws(()=>validateEvidencePartitions(f.index,f.options),/Unverified baseline/);
});
test('empty inventory, alternate executed index and omitted preservation bytes reject',()=>{
 let f=fixture();const empty=gzipSync(encode({version:1,baseline_commit:f.index.baseline_commit,files:[]}));f.bytes.set(f.inventoryPath,empty);f.index.baseline_inventory.sha256=sha256(empty);
 let root=JSON.parse(f.bytes.get(f.rootPath));root.outputs=root.outputs.map(row=>row.path===f.inventoryPath?descriptor(f.inventoryPath,empty):row);f.bytes.set(f.rootPath,encode(root));bindIndex(f);assert.throws(()=>validateEvidencePartitions(f.index,f.options),/Incomplete baseline inventory/);
 f=fixture();f.index.baseline_inventory.files=2;assert.throws(()=>validateEvidencePartitions(f.index,f.options),/Executed index differs/);
 f=fixture();root=JSON.parse(f.bytes.get(f.rootPath));root.outputs=root.outputs.filter(row=>row.path!=='data/input.json');f.bytes.set(f.rootPath,encode(root));assert.throws(()=>validateEvidencePartitions(f.index,f.options),/Unverified unchanged candidate/);
});


test('trusted per-partition descriptor and individual byte budgets are not raised',()=>{
 let f=fixture();let root=JSON.parse(f.bytes.get(f.rootPath));
 for(let i=0;i<512;i++){const name=`data/control-${i}.json`,raw=Buffer.from('control');f.bytes.set(name,raw);root.baseline.files.push(descriptor(name,raw));}
 f.bytes.set(f.rootPath,encode(root));assert.throws(()=>validateEvidencePartitions(f.index,f.options),/bounded review budget/);
 f=fixture();root=JSON.parse(f.bytes.get(f.rootPath));root.baseline.files[0].bytes=32*1024*1024+1;f.bytes.set(f.rootPath,encode(root));assert.throws(()=>validateEvidencePartitions(f.index,f.options),/file exceeds budget/);
});
