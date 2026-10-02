#!/usr/bin/env python3
"""Focused reference migration tests; no database or live geography is modified."""
import copy
import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
loader = importlib.util.spec_from_file_location('macro', ROOT / 'scripts/prepare-global-macro-geography.py')
macro = importlib.util.module_from_spec(loader)
loader.loader.exec_module(macro)
EVIDENCE = [{'url': 'https://example.org/source', 'source_sha256': 'a' * 64}]


def fixture():
    groups = [('c', 'continent', None), ('s', 'subcontinent', 'c'),
              ('r', 'region', 's'), ('a', 'area', 'r'),
              ('p', 'province', 'a'), ('q', 'province', 'a')]
    units = {i: {'id': i, 'name': i, 'level': level, 'parent_id': parent,
                 'metadata': {'retained': {'full': ['original', i]}, 'child_count': 2 if i == 'a' else 1}}
             for i, level, parent in groups}
    features = [{'id': i, 'type': 'Feature', 'geometry': {'type': 'Polygon', 'coordinates': [[[0, 0], [1, 0], [1, 1], [0, 0]]]},
                 'properties': {'id': i, 'name': 'Original ' + i, 'parent_id': parent,
                                'metadata': {'source': 'original'}, 'reference_owner': 'unchanged'}}
                for i, parent in [('x', 'p'), ('y', 'q')]]
    return units, features


class MacroMigration(unittest.TestCase):
    def test_parent_repair_preserves_full_history_context_and_retires_empty_province(self):
        units, features = fixture()
        original = copy.deepcopy((units, features))
        new, after, receipt = macro.apply_stage(units, features,
            {'location_changes': [{'id': 'x', 'old_parent_id': 'p', 'parent_id': 'q'}]}, EVIDENCE, 'repairs')
        self.assertEqual((units, features), original)
        self.assertEqual(receipt['before_units'], [original[0][i] for i in sorted(original[0])])
        self.assertEqual(receipt['retired_units'], [original[0]['p']])
        self.assertEqual(receipt['relationships'], [macro.relationship('retire', 'p', None)])
        self.assertEqual(after[0]['geometry'], features[0]['geometry'])
        self.assertEqual(after[0]['properties'], {**features[0]['properties'], 'parent_id': 'q'})
        self.assertEqual(receipt['summary']['geometry_changes'], 0)
        self.assertEqual(new['r'], original[0]['r'])

    def test_area_split_then_region_split_preserves_exact_before_records(self):
        units, features = fixture()
        targets = [{'id': 'a1', 'name': 'North', 'member_ids': ['p']},
                   {'id': 'a2', 'name': 'South', 'member_ids': ['q']}]
        after, locations, first = macro.apply_stage(units, features,
            {'splits': [{'old_id': 'a', 'children': targets}]}, EVIDENCE, 'areas')
        self.assertEqual({r['change_type'] for r in first['relationships']}, {'split'})
        self.assertEqual(first['changed_location_properties'], [])
        self.assertTrue(all(r['before'] is None for r in first['group_changes'] if r['id'] in ['a1', 'a2']))
        final, locations, second = macro.apply_stage(after, locations,
            {'splits': [{'old_id': 'r', 'children': [
                {'id': 'r1', 'name': 'Northern region', 'area_ids': ['a1']},
                {'id': 'r2', 'name': 'Southern region', 'area_ids': ['a2']}]}]}, EVIDENCE, 'regions')
        self.assertEqual(second['before_units'], [after[i] for i in sorted(after)])
        self.assertEqual(final['a1']['parent_id'], 'r1')
        self.assertEqual(final['a2']['parent_id'], 'r2')
        self.assertEqual(len(macro.check(final, locations)), 2)

    def test_split_rejects_missing_repeated_foreign_and_cross_parent_members(self):
        units, features = fixture()
        invalid = [
            [{'id': 'a1', 'name': 'One', 'member_ids': ['p']}, {'id': 'a2', 'name': 'Two', 'member_ids': ['p']}],
            [{'id': 'a1', 'name': 'One', 'member_ids': ['p']}, {'id': 'a2', 'name': 'Two', 'member_ids': ['unknown']}],
            [{'id': 'a1', 'name': 'One', 'member_ids': ['p']}, {'id': 'a2', 'name': 'Two', 'member_ids': []}],
            [{'id': 'a1', 'name': 'One', 'member_ids': ['p'], 'parent_id': 's'}, {'id': 'a2', 'name': 'Two', 'member_ids': ['q']}]]
        for targets in invalid:
            with self.subTest(targets=targets), self.assertRaises(ValueError):
                macro.apply_stage(units, features, {'splits': [{'old_id': 'a', 'children': targets}]}, EVIDENCE, 'areas')

    def test_split_rejects_incomplete_nonempty_partition(self):
        units, features = fixture()
        units['z'] = {**units['p'], 'id': 'z', 'name': 'Third province'}
        features.append({**features[0], 'id': 'third',
                         'properties': {**features[0]['properties'], 'id': 'third', 'parent_id': 'z'}})
        with self.assertRaisesRegex(ValueError, 'conserve exact member inventory'):
            macro.apply_stage(units, features, {'splits': [{'old_id': 'a', 'children': [
                {'id': 'a1', 'name': 'One', 'member_ids': ['p']},
                {'id': 'a2', 'name': 'Two', 'member_ids': ['q']}]}]}, EVIDENCE, 'areas')

    def test_created_geographic_portion_has_creation_crosswalk(self):
        units, features = fixture()
        portion = {'id': 'new', 'name': 'Geographic portion', 'level': 'province', 'parent_id': 'a',
                   'metadata': {'derived_from_id': 'p'}}
        _, _, receipt = macro.apply_stage(units, features,
            {'new_groups': [portion], 'location_changes': [{'id': 'x', 'old_parent_id': 'p', 'parent_id': 'new'}]}, EVIDENCE, 'repairs')
        self.assertIn(macro.relationship('create', None, 'new', 'p'), receipt['relationships'])
        self.assertIn(macro.relationship('retire', 'p', None), receipt['relationships'])
        self.assertEqual(next(r for r in receipt['group_changes'] if r['id'] == 'new')['before'], None)

    def test_stale_proposals_and_empty_macro_are_rejected(self):
        units, features = fixture()
        with self.assertRaisesRegex(ValueError, 'Stale location parent'):
            macro.apply_stage(units, features, {'location_changes': [{'id': 'x', 'old_parent_id': 'q', 'parent_id': 'p'}]}, EVIDENCE, 'repairs')
        with self.assertRaisesRegex(ValueError, 'Empty geographic unit'):
            macro.apply_stage(units, features, {'new_groups': [{'id': 'empty', 'name': 'Empty', 'level': 'region', 'parent_id': 's'}]}, EVIDENCE, 'repairs')

    def test_untouched_metadata_including_legacy_child_count_is_preserved(self):
        units, features = fixture()
        units['a']['metadata']['child_count'] = 900
        after, _, receipt = macro.apply_stage(units, features, {}, EVIDENCE, 'repairs')
        self.assertEqual(after, units)
        self.assertEqual(receipt['group_changes'], [])


if __name__ == '__main__':
    unittest.main()
