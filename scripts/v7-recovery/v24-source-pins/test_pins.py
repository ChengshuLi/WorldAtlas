import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent


class PreservedSourceTests(unittest.TestCase):
    def test_preserved_code_matches_recorded_digests(self):
        manifest = json.loads((ROOT / 'pins.json').read_text())
        self.assertEqual(len(manifest['files']), 9)
        for entry in manifest['files']:
            with self.subTest(role=entry['report_role']):
                self.assertEqual(hashlib.sha256((ROOT / entry['path']).read_bytes()).hexdigest(),
                                 entry['sha256'])


if __name__ == '__main__': unittest.main()
