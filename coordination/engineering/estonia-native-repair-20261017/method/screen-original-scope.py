import pathlib,json,gzip,hashlib,subprocess,os,collections,bisect,sys
assert len(sys.argv)==4
W=pathlib.Path(sys.argv[1]).absolute();H=sys.argv[2];D=pathlib.Path(sys.argv[3]).absolute();assert len(H)==40 and D.parent.is_dir() and not D.exists() and all(not p.is_symlink() for p in (D,*D.parents));S='b3914bbdd2b6fdcb5e4ae7c860494425fa2c27ea';Q='coordination/engineering/global-current-cell-work-queue-20261014/';K='gb-EST-ADM2--repair-evaluation';pins=[];env={**os.environ,'GIT_NO_LAZY_FETCH':'1','GIT_NO_REPLACE_OBJECTS':'1'};sha=lambda b:hashlib.sha256(b).hexdigest()
def raw(p,c=S):
 cmd=['git','-c','protocol.allow=never','-C',str(W)];meta,name=subprocess.check_output(cmd+['ls-tree','-z',c,'--',p],env=env).rstrip(b'\0').split(b'\t');m,k,oid=meta.decode().split();assert m=='100644' and k=='blob' and name.decode()==p;sz=int(subprocess.check_output(cmd+['cat-file','-s',oid],env=env));assert sz>0;b=subprocess.check_output(cmd+['cat-file','blob',oid],env=env);assert len(b)==sz and hashlib.sha1(b'blob '+str(sz).encode()+b'\0'+b).hexdigest()==oid;pins.append(dict(commit=c,path=p,mode=m,git_blob_oid=oid,bytes=sz,sha256=sha(b)));return b
def read(p,c=S):
 b=raw(p,c);u=gzip.decompress(b) if p.endswith('.gz') else b
 if p.endswith('.gz'):pins[-1].update(decoded_bytes=len(u),decoded_sha256=sha(u))
 return json.loads(u)
def pinned(pin,c=H):
 b=raw(pin['path'],pin.get('commit',c));assert len(b)==pin['bytes'] and sha(b)==pin['sha256'];return json.loads(b)
queue=read(Q+'source-package-queue.json');pkg=next(p for p in queue['packages'] if p['package_id']==K);roster=read(Q+'source-feature-roster.json.gz');sc=read(Q+'source-census-summary.json');ph=read(Q+'physical-unassigned-summary.json');rows=[];wanted=set(pkg['owners']);family=pkg['source_family_index']
def block(kind,n):
 p=sc['blocks'][n] if kind=='source-candidates' else next(p for p in ph['phases'][n]['files'] if p['kind']==kind);parts=p.get('parts',[{**p,'path':kind+'-block-'+str(n).zfill(3)+'.json.gz'}]);rs=[]
 for part in parts:
  b=raw(Q+part['path']);assert sha(b)==part['sha256'];u=gzip.decompress(b);assert sha(u)==part['decoded_sha256'];pins[-1].update(decoded_bytes=len(u),decoded_sha256=sha(u));rs.extend(json.loads(u))
 if 'parts' in p:assert sha((json.dumps(rs,separators=(',',':'),ensure_ascii=False)+'\n').encode())==p['decoded_sha256']
 return rs
def hits(a,z,rs):
 i=bisect.bisect_right(rs,a,key=lambda x:x[1])
 while i<len(rs) and rs[i][0]<z:
  aa,zz,*_=rs[i];l=max(a,aa);r=min(z,zz)
  if l<r:yield l,r
  i+=1
for n in pkg['native_blocks']:
 source=block('source-candidates',n);land={r['y']:r['runs'] for r in block('physical-support',n)};water={r['y']:r['runs'] for r in block('inland-water-support',n)}
 for r in source:
  for a,z,owners,sids in r['runs']:
   if len(owners)!=1 or owners[0] not in wanted:continue
   if min(roster[i-1]['family_index'] for i in sids if roster[i-1]['owners'])!=family:continue
   for kind,rs in [('land',land.get(r['y'],[])),('inland-water',water.get(r['y'],[]))]:
    for l,e in hits(a,z,rs):rows.append([r['y'],l,e,owners,sids,kind])
 print('authenticated original block',n,flush=True)
encoded=(json.dumps(rows,separators=(',',':'))+'\n').encode()
counts=collections.Counter(o[0] for y,a,z,o,s,k in rows);cells=sum(z-a for y,a,z,o,s,k in rows);assert cells==pkg['native_cells'] and len(rows)==pkg['interval_segments'] and set(counts)==wanted
selection=read('data/ownership-selection.json',H);release=pinned(selection['additive_release']);patch=pinned(release['logical_asset_map']['patch']);accepted={r['y']:r['runs'] for r in patch['rows']};overlaps=[]
for y,a,z,owners,sids,k in rows:
 for aa,zz,o in accepted.get(y,[]):
  l=max(a,aa);r=min(z,zz)
  if l<r:overlaps.append(dict(y=y,start=l,end=r,candidate_owner=owners[0],accepted_owner=o))
cat=read('coordination/engineering/original-geography-source-corpus-20261006/catalogue.json',H);products=[]
for p in cat['products']:
 if not p['key'].startswith('gb:EST:'):continue
 buf=[]
 for part in p['parts']:
  b=raw(part['path'],H);assert len(b)==part['bytes'] and sha(b)==part['sha256'];u=gzip.decompress(b);assert len(u)==part['uncompressed_bytes'] and sha(u)==part['uncompressed_sha256'];pins[-1].update(decoded_bytes=len(u),decoded_sha256=sha(u));buf.append(u)
 u=b''.join(buf);assert len(u)==p['original_bytes'] and sha(u)==p['original_sha256'];j=json.loads(u);assert len(j['features'])==p['feature_count'];products.append({k:p[k] for k in ['key','feature_count','advertised_feature_count','original_bytes','original_sha256','recorded_license','source_represented_year_claim']})
lineage=read(Q+'lineage.json.gz');loc={x['index']:x for x in lineage['locations']};original_commit='a61b6f9e7f88b1da380e3a834f89d7509132ed71';path='data/geography/part-8.json';old=raw(path,original_commit);current=raw(path,H);oldfeatures={f['properties']['id']:f for f in json.loads(old)['features']};targetfeatures={f['properties']['id']:f for f in json.loads(current)['features']};prior={'owners':[]}
for o in sorted(wanted):
 l=loc[o];assert l['id'] in targetfeatures and oldfeatures[l['id']]==targetfeatures[l['id']];meta=targetfeatures[l['id']]['properties']['metadata'];prior['owners'].append(dict(index=o,id=l['id'],name=l['name'],candidate_cells=sum(z-a for y,a,z,owners,s,k in rows if owners[0]==o),source_atoms=l['source_atoms'],current_feature=targetfeatures[l['id']]))
checks=[dict(path=path,original_commit=original_commit,current_commit=H,bytes=len(current),sha256=sha(current),selected_package_whole_records_equal=True)]
foreign={r['source_index'] for r in roster if not r['owners'] and not r['source_id'].startswith('gb:EST:')};foreignhits=[r for r in rows if foreign.intersection(r[4])]
result=dict(kind='read-only screening, no new claim or qualification',package_id=K,accepted_head=H,original_cells=cells,original_intervals=len(rows),original_owners=len(counts),physical_classes=dict(collections.Counter({k:sum(z-a for y,a,z,o,s,c in rows if c==k) for k in set(r[5] for r in rows)})),accepted_overlap_cells=sum(r['end']-r['start'] for r in overlaps),accepted_overlaps=overlaps,accepted_cumulative_cells=sum(z-a for r in patch['rows'] for a,z,o in r['runs']),accepted_patch=release['logical_asset_map']['patch'],exact_global_source_physical_interval_reconstruction=True,original_decoded_interval_sha256=sha(encoded),complete_products=products,complete_source_decoded_bytes=sum(p['original_bytes'] for p in products),target_record_checks=checks,declared_source_members=sum(len(o['source_atoms']) for o in prior['owners']),aggregate_targets=[{k:o[k] for k in ['index','id','name','candidate_cells','source_atoms']} for o in prior['owners'] if len(o['source_atoms'])>1],complete_foreign_ownerless_roster_features=len(foreign),foreign_ownerless_original_hit_cells=sum(r[2]-r[1] for r in foreignhits),proposed_owner='/root/complete_uk_repair after independently reviewed PNG handoff and verified clean release; no claim until accepted-outcome and assignment screen completes',original_package=pkg,current_owners=prior['owners'],inputs=pins,limits=['No source-relative qualification, current dry-land, contemporary territorial or legal-boundary approval.','All prior Baltic regional, source-date, administrative-role and source-fitness work must be inspected and preserved; completion outcomes and open claims must be checked before any assignment.','Complete country, physical, source/target intent and historical applicability remain author obligations.'])
assert not D.exists() and all(not p.is_symlink() for p in (D,*D.parents));D.mkdir();(D/(K+'.json.gz')).write_bytes(gzip.compress(encoded,mtime=0));(D/'estonia-screen.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['inputs','aggregate_targets','accepted_patch','complete_products','target_record_checks','limits','current_owners','original_package']}))
