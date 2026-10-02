import {readClaim} from './issue-claim-contract.mjs';

const prefix=kind=>kind==='claim'?'**Reservation result:**':'**Merge result:**';
export function renderWorkerResult(kind,result){
 if(!['claim','merge'].includes(kind))throw Error('Unknown worker result kind');
 const json=JSON.stringify(result).replaceAll('<','\\u003c');
 return `${prefix(kind)} ${result.accepted?'accepted':'not accepted'}\n\nRequest: \`${result.request_id}\`\n\n<!-- worldatlas-${kind}-result:v1\n${json}\n-->`;
}
export function readWorkerResult(comments,kind,request_id,number){
 const field=kind==='claim'?'issue_number':'pr_number';
 const matches=comments.filter(c=>c.user?.login==='github-actions[bot]'&&c.body?.startsWith(prefix(kind))).sort((a,b)=>b.id-a.id);
 for(const comment of matches){
  const match=new RegExp(`<!-- worldatlas-${kind}-result:v1\\n([\\s\\S]*?)\\n-->`).exec(comment.body);
  if(!match)continue;
  let result;try{result=JSON.parse(match[1]);}catch{continue;}
  if(result.request_id!==request_id||result[field]!==number)continue;
  if(typeof result.accepted!=='boolean')throw Error('Malformed worker result');
  return {...result,result_source:'github-comment',result_comment_id:comment.id};
 }
 return null;
}
export function confirmReservation(comments,request,now=Date.now()){
 const result=readWorkerResult(comments,'claim',request.request_id,request.issue_number);
 if(result?.accepted===false)return result;
 const claim=readClaim(comments);
 const exact=claim?.request_id===request.request_id&&claim.issue_number===request.issue_number&&claim.worker_id===request.worker_id&&claim.claim_id===request.claim_id&&claim.branch===request.branch;
 const expectedState=request.action==='release'?claim?.active===false:claim?.active===true&&Date.parse(claim.expires_at)>now;
 // Also supports a trusted older workflow during bootstrap: its canonical state
 // must confirm this exact request, never merely the same worker or branch.
 if(!exact||!expectedState)throw Error('Reservation is not confirmed in current canonical state; do not begin work. Inspect the issue/workflow.');
 return {...(result??{accepted:true,request_id:request.request_id,issue_number:request.issue_number,result_source:'canonical-comment'}),claim};
}
