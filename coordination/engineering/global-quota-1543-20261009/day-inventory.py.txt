import json,subprocess,datetime,collections
from pathlib import Path
root=Path('/tmp/worldatlas-p0-1543-checkpoint/global-hour-audit')
end=datetime.datetime(2026,10,9,2,5,tzinfo=datetime.timezone.utc);start=end-datetime.timedelta(hours=24)
rows={};windows=[]
for offset in range(4):
 a=start+datetime.timedelta(hours=6*offset);b=a+datetime.timedelta(hours=6)
 query=a.strftime('%Y-%m-%dT%H:%M:%SZ')+'..'+b.strftime('%Y-%m-%dT%H:%M:%SZ')
 pages=0;count=None
 for page in range(1,11):
  raw=subprocess.check_output(['gh','api','repos/ChengshuLi/WorldAtlas/actions/runs','--method','GET','-f','created='+query,'-f','per_page=100','-f','page='+str(page)],timeout=60)
  v=json.loads(raw);count=v['total_count'];pages+=1
  for r in v['workflow_runs']:rows[r['id']]={k:r.get(k) for k in ['id','name','path','event','head_branch','head_sha','created_at','run_started_at','updated_at','status','conclusion','run_attempt']}
  if len(v['workflow_runs'])<100:break
 if count>1000:raise ValueError('Window capped; split further')
 windows.append({'query':query,'reported_total':count,'pages':pages})
result={'start':start.isoformat(),'end':end.isoformat(),'windows':windows,'runs':sorted(rows.values(),key=lambda r:r['created_at'])}
(root/'day-inventory.json').write_text(json.dumps(result,indent=2)+'\n')
workflows=collections.Counter(r['path'] for r in rows.values());events=collections.Counter(r['event'] for r in rows.values());conclusions=collections.Counter(str(r['conclusion']) for r in rows.values())
print(json.dumps({'complete_inventory_runs':len(rows),'windows':windows,'workflows':workflows,'events':events,'conclusions':conclusions}))
