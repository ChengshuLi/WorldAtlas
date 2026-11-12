#!/usr/bin/env python3
"""Extract all snapshot-selected SeaVoX polygons in one pinned archive scan.

Each decision retains the single-feature GeoJSON and manifest contract. A final
index seals the complete selection and every emitted file for checkpoint reuse.
Partial attempts are never reused or overwritten.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
import tempfile
import time
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from osgeo import gdal
from decision_snapshot import read_snapshot, find_source
from map_build.execution.outputs import create_directory_exclusive, validate_fresh_output, write_json_exclusive
from extract_seavox_feature import (canonical_hash, digest, extract_features,
                                    extract_indexed_features, validate_archive, write_extraction)


def selected_basins(snapshot):
    basins = snapshot.get('basins')
    if not isinstance(basins, list):
        raise ValueError('snapshot basins must be a list')
    selected, archive_hashes = {}, set()
    for basin in basins:
        ident = basin.get('id')
        if not isinstance(ident, str) or not re.fullmatch(r'[a-z0-9_-]+', ident) or ident in selected:
            raise ValueError('basin decision IDs must be unique and safe directory names')
        if not basin.get('source_feature_id') or not re.fullmatch(r'[0-9]+', str(basin['source_feature_id'])):
            raise ValueError('SeaVoX feature ID must contain digits only')
        if not isinstance(basin.get('geometry_sha256'), str) or not re.fullmatch(r'[0-9a-f]{64}', basin['geometry_sha256']):
            raise ValueError('decision must bind a feature ID and geometry hash')
        source = find_source(snapshot, basin)
        archive_hashes.add(source['sha256'])
        selected[ident] = (basin, source)
    if len(archive_hashes) != 1:
        raise ValueError('selected basins must bind one nonempty pinned archive')
    return [selected[ident] for ident in sorted(selected)], archive_hashes.pop()


def run(archive, root, policy, policy_sha, out, *, allow_unverified=False, allow_draft=False,
        work_root=None, scan_reference=False, scalar_coordinates=False):
    started = time.perf_counter()
    if not allow_unverified:
        raise ValueError('authenticated Neon revision verification is not implemented; explicit test-only flag required')
    root, archive, policy = root.resolve(), archive.resolve(), policy.resolve()
    if not root.is_dir() or any(not path.is_relative_to(root) for path in (archive, policy)):
        raise ValueError('archive and policy must be inside an existing input root')
    out = validate_fresh_output(root, out, (archive, policy))
    snapshot = read_snapshot(policy, policy_sha, allow_draft=allow_draft)
    selected, archive_sha = selected_basins(snapshot)
    phases = {}
    before = time.perf_counter()
    shape = validate_archive(archive, archive_sha)
    phases['archive_validation'] = time.perf_counter() - before
    selection_index = {}
    # A compressed shapefile is seek-heavy. Materialize it once in this run's
    # workspace rather than repeatedly inflating ZIP prefixes through /vsizip/.
    # Archive member safety was checked above; this fresh directory contains no
    # preexisting paths and is never a persistent or cross-run source cache.
    with tempfile.TemporaryDirectory(prefix='seavox-', dir=work_root or out.parent) as workspace:
        before = time.perf_counter()
        with zipfile.ZipFile(archive) as zipped:
            zipped.extractall(workspace)
        phases['archive_materialization'] = time.perf_counter() - before
        before = time.perf_counter()
        feature_ids = [basin['source_feature_id'] for basin, _ in selected]
        if scan_reference:
            features = extract_features(archive, feature_ids, dataset=Path(workspace) / shape)
        else:
            features = extract_indexed_features(archive, feature_ids, dataset=Path(workspace) / shape,
                metrics=selection_index, geometry_hashes={str(basin['source_feature_id']): basin['geometry_sha256']
                                                          for basin, _ in selected},
                **({'scalar_coordinates': True} if scalar_coordinates else {}))
        phases['ogr_selection_and_json_decode'] = time.perf_counter() - before
    before = time.perf_counter()
    geometry_hashes = selection_index.get('geometry_sha256') or {
        ident: canonical_hash(feature['geometry']) for ident, feature in features.items()}
    for basin, _ in selected:
        actual = geometry_hashes[str(basin['source_feature_id'])]
        if actual != basin['geometry_sha256']:
            raise ValueError('archive feature geometry does not match the selected decision: ' + basin['id'] + ': ' + actual)
    phases['geometry_binding'] = time.perf_counter() - before
    gdal_version = selection_index.get('gdal_version') or gdal.VersionInfo('--version')
    # Validate all selected geometries and both input pins before creating any
    # candidate files. The final recheck below detects later source mutation.
    if digest(archive) != archive_sha or digest(policy) != policy_sha:
        raise ValueError('source archive or policy changed during extraction')
    create_directory_exclusive(out)
    entries = []
    before = time.perf_counter()
    for basin, source in selected:
        feature_started = time.perf_counter()
        folder = out / basin['id']
        manifest = write_extraction(folder, features[str(basin['source_feature_id'])], snapshot,
            policy_sha, basin, source, gdal_version,
            geometry_sha256=geometry_hashes[str(basin['source_feature_id'])])
        manifest['processing_elapsed_seconds'] = time.perf_counter() - feature_started
        write_json_exclusive(folder / 'manifest.json', manifest, indent=2)
        entries.append({'decision_id': basin['id'], 'source_feature_id': str(basin['source_feature_id']),
                        'geometry_sha256': manifest['geometry_sha256'],
                        'feature_file': str((folder / 'source.geojson').relative_to(out)),
                        'feature_file_sha256': manifest['feature_file_sha256'],
                        'manifest_file': str((folder / 'manifest.json').relative_to(out)),
                        'manifest_file_sha256': digest(folder / 'manifest.json')})
    phases['feature_serialization'] = time.perf_counter() - before
    if digest(archive) != archive_sha or digest(policy) != policy_sha:
        raise ValueError('source archive or policy changed during extraction')
    index = {'schema': 'worldatlas-seavox-batch-extraction-v1',
             'status': 'completed_unverified_candidate_not_published',
             'archive_sha256': archive_sha, 'decision_snapshot_sha256': policy_sha,
             'decision_revision': snapshot['decision_revision']['id'],
             'entity_revision': snapshot['decision_revision']['entity_revision'],
             'gdal_version': gdal_version, 'feature_count': len(features), 'decision_count': len(entries),
             'selection_method': 'ogr-filtered-scan' if scan_reference else 'ogr-attribute-index-direct-fid',
             'geometry_serialization_method': ('ogr-geojson-coordinate-precision-15' if scan_reference else
                 'decision-hash-certified-native-coordinates-with-ogr-fallback-v1'),
             'selection_index': selection_index,
             'features': entries, 'processing_stages_seconds': phases,
             'processing_elapsed_seconds': time.perf_counter() - started}
    write_json_exclusive(out / 'batch-manifest.json', index, indent=2)
    return index


def main(argv=None, *, emit=print):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive', type=Path, required=True)
    p.add_argument('--input-root', type=Path, required=True)
    p.add_argument('--policy', type=Path, required=True)
    p.add_argument('--policy-sha256', required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--work-root', type=Path, help='existing workspace directory for transient archive materialization; defaults to the output parent')
    p.add_argument('--scan-reference', action='store_true', help='reference engine: scan features with the GDAL attribute filter')
    p.add_argument('--scalar-coordinate-reference', action='store_true',
                   help='retain the scalar fixed-15 candidate for exact in-process A/B tests')
    p.add_argument('--allow-unverified-snapshot', action='store_true')
    p.add_argument('--allow-draft-snapshot', action='store_true')
    args = p.parse_args(argv)
    emit(json.dumps(run(args.archive, args.input_root, args.policy, args.policy_sha256, args.out,
                         allow_unverified=args.allow_unverified_snapshot, allow_draft=args.allow_draft_snapshot,
                         work_root=args.work_root, scan_reference=args.scan_reference,
                         scalar_coordinates=args.scalar_coordinate_reference)))


if __name__ == '__main__':
    main()
