"""Restored map inputs are independent of an earlier machine's comparison files."""

import json
from pathlib import Path
import tempfile
import unittest

from worldatlas.map_releases.inputs import restore_inputs


class ReplayConfiguration(unittest.TestCase):
    def test_comparison_paths_are_omitted_without_changing_captured_values(self):
        configuration = dict(
            sources=dict(
                land_config={"json": {"source": "coast"}},
                reference_rows={"path": "/old-machine/rows.u32le"},
                reference_runs={"path": "/old-machine/runs.u32le"},
            )
        )
        captured = dict(
            configuration=configuration, selection={"coordinates": [1.5, 2.5]}
        )
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "restored"
            restore_inputs(captured, output)
            restored = json.loads((output / "configuration.json").read_text())
            self.assertEqual(
                restored["sources"],
                {"land_config": configuration["sources"]["land_config"]},
            )
            self.assertEqual(
                json.loads((output / "selection.json").read_text()),
                captured["selection"],
            )
        self.assertIn("reference_rows", configuration["sources"])
        self.assertIn("reference_runs", configuration["sources"])
