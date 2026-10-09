import concurrent.futures,json,subprocess,collections
from pathlib import Path
root=Path('/tmp/worldatlas-p0-1543-checkpoint/global-hour-audit');day=json.loads((root/'day-inventory.json').read_text())
rows=[r for r in day['runs'] if r['path'] in ['.github/workflows/worker-merge.yml','.github/workflows/merge-scheduler.yml']]
def read(r):
 out={k:r[k] for k in ['id','path','name','event','created_at','conclusion','run_attempt']}
 if r['status']!='completed':return dict(out,limit='live run')
 p=subprocess.run(['gh','run','view',str(r['id']),'--repo','ChengshuLi/WorldAtlas','--log'],capture_output=True,text=True,timeout=100)
 if p.returncode:return dict(out,limit='log unavailable')
 if len(p.stdout.encode())>64*1024*1024:raise ValueError('Oversized log')
 latest={};capacity=[];quota=[]
 for line in p.stdout.splitlines():
  parts=line.split('\t',2)
  if len(parts)!=3:continue
  at=parts[2].find('{')
  if at<0:continue
  try:v=json.loads(parts[2][at:])
  except ValueError:continue
  if not isinstance(v,dict):continue
  a=v.get('request_accounting')
  if isinstance(a,dict) and isinstance(a.get('actual_http_attempts'),int):latest[(parts[0],a.get('phase'))]={'job':parts[0],**a}
  c=v.get('final_capacity')
  if isinstance(c,dict):capacity.append({k:c.get(k) for k in ['phase','limit','remaining','reset','required','validation_call_bound','waited_ms','status']})
  e=v.get('github')
  if isinstance(e,dict) and e.get('http_status') in [403,429]:quota.append({k:e.get(k) for k in ['http_status','rate_remaining','rate_reset','retry_after']})
 out['accounting']=list(latest.values());out['recorded_attempts']=sum(a['actual_http_attempts'] for a in latest.values());out['capacity']=capacity[-2:];out['refusals']=quota
 if not latest:out['limit']='no accounting receipt; not zero'
 return out
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 result=[]
 for i,r in enumerate(pool.map(read,rows)):
  result.append(r)
  if (i+1)%25==0:print(json.dumps({'completed_daily_log_reads':i+1,'total':len(rows)}),flush=True)
summary={'window':{'start':day['start'],'end':day['end']},'runs':result,'recorded_attempts_lower_bound':sum(r.get('recorded_attempts',0) for r in result)}
(root/'day-demand.json').write_text(json.dumps(summary,indent=2)+'\n')
by=collections.defaultdict(lambda:{'runs':0,'accounted_runs':0,'requests':0,'phase_requests':collections.Counter(),'route_requests':collections.Counter()})
for r in result:
 b=by[r['path']];b['runs']+=1;b['accounted_runs']+=bool(r.get('accounting'));b['requests']+=r.get('recorded_attempts',0)
 for a in r.get('accounting',[]):
  b['phase_requests'][a['phase']]+=a['actual_http_attempts']
  for k,v in a['counts'].items():b['route_requests'][k.split(':')[1]]+=v
print(json.dumps({'observed_requests':by,'recorded_lower_bound':summary['recorded_attempts_lower_bound']}))
