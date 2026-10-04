#!/usr/bin/env python3
"""Rebuild the complete 226-member Nigeria/Senegal/Sierra Leone source assessment."""
from __future__ import annotations
import csv,gzip,hashlib,io,json,pathlib,re,unicodedata,zipfile
from collections import Counter,defaultdict
from shapely.geometry import shape
from shapely.strtree import STRtree
from shapely.ops import transform
from pyproj import Geod,Transformer

ROOT=pathlib.Path(__file__).resolve().parent;SRC=ROOT/'sources';REPO=ROOT.parents[2]
PROJECT=Transformer.from_crs('EPSG:4326','EPSG:6933',always_xy=True).transform
GEOD=Geod(ellps='WGS84')
CODES={'NGA':('Nigeria','nga','2022','Local Government Areas'),'SEN':('Senegal','sen','2019','department'),'SLE':('Sierra Leone','sle','2017','Districts')}
ALIASES={'NGA':{'kirikasama':'Kiri Kasamma','barkinladi':'Barikin Ladi','tarmuwa':'Tarmua','birninkudu':'Birni Kudu','dambam':'Damban'},
 'SEN':{'tivaoune':'Tivaouane','medinayoroufoula':'Médina-Yorofoula'},'SLE':{}}
PARENT_ALIASES={'westernarea':'western'}

def sha(b):return hashlib.sha256(b).hexdigest()
def norm(s):
 s=unicodedata.normalize('NFKD',str(s or '')).encode('ascii','ignore').decode().lower()
 return re.sub(r'[^a-z0-9]','',s)
def unz(name):return gzip.decompress((SRC/name).read_bytes())
def zipjson(code,layer):
 _,slug,_,_=CODES[code]; archive=unz(f'hdx-cod-ab-{slug if code!="SEN" else "sen"}-admin-boundaries.geojson.zip.gz')
 # Filenames are country ISO lowercase; Senegal catalog uses SEN.
 with zipfile.ZipFile(io.BytesIO(archive)) as z:return json.loads(z.read(f'{slug}_{layer}.geojson'))
def projected(g):return transform(PROJECT,g)
def area(g):return projected(g).area/1e6
def geodesic_km(g):return abs(GEOD.geometry_length(g))/1000
def geom_parts(g):return list(g.geoms) if g.geom_type=='MultiPolygon' else [g]
def write_csv(name,rows):
 p=ROOT/name
 fields=list(rows[0]) if rows else []
 with p.open('w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(rows)

def read_old(code):
 year=CODES[code][2]
 return json.loads(unz(f'geoboundaries-{code}-adm2-{year}.geojson.gz'))['features']
def read_current(code,layer):return zipjson(code,layer)['features']

def main():
 scope=json.loads((ROOT/'scope.json').read_text()); ids=scope['member_location_ids']; members=json.loads((ROOT/'baseline-members.json').read_text())
 assert len(ids)==226 and len(set(ids))==226 and [m['id'] for m in members]==ids
 assert hashlib.sha256((ROOT/'issue-scope-pinned.json').read_bytes()).hexdigest()==scope['issue_scope_sha256']
 sources={c:{'old':read_old(c),'admin2':read_current(c,'admin2'),'admin1':read_current(c,'admin1'),'admin0':read_current(c,'admin0'),'caps':read_current(c,'admincapitals')} for c in CODES}
 places=json.loads(unz('wca-settlement-points-region-subset.geojson.gz'))['features']
 sen_places=json.loads(unz('senegal-settlements-2017.geojson.gz'))['features']
 # Retain source identity and code inventories for exact crosswalk reproduction.
 old_by={}; current_by={}; admin1_by={}; caps_by=defaultdict(list)
 for code,data in sources.items():
  old_by[code]={f['properties']['shapeID']:f for f in data['old']}
  current_by[code]=defaultdict(list)
  for f in data['admin2']:
   p=f['properties'];current_by[code][norm(p.get('adm2_name'))].append(f)
  admin1_by[code]={f['properties'].get('adm1_pcode'):f for f in data['admin1']}
  for f in data['caps']:
   p=f['properties'];caps_by[(code,p.get('adm2_pcode'))].append(f)
 admin1_geom_by={code:{f['properties'].get('adm1_pcode'):projected(shape(f['geometry'])) for f in data['admin1']}
  for code,data in sources.items()}
 admin1_feature_by={code:{f['properties'].get('adm1_pcode'):f for f in data['admin1']} for code,data in sources.items()}
 # Country-wide current official polygons and spatial trees support complete candidate screens.
 current_geoms={};current_trees={};current_tree_rows={}
 for code,data in sources.items():
  rows=data['admin2'];geoms=[projected(shape(f['geometry'])) for f in rows]
  current_geoms[code]=geoms;current_trees[code]=STRtree(geoms);current_tree_rows[code]=rows
 # National/WCA settlement observations grouped strictly by publisher codes, not inferred member transfers.
 wca_by_code=defaultdict(list);wca_by_country=Counter();axis_rows=0
 for f in places:
  p=f['properties'];country=str(p.get('admin0Name') or '')
  code=next((c for c,(n,_,_,_) in CODES.items() if norm(n)==norm(country)),None)
  if not code:continue
  key=(code,p.get('admin2Pcod'));wca_by_code[key].append(f);wca_by_country[code]+=1
  q=f['geometry']['coordinates']
  if len(q)==2 and abs(float(q[0])-float(p.get('LAT') or 1e99))<1e-6 and abs(float(q[1])-float(p.get('LONG') or 1e99))<1e-6:axis_rows+=1
 sen_by_code=defaultdict(list)
 for f in sen_places:
  p=f['properties'];sen_by_code[p.get('admin2Pcod')].append(f)
 # A second, explicitly weaker settlement crosswalk handles different code vintages.
 # Require normalized ADM2 and ADM1 labels together; preserve exact-code evidence separately.
 wca_by_name_parent=defaultdict(list)
 for f in places:
  p=f['properties'];cc=next((c for c,(n,_,_,_) in CODES.items() if norm(n)==norm(p.get('admin0Name'))),None)
  if cc:wca_by_name_parent[(cc,norm(p.get('admin2Name')),norm(p.get('admin1Name')))].append(f)
 city_tokens={'Lagos':['lagos'],'Abuja':['abuja'],'Dakar':['dakar','pikine','guediawaye','rufisque','keurmassar'],'Freetown':['freetown']}
 city_matches=defaultdict(Counter)
 for q in places:
  p=q['properties'];cc=next((c for c,(n,_,_,_) in CODES.items() if norm(n)==norm(p.get('admin0Name'))),None)
  if not cc:continue
  nm=norm(p.get('featureNam'))
  for city,tokens in city_tokens.items():
   if any(norm(t) in nm for t in tokens):city_matches[(cc,city,p.get('admin2Pcod'),p.get('admin2Name'))][p.get('featureNam')]+=1

 # Complete current-code inventory in all three source countries, including external context.
 unit_rows=[]
 for code,(country,_,_,_) in CODES.items():
  for f in sources[code]['admin2']:
   p=f['properties'];g=shape(f['geometry']);parts=geom_parts(g)
   unit_rows.append({'country_code':code,'country':country,'current_name':p.get('adm2_name'),'current_pcode':p.get('adm2_pcode'),
    'current_parent_name':p.get('adm1_name'),'current_parent_pcode':p.get('adm1_pcode'),'current_valid_on':p.get('valid_on'),
    'current_valid_to':p.get('valid_to'),'source_version':p.get('version'),'source_area_km2':p.get('area_sqkm'),
    'geometry_valid':g.is_valid,'polygon_components':len(parts),'settlement_points_WCA_by_current_code':len(wca_by_code[(code,p.get('adm2_pcode'))]),
    'national_settlement_points_2017_by_current_code':len(sen_by_code.get(p.get('adm2_pcode'),[])) if code=='SEN' else None,
    'admin_capital_records':len(caps_by[(code,p.get('adm2_pcode'))]),'name_missing':not bool(p.get('adm2_name')),'pcode_missing':not bool(p.get('adm2_pcode'))})
 write_csv('current-unit-inventory.csv',unit_rows)

 component_rows=[];crosswalk_rows=[];assessment=[];anomalies=[];settlement_rows=[];city_rows=[];parent_scale_rows=[]
 used_current_codes=defaultdict(set);current_match_counts=Counter();status_counts=Counter();parent_counts=Counter()
 alias_rows=[];subject_intersection_count=0
 for member in members:
  mid=member['id'];code=member['owner'] and {'Nigeria':'NGA','Senegal':'SEN','Sierra Leone':'SLE'}[member['owner']]
  country=CODES[code][0];shape_id=mid.rsplit(':',1)[-1]
  oldf=old_by[code].get(shape_id)
  if not oldf:raise AssertionError(f'Pinned source feature absent: {mid}')
  op=oldf['properties'];old_name=op.get('shapeName') or '';g_old=shape(oldf['geometry']);old_m=projected(g_old)
  direct_name=ALIASES[code].get(norm(old_name),old_name);matched_by_name=current_by[code].get(norm(direct_name),[])
  if norm(old_name)!=norm(direct_name):alias_rows.append({'location_id':mid,'country':country,'legacy_name':old_name,'current_source_name':direct_name,'method':'explicit normalized source-name alias','finding':'Candidate orthographic alias; geometry and code evidence remain separately retained.'})
  # All positive-area intersections are preserved, including split/merge candidates.
  cand_ix=current_trees[code].query(old_m)
  positive=[]
  for j in cand_ix:
   cf=current_tree_rows[code][int(j)];cg=current_geoms[code][int(j)];inter=old_m.intersection(cg).area
   if inter<=0:continue
   cp=cf['properties'];union=old_m.union(cg).area
   row={'location_id':mid,'country_code':code,'legacy_name':old_name,'legacy_shape_id':shape_id,
    'current_name':cp.get('adm2_name'),'current_pcode':cp.get('adm2_pcode'),'current_parent':cp.get('adm1_name'),
    'intersection_km2':round(inter/1e6,6),'legacy_covered_pct':round(100*inter/old_m.area,5) if old_m.area else None,
    'current_covered_pct':round(100*inter/cg.area,5) if cg.area else None,'area_IoU':round(inter/union,7) if union else None,
    'normalized_name_candidate':norm(cp.get('adm2_name'))==norm(direct_name),
    'interpretation':'Positive-area source-vintage overlap candidate only; no boundary/member transfer is selected.'}
   positive.append((inter,cf,row));crosswalk_rows.append(row);subject_intersection_count+=1
  positive.sort(key=lambda x:x[0],reverse=True)
  # Keep all same-name candidates. If duplicate names exist, a spatial ranking is only a screen.
  candidates=matched_by_name[:]
  if not candidates and positive:
   max_area=positive[0][0]; candidates=[cf for inter,cf,_ in positive if abs(inter-max_area)<=max(1e-4,max_area*1e-8)]
  if candidates and len(candidates)>1:
   candidate_codes=[x['properties'].get('adm2_pcode') for x in candidates]
   chosen_rows=[x for x in positive if x[1] in candidates]
   # Retain plausible-name list; do not resolve names by an arbitrary overlap cutoff.
   choice_method='duplicate normalized current name; all candidates retained and overlap-ranked'
  elif candidates:
   candidate_codes=[candidates[0]['properties'].get('adm2_pcode')];choice_method='unique normalized current name/explicit alias'
  elif positive:
   max_area=positive[0][0];best=[cf for inter,cf,_ in positive if abs(inter-max_area)<=max(1e-4,max_area*1e-8)]
   candidates=best;candidate_codes=[x['properties'].get('adm2_pcode') for x in candidates];choice_method='no name match; highest positive-area overlap is a candidate only'
  else:
   candidate_codes=[];choice_method='no current name or positive-area intersection candidate'
  candidates=[f for f in candidates if f is not None];candidate_codes=sorted(set(x for x in candidate_codes if x))
  used_current_codes[code].update(candidate_codes);current_match_counts[code]+=bool(candidate_codes)
  # The largest overlap is descriptive only. Parent support uses the entire candidate set.
  top=positive[0] if positive else None
  atlas_parent=member['parent_id'].split(':')[-2].replace('-region','').replace('-',' ')
  parents=sorted({str(f['properties'].get('adm1_name') or '') for f in candidates})
  parent_norms={norm(x) for x in parents}; atlas_norm=norm(atlas_parent)
  parent_supported=bool(parents) and (parent_norms=={atlas_norm} or (atlas_norm in PARENT_ALIASES and parent_norms=={PARENT_ALIASES[atlas_norm]}))
  parent_ambiguous=len(parent_norms)>1
  if parent_supported: parent_status='supported'
  elif parent_ambiguous or not parents: parent_status='insufficient-evidence'
  else: parent_status='correction-needed'
  parent_counts[parent_status]+=1
  candidate_details=[];point_counts=[];admincap_details=[];point_names=[]
  for cf in candidates:
   p=cf['properties'];pcode=p.get('adm2_pcode');geom=shape(cf['geometry']);parts=geom_parts(geom)
   parent_geom=admin1_geom_by[code].get(p.get('adm1_pcode'));parent_feature=admin1_feature_by[code].get(p.get('adm1_pcode'))
   child_geom=projected(geom);parent_area=parent_geom.area if parent_geom else 0;child_area=child_geom.area
   parent_intersection=child_geom.intersection(parent_geom).area if parent_geom else 0
   sibling_count=sum(x['properties'].get('adm1_pcode')==p.get('adm1_pcode') for x in sources[code]['admin2'])
   parent_scale_rows.append({'location_id':mid,'location_name':member['name'],'country':country,
    'candidate_current_adm2_name':p.get('adm2_name'),'candidate_current_adm2_pcode':pcode,
    'candidate_current_adm1_parent':p.get('adm1_name'),'candidate_current_adm1_pcode':p.get('adm1_pcode'),
    'candidate_sibling_adm2_units_in_complete_country_inventory':sibling_count,
    'candidate_adm2_area_km2':round(child_area/1e6,6),'candidate_parent_adm1_area_km2':round(parent_area/1e6,6) if parent_geom else None,
    'candidate_adm2_to_adm1_area_ratio':round(child_area/parent_area,7) if parent_area else None,
    'adm2_area_covered_by_candidate_parent_pct':round(100*parent_intersection/child_area,6) if child_area else None,
    'parent_area_covered_by_candidate_adm2_pct':round(100*parent_intersection/parent_area,6) if parent_area else None,
    'candidate_adm2_source_component_count':len(parts),'admin1_parent_present':bool(parent_feature),
    'interpretation':'Area ratio and containment screen for province-sized/repeated-tier candidates; no tier or membership correction is selected.'})
   exact_wf=wca_by_code[(code,pcode)]
   label_wf=wca_by_name_parent[(code,norm(p.get('adm2_name')),norm(p.get('adm1_name')))]
   wf=exact_wf if exact_wf else label_wf
   wca_method='exact publisher ADM2 code' if exact_wf else ('normalized ADM2+ADM1 labels; code-vintage mismatch candidate' if label_wf else 'no exact-code or normalized-name+parent records')
   sf=sen_by_code.get(pcode,[]) if code=='SEN' else []
   cap=caps_by[(code,pcode)];
   wca_inside=sum(geom.covers(shape(q['geometry'])) for q in wf)
   wca_out=len(wf)-wca_inside
   national_inside=sum(geom.covers(shape(q['geometry'])) for q in sf)
   cand={'current_name':p.get('adm2_name'),'current_pcode':pcode,'current_parent':p.get('adm1_name'),
      'parent_pcode':p.get('adm1_pcode'),'valid_on':p.get('valid_on'),'area_km2':p.get('area_sqkm'),
      'component_count':len(parts),'WCA_point_count_by_code':len(exact_wf),'WCA_point_count_name_parent_candidate':len(wf),
      'WCA_crosswalk_method':wca_method,'WCA_points_inside_current_geometry':wca_inside,
      'WCA_same_code_points_outside_geometry':wca_out,'Senegal_2017_OCHA_points_by_code':len(sf),
      'Senegal_2017_points_inside_current_geometry':national_inside,'admin_capital_records':len(cap)}
   candidate_details.append(cand)
   point_counts.append({'pcode':pcode,'count':len(exact_wf),'candidate_count':len(wf),'method':wca_method,'inside':wca_inside,'outside':wca_out,'senegal2017':len(sf)})
   admincap_details.extend([{'name':x['properties'].get('name'),'coordinates':x['geometry'].get('coordinates'),'adm_p_lvl':x['properties'].get('adm_p_lvl')} for x in cap])
   # Enumerate every component of every current candidate, attached to all observed WCA names on each component.
   for ix,part in enumerate(parts):
    names=[]
    for q in wf:
     if part.covers(shape(q['geometry'])):names.append(str(q['properties'].get('featureNam') or '(unnamed)'))
    component_rows.append({'location_id':mid,'location_name':member['name'],'country':country,'candidate_current_name':p.get('adm2_name'),
      'candidate_current_pcode':pcode,'source_component_index':ix,'source_component_count':len(parts),
      'component_area_km2':round(area(part),6),'bbox_lonlat':json.dumps(list(part.bounds)),
      'WCA_points_inside_component_by_name_parent_candidate':len(names),'WCA_point_names':json.dumps(names,ensure_ascii=False),
      'interpretation':'Source polygon component; not independently named as an island or proof of complete physical land coverage.'})
   # Test points joined by exact code or name+parent candidate against source polygons; do not call label joins exact-code evidence.
   for q in wf:
    pg=shape(q['geometry'])
    if geom.covers(pg):continue
    contain=[]
    for j in current_trees[code].query(projected(pg)):
     target=current_tree_rows[code][int(j)];tg=shape(target['geometry'])
     if tg.covers(pg):contain.append(f"{target['properties'].get('adm2_name')}[{target['properties'].get('adm2_pcode')}]")
    anomalies.append({'assigned_location_id':mid,'assigned_location_name':member['name'],'candidate_current_pcode':pcode,
      'point_object_id':q['properties'].get('OBJECTID'),'point_name':q['properties'].get('featureNam'),
      'point_lon_lat':json.dumps(list(pg.coords[0])),'catalog_admin2_name':q['properties'].get('admin2Name'),
      'catalog_admin2_pcode':q['properties'].get('admin2Pcod'),'containing_current_codab_candidates':';'.join(sorted(set(contain))) or 'outside all current COD-AB polygons',
      'source_last_modified':q['properties'].get('last_modif'),'finding':('Exact-code' if q in exact_wf else 'Name+parent crosswalk candidate')+' point outside candidate current polygon; no transfer inferred.'})
  # Individual settlement table includes zeroes and multiple-current-candidate ambiguity explicitly.
  for pc in point_counts:
   settlement_rows.append({'location_id':mid,'location_name':member['name'],'country':country,'legacy_shape_id':shape_id,
    'candidate_current_pcode':pc['pcode'],'WCA_exact_code_point_rows':pc['count'],'WCA_name_parent_candidate_point_rows':pc['candidate_count'],
    'WCA_crosswalk_method':pc['method'],'WCA_points_inside_candidate_polygon':pc['inside'],
    'WCA_candidate_points_outside_candidate_polygon':pc['outside'],'Senegal_2017_point_rows_by_code':pc['senegal2017'],
    'current_candidate_count':len(candidates),'candidate_method':choice_method,
    'limit':'Settlement points/administrative capitals are not settlement completeness evidence; code/date mismatches remain separate.'})
  city_group={k:v for k,v in city_matches.items() if k[0]==code}
  for (cc,city,pc,name),named_counts in sorted(city_group.items()):
   n=sum(named_counts.values())
   if pc in candidate_codes or (city=='Lagos' and code=='NGA') or (city=='Dakar' and code=='SEN') or (city=='Freetown' and code=='SLE'):
    city_rows.append({'assigned_location_id':mid,'screen_city':city,'point_name_match_admin2_code':pc,
      'point_name_match_admin2_name':name,'matching_WCA_point_rows':n,
      'interpretation':'Name-presence and current administrative code screen only; no urban/metropolitan footprint inferred.'})
  mismatch_reasons=[]
  if len(old_by[code])==0:mismatch_reasons.append('legacy source inventory absent')
  if not candidate_codes:mismatch_reasons.append('no current same-name/positive-overlap candidate')
  if len(candidate_codes)>1:mismatch_reasons.append('multiple current same-name candidates')
  if parent_status=='correction-needed':mismatch_reasons.append('current COD-AB parent label differs from atlas parent label')
  if not point_counts or sum(x['candidate_count'] for x in point_counts)==0:mismatch_reasons.append('no exact-code or name+parent WCA point rows for any candidate current unit')
  if not mismatch_reasons:mismatch_reasons.append('physical land/island completeness and current settlement completeness remain unverified')
  status='correction-needed' if parent_status=='correction-needed' else 'insufficient-evidence'
  status_counts[status]+=1
  assessment.append({'id':mid,'name':member['name'],'country':country,'source_id':member['source_id'],'source_year':member['source_year'],
   'legacy_shape_id':shape_id,'legacy_source_name':old_name,'legacy_source_role':CODES[code][3],
   'legacy_source_feature_present':True,'legacy_source_feature_count_country':len(sources[code]['old']),
   'baseline_area_id':member['parent_id'].split(':')[1] if False else member['parent_id'],
   'baseline_parent_id':member['parent_id'],'complete_baseline_parent_chain':member['parent_chain'],
   'parent_chain_length':len(member['parent_chain']),'country_current_admin1_candidate_parents':parents,
   'parent_assignment_assessment':parent_status,'baseline_parent_label':atlas_parent,'current_parent_label':';'.join(parents),'current_parent_candidates':parents,
   'current_candidate_codes':candidate_codes,'current_candidate_mapping_method':choice_method,
   'current_candidate_details':candidate_details,'legacy_current_positive_intersection_pairs':len(positive),
   'legacy_current_top_overlap_screen':{'current_name':top[1]['properties'].get('adm2_name'),'current_pcode':top[1]['properties'].get('adm2_pcode'),
    'intersection_km2':round(top[0]/1e6,6),'legacy_coverage_pct':round(100*top[0]/old_m.area,5) if old_m.area else None,
    'screen_only':True} if top else None,
   'wca_assigned_code_point_rows':sum(x['count'] for x in point_counts),
   'wca_name_parent_candidate_point_rows':sum(x['candidate_count'] for x in point_counts),
   'wca_candidate_points_outside_geometry_rows':sum(x['outside'] for x in point_counts),
   'senegal_2017_points_by_candidate_codes':sum(x['senegal2017'] for x in point_counts),
   'current_official_admin_capital_records':admincap_details,
   'assessment_status':status,'assessment_reasons':mismatch_reasons,
   'semantic_role_assessment':f"Pinned source role {CODES[code][3]!r} is independently represented as COD-AB ADM2 for these features; source role and administrative level alone do not certify tier purpose or physical extent.",
   'decision_limit':'Source name/code, administration and settlement screens remain separate. No political title, full settlement population, complete land/island footprint, or region approval is inferred.'})

 write_csv('assessment.csv',assessment);write_csv('source-vintage-crosswalk.csv',crosswalk_rows)
 write_csv('geometry-components.csv',component_rows);write_csv('settlement-point-anomalies.csv',anomalies)
 write_csv('settlement-source-counts.csv',settlement_rows);write_csv('city-name-spatial-screen.csv',city_rows)
 write_csv('province-scale-screen.csv',parent_scale_rows)

 # Every province and area is represented; partial country scopes include explicit external-owned remainder counts.
 groups=[]
 for level,source_key in [('area','area_scopes'),('province','province_scopes')]:
  for group in scope[source_key]:
   gid=group['id'];owned=[m for m in members if m['parent_id']==gid] if level=='province' else [m for m in members if m['owner']==group['name']]
   states=Counter(r['current_parent_label'] for r in assessment if r['id'] in {m['id'] for m in owned})
   if level=='area':
    full=group['full_area_location_count'];owned_n=group['owned_member_location_count']
   else:full=group['full_province_locations'];owned_n=len(owned)
   groups.append({'scope_level':level,'scope_id':gid,'name':group['name'],'country':group.get('country',group['name']),
    'baseline_full_location_count':full,'owned_location_count':owned_n,'partial_scope':group.get('partial',False),
    'owned_subject_ids':json.dumps([m['id'] for m in owned]),'current_parent_assignments':json.dumps(states,ensure_ascii=False),
    'source_role_and_parent_assessment':'See each subject row; source parent/vintage candidates are not a shared hierarchy edit.',
    'assessment':'scope inventory cross-reference; no source-count quota or regional approval.'})
 write_csv('administrative-scope.csv',groups)

 # Each current national ADM1 unit is compared by source code to the same-vintage edge-matched layer.
 wca1=json.loads(unz('wca-adm1-region-neighbors.geojson.gz'))['features'];wca1by=defaultdict(list)
 for f in wca1:wca1by[(norm(f['properties'].get('adm0_name')),str(f['properties'].get('adm1_pcode') or ''))].append(f)
 adm1_rows=[]
 for code,(country,_,_,_) in CODES.items():
  for f in sources[code]['admin1']:
   p=f['properties']; candidates=wca1by[(norm(country),str(p.get('adm1_pcode') or ''))]
   for wf in candidates:
    a=projected(shape(f['geometry']));b=projected(shape(wf['geometry']));union=a.union(b).area
    adm1_rows.append({'country':country,'pcode':p.get('adm1_pcode'),'COD_AB_name':p.get('adm1_name'),'COD_AB_valid_on':p.get('valid_on'),
      'WCA_edge_matched_name':wf['properties'].get('adm1_name'),'WCA_edge_matched_pcode':wf['properties'].get('adm1_pcode'),
      'IoU_source_screen':round(a.intersection(b).area/union,7) if union else None,
      'symmetric_difference_km2':round(a.symmetric_difference(b).area/1e6,6),
      'limit':'Code-linked current COD-AB versus WCA 2026 edge-matched source screen; not boundary approval.'})
 write_csv('admin1-source-comparison.csv',adm1_rows)

 # Common-source neighboring edges for all assigned countries; outer edges remain untouched.
 wca0=json.loads(unz('wca-adm0-region-neighbors.geojson.gz'))['features'];wca0by={norm(f['properties'].get('adm0_name')):f for f in wca0}
 country_pairs=[]
 for code,neighs in {'NGA':['Benin','Niger','Chad','Cameroon'],'SEN':['Mauritania','Mali','Guinea','Guinea-Bissau','The Gambia'],'SLE':['Guinea','Liberia']}.items():
  country=CODES[code][0];a=wca0by[norm(country)];ga=shape(a['geometry'])
  for n in neighs:
   if norm(n) not in wca0by:country_pairs.append({'country':country,'neighbor':n,'finding':'neighbor feature absent from extracted OCHA source'});continue
   b=wca0by[norm(n)];gb=shape(b['geometry']);shared=ga.boundary.intersection(gb.boundary);overlap=area(ga.intersection(gb))
   country_pairs.append({'country':country,'neighbor':b['properties'].get('adm0_name'),'shared_boundary_km':round(geodesic_km(shared),3),
    'areal_overlap_km2':round(overlap,6),'source':'OCHA WCA 2026 edge-matched ADM0',
    'finding':'Same-source shared edge/no positive areal overlap screen; not sovereignty, physical land completeness or approval.'})
 write_csv('neighbor-edge-screen.csv',country_pairs)

 # Full national source inventory counts and changes; no omission/role quota inferred from current totals.
 national=[]
 for code,(country,_,year,role) in CODES.items():
  old=sources[code]['old'];cur=sources[code]['admin2'];parents=sources[code]['admin1']
  old_names={norm(f['properties'].get('shapeName')) for f in old};cur_names={norm(f['properties'].get('adm2_name')) for f in cur}
  unmatched=[f['properties'].get('adm2_name') for f in cur if norm(f['properties'].get('adm2_name')) not in old_names and norm(f['properties'].get('adm2_name')) not in {norm(x) for x in ALIASES[code].values()}]
  national.append({'country_code':code,'country':country,'pinned_source_role':role,'pinned_source_vintage':year,
   'pinned_geoBoundaries_features':len(old),'current_OCHA_COD_AB_ADM2_features':len(cur),'current_OCHA_COD_AB_ADM1_features':len(parents),
   'assigned_scope_members':sum(m['source_id']==f'gb:{code}:ADM2' for m in members),
   'current_units_without_normalized_legacy_name':json.dumps(sorted(unmatched),ensure_ascii=False),
   'current_missing_adm2_name_count':sum(not f['properties'].get('adm2_name') for f in cur),
   'current_missing_adm2_pcode_count':sum(not f['properties'].get('adm2_pcode') for f in cur),
   'current_duplicate_normalized_names':json.dumps({k:len(v) for k,v in current_by[code].items() if k and len(v)>1}),
   'settlement_WCA_point_rows_country':wca_by_country[code],
   'limit':'National counts are source-vintage inventories; they are not EU5 quotas, proof of completeness or atlas membership instructions.'})
 write_csv('national-source-inventory.csv',national)

 # Settlement source axis and coverage are explicitly data vintage screens.
 ver={'status':'built','issue':478,'subjects_assessed':len(assessment),'area_and_province_scopes_assessed':len(groups),
  'countries':{c:{'assigned_members':sum(m['source_id']==f'gb:{c}:ADM2' for m in members),'legacy_features':len(sources[c]['old']),
    'current_COD_AB_ADM2_features':len(sources[c]['admin2']),'current_COD_AB_ADM1_features':len(sources[c]['admin1']),
    'WCA_settlement_points_in_country_subset':wca_by_country[c]} for c in CODES},
  'status_counts':dict(status_counts),'parent_assignment_counts':dict(parent_counts),'candidate_overlap_pairs':subject_intersection_count,
  'positive_source_vintage_overlap_rows':len(crosswalk_rows),'geometry_candidate_components':len(component_rows),
  'settlement_candidate_outlier_rows':len(anomalies),'WCA_geometry_x_matches_LAT_y_matches_LONG':axis_rows,
  'neighbor_edges_screened':len(country_pairs),'admin1_cross_source_comparisons':len(adm1_rows),
  'province_scale_candidate_rows':len(parent_scale_rows),
  'limitations':'Build counts do not approve membership or boundaries. Candidate overlaps, administrative capitals and settlement points are evidence screens; no source completeness, political ownership, physical coastline/island completeness, region approval, or import authorization follows.'}
 output_names=['assessment.csv','source-vintage-crosswalk.csv','geometry-components.csv','settlement-point-anomalies.csv',
  'settlement-source-counts.csv','city-name-spatial-screen.csv','current-unit-inventory.csv','administrative-scope.csv',
  'admin1-source-comparison.csv','neighbor-edge-screen.csv','province-scale-screen.csv','national-source-inventory.csv']
 ledger={'version':1,'issue':478,'generator':'build_assessment.py','baseline_commit':scope['published_region_baseline']['baseline_git_commit'],
  'generated_table_rows_excluding_headers':sum(len(rows) for rows in [assessment,crosswalk_rows,component_rows,anomalies,settlement_rows,city_rows,unit_rows,groups,adm1_rows,country_pairs,parent_scale_rows,national]),
  'outputs':[],'source_archives_accounted_separately':'sources/acquisition.json, context-extract.json, senegal-settlement-extract.json, sources/inherited-wca-register.json'}
 for name in output_names:
  data=(ROOT/name).read_bytes()
  with (ROOT/name).open(encoding='utf-8',newline='') as f:row_count=sum(1 for _ in csv.reader(f))-1
  ledger['outputs'].append({'path':name,'rows_excluding_header':row_count,'bytes':len(data),'sha256':sha(data)})
 (ROOT/'generated-data-accounting.json').write_text(json.dumps(ledger,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(ver,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
