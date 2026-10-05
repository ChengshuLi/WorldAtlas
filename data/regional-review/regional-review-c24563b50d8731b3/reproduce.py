#!/usr/bin/env python3
"""Rebuild the bounded issue-72 identity and inherited screening table."""
import json,hashlib,subprocess,unicodedata
from pathlib import Path
from shapely.geometry import shape
from shapely.ops import transform
from shapely.affinity import translate
from pyproj import Transformer
B=Path(__file__).resolve().parent
BASELINE='7ffd4e35364ec8246b9add7459378b3f971fcd72'
def baseline_json(path): return json.loads(Path(path).read_bytes())
scope_doc=json.loads((B/'issue-scope.json').read_text()); scope=scope_doc['scope']; ids=scope['member_location_ids']; wanted=set(ids)
source_path=B/'sources/geoboundaries-9469f09/geoBoundaries-TUR-ADM2.geojson'; source=json.loads(source_path.read_text())['features']; source_by_id={'gb:TUR:ADM2:'+f['properties']['shapeID']:f for f in source}
adm1_path=B/'sources/geoboundaries-9469f09/ADM1/geoBoundaries-TUR-ADM1.geojson'; adm1=json.loads(adm1_path.read_text())['features']
project=Transformer.from_crs('EPSG:4326','EPSG:6933',always_xy=True).transform
parent_shapes=[(f['properties']['shapeName'],transform(project,shape(f['geometry']))) for f in adm1]
def geometry_shares(left,right):
 inter=left.intersection(right).area
 return inter/left.area,inter/right.area,inter/left.union(right).area
atlas={}; containing={}
part_paths=['data/'+rel for rel in baseline_json('data/world-index.json')['parts']]
base_paths=['data/world-index.json','data/hierarchy.json','data/granularity-review-evidence.json']+part_paths
subprocess.check_call(['git','diff','--quiet',BASELINE,'--']+base_paths)
for part in part_paths:
 path=Path(part)
 for f in baseline_json(part)['features']:
  i=f.get('properties',{}).get('id')
  if i in wanted:
   if i in atlas: raise SystemExit('duplicate atlas subject '+i)
   atlas[i]=f; containing[i]=path.as_posix()
if set(atlas)!=wanted: raise SystemExit('atlas scope mismatch')
if set(source_by_id).intersection(wanted)!=wanted: raise SystemExit('source scope mismatch')
review=baseline_json('data/granularity-review-evidence.json'); turkey=next(t for t in review['territories'] if t['reference_iso']=='TUR'); flags={r['id']:r for r in turkey['flagged_locations']}
prov={p['id']:p for p in scope['province_scopes']}; rows=[]
for i in sorted(ids):
 a=atlas[i]['properties']; s=source_by_id[i]['properties']; flag=flags.get(i,{})
 sg=transform(project,shape(source_by_id[i]['geometry'])); area=sg.area
 ag=transform(project,shape(atlas[i]['geometry']))
 atlas_cover,source_cover,iou=geometry_shares(ag,sg)
 overlaps=sorted(((sg.intersection(pg).area/area,name,pg.area) for name,pg in parent_shapes),reverse=True)
 source_name_norm=unicodedata.normalize('NFKD',s['shapeName']).casefold()
 source_components=len(sg.geoms) if hasattr(sg,'geoms') else 1
 atlas_components=len(ag.geoms) if hasattr(ag,'geoms') else 1
 rows.append({'source_area_km2_equal_area':round(area/1_000_000,3),'source_parent_area_share':round(area/overlaps[0][2],6),'source_components':source_components,'atlas_components':atlas_components,'possible_central_district_label':'merkez' in source_name_norm,'source_name_is_only_merkez':source_name_norm.strip()=='merkez','atlas_source_geometry':{'atlas_covered_by_source':round(atlas_cover,6),'source_covered_by_atlas':round(source_cover,6),'intersection_over_union':round(iou,6),'atlas_components':len(ag.geoms) if hasattr(ag,'geoms') else 1,'source_components':len(sg.geoms) if hasattr(sg,'geoms') else 1},'classification':'insufficient-evidence','classification_reason':'No authoritative 2021 legal roster/parent crosswalk and no 2021 official boundary geometry retained; current source identity/name and ADM1 overlay corroborate but do not establish legal territorial status or boundary truth.','follow_up_flags':flag.get('reasons',[]),'source_adm1_top_parent':overlaps[0][1],'source_adm1_top_share':round(overlaps[0][0],6),'source_adm1_runner_up':overlaps[1][1],'source_adm1_runner_up_share':round(overlaps[1][0],6),'source_top_parent_matches_atlas':overlaps[0][1]==prov.get(a['parent_id'],{}).get('name'),'location_id':i,'atlas_name':a['name'],'source_name':s['shapeName'],'name_match':a['name']==s['shapeName'],'atlas_parent_id':a['parent_id'],'declared_issue_parent':prov.get(a['parent_id'],{}).get('name'),'parent_in_issue_scope':a['parent_id'] in prov,'source_boundary_id':s['shapeID'],'source_level':s['shapeType'],'source_country':s['shapeGroup'],'baseline_containing_file':containing[i],'prior_screen_flags':flag.get('reasons',[]),'prior_screen_parent_overlap':flag.get('parent_overlap'),'prior_screen_components':flag.get('components')})
if any(not r['name_match'] or not r['parent_in_issue_scope'] or not r['source_top_parent_matches_atlas'] or r['source_adm1_top_share']<0.95 for r in rows): raise SystemExit('name/parent source overlay mismatch')
control_geom=transform(project,shape(source[0]['geometry']))
if any(abs(v-1.0)>1e-12 for v in geometry_shares(control_geom,control_geom)): raise SystemExit('positive geometry control failed')
if geometry_shares(control_geom,translate(control_geom,xoff=5000000))[2]>=0.5: raise SystemExit('negative geometry control failed')
adm1_by_name={f['properties']['shapeName']:f for f in adm1}
province_summary=[]
for pid,p in sorted(prov.items(),key=lambda item:item[1]['name']):
 sf=adm1_by_name.get(p['name'])
 if sf is None: raise SystemExit('issue province missing from pinned ADM1 source: '+p['name'])
 province_summary.append({'province_id':pid,'name':p['name'],'issue_subject_count':sum(r['atlas_parent_id']==pid for r in rows),'source_boundary_id':sf['properties']['shapeID'],'source_iso':sf['properties'].get('shapeISO'),'source_name':sf['properties']['shapeName']})
if sum('weak-source-parent-match' in r['prior_screen_flags'] for r in rows)!=3: raise SystemExit('unexpected weak-parent flag count')
if sum('multipart-footprint' in r['prior_screen_flags'] for r in rows)!=2: raise SystemExit('unexpected multipart flag count')
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
paths={str(source_path),str(B/'issue-scope.json'),str(B/'sources/geoboundaries-9469f09/ADM1/geoBoundaries-TUR-ADM1.geojson'),str(B/'sources/geoboundaries-9469f09/ADM1/geoBoundaries-TUR-ADM1-metaData.json'),str(adm1_path),str(B/'sources/geoboundaries-9469f09/geoBoundaries-TUR-ADM2-metaData.json'),str(B/'sources/hgm-current-reference/turkiye-mulki-idare-sinirlari-2083.rar')}
inputs={p:sha(p) for p in sorted(paths)}
baseline_inputs={p:sha(p) for p in sorted(set(['data/granularity-review-evidence.json','data/world-index.json','data/hierarchy.json']+list(containing.values())))}
report={'version':1,'issue':72,'baseline_commit':BASELINE,'baseline_input_sha256':baseline_inputs,'scope':{'subject_count':len(ids),'subject_ids_sha256':hashlib.sha256(('\n'.join(sorted(ids))+'\n').encode()).hexdigest(),'area_scopes':scope['area_scopes'],'province_summary':province_summary,'province_scopes':[{'id':p['id'],'name':p['name'],'owned_location_count':len(p['owned_location_ids'])} for p in scope['province_scopes']],'owned_path':scope['owned_evidence_path']},'inputs_sha256':inputs,'findings':{'subjects_with_one_pinned_geoBoundaries_feature':sum(r['location_id'] in source_by_id for r in rows),'subjects_with_one_baseline_atlas_feature':len(atlas),'atlas_source_name_matches':sum(r['name_match'] for r in rows),'atlas_parent_present_in_issue_parent_scopes':sum(r['parent_in_issue_scope'] for r in rows),'geoBoundaries_adm1_top_overlay_agrees_with_declared_parent':sum(r['source_top_parent_matches_atlas'] for r in rows),'source_adm1_top_overlap_at_least_95_percent':sum(r['source_adm1_top_share']>=0.95 for r in rows),'source_multipart_feature_count':sum(r['source_components']>1 for r in rows),'atlas_multipart_feature_count':sum(r['atlas_components']>1 for r in rows),'possible_central_district_labels':sum(r['possible_central_district_label'] for r in rows),'standalone_merkez_labels':sum(r['source_name_is_only_merkez'] for r in rows),'children_over_50_percent_of_source_parent_area':sum(r['source_parent_area_share']>0.5 for r in rows),'maximum_source_parent_area_share':max(r['source_parent_area_share'] for r in rows),'atlas_source_iou_below_0_90':sum(r['atlas_source_geometry']['intersection_over_union']<0.90 for r in rows),'minimum_atlas_in_source_area_share':min(r['atlas_source_geometry']['atlas_covered_by_source'] for r in rows),'minimum_source_in_atlas_area_share':min(r['atlas_source_geometry']['source_covered_by_atlas'] for r in rows),'minimum_atlas_source_iou':min(r['atlas_source_geometry']['intersection_over_union'] for r in rows),'prior_weak_parent_screen_flags':sum('weak-source-parent-match' in r['prior_screen_flags'] for r in rows),'prior_multipart_screen_flags':sum('multipart-footprint' in r['prior_screen_flags'] for r in rows),'source_country_adm2_count':len(source),'source_country_adm1_count':len(json.loads((B/'sources/geoboundaries-9469f09/ADM1/geoBoundaries-TUR-ADM1.geojson').read_text())['features'])},'geometry_method':{'operation':'Intersection share of each pinned ADM2 source polygon against all pinned ADM1 source province polygons; select greatest share.','input_coordinates':'GeoJSON longitude, latitude (EPSG:4326)','area_crs':'EPSG:6933 equal-area projection; ratio only, not legal boundary accuracy','software':{'shapely':'2.1.2','pyproj':'3.7.2'},'positive_control':'Each of 226 source districts has its issue-declared province as the unique top intersection at >=95% area; identical polygons produce area shares and IoU of 1.0.','negative_control':'A province mismatch or top-share below 95% aborts reproduction; a translated synthetic polygon must produce IoU below 0.5.'},'assessments':rows,'limits':['Identity and displayed name match do not establish each district legal status or boundary accuracy.','Atlas parent references are structurally within this issue scope; the three prior weak overlap flags require district-level source/parent investigation and are unresolved.','Seven source multipart features include five represented as single-component atlas geometries; they and the two inherited atlas multipart flags require review, not automatic correction.','Counts do not establish roster completeness. The raw 973 feature count numerically equals TurkStat’s 922 non-center districts plus 51 province centers, but no ID crosswalk proves unit equivalence; geoBoundaries metadata says 999, 26 above the raw file count.','The current HGM boundary archive is indicative, not official, and is not the pinned 2021 source vintage; it cannot establish historical 2021 geometry.','No regional approval, boundary correctness certificate, import authorization, or engineering correction is proposed.']}
out=B/'district-assessments.json'; out.write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
print('wrote',out,'bytes',out.stat().st_size,'sha256',sha(out),'rows',len(rows))
