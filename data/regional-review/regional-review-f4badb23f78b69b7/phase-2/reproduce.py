#!/usr/bin/env python3
"""Reproduce the phase-2 per-province and issue-risk screens from retained inputs."""
from __future__ import annotations
import collections, csv, hashlib, json, pathlib, re, unicodedata

ROOT = pathlib.Path(__file__).resolve().parent
PACKET = ROOT.parent

def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))

def digest(path):
    data = path.read_bytes()
    return len(data), hashlib.sha256(data).hexdigest()

def norm(value):
    value = unicodedata.normalize('NFKD', value or '').encode('ascii', 'ignore').decode().lower()
    return ''.join(ch for ch in value if ch.isalnum())

def write_csv(path, fields, rows):
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)

scope = read_json(PACKET / 'scope.json')
issue_411 = read_json(ROOT / 'source/issue-411-api-snapshot.json')
match_411 = re.search(r'```json\s*([\s\S]*?)\s*```', issue_411['body'])
assert match_411, 'companion issue #411 scope contract missing'
scope_411 = json.loads(match_411.group(1))
moz_411 = next(row for row in scope_411['area_scopes'] if row['name'] == 'Mozambique')
moz_412 = next(row for row in scope['area_scopes'] if row['name'] == 'Mozambique')
ids_411 = {item for item in scope_411['member_location_ids'] if item.startswith('gb:MOZ:')}
ids_412 = {item for item in scope['member_location_ids'] if item.startswith('gb:MOZ:')}
assert len(ids_411.intersection(ids_412)) == 0
assert len(ids_411) == moz_411['owned_member_location_count'] == 38
assert len(ids_412) == moz_412['owned_member_location_count'] == 121
assert len(ids_411.union(ids_412)) == moz_412['full_area_location_count'] == 159
inventory = read_json(ROOT / 'source-inventory.json')
for source in inventory['source_files']:
    source_path = PACKET / source['path']
    assert source_path.is_file(), f'missing retained source: {source["path"]}'
    source_bytes, source_sha = digest(source_path)
    assert source_bytes == source['bytes'] and source_sha == source['sha256'], f'source integrity mismatch: {source["path"]}'
assert all(not row['retained'] and row['sha256'] for row in inventory['external_references'])
with (PACKET / 'location-assessments.csv').open(encoding='utf-8', newline='') as stream:
    location_rows = list(csv.DictReader(stream))
assert len(location_rows) == scope['location_count'] == 223
assert len({row['location_id'] for row in location_rows}) == 223
assert set(row['location_id'] for row in location_rows) == set(scope['member_location_ids'])

zmb_path = PACKET / 'source/zambia-grid3-2022/zambia-administrative-boundaries-2022.geojson'
zmb = read_json(zmb_path)
zmb_features = zmb['features']
moz_path = PACKET / 'source/geoboundaries/MOZ/geoBoundaries-MOZ-ADM2.geojson'
moz = read_json(moz_path)
zmb_gb_path = PACKET / 'source/geoboundaries/ZMB/geoBoundaries-ZMB-ADM2.geojson'
zmb_gb = read_json(zmb_gb_path)
assert len(moz['features']) == 159 and len(zmb_gb['features']) == len(zmb_features) == 116

# The 2022 official layer covers 116 distinct district names; crosswalk all names,
# not only those selected in this issue, to the retained geoBoundaries source roster.
zmb_gb_by_name = collections.defaultdict(list)
for feature in zmb_gb['features']:
    zmb_gb_by_name[norm(feature['properties']['shapeName'])].append(feature)
assert all(len(rows) == 1 for rows in zmb_gb_by_name.values())
zmb_by_name = collections.defaultdict(list)
for feature in zmb_features:
    zmb_by_name[norm(feature['properties']['DISTRICT'])].append(feature)
assert all(len(rows) == 1 for rows in zmb_by_name.values())
assert set(zmb_gb_by_name) == set(zmb_by_name)
for key in zmb_by_name:
    assert zmb_by_name[key][0]['properties']['DISTRICT']

scope_rows_by_parent = collections.defaultdict(list)
for row in location_rows:
    scope_rows_by_parent[(row['country'], row['atlas_parent_id'])].append(row)
source_by_province = collections.defaultdict(list)
for feature in zmb_features:
    source_by_province[feature['properties']['PROVINCE']].append(feature)

assessment_fields = [
    'country','province_id','province_name','scope_member_count','scope_member_names',
    'source_vintage','source_role','source_total_locations','source_parent_match_count',
    'source_member_names','semantic_classification','administrative_role_finding',
    'parent_assignment_finding','completeness_license_vintage_finding',
    'neighbor_granularity_finding','boundary_finding','specific_risks','evidence_refs'
]
assessments = []
for province in scope['province_scopes']:
    country = 'MOZ' if any(r['country'] == 'MOZ' and r['atlas_parent_id'] == province['id'] for r in location_rows) else 'ZMB'
    members = scope_rows_by_parent[(country, province['id'])]
    assert len(members) == province['full_province_locations']
    names = sorted({r['location_name'] for r in members})
    if country == 'MOZ':
        classification = 'insufficient-evidence'
        source_total = ''
        source_match = ''
        source_names = ''
        admin_role = 'Pinned 2019 geoBoundaries metadata labels ADM2 canonical role as districts; source features do not carry an independently usable province-parent property. INE 2017 and 2026 catalog references report 161 national districts versus the 159-feature product; the direct 2024 province-yearbook files were not retrievable for byte-level verification in this work item.'
        parent_finding = 'No independent lawful current province-to-district crosswalk was retained. Existing Atlas parent membership is a review subject, not its own corroboration.'
        completeness = '159/161 roster conflict and malformed geoBoundaries source/license pointer remain unresolved; asserted CC BY 3.0 IGO is not independently verified.'
        neighbor = 'All selected records are source ADM2 district features; per-province and adjacent-unit identity/parent review remains blocked on a current lawful crosswalk.'
        risks = 'Province-parent identity and completeness; Pemba/Metuge lineage; city-tier distinctions in all seven Cidade-labelled records; no validated boundary/topology or island-omission check.'
        vintage = '2019 product; source-data update 2023-01-19; currentness unproven'
        role = 'ADM2 / districts (geoBoundaries metadata assertion)'
        evidence = 'MOZ-GB-2019; MOZ-INE-2017-CATALOG; MOZ-INE-2026-CENSUS-CARTOGRAPHY-LEAD; issue-412-scope'
    else:
        official = source_by_province[province['name']]
        source_names_list = sorted(f['properties']['DISTRICT'] for f in official)
        member_names_norm = {norm(name) for name in names}
        feature_by_member = [zmb_by_name[norm(name)][0] for name in names]
        matched = [f for f in feature_by_member if f['properties']['PROVINCE'] == province['name']]
        # A parent is justified only when the whole parent roster agrees, all issue
        # members agree, and no selected member assigned elsewhere maps into it.
        source_scoped = [f for f in zmb_features if f['properties']['PROVINCE'] == province['name'] and norm(f['properties']['DISTRICT']) in member_names_norm]
        excluded_current_names = sorted(f['properties']['DISTRICT'] for f in official if norm(f['properties']['DISTRICT']) not in member_names_norm)
        external_source_members = sorted(f['properties']['DISTRICT'] for f in zmb_features if f['properties']['PROVINCE'] == province['name'] and norm(f['properties']['DISTRICT']) not in member_names_norm)
        wrong_parent = sorted(f['properties']['DISTRICT'] for f in feature_by_member if f['properties']['PROVINCE'] != province['name'])
        equal_rosters = {norm(x) for x in source_names_list} == member_names_norm
        justified = equal_rosters and len(matched) == len(members) and not external_source_members and not wrong_parent
        classification = 'justified' if justified else 'insufficient-evidence'
        source_total = len(official)
        source_match = len(matched)
        source_names = '; '.join(source_names_list)
        admin_role = 'ZamStats 2022 Census National Analytical Report (PDF p.24 / printed p.2) describes ten provinces and 116 districts at census date. OSG/GRID3 2022 item describes national, ten provincial and 116 district boundaries; its PROVINCE field supplies current layer parent labels. FEATURE_TY distinguishes District Town, Provincial Town, City, and one District Tiwn value; the source supplies no codebook for this field, so it is not treated as an ADM-tier field.'
        parent_finding = ('Whole 2022 layer roster agrees one-to-one with the pinned 2020 geoBoundaries district names and this Atlas parent group.' if justified else 'Source roster and Atlas parent membership differ or a selected member has another official PROVINCE value: ' + ('wrong-parent=' + ','.join(wrong_parent) if wrong_parent else '') + ('; source-parent members outside this issue group=' + ','.join(external_source_members) if external_source_members else '') + ('; official-parent names not in the group=' + ','.join(excluded_current_names) if excluded_current_names else ''))
        completeness = 'OSG/GRID3 2022 layer contains 116 district features; all 116 names crosswalk one-to-one to pinned geoBoundaries 2020 names. The census report confirms 10 provinces/116 districts at 2022 census date. Current post-2022 legal completeness is unverified; dataset states underlying district narratives date through 2017 and 2021. CC BY 4.0 item assertion.'
        neighbor = 'Compare full province roster and scope roster in source_member_names/scope_member_names. The four unresolved groups are Central, Lusaka, Muchinga and Southern; remaining five groups are one-to-one by official PROVINCE field.'
        risks = 'Parent mismatches handed to #1043 (Chama/Eastern, Chirundu/Southern, Itezhi-Tezhi/Southern); linework/adjacency/omitted-island validation remains open. FEATURE_TY mix is not documented as an administrative tier.'
        vintage = '2022 official layer; item created 2024-02-16, modified 2024-03-26; district narratives referenced through 2021'
        role = 'Administrative province group / 2022 district boundaries (OSG/GRID3 item assertion)'
        evidence = 'ZMB-OSG-GRID3-2022; ZMB-ZAMSTATS-2022-ANALYTICAL-REPORT; ZMB-GB-2020; issue-412-scope'
    assessments.append({
        'country':country,'province_id':province['id'],'province_name':province['name'],
        'scope_member_count':len(members),'scope_member_names':'; '.join(names),
        'source_vintage':vintage,'source_role':role,'source_total_locations':source_total,
        'source_parent_match_count':source_match,'source_member_names':source_names,
        'semantic_classification':classification,'administrative_role_finding':admin_role,
        'parent_assignment_finding':parent_finding,'completeness_license_vintage_finding':completeness,
        'neighbor_granularity_finding':neighbor,'boundary_finding':'insufficient-evidence: no independent boundary, topology, adjacency, gap/overlap or authoritative linework comparison in this packet.',
        'specific_risks':risks,'evidence_refs':evidence
    })
assert len(assessments) == 16

# Explicit all-country 2022 source roster. Eastern is retained as source context
# but marked outside this issue's exact owned province scope.
roster_fields = ['source_province','source_district_count','source_district_names','source_feature_type_counts','issue_scope_status','source_file_sha256']
zmb_hash = digest(zmb_path)[1]
roster_rows=[]
scoped_names_by_parent={}
for province in scope['province_scopes']:
    if any(r['country']=='ZMB' and r['atlas_parent_id']==province['id'] for r in location_rows):
        scoped_names_by_parent[province['name']]={norm(r['location_name']) for r in scope_rows_by_parent[('ZMB',province['id'])]}
for province, features in sorted(source_by_province.items()):
    types=collections.Counter(f['properties'].get('FEATURE_TY','') for f in features)
    names=sorted(f['properties']['DISTRICT'] for f in features)
    status='in-scope: assessed in province-assessments.csv' if province in scoped_names_by_parent else 'outside issue province scope'
    roster_rows.append({'source_province':province,'source_district_count':len(features),'source_district_names':'; '.join(names),'source_feature_type_counts':'; '.join(f'{k}={v}' for k,v in sorted(types.items())),'issue_scope_status':status,'source_file_sha256':zmb_hash})
assert sum(int(row['source_district_count']) for row in roster_rows)==116

# Source-reported Area_km is screened as supplied metadata only; no polygon area is recomputed here.
area_fields=['source_province','source_district_count','source_Area_km_sum','largest_source_district','largest_source_Area_km','largest_share_of_source_province_Area_pct','source_layer_area_field','area_screen_limit']
area_rows=[]
for province, features in sorted(source_by_province.items()):
    values=[(f['properties']['DISTRICT'],float(f['properties']['Area_km'])) for f in features]
    total=sum(value for _,value in values)
    largest,largest_area=max(values,key=lambda row:row[1])
    area_rows.append({'source_province':province,'source_district_count':len(features),'source_Area_km_sum':f'{total:.3f}','largest_source_district':largest,'largest_source_Area_km':f'{largest_area:.3f}','largest_share_of_source_province_Area_pct':f'{100*largest_area/total:.2f}','source_layer_area_field':'Area_km (unvalidated source value)','area_screen_limit':'Source values and aggregation only; source method/precision and geometry are not independently validated. The share is a screening signal, not an oversized-unit finding.'})
assert len(area_rows)==10 and abs(sum(float(row['source_Area_km_sum']) for row in area_rows)-752657.1242261719)<0.001

risk_fields=['risk_category','geographic_subjects','review_status','evidence_observed','unresolved_question','handoff_or_action']
city_rows=[r for r in location_rows if r['country']=='MOZ' and r['location_name'].casefold().startswith('cidade')]
multis=[r for r in location_rows if int(r['atlas_polygon_parts'])>1 or int(r['source_polygon_parts'])>1]
remainder_pat=re.compile(r'(^|\b)(other|others|remainder|remaining|rest of|unnamed|unallocated|unknown|unspecified|not stated)(\b|$)',re.I)
remainder_rows=[r for r in location_rows if remainder_pat.search(r['location_name']) or remainder_pat.search(r['source_name'])]
feature_types=collections.Counter(f['properties'].get('FEATURE_TY','') for f in zmb_features)
risk_rows=[
 {'risk_category':'fragmented or city-labelled administrative territories','geographic_subjects':'Mozambique: '+ '; '.join(sorted(r['location_name'] for r in city_rows))+'; Zambia: Kitwe, Ndola, Lusaka, Livingstone source feature types City', 'review_status':'partially screened; legal granularity unresolved','evidence_observed':f'{len(city_rows)} Mozambique Cidade-labelled ADM2 rows are separate source records; the first-pass packet inspected official INE territorial tables for Nampula and Pemba only. Zambia 2022 source FEATURE_TY has City=4 and Provincial Town=11, all inside a district-boundary item whose source has no codebook for FEATURE_TY.', 'unresolved_question':'Whether each municipal/city label is a district-tier unit, an urban municipality, or a separate tier; name and feature type alone cannot establish this.','handoff_or_action':'Mozambique 159/161 and Pemba/Metuge roster lineage is in #1042; Zambia feature-type semantics are a source-restoration follow-up if codebook not recovered.'},
 {'risk_category':'province-sized locations','geographic_subjects':'all 223 frozen location IDs; province groups are the 16 scope rows', 'review_status':'screened by source role; size outliers unresolved','evidence_observed':'All frozen source IDs are geoBoundaries ADM2/district records. OSG/GRID3 2022 distinguishes province and district boundaries at dataset level. Its source-reported Area_km screening identifies especially large district shares of the province source-area sums: Lufwanyama 43.58% of Copperbelt and Rufunsa 43.00% of Lusaka. See zambia-source-area-screen.csv; the field/method is not independently validated.', 'unresolved_question':'No helper-based polygon-area or official ADM1 overlay was run; the 2019 geoBoundaries max-area statistics and OSG Area_km do not decide if a district is implausibly large or acts as a province surrogate.', 'handoff_or_action':'Retain all boundary statuses insufficient; geometry/domain-review follow-up needed before regional certification.'},
 {'risk_category':'anonymous administrative remainders','geographic_subjects':'all 223 names', 'review_status':'no remainder label found; completeness still unresolved','evidence_observed':f'Pattern screen found {len(remainder_rows)} names matching other/remaining/remainder/unnamed/unallocated/unknown/unspecified patterns in Atlas/source labels.', 'unresolved_question':'The name screen cannot detect omitted anonymous geometry or a synthetic catch-all under a plausible name; MOZ roster still differs 159 vs 161.', 'handoff_or_action':'Use complete lawful current official rosters under #1042; no exception inferred from label absence.'},
 {'risk_category':'disconnected territories and omitted islands','geographic_subjects':'Multipart candidates: '+ '; '.join(sorted(r['location_name'] for r in multis))+'; explicit island-context candidates: Ibo, Ilha de Moçambique, Chilubi', 'review_status':'named island-risk screen; inclusion/omission remains unresolved','evidence_observed':f'{len(multis)} rows have a multi-part geometry in Atlas or the pinned source; first-pass counts are MOZ 13 Atlas/19 source, ZMB 6 Atlas/4 source. INE maps Ilha de Moçambique with island and mainland context; the official Mozambique tourism portal identifies Ibo among the Quirimbas islands; Northern Province Administration and Chilubi Town Council place district administration on Chilubi Island. These web leads have no retained original bytes/checksum and do not support a boundary verdict.', 'unresolved_question':'Multipart counts neither prove island coverage nor reveal absent islands; current lawful coast/lake source overlays and topology remain unverified, including whether single-part Chilubi and multipart Ibo/Ilha geometries include all relevant land.', 'handoff_or_action':'No geometry fix proposed; retain all rows as insufficient-evidence and require a lawful current ADM1/ADM2 comparison with explicit positive/negative island controls in a bounded geometry packet.'},
 {'risk_category':'repeated tiers and neighboring granularity','geographic_subjects':'all 223 ADM2 records; 16 parents', 'review_status':'partially screened; unit-kind discordance unresolved','evidence_observed':f'Pinned geoBoundaries source_type is ADM2 across the roster; no ADM3+ or remainder labels occur. OSG/GRID3 FEATURE_TY counts: {"; ".join(f"{k}={v}" for k,v in sorted(feature_types.items()))}; no field codebook included.', 'unresolved_question':'Feature-type meanings for City/Provincial Town/District Town are not explained by the item, and Mozambique city/district hierarchy requires current legal roster evidence.', 'handoff_or_action':'Do not collapse or promote city labels; request source codebook/current INE province tables and adjudicate source tier.'},
 {'risk_category':'oversized province groups / weak parent assignments','geographic_subjects':'16 province groups and their 223 scoped locations', 'review_status':'individual province classifications recorded; four ZMB groups and all seven MOZ groups insufficient','evidence_observed':'See province-assessments.csv and zambia-source-area-screen.csv. ZMB 2022 source parent rosters expose Chama, Chirundu and Itezhi-Tezhi discrepancies and resulting Central/Lusaka/Muchinga/Southern cross-parent gaps; Lufwanyama and Rufunsa dominate their province source-reported area sums. Mozambique lacks independent province parent fields.', 'unresolved_question':'Count size is not geographic suitability; no area/shape quality threshold proves a group or boundary correct.', 'handoff_or_action':'#1043 covers the three disputed Zambia rows and parent groups; #1042 covers current MOZ province relationships/completeness; #1048 owns FEATURE_TY and Area_km source semantics. Preserve all current identities and boundaries.'},
 {'risk_category':'inconsistent neighboring units and parent context','geographic_subjects':'country scope MOZ 121/159; ZMB 102/116; all row neighbors within pinned source', 'review_status':'ZMB whole-country name/parent screen; MOZ partial source screen; cross-region neighbors unresolved', 'evidence_observed':'ZMB official 116-name roster crosswalks one-to-one to geoBoundaries; 5 of 9 scoped Zambia parent rosters agree, 4 are insufficient. MOZ exact-name joins are identity checks only; current district count/source lineage conflicts remain.', 'unresolved_question':'No current, lawful comparable source and boundary topology for all province/neighbor units; neighboring packets/other affected regions were not geometrically harmonized.', 'handoff_or_action':'Keep area purpose bounded to this batch; coordinate shared parent decisions at regional integration after #1042/#1043.'}
]

write_csv(ROOT/'province-assessments.csv', assessment_fields, assessments)
write_csv(ROOT/'zambia-province-roster.csv', roster_fields, roster_rows)
write_csv(ROOT/'zambia-source-area-screen.csv', area_fields, area_rows)
write_csv(ROOT/'geographic-risk-review.csv', risk_fields, risk_rows)

# Verify committed plus referenced source identities before recording evidence.
retained = [PACKET/'source/geoboundaries/MOZ/geoBoundaries-MOZ-ADM2.geojson', PACKET/'source/geoboundaries/MOZ/geoBoundaries-MOZ-ADM2-metaData.json', PACKET/'source/geoboundaries/ZMB/geoBoundaries-ZMB-ADM2.geojson', PACKET/'source/geoboundaries/ZMB/geoBoundaries-ZMB-ADM2-metaData.json', zmb_path,
 ROOT/'source/zambia-2022/arcgis-item-58c57f0ae33249bd8948dbf253f4e49e.json', ROOT/'source/zambia-2022/arcgis-layer-0-schema.json']
for path in retained:
    data=path.read_bytes()
    assert len(data)>0 and len(hashlib.sha256(data).hexdigest())==64
classes=collections.Counter(r['semantic_classification'] for r in assessments)
assert classes=={'justified':5,'insufficient-evidence':11}
assert sum(r['country']=='MOZ' for r in assessments)==7
assert sum(r['country']=='ZMB' for r in assessments)==9
assert len(city_rows)==7 and len(remainder_rows)==0
assert len(risk_rows)==7 and len(area_rows)==10
print('PASS: 223 unique frozen issue IDs map once to the 16 frozen province groups')
print('PASS: issue #411 and #412 Mozambique source-ID partitions are disjoint and reconcile 38 + 121 = 159')
print('PASS: all 116 Zambia district names crosswalk one-to-one between retained 2020 and 2022 source rosters')
print('PASS: 16 province assessments individually classified: justified=5, insufficient-evidence=11')
print('PASS: Zambia official 2022 roster has 116 districts across ten provinces; Eastern is explicitly outside this issue scope')
print(f'PASS: {len(inventory["source_files"])} retained source/metadata files match exact SHA-256 and byte lengths')
print('PASS: ten Zambia province source-area screens identify size outliers without elevating them to geographic findings')
print('PASS: seven explicit acceptance-risk categories screened; uncertainty retained for geography not tested')
print('LIMIT: current MOZ province crosswalk/completeness/license and all 223 boundary/topology decisions remain insufficient as reported')
