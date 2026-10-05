#!/usr/bin/env python3
"""Rebuild the bounded issue-72 identity and inherited screening table."""
import json,glob,hashlib,os
from pathlib import Path
B=Path(__file__).resolve().parent
scope_doc=json.loads((B/'issue-scope.json').read_text()); scope=scope_doc['scope']; ids=scope['member_location_ids']; wanted=set(ids)
source_path=B/'sources/geoboundaries-9469f09/geoBoundaries-TUR-ADM2.geojson'; source=json.loads(source_path.read_text())['features']; source_by_id={'gb:TUR:ADM2:'+f['properties']['shapeID']:f for f in source}
atlas={}; containing={}
for path in sorted(Path('data/geography').glob('part-*.json')):
 for f in json.loads(path.read_text())['features']:
  i=f.get('properties',{}).get('id')
  if i in wanted:
   if i in atlas: raise SystemExit('duplicate atlas subject '+i)
   atlas[i]=f; containing[i]=path.as_posix()
if set(atlas)!=wanted: raise SystemExit('atlas scope mismatch')
if set(source_by_id).intersection(wanted)!=wanted: raise SystemExit('source scope mismatch')
review=json.loads(Path('data/granularity-review-evidence.json').read_text()); turkey=next(t for t in review['territories'] if t['reference_iso']=='TUR'); flags={r['id']:r for r in turkey['flagged_locations']}
prov={p['id']:p for p in scope['province_scopes']}; rows=[]
for i in sorted(ids):
 a=atlas[i]['properties']; s=source_by_id[i]['properties']; flag=flags.get(i,{})
 rows.append({'location_id':i,'atlas_name':a['name'],'source_name':s['shapeName'],'name_match':a['name']==s['shapeName'],'atlas_parent_id':a['parent_id'],'declared_issue_parent':prov.get(a['parent_id'],{}).get('name'),'parent_in_issue_scope':a['parent_id'] in prov,'source_boundary_id':s['shapeID'],'source_level':s['shapeType'],'source_country':s['shapeGroup'],'baseline_containing_file':containing[i],'prior_screen_flags':flag.get('reasons',[]),'prior_screen_parent_overlap':flag.get('parent_overlap'),'prior_screen_components':flag.get('components')})
if any(not r['name_match'] or not r['parent_in_issue_scope'] for r in rows): raise SystemExit('name/parent review mismatch')
if sum('weak-source-parent-match' in r['prior_screen_flags'] for r in rows)!=3: raise SystemExit('unexpected weak-parent flag count')
if sum('multipart-footprint' in r['prior_screen_flags'] for r in rows)!=2: raise SystemExit('unexpected multipart flag count')
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
paths={str(source_path),str(B/'issue-scope.json'),'data/granularity-review-evidence.json','data/world-index.json','data/hierarchy.json'}|set(containing.values())|{str(B/'sources/geoboundaries-9469f09/ADM1/geoBoundaries-TUR-ADM1.geojson'),str(B/'sources/geoboundaries-9469f09/ADM1/geoBoundaries-TUR-ADM1-metaData.json'),str(B/'sources/geoboundaries-9469f09/geoBoundaries-TUR-ADM2-metaData.json'),str(B/'sources/hgm-current-reference/turkiye-mulki-idare-sinirlari-2083.rar')}
inputs={p:sha(p) for p in sorted(paths)}
report={'version':1,'issue':72,'baseline_commit':'9f51f7aa535b8570a20bf7e9d31d247e1d89a437','scope':{'subject_count':len(ids),'subject_ids_sha256':hashlib.sha256(('\n'.join(sorted(ids))+'\n').encode()).hexdigest(),'area_scopes':scope['area_scopes'],'province_scopes':[{'id':p['id'],'name':p['name'],'owned_location_count':len(p['owned_location_ids'])} for p in scope['province_scopes']],'owned_path':scope['owned_evidence_path']},'inputs_sha256':inputs,'findings':{'subjects_with_one_pinned_geoBoundaries_feature':sum(r['location_id'] in source_by_id for r in rows),'subjects_with_one_baseline_atlas_feature':len(atlas),'atlas_source_name_matches':sum(r['name_match'] for r in rows),'atlas_parent_present_in_issue_parent_scopes':sum(r['parent_in_issue_scope'] for r in rows),'prior_weak_parent_screen_flags':sum('weak-source-parent-match' in r['prior_screen_flags'] for r in rows),'prior_multipart_screen_flags':sum('multipart-footprint' in r['prior_screen_flags'] for r in rows),'source_country_adm2_count':len(source),'source_country_adm1_count':len(json.loads((B/'sources/geoboundaries-9469f09/ADM1/geoBoundaries-TUR-ADM1.geojson').read_text())['features'])},'assessments':rows,'limits':['Identity and displayed name match do not establish each district legal status or boundary accuracy.','Atlas parent references are structurally within this issue scope; the three prior weak overlap flags require district-level source/parent investigation and are unresolved.','Two multipart flags are preservation/review prompts, not errors.','Counts do not establish roster completeness. TurkStat counts exclude provincial centers from the district count; this accounts for 51 units of the 999 vs 973 observed difference, leaving an unexplained 26-feature difference that requires a source crosswalk.','The current HGM boundary archive is indicative, not official, and is not the pinned 2021 source vintage; it cannot establish historical 2021 geometry.','No regional approval, boundary correctness certificate, import authorization, or engineering correction is proposed.']}
out=B/'district-assessments.json'; out.write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
print('wrote',out,'bytes',out.stat().st_size,'sha256',sha(out),'rows',len(rows))
