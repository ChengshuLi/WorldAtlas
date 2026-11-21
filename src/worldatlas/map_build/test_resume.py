"""Resume validates selected data and outputs while trusting code changes."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from worldatlas.map_build import build as pipeline
from worldatlas.map_build.test_support import selection
from worldatlas.shared.files import pin_file, read_json, write_json


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
            "input_root": str(self.root),
            "grid": dict(width=36, height=18, step=10),
            "sources": {
                "land_config": {
                    "land": [
                        {"dataset": str(self.source), "files": [pin_file(self.source)]}
                    ]
                },
                "inland_water": {"rasterization": {}, "files": []},
            },
        }
        self.config = write_json(inputs / "request.json", cfg)
        self.saved_selection = write_json(inputs / "selection.json", selection())
        self.out = self.root / "run"

    def runner(self, resume=False):
        runner = pipeline.Pipeline(
            self.config, self.out, resume=resume, selection=self.saved_selection
        )
        self.addCleanup(runner.close)
        return runner

    def test_changed_completed_output_fails_before_reuse(self):
        first = self.runner()
        self.execute(first)
        first.close()
        (self.out / "result/result.bin").write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "output changed"):
            self.runner(resume=True)

    def test_changed_input_pin_fails_before_reuse(self):
        first = self.runner()
        self.execute(first)
        first.close()
        self.source.write_bytes(b"changed input")
        with self.assertRaisesRegex(ValueError, "selected source file differs"):
            self.runner(resume=True)

    def test_lost_timing_prefix_is_rejected_before_checkpoint_reuse(self):
        first = self.runner()
        self.execute(first)
        first.close()
        (self.out / "timing-events.jsonl").write_bytes(b"")
        with self.assertRaisesRegex(ValueError, "timing journal lost"):
            self.runner(resume=True)

    def test_changed_code_is_recorded_and_resume_keeps_the_original_identity(self):
        first = self.runner()
        self.assertEqual(
            read_json(self.out / "build-config.json"), read_json(self.config)
        )
        original = pin_file(self.out / "run-identity.json")
        first.close()
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

    def test_resume_marks_an_interrupted_setup_with_no_sealed_timing(self):
        runner = self.runner()
        runner.close()
        interrupted = self.out / "attempts" / "interrupted"
        interrupted.mkdir()
        resumed = self.runner(resume=True)
        incomplete = [
            event for event in resumed.timing.records
            if event["event"] == "unmeasured-initialization"
        ]
        self.assertEqual([event["attempt"] for event in incomplete], ["interrupted"])

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
            (),
            timing=runner.timing,
            inputs=[pin_file(self.source)],
            outputs=[output],
        )
