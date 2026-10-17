import collections,gzip,hashlib,json,math,os,resource,signal,subprocess,time
resource.setrlimit(resource.RLIMIT_AS,(1024**3,1024**3));signal.alarm(120)
H='b83e2be4fab976d9c00f74ab087c16121dfb26a6';B='07d177c76bc5172fd5cce78621ed4cd8d992c4c3';P='coordination/engineering/tanzania-native-repair-recovery-20261017/'
def read(p,c=H):return subprocess.check_output(['git','-c','protocol.allow=never','show',c+':'+p],env={**os.environ,'GIT_NO_LAZY_FETCH':'1','GIT_NO_REPLACE_OBJECTS':'1','GIT_CONFIG_GLOBAL':'/dev/null'})
def js(p,c=H):return json.loads(read(p,c))
def boxes(g):
 assert set(g)=={'type','coordinates'} and g['type'] in ('Polygon','MultiPolygon')
 polys=[g['coordinates']]if g['type']=='Polygon'else g['coordinates'];assert polys
 out=[]
 for poly in polys:
  assert poly;xs=[];ys=[];seam=False
  for ring in poly:
   assert len(ring)>=4 and ring[0]==ring[-1]
   prev=None
   for q in ring:
    assert len(q)==2 and all(isinstance(n,(float,int))and math.isfinite(n)for n in q)and abs(q[0])<=180 and abs(q[1])<=90
    xs.append(q[0]);ys.append(q[1]);seam|=prev is not None and abs(prev-q[0])>180;prev=q[0]
  west,east=min(xs),max(xs)
  if seam or east-west>180:west,east=-180,180
  out.append([west,min(ys),east,max(ys)])
 return out
def touch(a,b):return not(a[0]>b[2]or b[0]>a[2]or a[1]>b[3]or b[1]>a[3])
start=time.monotonic();report=js(P+'source-review/foreign-bounds-001/complete-foreign-bounds.json');catalog=js('coordination/engineering/original-geography-source-corpus-20261006/catalogue.json',B);stages=js(P+'source-stage-001/original-stage-inputs.json');targets={s['target']:boxes(s['consumed']['geometry'])for s in stages};allboxes=[b for bs in targets.values()for b in bs];overall=[min(b[0]for b in allboxes),min(b[1]for b in allboxes),max(b[2]for b in allboxes),max(b[3]for b in allboxes)]
expected={r['source_family']:r for r in report['families']};n=selected=unsupported=0
for rec in catalog['products']:
 if rec['key'].startswith('gb:TZA:'):continue
 chunks=[]
 for p in rec['parts']:
  raw=read(p['path'],B);assert len(raw)==p['bytes']and hashlib.sha256(raw).hexdigest()==p['sha256'];d=gzip.decompress(raw);assert len(d)==p['uncompressed_bytes']and hashlib.sha256(d).hexdigest()==p['uncompressed_sha256'];chunks.append(d)
 raw=b''.join(chunks);assert len(raw)==rec['original_bytes']and hashlib.sha256(raw).hexdigest()==rec['original_sha256'];fc=json.loads(raw);del chunks,raw,d
 e=expected[rec['key']];want={r['source_id']:r for r in e['selected_features']};bad={r['source_id']for r in e['unsupported_features']};seen=set();got=set();gotbad=set()
 for f in fc['features']:
  sid=rec['key']+':'+f['properties']['shapeID'];assert sid not in seen;seen.add(sid)
  try:bb=boxes(f['geometry'])
  except AssertionError:gotbad.add(sid);continue
  contacts=[]
  if any(touch(z,overall)for z in bb):contacts=[k for k,ts in targets.items()if any(touch(z,t)for z in bb for t in ts)]
  if contacts:
   got.add(sid);assert sid in want and bb==want[sid]['whole_part_bounds'];assert set(contacts)=={r['source_id']for r in want[sid]['targets']}
 assert got==set(want)and gotbad==bad and len(seen)==e['complete_features'];n+=len(seen);selected+=len(got);unsupported+=len(gotbad)
assert (len(expected),n,selected,unsupported)==(366,73367,87,3)
print(json.dumps({'head':H,'independent_complete_foreign_families':366,'original_features':n,'exact_contacts':selected,'exact_unsupported':unsupported,'all_per_contact_target_sets_and_bounds_equal':True,'elapsed_seconds':time.monotonic()-start,'max_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'limits':'Independent read-only complete original bbox derivation; not point membership, physical/native authority or contemporary boundary approval.'}))
