"""Preserve actual source construction, open semantic decisions and original physical licence notices.
Usage: python preserve-interpretation.py READ_ONLY_REPO FRESH_OUTPUT
"""
import collections,gzip,hashlib,io,json,os,pathlib,resource,subprocess,sys,time
W,O=map(lambda v:pathlib.Path(v).absolute(),sys.argv[1:]);H='d4968ddc37aa3aa6105e9610c9e6fadbb368ba14';S='e4e80e383fa72ede778056c48c6c1eeb381c2944';P='coordination/engineering/philippines-native-repair-20261017/'
assert O.parent.is_dir() and not O.exists() and all(not p.is_symlink() for p in (O,*O.parents))
pins={};total=0;MAX=64*1024*1024;PHASE=256*1024*1024;started=time.monotonic();sha=lambda b:hashlib.sha256(b).hexdigest();env={**os.environ,'GIT_NO_LAZY_FETCH':'1','GIT_NO_REPLACE_OBJECTS':'1'}
def read(path,commit=H,expected=None):
 global total
 assert time.monotonic()-started<180 and path and not path.startswith('/') and all(x not in ['', '.', '..'] for x in path.split('/'))
 cmd=['git','-c','protocol.allow=never','-C',str(W)];meta,name=subprocess.check_output(cmd+['ls-tree','-z',commit,'--',path],env=env).rstrip(b'\0').split(b'\t');mode,kind,oid=meta.decode().split();assert mode=='100644' and kind=='blob' and name.decode()==path
 size=int(subprocess.check_output(cmd+['cat-file','-s',oid],env=env));assert 0<size<=MAX
 b=subprocess.check_output(cmd+['cat-file','blob',oid],env=env);assert len(b)==size and hashlib.sha1(b'blob '+str(size).encode()+b'\0'+b).hexdigest()==oid
 pin={'path':path,'commit':commit,'mode':mode,'git_blob_oid':oid,'bytes':size,'sha256':sha(b)}
 if expected:assert size==expected['bytes'] and sha(b)==expected['sha256']
 if path.endswith('.gz'):
  with gzip.GzipFile(fileobj=io.BytesIO(b)) as f:d=f.read(MAX+1)
  assert len(d)<=MAX;pin.update(decoded_bytes=len(d),decoded_sha256=sha(d));b=d
  if expected:assert len(b)==expected['decoded_bytes'] and sha(b)==expected['decoded_sha256']
 if (commit,path) not in pins:total+=size+pin.get('decoded_bytes',0)
 assert total<=PHASE;pins[(commit,path)]=pin;return b
js=lambda p,h=H:json.loads(read(p,h))

a=js(P+'source-stage/source-scope-assessment.json',S);targets={r['id']:r for r in a['target_checks'] if len(r['source_atoms'])>1};semantic=js('data/semantic-report.json');follow=js('data/geographic-semantic-followup/asia.json.gz');decisions=js('data/geographic-decisions/asia.json');hierarchy=js('data/hierarchy.json');metadata=js('data/administrative-sources.json');code=read('scripts/semantic-locations.py').decode()
assert 'union_all([geoms[i] for i in indices])' in code and 'if ratio>=.5 or parent_match:' in code and "'coverage_error_degrees2':0" in code
aggregates=[]
for ident,t in targets.items():
 change=next(c for c in semantic['changes'] if c['id']==ident);audit=next(c for c in semantic['city_membership_audit'] if 'atlas:city:'+c['source']==ident);f=next(r for r in follow['locations'] if r['id']==ident);atoms=set(t['source_atoms']);assert atoms==set(change['replaces'])=={r['id'] for r in audit['members']}==set(f['source_atoms']) and len(atoms)==len(audit['members'])
 targetdecision=[r for r in decisions['location_review'] if ident in r['ids']]
 aggregates.append({'id':ident,'name':t['name'],'candidate_cells':t['candidate_cells'],'complete_source_atoms':t['source_atoms'],'original_semantic_change':change,'recorded_membership_audit':audit,'current_semantic_followup':f,'current_location_decision':targetdecision,'counts':{'members':len(atoms),'named_parent_match':sum(r['named_parent_match'] for r in audit['members']),'overlap_at_least_half':sum(r['overlap']>=.5 for r in audit['members']),'parent_only_below_half':sum(r['named_parent_match'] and r['overlap']<.5 for r in audit['members']),'zero_recorded_overlap':sum(r['overlap']==0 for r in audit['members'])}})
selected={}
for p in ['data/geography/part-28.json']:
 for f in js(p)['features']:
  if f['id'] in targets:selected[f['id']]=f
assert set(selected)==set(targets)
parentids={f['properties']['parent_id'] for f in selected.values()}
physical_notices=[]
for p in ['research/geography/usa31-gap-family-source-fitness-20261007/sources/GSHHG-LICENSE.TXT','research/geography/usa31-gap-family-source-fitness-20261007/sources/GSHHG-README.TXT','coordination/engineering/global-physical-sources-20261006/COPYING.LESSERv3']:
 b=read(p)
 if p.endswith('LICENSE.TXT'):assert b'version 3 or later' in b
 if p.endswith('README.TXT'):assert b'v3 or any earlier version' in b
 physical_notices.append({'path':p,'sha256':sha(b),'bytes':len(b)})
result={'version':1,'aggregates':aggregates,'aggregate_source_members':sum(len(r['complete_source_atoms']) for r in aggregates),'aggregate_original_cells':sum(r['candidate_cells'] for r in aggregates),'constructor':{'path':'scripts/semantic-locations.py','whole_prepared_member_union':True,'reference_city_is_matching_candidate_only':True,'selection':'At least half candidate overlap or normalized named-parent match, within buffered spatial query; retain dominant reference-owner group; union whole pre-adaptation member geometries.','coverage_error_field':'coverage_error_degrees2 is written as constant zero; it is not a measured original-source-versus-current-target equality proof.'},'complete_current_parent_records':a['parent_records'],'current_aggregate_parent_diagnostics':[r for r in decisions['source_parent_diagnostics']['province_rows'] if r['province_id'] in parentids],'recorded_product_metadata':{k:v for k,v in metadata.items() if k.startswith('gb:PHL:')},'physical_licence_notices':physical_notices,'physical_licence_status':'Retained LICENSE.TXT says LGPL version 3 or later; retained README says v3 or any earlier version. Both original notices and LGPL text remain authenticated; this package does not resolve their wording conflict or substitute the GMT software licence.','inputs':list(pins.values()),'limits':['All five semantic decisions remain open; Cebu/Iloilo parent-name unions, Cotabato remote zero-overlap parent matches, Tagoloan in Cagayan de Oro and Cainta in Metro Manila are exact original scope, not contemporary city boundary claims.','Whole source-member ancestry permits testing the existing source-relative native rule only; it does not independently grant positive authority. The native constructor must qualify each original cell.','The sources are complete consumed simplified products. Recorded represented year 2020, January 2023 source update and July/December 2023 builds do not establish an effective observation date.','The source canonical Municipalities label is generic; prior unit-specific Philippine city/municipality role warnings remain. No current legal role is inferred solely from ADM level.','Source-union/current symmetric differences in the source assessment are squared-degree diagnostics, not physical area measurements.','No original pre-adaptation constructor or historical unsafe helper is replayed; retained audit observations remain their original vintage.']}
body=(json.dumps(result,ensure_ascii=False,separators=(',',':'))+'\n').encode();assert len(body)<=MAX and total+len(body)<=PHASE;assert O.parent.is_dir() and not O.exists() and all(not p.is_symlink() for p in (O,*O.parents));O.mkdir()
with (O/'construction-and-source-limits.json').open('xb') as f:f.write(body)
with (O/'preparation.json').open('x') as f:json.dump({'complete':True,'bytes':len(body),'sha256':sha(body)},f);f.write('\n')
print(json.dumps({'aggregate_members':result['aggregate_source_members'],'aggregate_cells':result['aggregate_original_cells'],'products':len(result['recorded_product_metadata']),'processing_bytes':total}))
