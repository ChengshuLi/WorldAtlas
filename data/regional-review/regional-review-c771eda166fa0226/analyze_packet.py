#!/usr/bin/env python3
"""Reproduce per-member findings and the Gambia city aggregation comparison for issue #471."""
import gzip, hashlib, json, math, sys
from pathlib import Path
from collections import Counter, defaultdict
from shapely.geometry import shape
from shapely.ops import transform, unary_union
from pyproj import Transformer

OWN=Path(__file__).resolve().parent
read=lambda p: json.loads(Path(p).read_text(encoding='utf-8'))
write=lambda p,x: Path(p).write_text(json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
sc=read(OWN/'issue-scope-pinned.json')
rows=read(OWN/'source-crosswalk.json')['members']
crosswalk_summary=read(OWN/'source-crosswalk.json')['summary']
if len(rows)!=sc['location_count'] or {r['id'] for r in rows}!=set(sc['member_location_ids']): raise SystemExit('crosswalk does not exactly cover issue scope')
features=json.loads(gzip.open(OWN/'baseline-members.geojson.gz','rt',encoding='utf-8').read())['features']
byid={f['properties']['id']:f for f in features}
if set(byid)!=set(sc['member_location_ids']): raise SystemExit('baseline member scope mismatch')
source_specs={'GMB':('gambia-gbopen-2020-adm2','gambia-gbopen-2020-adm1'),'GHA':('ghana-gbopen-2019-adm2','ghana-gbopen-2019-adm1'),'CIV':('civ-gbopen-2021-adm3','civ-gbopen-2021-adm2')}
sources={}
registered={s['id']:s for s in read(OWN/'sources/register.json')['sources']}
for iso,(child,parent) in source_specs.items():
 sources[iso]={'child':json.loads(gzip.open(OWN/'sources'/f'{child}.geojson.gz','rt',encoding='utf-8').read())['features'],'parent':json.loads(gzip.open(OWN/'sources'/f'{parent}.geojson.gz','rt',encoding='utf-8').read())['features']}
tr=Transformer.from_crs('EPSG:4326','EPSG:6933',always_xy=True).transform
proj=lambda g: transform(tr,g)
city=byid['atlas:city:GMB-2153']; meta=city['properties']['metadata']; gmbchild={f['properties']['shapeID']:f for f in sources['GMB']['child']}
city_source_ids=meta['source_member_ids']; shapes=[shape(gmbchild[x.rsplit(':',1)[-1]]['geometry']) for x in city_source_ids]
citygeom=proj(shape(city['geometry'])); group=proj(unary_union(shapes))
def cmp(g):
 i=citygeom.intersection(g).area
 return {'atlas_area_fraction':i/citygeom.area,'reference_area_fraction':i/g.area,'iou':i/(citygeom.union(g).area),'atlas_area_km2':citygeom.area/1e6,'reference_area_km2':g.area/1e6}
city_comparison={'method':'EPSG:6933 equal-area polygon intersection; exact nine source_member_ids converted from their gb:GMB:ADM2:<shapeID> identifiers; original geometries unchanged','nine_declared_source_members':len(shapes),'atlas_vs_nine_source_member_union':cmp(group),'per_source_member':[],'lga_intersections':[],'notes':['This tests only whether the atlas aggregation footprint follows its declared nine district members. It does not establish an official city or metropolitan boundary.','The 2020 geoBoundaries source is licensed CC BY 4.0; official district-level Gambia geometry was not independently located.']}
city_comparison['natural_earth_record']=crosswalk_summary['natural_earth_gambia_city']
standalone_gambia={r['source_shape_id'] for r in rows if r['source_id']=='gb:GMB:ADM2'}
declared_city={x.rsplit(':',1)[-1] for x in city_source_ids}
all_gambia={x['properties']['shapeID'] for x in sources['GMB']['child']}
city_comparison['source_layer_partition']={'source_feature_count':len(all_gambia),'standalone_scoped_source_count':len(standalone_gambia),'aggregate_member_source_count':len(declared_city),'union_member_count':len(standalone_gambia|declared_city),'duplicate_source_ids':sorted(standalone_gambia&declared_city),'unrepresented_source_ids':sorted(all_gambia-(standalone_gambia|declared_city)),'extra_atlas_source_ids':sorted((standalone_gambia|declared_city)-all_gambia),'complete_partition':len(all_gambia)==48 and standalone_gambia|declared_city==all_gambia and not (standalone_gambia&declared_city)}
for ident,geom in zip(city_source_ids,shapes):
 p=gmbchild[ident.rsplit(':',1)[-1]]['properties']
 city_comparison['per_source_member'].append({'source_id':ident,'name':p['shapeName'],'shape_id':p['shapeID']})
parents=sources['GMB']['parent']
for f in parents:
 name=f['properties']['shapeName']; pm=proj(shape(f['geometry'])); i=citygeom.intersection(pm).area
 if i/citygeom.area>1e-6:
  city_comparison['lga_intersections'].append({'name':name,'source_id':f['properties']['shapeID'],'atlas_area_fraction':i/citygeom.area,'lga_area_fraction':i/pm.area,'iou':i/(citygeom.union(pm).area)})
city_comparison['lga_intersections'].sort(key=lambda r:r['atlas_area_fraction'],reverse=True)

assess=[]
for r in rows:
 ident=r['id']; iso='GMB' if ident.startswith('gb:GMB:') or ident.startswith('atlas:city:GMB') else 'GHA' if ident.startswith('gb:GHA:') else 'CIV'
 source_entity={'GMB':'gambia-gbopen-2020-adm2','GHA':'ghana-gbopen-2019-adm2','CIV':'civ-gbopen-2021-adm3'}[iso]
 src=registered[source_entity]
 result={'id':ident,'name':r['name'],'area_id':r['area_id'],'province_id':r['province_id'],'province_name':r['province_name'],'source_id':r['source_id'],'source_shape_id':r.get('source_shape_id'),'source_shape_name':r.get('source_shape_name'),'source_vintage':src['metadata_fields']['boundaryYear'],'source_role':src['boundary_role'],'source_license':src['license'],'source_metadata_path':src['metadata_snapshot']['path'],'source_metadata_sha256':src['metadata_snapshot']['sha256'],'source_payload_sha256':src['original_sha256'],'status':None,'evidence':[],'limits':[],'recommendation':None}
 if iso=='GMB' and ident=='atlas:city:GMB-2153':
  ne=city_comparison['natural_earth_record']
  result.update({'status':'correction-needed','evidence':['Pinned Natural Earth 10m source record GMB-2153 is named Banjul and classified “Independent City”; its exact source attributes and retained source bytes are in source-crosswalk.json and the source register.','Natural Earth reference footprint vs Atlas city equal-area IoU is %.4f; vs the union of nine declared geoBoundaries districts it is %.4f.'%(ne['natural_earth_vs_atlas_city']['iou'],ne['natural_earth_vs_nine_geoBoundaries_member_union']['iou']),'All nine declared geoBoundaries 2020 district source members reconstruct a close footprint match: equal-area IoU %.6f, atlas share %.4f, source-union share %.4f.'%(city_comparison['atlas_vs_nine_source_member_union']['iou'],city_comparison['atlas_vs_nine_source_member_union']['atlas_area_fraction'],city_comparison['atlas_vs_nine_source_member_union']['reference_area_fraction']),'The same footprint overlaps three geoBoundaries 2020 Local Government Areas: '+', '.join(f"{x['name']} ({x['atlas_area_fraction']:.1%} of atlas area)" for x in city_comparison['lga_intersections'])+'. The atlas semantic parent is only Banjul; the declared membership/geometry spans Brikama and Kanifing too.'], 'limits':['Natural Earth is an undated modern generalized reference, not an authoritative statutory delimitation.','No official current urban/metropolitan boundary or legal text establishing the appropriate parent/role was found; the internal semantic decision remains open.'], 'recommendation':'Confirm whether this is an urban agglomeration or a statutory independent city. If an urban aggregate, replace the coextensive single-LGA parent assertion with an explicit cross-LGA relationship; if statutory, obtain the delimiting instrument and licensed official footprint. Engineering should preserve the aggregate until a hierarchy design decision.'})
 elif iso=='GMB':
  iou=r.get('atlas_source_iou') or 0
  if iou>=.95:
   result.update({'status':'justified','evidence':['Exact geoBoundaries 2020 ADM2 shapeID match; exact source name and source-parent-name match.','Equal-area IoU between Atlas geometry and the exact 2020 source district is %.4f.'%iou,'geoBoundaries metadata calls ADM2 “District” (48 units), with CC BY 4.0; the linked World Bank source identifies the Gambian administrative-boundary dataset.','GBoS official sources describe eight Local Government Areas and the 2024 census as using eight LGAs; the retained source parent layer also has eight LGAs.'],'limits':['The 2020 district boundary vintage is not independently validated against a current official district geometry.','This status supports the source-represented unit, not current legal boundaries or whole-area completeness.'],'recommendation':None})
  else:
   result.update({'status':'insufficient-evidence','evidence':['Exact geoBoundaries 2020 ADM2 shapeID, source name and source-parent-name match.','Equal-area IoU between Atlas geometry and the exact 2020 source district is %.4f, below the documented 0.95 source-alignment screen.'%iou,'geoBoundaries metadata calls ADM2 “District” (48 units), with CC BY 4.0; GBoS sources support the eight-LGA framework but no current official district polygon layer was found.'],'limits':['This overlap cannot distinguish a changed official boundary, data vintage/digitization, or Atlas representation error.'],'recommendation':'Obtain an official current district boundary or authoritative district-to-2020-source crosswalk for this exact ID before proposing a footprint edit.'})
 elif iso=='GHA':
  good=(r.get('gss2021_name_match_count')==1 and (r.get('gss2021_named_match_iou') or 0)>=.95 and (r.get('atlas_source_iou') or 0)>=.95 and (r.get('source_parent_area_coverage') or 0)>=.95 and r.get('atlas_parent_name_norm_matches_source_candidate') is True)
  if good:
   result.update({'status':'justified','evidence':['Exact geoBoundaries 2019 ADM2 shapeID, exact name and named parent match.','2019 source metadata identifies 260 Districts, sourced to USAID Ghana HPNO/Ghana Statistical Service, CC BY 4.0.','Official GSS 2021 District Assemblies crosswalk yielded one normalized name+region candidate (%s); equal-area IoU of that named 2021 district to the 2019 source is %.4f; atlas-to-2019-source IoU is %.4f; and source-child coverage in the named geoBoundaries 2021 region parent is %.4f.'%(r['gss2021_named_match_name'],r['gss2021_named_match_iou'],r['atlas_source_iou'],r['source_parent_area_coverage']),'Official GSS 2021 reports 261 District Assemblies; the named boundary, Atlas geometry and parent screens all meet the documented high-overlap threshold.'],'limits':['GSS redistribution terms for its boundary download were not located; only its exact checksums and derived comparison were retained.','This validates strong agreement across the inspected vintages, not statutory delineation or uninspected location attributes.'],'recommendation':None})
  else:
   result.update({'status':'insufficient-evidence','evidence':['Exact geoBoundaries 2019 ADM2 shapeID, exact name and named geoBoundaries parent match.','2019 source metadata identifies 260 Districts, sourced to USAID Ghana HPNO/Ghana Statistical Service, CC BY 4.0.','Official GSS 2021 file has 261 District Assemblies. Nearest spatial candidate: %s / %s, IoU %.4f; unique normalized name+region candidates: %s; named-candidate IoU: %s; atlas-to-2019-source IoU %.4f; source-child coverage in the named source parent %.4f.'%(r.get('gss2021_spatial_match_name'),r.get('gss2021_spatial_match_region'),r.get('gss2021_iou') or 0,r.get('gss2021_name_match_count'),('%.4f'%r['gss2021_named_match_iou'] if r.get('gss2021_named_match_iou') is not None else 'unavailable'),r.get('atlas_source_iou') or 0,r.get('source_parent_area_coverage') or 0)],'limits':['Observed 2019-to-2021 count/name/geometry difference cannot distinguish legal boundary changes, statistical redistricting, source digitization or classification without the exact GSS feature lineage and redistribution terms.','Area overlap is diagnostic; it cannot determine official status.'],'recommendation':'Restore the GSS Districts_261 source with its license/terms, source metadata and district-to-district name/code crosswalk; investigate this row against official 2021 geometry before proposing a footprint edit.'})
 elif iso=='CIV':
  bad_utf=(r.get('source_name_exact') is False)
  result.update({'status':'insufficient-evidence','evidence':['Exact geoBoundaries 2021 ADM3 shapeID, named-parent match, and source child lies within its geoBoundaries ADM2 2016 parent (overlap %.6f).'%r['source_parent_area_coverage'],'The retained source metadata labels this layer ADM3 “Departments”, count 510, source CNTIG/OCHA ROWCA, CC BY 3.0 IGO; atlas scoped row name %r, original source attribute %r.'%(r['name'],r['source_shape_name']), 'The 63 scoped units are in Bounkani (17), Gontougo (29), and Sud-Comoe (17); all source-parent relationships match, but the layer-level role/count is unresolved.']+(['Source attribute has a reversible mojibake form relative to atlas label; exact source ID and geometry anchor the join, but original raw attribute is preserved.' ] if bad_utf else []),'limits':['Official Côte d’Ivoire DGAT currently states 31 regions, 108 departments, and 509 sub-prefectures. geoBoundaries metadata instead says 33 ADM2 “regions” and 510 ADM3 “Departments”.','ANStat API docs describe 526 sub-prefecture records for reference year 2021; its public API host could not be reached from this research environment, so no exact 63-row official crosswalk was established.','The current formal administrative instrument and distinction among departments, sub-prefectures, autonomous districts, and source layer units remain unresolved.'],'recommendation':'Restore the official decree/code table and ANStat 2021 sub-prefecture crosswalk with redistribution terms; reconcile source IDs/names and parent vintage before retaining ADM3 as a semantic tier or editing any locations.'})
 assess.append(result)

city_result=next(x for x in assess if x['id']=='atlas:city:GMB-2153')
lineage_path=OWN/'baseline-source-lineage.json'
city_result.update({'source_vintage':'undated modern reference','source_role':'Atlas source aggregation; metadata says “Source city territory: Independent City”','source_license':'Natural Earth source license retained in semantic-report.json; pinned upstream Natural Earth commit ca96624a56bd078437bca8184e78163e5039ad19; the nine declared member layers are CC BY 4.0 geoBoundaries source units','source_metadata_path':'baseline-members.geojson.gz plus baseline-source-lineage.json','source_metadata_sha256':hashlib.sha256(lineage_path.read_bytes()).hexdigest(),'source_payload_sha256':None,'source_shape_id':None,'source_shape_name':'Atlas source aggregation','source_member_ids':city_source_ids})

cross_byid={r['id']:r for r in rows}
scope_members={p['id']:[] for p in sc['province_scopes']}
for a in assess:
 scope_members[a['province_id']].append(a)
provinces=[]
for ps in sc['province_scopes']:
 rr=scope_members[ps['id']]
 statuses=Counter(x['status'] for x in rr)
 status='correction-needed' if statuses['correction-needed'] else 'insufficient-evidence' if statuses['insufficient-evidence'] else 'justified'
 notes=[]
 if ps['name']=='Banjul': notes=['Its only scoped subject is the Banjul atlas city aggregation, which reconstructs from nine ADM2 districts spanning Banjul, Kanifing and Brikama LGAs; the current coextensive Banjul parent description needs a hierarchy decision.']
 elif ps['name'] in ('Bounkani','Gontougo','Sud-Comoe'): notes=['All scoped subjects have exact source IDs and 2016 source parent overlay/name agreement; provincial administrative semantics remain contingent on reconciling Côte d’Ivoire administrative-level counts.']
 else: notes=['Scoped locations have exact source IDs/named parent matches; this is a subset-specific assessment and does not approve wider region boundaries. Ghana current-vintage comparisons are unresolved for rows whose row-level status is insufficient.']
 crossrows=[cross_byid[x['id']] for x in rr if x['id'] in cross_byid]
 cover=[x['source_parent_area_coverage'] for x in crossrows if x.get('source_parent_area_coverage') is not None]
 iso='GMB' if ps['name'] in ('Banjul','Brikama','Kerewan','Mansakonko','Kuntaur','Janjanbureh','Basse') else 'GHA' if ps['name'].endswith('Region') else 'CIV'
 child_stem=source_specs[iso][0]; source_meta=registered[child_stem]
 provinces.append({'id':ps['id'],'name':ps['name'],'scoped_location_count':len(rr),'pinned_full_province_location_count':ps['full_province_locations'],'partial':ps['partial'],'status':status,'status_counts':dict(statuses),'subject_ids':[x['id'] for x in rr],'source_layer':{'id':child_stem,'vintage':source_meta['metadata_fields']['boundaryYear'],'role':source_meta['boundary_role'],'license':source_meta['license'],'source_payload_sha256':source_meta['original_sha256']},'named_source_parent_candidates':sorted({x.get('source_parent_name_candidate') for x in crossrows if x.get('source_parent_name_candidate')}),'source_parent_ids':sorted({x.get('source_parent_id_candidate') for x in crossrows if x.get('source_parent_id_candidate')}),'source_child_coverage_in_named_parent':{'minimum':min(cover) if cover else None,'median':sorted(cover)[len(cover)//2] if cover else None,'maximum':max(cover) if cover else None,'members_below_0_95':[x['id'] for x in crossrows if (x.get('source_parent_area_coverage') or 0)<.95]},'findings':notes})
areas=[]
for ar in sc['area_scopes']:
 rr=[x for x in assess if x['area_id']==ar['id']]; statuses=Counter(x['status'] for x in rr)
 status='correction-needed' if statuses['correction-needed'] else 'insufficient-evidence' if statuses['insufficient-evidence'] else 'justified'
 purpose={'Gambia':'The issue owns every current Atlas ID in this area; the geoBoundaries district source is represented by 39 separate Atlas source IDs plus the nine-member Banjul city aggregation. The source-layer membership partition is complete, but legal currentness and coastline/island completeness are not established.','Ghana':'Partial area cohort: exactly 113 of 260 pinned Atlas location IDs. Eight province scopes are included; 84 subjects remain insufficient against the retrieved 2021 GSS comparator. Other district units are outside this issue.','Côte d’Ivoire':'Partial area cohort: exactly 63 of 510 pinned Atlas location IDs across Bounkani, Gontougo and Sud-Comoe. The source-layer role is unresolved and remaining units are outside this issue.'}[ar['name']]
 areas.append({'id':ar['id'],'name':ar['name'],'scoped_location_count':len(rr),'pinned_full_area_location_count':ar['full_area_location_count'],'partial':ar['partial'],'status':status,'status_counts':dict(statuses),'subject_ids':[x['id'] for x in rr],'purpose':purpose,'findings':['This area result is limited to the exact issue-owned IDs; a partial area is not certified by its packet.']})

sources_index=[]
for iso,(child,parent) in source_specs.items():
 for role,stem in [('child',child),('parent',parent)]:
  for ext in ['geojson.gz']:
   p=OWN/'sources'/f'{stem}.{ext}'; raw=gzip.open(p,'rb').read()
   sources_index.append({'id':stem,'iso':iso,'role':role,'path':p.relative_to(OWN).as_posix(),'retained_bytes':p.stat().st_size,'retained_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'original_bytes':len(raw),'original_sha256':hashlib.sha256(raw).hexdigest()})

out={'schema_version':1,'issue':471,'scope_batch_id':sc['batch_id'],'baseline_commit':read(OWN/'baseline-receipt.json')['baseline_commit'],'source_crosswalk':'source-crosswalk.json','subject_count':len(assess),'status_counts':dict(Counter(x['status'] for x in assess)),'subjects':assess,'provinces':provinces,'areas':areas,'gambia_banjul_aggregation':city_comparison,'reproduction_sources':sources_index,'decision_method':['Exact source IDs and explicit source-role/vintage/license metadata establish source identity, not current legal correctness.','Ghana justified rows require exact source and parent name match, source-child share >=0.95 in its geoBoundaries 2021 region, unique normalized GSS name+region candidate with that named candidate source-to-GSS IoU >=0.95, and atlas-to-2019-source IoU >=0.95. The limit remains no GSS redistribution permission located.','Côte d’Ivoire subjects remain insufficient because published official administrative counts/roles conflict with layer metadata and no official row-level crosswalk was verified.','Gambia district subjects are justified only when Atlas-to-exact 2020 geoBoundaries source IoU >=0.95 plus exact source identity/name/parent agree; lower-overlap cases remain insufficient pending current official district geometry. The derived Banjul atlas city receives correction-needed for its stated coextensive single-province parent because its nine-unit footprint overlaps three LGAs.','No row is called corrected from counts, structural checks, or overlap alone.']}
write(OWN/'assessment.json',out)

# Explicit completeness/scale/granularity flags. Thresholds here identify candidates only;
# they never declare a region-size error or geographic completeness.
cross_byid={r['id']:r for r in rows}; geom_screens={}; remainder_screens={}; parent_screens={}; scale_screens={}; name_terms=('other','remainder','remaining','unallocated','unknown','not allocated')
for iso,(child_stem,parent_stem) in source_specs.items():
 child_by={f['properties']['shapeID']:f for f in sources[iso]['child']}; parent_by={f['properties']['shapeID']:f for f in sources[iso]['parent']}
 members=[r for r in rows if r['id'].startswith('gb:'+iso+':')]
 member_shapeids={r['source_shape_id'] for r in members if r.get('source_shape_id')}
 if iso=='GMB': member_shapeids |= {x.rsplit(':',1)[-1] for x in city_source_ids}
 all_shapeids=set(child_by)
 atlas_multi=[]; maxparts=0; big=[]; ratios=[]; generic=[]
 for r in members:
  feat=byid[r['id']]; gg=shape(feat['geometry']); parts=len(gg.geoms) if gg.geom_type=='MultiPolygon' else 1; maxparts=max(maxparts,parts)
  if parts>1: atlas_multi.append({'id':r['id'],'name':r['name'],'geometry_type':gg.geom_type,'component_count':parts})
  source=child_by[r['source_shape_id']]; props=source['properties']; nm=props.get('shapeName') or ''
  if any(term in nm.casefold() for term in name_terms): generic.append({'id':r['id'],'source_shape_name':nm,'source_shape_id':r['source_shape_id']})
  parent_id=r.get('source_parent_id_candidate'); parent=parent_by.get(parent_id)
  if parent:
   ca=proj(shape(source['geometry'])).area; pa=proj(shape(parent['geometry'])).area
   ratio=ca/pa if pa else None
   if ratio is not None:
    ratios.append(ratio)
    if ratio>=.5: big.append({'id':r['id'],'name':r['name'],'source_parent_name':r.get('source_parent_name_candidate'),'child_to_parent_area_ratio':ratio,'screen':'candidate only; no policy threshold and no geographic error implied'})
 weak=[{'id':r['id'],'name':r['name'],'parent_name':r.get('source_parent_name_candidate'),'child_covered_by_parent_fraction':r.get('source_parent_area_coverage')} for r in members if (r.get('source_parent_area_coverage') or 0)<.95]
 geom_screens[iso]={'scoped_subject_count':len(members),'multipolygon_subjects':atlas_multi,'maximum_atlas_polygon_components':maxparts,'unassessed_island_and_coast_completeness':'not assessed by source ID or feature counts'}
 remainder_screens[iso]={'retained_source_layer_features':len(all_shapeids),'scope_represented_source_shapeids':len(member_shapeids),'source_shapeids_outside_this_issue_packet':len(all_shapeids-member_shapeids),'source_layer_remainder_ids':sorted(all_shapeids-member_shapeids),'note':'Outside the exact packet member roster; counts do not distinguish another issue packet from a true source gap.'}
 parent_screens[iso]={'named_parent_source_matches':sum(r.get('atlas_parent_name_norm_matches_source_candidate') is True for r in members),'parent_name_mismatches':[r['id'] for r in members if r.get('atlas_parent_name_norm_matches_source_candidate') is False],'source_child_coverage_below_0_95':weak,'atlas_geometry_to_source_iou_below_0_95':[{'id':r['id'],'name':r['name'],'iou':r.get('atlas_source_iou')} for r in members if r.get('atlas_source_iou') is not None and r['atlas_source_iou']<.95],'atlas_source_name_mismatches':[{'id':r['id'],'atlas_name':r['name'],'source_name':r.get('source_shape_name')} for r in members if r.get('source_name_exact') is False],'note':'A parent-name match, source-layer containment, exact label, or overlap measure alone does not establish current parent geography.'}
 ratios_sorted=sorted(ratios)
 scale_screens[iso]={'child_to_named_parent_area_ratio_min':min(ratios_sorted) if ratios_sorted else None,'child_to_named_parent_area_ratio_median':ratios_sorted[len(ratios_sorted)//2] if ratios_sorted else None,'child_to_named_parent_area_ratio_max':max(ratios_sorted) if ratios_sorted else None,'exploratory_over_half_parent_flags':big,'name_remainder_flags':generic,'note':'Large relative area and name flags are review screens only; unit role cannot be inferred from area.'}
coverage={'issue':471,'subject_count':len(rows),'exact_scope_only':True,'fragmented_city_or_aggregate':city_comparison,'source_remainders':remainder_screens,'geometry_components':geom_screens,'source_parent_screens':parent_screens,'province_scale_screen':scale_screens,'checks_not_established':['No national authoritative island/coastline inventory or high-water/low-water boundary reference was inspected.','No full-country current statutory boundary layer was retained for Gambia, Ghana or Côte d’Ivoire.','Adjacent country boundary geometry was not independently crosswalked in this packet.','Source feature counts and location chains do not establish completeness.','The existing scope partly covers Ghana and Côte d’Ivoire; outside-packet source IDs may belong to other issues.']}
write(OWN/'coverage-screen.json',coverage)
print(json.dumps({'subjects':len(assess),'status_counts':out['status_counts'],'provinces':len(provinces),'areas':len(areas),'city_union':city_comparison['atlas_vs_nine_source_member_union'],'city_lgas':city_comparison['lga_intersections'],'gambia_partition':city_comparison['source_layer_partition']},ensure_ascii=False,indent=2))
