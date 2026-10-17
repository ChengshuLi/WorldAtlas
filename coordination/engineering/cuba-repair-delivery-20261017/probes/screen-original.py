import json,gzip,subprocess,hashlib,os,collections,bisect
from pathlib import Path
D=Path(__file__).resolve().parent;R=D.parent/'worldatlas-primary';Q='b3914bbdd2b6fdcb5e4ae7c860494425fa2c27ea';ROOT='coordination/engineering/global-current-cell-work-queue-20261014/';H='3b3e9e675cfb37999d5665438f9fbf25bbd4238b';inputs=[]
env={**os.environ,'GIT_NO_LAZY_FETCH':'1','GIT_TERMINAL_PROMPT':'0','GIT_NO_REPLACE_OBJECTS':'1'}
def sha(b):return hashlib.sha256(b).hexdigest()
def raw(path,h=Q):return subprocess.check_output(['git','-c','protocol.allow=never','-C',str(R),'show',h+':'+path],env=env)
def read(path,h=Q):
 b=raw(path,h);inputs.append({'commit':h,'path':path,'bytes':len(b),'sha256':sha(b)});return json.loads(gzip.decompress(b)if path.endswith('.gz')else b)
def deref(p,h=H):
 b=raw(p['path'],p.get('commit',h));assert len(b)==p['bytes'] and sha(b)==p['sha256'];inputs.append({'commit':p.get('commit',h),**p});return json.loads(gzip.decompress(b)if p['path'].endswith('.gz')else b)
q=read(ROOT+'source-package-queue.json');physicalq=read(ROOT+'physical-package-queue.json');package=next(x for x in q['packages']if x['package_id']=='gb-CUB-ADM2--repair-evaluation');roster=read(ROOT+'source-feature-roster.json.gz');sc=read(ROOT+'source-census-summary.json');ph=read(ROOT+'physical-unassigned-summary.json');lineage=read(ROOT+'lineage.json.gz');lo={x['index']:x for x in lineage['locations']};wanted=set(package['owners']);rows=[]
def readblock(kind,b):
 item=sc['blocks'][b]if kind=='source-candidates'else next(x for x in ph['phases'][b]['files']if x['kind']==kind);out=[]
 for part in item.get('parts',[{**item,'path':f'{kind}-block-{b:03d}.json.gz'}]):
  path=ROOT+part['path'];body=raw(path);assert sha(body)==part['sha256'];decoded=gzip.decompress(body);assert sha(decoded)==part['decoded_sha256'];out.extend(json.loads(decoded));inputs.append({'commit':Q,'path':path,'bytes':len(body),'sha256':part['sha256'],'decoded_bytes':len(decoded),'decoded_sha256':part['decoded_sha256']})
 if 'parts' in item:assert sha((json.dumps(out,separators=(',',':'),ensure_ascii=False)+'\n').encode())==item['decoded_sha256']
 return out
def hits(a,z,rr):
 i=bisect.bisect_right(rr,a,key=lambda r:r[1])
 while i<len(rr)and rr[i][0]<z:
  aa,zz,*_=rr[i];lo=max(a,aa);hi=min(z,zz)
  if lo<hi:yield lo,hi
  i+=1
for b in package['native_blocks']:
 source=readblock('source-candidates',b);land={r['y']:r['runs']for r in readblock('physical-support',b)};water={r['y']:r['runs']for r in readblock('inland-water-support',b)}
 for row in source:
  for a,z,owners,sids in row['runs']:
   if len(owners)!=1 or owners[0]not in wanted:continue
   mapped=[i for i in sids if roster[i-1]['owners']]
   if min(roster[i-1]['family_index']for i in mapped)!=package['source_family_index']:continue
   for kind,rr in [('land',land.get(row['y'],[])),('inland-water',water.get(row['y'],[]))]:
    for lo_,hi in hits(a,z,rr):rows.append([row['y'],lo_,hi,owners,sids,kind])
 print('verified original block',b,flush=True)
keys=set();classes=collections.Counter();ownerkeys=collections.Counter();byy={}
for y,a,z,owners,sids,kind in rows:
 for x in range(a,z):
  k=y,x,owners[0];assert k not in keys;keys.add(k)
 classes[kind]+=z-a;ownerkeys[owners[0]]+=z-a;byy.setdefault(y,[]).append((a,z,owners[0]))
assert len(keys)==package['native_cells']==26459 and len(rows)==package['interval_segments']==8489 and set(ownerkeys)==wanted and len(wanted)==87
sel=read('data/ownership-selection.json',H);side=deref(sel['additive_release']);patch=deref(side['logical_asset_map']['patch']);overlap=[]
for row in patch['rows']:
 for a,z,o in row['runs']:
  for aa,zz,oo in byy.get(row['y'],[]):
   if max(a,aa)<min(z,zz):overlap.append([row['y'],max(a,aa),min(z,zz),oo,o])
cat=read('coordination/engineering/original-geography-source-corpus-20261006/catalogue.json',H);source_checks=[]
family_keys={':'.join(r['source_id'].split(':')[:3])for r in roster if r['family_index']in package['source_families']}
for key in sorted(family_keys):
 p=next(p for p in cat['products']if p['key']==key);pieces=[]
 for part in p['parts']:
  b=raw(part['path'],H);assert len(b)==part['bytes'] and sha(b)==part['sha256'];d=gzip.decompress(b);assert len(d)==part['uncompressed_bytes']and sha(d)==part['uncompressed_sha256'];assert sum(map(len,pieces))==part['offset'];pieces.append(d);inputs.append({'commit':H,'path':part['path'],'bytes':len(b),'sha256':sha(b),'decoded_bytes':len(d),'decoded_sha256':sha(d)})
 body=b''.join(pieces);assert len(body)==p['original_bytes']and sha(body)==p['original_sha256'];features=json.loads(body)['features'];assert len(features)==p['feature_count'];source_checks.append({k:p.get(k)for k in ['key','feature_count','advertised_feature_count','original_bytes','original_sha256','recorded_consumed_url','recorded_license','source_represented_year_claim']})
issues=json.load(open(D/'open-issues.json'));prs=json.load(open(D/'open-prs.json'));ids={lo[o]['id']for o in wanted};matches=[]
for role,records in [('issue',issues),('pr',prs)]:
 for r in records:
  found=sorted(i for i in ids if i in r.get('body',''));pkg=package['package_id']in r.get('body','');country='cuba' in (r['title']+' '+r.get('body','')).lower()
  if found or pkg or country:matches.append({'kind':role,'number':r['number'],'title':r['title'],'url':r['url'],'subject_matches':found,'package_literal':pkg,'country_text':country})
transport=gzip.compress((json.dumps(rows,separators=(',',':'))+'\n').encode(),mtime=0);(D/'original-intervals.json.gz').write_bytes(transport)
result={'kind':'read-only-original-Cuba-proposal-screen','accepted_head':H,'queue_commit':Q,'source_packages':len(q['packages']),'physical_packages':len(physicalq['packages']),'package':package,'measured_cells':len(keys),'measured_intervals':len(rows),'measured_owners':len(wanted),'physical_classes':dict(classes),'accepted_cumulative_cells':sum(z-a for r in patch['rows']for a,z,o in r['runs']),'accepted_overlap_cells':sum(r[2]-r[1]for r in overlap),'accepted_overlaps':overlap,'owners':[{**lo[o],'original_cells':ownerkeys[o]}for o in sorted(wanted)],'complete_declared_source_checks':source_checks,'open_issue_count':len(issues),'open_pr_count':len(prs),'potential_scope_matches':matches,'inputs':inputs,'transport':{'path':'original-intervals.json.gz','bytes':len(transport),'sha256':sha(transport)},'limits':['No claim or scientific qualification has been made.','Original queue owner mapping is only the frozen requested scope; complete ownerless foreign originals must be tested separately.','Current source authority, actual construction intent and unresolved obligations still require substantive review.']}
(D/'screening.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k]for k in ['accepted_head','measured_cells','measured_intervals','measured_owners','physical_classes','accepted_cumulative_cells','accepted_overlap_cells','complete_declared_source_checks','potential_scope_matches']},indent=2))
