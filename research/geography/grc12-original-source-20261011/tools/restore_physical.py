"""Independent whole-shard exact inverse; no physical or geometric calculation."""
import gzip,hashlib,io,json,pathlib,resource,subprocess,sys,time,os
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[3];OWN=HERE.parent.relative_to(ROOT).as_posix();BASE='6a99a7606b9c2d11ac8cd093610653d4cd5d1382';PRE='coordination/engineering/global-physical-comparison-20261006/results/';CINDEX='coordination/engineering/physical-gap-components-1005-20261005-local19/custody-v1/index.json';SOURCE='research/geography/ukraine-original-singleton-source-fit-20261010/vintages/physical-restoration-001/'
sha=lambda b:hashlib.sha256(b).hexdigest()
def git(*a):return subprocess.check_output(['git','-C',str(ROOT),*a])
def main():
 head,vintage,part=sys.argv[1:];start=time.monotonic();name=f'components-{int(part):03}.jsonl.gz'
 if git('rev-parse','HEAD').decode().strip()!=head:raise ValueError('Exact execution HEAD required')
 controls=[OWN+'/tools/restore_physical.py',OWN+'/roster.json',OWN+'/physical-locators.json',OWN+'/tools/runtime-lock.json','scripts/evidence/immutable.py'];pins=[]
 for p in controls:
  b=(ROOT/p).read_bytes()
  if b!=git('show',head+':'+p):raise ValueError('Unfrozen control')
  pins.append({'path':p,'bytes':len(b),'sha256':sha(b),'hash_kind':'file-bytes'})
 ns={'__name__':'grc_immutable','__file__':str(ROOT/'scripts/evidence/immutable.py')};exec(compile(git('show',head+':scripts/evidence/immutable.py'),ns['__file__'],'exec'),ns)
 base=ns['Baseline'](ROOT,head,pins,max_phase_bytes=256*1024**2);canon=ns['canonical_json'];dest=ns['NewVintage'](base,OWN+'/',vintage,[name,'physical-records.json','queried-source-metadata.json','receipt.json'])
 runtime=json.loads(base.pinned_bytes(OWN+'/tools/runtime-lock.json'))
 if pathlib.Path(sys.executable).resolve()!=pathlib.Path(runtime['python_executable']).resolve() or not os.environ.get('PYTHONDONTWRITEBYTECODE') or not os.environ.get('PYTHONPYCACHEPREFIX'):raise ValueError('Wrong runtime or bytecode policy')
 for pin in runtime['files']:
  base.admit('runtime:'+pin['path'],pin['bytes']);b=pathlib.Path(pin['path']).read_bytes()
  if len(b)!=pin['bytes'] or sha(b)!=pin['sha256']:raise ValueError('Runtime drift')
 inputs=[]
 def read(p,pin=None,decode=False):
  line=git('ls-tree','-z',BASE,'--',p).decode().rstrip('\0');fields,path=line.split('\t');mode,kind,oid=fields.split()
  if (mode,kind,path)!=('100644','blob',p):raise ValueError('Nonordinary immutable body')
  base.admit(BASE+':'+p,int(git('cat-file','-s',oid)));b=git('cat-file','blob',oid);d={'commit':BASE,'path':p,'mode':mode,'git_blob_oid':oid,'bytes':len(b),'sha256':sha(b)}
  if pin and (len(b)!=pin['bytes'] or sha(b)!=pin['sha256']):raise ValueError('Whole encoded mismatch')
  if decode:
   base.admit('decoded:'+p,pin['uncompressed_bytes'])
   with gzip.GzipFile(fileobj=io.BytesIO(b)) as f:b=f.read(pin['uncompressed_bytes']+1)
   if len(b)!=pin['uncompressed_bytes'] or sha(b)!=pin['uncompressed_sha256']:raise ValueError('Whole decoded mismatch')
   d.update(uncompressed_bytes=len(b),uncompressed_sha256=sha(b))
  inputs.append(d);return b
 roster=json.loads(base.pinned_bytes(OWN+'/roster.json'));locators=json.loads(base.pinned_bytes(OWN+'/physical-locators.json'));want=[r['component_id'] for r in roster['members'] if locators[r['component_id']]['path']==name]
 if not want:raise ValueError('No requested component in this independent partition')
 report=json.loads(read(PRE+'report.json'));transport=json.loads(read(PRE+'transport-map.json'))
 if report['execution_commit']!=transport['scientific_execution'] or report['component_count']!=95173 or report['source_record_count']!=188612:raise ValueError('Wrong scientific epoch/denominator')
 entry=next(r for r in transport['entries'] if r['delivered']['path']==name)
 if entry['original']!=next(r for r in report['products'] if r['path']==name):raise ValueError('Original report binding changed')
 rows=[json.loads(l) for l in read(PRE+name,entry['delivered'],True).splitlines()];ids=[r['component_id'] for r in rows]
 if ids!=sorted(set(ids)) or not set(want).issubset(ids):raise ValueError('Wrong original partition')
 needed=set(ids);features={};index=json.loads(read(CINDEX));selected={r['candidate_custody']['path'] for r in roster['members'] if r['component_id'] in want};allaliases=sorted([a for a in index['aliases'] if '/components-v3/components-' in a['original']['path']],key=lambda a:a['original']['path']);aliases=[a for a in allaliases if a['payload'] in selected]
 # Neighbor products are admitted only if this full original physical shard crosses a boundary.
 loaded=set();queue=list(aliases)
 while queue and set(features)!=needed:
  a=queue.pop(0)
  if a['payload'] in loaded:continue
  if len(loaded)>=3:raise ValueError('Declared three-product inverse closure exhausted')
  loaded.add(a['payload'])
  product=json.loads(read(a['payload'],a['original'],True))['features'];pids=[f['id'] for f in product]
  if len(pids)!=len(set(pids)):raise ValueError('Duplicate original candidate')
  for f in product:
   if f['id'] in needed:
    if f['id'] in features:raise ValueError('Duplicate inverse candidate')
    features[f['id']]=f
  missing=needed-set(features)
  ai=allaliases.index(a)
  if missing and min(missing)<min(pids) and ai>0:queue.append(allaliases[ai-1])
  if missing and max(missing)>max(pids) and ai+1<len(allaliases):queue.append(allaliases[ai+1])
 if set(features)!=needed:raise ValueError('Incomplete full inverse candidate closure')
 for r in rows:
  if r.pop('complete_current_record_metadata_alias')!='v1':raise ValueError('Unknown alias')
  f=features[r['component_id']];r.update(original_context=f['properties'],candidate_feature_sha256=sha(canon(f)),candidate_geometry_sha256=sha(canon(f['geometry'])))
 raw=b''.join(canon(r) for r in rows);expected=entry['original'];base.admit('original-decoded:'+name,len(raw))
 if len(raw)!=expected['uncompressed_bytes'] or sha(raw)!=expected['uncompressed_sha256']:raise ValueError('Original whole inverse mismatch')
 encoded=ns['deterministic_gzip'](raw)
 if len(encoded)!=expected['bytes'] or sha(encoded)!=expected['sha256']:raise ValueError('Original encoded inverse mismatch')
 selected=[next(r for r in rows if r['component_id']==cid) for cid in want];del rows,raw,features
 sp=next(p for p in report['products'] if p['path']=='sources-000.jsonl.gz');sr=read(SOURCE+'sources-000.jsonl.gz',sp,True);sources=[json.loads(l) for l in sr.splitlines()];byid={s['id']:s for s in sources}
 if len(byid)!=len(sources):raise ValueError('Duplicate original source identity')
 old=json.loads(read(SOURCE+'receipt.json'));oldentry=next(r for r in old['restorations'] if r['path']=='sources-000.jsonl.gz')
 if oldentry['rows']!=len(sources) or oldentry['whole_original_sha256']!=sp['sha256'] or oldentry['decoded_sha256']!=sp['uncompressed_sha256']:raise ValueError('Source whole-product restoration differs')
 queried=[]
 for r in selected:
  qs=r['query_relations']
  if not qs or len({q['source_id'] for q in qs})!=len(qs):raise ValueError('Missing or duplicate full query')
  ms=[]
  for q in qs:
   s=byid[q['source_id']]
   if (s['record_sha256'],s['decoded_pointset_binary64_sha256'],s['level'])!=(q['source_record_sha256'],q['source_pointset_sha256'],q['source_level']):raise ValueError('Original native/query mismatch')
   ms.append(s)
  queried.append({'component_id':r['component_id'],'sources':ms})
 receipt={'baseline':BASE,'execution_commit':head,'component_ids':want,'original_product':expected,'restored_complete_rows':len(ids),'source_metadata_product':sp,'reused_source_receipt':oldentry,'source_inputs':inputs,'logical_consumed_input_bytes':sum(base.consumed.values()),'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'elapsed_seconds':time.monotonic()-start,'python_version':sys.version,'runtime_inventory_sha256':sha(base.pinned_bytes(OWN+'/tools/runtime-lock.json')),'limits':['Exact original whole-product custody inverse only; no new GIS or source approval.','Existing GSHHG source authority and observation-date limits remain unchanged.']}
 if receipt['peak_rss_bytes']>512*1024**2:raise ValueError('RSS reservation exceeded')
 dest.publish_bytes({name:encoded,'physical-records.json':canon(selected),'queried-source-metadata.json':canon(queried),'receipt.json':canon(receipt)})
 print(json.dumps({'part':part,'components':len(want),'logical_bytes':receipt['logical_consumed_input_bytes'],'peak_rss_bytes':receipt['peak_rss_bytes']}))
if __name__=='__main__':main()
