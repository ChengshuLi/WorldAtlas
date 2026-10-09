"""Whole-file custody controls, including rehashed omission and redirection."""
import copy
import json
import pathlib
import sys
import tempfile
import unittest
import subprocess
from unittest import mock
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'scripts'))
from evidence.immutable import canonical_json, descriptor, deterministic_gzip, sha256
from physical_component_custody import VERSION, OWNED, EXECUTED_PATHS, ROOT, describe, validate


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
            commit = '6ed6406f9fad4c7c468b06a376346b216cb50db7' if complete else '8f6dc184d1a41b634cec4759bb57b3cc04dd980a'
            body = {'status': 'complete' if complete else 'incomplete-export-failed',
                    'input_commit': 'c603befd3aaf4da90d59b12378e1e0739331efba', 'executed_code_commit': commit}
            code, code_inputs = [], []
            for source_path in EXECUTED_PATHS:
                source = subprocess.check_output(['git', 'show', commit + ':' + source_path], cwd=ROOT)
                code_path = OWNED + 'executed-code/' + commit + '/' + source_path
                if not any(a['original']['path'] == code_path for a in self.index['aliases']):
                    self.retain(code_path, source)
                code.append(descriptor(code_path, source))
                code_inputs.append(descriptor(source_path, source))
            if complete:
                body['code_inputs'] = code_inputs
            body['outputs' if complete else 'outputs_preserved'] = {'ledger': [row]} if complete else [row]
            entry = prefix + ('/report.json' if complete else '/incomplete-export-receipt.json')
            self.retain(entry, canonical_json(body))
            self.index['generations'].append({'prefix': prefix, 'status': 'complete' if complete else 'incomplete',
                                            'inventory': [path, entry], 'code': code,
                                            'input_commit': body['input_commit'], 'executed_code_commit': commit})

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
        self.assertEqual(result['logical_files'], 16)

    def test_descriptors_reuse_only_captured_payload_and_decoding_mode(self):
        expected = {(a['payload'], a['original']['path'].endswith(('.json.gz', '.geojson.gz')))
                    for a in self.index['aliases']}
        with mock.patch('physical_component_custody.describe', wraps=describe) as observed:
            validate(self.root, self.index)
        self.assertEqual(observed.call_count, len(expected))

    def test_reused_descriptor_still_checks_every_logical_alias(self):
        shared = self.index['aliases'][0]['payload']
        aliases = [a for a in self.index['aliases'] if a['payload'] == shared]
        self.assertGreater(len(aliases), 1)
        aliases[-1]['original']['uncompressed_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'Redirected or changed'):
            validate(self.root, self.index)

    def test_new_validation_recaptures_changed_actual_payload(self):
        validate(self.root, self.index)
        target = self.root / self.index['aliases'][0]['payload']
        target.write_bytes(target.read_bytes() + b'changed-after-success')
        with self.assertRaisesRegex(ValueError, 'Redirected or changed'):
            validate(self.root, self.index)

    def test_plain_alias_cannot_supply_compressed_descriptor(self):
        alias = self.index['aliases'][0]
        raw = (self.root / alias['payload']).read_bytes()
        plain = 'run-0/data.bin'
        alias['original'] = descriptor(plain, raw)
        generation = self.index['generations'][0]
        generation['inventory'][0] = plain
        receipt_alias = next(a for a in self.index['aliases']
                             if a['original']['path'] == generation['inventory'][1])
        receipt_target = self.root / receipt_alias['payload']
        receipt = json.loads(receipt_target.read_bytes())
        receipt['outputs_preserved'][0]['path'] = plain
        receipt_raw = canonical_json(receipt)
        receipt_target.write_bytes(receipt_raw)
        receipt_alias['original'] = describe(receipt_alias['original']['path'], receipt_raw)
        payload = next(p for p in self.index['payloads'] if p['path'] == receipt_alias['payload'])
        payload.update(descriptor(payload['path'], receipt_raw))
        with mock.patch('physical_component_custody.describe', wraps=describe) as observed:
            validate(self.root, self.index)
        decoded_modes = [call.args[0].endswith(('.json.gz', '.geojson.gz'))
                         for call in observed.call_args_list if call.args[1] == raw]
        self.assertEqual(decoded_modes, [False, True])

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
        with self.assertRaisesRegex(ValueError, 'distinct complete'):
            validate(self.root, self.index)

    def test_whole_failed_generation_cannot_be_omitted(self):
        self.index['generations'].pop(0)
        with self.assertRaisesRegex(ValueError, 'distinct complete'):
            validate(self.root, self.index)

    def test_duplicate_complete_vintage_cannot_fake_reproducibility(self):
        self.index['generations'][2] = copy.deepcopy(self.index['generations'][1])
        with self.assertRaisesRegex(ValueError, 'distinct complete'):
            validate(self.root, self.index)

    def test_execution_commit_metadata_cannot_change(self):
        self.index['generations'][0]['executed_code_commit'] = '0' * 40
        with self.assertRaisesRegex(ValueError, 'commit binding'):
            validate(self.root, self.index)

    def test_original_code_cannot_be_omitted(self):
        self.index['generations'][0]['code'] = []
        with self.assertRaisesRegex(ValueError, 'Missing original executed'):
            validate(self.root, self.index)

    def test_original_code_roster_cannot_be_reduced(self):
        self.index['generations'][0]['code'].pop()
        with self.assertRaisesRegex(ValueError, 'Incomplete original executed'):
            validate(self.root, self.index)


if __name__ == '__main__':
    unittest.main()
