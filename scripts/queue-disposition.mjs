import {createHash} from 'node:crypto';

// A reviewed handoff records decisions; it never grants approval or closes work.
export const scopeDigest = scope => createHash('sha256').update(JSON.stringify(scope)).digest('hex');
function latestMarker(comments) {
  let latest;
  for (const comment of [...comments].sort((a,b)=>a.id-b.id)) {
    for (const match of String(comment.body ?? '').matchAll(/<!-- worldatlas-queue-disposition:v1\s*\n([\s\S]*?)\n-->/g)) {
      latest={comment_id:comment.id,raw:match[1]};
    }
  }
  return latest;
}
export function dispositionReferences(comments) {
  try {
    const marker=latestMarker(comments);
    const value=marker && JSON.parse(marker.raw);
    if(!Array.isArray(value?.criteria) || value.criteria.length>100)return [];
    const ids=[...new Set(value.criteria.flatMap(row=>Array.isArray(row.follow_up_issues) && row.follow_up_issues.length<=50 ? row.follow_up_issues : []))].filter(id=>Number.isSafeInteger(id) && id>0);
    return ids.length<=50 ? ids : [];
  } catch { return []; }
}
export function readQueueDisposition(comments,{issue,scope,prs,relatedIssues=[]}) {
  const marker=latestMarker(comments);
  if (!marker) return {value:null};
  try {
    const value=JSON.parse(marker.raw);
    const need=(ok,message)=>{if(!ok)throw Error(message);};
    need(value.version===1 && value.issue===issue.number && value.scope_sha256===scopeDigest(scope), 'Disposition must bind the current issue scope');
    const merged=prs.filter(pr=>pr.merged_at).map(pr=>pr.number).sort((a,b)=>a-b);
    need(JSON.stringify(value.merged_prs)===JSON.stringify(merged), 'Disposition must bind the exact sorted merged-PR list');
    need(Array.isArray(value.criteria) && value.criteria.length>0 && value.criteria.length<=100, 'Map every acceptance criterion before recording a disposition');
    need(new Set(value.criteria.flatMap(row=>row.follow_up_issues??[])).size<=50, 'Disposition exceeds bounded follow-up inventory');
    for (const row of value.criteria) {
      need(typeof row.criterion==='string' && row.criterion.trim() && ['satisfied','remaining'].includes(row.status), 'Each criterion needs a reviewed status');
      need(Array.isArray(row.evidence) && row.evidence.length>0 && row.evidence.every(url=>typeof url==='string' && /^https:\/\//.test(url)), 'Each criterion needs durable evidence links');
      need(Array.isArray(row.follow_up_issues) && row.follow_up_issues.length<=50, 'Each criterion needs explicit follow-up issue numbers');
      need(row.status==='remaining' ? row.follow_up_issues.length>0 : row.follow_up_issues.length===0, 'Remaining work needs linked issues; satisfied work has none');
      need(row.follow_up_issues.every(id=>Number.isSafeInteger(id) && id>0 && id!==issue.number && relatedIssues.some(other=>other.number===id && !other.pull_request)), 'Follow-ups must be real distinct issues, not PRs or missing references');
    }
    return {value:{...value,comment_id:marker.comment_id}};
  } catch(e) {return {value:null,error:e.message};}
}
