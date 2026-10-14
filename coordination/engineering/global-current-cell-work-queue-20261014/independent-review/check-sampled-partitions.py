import json,gzip,struct,hashlib,resource,bisect
from pathlib import Path
D=Path('/workspace/scratch/127991fc8b8e/global-unassigned-census-20261014')
features=json.load(open(D/'source-feature-roster.json')); summary=json.load(open(D/'source-census-summary.json')); physical=json.load(open(D/'source-physical-join-summary.json')); queue=json.load(open(D/'source-package-queue.json'))
c=summary['counts'];assert c['all_source_covered_owner0']==c['unique_candidate_owner0']+c['ambiguous_candidate_owner0']+c['unmapped_source_only_owner0']; assert c['mapped_candidate_owner0']==c['unique_candidate_owner0']+c['ambiguous_candidate_owner0']; assert sum(x['native_cells'] for x in queue['packages'])==c['all_source_covered_owner0']; assert len({x['package_id'] for x in queue['packages']})==len(queue['packages'])
assert len(features)==73567 and all(f['source_index']==i+1 for i,f in enumerate(features));assert len(summary['blocks'])==65
for k in c:assert c[k]==sum(b['counts'][k] for b in summary['blocks'])
result={'aggregate_partitions':'pass','tested_blocks':[],'sampled_rows':0,'sampled_segments':0}
def read(prefix,b):
 p=D/f'{prefix}-block-{b:03}.json.gz';raw=p.read_bytes();decoded=gzip.decompress(raw);return raw,decoded,{r['y']:r['runs'] for r in json.loads(decoded)}
def inside(a,z,runs):
 return any(p<=a and z<=q for p,q,*_ in runs)
for b in [3,14,24,32,43,64]:
 enc,dec,rows=read('source-candidates',b); report=summary['blocks'][b];assert hashlib.sha256(enc).hexdigest()==report['sha256'];assert hashlib.sha256(dec).hexdigest()==report['decoded_sha256']
 _,_,free=read('owner0',b);_,_,land=read('physical-support',b);_,_,water=read('inland-water-support',b);_,_,supported=read('source-supported-unique',b)
 ys=sorted(rows);selected=set(ys[i] for i in sorted({0,len(ys)//4,len(ys)//2,3*len(ys)//4,len(ys)-1}) if ys)
 if b==24 and 99412 in rows:selected.add(99412)
 raw={y:[] for y in selected}
 with open(D/f'source-runs-block-{b:03}.u32','rb') as fh:
  while chunk:=fh.read(16):
   y,a,z,s=struct.unpack('<4I',chunk)
   if y in selected:raw[y].append((a,z,s))
 for y in selected:
  events={}
  for a,z,s in raw[y]:events.setdefault(a,[]).append((s,1));events.setdefault(z,[]).append((s,-1))
  active={};expected=[];px=None
  for x,ev in sorted(events.items()):
   if px is not None and x>px and active:
    sids=sorted(active);owners=sorted({o for s in sids for o in features[s-1]['owners']});r=[px,x,owners,sids]
    if expected and expected[-1][1]==px and expected[-1][2:]==r[2:]:expected[-1][1]=x
    else:expected.append(r)
   for s,d in ev:
    active[s]=active.get(s,0)+d;assert active[s]>=0
    if not active[s]:del active[s]
   px=x
  assert not active;assert expected==rows[y],(b,y,'source sweep mismatch')
  last=0
  want=[]
  for a,z,owners,sids in rows[y]:
   assert 0<=a<z<=262166 and a>=last and inside(a,z,free[y]);last=z
   if len(owners)==1:
    for p,q in sorted(land.get(y,[])+water.get(y,[])):
     lo,hi=max(a,p),min(z,q)
     if lo<hi:want.append([lo,hi,owners[0]])
  merged=[]
  for r in want:
   if merged and merged[-1][1]==r[0] and merged[-1][2]==r[2]:merged[-1][1]=r[1]
   else:merged.append(r)
  assert merged==supported.get(y,[]),(b,y,'physical join mismatch')
  for a,z in land.get(y,[]):
   assert inside(a,z,free[y]);assert all(z<=p or a>=q for p,q in water.get(y,[]))
  result['sampled_rows']+=1;result['sampled_segments']+=len(rows[y])
 result['tested_blocks'].append({'block':b,'decoded_source_hash':'pass','sampled_rows':sorted(selected)})
result['max_rss_kib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
Path('/workspace/scratch/127991fc8b8e/global-census-review-20261014/sampled-partition-review.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
