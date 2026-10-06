#!/usr/bin/env python3
"""Reproduce the exact-scope Eastern Cape/MDB identity and parent crosswalk.

Reads pinned Atlas files plus this packet's dated API snapshots. Writes only under
this packet. It does not retrieve data or mutate the repository baseline.
"""
from __future__ import annotations
import hashlib
import json
import re
import subprocess
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PACKET = ROOT / 'data/regional-review/eastern-cape-source-restoration-435'
SOURCE = PACKET / 'sources'
FINDINGS = PACKET / 'findings'
BASE = 'e8138aef2004b419cb8c458ccc1fb2ce31b639f6'
PINS = {
    'administrative-sources.json': ('data/administrative-sources.json', 'ed0051d2956271c72f8917e7da0c6f53e5dfb595bee5920cac489a65a747d633'),
    'geography_part-28.json': ('data/geography/part-28.json', '2aab2f36aeeb651ee8e6cc656e9541ad14e2ced2ea8160e8700ad4dc950c379d'),
    'hierarchy.json': ('data/hierarchy.json', '568301690ef231a85856666b57876a5efe8d8c7c6e671a56d81307b2dc28b80b'),
    'world-index.json': ('data/world-index.json', 'a62d4a74f0f969e228dfcdeb2797bb689ce9836c2498cadd31ed622ad2c38c03'),
    'source_register_435': ('data/regional-review/regional-review-b9aef9289b79194e/findings/source-register.json', 'f35089b4369f02119abe0973683c507643e7a3fe37b6a82706b7cb6e480e78cb'),
}
OWNED_IDS = [
    'gb:ZAF:ADM3:15628383B16723794281290', 'gb:ZAF:ADM3:15628383B24019341917361',
    'gb:ZAF:ADM3:15628383B24472250012031', 'gb:ZAF:ADM3:15628383B28857154592205',
    'gb:ZAF:ADM3:15628383B33674951697181', 'gb:ZAF:ADM3:15628383B35584475836677',
    'gb:ZAF:ADM3:15628383B36159893459203', 'gb:ZAF:ADM3:15628383B46688478529811',
    'gb:ZAF:ADM3:15628383B4889923419833', 'gb:ZAF:ADM3:15628383B56060894344771',
    'gb:ZAF:ADM3:15628383B59220525748831', 'gb:ZAF:ADM3:15628383B67522024924235',
    'gb:ZAF:ADM3:15628383B78908098986015', 'gb:ZAF:ADM3:15628383B80616091697700',
    'gb:ZAF:ADM3:15628383B88034979550306', 'gb:ZAF:ADM3:15628383B92131487833225',
    'gb:ZAF:ADM3:15628383B99818150234159',
]


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def norm(value: str) -> str:
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '', value)


def load_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def source_feature_objects(paths, max_feature_bytes=32 * 1024 * 1024):
    """Yield one GeoJSON feature at a time across exact byte-split source parts."""
    def chunks():
        for p in paths:
            with p.open('rb') as stream:
                while True:
                    block = stream.read(256 * 1024)
                    if not block:
                        break
                    yield block

    stream = iter(chunks())
    buffer = bytearray()
    cursor = 0

    def refill():
        nonlocal buffer
        try:
            block = next(stream)
        except StopIteration:
            return False
        buffer.extend(block)
        return True

    while True:
        at = buffer.find(b'"features"', cursor)
        if at >= 0:
            cursor = at + len(b'"features"')
            break
        cursor = max(0, len(buffer) - 32)
        if not refill():
            raise ValueError('Original GeoJSON has no features array')
    while True:
        while cursor >= len(buffer):
            if not refill():
                raise ValueError('Truncated GeoJSON before features array')
        if buffer[cursor] == ord('['):
            cursor += 1
            break
        cursor += 1

    whitespace = b' \t\r\n,'
    while True:
        while True:
            while cursor < len(buffer) and buffer[cursor] in whitespace:
                cursor += 1
            if cursor < len(buffer):
                break
            if not refill():
                raise ValueError('Truncated GeoJSON feature array')
        if buffer[cursor] == ord(']'):
            return
        if buffer[cursor] != ord('{'):
            raise ValueError('Feature array has unexpected non-object value')
        start = cursor
        depth = 0
        in_string = False
        escaped = False
        while True:
            while cursor < len(buffer):
                c = buffer[cursor]
                cursor += 1
                if in_string:
                    if escaped:
                        escaped = False
                    elif c == ord('\\'):
                        escaped = True
                    elif c == ord('"'):
                        in_string = False
                elif c == ord('"'):
                    in_string = True
                elif c == ord('{'):
                    depth += 1
                elif c == ord('}'):
                    depth -= 1
                    if depth == 0:
                        raw = bytes(buffer[start:cursor])
                        if len(raw) > max_feature_bytes:
                            raise ValueError('One original source feature exceeds the 32 MiB reproduction budget')
                        yield raw
                        buffer = buffer[cursor:]
                        cursor = 0
                        break
                if cursor - start > max_feature_bytes:
                    raise ValueError('One original source feature exceeds the 32 MiB reproduction budget')
            else:
                if not refill():
                    raise ValueError('Truncated GeoJSON feature object')
                continue
            break


def hash_parts(paths):
    overall = hashlib.sha256()
    parts = []
    total = 0
    for p in paths:
        h = hashlib.sha256()
        size = 0
        with p.open('rb') as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                h.update(block)
                overall.update(block)
                size += len(block)
                total += len(block)
        parts.append({'path': str(p.relative_to(ROOT)), 'bytes': size, 'sha256': h.hexdigest()})
    return {'bytes': total, 'sha256': overall.hexdigest(), 'parts': parts}


def main() -> None:
    baseline_receipts = {}
    for pin, (path, expected_sha) in PINS.items():
        raw = subprocess.run(['git', '-C', str(ROOT), 'show', f'{BASE}:{path}'],
                             check=True, capture_output=True).stdout
        actual_sha = hashlib.sha256(raw).hexdigest()
        assert actual_sha == expected_sha, f'Baseline pin changed: {pin}'
        baseline_receipts[pin] = {'path': path, 'bytes': len(raw), 'sha256': actual_sha}

    issue = load_json(SOURCE / 'issue-1137-api-snapshot.json')
    body = issue['body']
    block = re.search(r'<!-- worldatlas-work:v1\s*(\{.*?\})\s*-->', body, re.S)
    assert block, 'Issue snapshot lacks worldatlas-work:v1 scope block'
    contract = json.loads(block.group(1))
    assert contract['owned_paths'] == ['data/regional-review/eastern-cape-source-restoration-435/']
    assert set(contract['evidence_quality']['subject_ids']) == set(OWNED_IDS)
    assert contract['max_prs'] == 1
    sibling = load_json(SOURCE / 'issue-955-api-snapshot.json')
    sibling_block = re.search(r'<!-- worldatlas-work:v1\s*(\{.*?\})\s*-->', sibling['body'], re.S)
    assert sibling_block, 'Sibling issue snapshot lacks exact work scope'
    sibling_contract = json.loads(sibling_block.group(1))
    sibling_ids = set(sibling_contract['evidence_quality']['subject_ids'])
    assert len(sibling_ids) == 196 and sibling_ids.isdisjoint(OWNED_IDS)

    atlas = load_json(ROOT / 'data/geography/part-28.json')
    atlas_rows = {f['properties']['id']: f['properties'] for f in atlas['features']
                  if f.get('properties', {}).get('id') in OWNED_IDS}
    assert set(atlas_rows) == set(OWNED_IDS), 'Current containing file does not include exact scope'
    parents = load_json(ROOT / 'data/hierarchy.json')
    parent_rows = {x.get('id'): x for x in parents if x.get('id')} if isinstance(parents, list) else {}

    prior_roster = [json.loads(line) for line in
                    (ROOT / 'data/regional-review/regional-review-b9aef9289b79194e/findings/subject-roster.jsonl').read_text().splitlines()]
    prior_rows = {x['id']: x for x in prior_roster if x.get('id') in OWNED_IDS}
    assert set(prior_rows) == set(OWNED_IDS), 'Prior packet omitted one or more exact subjects'

    prior_packet = ROOT / 'data/regional-review/regional-review-b9aef9289b79194e'
    prior_source_register = load_json(prior_packet / 'findings/source-register.json')
    original_rows = [x for x in prior_source_register['retained_polygon_sources']
                     if x.get('evidence_id') == 'GB-ZAF-2020']
    assert len(original_rows) == 1
    original_register = original_rows[0]
    original_paths = [prior_packet / x['path'] for x in original_register['parts']]
    original_raw = hash_parts(original_paths)
    assert original_raw['bytes'] == original_register['bytes']
    assert original_raw['sha256'] == original_register['sha256_exact_retained_bytes']
    assert [x['sha256'] for x in original_raw['parts']] == [x['sha256'] for x in original_register['parts']]
    ids_needed = {x['source_original_id'] for x in prior_rows.values()}
    original_features = {}
    original_feature_count = 0
    for raw_feature in source_feature_objects(original_paths):
        feature = json.loads(raw_feature)
        props = feature.get('properties', {})
        original_feature_count += 1
        oid = props.get('shapeID')
        if oid in ids_needed:
            assert oid not in original_features, f'Duplicate original source ID {oid}'
            original_features[oid] = {
                'name': props.get('shapeName'), 'shape_type': props.get('shapeType'),
                'geometry_type': feature.get('geometry', {}).get('type'),
            }
    assert original_feature_count == original_register['feature_count'] == 213
    assert set(original_features) == ids_needed, 'Original source stream does not contain the exact 17 ancestry IDs'

    attrs_doc = load_json(SOURCE / 'mdb-2021-eastern-cape-attribute-roster.json')
    geo_doc = load_json(SOURCE / 'mdb-2021-eastern-cape-boundaries.geojson')
    attrs_2026_doc = load_json(SOURCE / 'mdb-2026-eastern-cape-attribute-roster.json')
    geo_2026_doc = load_json(SOURCE / 'mdb-2026-eastern-cape-boundaries.geojson')
    attrs = attrs_doc['features']
    geos = geo_doc['features']
    attrs_2026 = attrs_2026_doc['features']
    geos_2026 = geo_2026_doc['features']
    assert len(attrs) == 33 and len(geos) == 33
    assert len(attrs_2026) == 33 and len(geos_2026) == 33
    assert len({f['attributes']['CAT_B'] for f in attrs}) == 33
    assert len({f['attributes']['CAT_B'] for f in attrs_2026}) == 33
    assert sum(f['attributes']['CATEGORY'] == 'A' for f in attrs) == 2
    assert sum(f['attributes']['CATEGORY'] == 'B' for f in attrs) == 31
    assert geo_doc.get('type') == 'FeatureCollection'

    mdb_by_name = {}
    for f in attrs:
        a = f['attributes']
        k = norm(a['MUNICNAME'])
        assert k not in mdb_by_name
        mdb_by_name[k] = a
    geom_by_name = {norm(f['properties']['MUNICNAME']): f for f in geos}
    assert len(geom_by_name) == 33
    mdb_2026_by_code = {f['attributes']['CAT_B']: f['attributes'] for f in attrs_2026}
    geom_2026_by_code = {f['properties']['CAT_B']: f for f in geos_2026}
    assert len(mdb_2026_by_code) == 33 and len(geom_2026_by_code) == 33
    assert sum(f['attributes']['CATEGORY'] == 'A' for f in attrs_2026) == 2
    assert sum(f['attributes']['CATEGORY'] == 'B' for f in attrs_2026) == 31
    assert {f['attributes']['DATE_'] for f in attrs_2026} == {1793750400000}
    mdb_by_code = {f['attributes']['CAT_B']: f['attributes'] for f in attrs}
    geom_by_code = {f['properties']['CAT_B']: f for f in geos}

    crosswalk = []
    for sid in sorted(OWNED_IDS):
        p = atlas_rows[sid]
        src = prior_rows[sid]
        key = norm(p['name'])
        source_feature = original_features[p['metadata']['original_id']]
        assert source_feature['name'] == p['name'], f'Original source name/ID differs for {sid}'
        identity_note = 'exact normalized municipality-name match'
        if key in mdb_by_name:
            m = mdb_by_name[key]
            g = geom_by_name[key]
        else:
            # MDB's service names EC137 "Dr AB Xuma"; this Atlas/2020 source calls
            # EC137 Engcobo. Same source code is a strong crosswalk clue, but a
            # gazetted naming instrument is still needed to certify name continuity.
            assert p['name'] == 'Engcobo' and 'EC137' in mdb_by_code
            m = mdb_by_code['EC137']
            g = geom_by_code['EC137']
            identity_note = 'MDB code EC137 maps source name Engcobo to current label Dr AB Xuma; identity continuity/name-change date requires official instrument'
        assert g['properties']['CAT_B'] == m['CAT_B']
        assert m['PROVINCE'] == 'EC'
        assert src['source_original_id'] == p['metadata']['original_id']
        assert src['source_license'] == 'Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO)'
        geom = g['geometry']
        m26 = mdb_2026_by_code[m['CAT_B']]
        g26 = geom_2026_by_code[m['CAT_B']]
        assert m26['PROVINCE'] == 'Eastern Cape'
        assert g26['properties']['MUNICNAME'] == m26['MUNICNAME']
        assert g26['geometry'] and g26['geometry']['type'] in ('Polygon', 'MultiPolygon')
        assert geom and geom['type'] in ('Polygon', 'MultiPolygon')
        parts = len(geom['coordinates']) if geom['type'] == 'MultiPolygon' else 1
        crosswalk.append({
            'atlas_id': sid,
            'source_2020': {
                'name': p['name'], 'source': p['metadata']['source_id'],
                'original_id': p['metadata']['original_id'], 'role': p['metadata']['source_role'],
                'administrative_level': p['metadata']['administrative_level'],
                'parent_id': p['parent_id'], 'parent_name_at_2020': src['parent_name'],
                'source_year': p['metadata']['reference_year'],
                'whole_source_sha256': '74e489fd4370972403950719026a317abba443668cea7d49f4b36c61637958f1'
                , 'replayed_source_name': source_feature['name'],
                'replayed_source_shape_type': source_feature['shape_type'],
                'replayed_source_geometry_type': source_feature['geometry_type']
            },
            'mdb_2021': {
                'municipality_name': m['MUNICNAME'], 'province_code': m['PROVINCE'],
                'category': m['CATEGORY'], 'category_label': m['CAT2'],
                'municipality_code': m['CAT_B'], 'name_code': m['NAMECODE'],
                'district_name': m['DISTRICT_N'], 'district_code': m['DISTRICT'],
                'feature_date_utc': m['DATE'], 'geometry_type': geom['type'],
                'polygon_parts': parts,
                'identity_crosswalk_note': identity_note,
            },
            'mdb_2026_prospective': {
                'municipality_name': m26['MUNICNAME'], 'province_name': m26['PROVINCE'],
                'category': m26['CATEGORY'], 'category_label': m26['CAT2'],
                'municipality_code': m26['CAT_B'], 'name_code': m26['NAMECODE'],
                'district_name': m26['DISTRICT_N'], 'district_code': m26['DISTRICT'],
                'dataset_effective_date_utc': m26['DATE_'],
                'geometry_type': g26['geometry']['type'],
                'current_as_of_evaluation': False,
                'limit': 'MDB item metadata says this layer comes into effect after the 2026 Local Government Elections, on 2026-11-04; it is prospective on the 2026-10-06 evaluation date.'
            },
        })
    assert len(crosswalk) == 17
    byname = {r['source_2020']['name']: r['mdb_2021'] for r in crosswalk}
    assert sum(v['category'] == 'A' for v in byname.values()) == 1
    assert sum(v['category'] == 'B' for v in byname.values()) == 16
    old_parent = {}
    for r in crosswalk:
        p = r['source_2020']['parent_name_at_2020']
        old_parent.setdefault(p, []).append(r)
    assert len(old_parent['Cacadu']) == 7
    assert all(r['mdb_2021']['district_name'] == 'Sarah Baartman' and r['mdb_2021']['district_code'] == 'DC10'
               for r in old_parent['Cacadu'])
    assert byname['Nelson Mandela Bay']['category'] == 'A'
    assert byname['Nelson Mandela Bay']['district_name'] == 'Nelson Mandela Bay'
    assert byname['Engcobo']['municipality_code'] == 'EC137'
    assert byname['Engcobo']['municipality_name'] == 'Dr AB Xuma'

    result = {
        'method_id': 'source-and-scope-reproduction', 'kind': 'source', 'outcome': 'passed',
        'positive_control': {'exact_source_feature_count': 213, 'exact_issue_scope_source_id_matches': len(original_features), 'outcome': 'passed'},
        'negative_control': {'sibling_issue': 955, 'scope_intersection_count': len(sibling_ids.intersection(OWNED_IDS)), 'outcome': 'passed'},
        'version': 1,
        'evaluated_against_commit': BASE,
        'baseline_pins': baseline_receipts,
        'scope_issue': 1137,
        'subject_count': len(crosswalk),
        'sibling_scope': {'issue': 955, 'subject_count': len(sibling_ids),
                          'intersection_count': len(sibling_ids.intersection(OWNED_IDS))},
        'subjects': crosswalk,
        'mdb_eastern_cape_roster': {
            'record_count': len(attrs), 'category_a_count': 2, 'category_b_count': 31,
            'attribute_response_sha256': sha(SOURCE / 'mdb-2021-eastern-cape-attribute-roster.json'),
            'geometry_response_sha256': sha(SOURCE / 'mdb-2021-eastern-cape-boundaries.geojson'),
            'feature_names_unique': len(mdb_by_name) == 33,
            'all_features_have_geometry': all(f.get('geometry') for f in geos),
            'scope_exact_name_crosswalk_count': len(crosswalk),
            'scope_unique_municipal_code_count': len({r['mdb_2021']['municipality_code'] for r in crosswalk}),
            'scope_category_counts': {'A': 1, 'B': 16},
            'scope_geometry_type_counts': {k: sum(r['mdb_2021']['geometry_type'] == k for r in crosswalk)
                                           for k in ('Polygon', 'MultiPolygon')},
            'scope_multipart_component_count': sum(r['mdb_2021']['polygon_parts'] for r in crosswalk),
            'assertion_limit': 'Roster and geometry are the exact publicly served ArcGIS REST response captured on retrieval date, not the original MDB shapefile bytes; existence, completeness and legal status of detached/island polygons beyond the service feature records remain unproven.'
        },
        'source_2020_exact_replay': {
            'feature_count': original_feature_count, 'exact_scope_match_count': len(original_features),
            'combined_source_bytes': original_raw['bytes'], 'combined_source_sha256': original_raw['sha256'],
            'read_method': 'stream exact ordered 25,352,714-byte parts; hash as concatenated bytes; parse one JSON feature at a time; never create a >32 MiB joined file or load the complete source into memory',
            'parts': original_raw['parts'],
        },
        'mdb_2026_prospective_roster': {
            'record_count': len(attrs_2026), 'category_a_count': 2, 'category_b_count': 31,
            'feature_date_utc': 1793750400000,
            'effective_date_utc': '2026-11-04T00:00:00Z',
            'dataset_effective_before_election': False,
            'attribute_response_sha256': sha(SOURCE / 'mdb-2026-eastern-cape-attribute-roster.json'),
            'geometry_response_sha256': sha(SOURCE / 'mdb-2026-eastern-cape-boundaries.geojson'),
            'scope_exact_code_crosswalk_count': len(crosswalk),
            'scope_category_counts': {'A': 1, 'B': 16},
            'scope_unique_municipal_code_count': len({r['mdb_2026_prospective']['municipality_code'] for r in crosswalk}),
            'assertion_limit': 'Official item states future effectiveness after the 2026 local elections. This geometry is retained for forward-reference only; it does not establish the legal/current footprint on 2026-10-06.'
        },
        'confirmed_2024_changes_in_scope': [
            {'dem_number': 'DEM6500', 'effective_subjects': ['gb:ZAF:ADM3:15628383B88034979550306', 'gb:ZAF:ADM3:15628383B16723794281290'], 'description': 'Lower Seplan and Emaqwathini villages move from Intsika Yethu (EC135) into Sakhisizwe (EC138); Gazette 5030, Notice 763, 2024-01-08; Section 21(5) confirmation in Gazette 5064, Notice 805, 2024-03-11.'},
            {'dem_number': 'DEM6506', 'effective_subjects': ['gb:ZAF:ADM3:15628383B4889923419833'], 'description': 'Mbanga administrative area moves from Mbhashe (EC121) into Dr AB Xuma (EC137); Gazette 5030, Notice 763, 2024-01-08; Section 21(5) confirmation in Gazette 5064, Notice 805, 2024-03-11.'},
            {'dem_number': 'DEM6611', 'effective_subjects': ['gb:ZAF:ADM3:15628383B4889923419833', 'gb:ZAF:ADM3:15628383B16723794281290'], 'description': 'Gqutyini D moves from Dr AB Xuma (EC137) into Sakhisizwe (EC138); Gazette 5030, Notice 763, 2024-01-08; Section 21(5) confirmation in Gazette 5064, Notice 805, 2024-03-11.'},
        ],
        'parent_findings': [
            {'source_parent_id': 'framework:province:cacadu:241cd826ea0e',
             'source_parent_name': 'Cacadu', 'member_count': 7, 'current_mdb_district_name': 'Sarah Baartman',
             'current_mdb_district_code': 'DC10', 'disposition': 'sourced-name-crosswalk; preserve historical/source label and stable member IDs; do not rename shared hierarchy in this research packet.'},
            {'source_parent_id': 'framework:province:chris-hani:9c3f8a57309e', 'member_count': 6,
             'current_mdb_district_name': 'Chris Hani', 'current_mdb_district_code': 'DC13',
             'disposition': 'current 2021 MDB roster supports district relationship; boundary vintage remains bounded by source date.'},
            {'source_parent_id': 'framework:province:joe-gqabi:2eb3c0ffac00', 'member_count': 3,
             'current_mdb_district_name': 'Joe Gqabi', 'current_mdb_district_code': 'DC14',
             'disposition': 'current 2021 MDB roster supports district relationship; boundary vintage remains bounded by source date.'},
            {'source_parent_id': 'framework:province:nelson-mandela-bay:923919a403a5', 'member_count': 1,
             'source_parent_name': 'Nelson Mandela Bay', 'current_mdb_category': 'A - Metropolitan Municipality',
             'current_mdb_code': 'NMA', 'disposition': 'separate metropolitan category is explicit in MDB; same-name repeat needs hierarchy/parent-level engineering review, not a local-municipality alias.'}
        ],
        'source_bytes': {
            'mdb_attribute_roster_sha256': sha(SOURCE / 'mdb-2021-eastern-cape-attribute-roster.json'),
            'mdb_geometry_geojson_sha256': sha(SOURCE / 'mdb-2021-eastern-cape-boundaries.geojson'),
            'mdb_item_metadata_sha256': sha(SOURCE / 'mdb-local-municipalities-2021-item-metadata.json'),
            'mdb_service_layer_metadata_sha256': sha(SOURCE / 'mdb-local-municipalities-2021-layer-metadata.json'),
            'mdb_2026_item_metadata_sha256': sha(SOURCE / 'mdb-2026-item-metadata.json'),
            'mdb_2026_layer_metadata_sha256': sha(SOURCE / 'mdb-2026-layer-metadata.json'),
            'mdb_2026_attribute_roster_sha256': sha(SOURCE / 'mdb-2026-eastern-cape-attribute-roster.json'),
            'mdb_2026_geometry_geojson_sha256': sha(SOURCE / 'mdb-2026-eastern-cape-boundaries.geojson'),
            'issue_1137_snapshot_sha256': sha(SOURCE / 'issue-1137-api-snapshot.json'),
            'issue_955_snapshot_sha256': sha(SOURCE / 'issue-955-api-snapshot.json'),
        }
    }
    FINDINGS.mkdir(parents=True, exist_ok=True)
    out = FINDINGS / 'mdb-crosswalk-and-reproduction.json'
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps({
        'output': str(out.relative_to(ROOT)), 'subject_count': len(crosswalk),
        'current_roster': result['mdb_eastern_cape_roster'],
        'parents': result['parent_findings'],
        'sha256': sha(out)
    }, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
