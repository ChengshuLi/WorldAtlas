"""Whole-file custody controls, including rehashed omission and redirection."""
import copy
import json
import pathlib
import sys
import tempfile
import unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'scripts'))
from evidence.immutable import canonical_json, descriptor, deterministic_gzip, sha256
from physical_component_custody import VERSION, describe, validate


class CustodyControls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        self.index = {'version': VERSION, 'payloads': [], 'aliases': [], 'generations': []}
        self.payloads = set()
        data = deterministic_gzip(canonical_json([{'original': 'unchanged'}]))
        for number in range(3):
            prefix = f'run-{number}'
            path = prefix + '/data.json.gz'
            self.retain(path, data)
            complete = number != 0
            row = describe(path, data) if complete else descriptor(path, data)
            body = {'status': 'complete' if complete else 'incomplete-export-failed'}
            body['outputs' if complete else 'outputs_preserved'] = {'ledger': [row]} if complete else [row]
            entry = prefix + ('/report.json' if complete else '/incomplete-export-receipt.json')
            self.retain(entry, canonical_json(body))
            self.index['generations'].append({'prefix': prefix, 'status': 'complete' if complete else 'incomplete',
                                            'inventory': [path, entry], 'code': []})

    def retain(self, path, raw):
        target = 'payloads/' + sha256(raw) + '.bin'
        if target not in self.payloads:
            p = self.root / target
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(raw)
            self.index['payloads'].append(descriptor(target, raw))
            self.payloads.add(target)
        self.index['aliases'].append({'original': describe(path, raw), 'payload': target})

    def test_real_whole_bytes_deduplicate_without_erasing_failed_trial(self):
        result = validate(self.root, self.index)
        self.assertLess(result['unique_bytes'], result['logical_bytes'])
        self.assertEqual(result['logical_files'], 6)

    def test_omitted_alias_fails_even_with_consistent_index_hash(self):
        self.index['aliases'].pop(0)
        with self.assertRaisesRegex(ValueError, 'Missing or changed'):
            validate(self.root, self.index)

    def test_duplicate_alias_fails(self):
        self.index['aliases'].append(copy.deepcopy(self.index['aliases'][0]))
        with self.assertRaisesRegex(ValueError, 'Duplicate alias'):
            validate(self.root, self.index)

    def test_redirected_alias_to_other_valid_payload_fails(self):
        self.index['aliases'][0]['payload'] = self.index['aliases'][1]['payload']
        with self.assertRaisesRegex(ValueError, 'Redirected'):
            validate(self.root, self.index)

    def test_rehashed_partial_inventory_fails(self):
        self.index['generations'][0]['inventory'].pop(0)
        with self.assertRaisesRegex(ValueError, 'Partial'):
            validate(self.root, self.index)

    def test_failed_trial_cannot_be_reclassified_complete(self):
        self.index['generations'][0]['status'] = 'complete'
        with self.assertRaisesRegex(ValueError, 'Missing original'):
            validate(self.root, self.index)


if __name__ == '__main__':
    unittest.main()
