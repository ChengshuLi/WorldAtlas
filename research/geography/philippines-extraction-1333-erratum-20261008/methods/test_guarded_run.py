#!/usr/bin/env python3
"""Adverse bounded tests for the guarded producer and acceptance boundary."""
import gzip
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import guarded_run
import verify_bounded_run


class GuardedRunTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo = guarded_run.REPO
        cls.baseline = guarded_run.baseline_for(cls.repo)
        cls.owned = cls.repo / guarded_run.OWNED

    def test_original_refused_before_decoding_products(self):
        before = set(self.owned.rglob('*')) if self.owned.exists() else set()
        with self.assertRaisesRegex(ValueError, 'per-file limit|phase budget'):
            guarded_run.refuse_original(self.repo, self.baseline)
        after = set(self.owned.rglob('*')) if self.owned.exists() else set()
        self.assertEqual(before, after)

    def test_two_independent_fresh_complete_runs(self):
        names = ['repro-one-test', 'repro-two-test']
        try:
            first = guarded_run.run_synthetic(self.repo, names[0], self.baseline)
            second = guarded_run.run_synthetic(self.repo, names[1], self.baseline)
            self.assertEqual([(x['bytes'], x['sha256']) for x in first],
                             [(x['bytes'], x['sha256']) for x in second])
            for name in names:
                root = self.owned / 'vintages' / name
                receipt = json.loads((root / 'publication.json').read_bytes())
                self.assertEqual(receipt['status'], 'complete')
                self.assertEqual(len(receipt['outputs']), 2)
                self.assertEqual(verify_bounded_run.verify_run(root)['outputs'], 2)
                self.assertTrue(all(json.loads((root / row['path'].split('/')[-1]).read_bytes())['geographic_claim'] is False
                                    for row in receipt['outputs']))
        finally:
            for name in names:
                shutil.rmtree(self.owned / 'vintages' / name, ignore_errors=True)

    def test_existing_sentinel_and_rerun_preserved(self):
        name = 'sentinel-test'
        root = self.owned / 'vintages' / name
        root.mkdir(parents=True)
        sentinel = root / 'control.json'
        sentinel.write_bytes(b'ORIGINAL-VINTAGE\n')
        before = sentinel.read_bytes()
        try:
            with self.assertRaises((FileExistsError, ValueError)):
                guarded_run.run_synthetic(self.repo, name, self.baseline)
            self.assertEqual(sentinel.read_bytes(), before)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_dangling_leaf_and_symlink_parent_rejected_without_escape(self):
        parent = self.owned / 'vintages'
        parent.mkdir(parents=True, exist_ok=True)
        shutil.rmtree(parent / 'dangling-test', ignore_errors=True)
        if (parent / 'parent-link-test').is_symlink():
            (parent / 'parent-link-test').unlink()
        outside = self.owned / 'private-sentinel'
        outside.write_bytes(b'UNCHANGED\n')
        broken_run = parent / 'dangling-test'
        broken_run.mkdir()
        symlink_run = parent / 'parent-link-test'
        before = outside.read_bytes()
        with tempfile.TemporaryDirectory(prefix='phl-owned-path-control-') as scratch:
            target_dir = Path(scratch)
            escaped_output = target_dir / 'control.json'
            (broken_run / 'control.json').symlink_to(escaped_output)
            symlink_run.symlink_to(target_dir, target_is_directory=True)
            try:
                for name in ('dangling-test', 'parent-link-test'):
                    with self.assertRaises((FileExistsError, ValueError)):
                        guarded_run.run_synthetic(self.repo, name, self.baseline)
                self.assertEqual(outside.read_bytes(), before)
                self.assertFalse(escaped_output.exists())
                self.assertEqual(list(target_dir.iterdir()), [])
            finally:
                shutil.rmtree(broken_run, ignore_errors=True)
                symlink_run.unlink(missing_ok=True)
                outside.unlink(missing_ok=True)

    def test_later_output_collision_and_partial_failure_preserve_original(self):
        name = 'later-collision-test'
        root = self.owned / 'vintages' / name
        root.mkdir(parents=True)
        collision = root / 'control-summary.json'
        collision.write_bytes(b'ORIGINAL-LATER-OUTPUT\n')
        before = collision.read_bytes()
        try:
            with self.assertRaises((FileExistsError, ValueError)):
                guarded_run.run_synthetic(self.repo, name, self.baseline)
            self.assertEqual(collision.read_bytes(), before)
            self.assertFalse((root / 'publication.json').exists())
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_complete_budget_and_decoded_size_guards(self):
        from evidence.immutable import MAX_FILE_BYTES
        before = dict(self.baseline.consumed)
        with self.assertRaisesRegex(ValueError, 'Input exceeds file byte budget'):
            self.baseline.admit('oversized-decoded-fixture', MAX_FILE_BYTES + 1)
        self.assertEqual(self.baseline.consumed, before)
        self.assertGreater(MAX_FILE_BYTES, 0)
        # The pinned original descriptor inventory proves the 32 MiB logical
        # body overflow without constructing or decoding a giant gzip member.
        closure = json.loads(guarded_run.MANIFEST.read_bytes())['original_operation']['input_closure']
        self.assertTrue(all(row.get('uncompressed_bytes', 0) <= MAX_FILE_BYTES for row in closure))

    def test_combined_raw_decoded_and_output_inclusive_overflow(self):
        from evidence.immutable import NewVintage
        original_consumed = dict(self.baseline.consumed)
        original_budget = self.baseline.max_phase_bytes
        try:
            self.baseline.max_phase_bytes = sum(original_consumed.values()) + 1024
            self.baseline.admit('synthetic-raw-input', 600)
            with self.assertRaisesRegex(ValueError, 'phase exceeds byte budget'):
                self.baseline.admit('synthetic-decoded-input', 500)
            self.baseline.consumed = dict(original_consumed)
            self.baseline.max_phase_bytes = sum(original_consumed.values()) + 4096
            run = NewVintage(self.baseline, guarded_run.OWNED, 'output-budget-test', ['bounded.json'])
            with self.assertRaisesRegex(ValueError, 'phase including output exceeds byte budget'):
                run.publish({'bounded.json': {'value': 'bounded'}})
        finally:
            self.baseline.consumed = original_consumed
            self.baseline.max_phase_bytes = original_budget

    def test_compressed_small_decoded_large_rejected_before_write(self):
        from evidence.immutable import MAX_FILE_BYTES, NewVintage
        decoded = b'x' * (MAX_FILE_BYTES + 1)
        compressed = gzip.compress(decoded, compresslevel=9, mtime=0)
        self.assertLess(len(compressed), MAX_FILE_BYTES)
        run = NewVintage(self.baseline, guarded_run.OWNED, 'decoded-member-overflow-test',
                         ['large-member.json.gz'])
        with self.assertRaisesRegex(ValueError, 'Decoded output exceeds'):
            run.publish_bytes({'large-member.json.gz': compressed})
        self.assertFalse(run.root.exists())

    def test_logical_concatenation_overflow_and_missing_descriptor(self):
        manifest = json.loads(guarded_run.MANIFEST.read_bytes())
        operation = manifest['original_operation']
        with self.assertRaisesRegex(ValueError, 'logical stream'):
            guarded_run.validate_logical_streams(operation['logical_streams'])
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            guarded_run.validate_inventory(operation['input_closure'][1:], operation['input_closure'])

    def test_acceptance_reader_rejects_missing_or_mutated_output(self):
        name = 'harness-test'
        try:
            guarded_run.run_synthetic(self.repo, name, self.baseline)
            root = self.owned / 'vintages' / name
            missing = root / 'control-summary.json'
            preserved = missing.read_bytes()
            missing.unlink()
            with self.assertRaisesRegex(ValueError, 'inventory'):
                verify_bounded_run.verify_run(root)
            missing.write_bytes(preserved)
            (root / 'control.json').write_bytes(b'{"changed":true}\n')
            with self.assertRaisesRegex(ValueError, 'byte identity'):
                verify_bounded_run.verify_run(root)
        finally:
            shutil.rmtree(self.owned / 'vintages' / name, ignore_errors=True)

    def test_partial_failure_has_no_completion_receipt_and_preserves_attempt(self):
        from evidence.immutable import NewVintage
        name = 'partial-failure-test'
        root = self.owned / 'vintages' / name
        original_open = Path.open

        def fail_second(path, *args, **kwargs):
            if path == root / 'control-summary.json' and args and args[0] == 'xb':
                raise OSError('injected second-output failure')
            return original_open(path, *args, **kwargs)

        try:
            with mock.patch.object(Path, 'open', fail_second):
                with self.assertRaisesRegex(OSError, 'injected'):
                    NewVintage(self.baseline, guarded_run.OWNED, name,
                               ['control.json', 'control-summary.json']).publish({
                        'control.json': {'status': 'partial fixture'},
                        'control-summary.json': {'status': 'partial fixture'},
                    })
            self.assertTrue((root / 'control.json').is_file())
            self.assertFalse((root / 'publication.json').exists())
            with self.assertRaisesRegex(ValueError, 'Missing ordinary completion'):
                verify_bounded_run.verify_run(root)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_missing_descriptor_rejected_before_output(self):
        manifest = json.loads(guarded_run.MANIFEST.read_bytes())
        closure = manifest['original_operation']['input_closure']
        self.assertTrue(closure)
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            guarded_run.validate_inventory(closure[1:], closure)


if __name__ == '__main__':
    unittest.main(verbosity=2)
