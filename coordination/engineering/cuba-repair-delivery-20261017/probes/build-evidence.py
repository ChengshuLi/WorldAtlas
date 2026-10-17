"""Bind immutable Cuba scientific inputs, actual method bodies and exact claims.
Usage: python build-evidence.py REPO
Whole input bodies are read from Git; no source archive is copied to the worktree.
"""
import pathlib,json,gzip,hashlib,subprocess,re,posixpath,sys,os
assert len(sys.argv)==2
W=pathlib.Path(sys.argv[1]).absolute();P='coordination/engineering/cuba-repair-delivery-20261017';O=W/P;H='3b3e9e675cfb37999d5665438f9fbf25bbd4238b'
sha=lambda b:hashlib.sha256(b).hexdigest()
def git(*args):return subprocess.check_output(['git','-c','protocol.allow=never','-C',str(W),*args],env={**os.environ,'GIT_NO_LAZY_FETCH':'1','GIT_NO_REPLACE_OBJECTS':'1','GIT_TERMINAL_PROMPT':'0'})
def raw(p,c=H):return git('show',c+':'+p)
assert raw(P+'/probes/build-evidence.py','HEAD')==pathlib.Path(__file__).read_bytes()
def candidate(p):return(W/p).read_bytes()if(W/p).is_file()else raw(p,'HEAD')
def data(p):return json.loads(candidate(P+'/'+p))
def desc(p,c=None):
 b=raw(p,c)if c else candidate(p);r={'path':p,'bytes':len(b),'sha256':sha(b),'hash_kind':'file-bytes'}
 if c:r['commit']=c
 if p.endswith('.gz'):d=gzip.decompress(b);r.update(uncompressed_bytes=len(d),uncompressed_sha256=sha(d))
 return r
files={};aliases=[]
def baseline(p,c=H,expected=None):
 if p.startswith(P+'/') and not p.startswith(P+'/probes/'):return
 assert not p.startswith('/')and '..'not in p.split('/')
 key=c,p
 if key in files:return files[key]
 r=desc(p,c)
 if expected:
  assert r['bytes']==expected['bytes']and r['sha256']==expected['sha256'],(p,'changed retained pin')
 if c!=H and subprocess.run(['git','-C',str(W),'merge-base','--is-ancestor',c,'HEAD'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode:
  replacement=desc(p,H);alias_commit=H
  if {k:v for k,v in r.items()if k!='commit'}!={k:v for k,v in replacement.items()if k!='commit'}:
   candidates=git('log','--format=%H',H,'--',p).decode().splitlines();replacement=None
   for ancestor in candidates:
    probe=desc(p,ancestor)
    if {k:v for k,v in r.items()if k!='commit'}=={k:v for k,v in probe.items()if k!='commit'}:replacement=probe;alias_commit=ancestor;break
   assert replacement is not None,('No identical complete ancestor custody',p,c)
  aliases.append({'original_execution_pin':r,'current_ancestor_custody':replacement});r=replacement;c=alias_commit
 key=c,p
 if key in files:assert files[key]==r
 else:files[key]=r
 return r

def collect(obj):
 if isinstance(obj,list):
  for v in obj:collect(v)
 elif isinstance(obj,dict):
  if all(k in obj for k in ['path','commit','bytes','sha256'])and isinstance(obj['path'],str)and not obj['path'].startswith('/')and re.fullmatch('[a-f0-9]{40}',str(obj['commit'])):baseline(obj['path'],obj['commit'],obj)
  for v in obj.values():collect(v)
paths=set(git('ls-tree','-r','--name-only','HEAD','--',P+'/').decode().splitlines());paths.update(str(f.relative_to(W))for f in O.rglob('*')if f.is_file())
for p in sorted(paths):
 if p.endswith('.json')and not p.endswith('/evidence-quality.json'):collect(json.loads(candidate(p)))
for p in ['data/ownership-selection.json','.github/package-inputs.json','data/world-index.json','data/semantic-report.json','data/administrative-sources.json','scripts/semantic-locations.py','scripts/consolidate-fragments.py','scripts/administrative.py','scripts/qualify-source-cohort.py']:baseline(p)
# Complete executed JS static/dynamic literal import closure; Python physical helper
# and original comparison method are separately bound above and in physical config.
closure=set()
def imports(p):
 if p in closure:return
 closure.add(p);b=raw(p);baseline(p)
 for rel in re.findall(r'(?:from\s+|import\(\s*)[\'\"](\.[^\'\"]+)[\'\"]',b.decode()):
  name=posixpath.normpath(posixpath.join(posixpath.dirname(p),rel))
  if name.endswith(('.mjs','.js','.cjs')):imports(name)
imports('scripts/prepare-delivery-handoff.mjs')
catp='coordination/engineering/original-geography-source-corpus-20261006/catalogue.json';cat=json.loads(raw(catp));baseline(catp)
# Bind the complete original corpus underlying the original global census.
# Complete foreign whole-bounds applicability is separately retained with all raw exceptions.
for r in cat['products']:
 for p in r['parts']:baseline(p['path'])
sources=[]
for family in ['gb:CUB:ADM2','gb:CUB:ADM1']:
 r=next(row for row in cat['products']if row['key']==family)
 sources.append({'id':family,'url':r['recorded_consumed_url'],'role':'Complete consumed original simplified municipality positive source and all domestic competitors.'if family.endswith('ADM2')else'Complete original provincial context; not a clipping mask or automatic hold predicate.','vintage':str(r['source_represented_year_claim']),'retrieved_at':'2026-10-17T05:30:00Z','retrieval_note':'Authenticated retained immutable bytes; no fresh upstream download and no claim of original retrieval date.','license':{'status':'redistributable','terms':r['recorded_license']if isinstance(r['recorded_license'],str)else json.dumps(r['recorded_license'])},'retention':'restoration-only','verification':'verified','restoration':'Restore every complete catalogue part in ordinal order and authenticate encoded, decoded and complete raw lengths/hashes, full feature roster and original metadata.','original_parts':[baseline(part['path'])for part in r['parts']],'original_bytes':r['original_bytes'],'original_sha256':r['original_sha256'],'limit':'ODbL 1.0 and represented 2017 are recorded source metadata. Distinct unsimplified upstream bodies are not substituted. This is not current territorial, historical or legal approval.','temporal_status':'reference'})
sources.extend([
 {'id':'complete-original-foreign-corpus','url':'https://github.com/ChengshuLi/WorldAtlas/blob/'+H+'/'+catp,'role':'Complete 368-family original corpus, including 366 foreign families and all 73,383 foreign originals without selected-owner filtering. Actual fresh whole-part bounds screen retains 73,380 disjoint raw originals and three periodic-coordinate failures.','vintage':'Mixed retained original reference vintages','retrieved_at':'2026-10-17T05:30:00Z','license':{'status':'unknown','terms':'Product-specific complete metadata is retained; no blanket all-corpus license is asserted.'},'retention':'restoration-only','verification':'verified','restoration':'Every complete catalogue payload is bound in baseline.files. Restore ordinal raw bodies and compare the exact per-family original hashes/counts and screening traces.','limit':'No global current-sovereignty or missing-source clearance. The three raw failures remain visible and require their separately bound retained periodic interpretation.','temporal_status':'reference'},
 {'id':'retained-Fiji-periodic-frame','url':'https://github.com/ChengshuLi/WorldAtlas/blob/b3914bbdd2b6fdcb5e4ae7c860494425fa2c27ea/coordination/engineering/global-current-cell-work-queue-20261014/normalized-source-seams.json','role':'Exact three original Fiji periodic-coordinate cases are reconciled through previously retained complete originals, canonical frame interpretation and independent complete-native-span equality.','vintage':'Original immutable queue and its independently retained complete-native comparison','retrieved_at':'2026-10-17T05:30:00Z','license':{'status':'redistributable','terms':'WorldAtlas original-source reconciliation evidence; underlying source metadata and notices remain retained in complete products.'},'retention':'restoration-only','verification':'verified','restoration':'Use the exact input descriptors in source-review/periodic-negatives-001. Full original geometry equality, canonical whole bounds and original full-native row extents are all retained.','limit':'No new normalization, repair, clipping or raster science. The original raw-coordinate rejection is preserved. This is solely a negative-applicability interpretation, not territorial approval.','temporal_status':'reference'},
 {'id':'gshhg-original-physical','url':'https://github.com/ChengshuLi/WorldAtlas/blob/'+H+'/coordination/engineering/gshhg-native-member-custody-20261007/results/member-index.json','role':'Whole original GSHHG source and metadata, unchanged stock producer/runtime custody, and genuine complete support for all 87 members.','vintage':'Retained heterogeneous physical reference dates','retrieved_at':'2026-10-17T05:35:00Z','license':{'status':'redistributable','terms':'Retained original GSHHG LGPL 3-or-later custody and notices.'},'retention':'restoration-only','verification':'verified','restoration':'Use every exact config/physical-001.json input and runtime pin. Whole output, 28 geometric issues and actual execution receipt remain under physical-001.','limit':'Physical support is source-relative, not present physical truth or ownership approval. All 28 issues across 17 members remain.','temporal_status':'reference'}])
(O/'source-review/execution-input-ancestor-custody.json').write_text(json.dumps({'kind':'identical-original-execution-input-ancestor-custody','aliases':aliases,'limit':'Original actual execution locators remain unchanged in receipts. Any alternate manifest custody names byte-identical complete ancestor bodies.'},indent=2)+'\n')
(O/'source-review/native-executed-method-closure.json').write_text(json.dumps({'baseline':H,'entrypoint':'scripts/prepare-delivery-handoff.mjs','static_and_literal_dynamic_import_paths':sorted(closure),'physical_helper':'scripts/qualify-source-cohort.py','limits':['Static/literal project module closure, not a hermetic OS/native-library closure. Exact runtime pins and measured actual execution remain separately retained.']},indent=2)+'\n')
paths.update(str(f.relative_to(W))for f in O.rglob('*')if f.is_file())
outputs=[desc(p)for p in sorted(paths)if not p.endswith('/evidence-quality.json')and not p.endswith('.md')]
account='final-handoff-001/complete-native-authority-accounting.json'
rows=[('original-cells',account,'original_cells','native cells'),('original-intervals',account,'original_intervals','intervals'),('original-subjects',account,'original_subjects','subjects'),('qualified-cells',account,'qualified_cells','native cells'),('qualified-components',account,'qualified_components','components'),('held-cells',account,'held_cells','native cells'),('qualified-land',account,'qualified_physical_classes/land','native cells'),('qualified-water',account,'qualified_physical_classes/inland-water','native cells'),('held-land',account,'held_physical_classes/land','native cells'),('held-water',account,'held_physical_classes/inland-water','native cells'),('whole-physical-members',account,'full_physical_members','members'),('physical-issues',account,'physical_issues','issues'),('physical-members-with-issues',account,'physical_members_with_issues','members'),('complete-primary-features',account,'whole_primary_source_features','features'),('complete-context-features',account,'whole_context_source_features','features'),('qualified-source-members',account,'qualified_source_members','members'),('complete-foreign-families',account,'complete_foreign_families','families'),('complete-foreign-features',account,'complete_foreign_features','features'),('foreign-raw-disjoint-features',account,'foreign_raw_bounds_disjoint_features','features'),('foreign-periodic-disjoint-features',account,'foreign_retained_periodic_disjoint_features','features'),('unresolved-foreign-bounds',account,'unresolved_foreign_bound_features','features'),('foreign-negative-operands',account,'foreign_negative_instances','operands'),('initial-accepted-overlap','original-scope/scope-screen.json','accepted_overlap_cells','native cells'),('native-requested-cells','native-diagnostic-001/native-diagnostic.json','requested_cells','native cells'),('native-held-cells','native-diagnostic-001/native-diagnostic.json','held_cells','native cells'),('publication-controls','controls-001/publication-controls.json','passed','actual negative cases')]
metrics=[];bindings=[]
for ident,p,pointer,unit in rows:
 f=P+'/'+p;v=json.loads(candidate(f))
 for key in pointer.split('/'):v=v[key]
 assert isinstance(v,(int,float))and not isinstance(v,bool)
 metrics.append({'id':ident,'value':v,'unit':unit,'vintage':'baseline','evaluation_commit':H,'input_file':{'path':f,'commit':'candidate'},'input_sha256':sha(candidate(f))});bindings.append({'metric_id':ident,'path':f,'json_pointer':'/'+pointer})
subjects=data(account)['subject_ids'];assert len(subjects)==87
pinpaths={'original_source_catalogue':catp,'selected_baseline':'data/ownership-selection.json'}
x={'version':1,'issue':2384,'lane':'engineering','worker_id':'01a14784-198b-734e-b6ce-4c7c5e3ad008','subject_ids':subjects,'subject_ids_sha256':sha(json.dumps(subjects,separators=(',',':')).encode()),'baseline':{'version':2,'commit':H,'files':list(files.values()),'pins':{k:baseline(p)['sha256']for k,p in pinpaths.items()},'pin_files':{k:{'path':p,'commit':H}for k,p in pinpaths.items()}},'sources':sources,'outputs':outputs,'methods':[{'id':'complete-Cuba-original-native-restoration','kind':'geography','description':'Authenticate the complete frozen direct municipality originals and every original repair key; screen all whole foreign originals with documented retained periodic cases; retain all whole physical support and issues; qualify the complete unchanged request through genuine stock source/native construction and exact key reconciliation.','software':'Executed custom methods are retained as candidate outputs and exact ancestor method pins. Complete stock static/literal project closure, Python physical helper, Python/Shapely/NumPy/GEOS runtime custody and actual receipts are bound. The preliminary screen-original.py is a retained historical probe whose relative paths describe its original scratch layout; portable production methods take explicit repo/commit/output arguments.','units':'native cells, original intervals, whole geometry, file bytes','axis_order':'longitude-latitude','crs':'CRS84/EPSG:4326 and unchanged 262166-row native binary64 latitude table','area_method':'No area-based repair credit. Actual stock exact-rational native-centre predicates.','distance_method':'No nearest-owner assignment or inferred parent clipping.'}],'metrics':metrics,'metric_bindings':bindings,'summaries':[],'conclusions':[{'status':'supported','source_ids':['gb:CUB:ADM2','complete-original-foreign-corpus','retained-Fiji-periodic-frame','gshhg-original-physical'],'text':'All 26,459 original land cells, 8,489 intervals and 87 subjects exactly equal genuine stock native support and authority; zero native holds. This is a source-relative authority handoff, with no selected acceptance credit.'},{'status':'unresolved','source_ids':['gb:CUB:ADM2','gb:CUB:ADM1','complete-original-foreign-corpus','gshhg-original-physical'],'text':'Current source-vintage, territorial/Guantanamo, historical and regional obligations remain. Independent final source/native review and actual selected-owner-zero, conservation and emitted-consumer acceptance are still required.'}],'stages':{'research':'partial','implementation':'proposed','geographic_approval':'unapproved'},'commands':['env -u NODE_OPTIONS -u NODE_PATH node scripts/prepare-delivery-handoff.mjs physical '+P+'/config/physical-001.json FRESH_OUTPUT','env -u NODE_OPTIONS -u NODE_PATH node scripts/prepare-delivery-handoff.mjs native-diagnostic '+P+'/config/native-diagnostic-001.json FRESH_OUTPUT','env -u NODE_OPTIONS -u NODE_PATH node scripts/prepare-delivery-handoff.mjs native-authority '+P+'/config/native-authority-001.json FRESH_OUTPUT'],'limits':data(account)['limits']}
(O/'evidence-quality.json').write_text(json.dumps(x,separators=(',',':'),ensure_ascii=False)+'\n')
print(json.dumps({'baseline_files':len(files),'baseline_encoded_bytes':sum(f['bytes']for f in files.values()),'outputs':len(outputs),'output_bytes':sum(f['bytes']for f in outputs),'subjects':len(subjects),'metrics':len(metrics)}))
