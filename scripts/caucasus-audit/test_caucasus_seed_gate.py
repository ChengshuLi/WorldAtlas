import hashlib
import json
import tempfile
import unittest
import sys
from pathlib import Path
from unittest.mock import patch

import caucasus_seed_gate as gate


class SourceGateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        sources = [{'source_id': k[0], 'version': k[1], 'sha256': v,
                    'r2_bucket': gate.SOURCE_LOCATIONS[k][0], 'r2_key': gate.SOURCE_LOCATIONS[k][1],
                    'size_bytes': gate.SOURCE_LOCATIONS[k][2]} for k, v in gate.SOURCE_PINS.items()]
        snapshot = {'schema': 'worldatlas-geography-decision-draft-evidence-v1', 'source': 'neon-export',
                    'sources': sources, 'mainland_boundaries': [{'boundary_id': gate.BOUNDARY,
                    'execution_status': 'selected_for_research', 'geometry': {}, 'geometry_sha256': '0' * 64,
                    'provenance': {'source_refs': [{'source_id': s['source_id'], 'version': s['version']} for s in sources]}}]}
        self.snapshot = self.root / 'snapshot.json'
        self.snapshot.write_text(json.dumps(snapshot))
        self.request = self.root / 'request.json'
        self.request.write_text(json.dumps({'inputs': {'snapshot': {'path': str(self.snapshot), 'sha256': gate.digest(self.snapshot)}}}))

    def tearDown(self):
        self.tmp.cleanup()

    def test_snapshot_tampering_rejected_before_assembly(self):
        self.snapshot.write_text('{}')
        with patch.object(gate.subprocess, 'run') as run:
            with self.assertRaisesRegex(ValueError, 'input pin'):
                gate.check(self.request, 'not-read', '0' * 64, 'not-read', 'not-read')
            run.assert_not_called()

    def test_missing_source_reference_rejected_before_assembly(self):
        value = json.loads(self.snapshot.read_text())
        value['mainland_boundaries'][0]['provenance']['source_refs'].pop()
        self.snapshot.write_text(json.dumps(value))
        request = {'inputs': {'snapshot': {'path': str(self.snapshot), 'sha256': gate.digest(self.snapshot)}}}
        self.request.write_text(json.dumps(request))
        with patch.object(gate.subprocess, 'run') as run:
            with self.assertRaisesRegex(ValueError, 'source reference'):
                gate.check(self.request, 'not-read', '0' * 64, 'not-read', 'not-read')
            run.assert_not_called()

    def test_recipe_must_be_in_selected_snapshot(self):
        recipe = self.root / 'recipe.json'
        recipe.write_text('{}')
        with patch.object(gate.subprocess, 'run') as run:
            with self.assertRaisesRegex(ValueError, 'lacks pinned source assembly'):
                gate.check(self.request, recipe, gate.digest(recipe), 'not-read', 'not-read')
            run.assert_not_called()

    def test_region_hash_requires_exact_joins_and_changes_with_geometry(self):
        decision = {'segments': [{'kind': 'boundary', 'id': 'x', 'start': 0, 'end': 3, 'reverse': False},
                                 {'kind': 'route', 'id': 'r', 'start': 0, 'end': 3, 'reverse': False}]}
        records = {('boundary', 'x'): {'geometry': {'coordinates': [[0, 0], [1, 0], [1, 1]]}},
                   ('route', 'r'): {'geometry': {'coordinates': [[1, 1], [0, 1], [0, 0]]}}}
        original = gate.assembled_region_hash(decision, records)
        records[('boundary', 'x')]['geometry']['coordinates'][1] = [1.000001, 0]
        self.assertNotEqual(original, gate.assembled_region_hash(decision, records))
        records[('route', 'r')]['geometry']['coordinates'][0] = [2, 1]
        with self.assertRaisesRegex(ValueError, 'join'):
            gate.assembled_region_hash(decision, records)

    def test_worker_guard_reaches_producer_and_effective_snapshot(self):
        producer = self.root / 'seed_producer.py'
        producer.write_text("from pathlib import Path\ndef load_pinned_snapshot(path, digest, guard):\n    guard()\n    return {'original': True}\n"
                            "def run(request, work, output, guard):\n    guard()\n    value = load_pinned_snapshot('x', 'pin', guard)\n    Path(output).write_text(value['view'])\n")
        worker = self.root / 'seed_worker.py'
        worker.write_text("import sys\nimport seed_producer\n"
                          "def main():\n"
                          "    def guard():\n        with open(sys.argv[2], 'a') as f: f.write('g')\n"
                          "    seed_producer.run(sys.argv[1], sys.argv[2], sys.argv[3], guard)\n")
        report = {}
        with patch('caucasus_effective_snapshot.derive', return_value=({'view': 'effective'}, {'derived': True})):
            gate.run_guarded_worker(self.root, gate.digest(producer), gate.digest(worker),
                                    self.request, self.root / 'guards', self.root / 'out', {}, report)
        self.assertEqual((self.root / 'guards').read_text(), 'gg')
        self.assertEqual((self.root / 'out').read_text(), 'effective')
        self.assertEqual(report['effective_snapshot'], {'derived': True})
        self.assertNotIn('seed_producer', sys.modules)

    def test_worker_digest_checked_before_import(self):
        producer = self.root / 'seed_producer.py'
        producer.write_text('raise RuntimeError("must not import")\n')
        worker = self.root / 'seed_worker.py'
        worker.write_text('raise RuntimeError("must not import")\n')
        with self.assertRaisesRegex(ValueError, 'digest mismatch'):
            gate.run_guarded_worker(self.root, gate.digest(producer), '0' * 64,
                                    self.request, self.root / 'work', self.root / 'out', {}, {})

    def test_worker_guard_failure_stops_producer(self):
        producer = self.root / 'seed_producer.py'
        producer.write_text("def load_pinned_snapshot(*args): return {}\n"
                            "def run(request, work, output, guard):\n    guard()\n    open(output, 'w').close()\n")
        worker = self.root / 'seed_worker.py'
        worker.write_text("import sys\nimport seed_producer\n"
                          "def main():\n"
                          "    def guard(): raise RuntimeError('resource floor reached')\n"
                          "    seed_producer.run(sys.argv[1], sys.argv[2], sys.argv[3], guard)\n")
        with self.assertRaisesRegex(RuntimeError, 'resource floor reached'):
            gate.run_guarded_worker(self.root, gate.digest(producer), gate.digest(worker),
                                    self.request, self.root / 'work', self.root / 'out', {}, {})
        self.assertFalse((self.root / 'out').exists())
        self.assertNotIn('seed_producer', sys.modules)

    def test_direct_producer_uses_effective_view_without_worker(self):
        producer = self.root / 'seed_producer.py'
        producer.write_text("from pathlib import Path\ndef load_pinned_snapshot(path, digest, guard):\n    return {'original': True}\n"
                            "def run(request, work, output):\n    guard = lambda: None\n    value = load_pinned_snapshot('x', 'pin', guard)\n    Path(output).write_text(value['view'])\n")
        self.request.write_text(json.dumps({'schema': 'worldatlas-stage2-seed-direct-request-v2',
                                            'controls': {'strip_rows': 8}}))
        report = {}
        with patch('caucasus_effective_snapshot.derive', return_value=({'view': 'effective'}, {'derived': True})):
            gate.run_producer(self.root, gate.digest(producer), self.request,
                              self.root / 'work', self.root / 'out', {}, report)
        self.assertEqual((self.root / 'out').read_text(), 'effective')
        self.assertEqual(report['effective_snapshot'], {'derived': True})

    def test_direct_producer_rejects_legacy_or_invalid_controls(self):
        for schema, controls in [('worldatlas-stage2-seed-request-v1', {'strip_rows': 8}),
                                 ('worldatlas-stage2-seed-direct-request-v2', {'strip_rows': 0}),
                                 ('worldatlas-stage2-seed-direct-request-v2', {'strip_rows': 8, 'memory_floor_kib': 0})]:
            self.request.write_text(json.dumps({'schema': schema, 'controls': controls}))
            with self.assertRaisesRegex(ValueError, 'direct seed v2 request required'):
                gate.validate_direct_request(self.request)

    def test_direct_producer_receives_ural_request_and_original_snapshot(self):
        # The producer owns Ural input validation. The Caucasus wrapper must
        # pass its request through unchanged and derive from the original pin.
        ural = {'recipe_dir': '/recipe', 'inputs_dir': '/inputs',
                'helpers_dir': '/helpers', 'work_parent': '/work',
                'inventories': {'inputs': {'path': '/inputs', 'sha256': '1' * 64},
                                'recipe': {'path': '/recipe', 'sha256': '2' * 64},
                                'helpers': {'path': '/helpers', 'sha256': '3' * 64}},
                'python': {'path': '/python', 'sha256': '4' * 64},
                'dependency_dirs': [{'path': '/deps', 'sha256': '5' * 64}]}
        request = {'schema': 'worldatlas-stage2-seed-direct-request-v2',
                   'controls': {'strip_rows': 8}, 'ural_source': ural,
                   'inputs': {'snapshot': {'path': '/original', 'sha256': '6' * 64}}}
        self.request.write_text(json.dumps(request, sort_keys=True))
        before = self.request.read_bytes()
        producer = self.root / 'seed_producer.py'
        producer.write_text(
            'import json\nfrom pathlib import Path\n'
            'def load_pinned_snapshot(path, digest, guard):\n'
            '    assert path == "/original" and digest == "6" * 64\n'
            '    return {"original": True}\n'
            'def run(request, work, output):\n'
            '    q = json.loads(Path(request).read_bytes())\n'
            '    assert q["ural_source"] == ' + repr(ural) + '\n'
            '    pin = q["inputs"]["snapshot"]\n'
            '    value = load_pinned_snapshot(pin["path"], pin["sha256"], lambda: None)\n'
            '    Path(output).write_text(value["view"])\n')
        report = {}
        with patch('caucasus_effective_snapshot.derive', return_value=({'view': 'effective'}, {'derived': True})) as derive:
            gate.run_producer(self.root, gate.digest(producer), self.request,
                              self.root / 'work', self.root / 'out', {}, report)
        self.assertEqual(self.request.read_bytes(), before)
        self.assertEqual((self.root / 'out').read_text(), 'effective')
        self.assertEqual(derive.call_args.args[0], {'original': True})
        self.assertEqual(derive.call_args.args[3], '6' * 64)


if __name__ == '__main__':
    unittest.main()
