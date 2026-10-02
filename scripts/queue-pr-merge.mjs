import {execFileSync} from 'node:child_process';
import {randomUUID} from 'node:crypto';
const args=process.argv.slice(2),values={};
for(let i=0;i<args.length;i+=2){if(!['--pr','--head'].includes(args[i])||!args[i+1]||values[args[i]])throw Error('Usage: node scripts/queue-pr-merge.mjs --pr N --head SHA');values[args[i]]=args[i+1];}
if(!/^[1-9]\d*$/.test(values['--pr']??'')||!/^[a-f0-9]{40}$/.test(values['--head']??''))throw Error('Supply the exact PR number and verified head SHA');
const request_id=randomUUID(),repo='ChengshuLi/WorldAtlas';
execFileSync('gh',['workflow','run','worker-merge.yml','--repo',repo,'--ref','main','-f',`pr_number=${values['--pr']}`,'-f',`expected_head=${values['--head']}`,'-f',`request_id=${request_id}`],{stdio:'inherit'});
console.log(JSON.stringify({queued:true,request_id,run_name:`merge #${values['--pr']} ${request_id}`,next_action:'Find this exact run with gh run list, wait for it and read its bot-authored Merge result comment on the PR, matched to this request ID (or verify the actual merged PR/head). Queued/workflow success alone is not proof of an accepted merge. Cancelled requests may be retried; always recheck current main/claim/head.'}));
