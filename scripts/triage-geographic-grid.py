"""Bounded actual-grid triage of every retained component; never boundary repair."""
import argparse
import collections
import gzip
import io
import json
import pathlib
import re
import sys

import shapely
from shapely.geometry import Point, shape

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from evidence.immutable import (Baseline, MAX_FILE_BYTES, canonical_json, descriptor,
                                deterministic_gzip, safe_path, sha256)
from geographic_grid import (VERSION, CanonicalGrid, component_sample, owner_shape_check,
                             project, cell_centre)


def decoded(raw, pin=None):
    with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
        result = stream.read(MAX_FILE_BYTES + 1)
    if len(result) > MAX_FILE_BYTES:
        raise ValueError('Decoded original exceeds ordinary-file cap')
    if pin and (len(result) != pin['uncompressed_bytes']
                or sha256(result) != pin['uncompressed_sha256']):
        raise ValueError('Decoded component pin differs')
    return result


def protocol_members(body):
    members = set()
    def walk(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key in ('member_location_ids', 'location_ids', 'subject_ids') and isinstance(child, list):
                    if any(not isinstance(v, str) for v in child):
                        raise ValueError('Protocol subject inventory must contain strings')
                    members.update(child)
                else:
                    walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)
    for raw in re.findall(r'```json\s*\n([\s\S]*?)\n```', body):
        walk(json.loads(raw))
    return members


def write_parts(out, rows):
    batch, size, outputs = [], 0, []
    def flush():
        raw = canonical_json(batch)
        if len(raw) > MAX_FILE_BYTES:
            raise ValueError('Derived table exceeds ordinary-file cap')
        encoded = deterministic_gzip(raw)
        name = f'samples-{len(outputs):03d}.json.gz'
        with (out / name).open('xb') as f:
            f.write(encoded)
        outputs.append({**descriptor(name, encoded), 'uncompressed_bytes': len(raw),
                        'uncompressed_sha256': sha256(raw)})
    for row in rows:
        n = len(canonical_json(row))
        if batch and size + n > 8 * 1024 * 1024:
            flush();batch, size = [], 0
        batch.append(row);size += n
    if batch:
        flush()
    return outputs


def triage(input_commit, inputs_path, inputs_bytes, inputs_sha256, destination):
    registry_pin = {'path': safe_path(inputs_path), 'bytes': inputs_bytes,
                    'sha256': inputs_sha256, 'hash_kind': 'file-bytes'}
    registry_source = Baseline(ROOT, input_commit, [registry_pin])
    r = json.loads(registry_source.read(inputs_path))
    if r.get('version') != 'worldatlas-grid-triage-inputs-v1':
        raise ValueError('Unsupported immutable triage registry')
    protocols = Baseline(ROOT, input_commit, [registry_pin, *r['protocol_snapshots']])
    pins = [r[k] for k in ('grid_manifest', 'grid_bounds', 'hierarchy', 'world_index',
                          'release', 'release_index', 'components_report', 'water_report')]
    pins += [*r['grid_parts'], *r['components_files'], *r['selected_current_footprint_files']]
    source = Baseline(ROOT, r['reference_commit'], pins)
    gm = json.loads(source.read(r['grid_manifest']['path']))
    current = json.loads(source.read(r['release']['path']))
    if current['sha256'] != r['release_index']['sha256']:
        raise ValueError('Release pointer does not bind the retained whole index')
    releases = json.loads(decoded(source.read(r['release_index']['path'])))['releases']
    release = max(releases, key=lambda v: v['version'])
    if (release['footprints_sha256'] != gm['footprints_sha256']
            or release['hierarchy_sha256'] != gm['hierarchy_sha256']
            or sha256(source.read(r['hierarchy']['path'])) != gm['hierarchy_sha256']):
        raise ValueError('Grid, hierarchy and current release pins differ')
    bounds_encoded = source.read(r['grid_bounds']['path'])
    if sha256(bounds_encoded) != gm['bounds']['sha256']:
        raise ValueError('Grid integer-to-location binding differs')
    bounds_rows = json.loads(decoded(bounds_encoded))
    by_integer = {v['index']: v for v in bounds_rows}
    if len(by_integer) != len(bounds_rows) or set(by_integer) != set(range(1, len(bounds_rows) + 1)):
        raise ValueError('Grid location bindings are incomplete or duplicated')
    if len(by_integer) != release['expected_counts']['location']:
        raise ValueError('Grid binding count differs from release')
    grid = CanonicalGrid(source, gm, max_owner_id=len(by_integer))
    original_report = json.loads(source.read(r['components_report']['path']))
    if original_report.get('version') != 'worldatlas-geographic-gap-components-v1':
        raise ValueError('Unsupported original component product')
    declared = {p['path']: p for p in original_report['outputs']}
    expected = {name for name in declared if pathlib.Path(name).name.startswith('components-')}
    if {p['path'] for p in r['components_files']} != expected:
        raise ValueError('Missing original component partition')
    features, original_files = {}, {}
    for pin in r['components_files']:
        if pin != declared[pin['path']]:
            raise ValueError('Component descriptor differs from retained report')
        for f in json.loads(decoded(source.read(pin['path']), pin))['features']:
            if f['id'] in features:
                raise ValueError('Duplicate stable component identity')
            features[f['id']] = f
            original_files[f['id']] = pin['path']
    if len(features) != original_report['component_count']:
        raise ValueError('Incomplete component accounting')
    fragments = [b['id'] for f in features.values() for b in f['properties']['fragment_bindings']]
    unmeasured = [identity for f in features.values() for identity in f['properties']['unmeasured_fragment_ids']]
    if (len(fragments) != original_report['fragment_count'] or len(set(fragments)) != len(fragments)
            or sorted(unmeasured) != sorted(original_report['unmeasured_fragment_ids'])):
        raise ValueError('Original fragment/measurement-unknown accounting differs')
    wanted = set(r['known_owned_cell_geometry_subjects']) | set(r['current_pilot_contact_subjects'])
    selected, selected_pins = {}, {}
    world = json.loads(source.read(r['world_index']['path']))
    if any(p['path'] not in {'data/' + name for name in world['parts']}
           for p in r['selected_current_footprint_files']):
        raise ValueError('Selected original is not part of retained world index')
    for pin in r['selected_current_footprint_files']:
        for f in json.loads(source.read(pin['path']))['features']:
            if f['id'] in wanted:
                if f['id'] in selected:
                    raise ValueError('Duplicate selected current footprint')
                selected[f['id']] = f;selected_pins[f['id']] = pin
    if set(selected) != wanted:
        raise ValueError('Declared selected current footprints missing')
    scope_members, snapshot_pins = {}, {}
    for pin in r['protocol_snapshots']:
        snapshot = json.loads(protocols.read(pin['path']))
        number = pin['issue_number']
        if snapshot['number'] != number or snapshot['state'] != 'open':
            raise ValueError('Expected existing open research issue snapshot')
        scope_members[number] = protocol_members(snapshot['body'])
        snapshot_pins[number] = pin
    samples, counts, interpretations = [], collections.Counter(), collections.Counter()
    # A single representative cell per component. This does not examine every
    # native cell and cannot establish absence of raster-only gaps elsewhere.
    for identity in sorted(features):
        f = features[identity];sample = component_sample(f, grid)
        p = f['properties'];nearby = sorted({n['id'] for n in p['diagnostic_nearby_locations']})
        sample.update(original_component_file=original_files[identity],
                      original_component_feature_sha256=sha256(canonical_json(f)),
                      fragment_bindings=p['fragment_bindings'],
                      touches_blocked_tile=p['touches_blocked_tile'],
                      touches_domain_boundary=p['touches_domain_boundary'],
                      touches_reference_shore=p['touches_reference_shore'],
                      unmeasured_fragment_ids=p['unmeasured_fragment_ids'],
                      inherited_measured_fragment_area_sum_m2=p['measured_fragment_area_sum_m2'],
                      diagnostic_nearby_location_ids=nearby)
        owner = sample['owner_integer']
        if owner:
            if owner not in by_integer:
                raise ValueError('Sample owner absent from exact native ID binding')
            sample['owner_location_id'] = by_integer[owner]['id']
        if sample['status'] == 'centre-in-gap-owned-discrepancy':
            actual_owner = sample['owner_location_id']
            if actual_owner in selected:
                check = owner_shape_check(sample, selected[actual_owner], grid.size)
                check['current_footprint_file'] = selected_pins[actual_owner]
                check['current_feature_sha256'] = sha256(canonical_json(selected[actual_owner]))
                sample['owner_shape_check'] = check
                interpretations[check['interpretation']] += 1
            else:
                sample['owner_shape_check'] = {'interpretation': 'unknown-unextracted-owner-footprint'}
                interpretations['unknown-unextracted-owner-footprint'] += 1
        sample['triage_priority'] = (
            'blocked-or-unmeasured' if p['touches_blocked_tile'] or p['unmeasured_fragment_ids']
            else 'interior-multiple-nearby-unassigned-sample' if not p['touches_reference_shore']
            and len(nearby) >= 2 and sample['status'] == 'centre-in-gap-unassigned'
            else 'other-retained-candidate')
        counts[sample['status']] += 1;samples.append(sample)
    pilots = []
    for pilot in r['pilot_components']:
        f = features[pilot['component_id']];g = shape(f['geometry'])
        x, y = project(*pilot['anchor'], grid.size)
        contacts = []
        for identity in r['current_pilot_contact_subjects']:
            n = selected[identity];ng = shape(n['geometry'])
            if not ng.is_valid:
                raise ValueError('Invalid current contact footprint')
            if not g.intersects(ng):
                continue
            intersection = g.intersection(ng)
            edge = g.boundary.intersection(ng.boundary)
            kind = ('positive-area-intersection-flag' if intersection.area > 0
                    else 'positive-length-boundary' if edge.length > 0 else 'point-only-ambiguous')
            contacts.append({'location_id': identity, 'name': n['properties']['name'],
                             'parent_id': n['properties'].get('parent_id'), 'kind': kind,
                             'current_footprint_file': selected_pins[identity],
                             'current_feature_sha256': sha256(canonical_json(n)),
                             'source_metadata': n['properties'].get('metadata', {}),
                             'existing_research_issue_numbers': sorted(
                                 number for number, ids in scope_members.items() if identity in ids)})
        if not g.contains(Point(*pilot['anchor'])):
            raise ValueError('Pilot anchor outside original component')
        pilots.append({'name': pilot['name'], 'component_id': f['id'],
                       'anchor_lonlat': pilot['anchor'],
                       'actual_cell': [int(x // 1), int(y // 1)], 'owner_integer': grid.pick(x, y),
                       'current_contacts': sorted(contacts, key=lambda v: v['location_id']),
                       'source_status': 'native-provider-verification-still-required',
                       'administrative_assignment': None})
    out = ROOT / safe_path(destination)
    if out.exists() or any(p.is_symlink() for p in [out, *out.parents]):
        raise ValueError('Output must be an unused nonsymlink vintage')
    out.mkdir(parents=True)
    outputs = write_parts(out, samples)
    report = {'version': VERSION, 'status': 'partial-diagnostic-only',
              'registry_input_commit': input_commit, 'registry_pin': registry_pin,
              'reference_commit': source.commit, 'current_release': release,
              'current_grid_manifest': r['grid_manifest'], 'current_hierarchy': r['hierarchy'],
              'grid_size': grid.size, 'coordinate_bits': grid.bits,
              'grid_original_parts_verified': len(grid.verified),
              'original_geometry_evaluation_commit': original_report['original_evaluation_commit'],
              'original_component_report': r['components_report'],
              'component_count': len(samples), 'fragment_count': original_report['fragment_count'],
              'tiles_blocked': original_report['tiles_blocked'],
              'unmeasured_fragment_ids': original_report['unmeasured_fragment_ids'],
              'sample_counts': dict(counts), 'shape_interpretation_counts': dict(interpretations),
              'priority_counts': dict(collections.Counter(s['triage_priority'] for s in samples)),
              'water_pilot_reference': r['water_report'],
              'pilot_current_contacts': pilots, 'existing_research_snapshots': r['protocol_snapshots'],
              'sample_parts': outputs,
              'software': {'shapely': shapely.__version__, 'geos': shapely.geos_version_string},
              'limits': ['One native cell per component; all other cells remain unchecked.',
                         'This does not exhaustively discover raster-only gaps outside retained components.',
                         'Owned-cell discrepancies are separated from projection/interpolation effects.',
                         'All original blocked tiles and measurement failures remain unresolved.',
                         'Nearby IDs are inherited diagnostics; only pilot current contacts are extracted.',
                         'Selected current footprints are derived atlas data, not native-provider approval.',
                         'Point contacts and every positive-area numerical intersection are retained as flags.',
                         'Frozen water-pilot source, date, encoding and registration limits remain unchanged.',
                         'No source-backed boundary repair, administrative assignment, release or deployment.']}
    raw = canonical_json(report)
    if len(raw) > MAX_FILE_BYTES:
        raise ValueError('Report exceeds ordinary-file cap')
    with (out / 'report.json').open('xb') as f:
        f.write(raw)
    return descriptor(str((out / 'report.json').relative_to(ROOT)), raw)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input-commit', required=True)
    p.add_argument('--inputs', required=True)
    p.add_argument('--inputs-bytes', type=int, required=True)
    p.add_argument('--inputs-sha256', required=True)
    p.add_argument('--out', required=True)
    a = p.parse_args()
    print(json.dumps(triage(a.input_commit, a.inputs, a.inputs_bytes, a.inputs_sha256, a.out), sort_keys=True))
