// Read-only voluntary review extension for explicitly reviewed legacy partitions.
import {execFileSync} from 'node:child_process';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {sha256,safeEvidencePath,validateEvidence} from './evidence-quality.mjs';
import {validateReviewReceipt} from './premerge-evidence.mjs';
import {validateEvidencePartitions} from './validate-evidence-partitions.mjs';
import {githubPages} from './issue-claim-contract.mjs';
const need=(ok,message)=>{if(!ok)throw Error(message);};
const qualified=comment=>['OWNER','MEMBER','COLLABORATOR'].includes(comment.author_association);
export function reviewMarker(comment,name){const match=comment.body?.match(new RegExp('<!-- '+name+':v1\\s*([\\s\\S]*?)-->'));return match?JSON.parse(match[1]):null;}
export function selectAggregateReview(comments,head){
 const eligible=comments.filter(qualified),latest=new Map();
 for(const comment of eligible){const receipt=reviewMarker(comment,'worldatlas-review');if(receipt?.head_sha===head){const old=latest.get(receipt.reviewer_worker_id);if(!old||old.comment.id<comment.id)latest.set(receipt.reviewer_worker_id,{comment,receipt});}}
 need(![...latest.values()].some(row=>row.receipt.outcome==='changes-requested'),'Current head has unresolved changes-requested review');
 const roots=eligible.filter(comment=>{const aggregate=reviewMarker(comment,'worldatlas-review-aggregate');return aggregate?.head_sha===head&&latest.get(aggregate.reviewer_worker_id)?.comment.id===comment.id;}).sort((a,b)=>a.id-b.id);
 need(roots.length>0,'No qualified latest exact-head aggregate review');
 return roots.at(-1);
}
export function boundPartitionReview(binding,comments,{head,reviewer}){
 const comment=comments.find(row=>row.id===binding.comment_id);
 need(comment&&qualified(comment),'Partition review author is not qualified');
 need(comment.html_url===binding.comment_url&&sha256(Buffer.from(comment.body))===binding.body_sha256,'Review comment snapshot changed or absent');
 const receipt=reviewMarker(comment,'worldatlas-review-partition');
 need(receipt?.head_sha===head&&receipt.reviewer_worker_id===reviewer,'Partition review head/reviewer differs');
 const latest=new Map();
 for(const row of comments.filter(qualified)){const item=reviewMarker(row,'worldatlas-review-partition');if(item?.head_sha===head&&item.manifest_sha256===receipt.manifest_sha256){const old=latest.get(item.reviewer_worker_id);if(!old||old.comment.id<row.id)latest.set(item.reviewer_worker_id,{comment:row,receipt:item});}}
 need(![...latest.values()].some(row=>row.receipt.outcome==='changes-requested'),'Unresolved partition changes-requested review');
 need(latest.get(reviewer)?.comment.id===comment.id,'Partition review is not the latest worker receipt');
 return {comment,receipt};
}
export function checkPartitionReviewInventory(aggregate,index){
 need(Array.isArray(aggregate.partitions)&&aggregate.partitions.length===index.partitions.length&&new Set(aggregate.partitions.map(row=>row.manifest_path)).size===index.partitions.length&&index.partitions.every(part=>aggregate.partitions.some(row=>row.manifest_path===part.path)),'Incomplete partition review inventory');
}
async function main(){
const [number,indexPath]=process.argv.slice(2);
if(!/^\d+$/.test(number??'')||!indexPath)throw Error('Use PR-NUMBER PARTITION-INDEX-PATH');
safeEvidencePath(indexPath);
const repo='ChengshuLi/WorldAtlas';
const gh=route=>JSON.parse(execFileSync('gh',['api',route],{encoding:'utf8',maxBuffer:8*1024*1024}));
const pr=gh(`repos/${repo}/pulls/${number}`),head=pr.head.sha,base=pr.base.sha;
need(execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim()===head,'Local checkout differs from actual PR head');
const read=(name,vintage)=>{
 safeEvidencePath(name);const commit=vintage==='candidate'?head:vintage==='base'?base:vintage;
 const mode=execFileSync('git',['ls-tree',commit,'--',name],{encoding:'utf8'});
 need(mode.startsWith('100644 ')||mode.startsWith('100755 '),'Ordinary immutable Git evidence required');
 return execFileSync('git',['show',commit+':'+name],{maxBuffer:32*1024*1024});
};
const indexRaw=read(indexPath,'candidate'),index=JSON.parse(indexRaw);
need(indexPath===index.index_path,'Executed index path differs');
const changes=execFileSync('git',['diff','--name-status','-z','--find-renames',base,head],{encoding:'utf8',maxBuffer:8*1024*1024}).split('\0'),files=[];
for(let i=0;i<changes.length&&changes[i];){const status=changes[i++],first=changes[i++];files.push(status.startsWith('R')?{filename:changes[i++],previous_filename:first,status:'renamed'}:{filename:first,status:{A:'added',M:'modified',D:'removed'}[status]});}
need(files.length===pr.changed_files,'Incomplete actual PR file inventory');
const bytes=validateEvidencePartitions(index,{readFile:read,files,branch:pr.head.ref,workerId:index.worker_id,issueNumber:index.issue});
const comments=await githubPages(async route=>gh(route),`/repos/${repo}/issues/${number}/comments`);
const root=selectAggregateReview(comments,head),aggregate=reviewMarker(root,'worldatlas-review-aggregate'),rootReceipt=reviewMarker(root,'worldatlas-review');
need(aggregate.version===1&&aggregate.pr_number===pr.number&&aggregate.author_worker_id===index.worker_id&&aggregate.outcome==='accepted'&&aggregate.queue_enforces_aggregate===false,'Wrong aggregate review context/outcome');
need(aggregate.partition_index_sha256===sha256(indexRaw)&&aggregate.root_manifest_sha256===sha256(read(index.root_manifest_path,'candidate')),'Review index/root manifest changed');
need(aggregate.reviewer_worker_id!==index.worker_id&&aggregate.reviewer_worker_id===rootReceipt?.reviewer_worker_id,'Distinct consistent reviewer required');
checkPartitionReviewInventory(aggregate,index);
const reviewed=[];
for(const part of [{path:index.root_manifest_path,change_paths:index.root_change_paths,is_root:true},...index.partitions]){
 const manifestRaw=read(part.path,'candidate'),manifest=JSON.parse(manifestRaw),limits=validateEvidence(manifest,{readFile:read}).limits;
 let receipt=rootReceipt,comment=root;
 if(!part.is_root){
  const binding=aggregate.partitions.find(row=>row.manifest_path===part.path);
  need(binding?.manifest_sha256===sha256(manifestRaw),'Review partition manifest changed');
  ({comment,receipt}=boundPartitionReview(binding,comments,{head,reviewer:aggregate.reviewer_worker_id}));
 }
 need(receipt?.reviewer_worker_id===aggregate.reviewer_worker_id,'Partition reviewer differs');
 const assigned=files.filter(row=>part.change_paths.includes(row.filename));
 validateReviewReceipt(receipt,{pr,manifest,manifestHash:sha256(manifestRaw),files:assigned,limits,author:index.worker_id,reviewKind:'release'});
 reviewed.push({manifest_path:part.path,manifest_sha256:sha256(manifestRaw),comment_id:comment.id,assigned_files:assigned.length});
}
console.log(JSON.stringify({version:1,verified:true,pr_number:pr.number,head_sha:head,reviewer_worker_id:aggregate.reviewer_worker_id,root_comment_url:root.html_url,queue_enforces_aggregate:false,changed_files:bytes.changed_files_verified,baseline_files:bytes.baseline_files_verified,preserved_files:bytes.preserved_files_verified,partitions:reviewed,published:false},null,2));
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url))await main();
