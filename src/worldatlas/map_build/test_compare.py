"""Exercise standalone comparison using a completed build and an R2 fixture."""

import gzip
import hashlib
import io
import json
import runpy
import struct
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

from worldatlas.map_build import compare as command
from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.core.layers import write_layer
from worldatlas.map_build.inputs import releases
from worldatlas.map_build.inputs.selection import canonical_bytes
from worldatlas.shared import r2
from worldatlas.shared.files import pin_file, read_json, sha256_file, write_json


class CompareCommandTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.run = self.root / "run"
        self.run.mkdir()
        self.grid = Grid(4, 1, 90)
        final = self.run / "final"
        write_layer(final, self.grid, [(0, [(0, 3, 1), (3, 4, 2)])])
        self.selection = {
            "geography": {
                "category_bindings": [
                    {"code": code, "entity_id": code, "physical_class": "land"}
                    for code in (1, 2)
                ]
            }
        }
        write_json(self.run / "input-selection.json", self.selection)
        identity = write_json(
            self.run / "run-identity.json",
            {
                "input_selection_sha256": hashlib.sha256(
                    canonical_bytes(self.selection)
                ).hexdigest(),
            },
        )
        self.build_report = self.run / "report.json"
        write_json(
            self.build_report,
            {
                "status": "complete",
                "original_run_identity": pin_file(identity),
                "final": {
                    name: pin_file(final / filename)
                    for name, filename in (
                        ("rows", "rows.u32le"),
                        ("runs", "runs.u32le"),
                        ("report", "report.json"),
                    )
                },
            },
        )

        self.output = self.root / "diff"
        self.remote = {}
        baseline = self.root / "baseline"
        write_layer(baseline, self.grid, [(0, [(0, 4, 10)])])
        self.streams = []
        for name in ("rows", "runs"):
            path = baseline / f"{name}.u32le"
            pin = self.store(
                f"release/{path.name}.gz", gzip.compress(path.read_bytes())
            )
            self.streams.append((name, pin, sha256_file(path)))
        self.config = {
            **vars(self.grid),
            "categories": [{"id": 10, "entity_id": 1, "physical_class": "land"}],
        }
        self.config_pin = self.store(
            "release/config.json", json.dumps(self.config).encode()
        )
        self.release_assets = self.enterContext(
            patch.object(
                releases,
                "read_release_assets",
                return_value=(self.streams, self.config_pin),
            )
        )
        self.storage = Mock()
        self.storage.get_object.side_effect = lambda *, Bucket, Key: {
            "Body": io.BytesIO(self.remote[Key])
        }
        self.enterContext(
            patch.object(
                r2, "make_r2_client", side_effect=lambda: r2.R2Client(self.storage)
            )
        )

    def store(self, key, payload):
        self.remote[key] = payload
        return {
            "r2_bucket": "test",
            "r2_key": key,
            "size_bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }

    def compare(self):
        return command.compare_release(
            self.run, "v8.3", self.output, work_dir=self.root
        )

    def test_command_compares_assignments_and_reuses_files_for_another_release(self):
        saved = pin_file(self.build_report)
        with (
            patch(
                "sys.argv",
                [
                    "worldatlas-compare",
                    str(self.run),
                    "v8.3",
                    str(self.output),
                    "--work-dir",
                    str(self.root),
                ],
            ),
            redirect_stdout(io.StringIO()) as stdout,
        ):
            runpy.run_path(command.__file__, run_name="__main__")
        report = read_json(self.output / "report.json")
        self.assertEqual(json.loads(stdout.getvalue()), report)
        self.assertEqual(report["pair_counts"], {"10->2": 1})
        self.assertEqual(report["changed_cells"], 1)
        self.assertEqual(
            (self.output / "changes.u32le").read_bytes(),
            struct.pack("<5I", 0, 3, 4, 10, 2),
        )
        self.assertEqual(
            (self.output / "change-rows.u64le").read_bytes(), struct.pack("<2Q", 0, 1)
        )
        self.assertEqual(pin_file(self.build_report), saved)
        self.assertFalse((self.run / "comparison").exists())

        reissued = []
        for name, pin, decoded_hash in self.streams:
            (self.root / "inputs" / pin["sha256"] / Path(pin["r2_key"]).name).unlink()
            reissued.append(
                (name, {**pin, "r2_key": f"another/{name}.u32le.gz"}, decoded_hash)
            )
        self.release_assets.return_value = (reissued, self.config_pin)
        second = command.compare_release(
            self.run, "v8.4-rc.2", self.root / "second", work_dir=self.root
        )
        self.assertEqual(second["input_sha256"], report["input_sha256"])
        self.assertEqual(self.storage.get_object.call_count, 3)

    def test_command_rejects_incomplete_build_without_reading_release(self):
        self.build_report.write_text('{"status":"incomplete"}')
        with (
            patch(
                "sys.argv",
                [
                    "worldatlas-compare",
                    str(self.run),
                    "v8.3",
                    str(self.output),
                    "--work-dir",
                    str(self.root),
                ],
            ),
            redirect_stderr(io.StringIO()) as stderr,
            self.assertRaises(SystemExit) as failure,
        ):
            command.main()
        self.assertEqual(failure.exception.code, 2)
        self.assertIn("a completed map build is required", stderr.getvalue())
        self.release_assets.assert_not_called()

    def test_existing_output_and_changed_selection_fail_before_release_lookup(self):
        self.output.mkdir()
        with self.assertRaisesRegex(
            FileExistsError, "comparison output already exists"
        ):
            self.compare()
        self.output.rmdir()
        (self.run / "input-selection.json").write_text('{}')
        with self.assertRaisesRegex(ValueError, "saved geographic selection changed"):
            self.compare()
        self.release_assets.assert_not_called()

    def test_different_grid_leaves_no_comparison_output(self):
        config = {**self.config, "width": 8, "step": 45}
        config_pin = self.store("release/config.json", json.dumps(config).encode())
        self.release_assets.return_value = (self.streams, config_pin)
        with self.assertRaisesRegex(ValueError, "must use the same grid"):
            self.compare()
        self.assertFalse(self.output.exists())

    def test_changed_final_stream_leaves_no_comparison_output(self):
        (self.run / "final/runs.u32le").write_bytes(struct.pack("<4I", 3, 2, 4, 1))
        with self.assertRaisesRegex(ValueError, "final map files changed"):
            self.compare()
        self.assertFalse(self.output.exists())

    def test_invalid_decoded_stream_leaves_no_cached_file(self):
        name, pin, _ = self.streams[0]
        self.streams[0] = (name, pin, "0" * 64)
        with self.assertRaisesRegex(
            ValueError, "decoded reference stream hash mismatch"
        ):
            self.compare()
        self.assertEqual(list((self.root / "inputs").glob("release-*/*")), [])
        self.assertFalse(self.output.exists())
