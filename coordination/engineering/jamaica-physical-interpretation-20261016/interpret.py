"""Review original Jamaica physical candidates without creating native repair authority.

Run from a managed repository checkout with pinned Git objects, Python and Shapely.
The complete original source and reviewed whole-target result are read by Git pin;
no source download or whole-target scientific recomputation is performed.
"""
import argparse
import collections
import gzip
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import time

import shapely
from shapely.geometry import Point, shape

PACKET = Path(__file__).resolve().parent
SIZE = 262166
PACKAGE_ID = 'gb-JAM-ADM1--physical-interpretation'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(body):
    return hashlib.sha256(body).hexdigest()


def unique(rows, key, label):
    values = [key(row) for row in rows]
    require(len(values) == len(set(values)), 'Duplicate ' + label)
    return dict(zip(values, rows))


def admit_output(output):
    output = Path(output).absolute()
    for parent in [output, *output.parents]:
        require(not parent.is_symlink(), 'Symlink output path refused')
    require(not os.path.lexists(output), 'Fresh output directory required')
    require(output.parent.is_dir(), 'Output parent must exist')
    return output


def read_inputs():
    pins = json.loads((PACKET / 'input-pins.json').read_bytes())
    descriptors = pins['inputs']
    planned = sum(p['bytes'] + p.get('uncompressed_bytes', 0) for p in descriptors.values())
    require(planned <= 96 * 1024 * 1024, 'Input plan exceeds bounded 96 MiB allowance')
    bodies = {}
    for role, pin in descriptors.items():
        spec = pin['commit'] + ':' + pin['path']
        env = dict(os.environ, GIT_NO_LAZY_FETCH='1', GIT_NO_REPLACE_OBJECTS='1')
        size = int(subprocess.check_output(['git', '--no-replace-objects', 'cat-file', '-s', spec], env=env))
        require(size == pin['bytes'], 'Immutable tree size mismatch: ' + role)
        body = subprocess.check_output(['git', '--no-replace-objects', 'show', spec], env=env)
        require(len(body) == pin['bytes'] and digest(body) == pin['sha256'], 'Immutable input drift: ' + role)
        if pin['path'].endswith('.gz'):
            body = gzip.decompress(body)
            require(len(body) == pin['uncompressed_bytes'] and digest(body) == pin['uncompressed_sha256'], 'Decoded drift: ' + role)
        bodies[role] = body
    data = {key: json.loads(value) for key, value in bodies.items()
            if key not in {'latitudes', 'source_review', 'attribution'}}
    data['latitudes'] = struct.unpack('<262166d', bodies['latitudes'])
    data['intervals'] = json.loads(gzip.decompress((PACKET / 'intervals/block-028.json.gz').read_bytes()))
    data['pins'] = pins
    data['planned_bytes'] = planned
    return data


def analyze(data):
    package = next(p for p in data['queue']['packages'] if p['package_id'] == PACKAGE_ID)
    intervals = data['intervals']
    require(package['native_cells'] == 446 and package['interval_segments'] == 312, 'Original package denominator changed')
    roster = [r for r in data['global_roster'] if r['family_index'] == 167]
    byid = unique(roster, lambda r: r['source_id'], 'source identity')
    byowner = unique(roster, lambda r: r['owners'][0], 'owner identity')
    bysid = unique(roster, lambda r: r['source_index'], 'source index')
    require(len(roster) == 14 and all(len(r['owners']) == 1 for r in roster), 'Complete source family required')
    original = data['source']
    require(original['crs']['properties']['name'] == 'urn:ogc:def:crs:OGC:1.3:CRS84', 'Source CRS changed')
    source = unique(original['features'], lambda f: 'gb:JAM:ADM1:' + f['properties']['shapeID'], 'original feature')
    targets = unique([f for f in data['targets']['features'] if f['properties']['id'].startswith('gb:JAM:ADM1:')], lambda f: f['properties']['id'], 'target')
    stages = unique(data['selected_stage'], lambda r: r['target'], 'stage target')
    physical = unique(data['whole_physical']['results'], lambda r: r['target'], 'physical target')
    require(set(source) == set(targets) == set(stages) == set(physical) == set(byid), 'Full source/target/physical join differs')
    geometries = {}
    components = {}
    supports = {}
    issues = []
    for identity, r in byid.items():
        f = source[identity]
        require(original['features'][r['ordinal']] == f and r['name'] == f['properties']['shapeName'], 'Source ordinal/name mismatch')
        target = targets[identity]
        metadata = target['properties']['metadata']
        require(metadata['reference_year'] == '2011' and metadata['original_id'] == f['properties']['shapeID'], 'Reference target identity/vintage changed')
        require(stages[identity]['consumed'] == f and stages[identity]['selected'] == target, 'Whole-target consumed input mismatch')
        geometry = shape(f['geometry'])
        require(geometry.is_valid and not geometry.is_empty, 'Invalid original source geometry')
        geometries[identity] = geometry
        components[identity] = list(geometry.geoms) if geometry.geom_type == 'MultiPolygon' else [geometry]
        support = physical[identity]['support']
        require(set(support) == {'mapped_land_support', 'mapped_inland_water_support', 'outside_mapped_L1_context', 'hierarchy_disagreements', 'missing_reconstruction', 'extra_reconstruction', 'contradictory_land_water_support'}, 'Incomplete physical witness set')
        supports[identity] = {key: shape(value) for key, value in support.items() if key != 'hierarchy_disagreements'}
        supports[identity].update({'hierarchy:' + key: shape(value) for key, value in support['hierarchy_disagreements'].items()})
        for ordinal, item in enumerate(physical[identity]['issues']):
            issues.append((identity, ordinal, item, shape(item['geometry'])))
    # Independent exact cell denominator from original global rows, rather than
    # trusting the new packet's stock-extractor output or its summary counts.
    land = unique(data['land_census'], lambda r: r['y'], 'land row')
    water = unique(data['water_census'], lambda r: r['y'], 'water row')
    expected = []
    for row in data['source_candidates']:
        for start, end, owners, sids in row['runs']:
            if not set(sids).intersection(bysid):
                continue
            require(len(owners) == len(sids) == 1 and sids[0] in bysid and bysid[sids[0]]['owners'] == owners, 'Unexpected original candidate ownership')
            for x in range(start, end):
                y = row['y']
                mapped = any(a <= x < b for a, b in land.get(y, {}).get('runs', []))
                inland = any(a <= x < b for a, b in water.get(y, {}).get('runs', []))
                if not mapped and not inland:
                    expected.append((y, x, owners[0], sids[0]))
    actual = []
    for y, start, end, owners, sids, physical_class in intervals:
        require(len(owners) == len(sids) == 1 and physical_class == 'source-relative' and start < end, 'Malformed review interval')
        actual.extend((y, x, owners[0], sids[0]) for x in range(start, end))
    require(len(actual) == len(set(actual)) == len(expected) == len(set(expected)) == 446, 'Duplicate/missing review cells')
    require(set(actual) == set(expected) and len(intervals) == 312, 'Exact original review scope differs')
    require(sorted({r[2] for r in actual}) == package['owners'] and sorted({r[3] for r in actual}) == package['source_features'], 'Candidate owner/source roster differs')
    # All source-relative candidates remain questions. Point predicates establish
    # only which retained witnesses apply; they do not identify ocean or river.
    answers = []
    question_groups = {}
    totals = collections.Counter()
    minimum_source_boundary_distance = float('inf')
    for interval_index, interval in enumerate(intervals):
        y, start, end, owners, sids, physical_class = interval
        r = byowner[owners[0]]
        require(bysid[sids[0]] == r, 'Interval source/owner join differs')
        identity = r['source_id']
        points = []
        for x in range(start, end):
            longitude = (x + .5) / SIZE * 360 - 180
            latitude = data['latitudes'][y]
            point = Point(longitude, latitude)
            membership = [key for key, geom in geometries.items() if geom.covers(point)]
            require(membership == [identity], 'Original complete-family point membership differs')
            component_hits = [i for i, geom in enumerate(components[identity]) if geom.covers(point)]
            require(len(component_hits) == 1, 'Ambiguous original component')
            witness_hits = [key for key, geom in supports[identity].items() if geom.covers(point)]
            issue_hits = [{'target': key, 'issue_index': index, 'kind': item.get('kind', item.get('type'))}
                          for key, index, item, geom in issues if geom.intersects(point)]
            require(witness_hits == ['outside_mapped_L1_context'], 'Changed physical witness classification requires explicit review')
            require(not issue_hits, 'Residual witness contact requires explicit review')
            require(not any(shape(t['geometry']).covers(point) for t in targets.values()), 'Existing target point contact requires review')
            distance = geometries[identity].boundary.distance(point)
            require(distance > 0, 'Source boundary contact requires native-kernel adjudication')
            minimum_source_boundary_distance = min(minimum_source_boundary_distance, distance)
            component = component_hits[0]
            qid = 'JAM-physical-' + str(r['source_index']) + '-component-' + str(component)
            group = question_groups.setdefault(qid, {'question_id': qid, 'status': 'unresolved',
                'owner_index': owners[0], 'source_feature_index': sids[0], 'source_id': identity,
                'source_polygon_index': component, 'name': r['name'], 'reference_year': 2011,
                'native_cells': 0, 'interval_indices': [], 'cell_center_bounds': [longitude, latitude, longitude, latitude],
                'question': 'For these exact ' + r['name'] + ' reference-parish cells, does dated coast/river/local evidence support the original source-backed territorial assignment despite the GSHHG boundary difference, or establish a source simplification/vintage discrepancy? Physical surface and acceptance remain unresolved.',
                'needed_evidence': 'A dated, spatially explicit coast, river/estuary or local territorial source tied to these exact cells and the retained reference-source interpretation. A missing land mask, modern parish prose or later Portmore commencement alone is insufficient.',
                'known_interpretation': 'Unique original parish-source membership outside the retained mapped-L1 context; neither mapped inland water nor a physical exclusion is established.',
                'evidence_roles': ['source', 'targets', 'whole_physical', 'selected_stage', 'source_metadata', 'source_review']})
            group['native_cells'] += 1
            if interval_index not in group['interval_indices']:
                group['interval_indices'].append(interval_index)
            bounds = group['cell_center_bounds']
            bounds[0] = min(bounds[0], longitude); bounds[1] = min(bounds[1], latitude)
            bounds[2] = max(bounds[2], longitude); bounds[3] = max(bounds[3], latitude)
            points.append({'x': x, 'question_id': qid, 'source_polygon_index': component})
            totals['unique_original_source_cells'] += 1
            totals['outside_mapped_L1_context_cells'] += 1
        pieces = []
        for point in points:
            if pieces and pieces[-1]['end'] == point['x'] and pieces[-1]['question_id'] == point['question_id']:
                pieces[-1]['end'] += 1
            else:
                pieces.append({'start': point['x'], 'end': point['x'] + 1, 'question_id': point['question_id'], 'source_polygon_index': point['source_polygon_index']})
        answers.append({'interval_index': interval_index, 'original_interval': interval, 'source_id': identity,
            'name': r['name'], 'status': 'unresolved', 'interpretation': 'original-source-backed-physical-disagreement',
            'witnesses': ['outside_mapped_L1_context'], 'mapped_land_cells': 0, 'mapped_inland_water_cells': 0,
            'reconstruction_issue_contacts': [], 'parts': pieces})
    require(sum(q['native_cells'] for q in question_groups.values()) == 446, 'Question coverage lost cells')
    summary = {'package_id': PACKAGE_ID, 'evaluation_commit': data['pins']['evaluation_commit'],
        'shared_physical_execution_commit': data['pins']['shared_scientific_result_commit'],
        'native_cells': len(actual), 'interval_segments': len(intervals), 'candidate_owners': len(package['owners']),
        'complete_source_features': len(source), 'complete_source_components': sum(map(len, components.values())),
        'question_groups': len(question_groups), 'unresolved_cells': len(actual), 'resolved_physical_cells': 0,
        'native_repairs': 0, 'mapped_land_cells': 0, 'mapped_inland_water_cells': 0,
        'reconstruction_issue_witnesses_checked': len(issues), 'reconstruction_issue_contacts': 0,
        'hierarchy_disagreement_cells': 0, 'contradictory_support_cells': 0, 'selected_target_center_contacts': 0,
        'source_point_boundary_contacts': 0, 'minimum_source_boundary_distance_degrees': minimum_source_boundary_distance,
        **totals, 'runtime': {'python': sys.version.split()[0], 'shapely': shapely.__version__, 'geos': shapely.geos_version_string},
        'planned_input_encoded_decoded_bytes': data['planned_bytes'],
        'limits': ['Shapely candidate-centre diagnostic is not native qualification or selected-output readback.',
            'Original 2011 reference identities are retained; no current parish or offshore-completeness certification.',
            'All physical nature questions remain unresolved. Outside mapped L1 is not ocean or river evidence.',
            'Whole-target GSHHG execution is reused unchanged, not a new execution; its heterogeneous vintages and authority limits remain.',
            'This packet changes no selected asset, owner, mask, hierarchy or repair authority.']}
    return {'summary.json': summary, 'interval-assessments.json': answers,
            'questions.json': sorted(question_groups.values(), key=lambda q: q['question_id'])}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('output', help='fresh directory within the managed checkout')
    args = parser.parse_args()
    output = admit_output(args.output)
    start = time.monotonic()
    data = read_inputs()
    products = analyze(data)
    payloads = {name: (json.dumps(value, indent=2) + '\n').encode() for name, value in products.items()}
    require(sum(map(len, payloads.values())) < 8 * 1024 * 1024, 'Output plan exceeds 8 MiB')
    output.mkdir()
    receipt = {'version': 1, 'elapsed_seconds': time.monotonic() - start,
               'input_pins_sha256': digest((PACKET / 'input-pins.json').read_bytes()),
               'producer_sha256': digest(Path(__file__).read_bytes()), 'files': []}
    for name, body in payloads.items():
        with (output / name).open('xb') as file:
            file.write(body)
        receipt['files'].append({'path': name, 'bytes': len(body), 'sha256': digest(body)})
    with (output / 'publication.json').open('x') as file:
        json.dump(receipt, file, indent=2); file.write('\n')
    print(json.dumps(products['summary.json']))


if __name__ == '__main__':
    main()
