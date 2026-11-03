import hashlib
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.entity_registry_ui import wire_registry_ui
from scripts import build_full_v7_ui_bundle as builder

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / 'web' / 'v7'


class RecoveredV7UITest(unittest.TestCase):
    def test_historical_builder_fails_closed(self):
        with patch.dict(os.environ, {'WORLDATLAS_HISTORICAL_V7_REPLAY': ''}):
            with self.assertRaisesRegex(ValueError, 'superseded Gulf attribution'):
                builder.main()

    def test_candidate_sources_and_real_registry_wiring(self):
        # Hashes from the preserved staged-candidate runtime QA record.
        expected = {
            'app.js': 'b2d23046c4df031939fa97aac5c48b0aaa8a817988ae6ab1cb52a14c0fa0938f',
            'review-references.js': '318e2c6ad27a8e2fb40d4a3e31700687df5b0b8c1db7bf8f3cfe4a0465d03034',
            'index.html': 'e51ea6171808991da97b045db47f8c0172b19893097c2c744cd160d1b94a1c8e',
        }
        for name, digest in expected.items():
            self.assertEqual(hashlib.sha256((UI / name).read_bytes()).hexdigest(), digest)
        app, refs = wire_registry_ui((UI / 'app.js').read_text(), (UI / 'review-references.js').read_text())
        self.assertIn("from './v7-entity-adapter.js'", app)
        self.assertIn('continentOrder(meta)', refs)


if __name__ == '__main__':
    unittest.main()
