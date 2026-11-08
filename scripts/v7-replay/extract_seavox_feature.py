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
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import stage_external
from exclusive_outputs import create_directory_exclusive, write_json_exclusive, create_text_exclusive, validate_fresh_output
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


def extract_features(archive, feature_ids, *, dataset=None):
    """Select every requested feature in one archive scan, preserving OGR output."""
    # Restrict filter syntax: no user-provided SQL is passed through.
    feature_ids = {str(value) for value in feature_ids}
    if not feature_ids or any(not re.fullmatch(r'[0-9]+', value) for value in feature_ids):
        raise ValueError('SeaVoX feature ID must contain digits only')
    selected = sorted(feature_ids, key=lambda value: (int(value), value))
    where = ("mrgid_sr = '" + selected[0] + "'" if len(selected) == 1 else
             'mrgid_sr IN (' + ','.join("'" + value + "'" for value in selected) + ')')
    source = str(dataset) if dataset is not None else '/vsizip/' + str(archive)
    cmd = ['ogr2ogr', '-f', 'GeoJSON', '/vsistdout/', source,
           '-where', where, '-t_srs', 'EPSG:4326',
           '-lco', 'COORDINATE_PRECISION=15']
    data = json.loads(stage_external.run(cmd, check=True, capture_output=True).stdout)
    features = data.get('features', []) if data.get('type') == 'FeatureCollection' else []
    result = {}
    for feature in features:
        ident = read_feature_id(feature.get('properties'))
        if ident not in feature_ids or ident in result:
            raise ValueError('archive must contain exactly one matching SeaVoX feature per selected ID')
        if feature.get('geometry', {}).get('type') not in ('Polygon', 'MultiPolygon'):
            raise ValueError('selected feature must be a polygon')
        result[ident] = feature
    if result.keys() != feature_ids:
        raise ValueError('archive must contain exactly one matching SeaVoX feature')
    return result


def extract_feature(archive, feature_id):
    return extract_features(archive, [feature_id])[str(feature_id)]


def geojson_coordinate(value):
    """Candidate for GDAL's fixed-15 writer, including roundoff cleanup.

    The global-coordinate cases of GDAL's intelliround are reproduced here;
    other magnitudes remain eligible for the exact, hash-checked OGR fallback.
    See GDAL_FORMATTING_LICENSE.txt and GDAL ogr/ogrutils.cpp (v3.10.3).
    """
    if abs(value) >= 1000:
        return round(value, 15)
    text = format(value, '.15f')
    size, dot = len(text), text.find('.')
    if size > 10:
        if text[-6:-1] == '00000':
            text = text[:-1]
        elif dot < size - 8 and text[-9:-2] == '0000000':
            text = text[:-8]
        else:
            cut = 6 if text[-6:-1] == '99999' else (
                9 if dot < size - 9 and text[-9:-2] == '9999999' else 0)
            if cut:
                text = text[:-cut]
                negative = text.startswith('-')
                magnitude = text.lstrip('-')
                decimals = len(magnitude) - magnitude.index('.') - 1
                digits = str(int(magnitude.replace('.', '')) + 1).zfill(decimals + 1)
                text = ('-' if negative else '') + digits[:-decimals] + '.' + digits[-decimals:]
    return float(text)


def coordinate_geometry(geometry):
    """Build a candidate at the same 15-decimal precision as the OGR writer.

    This is never trusted by rounding alone: its canonical digest must match
    the decision-bound OGR geometry or the caller uses the reference writer.
    """
    name = geometry.GetGeometryName()
    if name == 'POLYGON':
        dimension = 3 if geometry.Is3D() else 2
        return {'type': 'Polygon', 'coordinates': [
            [[geojson_coordinate(value) for value in point[:dimension]]
             for point in geometry.GetGeometryRef(i).GetPoints()]
            for i in range(geometry.GetGeometryCount())]}
    if name == 'MULTIPOLYGON':
        polygons = [coordinate_geometry(geometry.GetGeometryRef(i))
                    for i in range(geometry.GetGeometryCount())]
        if any(polygon is None for polygon in polygons):
            return None
        return {'type': 'MultiPolygon', 'coordinates': [polygon['coordinates'] for polygon in polygons]}
    return None


def extract_indexed_features(archive, feature_ids, *, dataset, metrics=None, geometry_hashes=None):
    """Index attributes without geometry, then read only the selected FIDs.

    A shapefile's ordinary filtered cursor constructs geometries before testing
    its attribute predicate. Avoid that unnecessary work while retaining OGR's
    geometry organization, coordinate transformation and GeoJSON serializer.
    """
    from osgeo import gdal, ogr, osr

    selected = {str(value) for value in feature_ids}
    if not selected or any(not re.fullmatch(r'[0-9]+', value) for value in selected):
        raise ValueError('SeaVoX feature ID must contain digits only')
    started = time.perf_counter()
    source = ogr.Open(str(dataset), 0)
    if source is None or source.GetLayerCount() != 1:
        raise ValueError('materialized archive must contain one readable shapefile layer')
    layer = source.GetLayer(0)
    definition = layer.GetLayerDefn()
    names = [definition.GetFieldDefn(i).GetName() for i in range(definition.GetFieldCount())]
    fields = [name for name in names if name.casefold() == 'mrgid_sr']
    if len(fields) != 1:
        raise ValueError('SeaVoX feature needs one unambiguous MRGID_SR field')
    field = fields[0]
    if layer.SetIgnoredFields(['OGR_GEOMETRY']) != 0:
        raise ValueError('could not build a geometry-free SeaVoX feature index')
    fids, count = {}, 0
    for feature in layer:
        count += 1
        ident = str(feature.GetField(field))
        if ident in selected:
            if ident in fids or feature.GetFID() < 0:
                raise ValueError('archive must contain exactly one matching SeaVoX feature per selected ID')
            fids[ident] = feature.GetFID()
    if fids.keys() != selected:
        raise ValueError('archive must contain exactly one matching SeaVoX feature')
    if layer.SetIgnoredFields([]) != 0:
        raise ValueError('could not enable selected SeaVoX geometries')
    original = layer.GetSpatialRef()
    if original is None:
        raise ValueError('SeaVoX shapefile has no source coordinate system')
    original = original.Clone()
    original.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    target = osr.SpatialReference()
    target.ImportFromEPSG(4326)
    target.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    transform = osr.CoordinateTransformation(original, target)
    indexed = time.perf_counter()
    result, actual_hashes = {}, {}
    certified, fallbacks = 0, 0
    for ident in sorted(selected, key=lambda value: (int(value), value)):
        feature = layer.GetFeature(fids[ident])
        if feature is None or str(feature.GetField(field)) != ident:
            raise ValueError('selected SeaVoX feature index changed')
        geometry = feature.GetGeometryRef()
        if geometry is None or geometry.Transform(transform) != 0:
            raise ValueError('selected SeaVoX geometry could not be transformed')
        expected = (geometry_hashes or {}).get(ident)
        doc_geometry, actual = None, None
        if expected:
            try:
                candidate = coordinate_geometry(geometry)
                if candidate is not None and canonical_hash(candidate) == expected:
                    doc_geometry, actual = candidate, expected
                    certified += 1
            except (ValueError, OverflowError):
                pass  # The exact reference writer handles unsupported values.
        if doc_geometry is None:
            doc_geometry = json.loads(geometry.ExportToJson(options=['COORDINATE_PRECISION=15']))
            actual = canonical_hash(doc_geometry)
            fallbacks += 1
        # ogr2ogr does not preserve native shapefile FIDs unless requested.
        # Export properties without re-encoding or parsing the large geometry.
        feature.SetFID(-1)
        feature.SetGeometry(None)
        doc = feature.ExportToJson(as_object=True)
        doc['geometry'] = doc_geometry
        if (read_feature_id(doc.get('properties')) != ident
                or doc.get('geometry', {}).get('type') not in ('Polygon', 'MultiPolygon')):
            raise ValueError('selected feature must be a matching polygon')
        result[ident] = doc
        actual_hashes[ident] = actual
    if metrics is not None:
        metrics.update({'source_record_count': count, 'selected_feature_fids': fids,
                        'gdal_version': gdal.VersionInfo('--version'),
                        'geometry_sha256': actual_hashes,
                        'hash_certified_coordinate_features': certified,
                        'ogr_geometry_fallbacks': fallbacks,
                        'attribute_index_seconds': indexed - started,
                        'selected_geometry_seconds': time.perf_counter() - indexed})
    return result


def write_extraction(out, feature, snapshot, policy_sha, basin, source, gdal_version, *, geometry_sha256=None):
    """Write the same isolated feature/provenance contract for either producer."""
    create_directory_exclusive(out)
    feature_path = out/'source.geojson'
    with create_text_exclusive(feature_path) as f:
        f.write(json.dumps({'type':'FeatureCollection','features':[feature]}, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False))
    return {'schema':'worldatlas-seavox-archive-extraction-v1', 'status':'completed_unverified_candidate_not_published',
            'decision_id':basin['id'], 'decision_snapshot_sha256':policy_sha,
            'decision_revision':snapshot['decision_revision']['id'],
            'entity_revision':snapshot['decision_revision']['entity_revision'], 'source_id':basin['source_id'],
            'source_version':basin['source_version'], 'source_feature_id':str(basin['source_feature_id']),
            'archive_sha256':source['sha256'], 'geometry_sha256':geometry_sha256 or canonical_hash(feature['geometry']),
            'feature_file':feature_path.name, 'feature_file_sha256':digest(feature_path), 'gdal_version':gdal_version}


def main(argv=None, *, emit=print):
    processing_started=time.perf_counter()
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive', type=Path, required=True)
    p.add_argument('--input-root', type=Path, required=True)
    p.add_argument('--inspect-feature', help='candidate feature ID; print its geometry hash without writing output')
    p.add_argument('--archive-sha256', help='required in inspect mode')
    p.add_argument('--policy', type=Path); p.add_argument('--policy-sha256'); p.add_argument('--decision-id')
    p.add_argument('--out', type=Path, help='fresh directory, required in build mode')
    p.add_argument('--allow-unverified-snapshot', action='store_true', help='test only; snapshot acceptance is not authenticated here')
    p.add_argument('--allow-draft-snapshot', action='store_true', help='research only: allow explicitly draft Neon evidence')
    args = p.parse_args(argv)
    root = args.input_root.resolve(); archive = args.archive.resolve()
    if not root.is_dir() or not archive.is_relative_to(root):
        raise ValueError('archive must be inside an existing input root')
    if args.inspect_feature is not None:
        if not args.archive_sha256 or any((args.policy, args.policy_sha256, args.decision_id, args.out)):
            raise ValueError('inspect mode needs only archive hash and feature ID')
        validate_archive(archive, args.archive_sha256)
        feature = extract_feature(archive, args.inspect_feature)
        emit(json.dumps({'status':'unbound_candidate', 'archive_sha256':args.archive_sha256,
                          'source_feature_id':str(args.inspect_feature), 'geometry_sha256':canonical_hash(feature['geometry'])}))
        return
    if not args.allow_unverified_snapshot:
        raise ValueError('authenticated Neon revision verification is not implemented; explicit test-only flag required')
    if not all((args.policy, args.policy_sha256, args.decision_id, args.out)):
        raise ValueError('build mode requires policy, its hash, decision ID, and output')
    policy = args.policy.resolve()
    if not policy.is_relative_to(root):
        raise ValueError('policy must be inside input root')
    out=validate_fresh_output(root,args.out,(archive,policy))
    snapshot = read_snapshot(policy, args.policy_sha256, allow_draft=args.allow_draft_snapshot)
    basin = find_basin(snapshot, args.decision_id); source = find_source(snapshot, basin)
    if not basin.get('source_feature_id') or not basin.get('geometry_sha256'):
        raise ValueError('decision must bind a feature ID and geometry hash')
    validate_archive(archive, source['sha256'])
    feature = extract_feature(archive, basin['source_feature_id'])
    geometry_hash = canonical_hash(feature['geometry'])
    if geometry_hash != basin['geometry_sha256']:
        raise ValueError('archive feature geometry does not match the selected decision: ' + geometry_hash)
    gdal_version = stage_external.run(['ogr2ogr', '--version'], check=True, capture_output=True, text=True).stdout.strip()
    manifest = write_extraction(out, feature, snapshot, args.policy_sha256, basin, source, gdal_version)
    if digest(archive)!=source['sha256'] or digest(policy)!=args.policy_sha256:
        raise ValueError('source archive or policy changed during extraction')
    manifest['processing_elapsed_seconds']=time.perf_counter()-processing_started
    write_json_exclusive(out/'manifest.json', manifest, indent=2)
    emit(json.dumps(manifest))


if __name__ == '__main__':
    main()
