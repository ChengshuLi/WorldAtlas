import concurrent.futures,json,subprocess
from pathlib import Path
root=Path('/tmp/worldatlas-p0-1543-checkpoint')
rows=json.loads((root/'global-hour-audit/day-inventory.json').read_text())['runs']
rows=[r for r in rows if r['name']=='Handoff lane scope']
def read(row):
 p=subprocess.run(['gh','run','view',str(row['id']),'--repo','ChengshuLi/WorldAtlas','--log'],capture_output=True,text=True,timeout=100)
 result={k:row[k] for k in ['id','conclusion','created_at','head_branch','head_sha']}
 if p.returncode:return dict(result,limit='log unavailable')
 if len(p.stdout.encode())>64*1024*1024:raise ValueError('Oversized log')
 reports=[]
 for line in p.stdout.splitlines():
  parts=line.split('\t',2)
  if len(parts)!=3 or parts[0]!='evidence':continue
  at=parts[2].find('{')
  if at<0:continue
  try:v=json.loads(parts[2][at:])
  except ValueError:continue
  if not isinstance(v,dict) or not isinstance(v.get('status'),str):continue
  checked=v.get('checked')
  reports.append({'status':v['status'],'authenticated_unique_descriptor_keys':len(set(checked)) if isinstance(checked,list) else None,'manifest_sha256':v.get('manifest_sha256'),'http_accounting':v.get('request_accounting'),'transport':v.get('immutable_transport')})
 result['reports']=reports
 if reports and reports[-1]['authenticated_unique_descriptor_keys'] is not None:
  result['code_derived_blob_request_lower_bound']=reports[-1]['authenticated_unique_descriptor_keys']+1
  result['derivation']='Old remoteReader loads each unique vintage:path through REST, plus a separately read manifest. Excludes unchanged comparison bytes and metadata; inferred from successful receipt and trusted code, not HTTP telemetry.'
 return result
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 out=[]
 for i,r in enumerate(pool.map(read,rows)):
  out.append(r)
  if (i+1)%50==0:print(json.dumps({'completed_daily_evidence_log_reads':i+1,'total':len(rows)}),flush=True)
summary={'runs':out,'successful_evidence_receipts':sum('code_derived_blob_request_lower_bound' in r for r in out),'inferred_old_blob_requests_lower_bound':sum(r.get('code_derived_blob_request_lower_bound',0) for r in out),'limits':['Not a measured whole-installation total. Failed and cancelled requests, metadata, comparison originals, and action internals are uncounted.']}
(root/'global-hour-audit/day-evidence-demand.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k!='runs'}))
