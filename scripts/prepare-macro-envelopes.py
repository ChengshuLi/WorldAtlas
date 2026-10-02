#!/usr/bin/env python3
"""Freeze represented macro land envelopes; do not infer source completeness."""
import argparse
import collections
import gzip
import hashlib
import json
from pathlib import Path

from shapely import STRtree, from_wkb, make_valid, normalize, prepare as prepare_geometry, to_wkb, union_all
from shapely.geometry import shape

from ellipsoidal_area import area

ROOT = Path(__file__).resolve().parents[1]
LEVELS = ('continent', 'subcontinent', 'region')
# GEOS overlay can leave sub-millimetre ribbons along independently dissolved
# copies of the same source edge. Retain their measurements; never edit land.
NUMERICAL_CORRIDOR_DEGREES = 1e-9
OVERLAY_RIBBON_CORRIDOR_DEGREES = 1e-6


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(',', ':')) + '\n')


def conserved_union(inputs):
    """Verify GEOS overlay conserves inputs, restoring any dropped components."""
    combined = union_all(inputs)
    if not combined.is_valid:
        combined = make_valid(combined)
    restoration = []
    for attempt in range(4):
        prepare_geometry(combined)
        missing = []
        for member in inputs:
            if combined.covers(member):
                continue
            difference = member.difference(combined)
            if not difference.is_empty and not difference.buffer(-NUMERICAL_CORRIDOR_DEGREES).is_empty:
                missing.append((member, difference))
        if not missing:
            return normalize(combined), restoration
        restoration.append({'iteration': attempt + 1, 'components': len(missing),
                            'restored_m2': sum(area(g) for _, g in missing)})
        # Sequentially adding the omitted land avoids repeating a failed bulk
        # cascade. No source vertex is rounded, clipped or reassigned.
        for member, _ in missing:
            combined = combined.union(member)
            if not combined.is_valid:
                combined = make_valid(combined)
    raise ValueError('Dissolution could not conserve every source territory: ' + json.dumps(restoration))


def inventory(data):
    rows = read(data / 'hierarchy.json')
    units = {u['id']: u for u in rows}
    if len(units) != len(rows):
        raise ValueError('Duplicate geographic group')
    memberships = collections.defaultdict(list)
    features = {}
    for part in read(data / 'world-index.json')['parts']:
        for feature in read(data / part)['features']:
            identity = feature['properties']['id']
            if identity in features or feature['id'] != identity:
                raise ValueError('Duplicate or mismatched location')
            geom = shape(feature['geometry'])
            if not geom.is_valid or geom.is_empty:
                raise ValueError('Invalid or empty location geometry: ' + identity)
            features[identity] = geom
            parent = feature['properties']['parent_id']
            for tier in ('province', 'area', 'region', 'subcontinent', 'continent'):
                unit = units.get(parent)
                if not unit or unit['level'] != tier:
                    raise ValueError('Incomplete location chain: ' + identity)
                if tier in LEVELS:
                    memberships[parent].append(identity)
                parent = unit['parent_id']
            if parent is not None:
                raise ValueError('Continent has a parent')
    expected = {u['id'] for u in rows if u['level'] in LEVELS}
    if expected != set(memberships):
        raise ValueError('Empty or missing macro group')
    return units, features, memberships


def prepare(data, output, baseline=None):
    data, output = data.resolve(), output.resolve()
    if data == output or data in output.parents:
        raise ValueError('Envelope output must be outside live geography')
    units, features, memberships = inventory(data)
    output.mkdir(parents=True, exist_ok=True)
    old = read(baseline / 'envelope-index.json') if baseline else None
    old_by_id = {g['id']: g for g in old['groups']} if old else {}
    geometries, groups, changes, restorations = {}, [], [], []
    ordered = sorted(memberships, key=lambda i: (-LEVELS.index(units[i]['level']), i))
    for identity in ordered:
        member_ids = sorted(memberships[identity])
        if units[identity]['level'] == 'region':
            inputs = [features[i] for i in member_ids]
        else:
            inputs = [g for i, g in geometries.items() if units[i]['parent_id'] == identity]
        try:
            geom, repaired = conserved_union(inputs)
        except ValueError as error:
            raise ValueError(identity + ': ' + str(error)) from error
        if repaired:
            restorations.append({'id': identity, 'operations': repaired})
        if not geom.is_valid or geom.is_empty:
            raise ValueError('Invalid dissolved macro envelope: ' + identity)
        geometries[identity] = geom
        raw = to_wkb(geom, byte_order=1)
        filename = sha(identity.encode())[:24] + '.wkb.gz'
        payload = gzip.compress(raw, mtime=0)
        (output / filename).write_bytes(payload)
        row = {k: units[identity][k] for k in ('id', 'name', 'level', 'parent_id')}
        row.update(path=filename, sha256=sha(payload), geometry_sha256=sha(raw),
                   member_location_ids_sha256=sha(json.dumps(member_ids, ensure_ascii=False,
                       separators=(',', ':')).encode()), locations=len(member_ids),
                   area_m2=area(geom), bounds=list(geom.bounds))
        groups.append(row)
        if baseline and identity in old_by_id:
            previous = old_by_id[identity]
            encoded = (baseline / previous['path']).read_bytes()
            if sha(encoded) != previous['sha256']:
                raise ValueError('Frozen baseline envelope asset changed')
            former = from_wkb(gzip.decompress(encoded))
            delta = geom.symmetric_difference(former)
            if not delta.is_empty and not delta.buffer(-NUMERICAL_CORRIDOR_DEGREES).is_empty:
                changes.append({'id': identity, 'difference_m2': area(delta),
                                'status': 'requires-coordinated-boundary-review'})
    overlaps, numerical_overlays = [], []
    for tier in LEVELS:
        ids = sorted(i for i in geometries if units[i]['level'] == tier)
        geoms = [geometries[i] for i in ids]
        tree = STRtree(geoms)
        for left, geom in enumerate(geoms):
            for right in tree.query(geom, predicate='intersects'):
                if right <= left:
                    continue
                shared = geom.intersection(geoms[right])
                if not shared.is_empty and shared.area > 0:
                    row = {'level': tier, 'first': ids[left], 'second': ids[right],
                                     'area_m2': area(shared), 'bounds': list(shared.bounds),
                                     'status': 'unresolved-source-overlap'}
                    if shared.buffer(-OVERLAY_RIBBON_CORRIDOR_DEGREES).is_empty:
                        row['status'] = 'overlay-ribbon-within-numerical-corridor'
                        numerical_overlays.append(row)
                    else:
                        overlaps.append(row)
    # Parent footprints must equal exactly the union of child envelopes. This
    # check proves membership coherence, not independently correct geography.
    mismatches, numerical_unions = [], []
    for identity, geom in geometries.items():
        if units[identity]['level'] == 'region':
            continue
        children = [g for i, g in geometries.items() if units[i]['parent_id'] == identity]
        if not children:
            raise ValueError('Missing macro children: ' + identity)
        conserved, _ = conserved_union(children)
        delta = geom.symmetric_difference(conserved)
        if not delta.is_empty:
            row = {'id': identity, 'difference_m2': area(delta)}
            if delta.buffer(-NUMERICAL_CORRIDOR_DEGREES).is_empty:
                numerical_unions.append(row)
            else:
                mismatches.append(row)
    summary = {'version': 1, 'hierarchy_sha256': sha((data / 'hierarchy.json').read_bytes()),
               'groups': sorted(groups, key=lambda g: g['id']), 'locations': len(features), 'source_coverage_approved': False,
               'physical_precision_verified': False,
               'scope': 'Represented land only; independently sourced scope decisions remain required.',
               'same_tier_overlaps': overlaps, 'parent_union_mismatches': mismatches,
               'numerical_overlay_ribbons': numerical_overlays,
               'numerical_parent_union_differences': numerical_unions,
               'overlay_input_conservation_restorations': restorations,
               'numerical_corridor_degrees': NUMERICAL_CORRIDOR_DEGREES,
               'overlay_ribbon_corridor_degrees': OVERLAY_RIBBON_CORRIDOR_DEGREES,
               'numerical_policy': 'Check source conservation within 1e-9 degrees. Measure and retain source-overlay ribbons contained within a 1e-6 degree corridor (at most about 0.112 m), below source and canonical-grid precision; do not alter input or output geometry.',
               'baseline_boundary_changes': changes,
               'retired_baseline_groups': sorted(set(old_by_id) - set(geometries)),
               'geometry_encoding': 'Normalized little-endian WKB, longitude/latitude, gzip mtime 0',
               'area_method': 'WGS84 ellipsoidal surface integration; not planar degree area'}
    write(output / 'envelope-index.json', summary)
    return {'groups': len(groups), 'locations': len(features), 'overlap_pairs': len(overlaps),
            'parent_union_mismatches': len(mismatches), 'baseline_changes': len(changes),
            'output': str(output), 'approved': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=ROOT / '.cache/global-macro-foundation/after')
    parser.add_argument('--output', type=Path, default=ROOT / '.cache/global-macro-envelopes')
    parser.add_argument('--baseline', type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare(args.data, args.output, args.baseline)))
