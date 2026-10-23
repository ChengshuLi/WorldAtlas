"""Bind the USA source/native handoff's actual immutable inputs and numerical claims.
Run from author scratch after genuine authority and final accounting exist.
"""
import pathlib,json,gzip,hashlib,subprocess,re,posixpath
D=pathlib.Path(__file__).resolve().parent;W=pathlib.Path((D/'workspace.txt').read_text().strip());P='coordination/engineering/usa-repair-delivery-20261017';O=W/P;H='d4968ddc37aa3aa6105e9610c9e6fadbb368ba14'
sha=lambda b:hashlib.sha256(b).hexdigest()
def git(*args):return subprocess.check_output(['git','-c','protocol.allow=never','-C',str(W),*args])
def raw(p,c=H):return git('show',c+':'+p)
def candidate(p):return(W/p).read_bytes()if(W/p).is_file()else raw(p,'HEAD')
def data(p):return json.loads(candidate(P+'/'+p))
def desc(p,c=None):
 b=raw(p,c)if c else candidate(p);r={'path':p,'bytes':len(b),'sha256':sha(b),'hash_kind':'file-bytes'}
 if c:r['commit']=c
 if p.endswith('.gz'):d=gzip.decompress(b);r.update(uncompressed_bytes=len(d),uncompressed_sha256=sha(d))
 return r
files={};aliases=[]
def baseline(p,c=H,expected=None):
 if p.startswith(P+'/'):return
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
# The independent all-family predicate claim requires every complete original,
# including zero-contact families and originals without selected owners.
for r in cat['products']:
 for p in r['parts']:baseline(p['path'])
sources=[]
for r in cat['products']:
 if r['key']not in['gb:USA:ADM2','gb:CAN:ADM1','gb:CAN:ADM2','gb:MEX:ADM1']:continue
 sources.append({'id':r['key'],'url':r['recorded_consumed_url'],'role':'Complete retained original product; USA ADM2 is source-relative positive county-equivalent coverage and complete domestic competition; other families are complete conservative foreign negatives, including ownerless features.','vintage':str(r['source_represented_year_claim']),'retrieved_at':'2026-10-17T03:50:00Z','retrieval_note':'Authenticated retained immutable bytes; no new source download.','license':{'status':'redistributable','terms':r['recorded_license']if isinstance(r['recorded_license'],str)else json.dumps(r['recorded_license'])},'retention':'restoration-only','verification':'verified','restoration':'Restore all parts from the baseline catalogue in ordinal order, verify encoded/decoded pins and complete original hash/count. Every part is bound in baseline.files.','original_parts':[baseline(p['path'])for p in r['parts']],'original_bytes':r['original_bytes'],'original_sha256':r['original_sha256'],'limit':'Retained consumed product, represented-year and license metadata only; no current legal boundary approval. USA source is the original simplified product. Census and geoBoundaries attribution and unresolved project derivative-language applicability remain distinct.','temporal_status':'reference'})
sources.extend([
 {'id':'complete-retained-original-corpus','url':'https://github.com/ChengshuLi/WorldAtlas/blob/'+H+'/'+catp,'role':'All368 complete retained products and73567 features independently screened against the whole original USA key set; every exact source family is preserved, including zero-contact and ownerless originals.','vintage':'Retained mixed reference years in each original catalogue record','retrieved_at':'2026-10-17T03:51:00Z','license':{'status':'unknown','terms':'Per-product original licenses remain in the complete catalogue and metadata; no blanket all-corpus license is asserted.'},'retention':'restoration-only','verification':'verified','restoration':'Restore every catalogue product part from its baseline descriptor. Retain original complete product hashes and per-file license terms.','limit':'Complete original-corpus absence is source-relative native-centre evidence, not global contemporary sovereignty or physical clearance.','temporal_status':'reference'},
 {'id':'gshhg-original-physical','url':'https://github.com/ChengshuLi/WorldAtlas/blob/'+H+'/coordination/engineering/gshhg-native-member-custody-20261007/results/member-index.json','role':'Whole original GSHHG source body, complete metadata, hierarchy and whole-target support with all issues.','vintage':'Retained source-relative physical reference with heterogeneous observation dates','retrieved_at':'2026-10-17T03:54:00Z','license':{'status':'redistributable','terms':'Retained GSHHG LGPL3-or-later original custody and notices.'},'retention':'restoration-only','verification':'verified','restoration':'Use every exact input locator in config/physical-001.json; baseline.files binds their complete bodies. Do not omit unmeasured invalid-source2380 or other issues.','limit':'Source2380 has no measured valid relation for two whole targets; all604 affected owner keys remain conservatively held. Whole physical evidence is not current physical truth or ownership approval.','temporal_status':'reference'},
 {'id':'independent-USA-source-review','url':'https://github.com/ChengshuLi/WorldAtlas/issues/2358','role':'Independent complete source scope, exact original keys, actual aggregate intent, ownerless foreign negative scope and later-resolution review.','vintage':'Exact author baseline '+H,'retrieved_at':'2026-10-17T03:56:00Z','license':{'status':'redistributable','terms':'WorldAtlas task evidence with all underlying source notices retained.'},'retention':'restoration-only','verification':'verified','restoration':'Restore independent-source-review/REVIEW.md and the full artifact-inventory.json roster from this candidate. Original review probes keep their documented local layouts.','limit':'This source review is complete within its scope but predates final native authority; final exact-head source/native review remains required.','temporal_status':'reference'}])
# Preserve ancestor aliases rather than silently changing actual execution locators.
aliasbody={'kind':'identical-original-execution-input-ancestor-custody','aliases':aliases,'limit':'Original execution pins remain literal in all receipts. Manifest custody uses identical complete bytes at an ancestor when an original execution commit was not an ancestor.'}
(O/'source-review/execution-input-ancestor-custody.json').write_text(json.dumps(aliasbody,indent=2)+'\n')
(O/'source-review/native-executed-method-closure.json').write_text(json.dumps({'baseline':H,'entrypoint':'scripts/prepare-delivery-handoff.mjs','static_and_literal_dynamic_import_paths':sorted(closure),'physical_helper':'scripts/qualify-source-cohort.py','limits':['A static/literal module closure documents method custody; it is not a hermetic OS or native-library dependency closure. Actual runtime inventories and measured execution observations remain separately retained.']},indent=2)+'\n')
paths.update(str(f.relative_to(W))for f in O.rglob('*')if f.is_file());outputs=[desc(p)for p in sorted(paths)if not p.endswith('/evidence-quality.json')and not p.endswith('.md')]
metrics=[];bindings=[]
rows=[('original-cells','final-handoff-001/complete-native-authority-accounting.json','original_cells','native cells'),('original-intervals','final-handoff-001/complete-native-authority-accounting.json','original_intervals','intervals'),('original-subjects','final-handoff-001/complete-native-authority-accounting.json','original_subjects','subjects'),('qualified-cells','final-handoff-001/complete-native-authority-accounting.json','qualified_cells','native cells'),('qualified-components','final-handoff-001/complete-native-authority-accounting.json','qualified_components','components'),('held-cells','final-handoff-001/complete-native-authority-accounting.json','held_cells','native cells'),('source-holds','final-handoff-001/complete-native-authority-accounting.json','source_hold_cells','native cells'),('physical-admission-holds','final-handoff-001/complete-native-authority-accounting.json','physical_admission_hold_cells','native cells'),('hold-intersection','final-handoff-001/complete-native-authority-accounting.json','hold_intersection_cells','native cells'),('qualified-land','final-handoff-001/complete-native-authority-accounting.json','qualified_physical_classes/land','native cells'),('qualified-water','final-handoff-001/complete-native-authority-accounting.json','qualified_physical_classes/inland-water','native cells'),('held-land','final-handoff-001/complete-native-authority-accounting.json','held_physical_classes/land','native cells'),('held-water','final-handoff-001/complete-native-authority-accounting.json','held_physical_classes/inland-water','native cells'),('retained-original-negative-instances','final-handoff-001/complete-native-authority-accounting.json','original_negative_instances_preserved','whole original exclusion instances'),('qualified-negative-instances','final-handoff-001/complete-native-authority-accounting.json','qualified_positive_negative_instances','whole original exclusion instances'),('complete-negative-features','final-handoff-001/complete-native-authority-accounting.json','complete_negative_source_features','features'),('whole-physical-members','final-handoff-001/complete-native-authority-accounting.json','full_physical_members','members'),('physical-issues','final-handoff-001/complete-native-authority-accounting.json','physical_issues','issues'),('physical-members-with-issues','final-handoff-001/complete-native-authority-accounting.json','physical_members_with_issues','members'),('complete-primary-source-features','final-handoff-001/complete-native-authority-accounting.json','full_primary_source_features','features'),('qualified-source-members','final-handoff-001/complete-native-authority-accounting.json','qualified_source_members','members'),('wholly-held-owners','final-handoff-001/complete-native-authority-accounting.json','whole_held_owners','owners'),('initial-accepted-overlap','original-scope/scope-screen.json','accepted_overlap_cells','native cells'),('native-requested-cells','native-diagnostic-002/native-diagnostic.json','requested_cells','native cells'),('native-held-foreign-cells','native-diagnostic-002/native-diagnostic.json','held_cells','native cells'),('original-source-families','independent-source-review/complete-source-scope-screen.json','all_source_families','families'),('original-source-features','independent-source-review/complete-source-scope-screen.json','all_original_features','features')]
for ident,p,pointer,unit in rows:
 f=P+'/'+p;v=json.loads(candidate(f))
 for key in pointer.split('/'):v=v[key]
 assert isinstance(v,(int,float));metrics.append({'id':ident,'value':v,'unit':unit,'vintage':'baseline','evaluation_commit':H,'input_file':{'path':f,'commit':'candidate'},'input_sha256':sha(candidate(f))});bindings.append({'metric_id':ident,'path':f,'json_pointer':'/'+pointer})
subjects=data('final-handoff-001/complete-native-authority-accounting.json')['subject_ids'];assert len(subjects)==351
pinpaths={'original_source_catalogue':catp,'selected_baseline':'data/ownership-selection.json'}
x={'version':1,'issue':2358,'lane':'engineering','worker_id':'01a14784-198b-734e-b6ce-4c7c5e3ad008','subject_ids':subjects,'subject_ids_sha256':sha(json.dumps(subjects,separators=(',',':')).encode()),'baseline':{'version':2,'commit':H,'files':list(files.values()),'pins':{k:baseline(p)['sha256']for k,p in pinpaths.items()},'pin_files':{k:{'path':p,'commit':H}for k,p in pinpaths.items()}},'sources':sources,'outputs':outputs,'methods':[{'id':'complete-USA-original-native-restoration','kind':'geography','description':'Authenticate complete originals, preserve all original intervals/owners, verify actual five-county aggregate intent and identity/source-history holds, retain all whole foreign originals and complete source-relative physical issues, then qualify only exact native-supported original keys through the unchanged stock constructor.','software':'Executed custom method files are bound as candidate outputs. Baseline code includes the whole static/literal stock entrypoint closure, original Python physical helper and comparison code. Actual pinned Python/Shapely/NumPy/GEOS runtime inventories and measurements are retained.','units':'native grid cells, intervals, whole original geometry and file bytes','axis_order':'longitude-latitude','crs':'EPSG:4326 and unchanged262166 binary64 native latitude table','area_method':'No area-based repair credit; whole-source exact-native polygon predicates.','distance_method':'No nearest-owner/distance assignment; inherited Fairfax heuristic is explicitly held.'}],'metrics':metrics,'metric_bindings':bindings,'summaries':[],'conclusions':[{'status':'supported','source_ids':['gb:USA:ADM2','gb:CAN:ADM1','gb:CAN:ADM2','gb:MEX:ADM1','gshhg-original-physical','independent-USA-source-review'],'text':'All107131 original cells /46575 intervals /351 subjects are reconciled. Genuine stock source/native authority qualifies105927 cells;1204 exact source/physical holds remain. This is not an accepted selected-output count.'},{'status':'unresolved','source_ids':['complete-retained-original-corpus','gshhg-original-physical','independent-USA-source-review'],'text':'USA31 source history, Fairfax identity, foreign contacts, conservative unmeasured-source physical holds and broader original boundary/reproduction obligations remain. Final exact-head review and actual selected-owner-zero/conservation/emitted-consumer acceptance are pending.'}],'stages':{'research':'partial','implementation':'proposed','geographic_approval':'unapproved'},'commands':['env -u NODE_OPTIONS -u NODE_PATH node scripts/prepare-delivery-handoff.mjs physical '+P+'/config/physical-001.json FRESH_OUTPUT','env -u NODE_OPTIONS -u NODE_PATH node scripts/prepare-delivery-handoff.mjs native-diagnostic '+P+'/config/native-diagnostic-002.json FRESH_OUTPUT','env -u NODE_OPTIONS -u NODE_PATH node scripts/prepare-delivery-handoff.mjs native-authority '+P+'/config/native-authority-001.json FRESH_OUTPUT'],'limits':data('final-handoff-001/complete-native-authority-accounting.json')['limits']}
(O/'evidence-quality.json').write_text(json.dumps(x,separators=(',',':'),ensure_ascii=False)+'\n');print(json.dumps({'baseline_files':len(files),'baseline_encoded_bytes':sum(f['bytes']for f in files.values()),'outputs':len(outputs),'output_bytes':sum(f['bytes']for f in outputs),'subjects':len(subjects),'metrics':len(metrics)}))
