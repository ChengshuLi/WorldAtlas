#!/usr/bin/env python3
"""Reproduce issue #429 identity and boundary-screen findings from retained inputs.

Requires Python 3 and Shapely 2.0.7.  The overlap metric is planar EPSG:4326
and is a prioritization screen only; it does not resolve maritime or legal lines.
"""
from __future__ import annotations
import csv, hashlib, json, re
from collections import Counter
from pathlib import Path
import shapely
from shapely.geometry import shape
from shapely.validation import make_valid

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = 'f7b45a2d491ced539ca520979e182bcec9e0e90b'
EXPECTED_STATES = {'12': 'Florida', '37': 'North Carolina', '45': 'South Carolina', '54': 'West Virginia'}

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def norm(value: str) -> str:
    value = value.lower().replace('&', 'and').replace('saint', 'st').replace('.', '').replace('-', ' ')
    value = re.sub(r'\b(county|parish|borough|census area|city and borough|municipality)\b', '', value)
    return ' '.join(value.split())

def main() -> None:
    issue = json.loads((HERE / 'issue-api-snapshot.json').read_text())
    scope = json.loads((HERE / 'issue-scope.json').read_text())
    register = json.loads((HERE / 'source-register.json').read_text())
    ids = scope['member_location_ids']
    assert issue['number'] == 429 and issue['state'] == 'open'
    assert len(ids) == len(set(ids)) == scope['location_count'] == 268
    assert register['baseline_commit'] == BASE
    assert shapely.__version__ == '2.0.7'
    for item in register['baseline_inputs']:
        assert sha(ROOT / item['path']) == item['sha256'], item['path']
    for item in register['retained_evidence']:
        retained = ROOT / item['path']
        assert retained.stat().st_size == item['bytes'] and sha(retained) == item['sha256'], item['path']
    assert hashlib.sha256(('\n'.join(ids)).encode()).hexdigest() == scope['member_location_ids_sha256']

    source_data = json.loads((HERE / 'sources/geoboundaries-USA-ADM2-2018.geojson').read_text())
    source = {'gb:USA:ADM2:' + f['properties']['shapeID']: f for f in source_data['features']}
    atlas = {}
    for part in (25, 26, 27):
        doc = json.loads((ROOT / f'data/geography/part-{part}.json').read_text())
        atlas.update({f['id']: f for f in doc['features'] if f['id'] in set(ids)})
    hierarchy = {u['id']: u for u in json.loads((ROOT / 'data/hierarchy.json').read_text())}
    datasets = {}
    county_area_attributes = {}
    for vintage in ('2025', '2026'):
        folder = HERE / f'sources/tiger{vintage}'
        layer = 41 if vintage == '2025' else 82
        national_count = json.loads((folder / 'national-count.json').read_text())['count']
        assert national_count == 3235
        all_features, by_state = {}, {}
        if vintage == '2026':
            county_area_attributes = {}
        for fips in EXPECTED_STATES:
            doc = json.loads((folder / f'tigerweb-{vintage}-state-{fips}-counties.geojson').read_text())
            by_state[fips] = doc['features']
            for feature in doc['features']:
                geoid = feature['properties']['GEOID']
                assert geoid not in all_features
                all_features[geoid] = feature
            count = json.loads((folder / f'state-{fips}-count.json').read_text())['count']
            assert count == len(doc['features'])
            assert all(f['properties']['STATE'] == fips for f in doc['features'])
            if vintage == '2026':
                area_doc = json.loads((folder / f'state-{fips}-area-attributes.json').read_text())
                assert len(area_doc['features']) == len(doc['features'])
                attrs = {f['attributes']['GEOID']:f['attributes'] for f in area_doc['features']}
                assert len(attrs) == len(area_doc['features']) and set(attrs) == {f['properties']['GEOID'] for f in doc['features']}
                county_area_attributes.update(attrs)
        metadata = json.loads((folder / f'tigerweb-layer-{layer}-metadata.json').read_text())
        datasets[vintage] = {'all':all_features,'by_state':by_state,'national_count':national_count,'metadata':metadata}
    assert '2026' in datasets['2026']['metadata'].get('description','')
    census_by_state = datasets['2026']['by_state']
    state_land_totals = {fips:sum(int(county_area_attributes[f['properties']['GEOID']]['AREALAND']) for f in features) for fips,features in census_by_state.items()}
    assert set(ids) == set(source) & set(ids)
    assert set(ids) == set(atlas)
    rows, ious, ious_2018_2025, ious_2025_2026, low = [], [], [], [], []
    parent_counts, state_counts = Counter(), Counter()
    invalid = []
    for location_id in ids:
        sf, af = source[location_id], atlas[location_id]
        sp, ap = sf['properties'], af['properties']
        parent_id = ap.get('parent_id')
        parent = hierarchy.get(parent_id)
        assert parent and parent.get('level') == 'province'
        state_name = parent['name']
        state = next((code for code, name in EXPECTED_STATES.items() if name == state_name), None)
        assert state
        assert ap['name'] == sp['shapeName']
        assert ap['metadata']['source_role'] == 'Counties' and sp['shapeType'] == 'ADM2'
        assert sp['shapeGroup'] == 'USA'
        matches = {}
        for vintage in ('2025', '2026'):
            matches[vintage] = [f for f in datasets[vintage]['by_state'][state] if norm(f['properties']['NAME']) == norm(sp['shapeName'])]
            assert len(matches[vintage]) == 1, (location_id, vintage, state_name, sp['shapeName'], len(matches[vintage]))
        cf2025, cf2026 = matches['2025'][0], matches['2026'][0]
        props2025, props2026 = cf2025['properties'], cf2026['properties']
        assert props2025['GEOID'] == props2026['GEOID']
        assert props2026['STATE'] == state and props2026['LSADC'] == '06'
        assert props2026['NAME'].endswith('County')
        geoms = {'2018':shape(sf['geometry']), '2025':shape(cf2025['geometry']), '2026':shape(cf2026['geometry'])}
        geometry_types = {key:value.geom_type for key,value in geoms.items()}
        polygon_parts = {key:(len(value.geoms) if value.geom_type == 'MultiPolygon' else 1) for key,value in geoms.items()}
        valid = {key:value.is_valid for key,value in geoms.items()}
        for key in geoms:
            if not valid[key]:
                geoms[key] = make_valid(geoms[key])
        if not all(valid.values()):
            invalid.append(location_id)
        def iou(left, right):
            union = left.union(right).area
            return left.intersection(right).area / union if union else 0.0
        iou1825 = iou(geoms['2018'], geoms['2025'])
        iou1826 = iou(geoms['2018'], geoms['2026'])
        iou2526 = iou(geoms['2025'], geoms['2026'])
        ious.append(iou1826)
        ious_2018_2025.append(iou1825)
        ious_2025_2026.append(iou2526)
        current_id = props2026['GEOID']
        area_attrs = county_area_attributes[current_id]
        assert area_attrs['STATE'] == state and norm(area_attrs['NAME']) == norm(props2026['NAME'])
        area_land = int(area_attrs['AREALAND'])
        area_water = int(area_attrs['AREAWATER'])
        assert area_land > 0 and area_water >= 0
        land_share = area_land / state_land_totals[state]
        water_land_ratio = area_water / area_land
        assert current_id not in {row['tigerweb_2026_geoid'] for row in rows}
        state_counts[state_name] += 1
        parent_counts[(state_name, parent_id)] += 1
        boundary_flag = iou1826 < 0.95
        if boundary_flag:
            low.append(location_id)
        rows.append({
            'atlas_id': location_id,
            'source_shape_id': sp['shapeID'],
            'atlas_name': ap['name'],
            'source_name': sp['shapeName'],
            'parent_name': state_name,
            'parent_id': parent_id,
            'source_role': sp['shapeType'],
            'atlas_admin_role': ap['metadata'].get('source_role'),
            'semantic_role_finding': 'justified',
            'tigerweb_2025_geoid': props2025['GEOID'],
            'tigerweb_2025_name': props2025['NAME'],
            'tigerweb_2026_geoid': current_id,
            'tigerweb_2026_name': props2026['NAME'],
            'tigerweb_2026_statefp': props2026['STATE'],
            'tigerweb_2026_countyfp': props2026['COUNTY'],
            'tigerweb_2026_lsadc': props2026['LSADC'],
            'tigerweb_2026_arealand_m2': area_land,
            'tigerweb_2026_areawater_m2': area_water,
            'land_area_share_of_scoped_state': f'{land_share:.8f}',
            'water_to_land_area_ratio': f'{water_land_ratio:.8f}',
            'source_2018_geometry_type': geometry_types['2018'],
            'source_2018_polygon_parts': polygon_parts['2018'],
            'tigerweb_2025_geometry_type': geometry_types['2025'],
            'tigerweb_2025_polygon_parts': polygon_parts['2025'],
            'tigerweb_2026_geometry_type': geometry_types['2026'],
            'tigerweb_2026_polygon_parts': polygon_parts['2026'],
            'identity_and_parent_finding': 'justified',
            'iou_2018_to_2025_epsg4326_screen': f'{iou1825:.9f}',
            'iou_2018_to_2026_epsg4326_screen': f'{iou1826:.9f}',
            'iou_2025_to_2026_epsg4326_screen': f'{iou2526:.9f}',
            'boundary_screen': 'manual-review-priority' if boundary_flag else 'no-large-difference-screen-only',
            'whole_geometry_status': 'insufficient-evidence',
            'interpretation': ('2018/2026 footprint overlap is below 95%; distinguish source-vintage and water extent from a true boundary error.'
                               if boundary_flag else 'High 2018/2026 overlap is screening evidence only; it does not certify the authoritative boundary.'),
        })
    assert len(rows) == len(ids) == 268
    assert state_counts == Counter({'Florida':67,'North Carolina':100,'South Carolina':46,'West Virginia':55})
    assert len(set(r['tigerweb_2026_geoid'] for r in rows)) == 268
    rows.sort(key=lambda r: r['atlas_id'])
    out = HERE / 'individual-assessments.csv'
    with out.open('w', newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    prov_rows = []
    for ps in scope['province_scopes']:
        pid = ps['id']
        current_parent = hierarchy.get(pid)
        current_children = current_parent.get('metadata',{}).get('child_count') if current_parent else None
        issue_members = parent_counts.get((ps['name'],pid),0)
        matches_count = issue_members == ps['full_province_locations']
        prov_rows.append({'issue_scope_parent_id':pid,'issue_scope_parent_name':ps['name'],'issue_summary_count':ps['full_province_locations'],'current_hierarchy_parent_exists':bool(current_parent),'current_hierarchy_parent_children':current_children if current_children is not None else '', 'current_issue_members_under_parent':issue_members,'parent_role_finding':'justified' if current_parent else 'insufficient-evidence','issue_scope_reconciliation':'matches current scope' if matches_count else 'stale or missing current parent; preserve issue summary'})
    with (HERE / 'province-assessments.csv').open('w',newline='') as fh:
        writer=csv.DictWriter(fh,fieldnames=list(prov_rows[0]));writer.writeheader();writer.writerows(prov_rows)
    sorted_ious = sorted(ious)
    low_iou_ids = set(low)
    water_ratios = [float(r['water_to_land_area_ratio']) for r in rows]
    low_water_ratios = [float(r['water_to_land_area_ratio']) for r in rows if r['atlas_id'] in low_iou_ids]
    max_land_share = []
    for state_name in sorted(state_counts):
        candidate_rows = [r for r in rows if r['parent_name'] == state_name]
        largest = max(candidate_rows, key=lambda r: float(r['land_area_share_of_scoped_state']))
        max_land_share.append({'state':state_name,'name':largest['atlas_name'],'geoid':largest['tigerweb_2026_geoid'],'land_area_share':float(largest['land_area_share_of_scoped_state'])})
    source_multipart = [r for r in rows if r['source_2018_polygon_parts'] > 1]
    current_multipart = [r for r in rows if r['tigerweb_2026_polygon_parts'] > 1]
    summary = {
        'version': 1,
        'issue': 429,
        'baseline_commit': BASE,
        'shapely_version': shapely.__version__,
        'all_pinned_baseline_and_retained_source_bytes_verified': True,
        'baseline_input_pin_count': len(register['baseline_inputs']),
        'retained_source_pin_count': len(register['retained_evidence']),
        'issue_scope_count': len(ids),
        'scope_ids_sha256_newline_joined': hashlib.sha256(('\n'.join(ids)).encode()).hexdigest(),
        'matched_atlas_features': len(atlas),
        'matched_geoBoundaries_2018_source_features': len(ids),
        'matched_TIGERweb_2025_features': len(datasets['2025']['all']),
        'matched_TIGERweb_2026_features': len(datasets['2026']['all']),
        'matched_TIGERweb_2026_area_attribute_features': len(county_area_attributes),
        'province_scope_summary_rows': len(prov_rows),
        'province_scope_summary_matches_current_membership': sum(row['issue_scope_reconciliation'] == 'matches current scope' for row in prov_rows),
        'all_current_land_water_attributes_match_exact_geoid': len(county_area_attributes) == len(datasets['2026']['all']),
        'largest_county_land_share_by_state': max_land_share,
        'counties_where_reported_water_area_exceeds_land_area': sum(float(r['water_to_land_area_ratio']) > 1 for r in rows),
        'median_water_to_land_area_ratio_all_scoped_counties': sorted(water_ratios)[len(water_ratios)//2],
        'median_water_to_land_area_ratio_under_0_95_overlap_screen': sorted(low_water_ratios)[len(low_water_ratios)//2],
        'Census_TIGERweb_2025_national_count': datasets['2025']['national_count'],
        'Census_TIGERweb_2026_national_count': datasets['2026']['national_count'],
        'state_counts': dict(sorted(state_counts.items())),
        'parent_counts': [{'name': name, 'id': pid, 'count': count} for (name,pid),count in sorted(parent_counts.items())],
        'all_names_and_state_parents_match': True,
        'all_source_roles_are_USA_ADM2_counties': True,
        'all_geometries_valid_before_repair': not invalid,
        'multipart_2018_feature_count': len(source_multipart),
        'multipart_2026_feature_count': len(current_multipart),
        'maximum_source_polygon_parts': max(r['source_2018_polygon_parts'] for r in rows),
        'maximum_TIGERweb_2026_polygon_parts': max(r['tigerweb_2026_polygon_parts'] for r in rows),
        'multipart_screen_limit': 'Multiple polygon parts can reflect islands or source cuts; part counts do not establish missing/extra territory.' ,
        'original_issue_West_Virginia_partition': 'scope metadata records 54+1 under two old IDs; all 55 current children resolve to one current province parent',
        'invalid_geometry_ids': invalid,
        'planar_epsg4326_iou_2018_to_2026': {'minimum': sorted_ious[0], 'p25': sorted_ious[67], 'median': sorted_ious[134], 'p75': sorted_ious[201], 'maximum': sorted_ious[-1]},
        'planar_epsg4326_iou_2018_to_2025': {'minimum': sorted(ious_2018_2025)[0], 'median': sorted(ious_2018_2025)[134], 'maximum': sorted(ious_2018_2025)[-1]},
        'planar_epsg4326_iou_2025_to_2026': {'minimum': min(ious_2025_2026), 'median': sorted(ious_2025_2026)[134], 'maximum': max(ious_2025_2026)},
        'under_0_95_overlap_screen_count': len(low),
        'under_0_95_state_counts': dict(sorted(Counter(hierarchy[atlas[id]['properties']['parent_id']]['name'] for id in low).items())),
        'under_0_95_ids': sorted(low),
        'screen_limit': 'Overlap is planar in EPSG:4326 and prioritizes inspection only. Differences may reflect boundary vintage, generalized shorelines, and water extents; TIGER statistical boundaries disclaim jurisdictional determinations. Neither high nor low overlap alone justifies correction or approval.',
        'output': 'individual-assessments.csv',
        'output_sha256': sha(out),
        'province_assessments_output':'province-assessments.csv',
        'province_assessments_sha256': sha(HERE / 'province-assessments.csv'),
    }
    (HERE / 'reproduction-results.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({k:v for k,v in summary.items() if k not in ('under_0_95_ids',)}, indent=2))

if __name__ == '__main__':
    main()
