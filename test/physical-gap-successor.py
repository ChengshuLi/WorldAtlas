"""Fail-closed fixture controls for immutable physical-gap tile reuse."""
import copy
import hashlib
import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'scripts'))
from evidence.immutable import descriptor, deterministic_gzip
from physical_gap_successor import (VERSION, build_reuse_plan, decode_gzip_layers,
                                    reuse_decision, verify_decoded_relation, verify_snapshot)


def snapshot(commit, *, geometry='a' * 64, order=('land:1',), status='checked', unknowns=(), semantics=None):
    geometry_raw = bytes.fromhex(geometry)
    raw = {'source.json': b'{"full":"source bytes"}\n',
           'code.py': b'# committed code\n', 'software.json': b'{"runtime":"pinned"}\n',
           'domain.json': b'{"extent":[0,0,1,1]}\n', 'hierarchy.json': b'{"hierarchy":"pinned"}\n',
           'release.json': b'{"release":"pinned"}\n', 'native-owner.json': b'{"owners":"pinned"}\n',
           'tiles.json': b'{"tile_ids":["tile-0"]}\n', 'geometry/land-1.wkb': geometry_raw,
           'metadata/land-1.json': b'{"name":"exact metadata"}\n',
           'tile/candidates.json': b'{"candidate":"all exact bytes"}\n',
           'tile/residues.json': b'{"tiny_line_point":"all retained"}\n',
           'tile/physical-shore.json': b'{"shore":"retained"}\n',
           'tile/missing-digest.txt': b'0123456789abcdef\n',
           'tile/water-diagnostics.json': b'{"water":"diagnostic only"}\n',
           'tile/blocked.json': b'{"blocked_sources":["invalid land"]}\n'}
    if status == 'unchecked':
        output_roles, output_paths = ['blocked_sources'], ['tile/blocked.json']
    else:
        output_roles = ['candidates', 'residues', 'physical_shore', 'missing_geometry_sha256', 'invalid_water_diagnostics']
        output_paths = ['tile/candidates.json', 'tile/residues.json', 'tile/physical-shore.json',
                        'tile/missing-digest.txt', 'tile/water-diagnostics.json']
    layered_order = {'land': list(order), 'locations': [], 'invalid_land': [],
                     'invalid_locations': [], 'invalid_water': [], 'shorelines': []}
    tile = {'tile_id': 'tile-0', 'bounds': [0, 0, 1, 1], 'query_order': layered_order,
            'members': [{'kind': 'land', 'id': identity, 'source_commit': commit,
                         'geometry_file': descriptor('geometry/land-1.wkb', geometry_raw),
                         'metadata_file': descriptor('metadata/land-1.json', raw['metadata/land-1.json'])}
                        for identity in order],
            'status': status, 'unknowns': list(unknowns),
            'outputs': [{'role': role, 'source_commit': commit, 'file': descriptor(path, raw[path])}
                        for role, path in zip(output_roles, output_paths)]}
    role_by_name = {'source.json':'source:world-index', 'code.py':'code:detector', 'software.json':'software',
                    'domain.json':'domain', 'hierarchy.json':'hierarchy', 'release.json':'release',
                    'native-owner.json':'native_owner', 'tiles.json':'tile-roster',
                    'geometry/land-1.wkb':'geometry:land:1', 'tile/candidates.json':'tile-output:tile-0:candidates',
                    'tile/residues.json':'tile-output:tile-0:residues', 'metadata/land-1.json':'member-metadata:land:1',
                    'tile/physical-shore.json':'tile-output:tile-0:physical_shore',
                    'tile/missing-digest.txt':'tile-output:tile-0:missing_geometry_sha256',
                    'tile/water-diagnostics.json':'tile-output:tile-0:invalid_water_diagnostics',
                    'tile/blocked.json':'tile-output:tile-0:blocked_sources'}
    value = {'version': VERSION, 'snapshot_id': commit, 'source_commits': [commit],
             'files': [{'source_commit': commit, 'role': role_by_name[name],
                        'file': descriptor(name, data)} for name, data in raw.items()],
             'semantics': semantics or {'algorithm': 'detector-v1', 'parameters': {'domain': [-180, -60, 180, 85.0511287798066]},
                                        'software': {'python': '3.12.14', 'shapely': '2.1.2', 'geos': '3.13.1'},
                                        'domain': [-180, -60, 180, 85.0511287798066],
                                        'land_input_policy': {'repair': False}, 'location_input_policy': {'repair': False},
                                        'invalid_input_policy': {'preserve_unknown': True},
                                        'tile_query_policy': {'predicate': 'intersects', 'order': 'exact'},
                                        'physical_union_policy': {'global_union': True}},
             'provenance': {'hierarchy': {'source_commit': commit, 'file': descriptor('hierarchy.json', raw['hierarchy.json'])},
                            'release': {'source_commit': commit, 'file': descriptor('release.json', raw['release.json'])},
                            'native_owner': {'source_commit': commit, 'file': descriptor('native-owner.json', raw['native-owner.json'])}},
             'tiles': [tile]}
    return value, {commit + ':' + name: data for name, data in raw.items()}


class SuccessorReuseControls(unittest.TestCase):
    def setUp(self):
        self.old, self.old_files = snapshot('1' * 40)
        self.new, self.new_files = snapshot('2' * 40)

    def decision(self, **kwargs):
        return reuse_decision(self.old, self.new, self.old_files, self.new_files, 'tile-0', **kwargs)

    def replace_geometry(self, snapshot_value, files, geometry_bytes):
        commit = snapshot_value['snapshot_id']
        key = commit + ':geometry/land-1.wkb'
        files[key] = geometry_bytes
        row = descriptor('geometry/land-1.wkb', geometry_bytes)
        next(x for x in snapshot_value['files'] if x['file']['path'] == 'geometry/land-1.wkb')['file'] = row
        for member in snapshot_value['tiles'][0]['members']:
            member['geometry_file'] = row

    def replace_metadata(self, snapshot_value, files, metadata_bytes):
        commit = snapshot_value['snapshot_id']
        key = commit + ':metadata/land-1.json'
        files[key] = metadata_bytes
        row = descriptor('metadata/land-1.json', metadata_bytes)
        next(x for x in snapshot_value['files'] if x['file']['path'] == 'metadata/land-1.json')['file'] = row
        for member in snapshot_value['tiles'][0]['members']:
            member['metadata_file'] = row

    def test_exact_complete_snapshot_reuses_original_candidate_and_residue_bytes(self):
        decision = self.decision()
        self.assertEqual(decision['status'], 'reuse-original-output-bytes')
        self.assertEqual({row['role'] for row in decision['outputs']}, {
            'candidates', 'residues', 'physical_shore', 'missing_geometry_sha256', 'invalid_water_diagnostics'})
        self.assertEqual(decision['outputs'][0]['sha256'], hashlib.sha256(self.old_files['1' * 40 + ':tile/candidates.json']).hexdigest())

    def test_successor_can_decide_before_writing_new_tile_products(self):
        generated_paths = {row['file']['path'] for row in self.new['files'] if row['role'].startswith('tile-output:')}
        self.new['files'] = [row for row in self.new['files'] if row['file']['path'] not in generated_paths]
        self.new['tiles'][0]['outputs'] = []
        self.new_files = {key: raw for key, raw in self.new_files.items()
                          if key.split(':', 1)[1] not in generated_paths}
        self.assertEqual(self.decision()['status'], 'reuse-original-output-bytes')

    def test_unpinned_source_commit_binding_is_rejected(self):
        self.new['files'][0]['source_commit'] = 'f' * 40
        with self.assertRaisesRegex(ValueError, 'not bound to a pinned'):
            self.decision()

    def test_code_and_outputs_must_bind_to_the_execution_commit(self):
        self.old['source_commits'] = ['f' * 40]
        source = next(row for row in self.old['files'] if row['role'].startswith('source:'))
        source['source_commit'] = 'f' * 40
        self.old_files['f' * 40 + ':' + source['file']['path']] = self.old_files.pop('1' * 40 + ':' + source['file']['path'])
        code = next(row for row in self.old['files'] if row['role'].startswith('code:'))
        code['source_commit'] = 'f' * 40
        self.old_files['f' * 40 + ':' + code['file']['path']] = self.old_files.pop('1' * 40 + ':' + code['file']['path'])
        with self.assertRaisesRegex(ValueError, 'Executed code and tile outputs'):
            verify_snapshot(self.old, self.old_files)

    def test_foreign_output_commit_and_role_laundering_are_rejected(self):
        foreign = 'f' * 40
        snapshot_value = copy.deepcopy(self.old)
        payloads = dict(self.old_files)
        snapshot_value['source_commits'] = [foreign]
        for row in snapshot_value['files']:
            if row['role'] == 'source:world-index':
                old_key = '1' * 40 + ':' + row['file']['path']
                payloads[foreign + ':' + row['file']['path']] = payloads.pop(old_key)
                row['source_commit'] = foreign
        for output in snapshot_value['tiles'][0]['outputs']:
            output['source_commit'] = foreign
            payloads[foreign + ':' + output['file']['path']] = payloads.pop(
                '1' * 40 + ':' + output['file']['path'])
            closure = next(row for row in snapshot_value['files']
                           if row['file'] == output['file'])
            closure['source_commit'] = foreign
            closure['role'] = 'source:foreign-' + output['role']
        with self.assertRaisesRegex(ValueError, 'Tile output is not bound to the snapshot execution commit'):
            verify_snapshot(snapshot_value, payloads)

    def test_output_cannot_use_execution_commit_with_a_laundered_closure_role(self):
        row = self.old['tiles'][0]['outputs'][0]
        closure = next(item for item in self.old['files'] if item['file'] == row['file'])
        closure['role'] = 'source:foreign-' + row['role']
        with self.assertRaisesRegex(ValueError, 'Tile output lacks its exact execution-bound closure role'):
            verify_snapshot(self.old, self.old_files)

    def test_checked_output_bundle_cannot_omit_native_detector_diagnostics(self):
        self.old['tiles'][0]['outputs'] = [row for row in self.old['tiles'][0]['outputs']
                                           if row['role'] != 'invalid_water_diagnostics']
        with self.assertRaisesRegex(ValueError, 'omits required detector products'):
            verify_snapshot(self.old, self.old_files)

    def test_duplicate_output_role_is_rejected(self):
        self.new['tiles'][0]['outputs'].append(copy.deepcopy(self.new['tiles'][0]['outputs'][0]))
        with self.assertRaisesRegex(ValueError, 'Duplicate tile output role'):
            self.decision()

    def test_output_roles_cannot_alias_one_payload(self):
        alias = copy.deepcopy(self.new['tiles'][0]['outputs'][0])
        alias['role'] = 'different-output-label'
        self.new['tiles'][0]['outputs'].append(alias)
        with self.assertRaisesRegex(ValueError, 'exact execution-bound closure role'):
            self.decision()

    def test_changed_exact_member_geometry_forces_recompute_even_with_same_bbox_order(self):
        self.replace_geometry(self.new, self.new_files, bytes.fromhex('f' * 64))
        self.assertEqual(self.decision()['reason'], 'tile-operands-or-unknown-state-changed')

    def test_changed_query_order_forces_recompute(self):
        self.old['tiles'][0]['query_order']['land'] = ['land:1', 'land:2']
        self.old['tiles'][0]['members'].append({'kind': 'land', 'id': 'land:2', 'source_commit': '1' * 40,
                                               'geometry_file': self.old['tiles'][0]['members'][0]['geometry_file'],
                                               'metadata_file': self.old['tiles'][0]['members'][0]['metadata_file']})
        self.new['tiles'][0]['query_order']['land'] = ['land:2', 'land:1']
        self.new['tiles'][0]['members'].insert(0, {'kind': 'land', 'id': 'land:2', 'source_commit': '2' * 40,
                                                  'geometry_file': self.new['tiles'][0]['members'][0]['geometry_file'],
                                                  'metadata_file': self.new['tiles'][0]['members'][0]['metadata_file']})
        self.assertEqual(self.decision()['reason'], 'tile-operands-or-unknown-state-changed')

    def test_changed_query_metadata_forces_recompute_even_with_identical_geometry(self):
        self.replace_metadata(self.new, self.new_files, b'{"name":"changed metadata"}\n')
        self.assertEqual(self.decision()['reason'], 'tile-operands-or-unknown-state-changed')

    def test_changed_executed_code_bytes_force_recompute(self):
        raw = b'# a different detector implementation\n'
        self.new_files['2' * 40 + ':code.py'] = raw
        next(x for x in self.new['files'] if x['role'] == 'code:detector')['file'] = descriptor('code.py', raw)
        self.assertEqual(self.decision()['reason'], 'execution-code-runtime-or-domain-bytes-changed')

    def test_boolean_and_integer_semantics_are_not_equated(self):
        self.old['semantics']['parameters'] = {'control': True}
        self.new['semantics']['parameters'] = {'control': 1}
        self.assertEqual(self.decision()['reason'], 'global-semantics-changed')

    def test_changed_code_software_domain_hierarchy_release_or_native_pin_forces_recompute(self):
        for key in ['algorithm', 'domain', 'software', 'parameters', 'land_input_policy',
                    'location_input_policy', 'invalid_input_policy', 'tile_query_policy', 'physical_union_policy']:
            with self.subTest(key=key):
                old, old_files = snapshot('1' * 40)
                new, new_files = snapshot('2' * 40)
                value = new['semantics'][key]
                if isinstance(value, dict):
                    new['semantics'][key] = {**value, 'changed': True}
                elif isinstance(value, list):
                    new['semantics'][key] = [0, 0, 2, 1] if key == 'domain' else [*value, 123.0]
                else:
                    new['semantics'][key] = value + '-changed'
                self.assertEqual(reuse_decision(old, new, old_files, new_files, 'tile-0')['reason'],
                                 'global-semantics-changed')

    def test_release_hierarchy_and_native_pointer_changes_are_authenticated_but_not_geometry_dependencies(self):
        for name, key in [('release.json', 'release'), ('data/hierarchy.json', 'hierarchy'),
                          ('native-owner.json', 'native_owner')]:
            with self.subTest(key=key):
                old, old_files = snapshot('1' * 40)
                new, new_files = snapshot('2' * 40)
                raw = ('changed ' + key).encode()
                path = old['provenance'][key]['file']['path']
                # Keep the provenance file path/role fixed, while binding a different actual byte vintage.
                new_key = '2' * 40 + ':' + path
                new_files[new_key] = raw
                row = descriptor(path, raw)
                next(x for x in new['files'] if x['file']['path'] == path)['file'] = row
                new['provenance'][key]['file'] = row
                self.assertEqual(reuse_decision(old, new, old_files, new_files, 'tile-0')['status'],
                                 'reuse-original-output-bytes')

    def test_changed_unknown_state_forces_recompute(self):
        self.new['tiles'][0]['status'] = 'unchecked'
        self.new['tiles'][0]['unknowns'] = [{'reason': 'invalid source'}]
        self.assertEqual(self.decision()['reason'], 'tile-operands-or-unknown-state-changed')

    def test_exact_unknown_tile_can_reuse_only_while_remaining_unknown(self):
        old, old_files = snapshot('1' * 40, status='unchecked', unknowns=[{'id': 'source:bad', 'reason': 'invalid'}])
        new, new_files = snapshot('2' * 40, status='unchecked', unknowns=[{'id': 'source:bad', 'reason': 'invalid'}])
        result = reuse_decision(old, new, old_files, new_files, 'tile-0')
        self.assertEqual(result['status'], 'reuse-original-output-bytes')
        self.assertEqual(result['preserved_status'], 'unchecked')
        self.assertEqual(result['preserved_unknowns'], [{'id': 'source:bad', 'reason': 'invalid'}])

    def test_boolean_and_integer_unknowns_are_not_equated(self):
        old, old_files = snapshot('1' * 40, status='unchecked', unknowns=[{'flag': True}])
        new, new_files = snapshot('2' * 40, status='unchecked', unknowns=[{'flag': 1}])
        self.assertEqual(reuse_decision(old, new, old_files, new_files, 'tile-0')['reason'],
                         'tile-operands-or-unknown-state-changed')

    def test_unchecked_tile_without_retained_cause_is_rejected(self):
        self.old['tiles'][0]['status'] = 'unchecked'
        with self.assertRaisesRegex(ValueError, 'discarded its blocking'):
            verify_snapshot(self.old, self.old_files)

    def test_forced_recompute_cannot_be_overridden_by_identical_operands(self):
        self.assertEqual(self.decision(force_recompute={'tile-0'})['reason'], 'explicit-force-recompute')

    def test_plan_accounts_for_reuse_pending_recompute_and_preview_status(self):
        plan = build_reuse_plan(self.old, self.new, self.old_files, self.new_files)
        self.assertEqual(plan['status'], 'preview-not-installed')
        self.assertEqual(plan['tile_decision_count'], 1)
        self.assertEqual(plan['decision_counts'], {'reuse-original-output-bytes': 1})
        self.assertEqual(plan['tiles'][0]['tile_id'], 'tile-0')
        forced = build_reuse_plan(self.old, self.new, self.old_files, self.new_files, {'tile-0'})
        self.assertEqual(forced['decision_counts'], {'recompute': 1})

    def test_plan_marks_new_tiles_as_pending_and_keeps_existing_tiles(self):
        tile = copy.deepcopy(self.new['tiles'][0])
        tile['tile_id'] = 'tile-1'
        tile['bounds'] = [1, 0, 2, 1]
        tile['query_order']['land'] = []
        tile['members'] = []
        tile['outputs'] = []
        self.new['tiles'].append(tile)
        roster_raw = b'{"tile_ids":["tile-0","tile-1"]}\n'
        self.new_files['2' * 40 + ':tiles.json'] = roster_raw
        next(row for row in self.new['files'] if row['role'] == 'tile-roster')['file'] = descriptor('tiles.json', roster_raw)
        plan = build_reuse_plan(self.old, self.new, self.old_files, self.new_files)
        self.assertEqual(plan['tile_decision_count'], 2)
        self.assertEqual(plan['decision_counts'], {'reuse-original-output-bytes': 1, 'recompute': 1})
        self.assertEqual(plan['tiles'][1]['reason'], 'new-tile')

    def test_plan_indexes_large_tile_rosters_and_preserves_every_decision(self):
        def expand(value, payloads, count):
            rows = [copy.deepcopy(value['tiles'][0])]
            for index in range(1, count):
                tile_id = f'tile-{index}'
                tile = copy.deepcopy(value['tiles'][0])
                tile['tile_id'] = tile_id
                for output in tile['outputs']:
                    previous_path = output['file']['path']
                    raw = payloads[output['source_commit'] + ':' + previous_path]
                    role = output['role']
                    path = f'tile/{index}-{role}.json'
                    row = descriptor(path, raw)
                    output['file'] = row
                    value['files'].append({'source_commit': value['snapshot_id'],
                                           'role': f'tile-output:{tile_id}:{role}', 'file': row})
                    payloads[value['snapshot_id'] + ':' + path] = raw
                rows.append(tile)
            value['tiles'] = rows
            roster = {'tile_ids': [row['tile_id'] for row in rows]}
            raw_roster = (json.dumps(roster, separators=(',', ':')) + '\n').encode()
            payloads[value['snapshot_id'] + ':tiles.json'] = raw_roster
            roster_row = next(row for row in value['files'] if row['role'] == 'tile-roster')
            roster_row['file'] = descriptor('tiles.json', raw_roster)
            return rows

        count = 2048
        expand(self.old, self.old_files, count)
        expand(self.new, self.new_files, count)
        plan = build_reuse_plan(self.old, self.new, self.old_files, self.new_files)
        self.assertEqual(plan['tile_decision_count'], count)
        self.assertEqual(plan['decision_counts'], {'reuse-original-output-bytes': count})
        self.assertEqual([row['tile_id'] for row in plan['tiles']], [f'tile-{i}' for i in range(count)])

    def test_tampered_source_file_rejects_before_reuse(self):
        self.new_files['2' * 40 + ':source.json'] += b'changed'
        with self.assertRaisesRegex(ValueError, 'do not match'):
            self.decision()

    def test_tampered_old_output_rejects_before_reuse(self):
        self.old_files['1' * 40 + ':tile/residues.json'] += b'dropped remnant'
        with self.assertRaisesRegex(ValueError, 'do not match'):
            self.decision()

    def test_omitted_or_extra_snapshot_bytes_are_rejected(self):
        del self.new_files['2' * 40 + ':source.json']
        with self.assertRaisesRegex(ValueError, 'no retained'):
            self.decision()
        self.new_files['2' * 40 + ':source.json'] = b'{"full":"source bytes"}\n'
        self.new_files['2' * 40 + ':invented'] = b'extra'
        with self.assertRaisesRegex(ValueError, 'incomplete, or expanded'):
            self.decision()

    def test_tile_output_missing_from_closure_is_rejected(self):
        self.new['files'] = [row for row in self.new['files'] if row['file']['path'] != 'tile/residues.json']
        self.new_files.pop('2' * 40 + ':tile/residues.json')
        with self.assertRaisesRegex(ValueError, 'exact execution-bound closure role'):
            self.decision()

    def test_tiny_geometry_fingerprint_is_not_area_filtered(self):
        self.replace_geometry(self.old, self.old_files, b'polygon area 1e-24')
        self.replace_geometry(self.new, self.new_files, b'polygon area 1e-24')
        self.old_files['1' * 40 + ':tile/residues.json'] = b'{"tiny_polygon_area":1e-24,"line":true,"point":true}\n'
        self.new_files['2' * 40 + ':tile/residues.json'] = self.old_files['1' * 40 + ':tile/residues.json']
        for snap, files in [(self.old, self.old_files), (self.new, self.new_files)]:
            commit = snap['snapshot_id']
            row = next(x for x in snap['files'] if x['file']['path'] == 'tile/residues.json')
            row['file'] = descriptor('tile/residues.json', files[commit + ':tile/residues.json'])
            snap['tiles'][0]['outputs'][1]['file'] = descriptor('tile/residues.json', files[commit + ':tile/residues.json'])
        self.assertEqual(self.decision()['status'], 'reuse-original-output-bytes')

    def test_global_semantics_cannot_be_asserted_by_boolean(self):
        self.new['verified'] = True
        with self.assertRaisesRegex(ValueError, 'unknown or missing field'):
            self.decision()

    def test_duplicate_member_or_output_roles_are_rejected(self):
        self.new['tiles'][0]['query_order']['land'].append('land:1')
        self.new['tiles'][0]['members'].append(copy.deepcopy(self.new['tiles'][0]['members'][0]))
        with self.assertRaisesRegex(ValueError, 'Duplicate or malformed layered query order'):
            self.decision()


class DecodedSourceControls(unittest.TestCase):
    def test_nested_gzip_retains_both_exact_whole_byte_layers(self):
        decoded = b'{ "original": [1.000, true, null] }\n'
        encoded = deterministic_gzip(deterministic_gzip(decoded))
        record = verify_decoded_relation(descriptor('source.gz.gz', encoded), encoded,
                                         descriptor('source.json', decoded), decoded, 2)
        self.assertEqual(record['decoded_sha256'], hashlib.sha256(decoded).hexdigest())
        self.assertEqual(decode_gzip_layers(encoded, 2), decoded)

    def test_truncation_trailing_data_wrong_layer_count_and_changed_decoded_bytes_fail(self):
        decoded = b'complete source bytes\n'
        encoded = deterministic_gzip(decoded)
        with self.assertRaisesRegex(ValueError, 'not a valid gzip|truncated'):
            decode_gzip_layers(encoded[:-2], 1)
        with self.assertRaisesRegex(ValueError, 'trailing bytes'):
            decode_gzip_layers(encoded + b'unclaimed tail', 1)
        with self.assertRaisesRegex(ValueError, 'not a valid gzip'):
            decode_gzip_layers(encoded, 2)
        changed = b'changed source bytes\n'
        with self.assertRaisesRegex(ValueError, 'do not equal'):
            verify_decoded_relation(descriptor('source.gz', encoded), encoded,
                                    descriptor('source.json', changed), changed, 1)

    def test_invalid_gzip_layer_counts_fail_closed(self):
        for layers in [0, -1, 4, True, 1.0]:
            with self.subTest(layers=layers), self.assertRaisesRegex(ValueError, 'layer count'):
                decode_gzip_layers(b'irrelevant', layers)


if __name__ == '__main__':
    unittest.main()
