"""Typed source/archived-code/full-product gate; never factual geography approval."""
import argparse
import copy
import gzip
import hashlib
import io
import json
import math
import pathlib

from evidence.immutable import Baseline, canonical_json
from physical_gap_audit import load_inputs, blocked_sources
from lossless_audit_inputs import digest, ordinary, report_roster, verify_manifest

SCIENCE_CODE = {'scripts/audit-physical-gaps.py', 'scripts/physical_gap_audit.py',
                'scripts/evidence/immutable.py', 'scripts/evidence/geometry.py', 'scripts/ellipsoidal_area.py'}
ENVELOPE_CODE = {'scripts/lossless_audit_inputs.py', 'scripts/evidence/immutable.py'}
DOMAIN = [-180, -60, 180, 85.0511287798066]
LIMIT = 32 * 1024 * 1024


def read_json(path, sha=None):
    raw = ordinary(path)
    if sha is not None and digest(raw) != sha:
        raise ValueError('Pinned evidence bytes changed: ' + path)
    return json.loads(raw)


def decoded_features(entry):
    raw = ordinary(entry['path'])
    if len(raw) != entry['bytes'] or digest(raw) != entry['sha256']:
        raise ValueError('Complete product bytes changed')
    with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
        decoded = stream.read(LIMIT + 1)
    if (len(decoded) > LIMIT or len(decoded) != entry['uncompressed_bytes']
            or digest(decoded) != entry['uncompressed_sha256']):
        raise ValueError('Complete decoded product changed or exceeded byte budget')
    body = json.loads(decoded)
    if body['type'] != 'FeatureCollection' or not isinstance(body['features'], list):
        raise ValueError('Invalid audit product collection')
    return body['features']


def require_code(snapshot, report, expected):
    if {row['path'] for row in report['code_inputs']} != expected or len(report['code_inputs']) != len(expected):
        raise ValueError('Incomplete actual execution-code closure')
    aliases = []
    for row in report['code_inputs']:
        key = report['executed_code_commit'] + ':' + row['path']
        binding = snapshot['aliases'].get(key)
        if binding is None or binding['original_commit'] != report['executed_code_commit'] or binding['original'] != row:
            raise ValueError('Archived code alias is missing or changed')
        encoded = ordinary(binding['snapshot']['path'])
        if (len(encoded) != row['bytes'] or binding['snapshot']['bytes'] != row['bytes']
                or digest(encoded) != row['sha256'] or binding['snapshot']['sha256'] != row['sha256']):
            raise ValueError('Archived execution code bytes do not match the actual report')
        original = Baseline(pathlib.Path(__file__).resolve().parents[1], report['executed_code_commit'], [row]).read(row['path'])
        if original != encoded:
            raise ValueError('Archived code differs from immutable executed Git bytes')
        aliases.append(key)
    return aliases


def normalized(report):
    report = copy.deepcopy(report)
    for kind in ['outputs', 'residue_outputs']:
        for entry in report[kind]:
            entry['path'] = pathlib.PurePosixPath(entry['path']).name
    return report


def expected_tiles(size):
    if isinstance(size, bool) or not math.isfinite(size) or not 0.25 <= size <= 10:
        raise ValueError('Invalid tile size; no unbounded or empty-domain loops')
    west, south, east, north = DOMAIN
    result, y = [], south
    while y < north:
        x = west
        while x < east:
            result.append([x, y, min(east, x + size), min(north, y + size)])
            x += size
        y += size
    return result


def inventory(report, final):
    if report['version'] != 'worldatlas-physical-land-before-water-v1' or report['bounds'] != DOMAIN:
        raise ValueError('Unrecognized or narrowed audit domain/method')
    bounds = expected_tiles(report['tile_degrees'])
    tiles = report['tiles']
    if any(row['status'] not in ('checked', 'unchecked') for row in tiles):
        raise ValueError('Invalid checked/unchecked state')
    if len(tiles) != len(bounds) or any(row['id'] != i or row['bounds'] != bounds[i] for i, row in enumerate(tiles)):
        raise ValueError('Incomplete, reordered or duplicate declared-domain accounting')
    checked = sum(row['status'] == 'checked' for row in tiles)
    expected_status = 'declared-domain-detection-complete' if checked == len(tiles) else 'partial-unknown-domain'
    if report['status'] != expected_status:
        raise ValueError('Report status contradicts unknown-domain ledger')
    if checked != report['tiles_checked'] or len(tiles) - checked != report['tiles_unchecked']:
        raise ValueError('Checked/unchecked tile ledger mismatch')
    counters = [[0, 0] for _ in tiles]
    seen, geometries, measurements = set(), hashlib.sha256(), []
    unmeasured = set()
    for kind, counter in [('outputs', 0), ('residue_outputs', 1)]:
        for entry in report[kind]:
            for feature in decoded_features(entry):
                identity = feature['id']
                if feature['type'] != 'Feature' or identity in seen:
                    raise ValueError('Duplicate/invalid output identity')
                seen.add(identity)
                tile_id = int(identity.split(':')[1])
                if not 0 <= tile_id < len(tiles) or tiles[tile_id]['status'] != 'checked':
                    raise ValueError('Output from an unchecked/outside tile')
                props = feature['properties']
                if props['tile'] != bounds[tile_id]:
                    raise ValueError('Output tile binding changed')
                geometry = canonical_json(feature['geometry'])
                geometries.update(canonical_json({'id': identity, 'geometry': feature['geometry']}))
                counters[tile_id][counter] += 1
                if kind == 'outputs':
                    if (feature['geometry']['type'] != 'Polygon' or props['original_planar_area'] <= 0
                            or not math.isfinite(props['original_planar_area'])
                            or identity.split(':')[-1] != digest(geometry)):
                        raise ValueError('Candidate is nonpositive or lost its exact geometry binding')
                    if props['water_status'] != 'unverified' or props['administrative_assignment'] is not None:
                        raise ValueError('Diagnostic candidate asserts unsupported water/owner approval')
                    area = props['area_m2']
                    if area is None:
                        unmeasured.add(identity)
                    elif isinstance(area, bool) or not math.isfinite(area) or area <= 0:
                        raise ValueError('Invalid measured candidate area')
                    else:
                        measurements.append(area)
                elif final and props['stage'] in ('physical-land-clipping', 'location-clipping'):
                    if not props.get('source', {}).get('id') or not props['source'].get('input_path'):
                        raise ValueError('Final clipping remnant lost its original source key')
    for row, counts in zip(tiles, counters):
        if row['status'] == 'checked' and counts != [row['candidate_fragments'], row['residues']]:
            raise ValueError('Full tile/product counts disagree')
    totals = [sum(c[i] for c in counters) for i in [0, 1]]
    if totals != [report['candidate_fragments'], report['residues']]:
        raise ValueError('Full product/report counts disagree')
    if unmeasured != {row['fragment'] for row in report['measurement_errors']}:
        raise ValueError('Measurement uncertainty omitted or mislabeled')
    if math.fsum(measurements) != report['measured_candidate_area_m2']:
        raise ValueError('Complete measured-area sum differs')
    return {'geometry_and_ids_sha256': geometries.hexdigest(), 'candidates': totals[0],
            'residues': totals[1], 'measurement_unknowns': len(unmeasured), 'tiles_checked': checked}


def source_accounting(report, inputs):
    """Re-read original source validity and every tile's uncertainty diagnostics."""
    # The original immutable trial predates the explicit source_extent_status
    # diagnostic. Preserve its exact schema; never waive bounds, identity or WKB.
    if report.get('executed_code_commit') == 'e67eeafc1aa130aa5c1a6d1222d39116625fd003':
        inputs = copy.deepcopy({k: v for k, v in inputs.items() if k not in ('land', 'locations', 'water')})
        for key in ('invalid_land', 'invalid_locations', 'invalid_water'):
            for row in inputs[key]:
                if row['source_extent_status'] != 'finite-bounds':
                    raise ValueError('Original trial cannot certify amended unknown extent')
                row.pop('source_extent_status')
    fields = {'invalid_land': 'invalid_land', 'invalid_locations': 'invalid_locations',
              'invalid_water_reference': 'invalid_water', 'locations': 'location_count',
              'physical_reference': 'land_source', 'water_reference': 'water_source',
              'canonical_grid_sha256': 'canonical_grid_sha256',
              'release_index_sha256': 'release_index_sha256', 'release_ids': 'release_ids'}
    for reported, original in fields.items():
        if report[reported] != inputs[original]:
            raise ValueError('Original source/release diagnostic changed: ' + reported)
    for tile in report['tiles']:
        blocked = blocked_sources(tile['bounds'], inputs['invalid_land'] + inputs['invalid_locations'])
        if blocked:
            if tile['status'] != 'unchecked' or tile.get('blocked_sources') != blocked:
                raise ValueError('Original invalid land/location unchecked extent omitted')
        elif tile['status'] == 'unchecked':
            if tile.get('reason') != 'original-geometry-operation-failed' or not tile.get('error'):
                raise ValueError('Unchecked tile lacks original source block or operation failure')
        if tile['status'] == 'checked':
            expected = blocked_sources(tile['bounds'], inputs['invalid_water'])
            if tile.get('invalid_water_diagnostics') != expected:
                raise ValueError('Original invalid-water diagnostic omitted or changed')
            sha = tile.get('missing_geometry_sha256', '')
            if len(sha) != 64 or any(c not in '0123456789abcdef' for c in sha):
                raise ValueError('Checked tile lost its original missing-geometry digest')


def upstream_closure(child, envelope, reports):
    """Require whole original/encoded descriptors and the normal byte budgets."""
    original_rows = child['baseline']['files'] + [row for source in child['sources'] for row in source.get('files', [])]
    def clean(row):
        return {key: row[key] for key in ('path', 'bytes', 'sha256', 'hash_kind')}
    originals = {row['path']: clean(row) for row in original_rows}
    expected = {row['original']['path']: clean(row['original']) for row in envelope['entries']}
    if len(originals) != len(original_rows) or originals != expected:
        raise ValueError('Upstream manifest omitted or changed complete original file descriptors')
    if child['baseline']['commit'] != reports[3]['baseline_commit']:
        raise ValueError('Upstream original baseline commit differs')
    outputs = {row['path']: row for row in child['outputs']}
    if len(outputs) != len(child['outputs']):
        raise ValueError('Duplicate upstream output descriptor')
    for row in envelope['entries']:
        if clean(outputs.get(row['encoded']['path'], {})) != clean(row['encoded']):
            raise ValueError('Upstream manifest omitted/changed complete encoded payload')
    all_rows = original_rows + child['outputs']
    if len(all_rows) > 512 or sum(row['bytes'] for row in all_rows) > 256 * 1024 * 1024:
        raise ValueError('Upstream stage exceeds original evidence budget')
    repo = pathlib.Path(__file__).resolve().parents[1]
    source_paths = {row['path'] for row in child['baseline']['files']}
    original = Baseline(repo, child['baseline']['commit'], child['baseline']['files'])
    for row in all_rows:
        raw = original.read(row['path']) if row['path'] in source_paths else ordinary(row['path'])
        if row['hash_kind'] != 'file-bytes' or len(raw) != row['bytes'] or digest(raw) != row['sha256']:
            raise ValueError('Upstream complete descriptor bytes changed')


def validate(root_manifest):
    root = read_json(root_manifest)
    stage = root['mandatory_input_stage']
    if stage['kind'] != 'lossless-original-audit-byte-envelope-v1':
        raise ValueError('Unknown mandatory upstream source stage')
    child = read_json(stage['evidence_manifest'], stage['evidence_sha256'])
    if child['issue'] != root['issue'] or child['subject_ids'] != root['subject_ids']:
        raise ValueError('Upstream evidence scope differs')
    envelope = read_json(stage['envelope_manifest'], stage['envelope_sha256'])
    snapshot = read_json(root['execution_code_manifest'])
    reports = [read_json(row['path'], row['sha256']) for row in root['audit_reports']]
    if len(reports) != 5 or len({r['path'] for r in root['audit_reports']}) != 5:
        raise ValueError('Initial/intermediate/final audit vintages were omitted')
    upstream_closure(child, envelope, reports)
    restored = verify_manifest(stage['envelope_manifest'], stage['envelope_sha256'],
                               root['audit_reports'][3]['path'], root['audit_reports'][3]['sha256'])
    roster = report_roster(reports[3])
    inputs = load_inputs(pathlib.Path(__file__).resolve().parents[1], reports[3]['baseline_commit'],
                         envelope['water_root'], reports[3]['water_commit'])
    aliases = set(require_code(snapshot, envelope, ENVELOPE_CODE))
    results = []
    for i, report in enumerate(reports):
        if report_roster(report) != roster:
            raise ValueError('A scientific vintage consumed different original input bytes')
        aliases.update(require_code(snapshot, report, SCIENCE_CODE))
        source_accounting(report, inputs)
        results.append(inventory(report, i >= 3))
    if aliases != set(snapshot['aliases']):
        raise ValueError('Execution snapshot has missing/undeclared code aliases')
    if snapshot['unique_files'] != len({row['snapshot']['path'] for row in snapshot['aliases'].values()}):
        raise ValueError('Archived unique-file inventory differs')
    if len({r['geometry_and_ids_sha256'] for r in results}) != 1:
        raise ValueError('Diagnostic amendments changed an original candidate/remnant point set or ID')
    for earlier in reports[:3]:
        for old, final in zip(earlier['tiles'], reports[3]['tiles'], strict=True):
            if old['status'] != final['status'] or old.get('missing_geometry_sha256') != final.get('missing_geometry_sha256'):
                raise ValueError('Diagnostic amendment changed original tile status/difference digest')
    for left, right in [(reports[1], reports[2]), (reports[3], reports[4])]:
        if normalized(left) != normalized(right):
            raise ValueError('Two complete reports disagree beyond the output-vintage prefix')
        for kind in ['outputs', 'residue_outputs']:
            for a, b in zip(left[kind], right[kind], strict=True):
                if ordinary(a['path']) != ordinary(b['path']):
                    raise ValueError('Two complete generations differ in actual file bytes')
    return {'status': 'complete-typed-source-code-product-validation', 'original_source': restored,
            'archived_code_aliases': len(aliases), 'vintages_checked': len(reports),
            **results[-1], 'final_files_byte_identical': True,
            'limits': ['Declared-domain numerical discovery and exact byte preservation only.',
                       'Original/new component crosswalk, global prioritization, factual repairs and delivery remain incomplete.',
                       'Earlier trial shoreline/provenance flags are retained unapproved; final controls are separate.',
                       'Tile difference digests prove preservation relative to original runs, not an independent reconstruction.']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True)
    args = parser.parse_args()
    print(json.dumps(validate(args.manifest), sort_keys=True))
