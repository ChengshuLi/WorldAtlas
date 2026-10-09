import json,concurrent.futures,subprocess,collections
from pathlib import Path
root=Path('/tmp/worldatlas-p0-1543-checkpoint/global-hour-audit');day=json.loads((root/'day-inventory.json').read_text());rows=[r for r in day['runs'] if r['path'].endswith('issue-claims.yml')]
def read(r):
 out={k:r[k] for k in ['id','created_at','conclusion']};out['action']=r['name'].split()[0]
 p=subprocess.run(['gh','run','view',str(r['id']),'--repo','ChengshuLi/WorldAtlas','--log'],capture_output=True,text=True,timeout=100)
 if p.returncode:return dict(out,limit='log unavailable')
 if len(p.stdout.encode())>64*1024*1024:raise ValueError('Oversized log')
 result=None
 for line in p.stdout.splitlines():
  parts=line.split('\t',2)
  if len(parts)!=3:continue
  at=parts[2].find('{')
  if at<0:continue
  try:v=json.loads(parts[2][at:])
  except ValueError:continue
  if isinstance(v,dict) and isinstance(v.get('accepted'),bool) and 'issue_number' in v:result=v
 if result:
  out['accepted']=result['accepted'];out['mode']=(result.get('claim') or {}).get('mode')
  if result['accepted']:
   out['code_derived_minimum_requests']=8+(2 if out['mode']=='geography' and out['action']!='release' else 0)+(1 if out['action']!='renew' else 0)
   out['derivation']='Two issue/comment/timeline snapshots, canonical mutation, result notification; geography ownership snapshots and non-renew progress. Excludes linked PRs, dependencies, extra pages and labels.'
  out['accounting']=result.get('request_accounting')
 else:out['limit']='No parseable claim result; not zero'
 return out
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 out=[]
 for i,r in enumerate(pool.map(read,rows)):
  out.append(r)
  if (i+1)%50==0:print(json.dumps({'claim_log_reads':i+1,'total':len(rows)}),flush=True)
summary={'runs':out,'accepted':sum(r.get('accepted') is True for r in out),'refused':sum(r.get('accepted') is False for r in out),'inferred_request_floor':sum(r.get('code_derived_minimum_requests',0) for r in out)}
(root/'day-claims.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({k:v for k,v in summary.items() if k!='runs'}))
