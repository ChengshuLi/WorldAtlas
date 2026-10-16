import test from 'node:test';
import assert from 'node:assert/strict';
import {gzipSync} from 'node:zlib';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {validateEvidencePartitions,partitionGitReader} from '../scripts/validate-evidence-partitions.mjs';
import {sha256,subjectsHash,validateEvidence,evidenceBytePlan,baselineFiles} from '../scripts/evidence-quality.mjs';
const encode=value=>Buffer.from(JSON.stringify(value)+'\n');
const descriptor=(path,raw)=>({path,bytes:raw.length,sha256:sha256(raw),hash_kind:'file-bytes'});
function fixture({source=Buffer.from('immutable baseline'),baselineCommit='a'.repeat(40)}={}){
 const workerId='partition-test-worker',rootPath='coordination/engineering/partition-test/evidence-quality.json',childPath='coordination/engineering/partition-test/child.json',indexPath='coordination/engineering/partition-test/index.json',inventoryPath='coordination/engineering/partition-test/inventory.json.gz';
 const inputs=[descriptor('data/input.json',source)],bytes=new Map([['data/input.json',source],['docs/result.md',Buffer.from('candidate result')]]);
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


test('trusted per-partition descriptor count remains bounded',()=>{
 const f=fixture(),root=JSON.parse(f.bytes.get(f.rootPath));
 for(let i=0;i<512;i++){const name=`data/control-${i}.json`,raw=Buffer.from('control');f.bytes.set(name,raw);root.baseline.files.push(descriptor(name,raw));}
 f.bytes.set(f.rootPath,encode(root));assert.throws(()=>validateEvidencePartitions(f.index,f.options),/bounded review budget/);
});

test('partition exact reviewed sizes admit a genuine body above the former default ceiling',()=>{
 const f=fixture({source:Buffer.alloc(32*1024*1024+1,65)});
 const result=validateEvidencePartitions(f.index,f.options);
 assert.equal(result.validated,true);assert.equal(result.partitions.length,2);
 assert.equal(result.baseline_files_verified,1);assert.equal(result.preserved_files_verified,1);
 const root=JSON.parse(f.bytes.get(f.rootPath));let reads=0;
 assert.throws(()=>validateEvidence(root,{maxFileBytes:32*1024*1024,readFile:()=>{reads++;}}),/file exceeds budget/);
 assert.equal(reads,0);
});

test('immutable partition CLI forwards exact descriptors above the former Git buffer ceiling',()=>{
 const directory=fs.mkdtempSync(path.join(os.tmpdir(),'worldatlas-partition-exact-'));
 const env={...process.env,GIT_CONFIG_NOSYSTEM:'1',GIT_CONFIG_GLOBAL:'/dev/null',GIT_NO_LAZY_FETCH:'1',NODE_PATH:'',NODE_OPTIONS:''};
 const git=(...args)=>execFileSync('git',['-c','core.hooksPath=/dev/null','-c','user.name=Partition fixture','-c','user.email=partition@example.invalid',...args],{cwd:directory,env,stdio:['ignore','pipe','pipe']}).toString().trim();
 try{
  git('init','-q','-b','engineering/partition-test');fs.mkdirSync(path.join(directory,'data'));
  const source=Buffer.alloc(32*1024*1024+1,65);fs.writeFileSync(path.join(directory,'data/input.json'),source);
  git('add','.');git('commit','-qm','Exact original input');
  const f=fixture({source,baselineCommit:git('rev-parse','HEAD')});
  for(const [name,raw]of f.bytes){fs.mkdirSync(path.dirname(path.join(directory,name)),{recursive:true});fs.writeFileSync(path.join(directory,name),raw);}
  git('add','.');git('commit','-qm','Bounded partition evidence');
  const script=fileURLToPath(new URL('../scripts/validate-evidence-partitions.mjs',import.meta.url));
  const result=JSON.parse(execFileSync(process.execPath,[script,f.indexPath,f.index.baseline_commit,'HEAD'],{cwd:directory,env,encoding:'utf8'}));
  assert.equal(result.validated,true);assert.equal(result.partitions.length,2);
  const read=partitionGitReader({head:git('rev-parse','HEAD'),base:f.index.baseline_commit,cwd:directory});
  const pin=descriptor('data/input.json',source);
  assert.throws(()=>read(pin.path,'candidate'),/file budget/);
  for(const bytes of [pin.bytes-1,pin.bytes+1])assert.throws(()=>read(pin.path,'candidate',{...pin,bytes}),/file budget/);
  for(const bytes of [Infinity,NaN,-1,Number.MAX_SAFE_INTEGER+1])
   assert.throws(()=>read(pin.path,'candidate',{...pin,bytes}),/finite/);
  const fd=fs.openSync(path.join(directory,'data/input.json'),'r+');
  try{fs.writeSync(fd,Buffer.from('B'),0,1,0);}finally{fs.closeSync(fd);}
  git('add','data/input.json');git('commit','-qm','Same-size changed candidate control');
  assert.throws(()=>execFileSync(process.execPath,[script,f.indexPath,f.index.baseline_commit,'HEAD'],
   {cwd:directory,env,encoding:'utf8',stdio:['ignore','pipe','pipe']}),error=>/Input bytes mismatch/.test(error.stderr));
 }finally{fs.rmSync(directory,{recursive:true,force:true});}
});

test('partition whole-body lengths and same-size hashes still reject drift',()=>{
 let f=fixture(),root=JSON.parse(f.bytes.get(f.rootPath));
 root.baseline.files[0].bytes=32*1024*1024+1;f.bytes.set(f.rootPath,encode(root));
 assert.throws(()=>validateEvidencePartitions(f.index,f.options),/Input bytes mismatch/);
 f=fixture();f.bytes.set('data/input.json',Buffer.from('Immutable baseline'));
 assert.throws(()=>validateEvidencePartitions(f.index,f.options),/Input bytes mismatch/);
});

test('explicit validator file and phase operating limits reject before body reads',()=>{
 const f=fixture(),root=JSON.parse(f.bytes.get(f.rootPath));
 const plan=evidenceBytePlan([...baselineFiles(root),...root.outputs]);let reads=0;
 const readFile=()=>{reads++;throw Error('Body read before operating admission');};
 assert.throws(()=>validateEvidence(root,{readFile,maxFileBytes:plan.maxFileBytes-1}),/file exceeds budget/);
 assert.throws(()=>validateEvidence(root,{readFile,maxTotalBytes:plan.totalBytes-1}),/phase exceeds byte budget/);
 assert.equal(reads,0);
});
