"""Compare immutable geography, without repairing or approving any footprint.

Positive-area lost coverage and added pairwise overlap are review blockers.
No area threshold, snapping, MakeValid, ownership inference or water exception
is applied. The exact shapes remain available for source-backed adjudication.
This detector alone is not yet an enforced integration gate.
"""
import argparse
import gzip
import hashlib
import io
import json
import pathlib
import re
import sys

import shapely
from shapely import STRtree, union_all
from shapely.geometry import shape, mapping
from shapely.affinity import translate
from evidence.geometry import canonical_land, METHOD
from evidence.immutable import Baseline, canonical_json, descriptor, safe_path

VERSION = 'worldatlas-geographic-regression-v1'
MAX_DECODED = 32 * 1024 * 1024


def decode(raw, name, budget=None):
    if name.endswith('.gz'):
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
            raw = stream.read(MAX_DECODED + 1)
    if len(raw) > MAX_DECODED:
        raise ValueError('Decoded geography exceeds byte budget')
    if budget is not None:
        budget[0] += len(raw)
        if budget[0] > 512 * 1024 * 1024:
            raise ValueError('Aggregate decoded snapshot exceeds 512 MiB budget')
    return json.loads(raw)


def snapshot(repo, commit):
    """Pin every consumed ordinary Git blob, never mutable checkout geometry."""
    import subprocess
    if not isinstance(commit, str) or not re.fullmatch('[a-f0-9]{40}', commit):
        raise ValueError('Snapshot requires an immutable 40-character Git commit')
    index_path = 'data/world-index.json'
    raw = subprocess.check_output(['git', '-C', str(repo), 'show', commit + ':' + index_path])
    baseline = Baseline(repo, commit, [descriptor(index_path, raw)])
    files = {index_path: descriptor(index_path, raw)}
    budget = [0]

    def read(name):
        raw = baseline.read(name)
        files[name] = descriptor(name, raw)
        return decode(raw, name, budget)

    index = read(index_path)
    parts = index.get('parts')
    if not isinstance(parts, list) or not parts or len(parts) > 512 or len(set(parts)) != len(parts):
        raise ValueError('Incomplete or duplicate world-index part inventory')
    features, containing = {}, {}
    for part in parts:
        name = safe_path('data/' + safe_path(part))
        collection = read(name)
        if collection.get('type') != 'FeatureCollection' or not isinstance(collection.get('features'), list):
            raise ValueError('World-index part must be a FeatureCollection')
        for feature in collection['features']:
            identity = feature.get('id') or feature.get('properties', {}).get('id')
            if not isinstance(identity, str) or not identity or identity in features:
                raise ValueError('Missing or duplicate stable location identity')
            if feature.get('type') != 'Feature' or not isinstance(feature.get('geometry'), dict):
                raise ValueError('Missing location geometry: ' + identity)
            # Nonfinite coordinates must fail, including otherwise unchanged inputs.
            canonical_json(feature['geometry'])
            features[identity], containing[identity] = feature, name
    if not features or len(features) > 200000:
        raise ValueError('Location inventory outside bounded detector scope')
    pins = {}
    for name in ['data/hierarchy.json', 'data/canonical-grid/manifest.json',
                 'data/geographic-releases/index.json', 'data/geographic-releases/current-manifest.json']:
        value = read(name)
        pins[name] = files[name]['sha256']
        # Pointer bytes are insufficient: preserve the immutable pointed-to release too.
        if name.endswith('current-manifest.json'):
            if not isinstance(value, dict) or not isinstance(value.get('path'), str) or not re.fullmatch('[a-f0-9]{64}', value.get('sha256', '')):
                raise ValueError('Incomplete geographic release pointer')
            pointed = safe_path(value['path'])
            if not pointed.startswith('data/'):
                pointed = 'data/geographic-releases/' + pointed
            read(pointed)
            if value.get('sha256') != files[pointed]['sha256']:
                raise ValueError('Geographic release pointer hash mismatch')
    return {'commit': commit, 'features': features, 'containing': containing,
            'files': [files[name] for name in sorted(files)], 'pins': pins}


def geometry_hash(feature):
    return hashlib.sha256(canonical_json(feature['geometry'])).hexdigest()


def polygon_parts(geometry):
    if geometry.geom_type == 'Polygon':
        if not geometry.is_empty and geometry.area > 0:
            yield geometry
    elif hasattr(geometry, 'geoms'):
        for member in geometry.geoms:
            yield from polygon_parts(member)


def prepare(features, vintage, validated=None, original=None):
    result, errors = {}, []
    for identity in sorted(features):
        try:
            # Shared versioned method unwraps short edges, aligns holes and splits
            # the date line. Unsupported/invalid geometry cannot be MakeValid'd.
            if validated is not None and identity in validated and identity in original and geometry_hash(features[identity]) == geometry_hash(original[identity]):
                result[identity] = validated[identity]
            else:
                result[identity] = canonical_land(shape(features[identity]['geometry']))
        except (ValueError, shapely.errors.ShapelyError, TypeError, KeyError, AttributeError) as error:
            errors.append({'vintage': vintage, 'location_id': identity, 'reason': str(error),
                           'original_geometry': features[identity]['geometry']})
    return result, errors


def report_feature(kind, geometry, ids, before, after, changed):
    point = list(geometry.representative_point().coords)[0]
    return {'type': 'Feature', 'geometry': mapping(geometry), 'properties': {
        'kind': kind, 'location_ids': sorted(ids), 'changed_location_ids': sorted(set(ids) & set(changed)),
        'coordinate': list(point), 'bounds': list(geometry.bounds),
        'source_geometry_area_square_degrees': geometry.area,
        'physical_classification': 'unverified',
        'before': [{'location_id': identity, 'geometry': mapping(before[identity])}
                   for identity in sorted(ids) if identity in before],
        'after': [{'location_id': identity, 'geometry': mapping(after[identity])}
                  for identity in sorted(ids) if identity in after]}}


def neighbors(tree, identities, geometry):
    """Include the other side of the date line in an actionable neighbor list."""
    queries = [geometry]
    if geometry.bounds[0] <= -180:
        queries.append(translate(geometry, xoff=360))
    if geometry.bounds[2] >= 180:
        queries.append(translate(geometry, xoff=-360))
    return {identities[int(index)] for query in queries for index in tree.query(query, predicate='intersects')}


def compare(before_features, after_features):
    changed = sorted(identity for identity in set(before_features) | set(after_features)
                     if identity not in before_features or identity not in after_features
                     or geometry_hash(before_features[identity]) != geometry_hash(after_features[identity]))
    base = {'changed_location_ids': changed, 'affected_neighbor_ids': [],
            'geometry_errors': [], 'findings': {'type': 'FeatureCollection', 'features': []},
            'coverage_gained': {'type': 'FeatureCollection', 'features': []}}
    before, before_errors = prepare(before_features, 'baseline')
    if not changed and not before_errors:
        return {**base, 'status': 'no-footprint-change', 'regressions': 0}
    after, after_errors = prepare(after_features, 'candidate', before, before_features)
    errors = before_errors + after_errors
    if errors:
        return {**base, 'status': 'blocked-invalid-or-unsupported-geometry',
                'geometry_errors': errors, 'regressions': None}

    # The index contains all locations. A changed polygon can expose a gap with
    # an unchanged neighbor outside an issue's declared subject list.
    ids_before, ids_after = sorted(before), sorted(after)
    tree_before = STRtree([before[i] for i in ids_before])
    tree_after = STRtree([after[i] for i in ids_after])
    affected = set(changed)
    footprint = union_all([g for identity in changed for g in [before.get(identity), after.get(identity)] if g is not None])
    for piece in polygon_parts(footprint):
        affected.update(neighbors(tree_before, ids_before, piece))
        affected.update(neighbors(tree_after, ids_after, piece))
    occupied_before = union_all([before[i] for i in sorted(affected) if i in before])
    occupied_after = union_all([after[i] for i in sorted(affected) if i in after])
    findings, gained = [], []
    for kind, geometry, output in [
        ('lost-previous-coverage', occupied_before.difference(occupied_after), findings),
        ('gained-coverage', occupied_after.difference(occupied_before), gained)]:
        for piece in polygon_parts(geometry):
            # Preserve all positive-area shapes; no sliver-size filtering.
            nearby = neighbors(tree_before, ids_before, piece)
            nearby.update(neighbors(tree_after, ids_after, piece))
            output.append(report_feature(kind, piece, nearby, before, after, changed))

    pairs = set()
    for identity in changed:
        if identity not in after:
            continue
        for index in tree_after.query(after[identity], predicate='intersects'):
            other = ids_after[int(index)]
            if identity != other:
                pairs.add(tuple(sorted([identity, other])))
    for left, right in sorted(pairs):
        overlap = after[left].intersection(after[right])
        old = before[left].intersection(before[right]) if left in before and right in before else union_all([])
        for piece in polygon_parts(overlap.difference(old)):
            findings.append(report_feature('new-pair-overlap', piece, [left, right], before, after, changed))
    for output in [findings, gained]:
        output.sort(key=lambda f: canonical_json(f))
    return {**base, 'status': 'regressions-found' if findings else 'no-new-regression',
            'regressions': len(findings), 'affected_neighbor_ids': sorted(affected - set(changed)),
            'findings': {'type': 'FeatureCollection', 'features': findings},
            'coverage_gained': {'type': 'FeatureCollection', 'features': gained}}


def inspect(repo, baseline_commit, candidate_commit):
    baseline = snapshot(repo, baseline_commit)
    candidate = baseline if baseline_commit == candidate_commit else snapshot(repo, candidate_commit)
    result = compare(baseline['features'], candidate['features'])
    for vintage, snap in [('baseline', baseline), ('candidate', candidate)]:
        identities = sorted(set(result['changed_location_ids']) | set(result['affected_neighbor_ids']) |
                            {error['location_id'] for error in result['geometry_errors']})
        result[vintage] = {key: snap[key] for key in ['commit', 'files', 'pins']}
        result[vintage]['locations'] = [{'location_id': i, 'containing_file': snap['containing'][i],
            'original_geometry_sha256': geometry_hash(snap['features'][i]),
            'original_geometry': snap['features'][i]['geometry'],
            'properties': snap['features'][i].get('properties', {})} for i in identities if i in snap['features']]
    return {'version': 1, 'method_id': VERSION, 'geometry_helper': METHOD,
        'software': {'shapely': shapely.__version__, 'geos': shapely.geos_version_string},
        'coordinates': 'longitude, latitude; WGS84; short straight source edges; antimeridian split',
        'positive_area_threshold_square_degrees': 0, 'snapping_applied': False,
        'existing_gap_policy': 'Only previously covered land loss is a regression; unchanged gaps remain in the independent audit.',
        'integration_enforced': False, 'published': False,
        'limits': ['Diagnostic geometry only; neither coverage nor loss establishes real land/water, a rightful province or historical ownership.',
                   'Source-backed intentional coastline changes require separate exact-geometry review. This detector has no exception or automatic repair path.',
                   'No new raster, hierarchy, crosswalk, release or content certification; existing release and publication gates still apply.'],
        **result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=pathlib.Path, default=pathlib.Path(__file__).resolve().parents[1])
    parser.add_argument('--baseline', required=True)
    parser.add_argument('--candidate', required=True)
    parser.add_argument('--out', required=True, type=pathlib.Path)
    args = parser.parse_args()
    report = inspect(args.repo, args.baseline, args.candidate)
    raw = canonical_json(report)
    if len(raw) > MAX_DECODED:
        raise ValueError('Report exceeds bounded output size; split the coordinated migration for review')
    if any(parent.is_symlink() for parent in [args.out, *args.out.absolute().parents]):
        raise ValueError('Symlink output path is forbidden')
    with args.out.open('xb') as stream:
        stream.write(raw)
    print(json.dumps({'status': report['status'], 'regressions': report['regressions'],
        'changed_locations': len(report['changed_location_ids']), 'report': descriptor(str(args.out.name), raw)}))
    return 0 if report['status'] in ['no-footprint-change', 'no-new-regression'] else 1


if __name__ == '__main__':
    sys.exit(main())
