#!/usr/bin/env python3
"""Rebuild component-bounds inventory from preserved #140/#526 evidence."""
import hashlib
import json
import gzip
import io
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OWN = Path(__file__).resolve().parent
P140 = ROOT / 'data/regional-review/regional-review-4857646bb9b55df5'
P526 = ROOT / 'data/regional-review/regional-supplement-948d12b02687d2a9'
SRC = P140 / 'sources/geoBoundaries-KIR-ADM1.geojson'
BASE = P140 / 'baseline-extract.json'
PHX = P526 / 'phoenix-assessment.json'
MIGRATION_ARCHIVE = 'data/geographic-migration-archive.json.gz'
BASELINE_COMMIT = '8b6835dfa645cf763137374c3730401d5ac2f732'
CENSUS_ROWS = [
    ('Northern', 'Abaiang', 'census island row'), ('Northern', 'Butaritari', 'census island row'),
    ('Northern', 'Makin', 'census island row'), ('Northern', 'Marakei', 'census island row'),
    ('Northern', 'North Tarawa', 'reporting division of Tarawa'), ('South Tarawa', 'South Tarawa', 'reporting division of Tarawa'),
    ('Central', 'Abemama', 'census island row'), ('Central', 'Aranuka', 'census island row'),
    ('Central', 'Banaba', 'raised coral island'), ('Central', 'Kuria', 'census island row'), ('Central', 'Maiana', 'census island row'),
    ('Southern', 'Arorae', 'census island row'), ('Southern', 'Beru', 'census island row'),
    ('Southern', 'Nikunau', 'census island row'), ('Southern', 'Nonouti', 'census island row'),
    ('Southern', 'North Tabiteuea', 'reporting division of Tabiteuea'), ('Southern', 'Onotoa', 'census island row'),
    ('Southern', 'South Tabiteuea', 'reporting division of Tabiteuea'), ('Southern', 'Tamana', 'census island row'),
]

def load(path):
    return json.loads(path.read_text())

def points(value):
    if isinstance(value, list):
        if len(value) >= 2 and isinstance(value[0], (float, int)) and isinstance(value[1], (float, int)):
            yield value
        else:
            for child in value:
                yield from points(child)

def bbox(geometry):
    pts = list(points(geometry['coordinates']))
    return [round(min(p[0] for p in pts), 7), round(min(p[1] for p in pts), 7),
            round(max(p[0] for p in pts), 7), round(max(p[1] for p in pts), 7)]

def overlaps(a, b):
    return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])

def main():
    source_bytes = SRC.read_bytes()
    manifest = load(P140 / 'sources-manifest.json')
    expected = next(x for x in manifest['retained_sources'] if x['path'].endswith('geoBoundaries-KIR-ADM1.geojson'))
    assert len(source_bytes) == expected['bytes']
    assert hashlib.sha256(source_bytes).hexdigest() == expected['sha256']
    source = json.loads(source_bytes)
    base = load(BASE)
    phoenix = load(PHX)
    archive_bytes = subprocess.check_output(['git', 'show', f'{BASELINE_COMMIT}:{MIGRATION_ARCHIVE}'], cwd=ROOT)
    archive_raw = gzip.decompress(archive_bytes)
    archive = json.loads(archive_raw)
    baseline_ids = [
        'gb:KIR:ADM1:97431129B55805139245338',
        'gb:KIR:ADM1:97431129B36644055464690',
        'gb:KIR:ADM1:97431129B35506555718846',
    ]
    retained = {}
    for fid in baseline_ids:
        if fid in base['locations']:
            retained[fid] = {
                'name': base['locations'][fid]['properties']['name'],
            'parts': [bbox({'type': 'Polygon', 'coordinates': part}) for part in base['locations'][fid]['geometry']['coordinates']],
        }
    # Scan the complete current geography directory so island-level feature IDs
    # are not inferred from the scoped #140 extract alone. This is a bbox filter.
    zones = {'Gilbert/Banaba/Tarawa': [168, -4, 178, 4],
             'Phoenix': [-178, -6, -170, -2], 'Line': [-162, 1, -155, 6]}
    geography_files = sorted((ROOT / 'data/geography').glob('part-*.json'))
    nearby_features = []
    for path in geography_files:
        part = load(path)
        for feature in part.get('features', []):
            feature_box = bbox(feature['geometry'])
            zone_hits = [name for name, zone in zones.items() if overlaps(feature_box, zone)]
            if zone_hits:
                props = feature.get('properties', {})
                nearby_features.append({'id': props.get('id'), 'name': props.get('name'),
                                        'parent_id': props.get('parent_id'), 'source_id': props.get('metadata', {}).get('source_id'),
                                        'part_file': path.name, 'bbox_wgs84': feature_box, 'zone_candidates': zone_hits,
                                        'parts': [bbox({'type': 'Polygon', 'coordinates': part}) for part in feature['geometry']['coordinates']]})
    features = []
    for feature in source['features']:
        props = feature['properties']
        parts = [bbox({'type': 'Polygon', 'coordinates': part}) for part in feature['geometry']['coordinates']]
        candidate = []
        for part_no, part_box in enumerate(parts, 1):
            part_coordinates = feature['geometry']['coordinates'][part_no - 1]
            source_vertex_count = sum(len(ring) for ring in part_coordinates)
            candidate.append({
                'source_part': part_no,
                'bbox_wgs84': part_box,
                'source_vertex_count': source_vertex_count,
                'retained_bbox_candidates': [
                    {'id': fid, 'part': i}
                    for rec in nearby_features
                    for i, rb in enumerate(rec['parts'], 1) if overlaps(part_box, rb)
                    for fid in [rec['id']]
                ],
                'phoenix_526_osm_bbox_candidates': [x['id'] for x in phoenix['locations'] if x.get('source', {}).get('bbox') and overlaps(part_box, x['source']['bbox'])],
                'phoenix_526_land_component_bbox_candidates': [
                    {'id': x['id'], 'name': x['name'], 'component': i,
                     'bbox_wgs84': land.get('bbox'), 'osm_way_ids': land.get('osm_way_ids'),
                     'osm_way_records': [w for w in x.get('osm_audit', {}).get('source_way_inventory', []) if w.get('way_id') in land.get('osm_way_ids', [])]}
                    for x in phoenix['locations']
                    for i, land in enumerate(x.get('osm_audit', {}).get('land_component_inventory', []), 1)
                    if land.get('bbox') and overlaps(part_box, land['bbox'])
                ],
                'interpretation': 'Bounding-box candidate screen only; it is not polygon intersection, island identity, administrative jurisdiction, or a boundary verdict.',
            })
        features.append({
            'name': props.get('shapeName'), 'source_shape_id': props.get('shapeID'),
            'source_feature_id': f"gb:KIR:ADM1:{props.get('shapeID')}",
            'component_count': len(parts), 'parts': candidate,
        })
    archived_id_crosswalk = []
    for source_id in baseline_ids:
        original_path = f'world/continent:Oceania/subcontinent:Micronesia/region:Kiribati/area:Kiribati/province:{source_id.rsplit(":", 1)[1]}'
        archived_rows = [x for x in archive['units'] if x.get('metadata', {}).get('original_unit_id') == original_path or x.get('id') == original_path]
        assert len(archived_rows) == 2, (source_id, len(archived_rows))
        archived_id_crosswalk.append({'current_source_id': source_id, 'original_unit_path': original_path, 'archive_records': archived_rows, 'interpretation': 'Identity/name/parent migration records only; this archive has no geometry for these locations and is explicitly undated. It is not evidence that historical territorial attributes transfer.'})
    out = {
        'packet': 'Kiribati Gilbert/Phoenix retained ADM1 source crosswalk',
        'issue': 611,
        'source': {'path': str(SRC.relative_to(ROOT)), 'bytes': len(source_bytes), 'sha256': hashlib.sha256(source_bytes).hexdigest(), 'manifest_sha256': expected['sha256']},
        'retained_baseline_commit': base['baseline_commit'],
        'archived_id_crosswalk': {'archive': {'path': MIGRATION_ARCHIVE, 'baseline_commit': BASELINE_COMMIT, 'compressed_bytes': len(archive_bytes), 'compressed_sha256': hashlib.sha256(archive_bytes).hexdigest(), 'uncompressed_bytes': len(archive_raw), 'uncompressed_sha256': hashlib.sha256(archive_raw).hexdigest(), 'kind': archive.get('kind'), 'historical_effective_year': archive.get('historical_effective_year'), 'record_transfer_policy': archive.get('record_transfer_policy'), 'units_total': len(archive['units'])}, 'subjects': archived_id_crosswalk, 'limits': 'The full archive is retained unchanged in Git and too large to copy into this packet. This extract contains the exact two identity rows per source ID; it does not assert historical geometry or attribute transfer.'},
        'retained_baseline_file': {'path': str(BASE.relative_to(ROOT)), 'sha256': hashlib.sha256(BASE.read_bytes()).hexdigest()},
        'retained_subject_component_inventory': retained,
        'current_geography_bbox_scan': {'files_scanned': len(geography_files), 'zones': zones, 'candidate_features': nearby_features,
            'interpretation': 'Bounding-box scan only. In current geographic parts, only the three listed Kiribati ADM1 feature IDs intersect these broad zones; no island-level Kiribati child ID was found. Archived migration aliases are separately inventoried; this does not search every historical claim or transfer attributes.'},
        'source_feature_component_inventory': features,
        'phoenix_526_members': [{'id': x['id'], 'name': x['name'], 'source_bbox': x['source'].get('bbox'), 'source_license': x['source'].get('license'), 'retained_archive': x['source'].get('retained_archive'), 'retained_archive_sha256': x['source'].get('retained_archive_sha256')} for x in phoenix['locations']],
        'phoenix_526_assessment': {'path': str(PHX.relative_to(ROOT)), 'bytes': PHX.stat().st_size, 'sha256': hashlib.sha256(PHX.read_bytes()).hexdigest()},
        'limits': [
            'The source polygons are not authoritative local-government boundaries.',
            'A bounding-box intersection is a candidate only, never proof of polygon overlap or island identity.',
            'Census island rows are population/statistical reporting units, not a cadastral or complete physical-island inventory.',
            'Bounding boxes do not establish exact geometry; the undated migration archive supplies identity/name/parent aliases only and has no geometry or territorial-attribute transfer authority.',
        ],
    }
    counts = {f['name']: f['component_count'] for f in features}
    assert counts == {'Gilbert Islands': 29, 'Phoenix Islands': 11, 'Line Islands': 5}, counts
    out['crosswalk_result_summary'] = {
        'Gilbert': {'source_parts': 29, 'source_parts_with_current_bbox_candidate': sum(bool(p['retained_bbox_candidates']) for f in features if f['name'] == 'Gilbert Islands' for p in f['parts']), 'source_parts_without_current_bbox_candidate': sum(not p['retained_bbox_candidates'] for f in features if f['name'] == 'Gilbert Islands' for p in f['parts']), 'interpretation': 'Candidate bounds only; remaining parts have no candidate in current geography parts, but exact polygon coverage and lineage are unresolved.'},
        'Phoenix': {'source_parts': 11, 'source_parts_with_current_remainder_bbox_candidate': sum(bool(p['retained_bbox_candidates']) for f in features if f['name'] == 'Phoenix Islands' for p in f['parts']), 'source_parts_with_526_land_bbox_candidate': sum(bool(p['phoenix_526_land_component_bbox_candidates']) for f in features if f['name'] == 'Phoenix Islands' for p in f['parts']), 'likely_kanton_source_part': 1, 'interpretation': 'Source part 1 closely bounds #526 Kanton land, strong geographic correspondence but no polygon overlay; source parts 2 and 4 are candidates for the two western retained remainder components. Seven other #526 Phoenix locations have no source-component bbox candidate.'},
        'Line': {'source_parts': 5, 'source_parts_with_current_line_bbox_candidate': sum(bool(p['retained_bbox_candidates']) for f in features if f['name'] == 'Line Islands' for p in f['parts']), 'interpretation': 'All five have bbox candidates in current Line ADM1 geometry; one source/current bbox can overlap multiple pieces, so this does not establish a one-to-one mapping.'},
    }
    assert len(CENSUS_ROWS) == 19 and len({row for _, row, _ in CENSUS_ROWS}) == 19
    out['gilbert_census_rows'] = {
        'source': 'NSO/SPC Kiribati Census Atlas 2022, Table 5, printed page 18 (source receipt in README)',
        'row_count': len(CENSUS_ROWS),
        'limits': 'These are statistical population/reporting rows; not 19 separate physical islands or authoritative boundary polygons. No one-to-one row-to-source-part assignment is claimed.',
        'rows': [
            {'division': division, 'census_row': row, 'qualification': qualification,
             'candidate_current_subject_ids': (['gb:KIR:ADM1:97431129B36644055464690'] if row == 'Banaba' else
                 ['gb:KIR:ADM1:97431129B55805139245338', 'gb:KIR:ADM1:97431129B36644055464690'] if row in ('North Tarawa', 'South Tarawa') else
                 ['gb:KIR:ADM1:97431129B55805139245338']),
             'match_status': 'candidate only; exact source-component, retained-polygon and legal-jurisdiction crosswalk unresolved'}
            for division, row, qualification in CENSUS_ROWS
        ],
    }
    (OWN / 'source-component-inventory.json').write_text(json.dumps(out, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'source_sha256': out['source']['sha256'], 'component_counts': counts, 'retained_parts': {k: len(v['parts']) for k,v in retained.items()}, 'phoenix_526_members': len(out['phoenix_526_members']), 'current_geography_files_scanned': len(geography_files), 'nearby_current_features': [x['id'] for x in nearby_features], 'archived_id_records': len(archived_id_crosswalk), 'inventory': 'source-component-inventory.json'}, indent=2))

if __name__ == '__main__':
    main()
