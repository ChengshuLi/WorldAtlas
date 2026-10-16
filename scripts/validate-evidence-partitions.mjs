// Voluntary aggregate evidence for reviewed large legacy scopes.
// The GitHub merge queue does not enforce this aggregate contract.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {isDeepStrictEqual} from 'node:util';
import {sha256,safeEvidencePath,finiteBytes,addBytes,decodeEvidenceGzip,gitEvidenceDescriptor} from './evidence-quality.mjs';
import {validatePremergeManifest} from './premerge-evidence.mjs';
const need=(ok,message)=>{if(!ok)throw Error(message);};
export function readGitPRFiles(base,head,{cwd=process.cwd()}={}){
 // GitHub reviews changes since the merge base, not main-only additions.
 // Original-byte receipts still read the actual current PR base below.
 const raw=execFileSync('git',['diff','--name-status','-z','--find-renames',`${base}...${head}`],{cwd,encoding:'utf8',maxBuffer:8*1024*1024}).split('\0'),files=[];
 for(let i=0;i<raw.length&&raw[i];){const status=raw[i++],first=raw[i++];files.push(status.startsWith('R')?{filename:raw[i++],previous_filename:first,status:'renamed'}:{filename:first,status:{A:'added',M:'modified',D:'removed'}[status]});}
 return files;
}
// Share the exact whole-body reader with the voluntary review CLI. Bootstrap
// metadata keeps its legacy bound; reviewed payloads use their own descriptor.
export function partitionGitReader({head,base,cwd=process.cwd()}){
 need([head,base].every(value=>typeof value==='string'&&/^[a-f0-9]{40}$/.test(value)),
  'Exact immutable partition commits required');
 const resolve=vintage=>{
  const commit=vintage==='candidate'?head:vintage==='base'?base:vintage;
  need(typeof commit==='string'&&/^[a-f0-9]{40}$/.test(commit),'Exact immutable partition vintage required');return commit;
 };
 const read=(name,vintage,descriptor)=>{
  const bound=descriptor===undefined?32*1024*1024:finiteBytes(descriptor.bytes,'partition file descriptor');
  const actual=gitEvidenceDescriptor(cwd,name,resolve(vintage)),bytes=actual.bytes;
  need(descriptor===undefined?bytes<=bound:bytes===bound,'Partition Git body differs from exact file budget');
  const raw=execFileSync('git',['cat-file','blob',actual.git_blob_oid],{cwd,maxBuffer:addBytes(bound,1)});
  need(raw.length===bytes,'Partition Git body length changed');return raw;
 };
 read.descriptor=(name,vintage)=>gitEvidenceDescriptor(cwd,name,resolve(vintage));return read;
}
export function validateEvidencePartitions(index,{readFile,files,branch,workerId,issueNumber}){
 need(index.version===1&&index.issue===issueNumber&&index.worker_id===workerId&&index.queue_enforces_aggregate===false,'Wrong aggregate context');
 need(Array.isArray(index.partitions)&&index.partitions.length>0&&new Set(index.partitions.map(row=>row.path)).size===index.partitions.length,'Duplicate or missing partitions');
 safeEvidencePath(index.root_manifest_path);safeEvidencePath(index.index_path);
 need(isDeepStrictEqual(JSON.parse(readFile(index.index_path,'candidate')),index),'Executed index differs from bound index bytes');
 need(!index.partitions.some(row=>row.path===index.root_manifest_path),'Root manifest must not create a self-hash cycle');
 const assigned=new Set(),baseline=new Map(),candidate=new Map(),results=[];
 const mergeDescriptor=(prior,file,label)=>{
  if(!prior)return file;
  need(prior.sha256===file.sha256&&prior.bytes===file.bytes,'Conflicting '+label+' descriptors');
  if(prior.uncompressed_sha256!==undefined&&file.uncompressed_sha256!==undefined)
   need(prior.uncompressed_sha256===file.uncompressed_sha256&&prior.uncompressed_bytes===file.uncompressed_bytes,
    'Conflicting '+label+' decoded descriptors');
  return prior.uncompressed_sha256!==undefined?prior:file;
 };
 const entries=[{path:index.root_manifest_path,change_paths:index.root_change_paths,is_root:true},...index.partitions];
 for(const partition of entries){
  safeEvidencePath(partition.path);
  const raw=readFile(partition.path,'candidate',partition.is_root?undefined:partition);
  if(!partition.is_root)need(raw.length===partition.bytes&&sha256(raw)===partition.sha256,'Partition manifest bytes changed');
  const manifest=JSON.parse(raw);
  if(partition.is_root){
   const pin=manifest.outputs.find(row=>row.path===index.index_path);
   need(pin&&pin.sha256===sha256(readFile(index.index_path,'candidate',pin)),'Root manifest does not bind aggregate index');
  }
  need(manifest.baseline.commit===index.baseline_commit&&manifest.worker_id===workerId&&manifest.issue===issueNumber,'Partition baseline/worker differs');
  const selected=[];
  for(const name of partition.change_paths){
   safeEvidencePath(name);need(!assigned.has(name),'Changed file assigned more than once');
   const file=files.find(row=>row.filename===name);need(file,'Partition accounts for an absent changed file');
   assigned.add(name);selected.push(file);
  }
  const result=validatePremergeManifest(manifest,{readFile,files:selected,manifestPath:partition.path,issue:{number:issueNumber},spec:{mode:'engineering',evidence_quality:{subject_ids:manifest.subject_ids,pins:manifest.baseline.pins}},reservation:{worker_id:workerId},branch});
  for(const file of manifest.baseline.files){
   baseline.set(file.path,mergeDescriptor(baseline.get(file.path),file,'baseline'));
  }
  for(const file of manifest.outputs){
   candidate.set(file.path,mergeDescriptor(candidate.get(file.path),file,'candidate'));
  }
  results.push({path:partition.path,sha256:sha256(raw),descriptors:manifest.baseline.files.length+manifest.outputs.length+manifest.sources.flatMap(source=>source.files??[]).length,changed_files:selected.length,status:result.status,limits:result.limits});
 }
 need(assigned.size===files.length&&files.every(file=>assigned.has(file.filename)),'Incomplete aggregate PR change accounting');
 const inventoryPin=candidate.get(index.baseline_inventory.path);
 need(inventoryPin&&inventoryPin.sha256===index.baseline_inventory.sha256,'Unbound baseline inventory');
 const inventoryRaw=readFile(index.baseline_inventory.path,'candidate',inventoryPin);
 need(sha256(inventoryRaw)===index.baseline_inventory.sha256,'Baseline inventory changed');
 const inventory=JSON.parse(decodeEvidenceGzip(inventoryRaw,inventoryPin));
 need(inventory.baseline_commit===index.baseline_commit,'Baseline inventory vintage differs');
 need(inventory.files.length>0&&inventory.files.length===index.baseline_inventory.files&&inventory.files.length===baseline.size,'Incomplete baseline inventory union');
 need(new Set(inventory.files.map(file=>file.path)).size===inventory.files.length,'Duplicate baseline inventory path');
 for(const file of inventory.files)need(baseline.get(file.path)?.sha256===file.sha256&&baseline.get(file.path)?.bytes===file.bytes,'Unverified baseline/preservation input: '+file.path);
 const preservationPin=candidate.get(index.preservation_report.path);
 need(preservationPin&&preservationPin.sha256===index.preservation_report.sha256,'Unbound preservation report');
 const preservationRaw=readFile(index.preservation_report.path,'candidate',preservationPin);
 need(sha256(preservationRaw)===index.preservation_report.sha256,'Unbound preservation report');
 const report=JSON.parse(preservationRaw),protectedFiles=new Map(Object.entries(report.preserved??{}).map(([name,pin])=>['data/'+name,pin]));
 for(const file of report.immutable_grid_parts??[])protectedFiles.set('data/'+file.path,file.sha256);
 need(protectedFiles.size>0&&protectedFiles.size===index.preservation_report.files,'Incomplete preservation inventory');
 for(const [name,pin]of protectedFiles)need(baseline.get(name)?.sha256===pin&&candidate.get(name)?.sha256===pin,'Unverified unchanged candidate payload: '+name);
 return {validated:true,queue_enforces_aggregate:false,baseline_files_verified:inventory.files.length,preserved_files_verified:protectedFiles.size,changed_files_verified:files.length,partitions:results,geographic_approval:false,published:false};
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 const [file,base,head='HEAD']=process.argv.slice(2);
 if(!file||!base)throw Error('Use INDEX.json BASE-COMMIT [CANDIDATE-COMMIT]');
 const root=process.cwd(),resolve=ref=>execFileSync('git',['rev-parse','--verify',ref+'^{commit}'],{encoding:'utf8'}).trim();
 const baseCommit=resolve(base),headCommit=resolve(head);
 const read=partitionGitReader({head:headCommit,base:baseCommit,cwd:root});
 const relative=path.relative(root,path.resolve(file));
 const index=JSON.parse(read(relative,'candidate'));
 need(relative===index.index_path,'Executed index path differs from declared index');
 const files=readGitPRFiles(baseCommit,headCommit);
 const result=validateEvidencePartitions(index,{readFile:read,files,branch:execFileSync('git',['branch','--show-current'],{encoding:'utf8'}).trim(),workerId:index.worker_id,issueNumber:index.issue});
 console.log(JSON.stringify({...result,base_commit:baseCommit,head_commit:headCommit},null,2));
}
