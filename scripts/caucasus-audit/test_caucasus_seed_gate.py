import hashlib
import json
import tempfile
import unittest
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


if __name__ == '__main__':
    unittest.main()
