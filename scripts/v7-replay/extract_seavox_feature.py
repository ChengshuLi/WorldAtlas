#!/usr/bin/env python3
"""Extract a decision-selected SeaVoX polygon from a pinned compact shapefile ZIP.

Inspect mode prints a candidate geometry hash for preparing a decision. Build mode
requires the decision snapshot to bind that exact geometry and writes an isolated,
non-published feature plus provenance manifest. Neither mode modifies the archive.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import time
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from exclusive_outputs import create_directory_exclusive, write_json_exclusive, create_text_exclusive
from decision_snapshot import read_snapshot, find_basin, find_source
from seavox_properties import feature_id as read_feature_id


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def validate_archive(path, expected_sha256):
    if digest(path) != expected_sha256:
        raise ValueError('source archive hash mismatch')
    with zipfile.ZipFile(path) as z:
        names = [x.filename for x in z.infolist() if not x.is_dir()]
        if len(set(names)) != len(names) or any(PurePosixPath(n).is_absolute() or '..' in PurePosixPath(n).parts for n in names):
            raise ValueError('unsafe or duplicate archive member')
        shapes = [n for n in names if n.lower().endswith('.shp')]
        if len(shapes) != 1:
            raise ValueError('archive must contain one shapefile')
        stem = shapes[0][:-4]
        if any(stem + ext not in names for ext in ('.shx', '.dbf', '.prj')):
            raise ValueError('archive is missing a shapefile component')
        return shapes[0]


def extract_feature(archive, feature_id):
    # Restrict filter syntax: no user-provided SQL is passed through.
    feature_id = str(feature_id)
    if not re.fullmatch(r'[0-9]+', feature_id):
        raise ValueError('SeaVoX feature ID must contain digits only')
    cmd = ['ogr2ogr', '-f', 'GeoJSON', '/vsistdout/', '/vsizip/' + str(archive),
           '-where', "mrgid_sr = '" + feature_id + "'", '-t_srs', 'EPSG:4326',
           '-lco', 'COORDINATE_PRECISION=15']
    data = json.loads(subprocess.run(cmd, check=True, capture_output=True).stdout)
    features = data.get('features', []) if data.get('type') == 'FeatureCollection' else []
    if len(features) != 1 or read_feature_id(features[0].get('properties')) != feature_id:
        raise ValueError('archive must contain exactly one matching SeaVoX feature')
    feature = features[0]
    if feature.get('geometry', {}).get('type') not in ('Polygon', 'MultiPolygon'):
        raise ValueError('selected feature must be a polygon')
    return feature


def main():
    processing_started=time.perf_counter()
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive', type=Path, required=True)
    p.add_argument('--input-root', type=Path, required=True)
    p.add_argument('--inspect-feature', help='candidate feature ID; print its geometry hash without writing output')
    p.add_argument('--archive-sha256', help='required in inspect mode')
    p.add_argument('--policy', type=Path); p.add_argument('--policy-sha256'); p.add_argument('--decision-id')
    p.add_argument('--out', type=Path, help='new directory outside input root, required in build mode')
    p.add_argument('--allow-unverified-snapshot', action='store_true', help='test only; snapshot acceptance is not authenticated here')
    p.add_argument('--allow-draft-snapshot', action='store_true', help='research only: allow explicitly draft Neon evidence')
    args = p.parse_args()
    root = args.input_root.resolve(); archive = args.archive.resolve()
    if not root.is_dir() or not archive.is_relative_to(root):
        raise ValueError('archive must be inside an existing input root')
    if args.inspect_feature is not None:
        if not args.archive_sha256 or any((args.policy, args.policy_sha256, args.decision_id, args.out)):
            raise ValueError('inspect mode needs only archive hash and feature ID')
        validate_archive(archive, args.archive_sha256)
        feature = extract_feature(archive, args.inspect_feature)
        print(json.dumps({'status':'unbound_candidate', 'archive_sha256':args.archive_sha256,
                          'source_feature_id':str(args.inspect_feature), 'geometry_sha256':canonical_hash(feature['geometry'])}))
        return
    if not args.allow_unverified_snapshot:
        raise ValueError('authenticated Neon revision verification is not implemented; explicit test-only flag required')
    if not all((args.policy, args.policy_sha256, args.decision_id, args.out)):
        raise ValueError('build mode requires policy, its hash, decision ID, and output')
    policy = args.policy.resolve(); out = args.out.resolve()
    if not policy.is_relative_to(root) or out.is_relative_to(root) or root.is_relative_to(out):
        raise ValueError('policy must be inside input root and output outside it')
    snapshot = read_snapshot(policy, args.policy_sha256, allow_draft=args.allow_draft_snapshot)
    basin = find_basin(snapshot, args.decision_id); source = find_source(snapshot, basin)
    if not basin.get('source_feature_id') or not basin.get('geometry_sha256'):
        raise ValueError('decision must bind a feature ID and geometry hash')
    validate_archive(archive, source['sha256'])
    feature = extract_feature(archive, basin['source_feature_id'])
    geometry_hash = canonical_hash(feature['geometry'])
    if geometry_hash != basin['geometry_sha256']:
        raise ValueError('archive feature geometry does not match the selected decision: ' + geometry_hash)
    gdal_version = subprocess.run(['ogr2ogr', '--version'], check=True, capture_output=True, text=True).stdout.strip()
    create_directory_exclusive(out)
    feature_path = out/'source.geojson'
    with create_text_exclusive(feature_path) as f:
        json.dump({'type':'FeatureCollection','features':[feature]}, f, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)
    manifest = {'schema':'worldatlas-seavox-archive-extraction-v1', 'status':'completed_unverified_candidate_not_published',
                'decision_id':args.decision_id, 'decision_snapshot_sha256':args.policy_sha256,
                'decision_revision':snapshot['decision_revision']['id'],
                'entity_revision':snapshot['decision_revision']['entity_revision'], 'source_id':basin['source_id'],
                'source_version':basin['source_version'], 'source_feature_id':str(basin['source_feature_id']),
                'archive_sha256':source['sha256'], 'geometry_sha256':geometry_hash, 'feature_file':feature_path.name,
                'feature_file_sha256':digest(feature_path), 'gdal_version':gdal_version}
    manifest['processing_elapsed_seconds']=time.perf_counter()-processing_started
    write_json_exclusive(out/'manifest.json', manifest, indent=2)
    print(json.dumps(manifest))


if __name__ == '__main__':
    main()
