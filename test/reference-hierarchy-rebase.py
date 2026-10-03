"""Controls are synthetic contract tests, not new geographic source evidence."""
import copy
import gzip
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('rebase', ROOT / 'scripts/rebase-reference-hierarchy.py')
rebase = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rebase)


def synthetic_tree():
    units, features = [], []
    for number in range(6):
        parent = None
        for tier in reversed(rebase.TIERS[1:]):
            identity = f'{tier}-{number}'
            units.append({'id': identity, 'name': identity, 'level': tier, 'parent_id': parent})
            parent = identity
        identity = f'location-{number}'
        features.append({'id': identity, 'properties': {'id': identity, 'name': identity, 'parent_id': parent},
                         'geometry': {'type': 'Polygon', 'coordinates': [[[0.0, 0], [1, 0], [1, 1], [0.0, 0]]]}})
    return units, features


class RebaseControls(unittest.TestCase):
    def proposal_fixture(self):
        proposal = json.loads(gzip.decompress((ROOT / rebase.PREFIX / 'migration-receipt.json.gz').read_bytes()))
        units = [copy.deepcopy(row['before']) for row in proposal['group_changes']]
        properties = copy.deepcopy(proposal['changed_location_properties'][0]['before_properties'])
        feature = {'id': rebase.HANCOCK, 'properties': properties,
                   'geometry': {'type': 'Polygon', 'coordinates': [[[0.0, 0], [1, 0], [1, 1], [0.0, 0]]]}}
        return units, [feature], proposal

    def test_complete_chains_and_nonmutation(self):
        units, features = synthetic_tree()
        original = copy.deepcopy((units, features))
        members, chains = rebase.inventory(features, units)
        self.assertEqual(len(chains), 6)
        self.assertTrue(all(len(chain) == 6 for chain in chains.values()))
        self.assertTrue(all(len(ids) == 1 for ids in members.values()))
        self.assertEqual((units, features), original)

    def test_skipped_cycle_and_missing_parent_rejected(self):
        for bad_parent in ('region-0', 'province-0', 'absent'):
            units, features = synthetic_tree()
            units[4]['parent_id'] = bad_parent
            with self.assertRaises(ValueError):
                rebase.inventory(features, units)

    def test_duplicate_id_and_empty_group_rejected(self):
        units, features = synthetic_tree()
        for bad_units, bad_features in ((units + [units[0]], features), (units, features + [features[0]]),
                                        (units, features[:-1])):
            with self.assertRaises(ValueError):
                rebase.inventory(bad_features, bad_units)

    def test_exact_merge_preserves_originals_geometry_and_identity(self):
        units, features, proposal = self.proposal_fixture()
        originals = copy.deepcopy((units, features, proposal))
        after_units, after_features = rebase.apply_corrections(units, features, proposal)
        self.assertEqual({u['id'] for u in after_units}, {u['id'] for u in units} - {rebase.RETIRE})
        self.assertEqual(after_features[0]['properties']['parent_id'], rebase.RETAIN)
        self.assertEqual(after_features[0]['geometry'], features[0]['geometry'])
        self.assertEqual((units, features, proposal), originals)

    def test_changed_before_record_and_hancock_properties_rejected(self):
        units, features, proposal = self.proposal_fixture()
        changed = copy.deepcopy(units)
        changed[0]['name'] = 'concurrent changed reference'
        with self.assertRaises(ValueError):
            rebase.apply_corrections(changed, features, proposal)
        features[0]['properties']['name'] = 'changed subject'
        with self.assertRaises(ValueError):
            rebase.apply_corrections(units, features, proposal)

    def test_history_transfer_wrong_endpoint_and_extra_group_rejected(self):
        for mutate in (lambda p: p.update(historical_claims_transferred=True),
                       lambda p: p['relationships'][0].update(new_entity_id=rebase.MONACO),
                       lambda p: p['group_changes'].append(p['group_changes'][0])):
            units, features, proposal = self.proposal_fixture()
            mutate(proposal)
            with self.assertRaises(ValueError):
                rebase.apply_corrections(units, features, proposal)

    def test_nonparent_location_mutation_rejected(self):
        units, features, proposal = self.proposal_fixture()
        proposal['changed_location_properties'][0]['after_properties']['name'] = 'unapproved rename'
        with self.assertRaises(ValueError):
            rebase.apply_corrections(units, features, proposal)

    def test_legacy_hash_contract_is_explicit(self):
        geometries = {'synthetic-é': 'a' * 64}
        result = rebase.member_proof(['synthetic-é'], geometries)
        expected = json.dumps([['synthetic-é', 'a' * 64]], separators=(',', ':')).encode()
        self.assertEqual(result['footprint_sha256'], rebase.sha256(expected))
        self.assertNotEqual(result['footprint_sha256'], rebase.sha256(expected + b'\n'))
        self.assertNotEqual(result['footprint_sha256'], rebase.sha256(json.dumps(
            [['synthetic-é', 'a' * 64]], ensure_ascii=False, separators=(',', ':')).encode()))


if __name__ == '__main__':
    unittest.main()
