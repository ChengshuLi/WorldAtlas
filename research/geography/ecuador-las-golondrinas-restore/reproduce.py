#!/usr/bin/env python3
"""Reproduce the pinned #575 baseline, geometry and neighboring-shape audit.

Requires /usr/bin/python3 with GDAL/OGR and pyproj. All repository inputs are
read as Git blobs from the immutable baseline in scope.json. --write creates
geometry-reconciliation.json exclusively inside this issue-owned directory;
--check compares without modifying any evidence.
"""
import argparse
import gzip
import hashlib
import json
import math
import pathlib
import subprocess
import sys

from osgeo import ogr, osr
from pyproj import Geod, Transformer

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCOPE = json.loads((HERE / 'scope.json').read_text(encoding='utf-8'))
BASE = SCOPE['baseline_commit']
IDENT = 'gb:ECU:ADM2:8360857B1829680752404'
OUT = HERE / 'geometry-reconciliation.json'
SOURCE_SRS = osr.SpatialReference(); SOURCE_SRS.ImportFromEPSG(4326); SOURCE_SRS.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
TARGET_SRS = osr.SpatialReference(); TARGET_SRS.ImportFromEPSG(6933); TARGET_SRS.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
TRANSFORM = osr.CoordinateTransformation(SOURCE_SRS, TARGET_SRS)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git_blob(path):
    return subprocess.check_output(['git', '-C', str(ROOT), 'show', f'{BASE}:{path}'])


def read_baseline(path, descriptors):
    if path not in descriptors:
        raise ValueError(f'Unpinned baseline file: {path}')
    raw = git_blob(path)
    desc = descriptors[path]
    if len(raw) != desc['bytes'] or sha(raw) != desc['sha256']:
        raise ValueError(f'Pinned baseline bytes differ: {path}')
    return raw


def parse_json(raw, path):
    try:
        return json.loads(raw)
    except Exception as error:
        raise ValueError(f'Invalid JSON in {path}: {error}') from error


def geom(feature):
    result = ogr.CreateGeometryFromJson(json.dumps(feature['geometry'], separators=(',', ':')))
    if result is None:
        raise ValueError(f"Cannot parse feature geometry for {feature.get('id', feature.get('properties',{}).get('shapeID'))}")
    return result


def polygon_rows(g):
    kind = g.GetGeometryName().upper()
    if kind == 'POLYGON':
        yield g
    elif kind in ('MULTIPOLYGON', 'GEOMETRYCOLLECTION'):
        for i in range(g.GetGeometryCount()):
            yield from polygon_rows(g.GetGeometryRef(i))
    else:
        raise ValueError(f'Unexpected physical geometry type {kind}')


def rings_and_points(g):
    points = 0
    rings = 0
    holes = 0
    for polygon in polygon_rows(g):
        rings += polygon.GetGeometryCount()
        holes += max(0, polygon.GetGeometryCount() - 1)
        for i in range(polygon.GetGeometryCount()):
            points += polygon.GetGeometryRef(i).GetPointCount()
    return {'polygon_components': sum(1 for _ in polygon_rows(g)),
            'rings': rings, 'interior_rings': holes, 'coordinate_count': points}


def bbox_lonlat(geometry):
    env = geometry.GetEnvelope()  # OGR order is min-x,max-x,min-y,max-y
    return [env[0], env[2], env[1], env[3]]


def geometry_digest(feature):
    raw = json.dumps(feature['geometry'], ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return sha(raw)


def geodesic_area(geometry):
    """Ellipsoidal WGS84 polygon area; GeoJSON edges interpreted as lon/lat."""
    geod = Geod(ellps='WGS84')
    total = 0.0
    for polygon in polygon_rows(geometry):
        exterior = polygon.GetGeometryRef(0)
        xy = exterior.GetPoints()
        ext, _ = geod.polygon_area_perimeter([p[0] for p in xy], [p[1] for p in xy])
        area = abs(ext)
        for i in range(1, polygon.GetGeometryCount()):
            ring = polygon.GetGeometryRef(i).GetPoints()
            hole, _ = geod.polygon_area_perimeter([p[0] for p in ring], [p[1] for p in ring])
            area -= abs(hole)
        total += area
    return total


def projected(source):
    g = source.Clone()
    g.Transform(TRANSFORM)
    return g


def main():
    descriptors = {x['path']: x for x in SCOPE['baseline_files']}
    if len(descriptors) != len(SCOPE['baseline_files']):
        raise ValueError('Duplicate baseline file descriptors')
    if len(SCOPE['subjects']) != 1 or SCOPE['subjects'] != [IDENT]:
        raise ValueError('Issue scope must remain the one exact assigned location')
    if sha(json.dumps(SCOPE['subjects'], ensure_ascii=False, separators=(',', ':')).encode()) != SCOPE['subjects_sha256_sorted_json_array']:
        raise ValueError('Issue subject fingerprint mismatch')
    subprocess.check_output(['git', '-C', str(ROOT), 'cat-file', '-e', f'{BASE}^{{commit}}'])

    baseline = {path: read_baseline(path, descriptors) for path in descriptors}
    hierarchy = parse_json(baseline['data/hierarchy.json'], 'hierarchy')
    by_hierarchy = {x['id']: x for x in hierarchy}
    index = parse_json(baseline['data/world-index.json'], 'world-index')
    if sha(baseline['data/hierarchy.json']) != SCOPE['hierarchy_sha256']:
        raise ValueError('Hierarchy pin mismatch')
    grid = parse_json(baseline['data/canonical-grid/manifest.json'], 'canonical grid')
    if (grid.get('hierarchy_sha256') != SCOPE['hierarchy_sha256'] or
            grid.get('footprints_sha256') != SCOPE['footprints_sha256']):
        raise ValueError('Canonical-grid release pins differ from scope')
    cert = parse_json(baseline['data/macro-foundation/macro-certificate.json'], 'macro certificate')
    if (sha(baseline['data/macro-foundation/macro-certificate.json']) != SCOPE['macro_certificate_sha256'] or
            cert.get('release', {}).get('id') != SCOPE['release'] or cert.get('regional_interiors_approved') is not False):
        raise ValueError('Macro certificate/research-only status mismatch')
    handoffs = json.loads(gzip.decompress(baseline['data/macro-foundation/regional-handoffs.json.gz']))
    region = next((x for x in handoffs['regions'] if x.get('region_id') == SCOPE['region_id']), None)
    if not region or region['envelope'].get('geometry_sha256') != SCOPE['frozen_region_geometry_sha256'] or region['envelope'].get('member_location_ids_sha256') != SCOPE['frozen_region_member_ids_sha256']:
        raise ValueError('Frozen regional scope pins mismatch')
    members = json.loads(gzip.decompress(baseline['data/macro-foundation/current-membership-inventory.json.gz']))
    by_member = {x['id']: x for x in members}

    # Follow every ordinary world-index part; do not infer a containing part.
    occurrences = []
    feature = None
    feature_path = None
    current_country = []
    for rel in index['parts']:
        path = 'data/' + rel
        raw = read_baseline(path, descriptors)
        part = parse_json(raw, path)
        for candidate in part.get('features', []):
            props = candidate.get('properties', {})
            if candidate.get('id') == IDENT:
                occurrences.append(path)
                feature, feature_path = candidate, path
            if candidate.get('id', '').startswith('gb:ECU:ADM2:'):
                current_country.append(candidate)
    if occurrences != [SCOPE['subject_file']] or feature is None:
        raise ValueError(f'Exact subject must occur once in its pinned containing file, got {occurrences}')
    if feature_path != SCOPE['subject_file']:
        raise ValueError('Actual containing file differs from the scope record')

    chain = []
    seen = {IDENT}
    parent = feature['properties'].get('parent_id')
    while parent:
        if parent in seen or parent not in by_member or parent not in by_hierarchy:
            raise ValueError(f'Invalid or incomplete parent chain at {parent}')
        seen.add(parent)
        inv = by_member[parent]
        unit = by_hierarchy[parent]
        if (inv.get('name'), inv.get('level'), inv.get('parent_id')) != (unit.get('name'), unit.get('level'), unit.get('parent_id')):
            raise ValueError(f'Hierarchy/inventory disagreement at {parent}')
        chain.append({'id': parent, 'name': inv['name'], 'level': inv['level'], 'parent_id': inv.get('parent_id')})
        parent = inv.get('parent_id')
    expected = [
        'framework:province:imbabura:5b3789120dfb',
        'framework:area:ecuador:4b56c159dc75',
        SCOPE['region_id'], SCOPE['subcontinent_id'], SCOPE['continent_id']]
    if [x['id'] for x in chain] != expected:
        raise ValueError('Complete current parent chain differs from the issue handoff')

    packet = 'data/regional-review/regional-review-a1f74bfb55fcb8c1/'
    old_scope = parse_json(baseline[packet + 'scope.json'], 'parent issue scope')
    old_sources = parse_json(baseline[packet + 'sources.json'], 'parent source registry')
    if IDENT not in old_scope.get('member_location_ids', []):
        raise ValueError('Subject absent from its completed parent review')
    src_path = packet + 'sources/geoboundaries-ECU-ADM2-2019.geojson.gz'
    source_gzip = baseline[src_path]
    source_raw = gzip.decompress(source_gzip)
    source_doc = parse_json(source_raw, 'retained 2019 geoBoundaries bytes')
    shape_id = IDENT.split(':')[-1]
    source_matches = [x for x in source_doc.get('features', []) if x.get('properties', {}).get('shapeID') == shape_id]
    if len(source_matches) != 1:
        raise ValueError(f'Original source ID must occur exactly once, got {len(source_matches)}')
    source_feature = source_matches[0]

    source_roster = parse_json(baseline[packet + 'sources/ecu-admin2-official-roster.json'], 'retained 2023 INEC/OCHA roster')
    current_roster = parse_json(baseline[packet + 'sources/ecu-admin2-gazetteer-2024.json'], 'retained 2024 INEC/OCHA gazetteer')
    rows_2023 = source_roster.get('rows', [])
    rows_2024 = current_roster.get('rows', [])
    row_2023 = [x for x in rows_2023 if x.get('ADM2_PCODE') == 'EC9001']
    rows_2024_exact = [x for x in rows_2024 if x.get('ADM2_PCODE') == 'EC9001' or x.get('ADM2_ES') == 'Las Golondrinas']
    if len(rows_2023) != 224 or len(row_2023) != 1 or len(rows_2024) != 223 or rows_2024_exact:
        raise ValueError('Official INEC/OCHA source vintage crosswalk changed')

    source_geo = geom(source_feature)
    current_geo = geom(feature)
    if not source_geo.IsValid() or not current_geo.IsValid():
        raise ValueError('Do not calculate overlay metrics for invalid source/current input')
    source_area_geo = projected(source_geo)
    current_area_geo = projected(current_geo)
    intersection = source_area_geo.Intersection(current_area_geo)
    symmetric_difference = source_area_geo.SymDifference(current_area_geo)
    if intersection is None or symmetric_difference is None:
        raise ValueError('OGR source/current overlay failed')

    # Independent known-point axis control (EPSG:4326 GeoJSON is lon,lat).
    ogr_source = osr.SpatialReference(); ogr_source.ImportFromEPSG(4326); ogr_source.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    ogr_target = osr.SpatialReference(); ogr_target.ImportFromEPSG(6933); ogr_target.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    ogr_transform = osr.CoordinateTransformation(ogr_source, ogr_target)
    p_ogr = ogr_transform.TransformPoint(-73.0, 5.0)
    p_pyproj = Transformer.from_crs('EPSG:4326', 'EPSG:6933', always_xy=True).transform(-73.0, 5.0)
    point_delta = math.hypot(p_ogr[0] - p_pyproj[0], p_ogr[1] - p_pyproj[1])
    wrong_source = osr.SpatialReference(); wrong_source.ImportFromEPSG(4326); wrong_source.SetAxisMappingStrategy(osr.OAMS_AUTHORITY_COMPLIANT)
    wrong_transform = osr.CoordinateTransformation(wrong_source, ogr_target)
    wrong = wrong_transform.TransformPoint(-73.0, 5.0)
    wrong_separation = math.hypot(wrong[0] - p_ogr[0], wrong[1] - p_ogr[1])
    if point_delta > 0.001 or wrong_separation < 1_000_000:
        raise ValueError('Coordinate-axis positive/negative control failed')

    source_geod = geodesic_area(source_geo)
    current_geod = geodesic_area(current_geo)
    source_equal_area = source_area_geo.GetArea()
    current_equal_area = current_area_geo.GetArea()
    if max(abs(source_geod - source_equal_area) / source_geod,
           abs(current_geod - current_equal_area) / current_geod) > 0.003:
        raise ValueError('Independent WGS84 ellipsoidal/equal-area comparison exceeded 0.3%')

    neighbours = []
    for candidate in current_country:
        if candidate['id'] == IDENT or candidate.get('geometry', {}).get('type') not in ('Polygon', 'MultiPolygon'):
            continue
        other = projected(geom(candidate))
        overlap = current_area_geo.Intersection(other).GetArea()
        shared = current_area_geo.Boundary().Intersection(other.Boundary()).Length()
        if overlap > 0.1 or shared > 1.0:
            props = candidate['properties']
            neighbours.append({'id': candidate['id'], 'name': props['name'],
                               'parent_id': props.get('parent_id'),
                               'shared_boundary_length_km_epsg6933': round(shared / 1000, 6),
                               'areal_overlap_m2_epsg6933': round(overlap, 6)})
    neighbours.sort(key=lambda x: x['id'])

    source_components = []
    for i in range(source_geo.GetGeometryCount() if source_geo.GetGeometryName().upper() == 'MULTIPOLYGON' else 1):
        component = source_geo.GetGeometryRef(i) if source_geo.GetGeometryName().upper() == 'MULTIPOLYGON' else source_geo
        component_projected = projected(component)
        source_components.append({'index': i, 'area_m2_epsg6933': component_projected.GetArea(),
                                  'source_bounds_lonlat': bbox_lonlat(component)})

    output = {
        'version': 1,
        'issue': 575,
        'baseline_commit': BASE,
        'subject': {'id': IDENT, 'name': feature['properties']['name'], 'containing_file': feature_path,
                    'containing_file_sha256': descriptors[feature_path]['sha256'],
                    'source_shape_id': shape_id,
                    'source_geometry_canonical_json_sha256': geometry_digest(source_feature),
                    'current_geometry_canonical_json_sha256': geometry_digest(feature)},
        'scope': {'subject_count': len(SCOPE['subjects']), 'subject_ids_sha256': SCOPE['subjects_sha256_sorted_json_array'],
                  'parent_review_subjects': old_scope['location_count'], 'source_2019_features': len(source_doc['features']),
                  'source_file_sha256_compressed': sha(source_gzip), 'source_file_bytes_compressed': len(source_gzip),
                  'source_file_sha256_uncompressed': sha(source_raw), 'source_file_bytes_uncompressed': len(source_raw),
                  'source_feature_occurrences': len(source_matches)},
        'parent_chain': [{'id': IDENT, 'name': feature['properties']['name'], 'level': 'location',
                          'parent_id': feature['properties'].get('parent_id')}] + chain,
        'administrative_source_vintage_comparison': {
            'inec_ocha_2023_roster_rows': len(rows_2023), 'code_EC9001_matches': len(row_2023),
            'code_EC9001_row': row_2023[0], 'inec_ocha_2024_gazetteer_rows': len(rows_2024),
            '2024_name_or_code_matches': len(rows_2024_exact)},
        'geometry_method': {'source_crs': 'EPSG:4326', 'coordinate_order': 'longitude, latitude',
                            'measurement_crs': 'EPSG:6933 World Equidistant Cylindrical / equal area',
                            'axis_policy': 'OSR OAMS_TRADITIONAL_GIS_ORDER',
                            'independent_area_check': 'WGS84 ellipsoidal polygon area from pyproj.Geod.polygon_area_perimeter; GeoJSON edges follow straight lon/lat segments',
                            'software': {'GDAL': ogr.GetDriverCount() and __import__('osgeo').__version__,
                                         'pyproj': __import__('pyproj').__version__}},
        'axis_control': {'point_lonlat': [-73.0, 5.0], 'ogr_pyproj_difference_m': point_delta,
                         'wrong_authority_axis_separation_m': wrong_separation},
        'source_geometry': {'type': source_geo.GetGeometryName(), 'valid': bool(source_geo.IsValid()),
                            **rings_and_points(source_geo), 'area_m2_epsg6933': source_equal_area,
                            'area_m2_wgs84_geodesic': source_geod,
                            'equal_area_vs_geodesic_relative_difference': abs(source_geod-source_equal_area)/source_geod,
                            'components': source_components, 'bounds_lonlat': bbox_lonlat(source_geo)},
        'current_geometry': {'type': current_geo.GetGeometryName(), 'valid': bool(current_geo.IsValid()),
                             **rings_and_points(current_geo), 'area_m2_epsg6933': current_equal_area,
                             'area_m2_wgs84_geodesic': current_geod,
                             'equal_area_vs_geodesic_relative_difference': abs(current_geod-current_equal_area)/current_geod,
                             'bounds_lonlat': bbox_lonlat(current_geo)},
        'overlay': {'intersection_area_m2_epsg6933': intersection.GetArea(),
                    'symmetric_difference_area_m2_epsg6933': symmetric_difference.GetArea(),
                    'symmetric_difference_fraction_of_source': symmetric_difference.GetArea()/source_equal_area,
                    'source_area_outside_current_fraction': (source_equal_area-intersection.GetArea())/source_equal_area,
                    'current_area_outside_source_fraction': (current_equal_area-intersection.GetArea())/current_equal_area,
                    'relative_area_difference_absolute': abs(current_equal_area-source_equal_area)/source_equal_area},
        'current_same_country_admin2_neighbours': neighbours,
        'limitations': [
            'The 2017 statute fixes a provincial boundary segment; it is not a complete physical-land inventory or a downloadable polygon for the named Las Golondrinas location.',
            'The 2023 and 2024 INEC/OCHA tabular vintages disagree with the statute in different ways; the 2024 absence is not interpreted as physical disappearance.',
            'A coarse 2017 GSHHG centroid screen in the parent packet is not a national physical-land, island, coastline or settlement source.',
            'No 2022/2026 authoritative settlement inventory or current IGM/CONALI georeferenced parcel/boundary was retained or identified; no completeness claim is made.',
            'The listed neighbours describe the current indexed geometry only, not legal boundaries or proof of source-to-source neighbor consistency.',
            'The source/current symmetric difference is a diagnostic of two vintages; it does not identify which contour is correct and proposes no boundary edit.'
        ]
    }
    encoded = (json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True) + '\n').encode('utf-8')
    parser = argparse.ArgumentParser()
    parser.add_argument('--write', action='store_true', help='create the owned geometry output once; refuses overwrite')
    parser.add_argument('--check', action='store_true', help='compare a previously retained output byte-for-byte')
    args = parser.parse_args()
    if args.write and args.check:
        raise ValueError('Choose --write or --check')
    if args.write:
        with OUT.open('xb') as stream:
            stream.write(encoded)
            stream.flush()
    elif args.check:
        if not OUT.is_file() or OUT.read_bytes() != encoded:
            raise ValueError('Retained geometry-reconciliation.json differs from reproduced bytes')
    sys.stdout.buffer.write(encoded)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(f'ERROR: {error}', file=sys.stderr)
        raise SystemExit(1)
