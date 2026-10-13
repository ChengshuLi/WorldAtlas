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
// Shared by queue observation and accepted-checkpoint acquisition. A comment is
// insufficient: its reviewed head and merge identity must match the actual PR.
export function verifyAcceptedMergeResult(result, merged, head) {
  if (result?.accepted !== true || result.status !== 'merged' || !/^[a-f0-9]{40}$/.test(result.merge_commit ?? '') ||
      (result.expected_head !== undefined && result.expected_head !== head) ||
      (result.reviewed_head !== undefined && result.reviewed_head !== head))
    throw Error('Malformed or mismatched accepted merge receipt');
  if (!merged?.merged || merged.head?.sha !== head || merged.merge_commit_sha !== result.merge_commit)
    throw Error('Merge receipt differs from actual PR state');
  return result;
}
