#!/usr/bin/env python3
"""Reproduce bounded DAF island-to-subdivision crosswalk and area diagnostics."""
from __future__ import annotations
import csv, hashlib, json, subprocess, zipfile
from pathlib import Path
from shapely.geometry import shape
from shapely import union_all
from evidence.geometry import canonical_land, land_area_m2

ROOT = Path(__file__).resolve().parents[3]
OWNED = Path(__file__).resolve().parent
SRC = OWNED / 'source'
BASELINE = '0463152556158926681120155ec2e6fd7d0d8c7f'
PINS = {
    'data/geography/part-28.json': '2aab2f36aeeb651ee8e6cc656e9541ad14e2ced2ea8160e8700ad4dc950c379d',
    'data/hierarchy.json': '568301690ef231a85856666b57876a5efe8d8c7c6e671a56d81307b2dc28b80b',
    'data/regional-review/regional-review-14a242c4cb0781a7/source/natural-earth/ne_10m_admin_1_scoped-admin-features.json': 'dd3f4a5683c713fd89c00b41748d89771f905ef236feaacb7887818085f3d96e',
}
SUBDIVISIONS = {
    'PYF-4963': {'group_id': 1, 'name': 'Windward Islands', 'daf_name': 'Iles Du Vent', 'parent': 'framework:province:windward-islands:f00645bd9827', 'control_island': 'Tahiti'},
    'PYF-4964': {'group_id': 2, 'name': 'Leeward Islands', 'daf_name': 'Iles Sous Le Vent', 'parent': 'framework:province:leeward-islands:f1d53af78fed', 'control_island': 'Bora Bora'},
    'PYF-4965': {'group_id': 5, 'name': 'Tuamotu-Gambier', 'daf_name': 'Tuamotu - Gambier', 'parent': 'framework:province:tuamotu-gambier:f6a7d4ec9817', 'control_island': 'Mangareva'},
    'PYF-4966': {'group_id': 4, 'name': 'Austral Islands', 'daf_name': 'Australes', 'parent': 'framework:province:austral-islands:280986970614', 'control_island': 'Tubuai'},
    'PYF-4967': {'group_id': 3, 'name': 'Marquesas Islands', 'daf_name': 'Marquises', 'parent': 'framework:province:marquesas-islands:0beb7fe5d3cd', 'control_island': 'Nuku Hiva'},
}
ZIP_HASHES = {
    'loc-ile.zip': '5018fa62ff269ae5b93502218213ce57baa36f31fcbf9d12b47bd36e12a6e29b',
    'loc-groupe-ile.zip': '3f71d87855a6d46885396b6802ccfa19f559ca4b9876f6480cd122fcba42d6fb',
    'loc-commune-associee.zip': '29230c18487385f84ca480e9b2c921ea389f848663a4a9574e77b9cbbf40db7b',
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob(path: str) -> bytes:
    return subprocess.check_output(['git', '-C', str(ROOT), 'show', f'{BASELINE}:{path}'])


def load(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def geometry_parts(geometry):
    polygons = [geometry] if geometry.geom_type == 'Polygon' else list(geometry.geoms)
    return {
        'polygon_components': len(polygons),
        'rings': sum(1 + len(p.interiors) for p in polygons),
        'vertices': sum(len(p.exterior.coords) + sum(len(r.coords) for r in p.interiors) for p in polygons),
    }


def write_json(path: Path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n', encoding='utf-8')


def main():
    for path, expected in PINS.items():
        actual = digest(git_blob(path))
        assert actual == expected, f'baseline pin mismatch: {path}: {actual}'
    archive_inventory = {'method_id': 'daf-zip-member-hashes-v1', 'archives': []}
    for filename, expected in ZIP_HASHES.items():
        archive = SRC / filename
        actual = digest(archive.read_bytes())
        assert actual == expected, f'original DAF archive hash mismatch: {filename}: {actual}'
        members = []
        with zipfile.ZipFile(archive) as zf:
            for info in sorted(zf.infolist(), key=lambda item: item.filename):
                data = zf.read(info.filename)
                members.append({'path': info.filename, 'bytes': len(data), 'sha256': digest(data), 'crc32': f'{info.CRC:08x}'})
        archive_inventory['archives'].append({'path': filename, 'bytes': archive.stat().st_size, 'sha256': actual, 'members': members})
    write_json(SRC / 'archive-inventory.json', archive_inventory)

    part = json.loads(git_blob('data/geography/part-28.json'))
    baseline_locations = {f.get('properties', {}).get('id'): f for f in part['features']}
    subjects = {id: baseline_locations[id] for id in SUBDIVISIONS}
    assert set(subjects) == set(SUBDIVISIONS)
    for id, row in SUBDIVISIONS.items():
        assert subjects[id]['properties']['parent_id'] == row['parent'], f'parent changed: {id}'

    daf_groups = load(SRC / 'admin-divisions.geojson')['features']
    group_by_id = {int(f['properties']['id_groupe_']): f for f in daf_groups}
    assert len(group_by_id) == 5
    for row in SUBDIVISIONS.values():
        f = group_by_id[row['group_id']]['properties']
        assert f['nom'] == row['daf_name'] and f['type_group'] == 'DIVISION_ADMINISTRATIVE'
        assert f['date_acq'].startswith('2018-09-05') and f['last_edite'].startswith('2020-03-09')

    islands = list(csv.DictReader((SRC / 'island-attributes.csv').open(encoding='utf-8-sig', newline='')))
    group_features = {i: load(SRC / f'island-group-{i}.geojson')['features'] for i in range(1, 6)}
    joined = []
    for group_id, features in group_features.items():
        for feature in features:
            assert int(feature['properties']['id_groupe_']) == group_id
            joined.append(feature)
    assert len(islands) == 128 and len(joined) == 125
    island_ids = [str(row['id_ile']) for row in islands]
    assert len(set(island_ids)) == 128
    assigned_by_id = {str(f['properties']['id_ile']): f for f in joined}
    island_by_id = {str(row['id_ile']): row for row in islands}
    assert set(assigned_by_id).issubset(island_by_id)
    by_id = assigned_by_id

    associations = list(csv.DictReader((SRC / 'commune-associations.csv').open(encoding='utf-8-sig', newline='')))
    municipal_codes = {}
    for row in associations:
        municipal_codes.setdefault(str(row['id_ile']), set()).add(str(row['code_subdi']))
    expected_municipal_counts = {1: 5, 2: 8, 3: 13, 4: 7, 5: 84}
    for group_id, expected in expected_municipal_counts.items():
        ids = {key for key, codes in municipal_codes.items() if str(group_id) in codes}
        assert len(ids) == expected, f'municipal crosswalk count mismatch for subdivision {group_id}'

    name_by_group = {v['group_id']: v['name'] for v in SUBDIVISIONS.values()}
    control_ids = {v['group_id']: v['control_island'] for v in SUBDIVISIONS.values()}
    counts = {group_id: 0 for group_id in name_by_group}
    members_by_group = {group_id: [] for group_id in name_by_group}
    unmatched = sorted(set(island_ids) - set(assigned_by_id), key=int)
    membership_rows = []
    for island_id in island_ids:
        p = island_by_id[island_id]
        f = assigned_by_id.get(island_id)
        assigned = int(f['properties']['id_groupe_']) if f else None
        if assigned in counts:
            counts[assigned] += 1
            members_by_group[assigned].append(island_id)
        codes = sorted(municipal_codes.get(island_id, set()), key=int)
        membership_rows.append({
            'daf_island_id': island_id,
            'island_name': p['nom'],
            'island_type': p['type_ile'],
            'physical_archipelago': p['archipel'],
            'division_polygon_id': assigned if assigned in counts else '',
            'division_polygon_name': name_by_group.get(assigned, ''),
            'municipal_subdivision_codes': ';'.join(codes),
            'daf_surface_km2': p.get('suface_eme', ''),
            'island_source_acquired': p.get('date_acq', ''),
            'island_source_last_edited': p.get('last_edite', ''),
        })
    expected_polygon_counts = {1: 5, 2: 8, 3: 16, 4: 10, 5: 86}
    assert counts == expected_polygon_counts, f'polygon assignment counts mismatch: {counts}'
    assert len(unmatched) == 3
    expected_unmatched = {'122', '128', '61'}
    assert set(unmatched) == expected_unmatched, f'unmatched source IDs differ: {unmatched}'
    for group_id, island_name in control_ids.items():
        found = [f for f in joined if f['properties']['nom'] == island_name and int(f['properties'].get('id_groupe_') or 0) == group_id]
        assert found, f'positive control failed: {island_name}'
    assert '2' in municipal_codes['61'] and '61' not in by_id
    assert not municipal_codes.get('122') and not municipal_codes.get('128')

    with (OWNED / 'island-membership.csv').open('w', encoding='utf-8', newline='') as out:
        writer = csv.DictWriter(out, fieldnames=list(membership_rows[0]), lineterminator='\n')
        writer.writeheader(); writer.writerows(sorted(membership_rows, key=lambda r: (r['physical_archipelago'], r['island_name'], r['daf_island_id'])))

    natural_earth = load(ROOT / 'data/regional-review/regional-review-14a242c4cb0781a7/source/natural-earth/ne_10m_admin_1_scoped-admin-features.json')
    ne = {f['properties']['adm1_code']: f for f in natural_earth['features'] if f['properties'].get('adm1_code') in SUBDIVISIONS}
    results = []
    for id, row in SUBDIVISIONS.items():
        atlas = canonical_land(shape(subjects[id]['geometry']))
        source_features = [f for f in joined if int(f['properties'].get('id_groupe_') or 0) == row['group_id']]
        source = union_all([canonical_land(shape(f['geometry'])) for f in source_features])
        intersection = atlas.intersection(source)
        total_atlas = land_area_m2(atlas)
        total_source = land_area_m2(source)
        overlap = land_area_m2(intersection)
        total_union = land_area_m2(atlas.union(source))
        ne_parts = shape(ne[id]['geometry'])
        results.append({
            'subject_id': id,
            'subject_name': row['name'],
            'daf_division_id': row['group_id'],
            'daf_division_feature': row['daf_name'],
            'atlas_polygon_components': geometry_parts(atlas)['polygon_components'],
            'natural_earth_source_components': geometry_parts(ne_parts)['polygon_components'],
            'daf_assigned_island_feature_count': len(source_features),
            'daf_commune_crosswalk_island_count': len({key for key, codes in municipal_codes.items() if str(row['group_id']) in codes}),
            'atlas_land_area_m2': round(total_atlas, 2),
            'daf_island_union_area_m2': round(total_source, 2),
            'intersection_area_m2': round(overlap, 2),
            'daf_land_covered_by_atlas': round(overlap / total_source, 8),
            'atlas_land_covered_by_daf': round(overlap / total_atlas, 8),
            'intersection_over_union': round(overlap / total_union, 8),
            'metric_limit': 'DAF objects assigned only by largest polygon overlap to the figurative division polygons; municipal-only and unassigned objects are not included in this area union. Diagnostic, not completeness or legal-boundary proof.',
        })

    # Pairwise positive-area overlap is a negative control for subdivision separation.
    pairs = []
    for a in range(1, 6):
        for b in range(a + 1, 6):
            ga = canonical_land(shape(group_by_id[a]['geometry']))
            gb = canonical_land(shape(group_by_id[b]['geometry']))
            shared = ga.intersection(gb)
            overlap = land_area_m2(shared) if not shared.is_empty and shared.geom_type in ('Polygon', 'MultiPolygon') else 0.0
            pairs.append({'group_a': a, 'group_b': b, 'overlap_area_m2': round(overlap, 4)})
    assert all(x['overlap_area_m2'] == 0 for x in pairs), 'DAF subdivision division polygons overlap'

    findings = {
        'method_id': 'daf-island-crosswalk-and-geometry-v1',
        'baseline_commit': BASELINE,
        'daf_island_source_object_count': len(islands),
        'daf_group_assigned_count': sum(counts.values()),
        'daf_unassigned_object_count': len(unmatched),
        'daf_group_assignment_counts': {name_by_group[k]: counts[k] for k in sorted(counts)},
        'daf_commune_crosswalk_unique_island_counts': {name_by_group[k]: expected_municipal_counts[k] for k in sorted(expected_municipal_counts)},
        'unassigned_daf_island_ids': sorted(unmatched, key=int),
        'unassigned_daf_island_names': [island_by_id[k]['nom'] for k in sorted(unmatched, key=int)],
        'positive_controls': [{'island': control_ids[k], 'daf_division_id': k, 'passed': True} for k in sorted(control_ids)],
        'negative_controls': {'exact_unassigned_ids': sorted(expected_unmatched, key=int), 'division_pairwise_overlap_area_m2': pairs, 'all_divisions_disjoint': True},
        'comparison_method': {
            'version': 'worldatlas-evidence-geometry-v1',
            'helper_version': 'worldatlas-evidence-geometry-v1',
            'axis_order': 'longitude-latitude',
            'crs': 'EPSG:4326',
            'area_method': 'WGS84 straight-source-edge ellipsoidal integral',
            'area_units': 'm2',
            'membership_method': 'Mapshaper polygon-polygon largest-overlap join, then explicit crosswalk from DAF commune-association id_ile/code_subdi attributes',
            'software': 'Mapshaper 0.6.121; Python 3.12; NumPy 2.3.5; Shapely 2.1.2; pyproj 3.7.2',
        },
        'subjects': results,
        'limits': [
            'DAF GEO PF is a 2022-published snapshot; island feature acquisition/edit dates vary, and the five group rows were last edited in 2020.',
            'The DAF administrative-group layer is explicitly figurative; its geometry is not treated as authoritative legal boundary precision.',
            'The municipal association crosswalk covers mapped municipal island IDs, not every uninhabited object or all emergent surface.',
            'Three island/reef objects do not overlap the five DAF administrative polygons. Motu One (Bellinghausen) is nevertheless linked to Maupiti/code_subdi 2 in the municipal association table.',
            'Area ratios are comparison signals only; they do not establish which edge is legally or geographically correct.',
        ],
    }
    write_json(OWNED / 'geometry-findings.json', findings)
    write_json(OWNED / 'source/positive-controls.json', {'method_id': findings['method_id'], 'kind': 'positive-control', 'outcome': 'passed', 'controls': findings['positive_controls']})
    write_json(OWNED / 'source/negative-controls.json', {'method_id': findings['method_id'], 'kind': 'negative-control', 'outcome': 'passed', 'controls': findings['negative_controls']})
    print(json.dumps({'subjects': len(results), 'island_objects': len(islands), 'assigned': sum(counts.values()), 'assignment_counts': findings['daf_group_assignment_counts'], 'unassigned': findings['unassigned_daf_island_names'], 'iou': {r['subject_id']: r['intersection_over_union'] for r in results}}, indent=2))


if __name__ == '__main__':
    main()
