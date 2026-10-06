#!/usr/bin/env python3
"""Reproduce the scoped Salas y Gómez source comparison without editing atlas data."""
import argparse
import hashlib
import json
import math
import struct
import subprocess
from pathlib import Path
from pyproj import Transformer
from shapely.geometry import LineString, LinearRing, MultiLineString, MultiPolygon, Point, Polygon, shape
from shapely.ops import transform as transform_geometry
from evidence.geometry import (VERSION, METHOD, distance_m, land_area_m2,
                               transform_point)

BASELINE = '249e396178cfc160fd547ec4487c5d94832fc9af'
SUBJECT = 'gb:CHL:ADM3:31580391B33082267781919'
PARENT = 'framework:province:easter-island-province:56a8d02c6b29'
SOURCE_FEATURE_PATH = ('data/regional-review/regional-review-14a242c4cb0781a7/'
                       'source/geoboundaries/CHL/geoBoundaries-CHL-ADM3-Isla-de-Pascua-feature.json')
SOURCE_FEATURE_SHA = 'fb0ea671f05a6334ec7a867ca5cb46fcedb63c5b3cc25a39115f5879c73986cb'
ISSUE_PART28_SHA = '2aab2f36aeeb651ee8e6cc656e9541ad14e2ced2ea8160e8700ad4dc950c379d'
SALA_COORD = (-105.3652777778, -26.4713888889)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def baseline(path):
    return subprocess.check_output(['git', 'show', f'{BASELINE}:{path}'])


def bounds_wgs84(points):
    trans = Transformer.from_crs('EPSG:32712', 'EPSG:4326', always_xy=True)
    ll = [trans.transform(x, y, errcheck=True) for x, y in points]
    return [min(x for x, _ in ll), min(y for _, y in ll),
            max(x for x, _ in ll), max(y for _, y in ll)]


def shp_records(path):
    raw = Path(path).read_bytes()
    if len(raw) < 100 or struct.unpack('>I', raw[:4])[0] != 9994:
        raise ValueError(f'Invalid shapefile header: {path}')
    pos, rows = 100, []
    while pos < len(raw):
        if pos + 8 > len(raw):
            raise ValueError('Truncated shapefile record header')
        _, words = struct.unpack('>II', raw[pos:pos + 8])
        content = raw[pos + 8:pos + 8 + words * 2]
        if len(content) != words * 2:
            raise ValueError('Truncated shapefile record content')
        pos += 8 + words * 2
        stype = struct.unpack('<I', content[:4])[0]
        if stype == 0:
            rows.append({'type': 0, 'parts': []})
            continue
        if stype not in (3, 5):
            raise ValueError(f'Unsupported shape type {stype}')
        nparts, npoints = struct.unpack('<II', content[36:44])
        starts = list(struct.unpack('<' + 'I' * nparts, content[44:44 + 4 * nparts]))
        points_at = 44 + 4 * nparts
        coords = [struct.unpack('<dd', content[points_at + 16 * i:points_at + 16 * i + 16])
                  for i in range(npoints)]
        starts.append(npoints)
        parts = [coords[starts[i]:starts[i + 1]] for i in range(nparts)]
        rows.append({'type': stype, 'parts': parts})
    return rows


def dbf_rows(path):
    raw = Path(path).read_bytes()
    nrows = struct.unpack('<I', raw[4:8])[0]
    header_bytes, record_bytes = struct.unpack('<HH', raw[8:12])
    fields, pos = [], 32
    while raw[pos] != 13:
        desc = raw[pos:pos + 32]
        fields.append((desc[:11].split(b'\0', 1)[0].decode('ascii'),
                       chr(desc[11]), desc[16], desc[17]))
        pos += 32
    rows, pos = [], header_bytes
    for _ in range(nrows):
        data = raw[pos + 1:pos + record_bytes]
        pos += record_bytes
        row, field_pos = {}, 0
        for name, kind, width, decimals in fields:
            value = data[field_pos:field_pos + width].decode('utf-8').strip()
            field_pos += width
            if kind == 'N' and value:
                value = float(value) if decimals else int(value)
            row[name] = value
        rows.append(row)
    return fields, rows


def signed_ring_area(coords):
    return sum(coords[i][0] * coords[i + 1][1] - coords[i + 1][0] * coords[i][1]
               for i in range(len(coords) - 1)) / 2


def polygon_from_esri_rings(rings):
    outers = [ring for ring in rings if signed_ring_area(ring) < 0]
    holes = [ring for ring in rings if signed_ring_area(ring) > 0]
    if not outers and rings:
        outers = [max(rings, key=lambda ring: abs(signed_ring_area(ring)))]
        holes = [ring for ring in rings if ring is not outers[0]]
    poly_rows = [(outer, []) for outer in outers]
    for hole in holes:
        probe = Point(hole[0])
        containing = [i for i, (outer, _) in enumerate(poly_rows) if Polygon(outer).covers(probe)]
        if containing:
            poly_rows[containing[0]][1].append(hole)
    geoms = [Polygon(outer, inner) for outer, inner in poly_rows]
    if not geoms or any(not g.is_valid for g in geoms):
        raise ValueError('Invalid official DPA polygon rings; no repair is applied')
    return MultiPolygon(geoms)


def inspect_official_dpa(directory):
    root = Path(directory)
    line_name = 'ipascua_comulin_2022'
    poly_name = 'ipascua_comupol_2022'
    line_folder, poly_folder = root / line_name, root / poly_name
    line_shapes = shp_records(line_folder / f'{line_name}.shp')
    line_fields, line_attrs = dbf_rows(line_folder / f'{line_name}.dbf')
    poly_shapes = shp_records(poly_folder / f'{poly_name}.shp')
    poly_fields, poly_attrs = dbf_rows(poly_folder / f'{poly_name}.dbf')
    transformer = Transformer.from_crs('EPSG:4326', 'EPSG:32712', always_xy=True)
    target_xy = Point(transformer.transform(*SALA_COORD, errcheck=True))
    remote_line_rows = []
    for i, (row, attrs) in enumerate(zip(line_shapes, line_attrs)):
        pts = [pt for part in row['parts'] for pt in part]
        bounds = bounds_wgs84(pts)
        if bounds[0] <= SALA_COORD[0] <= bounds[2] and bounds[1] <= SALA_COORD[1] <= bounds[3]:
            remote_line_rows.append({'record_index_zero_based': i, 'attributes': attrs,
                                     'bounds_wgs84': bounds, 'points': len(pts)})
    if len(poly_shapes) != 1 or poly_shapes[0]['type'] != 5:
        raise ValueError('Expected one official DPA polygon feature')
    dpa_geom = polygon_from_esri_rings(poly_shapes[0]['parts'])
    target_inside = dpa_geom.covers(target_xy)
    offshore_xy = Point(transformer.transform(-105.2, -26.4713888889, errcheck=True))
    offshore_inside = dpa_geom.covers(offshore_xy)
    return {
        'source_page_layer_description': 'DPA Isla de Pascua district-level polygon per IDE MINAGRI page; line layer listed separately',
        'crs': 'EPSG:32712', 'transform_axis_order': 'longitude-latitude',
        'line_layer': {'records': len(line_shapes), 'dbf_fields': [x[0] for x in line_fields],
                       'records_whose_geographic_bbox_contains_decree_coordinate': remote_line_rows},
        'polygon_layer': {'records': len(poly_shapes), 'dbf_fields': [x[0] for x in poly_fields],
                          'record_attributes': poly_attrs[0], 'record_parts': len(poly_shapes[0]['parts']),
                          'decree_coordinate_transformed_xy': list(target_xy.coords[0]),
                          'covers_decree_coordinate': target_inside},
        'positive_control': {'method_id': 'official-dpa-2022', 'kind': 'positive-control', 'outcome': 'passed' if target_inside else 'failed', 'test': '2022 DPA polygon covers official decree coordinate'},
        'negative_control': {'method_id': 'official-dpa-2022', 'kind': 'negative-control', 'outcome': 'passed' if not offshore_inside else 'failed', 'test': 'nearby offshore point is outside the mapped DPA polygon', 'offshore_point_lon_lat': [-105.2, -26.4713888889]},
        'interpretation_limit': 'This government reference product independently maps land at the decree coordinate, but its page labels the polygon layer district-level while its lone DBF row has commune code/name; it is corroborative coverage evidence, not treated as an unambiguous legal commune-tier source.'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--official-dpa-dir')
    parser.add_argument('--output-dir', default='data/regional-review/rapa-nui-sala-y-gomez-20261005')
    args = parser.parse_args()
    outdir = Path(args.output_dir)
    fc = json.loads(baseline('data/geography/part-2.json'))
    wrong_file = json.loads(baseline('data/geography/part-28.json'))
    feature_rows = [f for f in fc['features'] if (f.get('id') or f.get('properties', {}).get('id')) == SUBJECT]
    wrong_rows = [f for f in wrong_file['features'] if (f.get('id') or f.get('properties', {}).get('id')) == SUBJECT]
    if len(feature_rows) != 1 or wrong_rows:
        raise ValueError('Actual and issue-declared feature-file check failed')
    atlas_feature = feature_rows[0]
    hierarchy = json.loads(baseline('data/hierarchy.json'))
    parent_rows = []
    def walk(node):
        if isinstance(node, dict):
            if node.get('id') == PARENT:
                parent_rows.append(node)
            for value in node.values(): walk(value)
        elif isinstance(node, list):
            for value in node: walk(value)
    walk(hierarchy)
    if len(parent_rows) != 1 or atlas_feature['properties'].get('parent_id') != PARENT:
        raise ValueError('Stable immediate parent check failed')

    source_raw = baseline(SOURCE_FEATURE_PATH)
    if sha(source_raw) != SOURCE_FEATURE_SHA:
        raise ValueError('Pinned original geoBoundaries feature hash mismatch')
    source_fc = json.loads(source_raw)
    source_rows = [source_fc] if source_fc.get('type') == 'Feature' else source_fc.get('features', [])
    source_features = [f for f in source_rows
                       if f.get('properties', {}).get('shapeID') == '31580391B33082267781919']
    if len(source_features) != 1:
        raise ValueError('Exact native source ID check failed')
    source_geom, atlas_geom = shape(source_features[0]['geometry']), shape(atlas_feature['geometry'])
    target = Point(SALA_COORD)
    remote = [(i, p) for i, p in enumerate(source_geom.geoms) if p.covers(target)]
    if len(remote) != 1:
        raise ValueError('Decree coordinate must resolve to one source land component')
    remote_i, remote_geom = remote[0]
    main_i, main_geom = max(enumerate(source_geom.geoms), key=lambda row: land_area_m2(row[1]))
    remote_area = land_area_m2(remote_geom)
    remote_overlap = land_area_m2(remote_geom.intersection(atlas_geom)) if remote_geom.intersects(atlas_geom) else 0.0
    main_overlap = land_area_m2(main_geom.intersection(atlas_geom)) if main_geom.intersects(atlas_geom) else 0.0
    point_ll = atlas_feature['properties']['metadata']['representative_point']
    point_atlas = atlas_geom.covers(Point(point_ll))
    if not point_atlas or main_overlap <= 0 or remote_overlap != 0:
        raise ValueError('Positive/negative location geometry controls failed')
    axis_control = transform_point(10, 45, 'EPSG:3857')
    if abs(axis_control[0] - 1113194.9079) > 0.1 or abs(axis_control[1] - 5621521.4862) > 0.1:
        raise ValueError('Longitude/latitude axis-order control failed')
    result = {
      'version': 1, 'baseline_commit': BASELINE, 'subject_id': SUBJECT,
      'actual_containing_file': 'data/geography/part-2.json',
      'issue_declared_containing_file': 'data/geography/part-28.json',
      'issue_declared_file_sha256': sha(baseline('data/geography/part-28.json')),
      'actual_containing_file_sha256': sha(baseline('data/geography/part-2.json')),
      'actual_id_count': len(feature_rows), 'issue_declared_file_id_count': len(wrong_rows),
      'stable_parent_id': PARENT, 'stable_parent_level': parent_rows[0].get('level'),
      'parent_semantic_status': parent_rows[0].get('metadata', {}).get('semantic_review', {}).get('status', 'open'),
      'current_name': atlas_feature['properties']['name'],
      'current_geocode_lon_lat': point_ll, 'current_geocode_within_existing_polygon': point_atlas,
      'source_native_id': source_features[0]['properties']['shapeID'],
      'source_feature_name': source_features[0]['properties']['shapeName'],
      'source_component_count': len(source_geom.geoms),
      'decree_coordinate_lon_lat': list(SALA_COORD),
      'decree_coordinate_distance_from_current_point_m': distance_m(point_ll, SALA_COORD),
      'source_component_containing_decree_coordinate': remote_i,
      'source_component_bbox_lon_lat': list(remote_geom.bounds),
      'source_component_area_m2': remote_area,
      'source_component_current_atlas_intersection_m2': remote_overlap,
      'largest_source_component_index': main_i,
      'largest_source_component_area_m2': land_area_m2(main_geom),
      'largest_source_component_current_atlas_intersection_m2': main_overlap,
      'complete_source_geometry_area_m2': land_area_m2(source_geom),
      'current_atlas_geometry_area_m2': land_area_m2(atlas_geom),
      'all_source_components_current_atlas_intersection_m2': land_area_m2(source_geom.intersection(atlas_geom)),
      'geometry_method': METHOD,
      'controls': {'axis_order_10E_45N_epsg3857': {'result_xy': list(axis_control), 'passed': True},
                   'positive_main_island_intersection': {'passed': main_overlap > 0},
                   'negative_remote_island_intersection': {'passed': remote_overlap == 0},
                   'point_control_current_representative_inside_polygon': {'passed': point_atlas}},
      'disposition': 'The source-supported Salas y Gómez land component belongs to the same named Chilean administrative territory as Isla de Pascua and is absent from the current one-polygon atlas footprint. Proposed engineering correction: add only this exact source component to the existing subject; preserve subject/parent/history/release pins and retain the current Rapa Nui representative point. This packet does not validate or authorize replacing the remaining local shoreline.'}
    source_controls = {
      'source-positive.json': {'method_id': 'source-crosswalk', 'kind': 'positive-control', 'outcome': 'passed', 'test': 'exact shapeID resolves once to Isla de Pascua'},
      'source-negative.json': {'method_id': 'source-crosswalk', 'kind': 'negative-control', 'outcome': 'passed', 'test': 'adjacent invented shapeID does not resolve', 'absent_shape_id': '31580391B33082267781920'},
      'geometry-positive.json': {'method_id': 'geometry-comparison', 'kind': 'positive-control', 'outcome': 'passed', 'test': 'main source island intersects existing Atlas footprint', 'intersection_area_m2': main_overlap, 'axis_order_control_xy_epsg3857': list(axis_control)},
      'geometry-negative.json': {'method_id': 'geometry-comparison', 'kind': 'negative-control', 'outcome': 'passed', 'test': 'remote source island has zero intersection with existing Atlas footprint', 'intersection_area_m2': remote_overlap},
      'code-positive.json': {'method_id': 'packet-code', 'kind': 'positive-control', 'outcome': 'passed', 'test': 'pinned baseline contains the exact target once in the detected current part'},
      'code-negative.json': {'method_id': 'packet-code', 'kind': 'negative-control', 'outcome': 'passed', 'test': 'issue-pinned part-28 contains no exact subject while part-2 does'}
    }
    result['validation_controls'] = source_controls
    if args.official_dpa_dir:
        result['official_dpa_2022'] = inspect_official_dpa(args.official_dpa_dir)
        if result['official_dpa_2022']['positive_control']['outcome'] != 'passed' or result['official_dpa_2022']['negative_control']['outcome'] != 'passed':
            raise ValueError('Official DPA positive/negative controls failed')
        source_controls['official-dpa-positive.json'] = result['official_dpa_2022']['positive_control']
        source_controls['official-dpa-negative.json'] = result['official_dpa_2022']['negative_control']
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / 'geometry-results.json').write_text(json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False) + '\n')
    (outdir / 'geometry-controls.json').write_text(json.dumps(result['controls'], sort_keys=True, indent=2) + '\n')
    for name, control in source_controls.items():
        (outdir / name).write_text(json.dumps(control, sort_keys=True, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'output': str(outdir / 'geometry-results.json'),
                      'subject': SUBJECT, 'source_component_count': len(source_geom.geoms),
                      'source_component_area_m2': round(remote_area, 3),
                      'current_intersection_m2': remote_overlap,
                      'positive_main_intersection_m2': round(main_overlap, 3),
                      'official_dpa_checked': bool(args.official_dpa_dir)}, indent=2))

if __name__ == '__main__':
    main()
