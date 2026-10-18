"""Bounded SLE centre review adapted from accepted Jamaica interpretation.

Consumes the already-produced Cloud intervals. Never extracts/reconstructs them,
reruns whole-source physics, or constructs a native authority.
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
OWNERS = [39710, 39712, 39715, 39717, 39718, 39719, 39720]
PACKAGE_ID = 'gb-SLE-ADM2--physical-interpretation'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(body):
    return hashlib.sha256(body).hexdigest()


def unique(rows, key, label):
    values = [key(row) for row in rows]
    require(len(values) == len(set(values)), 'Duplicate ' + label)
    return dict(zip(values, rows))


def admit_output(value):
    output = Path(value).absolute()
    require(not os.path.lexists(output), 'Fresh output required')
    require(output.parent.is_dir(), 'Output parent required')
    for p in [output, *output.parents]:
        require(not p.is_symlink(), 'Symlink output refused')
    return output


def read_inputs():
    pins = json.loads((PACKET / 'input-pins.json').read_bytes())
    bodies = {}
    env = dict(os.environ, GIT_NO_LAZY_FETCH='1', GIT_NO_REPLACE_OBJECTS='1')
    for role, pin in pins['inputs'].items():
        spec = pin['commit'] + ':' + pin['path']
        body = subprocess.check_output(['git', '-c', 'protocol.allow=never', 'show', spec], env=env)
        require(len(body) == pin['bytes'] and digest(body) == pin['sha256'], 'Pinned input drift: ' + role)
        if 'uncompressed_bytes' in pin:
            body = gzip.decompress(body)
            require(len(body) == pin['uncompressed_bytes'] and digest(body) == pin['uncompressed_sha256'], 'Decoded input drift: ' + role)
        bodies[role] = body
    data = {k: json.loads(v) for k, v in bodies.items() if k not in {'latitudes', 'source_review'}}
    data['latitudes'] = struct.unpack('<262166d', bodies['latitudes'])
    # These are literal prior Cloud outputs, not a new source-row extraction.
    body = (PACKET / 'intervals/block-030.json.gz').read_bytes()
    require(len(body) == 3755 and digest(body) == '534192593d9caba16e86286e888e8384cfdadf35f5372d6536b31139565001a0', 'Retained Cloud interval bytes changed')
    data['intervals'] = json.loads(gzip.decompress(body))
    body = (PACKET / 'intervals/package.json').read_bytes()
    require(len(body) == 2354 and digest(body) == '3d63642a25356435c2190094367a1292085893ee56fad451fe0018dabd7cdad1', 'Retained Cloud package bytes changed')
    data['package'] = json.loads(body)
    data['pins'] = pins
    return data


def validate_scope(data):
    pkg = data['package']
    require(pkg['package_id'] == PACKAGE_ID and pkg['native_cells'] == 1213 and pkg['interval_segments'] == 613 and pkg['owners'] == OWNERS, 'Original package changed')
    require(next(p for p in data['queue']['packages'] if p['package_id'] == PACKAGE_ID) == pkg, 'Retained original queue/package mismatch')
    require(len(data['intervals']) == 613, 'Missing original intervals')
    keys = []
    for y, a, b, owners, sids, physical in data['intervals']:
        require(physical == 'source-relative' and len(owners) == 1 and owners[0] in OWNERS and a < b and sids, 'Malformed original interval')
        keys.extend((y, x, owners[0]) for x in range(a, b))
    require(len(keys) == len(set(keys)) == 1213, 'Duplicate/missing original keys')
    require(sorted({k[2] for k in keys}) == OWNERS, 'Original owners changed')
    roster = [r for r in data['global_roster'] if r['family_index'] in [291, 292]]
    bysid = unique(roster, lambda r: r['source_index'], 'source index')
    primary = [r for r in roster if r['family_index'] == 292]
    require(len(primary) == 14 and len(roster) == 18 and all(len(r['owners']) == 1 for r in primary), 'Complete4+14 source context required')
    byowner = unique(primary, lambda r: r['owners'][0], 'primary owner')
    for y, a, b, owners, sids, physical in data['intervals']:
        require(all(s in bysid for s in sids), 'Foreign original source index')
        require({o for sid in sids for o in bysid[sid]['owners']} == {owners[0]}, 'Wrong original owner/source join')
    state = unique(data['selected_state']['keys'], lambda r: (r['y'], r['x'], r['original_owner']), 'selected key')
    require(set(state) == set(keys), 'Selected-state scope differs from original')
    return roster, primary, bysid, byowner, state


def witness_hits(supports, issues, point):
    hits = [name for name, geometry in supports.items() if geometry.covers(point)]
    contacts = [{'target': identity, 'issue_index': ordinal, 'kind': item.get('kind', item.get('type')), 'reason': item.get('reason')}
                for identity, ordinal, item, geometry in issues if geometry.intersects(point)]
    return hits, contacts


def analyze(data):
    roster, primary, bysid, byowner, state = validate_scope(data)
    original = data['source']
    require(original['crs']['properties']['name'] == 'urn:ogc:def:crs:OGC:1.3:CRS84', 'Primary source CRS changed')
    source = unique(original['features'], lambda f: 'gb:SLE:ADM2:' + f['properties']['shapeID'], 'primary original')
    secondary = unique(data['secondary_source']['features'], lambda f: 'gb:SLE:ADM1:' + f['properties']['shapeID'], 'secondary original')
    byid = {r['source_id']: r for r in primary}
    require(set(source) == set(byid) and len(secondary) == 4, 'Whole source inventory changed')
    selected = unique(data['selected_state']['selected_targets'], lambda f: f['properties']['id'], 'selected target')
    require(set(selected) == set(source), 'Complete selected primary targets required')
    stages = unique(data['selected_stage'], lambda r: r['target'], 'physical-stage target')
    physical = unique(data['whole_physical']['results'], lambda r: r['target'], 'physical result')
    require(len(stages) == len(physical) == 11 and set(stages) == set(physical), 'Retain all11 physical/stage targets')
    geometries, components, supports, issues = {}, {}, {}, []
    for identity, feature in source.items():
        r = byid[identity]
        require(original['features'][r['ordinal']] == feature and r['name'] == feature['properties']['shapeName'], 'Original ordinal/name mismatch')
        geometry = shape(feature['geometry'])
        require(geometry.is_valid and not geometry.is_empty, 'Invalid whole original geometry; no repair authorized')
        geometries[identity] = geometry
        components[identity] = list(geometry.geoms) if geometry.geom_type == 'MultiPolygon' else [geometry]
    secondary_geometries = {identity: shape(f['geometry']) for identity, f in secondary.items()}
    selected_geometries = {identity: shape(f['geometry']) for identity, f in selected.items()}
    for identity, result in physical.items():
        require(stages[identity]['consumed'] == source[identity], 'Physical consumed original changed')
        require(stages[identity]['selected']['geometry'] == selected[identity]['geometry'], 'Retained/current selected target geometry differs')
        support = result['support']
        require(set(support) == {'mapped_land_support', 'mapped_inland_water_support', 'outside_mapped_L1_context', 'hierarchy_disagreements', 'missing_reconstruction', 'extra_reconstruction', 'contradictory_land_water_support'}, 'Incomplete physical witness roles')
        supports[identity] = {k: shape(v) for k, v in support.items() if k != 'hierarchy_disagreements'}
        supports[identity].update({'hierarchy:' + k: shape(v) for k, v in support['hierarchy_disagreements'].items()})
        issues.extend((identity, i, item, shape(item['geometry'])) for i, item in enumerate(result['issues']))
    require(all(byowner[owner]['source_id'] in physical for owner in OWNERS), 'Review owner lacks retained physical target')
    answers, observations, questions = [], [], {}
    totals = collections.Counter()
    for index, original_interval in enumerate(data['intervals']):
        y, start, end, owners, sids, physical_class = original_interval
        owner = owners[0]
        r = byowner[owner]
        identity = r['source_id']
        parts = []
        for x in range(start, end):
            longitude, latitude = (x + .5) / SIZE * 360 - 180, data['latitudes'][y]
            point = Point(longitude, latitude)
            membership = [key for key, geom in geometries.items() if geom.covers(point)]
            component_hits = [i for i, geom in enumerate(components[identity]) if geom.covers(point)]
            secondary_hits = [key for key, geom in secondary_geometries.items() if geom.covers(point)]
            hits, issue_contacts = witness_hits(supports[identity], issues, point)
            selected_hits = [key for key, geom in selected_geometries.items() if geom.covers(point)]
            boundary = geometries[identity].boundary.intersects(point)
            native = state[(y, x, owner)]
            concerns = []
            if membership != [identity] or len(component_hits) != 1 or boundary:
                concerns.append('source-membership-component-or-boundary-uncertainty')
            if issue_contacts or any(k.startswith('hierarchy:') or k in ['missing_reconstruction', 'extra_reconstruction', 'contradictory_land_water_support'] for k in hits):
                concerns.append('retained-physical-issue-or-disagreement-contact')
            if native['existing_product_overlap']:
                concerns.append('existing-selected-product-overlap')
            if native['effective_selected_owner']:
                concerns.append('already-occupied-in-existing-selected-state')
            if selected_hits:
                concerns.append('selected-continuous-target-centre-contact')
            if not hits:
                concerns.append('no-retained-physical-witness-contact')
            disposition = 'unresolved-specific-contact' if concerns else 'supported-limited-source-interpretation'
            observation = 'retained-mapped-support' if any(k in hits for k in ['mapped_land_support', 'mapped_inland_water_support']) else ('original-source-backed-outside-mapped-L1' if 'outside_mapped_L1_context' in hits else 'retained-witness-combination')
            component_tag = '+'.join(map(str, component_hits)) if component_hits else 'unknown'
            qid = 'SLE-physical-' + str(r['source_index']) + '-component-' + component_tag
            evidence = {'source_polygon_indices': component_hits, 'complete_primary_membership': membership,
                        'secondary_source_membership': secondary_hits, 'physical_witness_hits': hits,
                        'physical_issue_contacts': issue_contacts, 'source_boundary_contact': boundary,
                        'selected_target_contacts': selected_hits, 'base_owner': native['base_owner'],
                        'accepted_additive_owner': native['accepted_additive_owner'], 'effective_selected_owner': native['effective_selected_owner'],
                        'existing_product_overlap': native['existing_product_overlap'], 'disposition': disposition,
                        'supported_observation': observation, 'specific_unresolved_concerns': concerns,
                        'physical_nature': 'No dated cell-specific coast/river/local evidence in these retained inputs establishes the actual surface or cause of disagreement.'}
            observations.append({'interval_index': index, 'y': y, 'x': x, 'original_owner': owner,
                                 'source_id': identity, 'question_id': qid, **evidence})
            if parts and parts[-1]['end'] == x and parts[-1]['evidence'] == evidence:
                parts[-1]['end'] = x + 1
            else:
                parts.append({'start': x, 'end': x + 1, 'question_id': qid, 'evidence': evidence})
            question = questions.setdefault(qid, {'question_id': qid, 'owner_index': owner, 'source_feature_index': r['source_index'],
                'source_id': identity, 'source_polygon_indices': component_hits, 'name': r['name'], 'reference_year': 2017,
                'native_cells': 0, 'interval_indices': [], 'cell_center_bounds': [longitude, latitude, longitude, latitude],
                'observed_disposition_counts': {}, 'observed_concerns': [],
                'question': 'Which dated coast/river/local and territorial-source evidence explains these exact original reference-district cells and the observed retained-source/selected-state contacts?',
                'needed_evidence': 'Spatially explicit dated evidence tied to these cells and original whole source components. Resolve actual listed source-boundary, physical-witness or selected-state contacts where present; outside a GSHHG mask alone establishes neither ocean nor a permitted territorial exclusion.',
                'physical_nature_status': 'unresolved-with-specific-retained-observations',
                'evidence_roles': ['source', 'secondary_source', 'selected_stage', 'whole_physical', 'source_binding', 'selected_state', 'latitudes', 'source_review']})
            question['native_cells'] += 1
            question['observed_disposition_counts'][disposition] = question['observed_disposition_counts'].get(disposition, 0) + 1
            question['observed_concerns'] = sorted(set(question['observed_concerns'] + concerns))
            if index not in question['interval_indices']:
                question['interval_indices'].append(index)
            bounds = question['cell_center_bounds']
            bounds[0], bounds[1], bounds[2], bounds[3] = min(bounds[0], longitude), min(bounds[1], latitude), max(bounds[2], longitude), max(bounds[3], latitude)
            totals['disposition:' + disposition] += 1
            totals['observation:' + observation] += 1
            for hit in hits:
                totals['physical:' + hit] += 1
            totals['physical_issue_contact_cells'] += bool(issue_contacts)
            totals['selected_target_contact_cells'] += bool(selected_hits)
            totals['base_occupied_cells'] += bool(native['base_owner'])
            totals['accepted_additive_occupied_cells'] += bool(native['accepted_additive_owner'])
            totals['source_boundary_contact_cells'] += boundary
        answers.append({'interval_index': index, 'original_interval': original_interval, 'original_owner': owner,
                        'source_id': identity, 'name': r['name'], 'parts': parts})
    require(sum(q['native_cells'] for q in questions.values()) == len(observations) == 1213 and len(answers) == 613, 'Original question partition lost cells')
    summary = {'package_id': PACKAGE_ID, 'evaluation_commit': data['pins']['evaluation_commit'], 'original_cells': 1213,
               'original_intervals': 613, 'original_owners': OWNERS, 'source_relative_cells': 1213,
               'complete_primary_features': len(source), 'complete_secondary_features': len(secondary),
               'complete_primary_components': sum(map(len, components.values())), 'retained_whole_physical_targets': len(physical),
               'all_physical_issue_witnesses_retained': len(issues), 'question_groups': len(questions), 'observed_counts': dict(totals),
               'native_authority_created': False, 'native_qualification_executed': False, 'accepted_repair_credit': 0,
               'runtime': {'python': sys.version.split()[0], 'shapely': shapely.__version__, 'geos': shapely.geos_version_string},
               'limits': ['Candidate-centre binary64/GEOS diagnostic, not a native raster or authority qualification.',
                          'Existing Cloud613interval extraction is reused literally. No local extraction or independent reconstruction.',
                          'Whole11-target physical evidence is reused unchanged; heterogeneous GSHHG dates and source-relative limits remain.',
                          'Historical4ADM1/14ADM2 context, all zero-candidate competitors, current16 versus14 and open#751 remain distinct.',
                          'No source, geometry, hierarchy, native asset, selected composition, legal title or accepted repair is changed.']}
    return {'summary.json': summary, 'interval-assessments.json': answers, 'cell-observations.json': observations,
            'questions.json': sorted(questions.values(), key=lambda q: q['question_id'])}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('output')
    args = parser.parse_args()
    output = admit_output(args.output)
    started = time.monotonic()
    print(json.dumps({'event': 'actual-start', 'pid': os.getpid(), 'original_cells': 1213, 'intervals': 613, 'owners': 7}), flush=True)
    products = analyze(read_inputs())
    bodies = {name: (json.dumps(value, indent=2) + '\n').encode() for name, value in products.items()}
    output.mkdir()
    receipt = {'version': 1, 'complete': True, 'elapsed_seconds': time.monotonic() - started,
               'input_pins_sha256': digest((PACKET / 'input-pins.json').read_bytes()),
               'producer_sha256': digest(Path(__file__).read_bytes()), 'files': []}
    for name, body in bodies.items():
        with (output / name).open('xb') as f:
            f.write(body)
        receipt['files'].append({'path': name, 'bytes': len(body), 'sha256': digest(body)})
    with (output / 'publication.json').open('x') as f:
        json.dump(receipt, f, indent=2)
        f.write('\n')
    print(json.dumps(products['summary.json']), flush=True)


if __name__ == '__main__':
    main()
