import json,gzip,subprocess,hashlib,os,collections,bisect
from pathlib import Path
D=Path(__file__).resolve().parent;R=D.parent/'worldatlas-primary';Q='b3914bbdd2b6fdcb5e4ae7c860494425fa2c27ea';ROOT='coordination/engineering/global-current-cell-work-queue-20261014/';H=subprocess.check_output(['git','-C',str(R),'rev-parse','origin/main']).decode().strip();inputs=[]
env={**os.environ,'GIT_NO_LAZY_FETCH':'1'}
def raw(path,h=Q):return subprocess.check_output(['git','-c','protocol.allow=never','-C',str(R),'show',h+':'+path],env=env)
def read(path,h=Q):
 b=raw(path,h);inputs.append({'commit':h,'path':path,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()});return json.loads(gzip.decompress(b)if path.endswith('.gz')else b)
def deref(p,h=H):
 b=raw(p['path'],p.get('commit',h));assert len(b)==p['bytes'] and hashlib.sha256(b).hexdigest()==p['sha256'];return json.loads(gzip.decompress(b)if p['path'].endswith('.gz')else b)
q=read(ROOT+'source-package-queue.json');physicalq=read(ROOT+'physical-package-queue.json');package=next(x for x in q['packages']if x['package_id']=='gb-USA-ADM2--repair-evaluation');roster=read(ROOT+'source-feature-roster.json.gz');sc=read(ROOT+'source-census-summary.json');ph=read(ROOT+'physical-unassigned-summary.json');wanted=set(package['owners']);rows=[]
def readblock(kind,b):
 item=sc['blocks'][b]if kind=='source-candidates'else next(x for x in ph['phases'][b]['files']if x['kind']==kind);out=[]
 for part in item.get('parts',[{**item,'path':f'{kind}-block-{b:03d}.json.gz'}]):
  path=ROOT+part['path'];body=raw(path);assert hashlib.sha256(body).hexdigest()==part['sha256'];decoded=gzip.decompress(body);assert hashlib.sha256(decoded).hexdigest()==part['decoded_sha256'];out.extend(json.loads(decoded));inputs.append({'commit':Q,'path':path,'bytes':len(body),'sha256':part['sha256'],'decoded_bytes':len(decoded),'decoded_sha256':part['decoded_sha256']})
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
    for lo,hi in hits(a,z,rr):rows.append([row['y'],lo,hi,owners,sids,kind])
 print('verified immutable block',b,flush=True)
prior=json.loads(gzip.decompress((D.parent/'screen-next-repair-package-20261017'/f"{package['package_id']}.json.gz").read_bytes()));assert rows==prior,'Prior transport differs from immutable reconstruction'
keys=set();classes=collections.Counter();ownerkeys=collections.Counter();byy={}
for y,a,z,owners,sids,kind in rows:
 for x in range(a,z):
  k=y,x,owners[0];assert k not in keys;keys.add(k)
 classes[kind]+=z-a;ownerkeys[owners[0]]+=z-a;byy.setdefault(y,[]).append((a,z,owners[0]))
assert len(keys)==package['native_cells']==107131 and len(rows)==package['interval_segments']==46575 and set(ownerkeys)==wanted and len(wanted)==351
sel=read('data/ownership-selection.json',H);side=deref(sel['additive_release']);patch=deref(side['logical_asset_map']['patch']);overlap=[]
for row in patch['rows']:
 for a,z,o in row['runs']:
  for aa,zz,oo in byy.get(row['y'],[]):
   if max(a,aa)<min(z,zz):overlap.append([row['y'],max(a,aa),min(z,zz),oo,o])
s=json.load(open(D.parent/'screen-next-repair-package-20261017/screening.json'));screen=next(r for r in s['results']if r['package']['package_id']==package['package_id']);ids={r['id']for r in screen['owners']};issues=json.load(open(D/'open-issues.json'));prs=json.load(open(D/'open-prs.json'));matches=[]
for role,records in [('issue',issues),('pr',prs)]:
 for r in records:
  found=sorted(i for i in ids if i in r['body']);pkg=package['package_id']in r['body']
  if found or pkg:matches.append({'kind':role,'number':r['number'],'title':r['title'],'type_labels':[x['name']for x in r.get('labels',[])if x['name'].startswith('type:')],'subject_matches':found,'package_literal':pkg})
result={'kind':'authenticated-whole-original-USA-repair-screen','author_baseline':H,'queue_commit':Q,'source_packages':len(q['packages']),'physical_packages':len(physicalq['packages']),'package':package,'measured_cells':len(keys),'measured_intervals':len(rows),'measured_owners':len(wanted),'physical_classes':dict(classes),'original_transport_exact_immutable_block_equality':True,'accepted_patch':side['logical_asset_map']['patch'],'accepted_cumulative_cells':sum(z-a for r in patch['rows']for a,z,o in r['runs']),'accepted_overlap_cells':sum(r[2]-r[1]for r in overlap),'accepted_overlaps':overlap,'subject_ids':sorted(ids),'open_issue_count':len(issues),'open_pr_count':len(prs),'potential_scope_matches':matches,'inputs':inputs,'limits':['Original queue mapping defines only the frozen request, never positive authority or an exclusion of ownerless foreign originals.','No native/source/physical qualification or accepted repair credit.']}
(D/'scope-screen.json').write_text(json.dumps(result,indent=2)+'\n');(D/'screened-package.json').write_text(json.dumps(screen,indent=2)+'\n');(D/'base.txt').write_text(H+'\n');print(json.dumps({k:result[k]for k in ['source_packages','physical_packages','measured_cells','measured_intervals','measured_owners','physical_classes','accepted_cumulative_cells','accepted_overlap_cells','open_issue_count','open_pr_count','potential_scope_matches']},indent=2))
