"""Resume validates selected data and outputs while trusting code changes."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from worldatlas.map_build import build as pipeline
from worldatlas.map_build.execution import timing
from worldatlas.map_build.test_support import selection
from worldatlas.shared.files import json_bytes, pin_file, read_json, write_json


class ExecutorResumeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        inputs = self.root / "inputs"
        inputs.mkdir()
        self.source = inputs / "source.bin"
        self.source.write_bytes(b"final-output\x00\x01\x02")
        cfg = {
            "schema": "worldatlas-end-to-end-pipeline-v3",
            "grid": dict(width=36, height=18, step=10),
            "sources": {
                "land_config": {
                    "land": [
                        {"dataset": str(self.source), "files": [pin_file(self.source)]}
                    ]
                },
                "inland_water": {
                    "file_count": 1,
                    "files": [{"path": "water.parquet", "sha256": "a" * 64}],
                },
            },
        }
        self.config = write_json(inputs / "request.json", cfg)
        self.saved_selection = write_json(inputs / "selection.json", selection())
        self.out = self.root / "run"

    def runner(self, resume=False):
        runner = pipeline.Pipeline(
            self.config, self.out, work_dir=self.root,
            resume=resume, selection=None if resume else self.saved_selection,
        )
        self.addCleanup(runner.close)
        return runner

    def test_changed_completed_output_fails_before_reuse(self):
        first = self.runner()
        self.execute(first)
        first.close()
        (self.out / "result/result.bin").write_bytes(b"changed")
        attempts = self.out / "attempts"
        with self.assertRaisesRegex(ValueError, "output changed"):
            self.runner(resume=True)
        self.assertEqual(list(attempts.iterdir()), [first.attempt_dir])

    def test_changed_input_pin_fails_before_reuse(self):
        first = self.runner()
        self.execute(first)
        first.close()
        self.source.write_bytes(b"changed input")
        with self.assertRaisesRegex(ValueError, "checkpoint/input hash mismatch"):
            self.runner(resume=True)

    def test_lost_timing_prefix_is_rejected_before_checkpoint_reuse(self):
        first = self.runner()
        self.execute(first)
        first.close()
        (self.out / "timing-events.jsonl").write_bytes(b"")
        with self.assertRaisesRegex(ValueError, "timing journal lost"):
            self.runner(resume=True)
        self.assertEqual(list((self.out / "attempts").iterdir()), [first.attempt_dir])

    def test_changed_code_is_recorded_and_resume_keeps_the_original_identity(self):
        first = self.runner()
        self.assertEqual(
            (self.out / "build-config.json").read_bytes(), self.config.read_bytes()
        )
        first.close()
        identity_path = self.out / "run-identity.json"
        identity = read_json(identity_path)
        for key in ("code", "repository", "runtime", "runtime_paths", "scripts_root"):
            self.assertNotIn(key, identity)
        original = pin_file(identity_path)
        with (
            patch.object(
                pipeline, "code_identity", return_value={"changed.py": "0" * 64}
            ),
            patch.object(
                pipeline, "repository_identity", return_value={"commit": "changed"}
            ),
        ):
            resumed = self.runner(resume=True)
            self.assertEqual(pin_file(self.out / "run-identity.json"), original)
            self.assertEqual(
                read_json(resumed.attempt_dir / "producer.json")["code"],
                {"changed.py": "0" * 64},
            )

    def test_resume_rejects_an_earlier_checkpoint_layout_before_starting_an_attempt(self):
        first = self.runner()
        first.close()
        identity = self.out / "run-identity.json"
        identity.write_bytes(json_bytes(read_json(identity) | {"schema": "worldatlas-end-to-end-run-identity-v1"}))
        with self.assertRaisesRegex(ValueError, "original checkpoint format"):
            self.runner(resume=True)
        self.assertEqual(list((self.out / "attempts").iterdir()), [first.attempt_dir])

    def test_two_live_runners_cannot_resume_same_run(self):
        self.runner()
        with self.assertRaisesRegex(ValueError, "another pipeline runner"):
            self.runner(resume=True)

    def test_saved_build_configuration_must_match_on_resume(self):
        first = self.runner()
        first.close()
        (self.out / "build-config.json").write_bytes(b"{}")
        with self.assertRaisesRegex(ValueError, "saved build configuration changed"):
            self.runner(resume=True)
        self.assertEqual(list((self.out / "attempts").iterdir()), [first.attempt_dir])

    def test_resume_marks_an_interrupted_setup_with_no_sealed_timing(self):
        runner = self.runner()
        runner.close()
        interrupted = self.out / "attempts" / "interrupted"
        interrupted.mkdir()
        resumed = self.runner(resume=True)
        summary = resumed.timing.summary()["setup"]
        self.assertEqual(
            [event["attempt"] for event in summary["unmeasured_interrupted_attempts"]],
            ["interrupted"],
        )
        self.assertNotIn(
            "unmeasured-initialization", (self.out / "timing-events.jsonl").read_text()
        )
        resumed.close()
        resumed_again = self.runner(resume=True)
        summary = resumed_again.timing.summary()["setup"]
        self.assertFalse(summary["timing_complete"])
        self.assertEqual(
            [event["attempt"] for event in summary["unmeasured_interrupted_attempts"]],
            ["interrupted"],
        )

    def test_resume_starts_the_timing_log_if_first_setup_failed_before_opening_it(self):
        with patch.object(timing, "create_journal", side_effect=OSError("disk unavailable")):
            with self.assertRaisesRegex(OSError, "disk unavailable"):
                self.runner()
        interrupted, = (self.out / "attempts").iterdir()
        self.assertFalse((self.out / "timing-events.jsonl").exists())

        resumed = self.runner(resume=True)
        setup = resumed.timing.summary()["setup"]
        self.assertTrue(setup["outputs_complete"])
        self.assertFalse(setup["timing_complete"])
        self.assertEqual(
            setup["unmeasured_interrupted_attempts"],
            [{"attempt": interrupted.name, "id": "setup/interrupted-initialization"}],
        )

    def test_corrupt_unsealed_timing_releases_the_run_lock(self):
        runner = self.runner()
        runner.close()
        journal = self.out / "timing-events.jsonl"
        prior = journal.read_bytes()
        journal.write_bytes(prior + b'bad JSON\n{"event": "attempt"}\n')
        with self.assertRaisesRegex(ValueError, "invalid timing journal before final"):
            self.runner(resume=True)
        journal.write_bytes(prior)
        self.runner(resume=True)

    def test_each_failed_attempt_keeps_its_own_failure_report(self):
        first = self.runner()
        with (
            patch.object(first, "physical", side_effect=ValueError("first failure")),
            self.assertRaisesRegex(ValueError, "first failure"),
        ):
            first.run()
        first_failure = first.attempt_dir / "failure.json"
        first_report = first_failure.read_bytes()

        def write(path, value):
            if path.name == "setup-timing.json":
                raise OSError("cannot save setup timing")
            return write_json(path, value)

        with patch.object(timing, "write_json", side_effect=write):
            with self.assertRaisesRegex(OSError, "cannot save setup timing"):
                self.runner(resume=True)

        resumed = self.runner(resume=True)
        resumed_failure = resumed.attempt_dir / "failure.json"
        self.assertFalse(resumed_failure.exists())
        summary = resumed.timing.summary()["setup"]
        self.assertTrue(summary["timing_complete"])
        self.assertEqual(summary["unmeasured_interrupted_attempts"], [])
        with (
            patch.object(resumed, "physical", side_effect=ValueError("second failure")),
            self.assertRaisesRegex(ValueError, "second failure"),
        ):
            resumed.run()
        self.assertEqual(read_json(resumed_failure)["status"], "incomplete")
        self.assertEqual(first_failure.read_bytes(), first_report)
        self.assertFalse((self.out / "failure.json").exists())

    def execute(self, runner):
        output = self.out / "result"

        def calculate():
            output.mkdir()
            (output / "result.bin").write_bytes(self.source.read_bytes())
            return {"directory": str(output)}

        return runner.checkpoints.run_function(
            "fixture-stage",
            "water",
            calculate,
            timing=runner.timing,
            inputs=[pin_file(self.source)],
            outputs=[output],
        )
