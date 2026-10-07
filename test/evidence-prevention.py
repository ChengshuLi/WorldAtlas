"""Compact regressions for recurring audit families; no provider access/data copies."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from evidence.immutable import Baseline, NewVintage, descriptor, canonical_json
from evidence.contracts import exact_rows, join_rows, finite_metrics, require_source_text


class Prevention(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git = lambda *args: subprocess.check_output(['git', '-C', str(self.root), *args], stderr=subprocess.PIPE).decode().strip()
        self.git('init', '-q'); self.git('config', 'user.name', 'Fixture'); self.git('config', 'user.email', 'fixture@example.com')
        self.rows = [{'id': 'a', 'parent': 'province-a'}, {'id': 'b', 'parent': 'province-b'}]
        self.files = {'scope.json': canonical_json(self.rows), 'helper.py': b'def value(): return 4\n',
                      'producer.py': b'from helper import value\nresult = value()\n',
                      'data/world-index.json': canonical_json({'parts': ['geography/part-0.json', 'geography/additions.json']}),
                      'data/geography/part-0.json': canonical_json({'features': [{'id': 'a', 'properties': {}}]}),
                      'data/geography/additions.json': canonical_json({'features': [{'id': 'b', 'properties': {}}]})}
        self.pins = []
        for name, raw in self.files.items():
            target = self.root / name; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw)
            self.pins.append(descriptor(name, raw))
        self.git('add', '.'); self.git('commit', '-qm', 'Independent reference fixture')
        self.commit = self.git('rev-parse', 'HEAD')
        self.baseline = Baseline(self.root, self.commit, self.pins)
        self.owned = 'coordination/engineering/prevention-fixture/'

    def test_consumed_input_and_project_imports(self):
        (self.root / 'scope.json').write_bytes(canonical_json([{'id': 'fabricated'}]))
        with self.assertRaisesRegex(ValueError, 'materialized.*drift'):
            self.baseline.materialized_bytes('scope.json')
        self.assertEqual(json.loads(self.baseline.pinned_bytes('scope.json')), self.rows)
        (self.root / 'helper.py').write_text('def value(): return 999\n')
        modules = self.baseline.load_modules({'helper': 'helper.py', 'producer': 'producer.py'})
        self.assertEqual(modules['producer'].result, 4)  # Actual imported code comes from captured pinned bytes.
        with self.assertRaises(ValueError): self.baseline.pinned_bytes('undeclared.py')
        sys.path.insert(0, str(self.root))
        try:
            with self.assertRaisesRegex(ValueError, 'Undeclared executed project code'):
                self.baseline.load_modules({'producer': 'producer.py'})
        finally:
            sys.path.remove(str(self.root))

    def test_real_records_not_summary_counts_or_candidate_hashes(self):
        self.assertEqual(len(join_rows(self.rows, self.rows, {'parent': 'parent'})), 2)
        for rows in [self.rows[:1], self.rows + [self.rows[0]], [{'id': 'a', 'parent': 'wrong'}, self.rows[1]],
                     [self.rows[0], {'id': 'fabricated', 'parent': 'province-b'}]]:
            # A self-consistent hash/count does not rescue a wrong reference join.
            descriptor('candidate.json', canonical_json({'rows': rows, 'count': 2}))
            with self.assertRaises(ValueError): join_rows(rows, self.rows, {'parent': 'parent'})
        with self.assertRaises(ValueError): exact_rows([], [])
        with self.assertRaises(ValueError): exact_rows(self.rows, ['a', 'b', 'a'])
        self.assertEqual(exact_rows([], [], allow_empty=True), {})

    def test_complete_index_and_actual_phase_accounting(self):
        subjects, paths = self.baseline.subjects(['b'])
        self.assertEqual(set(subjects), {'b'})
        self.assertEqual(paths['b']['path'], 'data/geography/additions.json')
        (self.root / 'data/geography/additions.json').write_text('mutable garbage')
        self.assertEqual(set(self.baseline.subjects(['b'])[0]), {'b'})
        pin = next(pin for pin in self.pins if pin['path'] == 'data/world-index.json')
        tight = Baseline(self.root, self.commit, [pin], max_phase_bytes=pin['bytes'] + 1)
        with self.assertRaisesRegex(ValueError, 'execution phase'):
            tight.subjects(['b'])
        # Duplicate outside the requested scope must not disappear in a dict.
        (self.root / 'data/geography/additions.json').write_bytes(canonical_json({'features': [{'id': 'a', 'properties': {}}]}))
        self.git('add', '.'); self.git('commit', '-qm', 'Duplicate indexed fixture')
        current = self.git('rev-parse', 'HEAD')
        complete = Baseline(self.root, current, [pin])
        with self.assertRaisesRegex(ValueError, 'duplicate indexed'):
            complete.subjects(['a'])

    def test_destination_admission_and_complete_output_budget(self):
        for owned, run in [(self.owned, '../../../escape'), (self.owned, '/absolute'), ('data/other/', 'fresh')]:
            with self.assertRaises(ValueError): NewVintage(self.baseline, owned, run, ['one.json'])
        self.assertFalse((self.root / 'coordination').exists())
        vintage = NewVintage(self.baseline, self.owned, 'fresh', ['one.json', 'two.json'])
        with self.assertRaises(ValueError): vintage.publish({'one.json': {}})
        self.assertFalse(vintage.root.exists())
        pin = self.pins[0]
        tight = Baseline(self.root, self.commit, [pin], max_phase_bytes=4096 + pin['bytes'])
        with self.assertRaisesRegex(ValueError, 'including output'):
            NewVintage(tight, self.owned, 'oversize', ['one.json']).publish({'one.json': {'value': 'x' * 100}})
        self.assertFalse((self.root / 'coordination').exists())

    def test_fresh_runs_preserve_sentinels_and_reject_symlinks(self):
        outputs = {'one.json': self.rows, 'two.json': {'count': 2}}
        first = NewVintage(self.baseline, self.owned, 'one', list(outputs))
        first.publish(outputs)
        original = {p.name: p.read_bytes() for p in first.root.iterdir()}
        second = NewVintage(self.baseline, self.owned, 'two', list(outputs))
        second.publish(outputs)
        for name in outputs: self.assertEqual((first.root / name).read_bytes(), (second.root / name).read_bytes())
        with self.assertRaises(FileExistsError): NewVintage(self.baseline, self.owned, 'one', list(outputs))
        self.assertEqual(original, {p.name: p.read_bytes() for p in first.root.iterdir()})
        link = first.root.parent / 'broken'; link.symlink_to(self.root / 'absent')
        with self.assertRaisesRegex(ValueError, 'Symlink'): NewVintage(self.baseline, self.owned, 'broken', list(outputs))
        self.assertFalse((self.root / 'absent').exists())

    def test_partial_failure_cannot_claim_complete(self):
        run = NewVintage(self.baseline, self.owned, 'partial', ['one.json', 'two.json'])
        original_open = Path.open
        def fail_second(path, *args, **kwargs):
            if path == run.root / 'two.json': raise OSError('Simulated second-product failure')
            return original_open(path, *args, **kwargs)
        with patch.object(Path, 'open', fail_second):
            with self.assertRaises(OSError): run.publish({'one.json': {}, 'two.json': {}})
        self.assertTrue((run.root / 'one.json').exists())
        self.assertFalse((run.root / 'publication.json').exists())

    def test_no_vacuous_measurement_or_source_success(self):
        for value in [{}, {'iou': None}, {'iou': float('nan')}, {'iou': True}]:
            with self.assertRaises(ValueError): finite_metrics(value, ['iou'])
        self.assertEqual(finite_metrics({'iou': 0}, ['iou']), {'iou': 0})
        with self.assertRaises(ValueError): require_source_text('HTTP 200 navigation', ['Article V section 18'])
        self.assertEqual(require_source_text('Article V section 18 body', ['Article V section 18']), 'Article V section 18 body')


if __name__ == '__main__': unittest.main()
