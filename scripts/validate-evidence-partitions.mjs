// Voluntary aggregate evidence for reviewed large legacy scopes.
// The GitHub merge queue does not enforce this aggregate contract.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {isDeepStrictEqual} from 'node:util';
import {gunzipSync} from 'node:zlib';
import {sha256,safeEvidencePath} from './evidence-quality.mjs';
import {validatePremergeManifest} from './premerge-evidence.mjs';
const need=(ok,message)=>{if(!ok)throw Error(message);};
export function readGitPRFiles(base,head,{cwd=process.cwd()}={}){
 // GitHub reviews changes since the merge base, not main-only additions.
 // Original-byte receipts still read the actual current PR base below.
 const raw=execFileSync('git',['diff','--name-status','-z','--find-renames',`${base}...${head}`],{cwd,encoding:'utf8',maxBuffer:8*1024*1024}).split('\0'),files=[];
 for(let i=0;i<raw.length&&raw[i];){const status=raw[i++],first=raw[i++];files.push(status.startsWith('R')?{filename:raw[i++],previous_filename:first,status:'renamed'}:{filename:first,status:{A:'added',M:'modified',D:'removed'}[status]});}
 return files;
}
export function validateEvidencePartitions(index,{readFile,files,branch,workerId,issueNumber}){
 need(index.version===1&&index.issue===issueNumber&&index.worker_id===workerId&&index.queue_enforces_aggregate===false,'Wrong aggregate context');
 need(Array.isArray(index.partitions)&&index.partitions.length>0&&new Set(index.partitions.map(row=>row.path)).size===index.partitions.length,'Duplicate or missing partitions');
 safeEvidencePath(index.root_manifest_path);safeEvidencePath(index.index_path);
 need(isDeepStrictEqual(JSON.parse(readFile(index.index_path,'candidate')),index),'Executed index differs from bound index bytes');
 need(!index.partitions.some(row=>row.path===index.root_manifest_path),'Root manifest must not create a self-hash cycle');
 const assigned=new Set(),baseline=new Map(),candidate=new Map(),results=[];
 const entries=[{path:index.root_manifest_path,change_paths:index.root_change_paths,is_root:true},...index.partitions];
 for(const partition of entries){
  safeEvidencePath(partition.path);
  const raw=readFile(partition.path,'candidate');
  if(!partition.is_root)need(raw.length===partition.bytes&&sha256(raw)===partition.sha256,'Partition manifest bytes changed');
  const manifest=JSON.parse(raw);
  if(partition.is_root)need(manifest.outputs.some(row=>row.path===index.index_path&&row.sha256===sha256(readFile(index.index_path,'candidate'))),'Root manifest does not bind aggregate index');
  need(manifest.baseline.commit===index.baseline_commit&&manifest.worker_id===workerId&&manifest.issue===issueNumber,'Partition baseline/worker differs');
  const selected=[];
  for(const name of partition.change_paths){
   safeEvidencePath(name);need(!assigned.has(name),'Changed file assigned more than once');
   const file=files.find(row=>row.filename===name);need(file,'Partition accounts for an absent changed file');
   assigned.add(name);selected.push(file);
  }
  const result=validatePremergeManifest(manifest,{readFile,files:selected,manifestPath:partition.path,issue:{number:issueNumber},spec:{mode:'engineering',evidence_quality:{subject_ids:manifest.subject_ids,pins:manifest.baseline.pins}},reservation:{worker_id:workerId},branch});
  for(const file of manifest.baseline.files){
   need(!baseline.has(file.path)||baseline.get(file.path).sha256===file.sha256,'Conflicting baseline descriptors');baseline.set(file.path,file);
  }
  for(const file of manifest.outputs){
   need(!candidate.has(file.path)||candidate.get(file.path).sha256===file.sha256,'Conflicting candidate descriptors');candidate.set(file.path,file);
  }
  results.push({path:partition.path,sha256:sha256(raw),descriptors:manifest.baseline.files.length+manifest.outputs.length+manifest.sources.flatMap(source=>source.files??[]).length,changed_files:selected.length,status:result.status,limits:result.limits});
 }
 need(assigned.size===files.length&&files.every(file=>assigned.has(file.filename)),'Incomplete aggregate PR change accounting');
 const inventoryRaw=readFile(index.baseline_inventory.path,'candidate');
 need(sha256(inventoryRaw)===index.baseline_inventory.sha256,'Baseline inventory changed');
 const inventory=JSON.parse(gunzipSync(inventoryRaw,{maxOutputLength:32*1024*1024}));
 need(inventory.baseline_commit===index.baseline_commit,'Baseline inventory vintage differs');
 need(inventory.files.length>0&&inventory.files.length===index.baseline_inventory.files&&inventory.files.length===baseline.size,'Incomplete baseline inventory union');
 need(new Set(inventory.files.map(file=>file.path)).size===inventory.files.length,'Duplicate baseline inventory path');
 for(const file of inventory.files)need(baseline.get(file.path)?.sha256===file.sha256&&baseline.get(file.path)?.bytes===file.bytes,'Unverified baseline/preservation input: '+file.path);
 const preservationRaw=readFile(index.preservation_report.path,'candidate');
 need(sha256(preservationRaw)===index.preservation_report.sha256&&candidate.get(index.preservation_report.path)?.sha256===index.preservation_report.sha256,'Unbound preservation report');
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
 const blob=(name,commit)=>{
  safeEvidencePath(name);
  const entry=execFileSync('git',['ls-tree',commit,'--',name],{encoding:'utf8'});
  need(entry.startsWith('100644 ')||entry.startsWith('100755 '),'Evidence must be an ordinary Git blob');
  return execFileSync('git',['show',commit+':'+name],{maxBuffer:32*1024*1024});
 };
 const relative=path.relative(root,path.resolve(file));
 const index=JSON.parse(blob(relative,headCommit));
 need(relative===index.index_path,'Executed index path differs from declared index');
 const files=readGitPRFiles(baseCommit,headCommit);
 const result=validateEvidencePartitions(index,{readFile:(name,vintage)=>blob(name,vintage==='candidate'?headCommit:vintage==='base'?baseCommit:vintage),files,branch:execFileSync('git',['branch','--show-current'],{encoding:'utf8'}).trim(),workerId:index.worker_id,issueNumber:index.issue});
 console.log(JSON.stringify({...result,base_commit:baseCommit,head_commit:headCommit},null,2));
}
