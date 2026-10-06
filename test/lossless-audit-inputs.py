import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'scripts'))
from evidence.immutable import deterministic_gzip, descriptor
from lossless_audit_inputs import (LAND_ROOT, blob_id, report_roster,
                                   require_complete_roster, restore_payload)


def row_for(raw):
    encoded = deterministic_gzip(raw)
    return encoded, {'encoded': descriptor('encoded.bytes.gz', encoded),
                     'original': descriptor('original.json', raw), 'original_git_blob': blob_id(raw)}


class LosslessInputControls(unittest.TestCase):
    def test_exact_whitespace_attributes_and_nested_original_gzip(self):
        raw = b'{ "original_attributes": [null, true, "name"], "coordinates": [1.000000,2] }\n'
        for original in [raw, deterministic_gzip(raw)]:
            encoded, row = row_for(original)
            self.assertEqual(restore_payload(encoded, row), original)

    def test_tampered_envelope_is_rejected(self):
        encoded, row = row_for(b'original')
        with self.assertRaisesRegex(ValueError, 'encoded bytes changed'):
            restore_payload(encoded[:-1] + bytes([encoded[-1] ^ 1]), row)

    def test_reencoded_extract_cannot_replace_original(self):
        _, row = row_for(b'original with all fields')
        extract = deterministic_gzip(b'original')
        row['encoded'] = descriptor('encoded.bytes.gz', extract)
        with self.assertRaisesRegex(ValueError, 'complete original bytes'):
            restore_payload(extract, row)

    def test_wrong_original_git_identity_is_rejected(self):
        encoded, row = row_for(b'original')
        row['original_git_blob'] = '0' * 40
        with self.assertRaisesRegex(ValueError, 'complete original bytes'):
            restore_payload(encoded, row)

    def test_omitted_and_extra_world_sources_are_rejected(self):
        baseline, water = '1' * 40, '2' * 40
        water_root = 'coordination/engineering/example/sources'
        paths = ['data/world-index.json', 'data/hierarchy.json', 'data/canonical-grid/manifest.json',
                 'data/geographic-releases/current-manifest.json', 'data/geographic-releases/releases.json.gz',
                 LAND_ROOT + 'manifest.json.gz', LAND_ROOT + 'natural-earth-land.geojson.gz.gz',
                 'data/geography/part-0.json']
        restored = {(baseline, path): None for path in paths}
        restored[(baseline, 'data/world-index.json')] = json.dumps({'parts': ['geography/part-0.json']}).encode()
        restored[(baseline, 'data/geographic-releases/current-manifest.json')] = json.dumps({'path': 'releases.json.gz'}).encode()
        restored.update({(water, water_root + '/' + name): None
                         for name in ['receipt.json', 'natural-earth-lakes.geojson.gz']})
        require_complete_roster(restored, baseline, water, water_root)
        changed = dict(restored)
        changed.pop((baseline, 'data/geography/part-0.json'))
        with self.assertRaisesRegex(ValueError, 'source roster'):
            require_complete_roster(changed, baseline, water, water_root)
        extra = dict(restored)
        extra[(baseline, 'data/geography/invented.json')] = None
        with self.assertRaisesRegex(ValueError, 'source roster'):
            require_complete_roster(extra, baseline, water, water_root)

    def test_duplicate_original_source_is_rejected(self):
        entry = descriptor('data/world-index.json', b'original')
        report = {'baseline_commit': '1' * 40, 'water_commit': '2' * 40,
                  'inputs': [entry, entry], 'water_inputs': []}
        with self.assertRaisesRegex(ValueError, 'Duplicate original source'):
            report_roster(report)


if __name__ == '__main__':
    unittest.main()
