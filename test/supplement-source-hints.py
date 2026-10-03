import copy
import gzip
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('repair_hints', ROOT / 'scripts/repair-supplement-source-hints.py')
repair = importlib.util.module_from_spec(spec)
spec.loader.exec_module(repair)


class SourceHintControls(unittest.TestCase):
    def setUp(self):
        self.record = {'location_id': 'synthetic:one', 'name': 'Île synthetic', 'metadata': {'source': 'fixture'}}
        self.profiles = repair.profile_index([self.record])
        self.scope = {'member_location_ids': ['synthetic:one'], 'release': {'id': 'synthetic-release'},
                      'owned_evidence_path': 'data/regional-review/synthetic/',
                      'source_profile_hints': [{'location_id': 'synthetic:one',
                                               'durable_full_source_profile_path': repair.OLD_PATH,
                                               'full_source_profile_canonical_sha256': repair.entry_hash(self.record),
                                               'metadata': {'retained': 'exact fixture context'}}]}
        self.issue_metadata = {'number': 520, 'state': 'closed', 'updated_at': '2026-10-03T00:00:00Z'}
        self.artifact = {'path': repair.PROFILE_PATH, 'compressed_file': {'sha256': 'synthetic'},
                         'entry_hash': {'scope': repair.HASH_SCOPE}}

    def issue(self):
        return {**self.issue_metadata, 'body': 'Original recorded date and completed work\n```json\n' +
                json.dumps(self.scope, sort_keys=True, ensure_ascii=False, separators=(',', ':')) +
                '\n```\n<!-- worldatlas-work:v1\n{"max_prs":2,"mode":"geography"}\n-->'}

    def test_unicode_entry_contract_has_no_newline_and_is_not_file_hash(self):
        raw = json.dumps(self.record, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()
        self.assertEqual(repair.entry_hash(self.record), repair.sha256(raw))
        self.assertNotEqual(repair.entry_hash(self.record), repair.sha256(raw + b'\n'))
        self.assertNotEqual(repair.entry_hash(self.record), repair.sha256(gzip.compress(raw)))

    def test_repair_preserves_dates_scope_hashes_and_is_idempotent(self):
        original = self.issue()
        row = repair.repair_issue(original, self.profiles, self.artifact)
        self.assertTrue(row['changed'])
        self.assertIn('Original recorded date and completed work', row['body'])
        self.assertIn('"id":"synthetic-release"', row['body'])
        self.assertIn('data/regional-review/synthetic/', row['body'])
        self.assertIn(repair.entry_hash(self.record), row['body'])
        self.assertNotIn(repair.OLD_PATH, row['body'])
        again = repair.repair_issue({**original, 'body': row['body']}, self.profiles, self.artifact)
        self.assertFalse(again['changed'])
        self.assertEqual(row['body'], again['body'])

    def test_two_runs_produce_identical_plan_rows(self):
        self.assertEqual(repair.canonical_json(repair.repair_issue(self.issue(), self.profiles, self.artifact)),
                         repair.canonical_json(repair.repair_issue(self.issue(), self.profiles, self.artifact)))

    def test_wrong_entry_hash_rejects_without_rewriting(self):
        self.scope['source_profile_hints'][0]['full_source_profile_canonical_sha256'] = '0' * 64
        original = self.issue()
        with self.assertRaisesRegex(ValueError, 'entry hash mismatch'):
            repair.repair_issue(original, self.profiles, self.artifact)
        self.assertEqual(original, self.issue())

    def test_missing_profile_and_duplicate_identity_reject(self):
        with self.assertRaisesRegex(ValueError, 'no retained profile'):
            repair.repair_issue(self.issue(), {}, self.artifact)
        with self.assertRaisesRegex(ValueError, 'duplicate retained profile'):
            repair.profile_index([self.record, copy.deepcopy(self.record)])

    def test_incomplete_or_duplicate_owned_subject_hints_reject(self):
        self.scope['member_location_ids'].append('synthetic:missing')
        with self.assertRaisesRegex(ValueError, 'exact disjoint owned subjects'):
            repair.repair_issue(self.issue(), self.profiles, self.artifact)
        self.scope['member_location_ids'] = ['synthetic:one']
        self.scope['source_profile_hints'].append(copy.deepcopy(self.scope['source_profile_hints'][0]))
        with self.assertRaisesRegex(ValueError, 'exact disjoint owned subjects'):
            repair.repair_issue(self.issue(), self.profiles, self.artifact)

    def test_unexpected_pointer_or_conflicting_artifact_reject(self):
        self.scope['source_profile_hints'][0]['durable_full_source_profile_path'] = 'unrelated/path.gz'
        with self.assertRaisesRegex(ValueError, 'Unexpected advertised profile path'):
            repair.repair_issue(self.issue(), self.profiles, self.artifact)
        self.scope['source_profile_hints'][0]['durable_full_source_profile_path'] = repair.OLD_PATH
        self.scope['source_profile_artifact'] = {'path': 'other'}
        with self.assertRaisesRegex(ValueError, 'existing source artifact declaration disagrees'):
            repair.repair_issue(self.issue(), self.profiles, self.artifact)

    def test_compressed_and_uncompressed_file_pins_are_separate(self):
        raw = b'[{"synthetic":true}]\n'
        compressed = gzip.compress(raw, mtime=0)
        with patch.multiple(repair, COMPRESSED_SHA256=repair.sha256(compressed), UNCOMPRESSED_SHA256=repair.sha256(raw)):
            artifact = repair.source_artifact(compressed, raw)
            self.assertNotEqual(artifact['compressed_file']['sha256'], artifact['uncompressed_file']['sha256'])
            with self.assertRaisesRegex(ValueError, 'Compressed source file pin changed'):
                repair.source_artifact(compressed + b'changed', raw)
            with self.assertRaisesRegex(ValueError, 'Uncompressed source file pin changed'):
                repair.source_artifact(compressed, raw + b'changed')


if __name__ == '__main__':
    unittest.main()
