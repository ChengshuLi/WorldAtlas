#!/usr/bin/env python3
"""Reproduce French Polynesia RGPF export provenance and five-subject sensitivity.

Reads immutable DAF inputs and frozen atlas/source outputs. Generated Shapefile
exports are confined to the caller's managed-slot .scratch directory; only this
owned packet receives the compact JSON result.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import zipfile

import numpy as np
import pyproj
from pyproj import CRS, Geod, datadir, database
from pyproj.transformer import TransformerGroup
from shapely import STRtree, union_all
from shapely.geometry import shape
from shapely.ops import transform as transform_geometry
from evidence.geometry import canonical_land, land_area_m2

ROOT = Path(__file__).resolve().parents[3]
OWNED = Path(__file__).resolve().parent
BASE = ROOT / 'data/regional-review/french-polynesia-group-boundaries-20261005'
SOURCE = BASE / 'source'
SCRATCH = ROOT / '.scratch/french-polynesia-1294'
SUBJECTS = {
    'PYF-4963': {'group_id': 1, 'name': 'Windward Islands', 'parent': 'framework:province:windward-islands:f00645bd9827'},
    'PYF-4964': {'group_id': 2, 'name': 'Leeward Islands', 'parent': 'framework:province:leeward-islands:f1d53af78fed'},
    'PYF-4965': {'group_id': 5, 'name': 'Tuamotu-Gambier', 'parent': 'framework:province:tuamotu-gambier:f6a7d4ec9817'},
    'PYF-4966': {'group_id': 4, 'name': 'Austral Islands', 'parent': 'framework:province:austral-islands:280986970614'},
    'PYF-4967': {'group_id': 3, 'name': 'Marquesas Islands', 'parent': 'framework:province:marquesas-islands:0beb7fe5d3cd'},
}
ZIP_HASHES = {
    'loc-ile.zip': '5018fa62ff269ae5b93502218213ce57baa36f31fcbf9d12b47bd36e12a6e29b',
    'loc-groupe-ile.zip': '3f71d87855a6d46885396b6802ccfa19f559ca4b9876f6480cd122fcba42d6fb',
    'loc-commune-associee.zip': '29230c18487385f84ca480e9b2c921ea389f848663a4a9574e77b9cbbf40db7b',
}
POSITIVE = {1: 'Tahiti', 2: 'Bora Bora', 3: 'Nuku Hiva', 4: 'Tubuai', 5: 'Mangareva'}
NEGATIVE_IDS = ['61', '122', '128']
MAPSHAPER_VERSION = '0.6.121'


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha(path: Path) -> str:
    return sha(path.read_bytes())


def load(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path: Path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n', encoding='utf-8')


def run_checked(args, cwd: Path):
    result = subprocess.run(args, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError(f'command failed ({result.returncode}): {args!r}\n{result.stdout}')
    return result.stdout


def safe_extract(zip_path: Path, out: Path):
    out.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as archive:
        for item in archive.infolist():
            candidate = Path(item.filename)
            if candidate.is_absolute() or '..' in candidate.parts:
                raise ValueError(f'unsafe archive member: {item.filename!r}')
        archive.extractall(out)


def mapshaper(node: str, js: Path, args: list[str]):
    return run_checked([node, str(js), *args], ROOT)


def points(value):
    if isinstance(value, list) and len(value) >= 2 and all(isinstance(v, (int, float)) for v in value[:2]):
        yield value
    elif isinstance(value, list):
        for child in value:
            yield from points(child)


def metric_set(atlas_geom, source_features, transformer=None):
    atlas = canonical_land(atlas_geom)
    source_geoms = []
    for feature in source_features:
        geom = shape(feature['geometry'])
        if transformer is not None:
            geom = transform_geometry(transformer.transform, geom)
        source_geoms.append(canonical_land(geom))
    source = canonical_land(union_all(source_geoms))
    intersection = canonical_land(atlas.intersection(source))
    merged = canonical_land(atlas.union(source))
    atlas_area = land_area_m2(atlas)
    source_area = land_area_m2(source)
    intersection_area = land_area_m2(intersection)
    union_area = land_area_m2(merged)
    return {
        'atlas_land_area_m2': round(atlas_area, 2),
        'daf_island_union_area_m2': round(source_area, 2),
        'intersection_area_m2': round(intersection_area, 2),
        'daf_land_covered_by_atlas': round(intersection_area / source_area, 8),
        'atlas_land_covered_by_daf': round(intersection_area / atlas_area, 8),
        'intersection_over_union': round(intersection_area / union_area, 8),
        'assigned_island_feature_count': len(source_features),
    }


def assignment(features, admin_features, transformer=None):
    admin_geoms = []
    admin_ids = []
    for feature in admin_features:
        geom = shape(feature['geometry'])
        if transformer is not None:
            geom = transform_geometry(transformer.transform, geom)
        admin_geoms.append(geom)
        admin_ids.append(int(feature['properties']['id_groupe_']))
    tree = STRtree(admin_geoms)
    assigned, unassigned, ties = {}, [], []
    for feature in features:
        geom = shape(feature['geometry'])
        if transformer is not None:
            geom = transform_geometry(transformer.transform, geom)
        candidates = tree.query(geom, predicate='intersects')
        overlaps = [(admin_ids[int(i)], geom.intersection(admin_geoms[int(i)]).area) for i in candidates]
        positive = [(group_id, area) for group_id, area in overlaps if area > 0]
        if not positive:
            unassigned.append(str(feature['properties']['id_ile']))
            continue
        positive.sort(key=lambda x: (-x[1], x[0]))
        if len(positive) > 1 and abs(positive[0][1] - positive[1][1]) <= 1e-14:
            ties.append(str(feature['properties']['id_ile']))
        assigned[str(feature['properties']['id_ile'])] = positive[0][0]
    return assigned, sorted(unassigned, key=int), sorted(ties, key=int)


def operation_summary(transformer):
    data = transformer.to_json_dict()
    found = []
    def walk(value):
        if isinstance(value, dict):
            if value.get('type') == 'Transformation':
                found.append({k: value[k] for k in ('name', 'id', 'method', 'parameters', 'accuracy', 'scope', 'area', 'bbox', 'remarks') if k in value})
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)
    walk(data)
    return {
        'description': transformer.description,
        'accuracy_m': transformer.accuracy,
        'proj_pipeline': transformer.definition,
        'transformations': found,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--node', default='node', help='Node 24 executable')
    parser.add_argument('--mapshaper-js', default=str(SCRATCH / 'mapshaper/node_modules/mapshaper/bin/mapshaper'))
    args = parser.parse_args()
    node = shutil.which(args.node) or args.node
    mapshaper_js = Path(args.mapshaper_js).resolve()
    if not mapshaper_js.is_file():
        raise FileNotFoundError(f'Mapshaper script missing: {mapshaper_js}')
    SCRATCH.mkdir(parents=True, exist_ok=True)
    extracted = SCRATCH / 'extract'
    safe_extract(SOURCE / 'loc-ile.zip', extracted / 'islands')
    safe_extract(SOURCE / 'loc-groupe-ile.zip', extracted / 'groups')
    island_shp = extracted / 'islands/loc_ile.shp'
    group_shp = extracted / 'groups/loc_groupe_ile.shp'
    version = run_checked([node, str(mapshaper_js), '-version'], ROOT).strip()
    if version != MAPSHAPER_VERSION:
        raise AssertionError(f'Mapshaper version changed: {version}')
    info = run_checked([node, str(mapshaper_js), '-i', str(group_shp.relative_to(ROOT)), '-info'], ROOT)
    crs_match = re.search(r'^CRS:\s+(.+)$', info, flags=re.M)
    if not crs_match:
        raise AssertionError('Mapshaper -info did not report source CRS')
    mapshaper_crs = crs_match.group(1).strip()

    raw_admin_path = SCRATCH / 'admin-divisions.reproduced.geojson'
    raw_islands_path = SCRATCH / 'all-islands.reproduced.geojson'
    projected_islands_path = SCRATCH / 'all-islands-proj-wgs84.reproduced.geojson'
    mapshaper(node, mapshaper_js, ['-i', str(group_shp.relative_to(ROOT)), '-filter', 'type_group == "DIVISION_ADMINISTRATIVE"', '-o', 'format=geojson', str(raw_admin_path.relative_to(ROOT))])
    mapshaper(node, mapshaper_js, ['-i', str(island_shp.relative_to(ROOT)), '-o', 'format=geojson', str(raw_islands_path.relative_to(ROOT))])
    mapshaper(node, mapshaper_js, ['-i', str(island_shp.relative_to(ROOT)), '-proj', 'wgs84', '-o', 'format=geojson', str(projected_islands_path.relative_to(ROOT))])

    frozen_admin = file_sha(SOURCE / 'admin-divisions.geojson')
    if file_sha(raw_admin_path) != frozen_admin:
        raise AssertionError('Mapshaper reproduction no longer matches retained admin-divisions output')
    for group_id in range(1, 6):
        out = SCRATCH / f'island-group-{group_id}.reproduced.geojson'
        mapshaper(node, mapshaper_js, ['-i', str(island_shp.relative_to(ROOT)), '-join', 'data/regional-review/french-polynesia-group-boundaries-20261005/source/admin-divisions.geojson', 'largest-overlap', 'fields=id_groupe_', '-filter', f'id_groupe_ == {group_id}', '-o', 'format=geojson', str(out.relative_to(ROOT))])
        retained = SOURCE / f'island-group-{group_id}.geojson'
        if file_sha(out) != file_sha(retained):
            raise AssertionError(f'Mapshaper assignment/export differs from preserved group {group_id}')

    raw_islands_json, proj_islands_json = load(raw_islands_path), load(projected_islands_path)
    raw_islands = raw_islands_json['features']
    projected_by_id = {str(f['properties']['id_ile']): f for f in proj_islands_json['features']}
    if len(raw_islands) != 128 or len(projected_by_id) != 128:
        raise AssertionError('Expected the 128 complete DAF island/atoll/bank source objects')
    pyproj_group = TransformerGroup(CRS.from_epsg(4687), CRS.from_epsg(4326), always_xy=True)
    if len(pyproj_group.transformers) != 2 or not pyproj_group.best_available or pyproj_group.unavailable_operations:
        raise AssertionError('Expected both EPSG RGPF-to-WGS 84 operations to be available')
    op1, op2 = pyproj_group.transformers
    geod = Geod(ellps='WGS84')
    max_mapshaper_degree_delta = 0.0
    mapshaper_changed_vertices = 0
    max_mapshaper_displacement_m = 0.0
    max_op1_displacement_m = 0.0
    max_mapshaper_to_op1_m = 0.0
    op1_changed_vertices = 0
    vertex_count = 0
    for feature in raw_islands:
        island_id = str(feature['properties']['id_ile'])
        original = list(points(feature['geometry']['coordinates']))
        projected = list(points(projected_by_id[island_id]['geometry']['coordinates']))
        if len(original) != len(projected):
            raise AssertionError(f'Mapshaper changed vertex count for island {island_id}')
        coordinates = np.asarray(original, dtype='float64')
        proj_coordinates = np.asarray(projected, dtype='float64')
        lon, lat = coordinates[:, 0], coordinates[:, 1]
        p_lon, p_lat = proj_coordinates[:, 0], proj_coordinates[:, 1]
        out_lon, out_lat = op1.transform(lon, lat, errcheck=True)
        delta_deg = np.maximum(np.abs(lon - p_lon), np.abs(lat - p_lat))
        mapshaper_changed_vertices += int(np.count_nonzero(delta_deg))
        max_mapshaper_degree_delta = max(max_mapshaper_degree_delta, float(delta_deg.max(initial=0)))
        mapshaper_dist = geod.inv(lon, lat, p_lon, p_lat)[2]
        op1_dist = geod.inv(lon, lat, out_lon, out_lat)[2]
        mapshaper_op1_dist = geod.inv(p_lon, p_lat, out_lon, out_lat)[2]
        max_mapshaper_displacement_m = max(max_mapshaper_displacement_m, float(np.max(np.abs(mapshaper_dist), initial=0)))
        max_op1_displacement_m = max(max_op1_displacement_m, float(np.max(np.abs(op1_dist), initial=0)))
        max_mapshaper_to_op1_m = max(max_mapshaper_to_op1_m, float(np.max(np.abs(mapshaper_op1_dist), initial=0)))
        op1_changed_vertices += int(np.count_nonzero(np.maximum(np.abs(lon - out_lon), np.abs(lat - out_lat))))
        vertex_count += len(original)
    mapshaper_files = {
        'raw_admin_sha256': file_sha(raw_admin_path),
        'raw_admin_matches_retained_sha256': frozen_admin,
        'raw_full_islands_sha256': file_sha(raw_islands_path),
        'explicit_proj_wgs84_full_islands_sha256': file_sha(projected_islands_path),
        'joined_group_outputs_match_retained': True,
        'joined_group_output_sha256': {str(i): file_sha(SCRATCH / f'island-group-{i}.reproduced.geojson') for i in range(1, 6)},
    }

    prj_members = []
    for archive_name, member_name in [('loc-ile.zip', 'loc_ile.prj'), ('loc-groupe-ile.zip', 'loc_groupe_ile.prj'), ('loc-commune-associee.zip', 'loc_commune_associee.prj')]:
        with zipfile.ZipFile(SOURCE / archive_name) as archive:
            wkt = archive.read(member_name)
        crs = CRS.from_wkt(wkt.decode('ascii'))
        if crs.to_epsg() != 4687:
            raise AssertionError(f'{member_name} no longer resolves to EPSG:4687')
        prj_members.append({'archive': archive_name, 'member': member_name, 'bytes': len(wkt), 'sha256': sha(wkt), 'wkt_ascii': wkt.decode('ascii'), 'parsed_crs': crs.to_authority(), 'crs_name': crs.name, 'datum': crs.datum.name, 'ellipsoid': crs.ellipsoid.name, 'semi_major_m': crs.ellipsoid.semi_major_metre, 'inverse_flattening': crs.ellipsoid.inverse_flattening})
    if len({x['sha256'] for x in prj_members}) != 1:
        raise AssertionError('Three DAF archives no longer share one CRS sidecar')

    atlas_part = load(ROOT / 'data/geography/part-28.json')
    atlas = {f['properties']['id']: f for f in atlas_part['features'] if f.get('properties', {}).get('id') in SUBJECTS}
    if set(atlas) != set(SUBJECTS):
        raise AssertionError('Exact five issue subjects were not found in part-28.json')
    for subject_id, row in SUBJECTS.items():
        if atlas[subject_id]['properties'].get('parent_id') != row['parent']:
            raise AssertionError(f'Current parent changed for {subject_id}')
    old_findings = load(BASE / 'geometry-findings.json')
    old_metrics = {r['subject_id']: r for r in old_findings['subjects']}
    old_assignments = {}
    for group_id in range(1, 6):
        for feature in load(SOURCE / f'island-group-{group_id}.geojson')['features']:
            old_assignments[str(feature['properties']['id_ile'])] = int(feature['properties']['id_groupe_'])
    raw_assignment, raw_unassigned, raw_ties = assignment(raw_islands, load(raw_admin_path)['features'])
    op1_assignment, op1_unassigned, op1_ties = assignment(raw_islands, load(raw_admin_path)['features'], op1)
    stale_ids = sorted(k for k, v in old_assignments.items() if raw_assignment.get(k) != v)
    changed_assignments = sorted(k for k in set(raw_assignment) | set(op1_assignment) if raw_assignment.get(k) != op1_assignment.get(k))
    if raw_unassigned != NEGATIVE_IDS or len(old_assignments) != 125:
        raise AssertionError('Retained unassigned-source controls differ')

    sensitivity = []
    for subject_id, row in SUBJECTS.items():
        group_id = row['group_id']
        retained_group = load(SOURCE / f'island-group-{group_id}.geojson')['features']
        newly_assigned = [f for f in raw_islands if op1_assignment.get(str(f['properties']['id_ile'])) == group_id]
        raw_values = metric_set(shape(atlas[subject_id]['geometry']), retained_group)
        op1_values = metric_set(shape(atlas[subject_id]['geometry']), newly_assigned, op1)
        old = old_metrics[subject_id]
        for key in ('atlas_land_area_m2', 'daf_island_union_area_m2', 'intersection_area_m2', 'intersection_over_union'):
            if abs(raw_values[key] - old[key]) > (0.01 if key.endswith('_m2') else 1e-8):
                raise AssertionError(f'Independent raw replay does not reproduce original {subject_id}/{key}: {raw_values[key]} != {old[key]}')
        sensitivity.append({
            'subject_id': subject_id,
            'subject_name': row['name'],
            'stable_parent_id': row['parent'],
            'daf_group_id': group_id,
            'raw_interpretation': raw_values,
            'epsg_8828_position_vector': op1_values,
            'delta_m2_or_ratio': {key: round(op1_values[key] - raw_values[key], 8) for key in ('atlas_land_area_m2', 'daf_island_union_area_m2', 'intersection_area_m2', 'daf_land_covered_by_atlas', 'atlas_land_covered_by_daf', 'intersection_over_union')},
            'raw_reproduces_archived_baseline': True,
            'metric_limit': old['metric_limit'],
        })

    positive_controls = []
    for group_id, island_name in POSITIVE.items():
        found = [f for f in raw_islands if f['properties'].get('nom') == island_name]
        if len(found) != 1:
            raise AssertionError(f'Positive control does not resolve uniquely: {island_name}')
        island_id = str(found[0]['properties']['id_ile'])
        positive_controls.append({'island_name': island_name, 'source_id': island_id, 'expected_group_id': group_id, 'raw_group_id': raw_assignment.get(island_id), 'epsg_8828_group_id': op1_assignment.get(island_id), 'passed': raw_assignment.get(island_id) == group_id and op1_assignment.get(island_id) == group_id})
    negative_controls = [{'source_id': island_id, 'raw_unassigned': island_id in raw_unassigned, 'epsg_8828_unassigned': island_id in op1_unassigned} for island_id in NEGATIVE_IDS]
    if not all(x['passed'] for x in positive_controls) or not all(x['raw_unassigned'] and x['epsg_8828_unassigned'] for x in negative_controls):
        raise AssertionError('A retained source-group positive/negative control changed')

    operation_sample = []
    for name, transformer in [('EPSG:8828', op1), ('EPSG:15833', op2)]:
        x, y = transformer.transform(-149.5, -17.5, errcheck=True)
        displacement = geod.inv(-149.5, -17.5, x, y)[2]
        operation_sample.append({'operation': name, 'input_lon_lat': [-149.5, -17.5], 'output_lon_lat': [x, y], 'displacement_from_untransformed_m': round(abs(displacement), 9)})
    reversed_axis_rejected = False
    reversed_axis_error = None
    try:
        from pyproj import Transformer
        reversed_transformer = Transformer.from_crs(CRS.from_epsg(4687), CRS.from_epsg(4326), always_xy=False)
        reversed_transformer.transform(-149.5, -17.5, errcheck=True)
    except Exception as exc:
        reversed_axis_rejected = True
        reversed_axis_error = str(exc).splitlines()[0]
    if not reversed_axis_rejected:
        raise AssertionError('Negative axis-order control unexpectedly accepted longitude as latitude')

    proj_db = Path(datadir.get_data_dir()) / 'proj.db'
    original_archive_checks = {}
    for name, expected in ZIP_HASHES.items():
        actual = file_sha(SOURCE / name)
        if actual != expected:
            raise AssertionError(f'Original archive bytes changed: {name}')
        original_archive_checks[name] = {'bytes': (SOURCE / name).stat().st_size, 'sha256': actual}
    group_counts_raw = {str(g): sum(v == g for v in raw_assignment.values()) for g in range(1, 6)}
    group_counts_op1 = {str(g): sum(v == g for v in op1_assignment.values()) for g in range(1, 6)}
    result = {
        'method_id': 'french-polynesia-rgpf-export-and-sensitivity-v1',
        'issue': 1294,
        'subjects': sorted(SUBJECTS),
        'atlas_baseline_commit': run_checked(['git', 'rev-parse', 'origin/main'], ROOT).strip(),
        'source_packet_baseline_commit': '0463152556158926681120155ec2e6fd7d0d8c7f',
        'archive_hashes': original_archive_checks,
        'source_crs': {'authority': ['EPSG', '4687'], 'name': 'RGPF', 'datum': 'Reseau Geodesique de la Polynesie Francaise', 'ellipsoid': 'GRS 1980', 'sidecars': prj_members},
        'software': {'python': os.sys.version.split()[0], 'numpy': np.__version__, 'shapely': __import__('shapely').__version__, 'pyproj': pyproj.__version__, 'proj': pyproj.proj_version_str, 'epsg_database_version': database.get_database_metadata('EPSG.VERSION'), 'proj_db': {'bytes': proj_db.stat().st_size, 'sha256': file_sha(proj_db)}, 'mapshaper': version, 'node': run_checked([node, '--version'], ROOT).strip()},
        'mapshaper_export': {'input_crs_from_info': mapshaper_crs, 'default_geojson_has_crs_member': 'crs' in raw_islands_json, 'mapshaper_proj_wgs84_coordinate_count': vertex_count, 'default_vs_proj_wgs84_changed_vertices': mapshaper_changed_vertices, 'max_absolute_degree_delta': max_mapshaper_degree_delta, 'max_surface_displacement_m': max_mapshaper_displacement_m, 'max_default_output_vs_epsg_8828_displacement_m': max_op1_displacement_m, 'max_proj_wgs84_output_vs_epsg_8828_displacement_m': max_mapshaper_to_op1_m, 'epsg_8828_changed_vertices': op1_changed_vertices, 'raw_admin_and_all_five_join_outputs_match_retained_hashes': True, 'file_hashes': mapshaper_files},
        'datum_operations': {'selection_for_sensitivity': 'EPSG:8828 RGPF to WGS 84 (1), position-vector 7-parameter operation. This reproduces a supported EPSG database operation; it is not evidence that DAF or the historical export selected it.', 'group_best_available': pyproj_group.best_available, 'unavailable_operations': len(pyproj_group.unavailable_operations), 'EPSG:8828': operation_summary(op1), 'EPSG:15833': operation_summary(op2), 'sample_comparison': operation_sample},
        'source_group_assignments': {'raw_counts': group_counts_raw, 'epsg_8828_counts': group_counts_op1, 'raw_unassigned_ids': raw_unassigned, 'epsg_8828_unassigned_ids': op1_unassigned, 'retained_mapshaper_assignment_count': len(old_assignments), 'raw_spatial_replay_vs_retained_disagreements': stale_ids, 'changed_memberships_after_epsg_8828': changed_assignments, 'raw_tie_ids': raw_ties, 'epsg_8828_tie_ids': op1_ties, 'positive_controls': positive_controls, 'negative_controls': negative_controls, 'axis_order_negative_control': {'reversed_axis_input_rejected': reversed_axis_rejected, 'message': reversed_axis_error}},
        'subject_sensitivity': sensitivity,
        'limits': [
            'DAF is the authoritative producer for the retained 2022 GEO PF inputs; its site states that RGPF is the legal geodetic system, but no DAF export instruction for a WGS 84 transformation was found.',
            'Mapshaper reads only +proj=longlat +ellps=GRS80 from the ESRI sidecar and emits no CRS member; byte-identical RFC 7946 GeoJSON carries WGS 84 semantics despite preserving RGPF coordinate numbers.',
            'EPSG operation 8828 is a registered, supported sensitivity scenario, not a DAF-endorsed operation. Its catalog accuracy is 0.5 m to original WGS 84 Transit and its remarks say later WGS 84 realizations agree no better than 1 m.',
            'EPSG operation 15833 is a registered no-op approximation with stated +/-1 m assumption. The historical Mapshaper command did not identify/select EPSG:15833, so numerical equivalence does not prove that operation was intentionally selected.',
            'Area comparison reuses five frozen Natural Earth comparators and DAF island objects assigned by greatest planar overlap to a figurative division polygon. It is not a legal boundary, complete island roster, shoreline, surface-land, or regional approval test.',
            'DAF source feature acquisition/edit dates vary; the five administrative-group records were last edited in 2020 and asset published in 2022. The asset does not establish current 2026 boundaries or complete uninhabited/offshore membership.',
            'The DAF catalog reports Creative Commons Attribution but does not specify a license version. Attribution and source links are preserved; separate legal terms for official narrative pages were not assessed.',
        ],
    }
    output = OWNED / 'crs-sensitivity-results.json'
    write_json(output, result)
    print(json.dumps({'output': str(output.relative_to(ROOT)), 'subjects': len(sensitivity), 'mapshaper_assignments_reproduce': len(stale_ids) == 0, 'changed_group_memberships': len(changed_assignments), 'raw_unassigned': raw_unassigned, 'epsg_8828_unassigned': op1_unassigned, 'metrics': [{'id': x['subject_id'], 'raw_iou': x['raw_interpretation']['intersection_over_union'], 'epsg_8828_iou': x['epsg_8828_position_vector']['intersection_over_union'], 'delta_iou': x['delta_m2_or_ratio']['intersection_over_union']} for x in sensitivity]}, indent=2))


if __name__ == '__main__':
    main()
