"""Bounded actual-input controls; never invokes source downloads or global science."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import subprocess
import os
import unittest

spec = importlib.util.spec_from_file_location('interpret', Path(__file__).with_name('interpret.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class InterpretationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = m.read_inputs()

    def changed(self):
        return copy.deepcopy(self.original)

    def test_complete_result_and_retained_products(self):
        actual = m.analyze(self.original)
        for name, value in actual.items():
            expected = json.loads((m.PACKET / 'results' / name).read_bytes())
            self.assertEqual(value, expected)
        self.assertEqual(actual['summary.json']['unresolved_cells'], 446)
        self.assertEqual(actual['summary.json']['native_repairs'], 0)
        self.assertEqual(actual['summary.json']['question_groups'], 14)

    def test_reused_binding_is_exact(self):
        data = self.original
        pins = data['pins']['inputs']
        binding = data['source_binding']
        self.assertEqual(binding['physical_evidence']['sha256'], pins['whole_physical']['sha256'])
        self.assertEqual(binding['physical_input']['sha256'], pins['selected_stage']['sha256'])
        self.assertEqual(binding['families'][0]['parts'][0]['sha256'], pins['source']['sha256'])
        self.assertEqual(binding['native_latitudes']['sha256'], pins['latitudes']['sha256'])
        roster = {r['source_id']: r for r in data['global_roster'] if r['family_index'] == 167}
        targets = m.unique(binding['targets'], lambda t: t['id'], 'bound target')
        self.assertEqual(set(targets), set(roster))
        for identity, target in targets.items():
            self.assertEqual(target['source_receipt_sha256'], pins['whole_physical']['sha256'])
            self.assertEqual(target['pixelIndex'], roster[identity]['owners'][0])
        constructor = data['constructor']
        rows = m.unique(constructor['ledger_rows'], lambda r: r['target_id'], 'constructor target')
        self.assertEqual(set(rows), set(targets))
        self.assertEqual(sum(r['native_cells'] for r in rows.values()), 2251)
        for identity, row in rows.items():
            self.assertEqual(row['source_receipt_sha256'], pins['whole_physical']['sha256'])
            self.assertEqual(row['base_geometry'], targets[identity]['base_geometry'])

    def test_exact_accepted_and_repair_disjointness(self):
        record = json.loads((m.PACKET / 'patch-conservation.json').read_bytes())
        inputs = {}
        for role, pin in record['input_pins'].items():
            body = subprocess.check_output(['git', '--no-replace-objects', 'show', pin['commit'] + ':' + pin['path']],
                env=dict(os.environ, GIT_NO_LAZY_FETCH='1', GIT_NO_REPLACE_OBJECTS='1'))
            self.assertEqual(len(body), pin['bytes'])
            self.assertEqual(m.digest(body), pin['sha256'])
            inputs[role] = json.loads(body)
        self.assertEqual(inputs['accepted_selector']['additive_release']['sha256'], record['input_pins']['accepted_sidecar']['sha256'])
        self.assertEqual(inputs['accepted_sidecar']['logical_asset_map']['patch']['sha256'], record['input_pins']['accepted_patch']['sha256'])
        points = {(y, x) for y, start, end, *_ in self.original['intervals'] for x in range(start, end)}
        def cells(patch):
            return {(r['y'], x) for r in patch['rows'] for start, end, owner in r['runs'] for x in range(start, end)}
        accepted = cells(inputs['accepted_patch'])
        jamaica = cells(inputs['jamaica_repair_patch'])
        self.assertEqual(len(points), record['review_cells'])
        self.assertEqual(len(accepted), record['accepted_additive_cells'])
        self.assertEqual(len(jamaica), record['jamaica_repair_cells'])
        self.assertEqual(len(points & accepted), record['accepted_intersection_cells'])
        self.assertEqual(len(points & jamaica), record['jamaica_repair_intersection_cells'])
        self.assertEqual(len(points & (accepted | jamaica)), record['union_intersection_cells'])
        self.assertEqual(record['union_intersection_cells'], 0)
        # Positive contact control consumes an actual candidate, not a changed
        # expected digest or a hardcoded success flag.
        changed = accepted | {next(iter(points))}
        self.assertEqual(len(points & changed), 1)

    def test_duplicate_actual_interval_is_rejected(self):
        data = self.changed()
        data['intervals'].append(data['intervals'][0])
        with self.assertRaisesRegex(ValueError, 'Duplicate/missing'):
            m.analyze(data)

    def test_missing_actual_interval_is_rejected(self):
        data = self.changed()
        data['intervals'].pop()
        with self.assertRaisesRegex(ValueError, 'Duplicate/missing'):
            m.analyze(data)

    def test_wrong_interval_owner_is_rejected(self):
        data = self.changed()
        data['intervals'][0][3] = [24187]
        with self.assertRaisesRegex(ValueError, 'Exact original review scope'):
            m.analyze(data)

    def test_missing_zero_candidate_competitor_is_rejected(self):
        data = self.changed()
        data['source']['features'] = [f for f in data['source']['features'] if f['properties']['shapeName'] != 'Manchester']
        with self.assertRaisesRegex(ValueError, 'Full source/target/physical join'):
            m.analyze(data)

    def test_duplicate_physical_target_is_rejected(self):
        data = self.changed()
        data['whole_physical']['results'].append(data['whole_physical']['results'][0])
        with self.assertRaisesRegex(ValueError, 'Duplicate physical target'):
            m.analyze(data)

    def test_changed_consumed_original_is_rejected(self):
        data = self.changed()
        data['selected_stage'][0]['consumed']['properties']['shapeID'] = 'foreign'
        with self.assertRaisesRegex(ValueError, 'Whole-target consumed input'):
            m.analyze(data)

    def test_positive_land_witness_is_not_hidden(self):
        data = self.changed()
        data['whole_physical']['results'][0]['support']['mapped_land_support'] = data['source']['features'][0]['geometry']
        with self.assertRaisesRegex(ValueError, 'Changed physical witness classification'):
            m.analyze(data)

    def test_real_residual_contact_is_not_hidden(self):
        data = self.changed()
        data['whole_physical']['results'][0]['issues'].append({'kind': 'missing_reconstruction', 'geometry': data['source']['features'][0]['geometry']})
        with self.assertRaisesRegex(ValueError, 'Residual witness contact'):
            m.analyze(data)

    def test_output_collision_and_symlink_preserve_sentinel(self):
        with tempfile.TemporaryDirectory(dir=m.PACKET.parent) as directory:
            parent = Path(directory)
            output = parent / 'existing'
            output.mkdir()
            sentinel = output / 'sentinel'
            sentinel.write_bytes(b'original evidence')
            with self.assertRaisesRegex(ValueError, 'Fresh output'):
                m.admit_output(output)
            attempt = subprocess.run([os.sys.executable, '-B', str(m.PACKET / 'interpret.py'), str(output)], capture_output=True)
            self.assertNotEqual(attempt.returncode, 0)
            self.assertIn(b'Fresh output directory required', attempt.stderr)
            self.assertEqual(sentinel.read_bytes(), b'original evidence')
            link = parent / 'dangling'
            link.symlink_to(parent / 'missing')
            with self.assertRaisesRegex(ValueError, 'Symlink'):
                m.admit_output(link)
            attempt = subprocess.run([os.sys.executable, '-B', str(m.PACKET / 'interpret.py'), str(link)], capture_output=True)
            self.assertNotEqual(attempt.returncode, 0)
            self.assertIn(b'Symlink output path refused', attempt.stderr)
            self.assertTrue(link.is_symlink())
            self.assertFalse((parent / 'missing').exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
