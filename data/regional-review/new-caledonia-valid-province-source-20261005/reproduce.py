#!/usr/bin/env python3
"""Reproduce New Caledonia province-source checks from a manually obtained archive.

The archive is restoration-only in this packet because official license records
conflict. This script never downloads it. Give --archive only after independently
confirming the applicable terms; the exact response hash is checked before use.
"""
import argparse
import hashlib
import json
import math
import subprocess
import tempfile
import zipfile
from pathlib import Path

import fiona
from fiona.transform import transform_geom
from shapely import make_valid
from shapely.geometry import shape, mapping
from shapely.validation import explain_validity

BASELINE = '1f971fef3ed24f4ddc3e3c41caac00db567caea5'
ARCHIVE_SHA256 = '66363268e37d5f58c9e49864ea29ef11ecf518f4d24b09b31daa98bcc6c6e59d'
ARCHIVE_BYTES = 25287153
SUBJECTS = {'NCL-559': 'PROVINCE_NORD', 'NCL-1259': 'PROVINCE_SUD',
            'NCL-1258': 'PROVINCE_DES_ILES'}
GEOREP = {
    'NCL-559': ('data/regional-review/regional-review-1aa97b490604ea4e/sources/new-caledonia-province-parts/province-nord.geojson',
                'ab352991c7095df611ec40e79ff652fd4346070c4e725e689a1eed5f9c2fea66'),
    'NCL-1259': ('data/regional-review/regional-review-1aa97b490604ea4e/sources/new-caledonia-province-parts/province-sud.geojson',
                'c85d11f69e68c8a091ee7edc372212777952b897b3010082ba3af1d2774d5c85'),
    'NCL-1258': ('data/regional-review/regional-review-1aa97b490604ea4e/sources/new-caledonia-province-parts/province-des-iles.geojson',
                '5a5ff8fac68b4a28c90ebedc65ba8deff91b0971582f7bb5a8cd32202db962b2'),
}
PART28_SHA256 = '2aab2f36aeeb651ee8e6cc656e9541ad14e2ced2ea8160e8700ad4dc950c379d'
HIERARCHY_SHA256 = '568301690ef231a85856666b57876a5efe8d8c7c6e671a56d81307b2dc28b80b'
TARGET_CRS = '+proj=laea +lat_0=-21.5 +lon_0=165 +datum=WGS84 +units=m +no_defs'
LEGAL_COMMUNES = {
    'BELEP', 'POUM', 'OUEGOA', 'POUEBO', 'HIENGHENE', 'TOUHO', 'POINDIMIE',
    'PONERIHOUEN', 'HOUAILOU', 'CANALA', 'KOUMAC', 'KAALA_GOMEN', 'KOUAOUA',
    'VOH', 'KONE', 'POUEMBOUT', 'ILE_DES_PINS', 'MONT_DORE', 'NOUMEA',
    'DUMBEA', 'PAITA', 'BOULOUPARI', 'LA_FOA', 'MOINDOU', 'SARRAMEA', 'FARINO',
    'BOURAIL', 'THIO', 'YATE', 'MARE', 'LIFOU', 'OUVEA', 'POYA',
}


def git_bytes(repo, commit, path):
    return subprocess.check_output(['git', '-C', str(repo), 'show', f'{commit}:{path}'])


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def projected(geometry, source_crs):
    return shape(transform_geom(source_crs, TARGET_CRS, mapping(geometry), precision=-1))


def source_mapping_matches(expected, observed):
    """Accept only an exact subject-to-source feature mapping."""
    return dict(expected) == dict(observed)


def compare(a, b):
    inter = a.intersection(b).area
    union = a.union(b).area
    delta = a.symmetric_difference(b).area
    return {'jaccard': inter / union, 'symmetric_difference_km2': delta / 1e6}


def run(repo, archive):
    archive = Path(archive)
    raw_archive = archive.read_bytes()
    if len(raw_archive) != ARCHIVE_BYTES or digest(raw_archive) != ARCHIVE_SHA256:
        raise ValueError('BDADMIN-NC source archive size/hash mismatch')
    if not zipfile.is_zipfile(archive):
        raise ValueError('BDADMIN-NC source is not a readable ZIP')

    part28 = git_bytes(repo, BASELINE, 'data/geography/part-28.json')
    if digest(part28) != PART28_SHA256:
        raise ValueError('Pinned subject file mismatch')
    atlas = {f.get('id', f.get('properties', {}).get('id')): f
             for f in json.loads(part28)['features']}
    if set(SUBJECTS) - set(atlas):
        raise ValueError('Pinned Atlas subjects are incomplete')
    hierarchy_raw = git_bytes(repo, BASELINE, 'data/hierarchy.json')
    if digest(hierarchy_raw) != HIERARCHY_SHA256:
        raise ValueError('Pinned hierarchy file mismatch')
    hierarchy = {node['id']: node for node in json.loads(hierarchy_raw)}
    parents = {}
    for subject_id in SUBJECTS:
        node_id = atlas[subject_id]['properties']['parent_id']
        node = hierarchy.get(node_id)
        if (not node or node.get('level') != 'province' or
                node.get('name') != atlas[subject_id]['properties']['name'] or
                node.get('parent_id') != 'framework:area:new-caledonia:42bf5323d811'):
            raise ValueError(f'Unexpected province parent for {subject_id}')
        parents[subject_id] = {'province_node': node_id, 'area_parent': node['parent_id'], 'level': node['level']}
    if len({row['area_parent'] for row in parents.values()}) != 1:
        raise ValueError('The three province nodes do not share the pinned New Caledonia parent area')

    with tempfile.TemporaryDirectory(prefix='worldatlas-bdadmin-') as temp:
        with zipfile.ZipFile(archive) as zf:
            if zf.testzip() is not None:
                raise ValueError('BDADMIN-NC ZIP CRC check failed')
            zf.extractall(temp)
        gdb = Path(temp) / 'BDADMIN-NC.gdb'
        layers = fiona.listlayers(str(gdb))
        if 'PROVINCES' not in layers or 'COMMUNES' not in layers:
            raise ValueError('Expected PROVINCES and COMMUNES layers are absent')
        with fiona.open(str(gdb), layer='PROVINCES') as layer:
            province_rows = list(layer)
            province_crs = layer.crs
        with fiona.open(str(gdb), layer='COMMUNES') as layer:
            commune_names = {f['properties']['nom_fichier'] for f in layer}
            commune_count = len(layer)

    province_map = {f['properties']['nom_fichier']: f for f in province_rows}
    if set(province_map) != set(SUBJECTS.values()) or len(province_rows) != 3:
        raise ValueError('Province source scope is not exactly the three declared subjects')
    if commune_count != 33 or commune_names != LEGAL_COMMUNES:
        raise ValueError('Source commune inventory differs from the 33 names in Organic Law 99-209 Article 1')

    rows = []
    area_exports = []
    area_export_dir = getattr(run, 'area_export_dir', None)
    for subject_id, feature_name in SUBJECTS.items():
        official_row = province_map[feature_name]
        official_native = shape(official_row['geometry'])
        if official_native.is_empty or not official_native.is_valid:
            raise ValueError(f'Invalid official source geometry: {feature_name}')
        official = projected(official_native, province_crs)

        if area_export_dir:
            exported = transform_geom(province_crs, 'EPSG:4326', official_row['geometry'], precision=-1)

            def strip_z(value):
                if isinstance(value, (list, tuple)):
                    if value and isinstance(value[0], (int, float)):
                        return [value[0], value[1]]
                    return [strip_z(item) for item in value]
                return value

            exported['coordinates'] = strip_z(exported['coordinates'])
            export = {'type': 'Feature', 'id': feature_name,
                      'properties': dict(official_row['properties']), 'geometry': exported}
            export_path = Path(area_export_dir) / (feature_name.lower() + '.geojson')
            export_path.parent.mkdir(parents=True, exist_ok=True)
            export_bytes = (json.dumps(export, ensure_ascii=False, separators=(',', ':')) + '\n').encode('utf-8')
            export_path.write_bytes(export_bytes)
            area_exports.append({'subject_id': subject_id, 'path': export_path.name,
                                 'bytes': len(export_bytes), 'sha256': digest(export_bytes),
                                 'crs': 'EPSG:4326', 'retention': 'local temporary only'})

        atlas_feature = atlas[subject_id]
        atlas_geom = projected(shape(atlas_feature['geometry']), 'EPSG:4326')
        source_path, source_sha = GEOREP[subject_id]
        source_raw = git_bytes(repo, BASELINE, source_path)
        if digest(source_raw) != source_sha:
            raise ValueError(f'Pinned GeoReP source mismatch: {subject_id}')
        raw_feature = json.loads(source_raw)['features'][0]
        raw_geom_wgs84 = shape(raw_feature['geometry'])
        if raw_geom_wgs84.is_valid:
            raise ValueError(f'Expected preserved invalid GeoReP original: {subject_id}')
        # Diagnostic-only clone. Original source bytes are read-only and unchanged.
        diagnostic = projected(make_valid(raw_geom_wgs84), 'EPSG:4326')
        rows.append({
            'subject_id': subject_id,
            'atlas_name': atlas_feature['properties']['name'],
            'official_source_feature': feature_name,
            'official_source_valid': official_native.is_valid,
            'official_source_geometry_type': official_native.geom_type,
            'official_source_polygon_parts': len(official_native.geoms),
            'official_source_area_km2_local_equal_area': official.area / 1e6,
            'atlas_baseline_valid': atlas_geom.is_valid,
            'georep_original_valid': raw_geom_wgs84.is_valid,
            'georep_original_reason': explain_validity(raw_geom_wgs84),
            'official_vs_natural_earth': compare(official, atlas_geom),
            'official_vs_georep_makevalid_diagnostic': compare(official, diagnostic),
            'georep_makevalid_diagnostic_vs_natural_earth': compare(diagnostic, atlas_geom),
            'natural_earth_source_id': 'natural-earth',
            'georep_source_sha256': source_sha,
        })

    correct = {row['subject_id']: row['official_source_feature'] for row in rows}
    positive_scope = source_mapping_matches(SUBJECTS, correct)
    swapped_actual = dict(correct)
    swapped_actual['NCL-559'], swapped_actual['NCL-1259'] = (
        swapped_actual['NCL-1259'], swapped_actual['NCL-559'])
    negative_swap = not source_mapping_matches(SUBJECTS, swapped_actual)
    bogus_id_rejected = 'NCL-911' not in atlas
    if not (positive_scope and negative_swap and bogus_id_rejected):
        raise ValueError('Positive/negative scope controls did not pass')

    return {
        'version': 1,
        'baseline_commit': BASELINE,
        'source_archive': {'bytes': ARCHIVE_BYTES, 'sha256': ARCHIVE_SHA256},
        'source_layers': {
            'PROVINCES': {'feature_count': len(province_rows), 'crs': 'EPSG:3163',
                          'features': sorted(province_map)},
            'COMMUNES': {'feature_count': commune_count, 'crs': 'EPSG:3163',
                         'legal_name_set_match': commune_names == LEGAL_COMMUNES,
                         'names': sorted(commune_names)},
        },
        'parent_relationships': parents,
        'area_helper_inputs': area_exports,
        'positive_controls': {'exact_subject_to_source_mapping': positive_scope,
                              'all_official_source_geometries_nonempty_valid': all(r['official_source_valid'] for r in rows)},
        'negative_controls': {'swapped_nord_sud_source_mapping_rejected': negative_swap,
                              'out_of_scope_subject_absent': bogus_id_rejected,
                              'all_three_preserved_georep_originals_are_invalid': all(not r['georep_original_valid'] for r in rows)},
        'area_method': {'crs': TARGET_CRS, 'area_method': 'planar polygon overlay in local WGS84 Lambert azimuthal equal-area projection',
                        'edge_method': 'input vertices transformed without densification; source edges retained as straight coordinate segments',
                        'limits': 'diagnostic comparison only; no shoreline completeness, inter-province topology certification, legal survey or regional approval'},
        'subjects': rows,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True, type=Path)
    parser.add_argument('--archive', required=True, type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--area-export-dir', type=Path)
    args = parser.parse_args()
    run.area_export_dir = args.area_export_dir
    result = run(args.repo, args.archive)
    encoded = json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False) + '\n'
    if args.output:
        args.output.write_text(encoded)
    print(encoded, end='')
