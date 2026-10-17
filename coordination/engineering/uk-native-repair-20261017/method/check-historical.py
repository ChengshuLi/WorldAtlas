"""Authenticate the complete earlier candidate cohort and preserve UK native contacts.
Usage: python check-historical.py READ_ONLY_REPO FRESH_OUTPUT
The complete original 95,173-feature cohort is restored with its original delta;
all current native centres are screened, including historical records without UK tags.
"""
import ast,collections,csv,gzip,hashlib,io,json,os,pathlib,resource,subprocess,sys,time
import numpy as np,shapely
from shapely.geometry import shape
W,O=map(lambda s:pathlib.Path(s).absolute(),sys.argv[1:]);H='a9f6ccadcc1bdea6185fcaf5eac7ec00f8c4551a';F='79d17bfd955e14f4e74d92a03ee29f213874cf90';P='coordination/engineering/uk-native-repair-20261017';Q='coordination/engineering/global-gap-candidate-funnel-20261008/inputs/'
assert O.parent.is_dir() and not O.exists() and all(not p.is_symlink() for p in (O,*O.parents))
started=time.monotonic();pins={};total=0;MAX=32*1024*1024;PHASE=768*1024*1024
sha=lambda b:hashlib.sha256(b).hexdigest()
canonical=lambda j:(json.dumps(j,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
env={**os.environ,'GIT_NO_LAZY_FETCH':'1','GIT_NO_REPLACE_OBJECTS':'1'}
def read(path,commit=H,expected=None,decode=None):
 global total
 assert time.monotonic()-started<300 and path and not path.startswith('/') and all(x not in ['', '.', '..'] for x in path.split('/'))
 command=['git','-c','protocol.allow=never','-C',str(W)]
 meta,member=subprocess.check_output(command+['ls-tree','-z',commit,'--',path],env=env).rstrip(b'\0').split(b'\t');mode,kind,oid=meta.decode().split();assert mode=='100644' and kind=='blob' and member.decode()==path
 size=int(subprocess.check_output(command+['cat-file','-s',oid],env=env));assert 0<size<=MAX
 b=subprocess.check_output(command+['cat-file','blob',oid],env=env);assert len(b)==size and hashlib.sha1(b'blob '+str(size).encode()+b'\0'+b).hexdigest()==oid
 pin={'path':path,'commit':commit,'mode':mode,'git_blob_oid':oid,'bytes':len(b),'sha256':sha(b)}
 if expected:assert len(b)==expected['bytes'] and sha(b)==expected['sha256']
 if decode or decode is None and path.endswith('.gz'):
  with gzip.GzipFile(fileobj=io.BytesIO(b)) as f:d=f.read(MAX+1)
  assert len(d)<=MAX;pin.update(decoded_bytes=len(d),decoded_sha256=sha(d));b=d
  if expected:assert len(b)==expected['uncompressed_bytes'] and sha(b)==expected['uncompressed_sha256']
 if (commit,path) not in pins:total+=size+pin.get('decoded_bytes',0)
 assert total<=PHASE;pins[(commit,path)]=pin;return b
cfg=json.loads(read('coordination/engineering/global-actionability-routing-20261007/input-config.json'))
rows={};header=None
for i in range(1,8):
 reader=csv.DictReader(io.StringIO(read(Q+f'components-{i:02}.csv.gz').decode()),fieldnames=header);header=reader.fieldnames
 for r in reader:assert r['component_id'] not in rows;rows[r['component_id']]=r
assert len(rows)==cfg['current_components']==cfg['expected']['components']
original=[]
for d in cfg['candidate_inputs']:
 if d['kind']=='components':original+=json.loads(read(d['path'],d['commit'],d,True))['features']
delta_pin=next(d for d in cfg['candidate_inputs'] if d['kind']=='components_delta');delta=json.loads(read(delta_pin['path'],delta_pin['commit'],delta_pin,True))
program=cfg['existing_reconstructor'];code=read(program['path'],program['commit']);assert sha(code)==program['sha256'];tree=ast.parse(code.decode());node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='reconstruct');excerpt=ast.get_source_segment(code.decode(),node)+'\n';scope={'canonical_json':canonical,'digest':sha};exec(compile(excerpt,program['path']+':reconstruct','exec'),scope);current=scope['reconstruct'](original,delta);del original
assert len(current)==len(rows) and sha(canonical(current))==cfg['current_records_sha256']
for f in current:
 r=rows[f['id']];assert sha(canonical(f))==r['current_feature_sha256'] and sha(canonical(f['geometry']))==r['current_geometry_sha256']
segments=[]
for b in range(18,22):segments+=json.loads(read(P+f'/frozen-queue/block-{b:03}.json.gz',F))
cells=[(x,y,oo[0]) for y,a,z,oo,ss,kind in segments for x in range(a,z)];assert len(cells)==89390
ownership=json.loads(read('coordination/engineering/global-current-cell-work-queue-20261014/ownership-binding.json'));lp=ownership['native_latitudes'];lat=np.frombuffer(read(lp['path'],lp['commit'],dict(lp,uncompressed_bytes=lp['decoded_bytes'],uncompressed_sha256=lp['decoded_sha256']),True),dtype='<f8');assert len(lat)==262166
pts=shapely.points([[(x+.5)/262166*360-180,lat[y]] for x,y,o in cells]);index=shapely.STRtree(pts);contacts=[];invalid=[];retained=[];hitkeys=set();ukids=set()
for f in current:
 assert time.monotonic()-started<300
 r=rows[f['id']];tagged='gb:GBR:' in r['source_products'] or 'gb:GBR:' in r['unique_source_subject_id']
 if tagged:ukids.add(f['id'])
 g=shape(f['geometry']);candidates=index.query(g)
 if len(candidates) and not g.is_valid:
  invalid.append({'id':f['id'],'candidate_indices_in_bounds':[int(i) for i in candidates],'original':r});continue
 ix=[] if not len(candidates) else [int(i) for i in candidates[shapely.covers(g,pts[candidates])]]
 if ix:
  hitkeys.update(ix);contacts.append({'id':f['id'],'cells':[[*cells[i]] for i in sorted(ix)],'routing':r,'original_feature':f})
 if tagged:retained.append(r)
result={'version':1,'original_repair_cells':len(cells),'complete_historical_candidates':len(current),'complete_historical_routing_rows':len(rows),'complete_original_candidate_hash':cfg['current_records_sha256'],'complete_candidate_reconstruction':{'program':program,'extracted_function_sha256':sha(excerpt.encode()),'delta_original_count':delta['original_count'],'delta_current_count':delta['current_count']},'uk_source_tagged_candidates':len(retained),'uk_source_tagged_rows':retained,'native_overlap_candidates':len(contacts),'native_overlap_cells':len(hitkeys),'native_overlap_rows':contacts,'invalid_candidates_with_native_bbox_contacts':invalid,'all_original_held_dispositions_preserved':True,'inputs':list(pins.values()),'processing_bytes':total,'elapsed_seconds':time.monotonic()-started,'max_rss_linux_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'limits':['Complete earlier 95,173-component cohort and all routing rows screened; source tags are contextual, not used to omit spatial competitors.','Earlier whole-candidate unknowns and physical-unapproved statuses remain unchanged; point overlap is not a candidate approval or current dry-land/legal classification.','Native source-relative qualification separately establishes exact original repair-centre support; no historical evidence is promoted to positive authority.','Finite cooperative 300-second and 768-MiB processing allowances; measured RSS is not process-tree containment.']}
body=(json.dumps(result,ensure_ascii=False,separators=(',',':'))+'\n').encode();assert total+len(body)<=PHASE and len(body)<=MAX
assert O.parent.is_dir() and not O.exists() and all(not p.is_symlink() for p in (O,*O.parents));O.mkdir()
with (O/'historical-applicability.json').open('xb') as f:f.write(body)
with (O/'preparation.json').open('x') as f:json.dump({'complete':True,'bytes':len(body),'sha256':sha(body)},f);f.write('\n')
print(json.dumps({k:result[k] for k in ['complete_historical_candidates','uk_source_tagged_candidates','native_overlap_candidates','native_overlap_cells','processing_bytes','elapsed_seconds','max_rss_linux_kib']}))
