#!/usr/bin/env python3
"""Exhaustively reconcile the 376 #485 source IDs against StatCan 2016/2021 CSD evidence."""
from __future__ import annotations
import csv, gzip, json, re, unicodedata, hashlib, datetime, collections
from pathlib import Path
from pyproj import Transformer
from shapely.geometry import shape
from shapely import make_valid
from shapely.ops import transform
from shapely.strtree import STRtree
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
BASE=ROOT/'data/regional-review/regional-review-4254da254d94f450'
def norm(s):
 s=unicodedata.normalize('NFKD',s or '').encode('ascii','ignore').decode().casefold()
 return re.sub(r'[^a-z0-9]+','',s)
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def write_json(path,obj):
 path.write_text(json.dumps(obj,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
def geometry_parts(geometry):
 if geometry.get('type')=='Polygon':return 1
 if geometry.get('type')=='MultiPolygon':return len(geometry.get('coordinates',[]))
 return 0
roster=json.loads((OUT/'source-member-roster.json').read_text())['members']
statcan=json.loads((OUT/'statistics-canada-british-columbia-census-subdivisions-2016.geojson').read_text())
prior=json.loads((BASE/'assessment.json').read_text())
baseline_2021=BASE/'sources/statistics-canada-bc-census-subdivisions-2021.geojson.gz'
# Match the CRS used by the parent #485 source/CSD screen and StatCan's source file.
project=Transformer.from_crs(4326,3347,always_xy=True).transform
def projected(geojson):
 g=transform(project,shape(geojson))
 return g if g.is_valid else make_valid(g)
csd=[]
for f in statcan['features']:
 p=f['properties']; g=projected(f['geometry'])
 csd.append((p,g))
tree=STRtree([x[1] for x in csd])
sources={}
for part in range(1,5):
 d=json.loads((OUT/f'geoboundaries-bc-2016-members-part-{part:02d}-of-04.geojson').read_text())
 for f in d['features']:sources[f['properties']['shapeID']]=f
assert len(roster)==376 and len(sources)==376 and set(sources)=={r['source_shape_id'] for r in roster}
# Retain only the 2021 official candidate geometries that triggered the 33 low-overlap flags.
low_2021_ids={m['best_2021_csd_id'] for loc in prior['locations']
 if loc['current_parent_id']=='framework:province:british-columbia:83abeaaac0ca'
 for m in loc['source_identity_and_vintage'].get('members',[]) if m['overlap_pct']<95}
with gzip.open(baseline_2021,'rt',encoding='utf-8') as f: full_2021=json.load(f)
features_2021={str(f['properties']['CSDUID']):f for f in full_2021['features']}
csd_2021_by_cd=collections.defaultdict(list)
for f in full_2021['features']:csd_2021_by_cd[str(f['properties']['CSDUID'])[:4]].append(f)
assert len(low_2021_ids)==33 and low_2021_ids<=features_2021.keys()
all_2021_ids={m['best_2021_csd_id'] for loc in prior['locations']
 if loc['current_parent_id']=='framework:province:british-columbia:83abeaaac0ca'
 for m in loc['source_identity_and_vintage'].get('members',[])}
assert len(all_2021_ids)==374 and all_2021_ids<=features_2021.keys()
write_json(OUT/'statistics-canada-2021-csd-identity-extract.json',{'source_baseline_path':str(baseline_2021.relative_to(ROOT)),'source_baseline_bytes':baseline_2021.stat().st_size,'source_baseline_sha256':sha(baseline_2021),'extract_count':len(all_2021_ids),'records':[{**features_2021[k]['properties'],'CDUID_prefix_from_CSDUID':k[:4]} for k in sorted(all_2021_ids)]})
low_features=[features_2021[k] for k in sorted(low_2021_ids)]
(OUT/'statistics-canada-bc-csd-2021-low-overlap-targets.geojson').write_text(
 json.dumps({'type':'FeatureCollection','features':low_features},ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
current_2021={str(f['properties']['CSDUID']):(f['properties'],projected(f['geometry'])) for f in low_features}
# The CSV's table note fixes the time window; retain the actual one-based CSV line for every cited event.
change_path=OUT/'sources/statistics-canada-2016-2021-csd-changes.csv.gz'
with gzip.open(change_path,mode='rt',encoding='cp1252',newline='') as fp: csvrows=list(csv.reader(fp))
header=[x.strip() for x in csvrows[2]]; hix={k:i for i,k in enumerate(header)}
start=datetime.date(2016,1,2); end=datetime.date(2021,1,1)
events=[]; in_bc=False; bc_section_rows=0; out_of_window=0
for line,row in enumerate(csvrows[3:],4):
 row=(row+['']*len(header))[:len(header)]; e={k:row[i].strip() for k,i in hix.items()}
 if e.get('Gaining CSDuid')=='British Columbia' and not e.get('Gaining CSDname'):
  in_bc=True; continue
 if e.get('Gaining CSDuid') and not e['Gaining CSDuid'].isdigit():
  in_bc=False; continue
 if not in_bc or not e.get('Effective Date'):continue
 bc_section_rows+=1
 date=datetime.datetime.strptime(e['Effective Date'],'%d/%m/%Y').date()
 if not start<=date<=end:
  out_of_window+=1; continue
 events.append({'csv_line':line,**e})
results=[]
for m in roster:
 sid=m['source_shape_id']; source_feature=sources[sid]
 sg=projected(source_feature['geometry']); sa=sg.area
 candidates=[]
 for idx in tree.query(sg):
  idx=int(idx); p,cg=csd[idx]; inter=sg.intersection(cg).area
  if inter<=0:continue
  candidates.append({'csduid_2016':p['CSDUID'],'csdname_2016':p['CSDNAME'],'csdtype_2016':p['CSDTYPE'],'cd_uid_2016':p['CDUID'],'cd_name_2016':p['CDNAME'],'intersection_km2':round(inter/1e6,6),'source_covered_pct':round(100*inter/sa,6) if sa else 0,'csd_covered_pct':round(100*inter/cg.area,6) if cg.area else 0,'name_exact_normalized':norm(m['source_name'])==norm(p['CSDNAME'])})
 candidates.sort(key=lambda c:(-c['source_covered_pct'],-c['csd_covered_pct'],c['csduid_2016']))
 assert candidates, f'no 2016 official CSD intersection: {sid}'
 best=candidates[0]; old=best['csduid_2016']; current=m['best_2021_csd_id']
 current_feature=features_2021[current]['properties']
 assert current_feature['CSDNAME']==m['best_2021_csd_name'],(sid,current_feature['CSDNAME'],m['best_2021_csd_name'])
 relevant=[e for e in events if e['Losing CSDuid']==old or e['Gaining CSDuid']==old]
 outgoing=[e for e in events if e['Losing CSDuid']==old]
 successor_ids=sorted({e['Gaining CSDuid'] for e in outgoing if e['Gaining CSDuid'].isdigit() and e['Gaining CSDuid']!=old})
 if current==old:
  mapping_status='same_2016_2021_csduid'
 elif current in successor_ids:
  mapping_status='direct_successor_in_official_change_table'
 else:
  mapping_status='unresolved_candidate_to_official_transition'
 assert mapping_status!='unresolved_candidate_to_official_transition', (sid,old,current,successor_ids)
 # Name comparison is an identity clue, not an ownership judgment. The source name is retained exactly as received.
 flags={'no_exact_2021_name':m['name_matches_2021_csd_within_cd']==0,'multiple_exact_2021_names':m['name_matches_2021_csd_within_cd']>1,'best_2021_overlap_below_95':m['prior_overlap_pct']<95,'best_2021_overlap_below_50':m['prior_overlap_pct']<50}
 source_to_2016_name_count=sum(c['name_exact_normalized'] for c in candidates)
 extent_note=None
 if best['source_covered_pct']<95 or best['csd_covered_pct']<95:
  extent_note='The strongest 2016 official-CSD identity candidate has a source/target area difference above 5%; this is an extent discrepancy, not a political-ownership conclusion. Preserve the source geometry and report the measured difference separately from the identity crosswalk.'
 current_geom=None;current_props=None;screen_recomputed=None;old_to_current=None;current_to_old=None
 if flags['best_2021_overlap_below_95']:
  current_props,current_geom=current_2021[current]
  inter=sg.intersection(current_geom).area
  screen_recomputed=100*inter/sa if sa else 0
  assert abs(screen_recomputed-m['prior_overlap_pct'])<0.002, (sid,screen_recomputed,m['prior_overlap_pct'])
  old_geom=csd[[p['CSDUID'] for p,g in csd].index(old)][1]
  old_to_current=100*old_geom.intersection(current_geom).area/old_geom.area if old_geom.area else 0
  current_to_old=100*old_geom.intersection(current_geom).area/current_geom.area if current_geom.area else 0
 current_parent_cd=m['location_id'].split(':')[2].split('-')[1]
 name_candidates=[{'csduid':str(f['properties']['CSDUID']),'csdname':f['properties']['CSDNAME'],'csdtype':f['properties']['CSDTYPE']} for f in csd_2021_by_cd[current_parent_cd] if norm(f['properties']['CSDNAME'])==norm(m['source_name'])]
 assert len(name_candidates)==m['name_matches_2021_csd_within_cd'],(sid,len(name_candidates),m['name_matches_2021_csd_within_cd'])
 current_cd_uid=str(current_feature['CSDUID'])[:4]
 assert current_cd_uid==current_parent_cd,(sid,current_cd_uid,current_parent_cd)
 assert best['cd_uid_2016']==current_parent_cd,(sid,best['cd_uid_2016'],current_parent_cd)
 if screen_recomputed is not None and (old_to_current<95 or current_to_old<95):
  extent_status='unresolved_official_2016_to_2021_extent_difference'
  extent_note='Official 2016 CSD to assigned 2021 CSD geometry coverage is below 95% in at least one direction. Related Table 1 rows are retained when present, but the table does not quantify geometry and may omit changes; no boundary decision is inferred.'
 elif screen_recomputed is not None:
  extent_status='unresolved_geoBoundaries_to_StatCan_extent_difference'
  extent_note='Official 2016 and assigned 2021 CSD footprints cover at least 95% in both directions, while the retained 2016 geoBoundaries source shape has a sub-95% 2021 overlay. The source-to-2016 match is separately recorded; remaining extent cause is unresolved.'
 elif best['source_covered_pct']<95 or best['csd_covered_pct']<95:
  extent_status='unresolved_geoBoundaries_to_StatCan_2016_extent_difference'
  extent_note='The strongest 2016 official-CSD identity candidate has a source/target area difference above 5%; this is an extent discrepancy, not a political-ownership conclusion. Preserve the source geometry and report the measured difference separately from identity.'
 else:
  extent_status='no_extent_exception_in_remeasured_scope'
 results.append({**m,'source_feature_name_as_delivered':source_feature['properties']['shapeName'],'source_geometry_type':source_feature['geometry']['type'],'source_geometry_part_count':geometry_parts(source_feature['geometry']),'inherited_2021_screen_flags':flags,'same_name_2021_candidates_in_parent_cd':name_candidates,'official_2016_csd_match':best,'other_2016_candidates':candidates[1:5],'exact_normalized_2016_name_candidate_count':source_to_2016_name_count,'selected_2016_csd_uid':old,'selected_2016_csd_name':best['csdname_2016'],'selected_2016_csd_type':best['csdtype_2016'],'source_2016_parent_cd_uid':best['cd_uid_2016'],'current_parent_cd_uid':current_parent_cd,'parent_cd_code_consistent':best['cd_uid_2016']==current_parent_cd,'candidate_2021_csd_uid_from_485':current,'candidate_2021_csd_name_from_485':m['best_2021_csd_name'],'current_2021_csd_type':current_feature['CSDTYPE'],'current_2021_parent_cd_uid':current_cd_uid,'current_parent_cd_consistent_2021':current_cd_uid==current_parent_cd,'official_transition_status':mapping_status,'direct_successor_csd_uids_from_change_table':successor_ids,'relevant_official_change_table_rows':relevant,'extent_status':extent_status,'extent_assessment':extent_note,'official_2021_candidate_geometry_recomputed':screen_recomputed is not None,'recomputed_source_to_2021_candidate_overlap_pct':round(screen_recomputed,6) if screen_recomputed is not None else None,'official_2016_to_2021_candidate_overlap_2016_covered_pct':round(old_to_current,6) if old_to_current is not None else None,'official_2016_to_2021_candidate_overlap_2021_covered_pct':round(current_to_old,6) if current_to_old is not None else None})
# Every source subject maps to a distinct 2016 CSD UID; the two changed UIDs are complete annexations.
uid_counts=collections.Counter(r['selected_2016_csd_uid'] for r in results)
assert len(uid_counts)==376 and max(uid_counts.values())==1
assert sum(r['parent_cd_code_consistent'] for r in results)==376
assert sum(r['current_parent_cd_consistent_2021'] for r in results)==376
assert sum(r['official_transition_status']=='same_2016_2021_csduid' for r in results)==374
assert sum(r['official_transition_status']=='direct_successor_in_official_change_table' for r in results)==2
# Verify the only different-UID mappings are explicit dissolutions/complete annexations.
changed=[r for r in results if r['official_transition_status']!='same_2016_2021_csduid']
for r in changed:
 ev=[e for e in r['relevant_official_change_table_rows'] if e['Losing CSDuid']==r['selected_2016_csd_uid'] and e['Gaining CSDuid']==r['candidate_2021_csd_uid_from_485']]
 assert ev and any('complete annexation' in e['Gaining Change Code Description'].casefold() and e['Losing Change Code Description'].casefold()=='dissolution' for e in ev)
summary={
 'assigned_members':len(results),'unique_source_ids':len({r['source_shape_id'] for r in results}),
 'unique_2016_csd_uids':len(uid_counts),'official_2016_british_columbia_csd_count':len(csd),
 'source_2016_cd_uid_matches_inherited_current_parent_cd_for_all_members':sum(r['official_2016_csd_match']['cd_uid_2016']==r['location_id'].split(':')[2].split('-')[1] for r in results),
 'source_2021_cd_uid_matches_inherited_current_parent_cd_for_all_members':sum(r['current_parent_cd_consistent_2021'] for r in results),
 'baseline_no_exact_2021_name':sum(r['inherited_2021_screen_flags']['no_exact_2021_name'] for r in results),
 'baseline_multiple_exact_2021_names':sum(r['inherited_2021_screen_flags']['multiple_exact_2021_names'] for r in results),
 'baseline_best_overlap_below_95':sum(r['inherited_2021_screen_flags']['best_2021_overlap_below_95'] for r in results),
 'baseline_best_overlap_below_50':sum(r['inherited_2021_screen_flags']['best_2021_overlap_below_50'] for r in results),
 'baseline_flagged_union':sum(any(r['inherited_2021_screen_flags'].values()) for r in results),
 'source_to_2016_exact_name_match_counts':dict(sorted(collections.Counter(str(r['exact_normalized_2016_name_candidate_count']) for r in results).items())),
 'unique_2016_to_2021_same_csd_uid':sum(r['official_transition_status']=='same_2016_2021_csduid' for r in results),
 'unique_2016_to_2021_direct_successor':sum(r['official_transition_status']=='direct_successor_in_official_change_table' for r in results),
 '2016_source_to_csd_coverage_below_95':sum(r['official_2016_csd_match']['source_covered_pct']<95 for r in results),
 '2016_csd_types':dict(sorted(collections.Counter(r['selected_2016_csd_type'] for r in results).items())),
 'bc_table_rows_all_effective_dates':bc_section_rows,'bc_table_rows_within_2016_01_02_to_2021_01_01':len(events),'bc_table_rows_outside_requested_period':out_of_window,
 'events_associated_with_assigned_2016_csd_uids':sum(bool(r['relevant_official_change_table_rows']) for r in results),
 'low_overlap_2021_candidates_recomputed_from_official_geometries':sum(r['official_2021_candidate_geometry_recomputed'] for r in results),
 'low_overlap_recomputed_matches_prior_within_0_002_percentage_points':sum(r['official_2021_candidate_geometry_recomputed'] and abs(r['recomputed_source_to_2021_candidate_overlap_pct']-r['prior_overlap_pct'])<0.002 for r in results),
 'official_2016_to_2021_low_overlap_targets_below_95_pct_in_either_direction':sum(r['official_2016_to_2021_candidate_overlap_2016_covered_pct'] is not None and (r['official_2016_to_2021_candidate_overlap_2016_covered_pct']<95 or r['official_2016_to_2021_candidate_overlap_2021_covered_pct']<95) for r in results),
 'geoBoundaries_2016_source_to_StatCan_2016_coverage_below_95_pct':sum(r['official_2016_csd_match']['source_covered_pct']<95 for r in results),
 'source_baseline_geojson_sha256':sha(BASE/'sources/geoboundaries-CAN-ADM3-2016.geojson'),
 'inherited_2021_source_sha256':sha(baseline_2021),
 'official_2016_bc_extract_sha256':sha(OUT/'statistics-canada-british-columbia-census-subdivisions-2016.geojson'),
 'official_change_csv_sha256':sha(change_path)
}
packet={'method':{'source_to_2016':'Reconstruct each of the 376 exact geoBoundaries shapes, transform source and official Statistics Canada 2016 Census Subdivision geometries to EPSG:3347 (Statistics Canada Lambert conformal conic), repair only temporary invalid geometry with GEOS make-valid, and calculate intersection/source area and intersection/CSD area. Candidate ranking is by source-covered percent, then CSD-covered percent, then CSDUID. Preserve exact raw names; normalized name comparison uses Unicode NFKD accent removal, casefold, and punctuation/whitespace collapse. This ranks one unique 2016 CSDUID for all 376 shapes; it is a crosswalk screen, not legal boundary or ownership determination.','2016_to_2021':'For each selected 2016 CSDUID, find official Table 1 event rows where it appears as gaining or losing, within the published effective-date window. The #485 best 2021 overlay candidate is reconciled by exact CSDUID continuity or a direct losing-to-gaining record. All 33 best-overlap-below-95 target geometries are extracted from the retained official 2021 source and remeasured; their source-overlap values reproduce #485 within 0.002 percentage points. The same 33 official 2016 and 2021 CSD footprints are compared in both directions. Table wording says its information may not include all changes; absence of a change row is not proof no boundary change.','change_table_scope':'Statistics Canada states Table 1 covers changes in effect from January 2, 2016 through January 1, 2021; only the British Columbia section and that period are used.','interpretation':'Census subdivision IDs/names/transition codes establish statistical administrative identity and vintage lineage. They do not establish political ownership, title, jurisdictional sovereignty or a political boundary decision. Preserve both source vintages and all geometry deltas.'},'summary':summary,'results':results}
(OUT/'crosswalk-2016-source-to-csd-assessment.json').write_text(json.dumps(packet,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(summary,indent=2))
